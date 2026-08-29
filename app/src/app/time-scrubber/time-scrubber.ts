import { Component, inject } from '@angular/core';
import { TimelineState } from '../core/time/timeline-state';

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
 */
@Component({
  selector: 'app-time-scrubber',
  standalone: true,
  templateUrl: './time-scrubber.html',
  styleUrl: './time-scrubber.scss',
})
export class TimeScrubberComponent {
  protected readonly timeline = inject(TimelineState);
  protected readonly minYear = TimelineState.MIN_YEAR;
  protected readonly maxYear = TimelineState.MAX_YEAR;

  protected onInput(event: Event): void {
    const value = Number((event.target as HTMLInputElement).value);
    this.timeline.year.set(value);
  }
}
