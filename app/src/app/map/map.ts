import { Component, ElementRef, OnDestroy, afterNextRender, inject, viewChild } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { forkJoin } from 'rxjs';
// maplibre-gl 6.x 沒有 default export，只有具名匯出——`Map` 別名成 `MapLibreMap`，
// 避免跟全域內建的 Map（這個專案別處已經在用，例如 graph-coloring.ts 的
// Map<string, Set<string>>）撞名。
import { Map as MapLibreMap, Marker, NavigationControl } from 'maplibre-gl';
import type { FeatureCollection, MultiPolygon } from 'geojson';
import {
  assignTerritoryColorSlots,
  buildColorSlotMatchExpression,
  type TerritoryFeatureProperties,
} from '../core/geometry/territory-styling';
import { computeTerritoryLabelPoints } from '../core/geometry/territory-labels';
import { TERRITORY_COLOR_SLOTS } from '../core/design/territory-colors';

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
 * 任務 3.5（2026-08-29）：接上政權疆域圖層——基礎版。**暫定固定年份**（見
 * `TERRITORY_YEAR`）：時間拉桿（3.3/3.4）還沒做，先用一個具代表性的年份驗證整條
 * 資料管線（後端 GeoJSON → 相鄰計算 → 圖著色 → MapLibre 渲染）能不能動起來；拖拉桿
 * 即時換年份、疆域快照間的連續形變（3.6）都留給之後的任務。
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

  private map?: MapLibreMap;
  private labelMarkers: Marker[] = [];

  /** 暫定年份，見類別註解——三國疆域爭奪最激烈的荊州易手期已過、三方鼎立局面穩定，
      適合當「證明整條管線能動」的示範年份。 */
  private static readonly TERRITORY_YEAR = 225;

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
    this.map.on('load', () => this.loadTerritories());
  }

  private loadTerritories(): void {
    forkJoin({
      territories: this.http.get<ApiEnvelope<FeatureCollection<MultiPolygon, TerritoryFeatureProperties>>>(
        `/api/v1/territories?year=${MapComponent.TERRITORY_YEAR}`,
      ),
      // 不加 ?year=——一次拿全部政權建好 id→名稱對照表，不管地圖目前顯示哪個年份都能
      // 重複用。政權本身的存在不隨年份變動，變動的是「哪些政權的疆域快照落在這個
      // 年份」，那是 territories 端點自己的篩選邏輯，兩者不用綁在一起查。
      regimes: this.http.get<ApiEnvelope<RegimeSummary[]>>('/api/v1/regimes'),
    }).subscribe({
      next: ({ territories, regimes }) => this.renderTerritories(territories.data, regimes.data),
      // 第一版先求「資料管線走得通看得到東西」，還沒有失敗時的 UI 呈現（例如錯誤
      // 提示列）——那屬於之後才需要拍板的 loading/error 狀態設計，這裡先用
      // console.error 讓問題在開發時看得到，不是刻意省略錯誤處理。
      error: (err: unknown) => console.error('[MapComponent] 載入疆域/政權資料失敗', err),
    });
  }

  private renderTerritories(
    featureCollection: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>,
    regimes: RegimeSummary[],
  ): void {
    if (!this.map) {
      return;
    }

    // 相鄰計算＋圖著色（純函式，見 core/geometry/territory-styling.ts）——這一步把
    // 色格索引寫回每個 feature.properties.colorSlot，下面的 fill-color expression
    // 直接讀這個欄位。
    assignTerritoryColorSlots(featureCollection, TERRITORY_COLOR_SLOTS.length);

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

    this.renderLabels(featureCollection, regimes);
  }

  /** 政權名稱標籤——刻意用 `Marker` 掛 HTML 元素，不是 MapLibre 原生 symbol 圖層的
      `text-field`，理由見 territory-labels.ts 開頭說明（避免另外接字型 glyphs 服務）。 */
  private renderLabels(
    featureCollection: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>,
    regimes: RegimeSummary[],
  ): void {
    if (!this.map) {
      return;
    }

    this.clearLabelMarkers();

    const nameByRegimeId = new Map(regimes.map((r) => [r.id, r.selfName]));
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
