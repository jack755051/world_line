import { Component, DestroyRef, ElementRef, Injector, OnDestroy, afterNextRender, inject, viewChild } from '@angular/core';
import { takeUntilDestroyed, toObservable } from '@angular/core/rxjs-interop';
import { HttpClient } from '@angular/common/http';
import { debounceTime } from 'rxjs';
// maplibre-gl 6.x 沒有 default export，只有具名匯出——`Map` 別名成 `MapLibreMap`，
// 避免跟全域內建的 Map（這個專案別處已經在用，例如 graph-coloring.ts 的
// Map<string, Set<string>>）撞名。
import { Map as MapLibreMap, Marker, NavigationControl, type GeoJSONSource } from 'maplibre-gl';
import type { FeatureCollection, MultiPolygon } from 'geojson';
import {
  assignTerritoryColorSlots,
  buildColorSlotMatchExpression,
  type TerritoryFeatureProperties,
} from '../core/geometry/territory-styling';
import { computeTerritoryLabelPoints } from '../core/geometry/territory-labels';
import { territoryHatchImageId } from '../core/geometry/territory-dispute-pattern';
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
 * **爭議控制區斜線網底**（同日補上，使用者拖桿看到蜀漢/東吳疆域重疊、問「這是什麼
 * 意思」才發現 `isDisputed` 資料早就有、只是沒畫出來）：`territories-disputed-hatch`
 * 圖層疊在 `territories-fill` 之上，只對 `isDisputed=true` 的 feature 套用同色相加深
 * 一階的斜線網底（Canvas Pattern，見 territory-dispute-pattern.ts），讓「同一塊地兩種
 * 史觀並存」的爭議狀態一眼可辨，不會誤以為是資料重疊錯誤。
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

    const existingSource = this.map.getSource('territories') as GeoJSONSource | undefined;
    if (existingSource) {
      // 換年份時走這條路：只換資料，不重新 addLayer——避免圖層被整個移除重建造成閃爍。
      existingSource.setData(featureCollection);
    } else {
      // 第一次渲染：建立 source 跟兩個圖層。
      this.map.addSource('territories', { type: 'geojson', data: featureCollection });

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

      const borderColor = getComputedStyle(document.documentElement)
        .getPropertyValue('--wl-territory-border')
        .trim();

      this.map.addLayer({
        id: 'territories-border',
        type: 'line',
        source: 'territories',
        // 疆域邊界線維持單一中性色，不跟填色搶識別色資源（design-tokens.scss、PRD §6
        // 「政權識別色不是固定對照表」段落已拍板）。
        paint: { 'line-color': borderColor || '#52514e', 'line-width': 1 },
      });

      // 爭議控制區（isDisputed=true）疊一層斜線網底——同色相加深一階，tone-on-tone，
      // 不是另外挑一個全域固定顏色（見 territory-dispute-pattern.ts 開頭說明）。5 個
      // 色格各自註冊一張圖樣，跟 territories-fill 共用同一組 colorSlot 對照。
      const hatchPatternIds = TERRITORY_COLOR_SLOTS.map((_, i) => territoryHatchImageId(i));
      TERRITORY_COLOR_SLOTS.forEach((hex, i) => {
        const imageId = territoryHatchImageId(i);
        if (!this.map!.hasImage(imageId)) {
          this.map!.addImage(imageId, this.hatchPatterns.create(hex));
        }
      });

      this.map.addLayer({
        id: 'territories-disputed-hatch',
        type: 'fill',
        source: 'territories',
        // 2026-08-29 除錯記錄：原本用 `filter: ['==', ['get','isDisputed'], true]`
        // 排除非爭議疆域，實測（使用者實際在瀏覽器拖拉桿到 208-214 年）漢（isDisputed
        // 確認為 false，用瀏覽器 Console 直接 fetch 驗證過）還是被畫上網底，懷疑是
        // MapLibre 的 filter 在 `source.setData()` 動態換資料時沒有正確重新套用（第一次
        // 建圖層時的資料剛好是 0 筆爭議疆域，換年份後 filter 疑似沒跟著新資料重新篩選，
        // 根因未完全確認）。改成不用 filter，讓所有疆域都進這個圖層，改用
        // fill-opacity 的 case expression 依 isDisputed 決定要不要顯示（非爭議的直接
        // 設成全透明）——paint 屬性保證會跟著 setData() 每次重新求值，不依賴 filter
        // 在動態資料下的重新套用行為，繞開這個未完全查明根因的邊界案例。
        paint: {
          'fill-pattern': buildColorSlotMatchExpression(hatchPatternIds) as unknown as string,
          'fill-opacity': ['case', ['==', ['get', 'isDisputed'], true], 1, 0] as unknown as number,
        },
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
