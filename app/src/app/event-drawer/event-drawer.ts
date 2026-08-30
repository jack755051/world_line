import { Component, computed, inject, signal } from '@angular/core';
import { toObservable } from '@angular/core/rxjs-interop';
import { HttpClient } from '@angular/common/http';
import { EventDrawerState } from '../core/event/event-drawer-state';
import { SANRING_COLLAPSIBLE_IMPORTS } from '../components/ui/collapsible';
import { EdtfDateComponent } from '../edtf-date/edtf-date';

/** `ApiResponse<T>` 的最小形狀，同專案內其他直接打 API 的元件（`map.ts`/
    `time-scrubber.ts`）的 `ApiEnvelope<T>`。 */
interface ApiEnvelope<T> {
  data: T;
}

/**
 * `historical_events.sections` 的實際內容形狀（見 `api/Data/SeedData.cs` 種子資料、
 * notes §八「手風琴三層內容」）。**注意這裡是 snake_case，不是 camelCase**——跟這個
 * API 其他欄位不同，`sections` 是後端原封不動轉傳資料庫存的 jsonb 原始內容（見
 * `EventsController` 類別文件：「回應時解析回真正的巢狀 JsonElement」），不經過
 * ASP.NET 的屬性序列化器改鍵名，前端要對到資料庫種子資料實際寫的鍵名。**這個形狀
 * 目前沒有正式 schema 約束**（task 2.10 完成時明確記錄：`sections` 的結構化 schema
 * 留待真的需要時再拍板），三個欄位都當作可能不存在處理，不假設一定齊全。
 */
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

type LoadState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'success'; event: HistoricalEventDetail };

/**
 * 任務 3.12（事件詳情抽屜，notes §八）：由 `RegimeFocusPanelComponent` 的「互動記錄」
 * 清單點擊某個事件觸發，讀 `EventDrawerState.openEventId`，打 task 2.10 既有的
 * `GET /api/v1/events/:id` 取得完整事件詳情（含 `sections`）。
 *
 * **視覺**：notes §八原文給的毛玻璃規格（`backdrop-filter: blur(16px);
 * background: rgba(20,20,25,0.75); border: 1px solid rgba(255,255,255,0.1);`）
 * 直接照搬——**這是固定深色玻璃卡片，不跟著 `--wl-*` 淺色主題 token 走**：這個專案
 * 目前沒有深色模式（`design-tokens.scss` 開頭就說明刻意不做這個分支），玻璃卡片疊在
 * 地圖上是獨立於整體淺色介面主題之外的視覺元素（類似地圖類產品常見的深色浮層卡片），
 * 不是要讓整個 App 變深色，所以卡片內文字顏色也是獨立寫死的白色系，不借用
 * `--wl-ink-*`（那些是校過對淺色 `--wl-surface` 的對比度，套在深色玻璃背景上不成立）。
 *
 * **三層手風琴沿用既有的 `sanring-collapsible`**（跟 `RegimeFocusPanelComponent` 同一
 * 個元件），不是嚴格互斥的「同時只能開一個」傳統 accordion——三層預設都展開，使用者
 * 各自收合，跟這個專案既有的 Collapsible 使用慣例一致，不為了這個任務另外導入新的
 * accordion 元件。
 *
 * **刻意不做「點擊關鍵轉折時間點→地圖 flyTo+時間軸連動」**（notes §八原文互動草圖的
 * 一部分）：`turning_points` 目前的 schema 就是純文字陣列（見種子資料），沒有座標/
 * 年份這些結構化欄位可以驅動地圖鏡頭移動或時間拉桿定位，要做這個互動得先擴充
 * `historical_events` schema（例如每個轉折點自己的 point geometry + decimal year），
 * 這個任務範圍不含 schema 變更，先把三層內容呈現出來，flyTo 互動留到真的有資料支撐
 * 時再做，不用假座標/假年份湊出一個看起來能動、實際亂跳的互動。
 *
 * **事件無 `sections` 時的 empty state**（PRD §12「M3 前必須處理」原本待拍板的問題，
 * 這裡拍板）：目前種子資料 7 筆事件裡有 5 筆（漢禪魏、蜀漢滅亡、魏禪晉、吳滅亡、阿拔斯
 * 革命）沒有 `sections`——這些是政權轉換的骨幹記錄，本來就沒有詳細敘事内容，不是資料
 * 缺陷。顯示「這個事件目前只有基本記錄（名稱與時間），還沒有詳細內容」，不是空白一片
 * 也不是報錯，跟翻譯/代稱 fallback 同一個「沒有資料不等於錯誤狀態」的原則。
 */
@Component({
  selector: 'app-event-drawer',
  standalone: true,
  imports: [SANRING_COLLAPSIBLE_IMPORTS, EdtfDateComponent],
  templateUrl: './event-drawer.html',
  styleUrl: './event-drawer.scss',
})
export class EventDrawerComponent {
  private readonly drawerState = inject(EventDrawerState);
  private readonly http = inject(HttpClient);

  protected readonly openEventId = this.drawerState.openEventId;

  private readonly loadState = signal<LoadState | null>(null);

  protected readonly event = computed(() => {
    const state = this.loadState();
    return state?.status === 'success' ? state.event : null;
  });

  protected readonly isLoading = computed(() => this.loadState()?.status === 'loading');
  protected readonly hasError = computed(() => this.loadState()?.status === 'error');

  constructor() {
    // 開關抽屜是離散的使用者點擊動作，不像拉桿拖動會連續觸發，不需要 debounce。
    toObservable(this.openEventId).subscribe((id) => {
      if (id === null) {
        this.loadState.set(null);
        return;
      }
      this.loadEvent(id);
    });
  }

  protected close(): void {
    this.drawerState.close();
  }

  private loadEvent(id: string): void {
    this.loadState.set({ status: 'loading' });
    this.http.get<ApiEnvelope<HistoricalEventDetail>>(`/api/v1/events/${id}`).subscribe({
      next: (response) => this.loadState.set({ status: 'success', event: response.data }),
      error: (err: unknown) => {
        console.error('[EventDrawerComponent] 載入事件詳情失敗', err);
        this.loadState.set({ status: 'error' });
      },
    });
  }
}
