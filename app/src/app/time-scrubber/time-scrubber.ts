import { Component, computed, inject } from '@angular/core';
import { TimelineState } from '../core/time/timeline-state';
import { RegimeFocusState } from '../core/regime/regime-focus-state';

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
  protected readonly minYear = TimelineState.MIN_YEAR;
  protected readonly maxYear = TimelineState.MAX_YEAR;

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
}
