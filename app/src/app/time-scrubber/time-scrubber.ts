import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toObservable } from '@angular/core/rxjs-interop';
import { HttpClient } from '@angular/common/http';
import { debounceTime } from 'rxjs';
import { TimelineState } from '../core/time/timeline-state';
import { RegimeFocusState } from '../core/regime/regime-focus-state';
import { RegimeDirectoryService } from '../core/regime/regime-directory.service';

/** `GET /api/v1/reign-eras?year=` 回應的形狀（見 `api/Contracts/ReignEraResponse.cs`）。
    不支援 `?locale=`——`reign_eras` 不在雙語內容範圍內（task 2.16 拍板），`eraName`
    只有單一語言可顯示。 */
interface ReignEraSummary {
  id: string;
  regimeId: string;
  eraName: string;
  startYear: number;
  endYear: number | null;
}

/** `ApiResponse<T>` 的最小形狀，同 `map.ts` 的 `ApiEnvelope<T>`——這裡只取得到的
    `data` 欄位，不整個對照完整契約。 */
interface ApiEnvelope<T> {
  data: T;
}

/**
 * 時間軸 Scrubber 主軸（任務 3.3，憲法 §9「非離散跳轉」）。用原生
 * `<input type="range">`——瀏覽器原生支援真正連續拖動（不會卡固定格），鍵盤也能操作
 * （方向鍵微調），不需要自己刻一套拖曳手勢邏輯。**副軸（月/日展開，任務 3.4）刻意不在
 * 這裡做**：3.4 的用途是「聚焦近代事件時下方展開精細軸」，但事件資料（`historical_events`,
 * task 2.10+）根本還沒做，沒有東西可以展開，先不做無資料可展示的 UI。
 *
 * 拖動只更新 `TimelineState.year` 這個 signal 本身——實際觸發地圖重新查詢/渲染的
 * debounce 邏輯在 `MapComponent`（見 map.ts），不是這裡的責任：這個元件只管「使用者
 * 拖到哪一年」，不管「拖動後要做什麼」，保持職責單一。
 *
 * **任務 3.7 AC#2（2026-08-30）**：聚焦某個政權時，軌道上疊一條半透明色帶標示該政權
 * 的存續年份範圍（`RegimeFocusState.lifetimeRange`）。**刻意不客製原生 `<input
 * type=range>` 的 `::-webkit-slider-runnable-track`/`::-moz-range-track` 偽元素**
 * 去畫這個範圍——那兩個偽元素在不同瀏覽器引擎是分開的 API，沒辦法共用同一組樣式，
 * 而且會打架現有的 `accent-color` 簡化方案（見下方 `.time-scrubber-input` 的既有說明：
 * 先求功能正確跟基本一致的視覺，之後真的需要更精緻的外觀再客製）。改成在 input 底下疊
 * 一層獨立的裝飾用 `<div>`（`pointer-events: none`，不擋拖動手感），用百分比定位——
 * 跨瀏覽器行為一致，不用碰偽元素。超出存續區間的警示文字顯示在
 * `RegimeFocusPanelComponent`（見該元件的 `outOfLifetimeWarning`），不重複做在這裡。
 */
@Component({
  selector: 'app-time-scrubber',
  standalone: true,
  templateUrl: './time-scrubber.html',
  styleUrl: './time-scrubber.scss',
})
export class TimeScrubberComponent {
  protected readonly timeline = inject(TimelineState);
  private readonly focusState = inject(RegimeFocusState);
  private readonly http = inject(HttpClient);
  private readonly destroyRef = inject(DestroyRef);
  private readonly regimeDirectory = inject(RegimeDirectoryService);
  protected readonly minYear = TimelineState.MIN_YEAR;
  protected readonly maxYear = TimelineState.MAX_YEAR;

  private readonly activeEras = signal<readonly ReignEraSummary[]>([]);

  constructor() {
    // 政權名稱目錄可能已被 MapComponent 載入過（`shareReplay(1)` 快取，見該
    // service 的類別說明），這裡再呼叫一次不會重複打 API。
    this.regimeDirectory.ensureLoaded().subscribe();

    // 同 `MapComponent.loadTerritories()` 的 debounce 節奏——拖拉桿時每個中間值
    // 都打一次 API 沒有必要，跟疆域查詢共用同一套節流間隔（150ms）。
    toObservable(this.timeline.year)
      .pipe(debounceTime(150), takeUntilDestroyed(this.destroyRef))
      .subscribe((year) => this.loadReignEras(year));
  }

  /** 目前拉桿年份對應的年號標籤，格式「{政權名} {年號}{元年｜N年}」——多個政權可能
      在同一年各自有年號在使用中（例如三國時期），逐一列出並標政權名稱區分，不是
      只顯示年號本身（單看「建興」不知道是哪個政權的年號）。查無年號資料（seed 尚
      未涵蓋的年份）時回傳空陣列，模板端不顯示這個區塊。 */
  protected readonly eraLabels = computed<readonly string[]>(() => {
    const year = this.timeline.year();
    return this.activeEras().map((era) => {
      const regimeName = this.regimeDirectory.nameOf(era.regimeId) ?? era.regimeId;
      const yearInEra = year - era.startYear + 1;
      const yearLabel = yearInEra === 1 ? '元年' : `${yearInEra}年`;
      return `${regimeName} ${era.eraName}${yearLabel}`;
    });
  });

  protected readonly lifetimeBand = computed<{ left: string; width: string } | null>(() => {
    const range = this.focusState.lifetimeRange();
    if (!range) {
      return null;
    }
    const totalSpan = this.maxYear - this.minYear;
    // 存續區間可能超出拉桿本身的範圍（例如政權建立在拉桿下限之前），夾在拉桿範圍內，
    // 不然算出來的 left/width 百分比會跑到 0-100% 以外，視覺上溢出軌道。
    const clampedStart = Math.max(range.minYear, this.minYear);
    const clampedEnd = Math.min(range.maxYear, this.maxYear);
    const leftPercent = ((clampedStart - this.minYear) / totalSpan) * 100;
    const widthPercent = Math.max(((clampedEnd - clampedStart) / totalSpan) * 100, 0);
    return { left: `${leftPercent}%`, width: `${widthPercent}%` };
  });

  protected onInput(event: Event): void {
    const value = Number((event.target as HTMLInputElement).value);
    this.timeline.year.set(value);
  }

  private loadReignEras(year: number): void {
    this.http.get<ApiEnvelope<ReignEraSummary[]>>(`/api/v1/reign-eras?year=${year}`).subscribe({
      next: (response) => this.activeEras.set(response.data),
      // 同 `MapComponent.loadTerritories()`：第一版先求資料管線走得通，還沒有
      // loading/error 狀態的 UI 呈現，用 console.error 讓問題在開發時看得到。
      error: (err: unknown) => console.error('[TimeScrubberComponent] 載入年號資料失敗', err),
    });
  }
}
