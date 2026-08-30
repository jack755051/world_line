import { Component, DestroyRef, ElementRef, Injector, OnDestroy, afterNextRender, inject, viewChild } from '@angular/core';
import { takeUntilDestroyed, toObservable } from '@angular/core/rxjs-interop';
import { HttpClient } from '@angular/common/http';
import { debounceTime } from 'rxjs';
// maplibre-gl 6.x 沒有 default export，只有具名匯出——`Map` 別名成 `MapLibreMap`，
// 避免跟全域內建的 Map（這個專案別處已經在用，例如 graph-coloring.ts 的
// Map<string, Set<string>>）撞名。
import { Map as MapLibreMap, Marker, NavigationControl, type GeoJSONSource, type MapMouseEvent } from 'maplibre-gl';
import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson';
import {
  assignTerritoryColorSlots,
  buildColorSlotMatchExpression,
  type TerritoryFeatureProperties,
} from '../core/geometry/territory-styling';
import { computeTerritoryLabelPoints } from '../core/geometry/territory-labels';
import { computeTerritoryOverlaps, type TerritoryOverlap } from '../core/geometry/territory-overlap';
import { TerritoryHatchPatternService } from '../core/geometry/territory-hatch-pattern.service';
import { buildMorphPlan, easeInOutCubic, sampleMorphPlan, type MorphedFeatureProperties, type MorphPlan } from '../core/geometry/territory-morph';
import { MorphAnimationScheduler } from '../core/geometry/morph-animation-scheduler.service';
import { findNeighboringRegimeIds, findOtherContemporaryRegimeIds } from '../core/geometry/regime-focus';
import { TERRITORY_COLOR_SLOTS } from '../core/design/territory-colors';
import { TimelineState } from '../core/time/timeline-state';
import { RegimeDirectoryService } from '../core/regime/regime-directory.service';
import { RegimeFocusState } from '../core/regime/regime-focus-state';
import { RegimeAliasDirectoryService } from '../core/regime/regime-alias-directory.service';
import { NamingViewpointState } from '../core/regime/naming-viewpoint-state';

/** `ApiResponse<T>` 的最小形狀（見 api/Contracts/ApiResponse.cs）——只取這裡用得到的
    `data` 欄位，不整個對照完整契約，畢竟目前只有這一個端點在消費。 */
interface ApiEnvelope<T> {
  data: T;
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
 * **任務 3.17（2026-08-31）：補上上面說的「靜態海岸線 GeoJSON」**——`app/public/
 * ne_50m_land.geojson`（Natural Earth 1:50m Land，公眾領域 CC0，下載一次存成靜態
 * 檔案，瀏覽器跟自己的 origin 要，不是每次都打外部服務，維持零外部依賴原則）疊一層
 * 陸地色塊（`land-fill` 圖層，色票 `--wl-map-land`，比 `--wl-page`／海洋只深一階，
 * 純粹當地理方位參考，不能搶政權疆域填色的視覺重量）。**只畫陸地/海洋，不畫現代
 * 國界/現代地名**——上面提到的「時代錯置」疑慮只針對政治性邊界，物理地理（海岸線
 * 本身歷史上幾乎沒變過）不受這個疑慮影響，這正是任務 3.2 原本規劃的路線，不是推翻
 * 那個決策。
 *

 * 任務 3.5（2026-08-29）：接上政權疆域圖層。任務 3.3（同日）接上時間拉桿後，年份
 * 不再寫死——訂閱 `TimelineState.year`（debounce 150ms，避免拖桿時每個中間值都發一次
 * 請求），年份變動時重新查詢疆域。**換年份的畫面呈現方式見下方任務 3.6 的說明**（不再是
 * 單純的 `setData()` 硬切換）。政權清單只在地圖初始化時抓一次（不隨年份重複查），因為
 * 政權本身的存在不隨年份變動，變動的是「哪些政權的疆域快照落在這個年份」。
 *
 * **疆域重疊區斜線網底**（同日補上、同日修正一次語意）：第一版直接讀
 * `isDisputed` 整筆記錄畫網底，使用者指出這樣邏輯站不住腳（一整筆疆域記錄裡沒有
 * 爭議的部分也會被畫成整塊爭議，類比二戰後英法美蘇瓜分德國的佔領區，邊界是條約明訂
 * 沒有史料分歧，套用同一套判斷會荒謬地全部畫成爭議）。改成**即時計算幾何交集**
 * （`territory-overlap.ts`）——斜線只畫在真的有面積重疊的地方，不依賴任何手動標記的
 * 旗標，不管以後匯入什麼史料、任兩塊疆域重疊都會自動正確顯示。
 *
 * **任務 3.6（2026-08-30）：疆域快照間的連續形變**，對應憲法 §9「疆域必須連續變化
 * 呈現，非離散跳轉」。換年份時不再直接把新資料 `setData()` 上去做硬切換，改成用
 * `territory-morph.ts` 的 `buildMorphPlan()`／`sampleMorphPlan()`（Flubber.js 插值
 * 疆域環的座標點）跑一段固定時長的補間動畫，逐幀 `setData()`。**配對策略跟範圍限制**
 * 見 `territory-morph.ts` 開頭說明；這裡只說渲染面的決策：
 * - 有 `prefers-reduced-motion: reduce` 偏好設定的使用者，或是第一次載入（沒有「上一個
 *   狀態」可以形變過去），直接跳過動畫、瞬間顯示目標資料——不是每次都硬要播動畫。
 * - 動畫進行中，正在「出現」（entering）/「消失」（leaving）的疆域列（沒有形狀可以
 *   插值，見 territory-morph.ts）改用淡入/淡出（`morphOpacity`），連疆域重疊區網底
 *   也跟著兩個來源政權裡較晚出現/較早消失的那一邊一起淡，不會在來源政權自己都還沒
 *   「完全出現」時就先以滿版強度顯示重疊斜線（見 `territory-overlap.ts` 的
 *   `TerritoryOverlap.opacity`）。
 * - 動畫時序透過 `MorphAnimationScheduler`（DI 包裝 `requestAnimationFrame`）驅動，
 *   不是直接呼叫全域函式——理由跟 `TerritoryHatchPatternService` 包裝 Canvas 2D
 *   完全一樣：Angular 的 Vitest 整合不支援對相對路徑模組用 `vi.mock()`，需要 DI
 *   替換才能在測試裡把「真的等動畫播完」換成「立即跳到終點」，見 `map.spec.ts`。
 * - 拖拉桿拖得比動畫時長還快時，新一輪動畫會取消舊的（`morphToken` 比對 + 主動呼叫
 *   `cancelFrame`，雙重保險），不會有兩輪動畫同時搶著 `setData()`、新資料被舊動畫的
 *   殘留幀蓋掉的競態問題。
 * - 標籤（`Marker`）刻意不逐幀跟著疆域形狀移動，只在動畫終點（`settle()`）更新一次——
 *   這是刻意的 V1 範圍限制：逐幀重新算形心、搬動 DOM marker 位置的視覺效益，相對於
 *   額外的實作複雜度不成比例，之後真的有需求（例如使用者反應標籤位置跟疆域形狀動畫
 *   脫節很違和）再回頭做。
 *
 * **2026-08-30 修正兩個實機回報的問題**：
 * 1. 疆域環的插值不再一律交給 flubber 猜對應關係——頂點數相同時（目前種子資料的矩形
 *    永遠是這個情況）改成逐點線性插值，修正「明明只有一條邊移動，形變過程卻像在旋轉/
 *    不對稱拉伸」的問題，見 `territory-morph.ts` 的 `buildRingInterpolator()` 說明。
 * 2. `territory-overlap.ts` 的 `computeTerritoryOverlaps()` 現在會排除
 *    entering×leaving 這種跨政權配對——修正「漢禪魏、魏禪晉這種和平政權更迭，換年份
 *    動畫過程中會閃過一整塊紅色爭議斜線」的問題（根因：這個專案刻意讓禪讓前後兩個政權
 *    的疆域座標完全一致，交接瞬間舊政權淡出、新政權淡入，兩者座標重合被誤判成政權
 *    衝突）。詳見該函式文件註解的「政權更迭不是政權衝突」說明。
 *
 * **任務 3.7（2026-08-30）：政權聚焦模式**，對應 PRD Story 2。點擊 `territories-fill`
 * 圖層上的疆域（`map.on('click', ...)` + `queryRenderedFeatures()` 判斷點擊到哪個
 * regimeId，不是逐一比對疆域圖形），把 regimeId 寫進 `RegimeFocusState`（再點一次
 * 同一個政權會取消聚焦，跟一般「toggle」互動直覺一致）；沒點到任何疆域（點在背景）也
 * 會清除聚焦。渲染面：
 * - `territories-fill` 的 `fill-opacity` 改成聚焦中的政權維持原本不透明度、其餘政權
 *   大幅降低（「聚光燈」效果），跟形變動畫的 `morphOpacity` 相乘組合，兩者不衝突。
 * - 新增 `territories-focus-outline` 圖層（`filter` 綁定聚焦政權 id，`--wl-focus-ring`
 *   色，比一般疆域邊界粗），疊在所有圖層最上層，讓聚焦目標更醒目。
 * - 周邊政權清單重用圖著色也在用的同一套「政權層級相鄰關係」判斷（見
 *   `core/geometry/regime-focus.ts`），不是另外發明一套「周邊」定義；每次疆域資料
 *   定案（`settle()`）或聚焦目標改變時都重算一次，寫進 `RegimeFocusState`，讓拖拉桿
 *   換年份時周邊政權清單自動跟著更新（AC#1 隱含的要求：聚焦模式下換年份，畫面上的
 *   高亮/清單不能停留在舊年份的狀態）。
 * - 政權名稱對照表（原本是這個元件的私有欄位）抽成 `RegimeDirectoryService`
 *   （`providedIn:'root'`），跟政權聚焦面板（`RegimeFocusPanelComponent`）共用同一份、
 *   只打一次 `/api/v1/regimes`，不是各自重複查詢。
 *
 * **AC#3（互動清單，連結 `historical_events`/`regime_relations` 記錄）刻意不在這裡
 * 做**：後端對應端點（task 2.9、2.10）都還沒實作，沒有資料可以連結，跟任務 3.4
 * （時間軸副軸）因為事件資料還沒做而刻意跳過是同一個處理原則，見 implementation plan
 * 任務 3.7 的說明。
 *
 * **2026-08-30 追加「同時期、但不相鄰」的其他政權清單**（使用者提出：地理相鄰的周邊
 * 政權只是關係的一種，PRD §1 核心動機講的是「同一個時間點上同時看到多個文明/政權」，
 * 例如聚焦唐朝時阿拉伯帝國不接壤，但兩者是同時期存在的政權，也該呈現）。用
 * `regime-focus.ts` 的 `findOtherContemporaryRegimeIds()`：這批疆域資料裡除了聚焦
 * 政權自己、跟已經算出來的周邊政權以外，其餘政權全部算進去，不用額外查詢——當年有效
 * 的疆域資料本來就涵蓋地圖上所有政權。**目前種子資料規模下這個清單大概率是空的**
 * （漢/魏/蜀漢/吳/晉擠在同一小塊地理範圍，彼此幾乎都相鄰），不是邏輯錯誤，是還沒有
 * 真正「同時期不同地區」的政權資料可以示範，等之後匯入世界史資料才會開始出現東西，
 * 見該函式文件註解。
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
  private readonly scheduler = inject(MorphAnimationScheduler);
  private readonly regimeDirectory = inject(RegimeDirectoryService);
  private readonly focusState = inject(RegimeFocusState);
  private readonly aliasDirectory = inject(RegimeAliasDirectoryService);
  private readonly namingViewpoint = inject(NamingViewpointState);
  private readonly injector = inject(Injector);
  private readonly destroyRef = inject(DestroyRef);

  /** 形變動畫（任務 3.6）的固定時長——刻意不做成可調參數，目前沒有「使用者想調整動畫
      速度」這個需求，先寫死一個視覺上測過還算自然的值，之後真的有需求再拍板成 UI 選項。
      **2026-08-30 從 500ms 調高到 900ms**：使用者實機回報疆域有變動的年份切換時感覺
      突兀，500ms 對「疆域邊界移動」這種面積變化的視覺效果來說太快，人眼還來不及跟上
      形狀就已經定案了；900ms 讓變化過程有足夠時間被看清楚，同時還在「拖拉桿感覺是
      即時回饋」的合理範圍內（沒有拖到讓拖桿操作感覺遲鈍的程度）。 */
  private static readonly MORPH_DURATION_MS = 900;

  private map?: MapLibreMap;
  private labelMarkers: Marker[] = [];
  /** 圖著色的「前一次指派結果」，餵給 `assignTerritoryColorSlots()` 維持顏色穩定性
      （見 graph-coloring.ts）——拖拉桿換年份時，同一個政權不會無謂換色閃爍。 */
  private previousColorAssignment?: Map<string, number>;
  /** 目前畫面上已經「定案」的疆域資料（不是動畫過場中的中間幀）——`applyTerritories()`
      拿它當形變動畫的起點，`settle()` 每次定案後更新。第一次載入前是 `undefined`，
      用來判斷「這是第一次渲染，沒有上一個狀態可以形變過去，直接顯示」。 */
  private currentFeatureCollection?: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>;
  /** 目前排定中的動畫幀 handle，換年份換得比動畫時長還快時，用來取消上一輪還沒播完的
      動畫（見 `animateTo()`）。 */
  private morphFrameHandle?: number;
  /** 每次開始一輪新動畫就遞增——`step()` 回呼裡比對這個值，就算 `cancelFrame()`
      沒有真的立刻生效（或呼叫端忘了取消），過期的回呼也會被這個比對擋下，不會寫入
      已經被取代的舊資料，雙重保險。 */
  private morphToken = 0;

  constructor() {
    afterNextRender(() => this.initMap());
  }

  private initMap(): void {
    const backgroundColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--wl-page')
      .trim();
    const landColor = getComputedStyle(document.documentElement).getPropertyValue('--wl-map-land').trim();

    this.map = new MapLibreMap({
      container: this.mapContainer().nativeElement,
      style: {
        version: 8,
        // 任務 3.17：陸地/海洋參考層——`background` 圖層本身就是「海洋」（讀
        // `--wl-page`，跟 M1 決議一致，見下方 `land` source 的說明），`land` 這個
        // GeoJSON source 疊在上面畫出陸地色塊。這兩個圖層直接寫進初始 style（不像
        // 疆域圖層要等 'load' 事件後才 `addLayer()`）——不依賴任何 HTTP 請求回來的
        // 資料，沒有理由晚於地圖本身初始化。
        sources: {
          land: {
            type: 'geojson',
            // 靜態檔案，不是外部 API——Natural Earth 1:50m Land（公眾領域，CC0，不需
            // 標註來源），下載一次存進 `app/public/`（Angular assets glob 涵蓋整個
            // `public/` 目錄），瀏覽器直接跟自己的 origin 要這個檔案，不是每次都打
            // 外部服務，維持任務 3.2 拍板的「零外部依賴」原則。
            data: '/ne_50m_land.geojson',
          },
        },
        layers: [
          {
            id: 'background',
            type: 'background',
            paint: { 'background-color': backgroundColor || '#f9f9f7' },
          },
          {
            id: 'land-fill',
            type: 'fill',
            source: 'land',
            paint: { 'fill-color': landColor || '#e1e0d9' },
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
    this.map.on('click', (e) => this.handleMapClick(e));
    this.map.on('load', () => this.loadRegimesThenSubscribeToYear());
  }

  private loadRegimesThenSubscribeToYear(): void {
    // ensureLoaded() 是 idempotent 的快取載入（見 RegimeDirectoryService 說明），不管
    // 地圖目前顯示哪個年份都能重複用，不需要每次換年份都重新查一次政權清單。
    this.regimeDirectory.ensureLoaded().subscribe({
      next: () => {
        // toObservable 需要 injection context——這裡是在 map.on('load', ...) 的
        // callback 裡（非同步），已經離開建構子當下的 injection context，要明確傳
        // injector 選項才能用；debounceTime 避免拖拉桿時每個中間值都打一次 API。
        toObservable(this.timeline.year, { injector: this.injector })
          .pipe(debounceTime(150), takeUntilDestroyed(this.destroyRef))
          .subscribe((year) => this.loadTerritories(year));

        // 聚焦目標改變時（任務 3.7）：更新高亮圖層 + 重算周邊政權清單。跟年份訂閱
        // 分開，不用 debounce——點擊是離散動作，不像拖拉桿會連續觸發。
        toObservable(this.focusState.focusedRegimeId, { injector: this.injector })
          .pipe(takeUntilDestroyed(this.destroyRef))
          .subscribe(() => this.refreshFocusOverlay());

        // 命名視角改變時（任務 3.8）：重畫標籤，不用重打 territories，用已經快取的
        // currentFeatureCollection 就夠。刻意不在這裡就預先載入代稱資料——見
        // RegimeAliasDirectoryService 類別文件說明，只有使用者第一次切換到某個特定
        // 觀察視角（非 null）時才真的觸發 N 筆 GET /regimes/:id/aliases，之後靠
        // ensureLoaded() 內建的 shareReplay 快取，不會每次切換視角都重新查。
        toObservable(this.namingViewpoint.observerRegimeId, { injector: this.injector })
          .pipe(takeUntilDestroyed(this.destroyRef))
          .subscribe((observerId) => {
            if (!this.currentFeatureCollection) {
              return; // 疆域還沒載入完成，還沒有東西可以重畫標籤
            }
            if (observerId === null) {
              this.renderLabels(this.currentFeatureCollection);
              return;
            }
            this.aliasDirectory.ensureLoaded().subscribe({
              next: () => this.renderLabels(this.currentFeatureCollection!),
              error: (err: unknown) => console.error('[MapComponent] 載入政權代稱資料失敗', err),
            });
          });
      },
      error: (err: unknown) => console.error('[MapComponent] 載入政權清單失敗', err),
    });
  }

  /** 點擊地圖——判斷點到哪個政權的疆域（任務 3.7），沒點到任何疆域（點在背景/海）視為
      取消聚焦。用 `queryRenderedFeatures()` 查點擊當下畫面上實際渲染出的圖形，不是
      自己重新算一次點是否落在某個 GeoJSON polygon 裡——MapLibre 本來就有這個能力，
      不需要另外引入幾何運算。`territories-fill` 圖層在第一次疆域資料回來前不存在，
      查詢不存在的圖層 MapLibre 會直接拋例外，所以要先確認圖層存在。 */
  private handleMapClick(e: MapMouseEvent): void {
    if (!this.map || !this.map.getLayer('territories-fill')) {
      return;
    }

    const clicked = this.map.queryRenderedFeatures(e.point, { layers: ['territories-fill'] });
    const regimeId = clicked[0]?.properties?.['regimeId'] as string | undefined;

    if (regimeId) {
      this.focusState.toggle(regimeId);
    } else {
      this.focusState.clear();
    }
  }

  private loadTerritories(year: number): void {
    this.http
      .get<ApiEnvelope<FeatureCollection<MultiPolygon, TerritoryFeatureProperties>>>(
        `/api/v1/territories?year=${year}`,
      )
      .subscribe({
        next: (response) => this.applyTerritories(response.data),
        // 第一版先求「資料管線走得通看得到東西」，還沒有失敗時的 UI 呈現（例如錯誤
        // 提示列）——那屬於之後才需要拍板的 loading/error 狀態設計，這裡先用
        // console.error 讓問題在開發時看得到，不是刻意省略錯誤處理。
        error: (err: unknown) => console.error('[MapComponent] 載入疆域資料失敗', err),
      });
  }

  /** 新一批疆域資料到手後的進入點——決定「直接顯示」還是「跑形變動畫」，見任務 3.6
      的說明（class 開頭的檔案級註解）。 */
  private applyTerritories(next: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>): void {
    if (!this.map) {
      return;
    }

    // 相鄰計算＋圖著色（純函式，見 core/geometry/territory-styling.ts）——這一步把
    // 色格索引寫回每個 feature.properties.colorSlot，下面的 fill-color expression
    // 直接讀這個欄位。傳入 previousColorAssignment 維持顏色穩定性。**在動畫開始前先
    // 算好、寫進 `next` 的 properties**，讓動畫全程（包含 entering/leaving 的淡入淡出
    // 幀）都用同一個目標色格，不會中途變色。
    this.previousColorAssignment = assignTerritoryColorSlots(
      next,
      TERRITORY_COLOR_SLOTS.length,
      this.previousColorAssignment,
    );

    const prefersReducedMotion =
      typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (!this.currentFeatureCollection || prefersReducedMotion) {
      // 第一次載入：沒有「上一個狀態」可以形變過去。或使用者偏好減少動態效果：尊重
      // 這個瀏覽器層級的無障礙設定，直接跳過動畫。兩種情況都直接顯示目標資料。
      this.settle(next);
      return;
    }

    const plan = buildMorphPlan(this.currentFeatureCollection, next);
    this.animateTo(plan, next);
  }

  /** 跑一輪形變動畫，從目前畫面（`plan` 已經固定住起訖兩端）補間到 `target`。 */
  private animateTo(plan: MorphPlan, target: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>): void {
    if (this.morphFrameHandle !== undefined) {
      // 拖拉桿拖得比動畫時長還快，上一輪動畫還沒播完——取消掉，不要讓兩輪動畫同時
      // 搶著 setData()。
      this.scheduler.cancelFrame(this.morphFrameHandle);
      this.morphFrameHandle = undefined;
    }

    const token = ++this.morphToken;
    const start = this.scheduler.now();

    const step = (now: number): void => {
      if (token !== this.morphToken) {
        return; // 這輪動畫已經被更新的年份取代，見上方 morphToken 的說明，直接丟棄
      }

      const rawT = (now - start) / MapComponent.MORPH_DURATION_MS;
      if (rawT >= 1) {
        this.morphFrameHandle = undefined;
        this.settle(target); // 收斂到目標年份的原始資料，不用 interpolator(1) 的插值結果——
        // 見 territory-morph.ts 的 sampleMorphPlan() 文件註解：flubber 內部會重新取樣
        // 環的點數，t=1 的輸出不會跟原始資料完全一致，直接用原始資料才不會每次拖桿都
        // 疊加一次取樣誤差。
        return;
      }

      const territoriesSource = this.map?.getSource('territories') as GeoJSONSource | undefined;
      const overlapsSource = this.map?.getSource('territory-overlaps') as GeoJSONSource | undefined;
      if (territoriesSource && overlapsSource) {
        const sampled = sampleMorphPlan(plan, easeInOutCubic(rawT));
        territoriesSource.setData(sampled);
        overlapsSource.setData(this.buildOverlapFeatureCollection(sampled));
      }

      this.morphFrameHandle = this.scheduler.requestFrame(step);
    };

    this.morphFrameHandle = this.scheduler.requestFrame(step);
  }

  /** 動畫的「終點」／沒有動畫時的「直接顯示」共用路徑——第一次呼叫（source 還不存在）
      建立 source/圖層，之後單純換資料（`setData()`，不重新 `addLayer`，避免圖層被
      整個移除重建造成閃爍）。呼叫完會把 `featureCollection` 記成
      `currentFeatureCollection`，當下一次換年份的形變動畫起點。 */
  private settle(featureCollection: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>): void {
    if (!this.map) {
      return;
    }

    const overlaps = this.buildOverlapFeatureCollection(featureCollection);
    const existingSource = this.map.getSource('territories') as GeoJSONSource | undefined;
    const existingOverlapSource = this.map.getSource('territory-overlaps') as GeoJSONSource | undefined;

    if (existingSource && existingOverlapSource) {
      existingSource.setData(featureCollection);
      existingOverlapSource.setData(overlaps);
    } else {
      this.map.addSource('territories', { type: 'geojson', data: featureCollection });
      this.map.addSource('territory-overlaps', { type: 'geojson', data: overlaps });
      this.addTerritoryLayers();
    }

    this.currentFeatureCollection = featureCollection;
    this.renderLabels(featureCollection);
    this.refreshFocusOverlay();
  }

  /** 第一次渲染才會呼叫：建立四個圖層（疆域填色/邊界、重疊區底色+網底、聚焦高亮外框）。 */
  private addTerritoryLayers(): void {
    if (!this.map) {
      return;
    }

    this.map.addLayer({
      id: 'territories-fill',
      type: 'fill',
      source: 'territories',
      paint: {
        // MapLibre 的 expression 型別是遞迴 tuple union，buildColorSlotMatchExpression()
        // 回傳 unknown[] 沒辦法結構化對上，這裡轉型一次，交給 MapLibre 執行期自己驗證格式。
        'fill-color': buildColorSlotMatchExpression(TERRITORY_COLOR_SLOTS) as unknown as string,
        'fill-opacity': this.buildFillOpacityExpression(this.focusState.focusedRegimeId()) as unknown as number,
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
      paint: {
        'fill-color': disputeColor,
        // 任務 3.6：重疊區也跟著兩個來源政權疆域列裡較晚出現/較早消失的那一邊淡入
        // 淡出（見 territory-overlap.ts 的 TerritoryOverlap.opacity），不是寫死 1。
        'fill-opacity': ['coalesce', ['get', 'opacity'], 1] as unknown as number,
      },
    });

    if (!this.map.hasImage(OVERLAP_HATCH_IMAGE_ID)) {
      this.map.addImage(OVERLAP_HATCH_IMAGE_ID, this.hatchPatterns.create(disputeColor));
    }

    this.map.addLayer({
      id: 'territory-overlaps-hatch',
      type: 'fill',
      source: 'territory-overlaps',
      paint: {
        'fill-pattern': OVERLAP_HATCH_IMAGE_ID,
        'fill-opacity': ['coalesce', ['get', 'opacity'], 1] as unknown as number,
      },
    });

    // 政權聚焦模式的高亮外框（任務 3.7）——疊在所有圖層最上層（後加的圖層畫在上面），
    // 這樣即使聚焦的政權剛好落在爭議重疊區底下，外框依然清楚可見。一開始沒有聚焦任何
    // 政權，filter 給一個不會比對到任何 regimeId 的值（空字串），`refreshFocusOverlay()`
    // 會在聚焦目標改變時用 `setFilter()` 更新。
    const focusRingColor =
      getComputedStyle(document.documentElement).getPropertyValue('--wl-focus-ring').trim() || '#3d6fd1';
    this.map.addLayer({
      id: 'territories-focus-outline',
      type: 'line',
      source: 'territories',
      filter: ['==', ['get', 'regimeId'], ''],
      paint: { 'line-color': focusRingColor, 'line-width': 3 },
    });
  }

  /** 疊出 `fill-opacity` expression：沒有聚焦任何政權時維持原本固定不透明度；有聚焦時
      聚焦中的政權維持不透明、其餘政權大幅降低透明度（「聚光燈」效果，任務 3.7）。兩種
      情況都跟形變動畫的 `morphOpacity`（見 territory-morph.ts）相乘組合，不是互斥的
      兩條路——拖拉桿拖動時即使正在播放形變動畫，聚焦高亮也該繼續生效。 */
  private buildFillOpacityExpression(focusedRegimeId: string | null): unknown[] {
    const morphAdjustedOpacity = ['coalesce', ['get', 'morphOpacity'], 1];
    if (!focusedRegimeId) {
      return ['*', 0.85, morphAdjustedOpacity];
    }
    return [
      'case',
      ['==', ['get', 'regimeId'], focusedRegimeId],
      ['*', 0.9, morphAdjustedOpacity],
      ['*', 0.2, morphAdjustedOpacity],
    ];
  }

  /** 聚焦目標改變、或疆域資料重新定案（換年份）時都要呼叫：更新高亮圖層的 paint/filter，
      並重算周邊政權清單寫回 `RegimeFocusState`（任務 3.7）。 */
  private refreshFocusOverlay(): void {
    if (!this.map || !this.map.getLayer('territories-fill')) {
      return; // 圖層還沒建立（疆域資料還沒回來第一次）——沒有東西可以更新
    }

    const focusedRegimeId = this.focusState.focusedRegimeId();
    this.map.setPaintProperty(
      'territories-fill',
      'fill-opacity',
      this.buildFillOpacityExpression(focusedRegimeId) as unknown as number,
    );
    this.map.setFilter('territories-focus-outline', ['==', ['get', 'regimeId'], focusedRegimeId ?? '']);

    if (focusedRegimeId && this.currentFeatureCollection) {
      const neighbors = findNeighboringRegimeIds(this.currentFeatureCollection, focusedRegimeId);
      this.focusState.setNeighbors([...neighbors]);

      const others = findOtherContemporaryRegimeIds(this.currentFeatureCollection, focusedRegimeId, neighbors);
      this.focusState.setOtherContemporaryRegimes([...others]);
    }
  }

  /** 疆域重疊區（見 territory-overlap.ts）——不依賴任何手動標記的旗標，即時算幾何交集，
      只算「不同政權」之間的重疊（同一個政權自己底下多筆疆域記錄互相重疊，不算「政權
      重疊」，一律用顏色表示），所以要傳 regimeId，不能只傳 id。`morphOpacity`／
      `morphRole` 是選填屬性（只有動畫過場中的取樣結果才有），一般資料沒有這兩個欄位，
      `computeTerritoryOverlaps` 內部會分別當作 1／matched 處理。 */
  private buildOverlapFeatureCollection(
    featureCollection: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>,
  ): FeatureCollection<Polygon | MultiPolygon, Pick<TerritoryOverlap, 'opacity'>> {
    return {
      type: 'FeatureCollection',
      features: computeTerritoryOverlaps(
        featureCollection.features.map((f) => {
          const morphed = f.properties as Partial<MorphedFeatureProperties>;
          return {
            id: f.properties.id,
            regimeId: f.properties.regimeId,
            geometry: f.geometry,
            morphOpacity: morphed.morphOpacity,
            morphRole: morphed.morphRole,
          };
        }),
      ).map((overlap) => ({
        type: 'Feature',
        properties: { opacity: overlap.opacity },
        geometry: overlap.geometry,
      })),
    };
  }

  /** 政權名稱標籤——刻意用 `Marker` 掛 HTML 元素，不是 MapLibre 原生 symbol 圖層的
      `text-field`，理由見 territory-labels.ts 開頭說明（避免另外接字型 glyphs 服務）。
      **任務 3.8（Story 3）追加命名視角**：`NamingViewpointState.observerRegimeId()`
      為 `null`（全球客觀視角，AC#1）時一律顯示自稱名稱；非 `null`（聚焦某政權視角，
      AC#2）時改查 `RegimeAliasDirectoryService.aliasFor()`，查得到代稱才換成代稱顯示，
      查無資料 fallback 回自稱名稱（跟翻譯 fallback 同一個原則，不是資料缺陷）。 */
  private renderLabels(featureCollection: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>): void {
    if (!this.map) {
      return;
    }

    this.clearLabelMarkers();

    const labelPoints = computeTerritoryLabelPoints(featureCollection);
    const observerId = this.namingViewpoint.observerRegimeId();

    for (const [regimeId, [lon, lat]] of labelPoints) {
      const selfName = this.regimeDirectory.nameOf(regimeId);
      if (!selfName) {
        continue; // 查無名稱（理論上不該發生，territories/regimes 資料不一致才會走到這裡）
      }

      const alias = observerId ? this.aliasDirectory.aliasFor(regimeId, observerId) : undefined;

      const el = document.createElement('div');
      el.textContent = alias?.aliasName ?? selfName;

      if (alias) {
        // AC#2「點擊/hover 後可追溯回自稱本體」：hover 用原生 title 屬性顯示自稱名稱
        // （不用自己刻一個 tooltip UI，瀏覽器原生支援）；click 直接重用任務 3.7 既有的
        // 聚焦機制（跟點擊底下的疆域本身效果相同）——政權聚焦面板的標題本來就顯示
        // `RegimeDirectoryService.nameOf()` 算出的真正自稱名稱，不用為了這個 AC 另外
        // 做一個顯示自稱的 UI。`.territory-label` 預設 `pointer-events: none`（見
        // map-labels.global.scss，避免標籤擋住底下地圖的拖曳/縮放手勢），只有顯示代稱
        // 的這個分支才加 `.territory-label-clickable` 打開 pointer-events，不影響
        // 其餘（多數情況）標籤維持純裝飾、不可互動。
        el.className = 'territory-label territory-label-clickable';
        el.title = `自稱：${selfName}`;
        el.addEventListener('click', (e) => {
          e.stopPropagation(); // 避免同時被底下地圖的 'click' handler 當成點擊背景重複處理
          this.focusState.toggle(regimeId);
        });
      } else {
        el.className = 'territory-label';
      }

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
    if (this.morphFrameHandle !== undefined) {
      this.scheduler.cancelFrame(this.morphFrameHandle);
    }
    this.clearLabelMarkers();
    this.map?.remove();
  }
}
