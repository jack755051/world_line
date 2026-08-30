import { Component, computed, inject, signal } from '@angular/core';
import { toObservable } from '@angular/core/rxjs-interop';
import { HttpClient } from '@angular/common/http';
import { RegimeFocusState } from '../core/regime/regime-focus-state';
import { RegimeDirectoryService } from '../core/regime/regime-directory.service';
import { TimelineState } from '../core/time/timeline-state';
import { EdtfDateComponent } from '../edtf-date/edtf-date';

/** `ApiResponse<T>` 的最小形狀，同專案內其他直接打 API 的元件（`map.ts`/
    `time-scrubber.ts`/原本的 `event-drawer.ts`）的 `ApiEnvelope<T>`。 */
interface ApiEnvelope<T> {
  data: T;
}

/** `GET /api/v1/regimes/:id/events`（不帶 `year`）回應的一列——見
    `api/Contracts/RegimeEventInteractionResponse.cs`。同一個事件可能因為跟多個
    政權都有互動而在清單裡出現多次（`otherRegimeId` 不同），這裡只取得到
    `dedupeAndSortEvents()` 需要的欄位。 */
interface EventInteractionRow {
  eventId: string;
  eventName: string;
  startEdtf: string;
  endEdtf: string;
  startDecimal: number;
}

/** 這個元件實際要顯示的清單項目形狀——已經去重（同一個事件只出現一次，不分是跟哪個
    政權互動）、依 `startDecimal` 排序過。 */
interface RegimeEventSummary {
  id: string;
  name: string;
  startEdtf: string;
  endEdtf: string;
  startDecimal: number;
}

/** `historical_events.sections` 的實際內容形狀——**注意是 snake_case**，見原本
    `event-drawer.ts` 的說明：後端原封不動轉傳資料庫 jsonb 內容，不經過 ASP.NET
    屬性序列化器改鍵名。 */
interface HistoricalEventSections {
  background?: string;
  turning_points?: string[];
  impact?: string;
}

interface HistoricalEventDetail {
  id: string;
  name: string;
  startEdtf: string;
  endEdtf: string;
  sections: HistoricalEventSections | null;
}

type DetailState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'success'; event: HistoricalEventDetail };

/** 同一個事件可能因為跟多個政權互動而在原始回應裡重複出現——這個面板現在呈現的是
    「這個政權的事件史」，不是「這個政權跟誰互動」，一個事件只顯示一次，取第一次出現
    的那筆（`eventName`/`startEdtf`/`endEdtf`/`startDecimal` 對同一個 `eventId` 應該
    都一致，不會因為對到不同的 `otherRegimeId` 而有落差）。依 `startDecimal` 由舊到
    新排序，符合「依發生時間順序排列」的需求。 */
function dedupeAndSortEvents(rows: readonly EventInteractionRow[]): RegimeEventSummary[] {
  const byId = new Map<string, RegimeEventSummary>();
  for (const row of rows) {
    if (!byId.has(row.eventId)) {
      byId.set(row.eventId, {
        id: row.eventId,
        name: row.eventName,
        startEdtf: row.startEdtf,
        endEdtf: row.endEdtf,
        startDecimal: row.startDecimal,
      });
    }
  }
  return [...byId.values()].sort((a, b) => a.startDecimal - b.startDecimal);
}

/**
 * 政權事件記錄的地圖疊加面板（2026-08-31，使用者提案，見類別文件歷史：先是「把互動
 * 清單搬到地圖 overlay」，使用者實機測試後進一步提出這個更完整的規格）——`MapComponent`
 * 用 `ViewContainerRef.createComponent()` 動態建立、掛 MapLibre `Marker` 疊在聚焦
 * 政權疆域上方，見 `map.ts` 的 `updateEventPanelMarker()`。
 *
 * **抬頭 + 手風琴列表結構**：抬頭顯示政權名稱（不是固定文字「互動記錄」）；內容是這個
 * 政權的事件手風琴——每筆事件的標題是「{{年度}}年 {{事件名稱}}」，點標題展開/收合，
 * 展開時**直接在原地顯示事件詳情**（背景起因/關鍵轉折時間點/歷史影響），不是另外跳出
 * 一個獨立的抽屜——這取代了原本 task 3.12 的 `EventDrawerComponent`（已移除，見該次
 * commit 的說明），避免同一件事「顯示事件詳情」有兩條互相獨立的 UI 路徑。
 *
 * **不拘泥於目前拉桿年份**：改打 `GET /api/v1/regimes/:id/events`（不帶 `year`，
 * task 3.12 後續調整讓這個參數變選填），拿到這個政權「全部已知事件」，依 `startDecimal`
 * 由舊到新排序，預設只顯示前 5 筆（`MAX_DISPLAYED_EVENTS`，這個規模的資料量下先簡單
 * 用固定上限，沒有「顯示更多」的分頁 UI——真的有需要（未來事件資料量大到 5 筆不夠用）
 * 再回頭加）。**只在聚焦政權改變時查一次，不會跟著拉桿換年份重新查**——這是跟先前
 * `RegimeFocusState` 版本最大的行為差異：既然清單本身不受年份限制，年份改變自然不需要
 * 觸發重新查詢，也因此不再需要 `RegimeFocusState` 那套「聚焦目標 × 年份」的 debounce
 * 訂閱跟競態 token（見 `regime-focus-state.ts` 的說明，這段邏輯已經整個移除）。
 *
 * **點擊展開事件時，時間拉桿同步跳到那個事件的年份**（`Math.floor(startDecimal)`）——
 * 使用者原文「打開206年的事件，外部時間也要跳到206」；收合事件不會把時間拉桿跳回去，
 * 維持使用者最後一次操作的狀態，不做自動復原。
 *
 * **事件詳情用 `Map` 做記憶體內快取，不是响應式 signal**：同一時間只會有一個事件展開
 * （手風琴互斥），只有「目前展開的那一個」需要響應式呈現，用一個 `expandedDetail`
 * signal 就夠；快取本身是給「使用者收合又重新展開同一筆」這種情境用，避免重複打 API，
 * 不需要讓快取本身也是響應式的。
 *
 * **持續性關係（`regime_relations`，例如「同盟」）這次改版刻意整個拿掉，不再顯示**
 * （使用者確認）——關係沒有單一「年度」（是一段存續區間），套不進「年度+事件名稱」這種
 * 手風琴標題格式，跟這次「事件史」的呈現邏輯不是同一種資料形狀，混在一起會讓手風琴標題
 * 格式不一致。
 */
@Component({
  selector: 'app-regime-event-panel',
  standalone: true,
  imports: [EdtfDateComponent],
  templateUrl: './regime-event-panel.html',
  styleUrl: './regime-event-panel.scss',
})
export class RegimeEventPanelComponent {
  private static readonly MAX_DISPLAYED_EVENTS = 5;

  private readonly focusState = inject(RegimeFocusState);
  private readonly directory = inject(RegimeDirectoryService);
  private readonly timeline = inject(TimelineState);
  private readonly http = inject(HttpClient);

  protected readonly focusedRegimeId = this.focusState.focusedRegimeId;

  protected readonly focusedRegimeName = computed(() => {
    const id = this.focusedRegimeId();
    return id ? (this.directory.nameOf(id) ?? id) : null;
  });

  private readonly allEvents = signal<readonly RegimeEventSummary[]>([]);
  protected readonly displayedEvents = computed(() =>
    this.allEvents().slice(0, RegimeEventPanelComponent.MAX_DISPLAYED_EVENTS),
  );

  protected readonly expandedEventId = signal<string | null>(null);
  private readonly expandedDetail = signal<DetailState | null>(null);
  /** 已經成功查過的事件詳情快取——見類別文件「記憶體內快取」說明。 */
  private readonly detailCache = new Map<string, HistoricalEventDetail>();

  protected readonly isExpandedLoading = computed(() => this.expandedDetail()?.status === 'loading');
  protected readonly isExpandedError = computed(() => this.expandedDetail()?.status === 'error');
  protected readonly expandedEventDetail = computed(() => {
    const state = this.expandedDetail();
    return state?.status === 'success' ? state.event : null;
  });

  constructor() {
    toObservable(this.focusedRegimeId).subscribe((id) => {
      this.expandedEventId.set(null);
      this.expandedDetail.set(null);
      this.detailCache.clear();
      if (!id) {
        this.allEvents.set([]);
        return;
      }
      this.loadEvents(id);
    });
  }

  protected yearLabel(startDecimal: number): number {
    return Math.floor(startDecimal);
  }

  /** 點擊手風琴標題——已展開的再點一次收合，否則展開並跳時間拉桿到這個事件的年份、
      視需要（沒快取過）打 API 查詳情。 */
  protected toggleEvent(event: RegimeEventSummary): void {
    if (this.expandedEventId() === event.id) {
      this.expandedEventId.set(null);
      this.expandedDetail.set(null);
      return;
    }

    this.expandedEventId.set(event.id);
    this.timeline.year.set(this.yearLabel(event.startDecimal));

    const cached = this.detailCache.get(event.id);
    if (cached) {
      this.expandedDetail.set({ status: 'success', event: cached });
      return;
    }

    this.expandedDetail.set({ status: 'loading' });
    this.http.get<ApiEnvelope<HistoricalEventDetail>>(`/api/v1/events/${event.id}`).subscribe({
      next: (response) => {
        this.detailCache.set(event.id, response.data);
        // 使用者可能在請求還沒回來前就收合、或展開了別的事件——只套用還對得上目前
        // 展開目標的回應，避免過期請求蓋掉使用者已經在看的內容。
        if (this.expandedEventId() === event.id) {
          this.expandedDetail.set({ status: 'success', event: response.data });
        }
      },
      error: (err: unknown) => {
        console.error('[RegimeEventPanelComponent] 載入事件詳情失敗', err);
        if (this.expandedEventId() === event.id) {
          this.expandedDetail.set({ status: 'error' });
        }
      },
    });
  }

  private loadEvents(regimeId: string): void {
    this.http.get<ApiEnvelope<EventInteractionRow[]>>(`/api/v1/regimes/${regimeId}/events`).subscribe({
      next: (response) => {
        // 使用者可能已經切換到別的政權——只套用還對得上目前聚焦目標的回應。
        if (this.focusedRegimeId() !== regimeId) {
          return;
        }
        this.allEvents.set(dedupeAndSortEvents(response.data));
      },
      error: (err: unknown) => console.error('[RegimeEventPanelComponent] 載入政權事件清單失敗', err),
    });
  }
}
