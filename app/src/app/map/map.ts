import { Component, DestroyRef, ElementRef, Injector, OnDestroy, afterNextRender, inject, viewChild } from '@angular/core';
import { takeUntilDestroyed, toObservable } from '@angular/core/rxjs-interop';
import { HttpClient } from '@angular/common/http';
import { debounceTime } from 'rxjs';
// maplibre-gl 6.x 沒有 default export，只有具名匯出——`Map` 別名成 `MapLibreMap`，
// 避免跟全域內建的 Map（這個專案別處已經在用，例如 graph-coloring.ts 的
// Map<string, Set<string>>）撞名。
import { Map as MapLibreMap, Marker, NavigationControl, type GeoJSONSource } from 'maplibre-gl';
import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson';
import {
  assignTerritoryColorSlots,
  buildColorSlotMatchExpression,
  type TerritoryFeatureProperties,
} from '../core/geometry/territory-styling';
import { computeTerritoryLabelPoints } from '../core/geometry/territory-labels';
import { computeTerritoryOverlaps } from '../core/geometry/territory-overlap';
import { TerritoryHatchPatternService } from '../core/geometry/territory-hatch-pattern.service';
import { TERRITORY_COLOR_SLOTS } from '../core/design/territory-colors';
import { TimelineState } from '../core/time/timeline-state';

/** `ApiResponse<T>` 的最小形狀（見 api/Contracts/ApiResponse.cs）——只取這裡用得到的
    `data` 欄位，不整個對照完整契約，畢竟目前只有這一個端點在消費。 */
interface ApiEnvelope<T> {
  data: T;
}

/** `GET /api/v1/regimes` 回應的最小形狀（見 api/Contracts/RegimeResponse.cs）——這裡
    只取畫標籤用得到的 id/selfName，其餘欄位（status、轉換邊）暫時用不到不列。 */
interface RegimeSummary {
  id: string;
  selfName: string;
}

/** 疆域重疊區斜線網底用的圖樣 id——單一中性色，不分政權（見 territory-dispute-pattern.ts
    開頭說明）。 */
const OVERLAP_HATCH_IMAGE_ID = 'territory-overlap-hatch';

/**
 * 底圖決策（2026-08-29，任務 3.2）：**不接外部瓦片服務**，用中性背景色當畫布，
 * 不畫海岸線/現代地名參考層。理由：
 * - 專案的疆域資料本來就自己從 OpenHistoricalMap 取 GeoJSON（見 PRD §5），不依賴
 *   第三方瓦片服務這個方向本來就已經定案，底圖跟著同一個原則走。
 * - 歷史地圖疊在「現代國界/現代地名」的底圖上，會有時代錯置的觀感問題（例如三國
 *   疆域疊在現代中國省界上）；之後真的需要海岸線等物理地理參考時，用公眾領域的
 *   靜態海岸線 GeoJSON 疊一層即可，不需要為此換成瓦片服務。
 * - 零外部依賴、零 API key／流量限制風險，符合目前單人自用開發階段的需求。
 *
 * 背景色不寫死色碼，直接讀 --wl-page 的 computed 值——避免跟 design-tokens.scss
 * 顏色定義兩處各自維護、之後改色沒同步更新的風險（這個專案已經因為「兩處各自維護
 * 同一個概念」踩過真的 bug，見憲法/PRD 對 regimes.status 字面值飄移的記錄）。
 *
 * 任務 3.5（2026-08-29）：接上政權疆域圖層。任務 3.3（同日）接上時間拉桿後，年份
 * 不再寫死——訂閱 `TimelineState.year`（debounce 150ms，避免拖桿時每個中間值都發一次
 * 請求），年份變動時重新查詢疆域並用 `source.setData()` 更新，不重新 `addSource`/
 * `addLayer`（MapLibre 官方建議的動態資料更新方式，避免圖層閃爍重建）。**疆域快照間的
 * 連續形變（3.6）還沒做**：現在換年份是「整批資料換掉」，不是真的插值形變，見任務
 * 3.6。政權清單只在地圖初始化時抓一次（不隨年份重複查），因為政權本身的存在不隨
 * 年份變動，變動的是「哪些政權的疆域快照落在這個年份」。
 *
 * **疆域重疊區斜線網底**（同日補上、同日修正一次語意）：第一版直接讀
 * `isDisputed` 整筆記錄畫網底，使用者指出這樣邏輯站不住腳（一整筆疆域記錄裡沒有
 * 爭議的部分也會被畫成整塊爭議，類比二戰後英法美蘇瓜分德國的佔領區，邊界是條約明訂
 * 沒有史料分歧，套用同一套判斷會荒謬地全部畫成爭議）。改成**即時計算幾何交集**
 * （`territory-overlap.ts`）——斜線只畫在真的有面積重疊的地方，不依賴任何手動標記的
 * 旗標，不管以後匯入什麼史料、任兩塊疆域重疊都會自動正確顯示。
 */
@Component({
  selector: 'app-map',
  standalone: true,
  templateUrl: './map.html',
  styleUrl: './map.scss',
})
export class MapComponent implements OnDestroy {
  private readonly mapContainer = viewChild.required<ElementRef<HTMLDivElement>>('mapContainer');
  private readonly http = inject(HttpClient);
  private readonly timeline = inject(TimelineState);
  private readonly hatchPatterns = inject(TerritoryHatchPatternService);
  private readonly injector = inject(Injector);
  private readonly destroyRef = inject(DestroyRef);

  private map?: MapLibreMap;
  private labelMarkers: Marker[] = [];
  private regimeNames: RegimeSummary[] = [];
  /** 圖著色的「前一次指派結果」，餵給 `assignTerritoryColorSlots()` 維持顏色穩定性
      （見 graph-coloring.ts）——拖拉桿換年份時，同一個政權不會無謂換色閃爍。 */
  private previousColorAssignment?: Map<string, number>;

  constructor() {
    afterNextRender(() => this.initMap());
  }

  private initMap(): void {
    const backgroundColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--wl-page')
      .trim();

    this.map = new MapLibreMap({
      container: this.mapContainer().nativeElement,
      style: {
        version: 8,
        sources: {},
        layers: [
          {
            id: 'background',
            type: 'background',
            paint: { 'background-color': backgroundColor || '#f9f9f7' },
          },
        ],
      },
      // 暫定中心點：目前種子資料是三國時期中國，之後接上疆域範圍自動置中時
      // 再改成動態計算，這裡先給一個合理的固定預設值。
      center: [110, 32],
      zoom: 3,
      attributionControl: false, // 沒有接外部瓦片服務，不需要顯示歸屬聲明
    });

    this.map.addControl(new NavigationControl(), 'top-right');
    this.map.on('load', () => this.loadRegimesThenSubscribeToYear());
  }

  private loadRegimesThenSubscribeToYear(): void {
    // 不加 ?year=——一次拿全部政權建好 id→名稱對照表，不管地圖目前顯示哪個年份都能
    // 重複用，不需要每次換年份都重新查一次政權清單。
    this.http.get<ApiEnvelope<RegimeSummary[]>>('/api/v1/regimes').subscribe({
      next: (response) => {
        this.regimeNames = response.data;

        // toObservable 需要 injection context——這裡是在 map.on('load', ...) 的
        // callback 裡（非同步），已經離開建構子當下的 injection context，要明確傳
        // injector 選項才能用；debounceTime 避免拖拉桿時每個中間值都打一次 API。
        toObservable(this.timeline.year, { injector: this.injector })
          .pipe(debounceTime(150), takeUntilDestroyed(this.destroyRef))
          .subscribe((year) => this.loadTerritories(year));
      },
      error: (err: unknown) => console.error('[MapComponent] 載入政權清單失敗', err),
    });
  }

  private loadTerritories(year: number): void {
    this.http
      .get<ApiEnvelope<FeatureCollection<MultiPolygon, TerritoryFeatureProperties>>>(
        `/api/v1/territories?year=${year}`,
      )
      .subscribe({
        next: (response) => this.renderTerritories(response.data),
        // 第一版先求「資料管線走得通看得到東西」，還沒有失敗時的 UI 呈現（例如錯誤
        // 提示列）——那屬於之後才需要拍板的 loading/error 狀態設計，這裡先用
        // console.error 讓問題在開發時看得到，不是刻意省略錯誤處理。
        error: (err: unknown) => console.error('[MapComponent] 載入疆域資料失敗', err),
      });
  }

  private renderTerritories(featureCollection: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>): void {
    if (!this.map) {
      return;
    }

    // 相鄰計算＋圖著色（純函式，見 core/geometry/territory-styling.ts）——這一步把
    // 色格索引寫回每個 feature.properties.colorSlot，下面的 fill-color expression
    // 直接讀這個欄位。傳入 previousColorAssignment 維持顏色穩定性。
    this.previousColorAssignment = assignTerritoryColorSlots(
      featureCollection,
      TERRITORY_COLOR_SLOTS.length,
      this.previousColorAssignment,
    );

    // 疆域重疊區（見 territory-overlap.ts）——不依賴任何手動標記的旗標，即時算幾何交集，
    // 只算「不同政權」之間的重疊（同一個政權自己底下多筆疆域記錄互相重疊，不算「政權
    // 重疊」，一律用顏色表示），所以要傳 regimeId，不能只傳 id。
    const overlaps: FeatureCollection<Polygon | MultiPolygon> = {
      type: 'FeatureCollection',
      features: computeTerritoryOverlaps(
        featureCollection.features.map((f) => ({
          id: f.properties.id,
          regimeId: f.properties.regimeId,
          geometry: f.geometry,
        })),
      ).map((geometry) => ({ type: 'Feature', properties: {}, geometry })),
    };

    const existingSource = this.map.getSource('territories') as GeoJSONSource | undefined;
    const existingOverlapSource = this.map.getSource('territory-overlaps') as GeoJSONSource | undefined;

    if (existingSource && existingOverlapSource) {
      // 換年份時走這條路：只換資料，不重新 addLayer——避免圖層被整個移除重建造成閃爍。
      existingSource.setData(featureCollection);
      existingOverlapSource.setData(overlaps);
    } else {
      // 第一次渲染：建立兩個 source 跟三個圖層。
      this.map.addSource('territories', { type: 'geojson', data: featureCollection });
      this.map.addSource('territory-overlaps', { type: 'geojson', data: overlaps });

      this.map.addLayer({
        id: 'territories-fill',
        type: 'fill',
        source: 'territories',
        paint: {
          // MapLibre 的 expression 型別是遞迴 tuple union，buildColorSlotMatchExpression()
          // 回傳 unknown[] 沒辦法結構化對上，這裡轉型一次，交給 MapLibre 執行期自己驗證格式。
          'fill-color': buildColorSlotMatchExpression(TERRITORY_COLOR_SLOTS) as unknown as string,
          'fill-opacity': 0.85,
        },
      });

      const borderColor =
        getComputedStyle(document.documentElement).getPropertyValue('--wl-territory-border').trim() || '#52514e';
      // 爭議區専用色——design-tokens.scss 的 --wl-dispute-* 紅色階（2026-08-29 拍板），
      // 跟 territories-border 的中性灰刻意分開：中性灰是「疆域邊界」這個結構性語意，
      // 紅色才是「這裡有政權主張衝突」這個內容語意，兩者不該共用同一個 token。
      const disputeColor =
        getComputedStyle(document.documentElement).getPropertyValue('--wl-dispute-500').trim() || '#b83333';

      this.map.addLayer({
        id: 'territories-border',
        type: 'line',
        source: 'territories',
        // 疆域邊界線維持單一中性色，不跟填色搶識別色資源（design-tokens.scss、PRD §6
        // 「政權識別色不是固定對照表」段落已拍板）。
        paint: { 'line-color': borderColor, 'line-width': 1 },
      });

      // 疆域重疊區——先鋪一層不透明的爭議紅底色，再疊斜線網底。**不能只疊網底**：網底
      // 圖樣本身背景是透明的（只有斜線本身不透明，見 createDiagonalHatchImageData()），
      // 疊在 territories-fill 上面時，透明部分會透出底下「剛好排在後面那個政權」的
      // 顏色，看起來像這塊地「只屬於其中一個政權」——使用者實機發現這個問題（重疊區
      // 看起來像單純東吳的顏色加網底，看不出蜀漢也宣稱這塊地）。先鋪不透明底色蓋掉
      // 底下兩個政權各自的顏色，才能明確傳達「這裡不屬於任何單一政權，是重疊爭議
      // 區」；改用 --wl-dispute-500 而非中性灰是因為「爭議」本身是需要被看見的內容
      // 語意，不只是結構線條，見 design-tokens.scss 該 token 區塊的說明。不是
      // tone-on-tone：重疊區可能同時牽涉兩個以上不同色相的政權，不屬於任何單一政權的
      // 識別色，見 territory-dispute-pattern.ts 開頭說明。
      this.map.addLayer({
        id: 'territory-overlaps-fill',
        type: 'fill',
        source: 'territory-overlaps',
        paint: { 'fill-color': disputeColor, 'fill-opacity': 1 },
      });

      if (!this.map.hasImage(OVERLAP_HATCH_IMAGE_ID)) {
        this.map.addImage(OVERLAP_HATCH_IMAGE_ID, this.hatchPatterns.create(disputeColor));
      }

      this.map.addLayer({
        id: 'territory-overlaps-hatch',
        type: 'fill',
        source: 'territory-overlaps',
        paint: { 'fill-pattern': OVERLAP_HATCH_IMAGE_ID },
      });
    }

    this.renderLabels(featureCollection);
  }

  /** 政權名稱標籤——刻意用 `Marker` 掛 HTML 元素，不是 MapLibre 原生 symbol 圖層的
      `text-field`，理由見 territory-labels.ts 開頭說明（避免另外接字型 glyphs 服務）。 */
  private renderLabels(featureCollection: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>): void {
    if (!this.map) {
      return;
    }

    this.clearLabelMarkers();

    const nameByRegimeId = new Map(this.regimeNames.map((r) => [r.id, r.selfName]));
    const labelPoints = computeTerritoryLabelPoints(featureCollection);

    for (const [regimeId, [lon, lat]] of labelPoints) {
      const name = nameByRegimeId.get(regimeId);
      if (!name) {
        continue; // 查無名稱（理論上不該發生，territories/regimes 資料不一致才會走到這裡）
      }

      const el = document.createElement('div');
      el.className = 'territory-label';
      el.textContent = name;

      const marker = new Marker({ element: el }).setLngLat([lon, lat]).addTo(this.map);
      this.labelMarkers.push(marker);
    }
  }

  private clearLabelMarkers(): void {
    for (const marker of this.labelMarkers) {
      marker.remove();
    }
    this.labelMarkers = [];
  }

  ngOnDestroy(): void {
    this.clearLabelMarkers();
    this.map?.remove();
  }
}
