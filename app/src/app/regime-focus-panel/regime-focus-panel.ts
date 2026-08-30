import { Component, computed, inject } from '@angular/core';
import { RegimeFocusState } from '../core/regime/regime-focus-state';
import { RegimeDirectoryService } from '../core/regime/regime-directory.service';
import { TimelineState } from '../core/time/timeline-state';

/**
 * 政權聚焦模式的資訊面板（任務 3.7，對應 PRD Story 2）——點擊地圖上的疆域後顯示，列出
 * 聚焦政權名稱、同時期周邊政權清單，以及存續區間警示（AC#2：拖動時間拉桿超出聚焦政權
 * 存續區間時提示「尚未建立/已不存在」）。這個元件本身**只讀** `RegimeFocusState`，
 * 不自己算高亮/相鄰關係——那些是 `MapComponent` 的責任（見 map.ts 開頭說明），職責
 * 單一，跟 `TimeScrubberComponent`「只管拖到哪一年，不管拖動後要做什麼」是同一個
 * 分工原則。
 *
 * **AC#3（互動清單，連結 `historical_events`/`regime_relations` 記錄）刻意不在這裡
 * 做**：後端對應端點（task 2.9 政權關係、2.10 事件骨幹）都還沒實作，沒有資料可以連結，
 * 跟任務 3.4（時間軸副軸）因為事件資料還沒做而刻意跳過是同一個處理原則，見
 * implementation plan 任務 3.7 的說明。
 */
@Component({
  selector: 'app-regime-focus-panel',
  standalone: true,
  templateUrl: './regime-focus-panel.html',
  styleUrl: './regime-focus-panel.scss',
})
export class RegimeFocusPanelComponent {
  private readonly focusState = inject(RegimeFocusState);
  private readonly directory = inject(RegimeDirectoryService);
  private readonly timeline = inject(TimelineState);

  protected readonly focusedRegimeId = this.focusState.focusedRegimeId;

  protected readonly focusedRegimeName = computed(() => {
    const id = this.focusedRegimeId();
    return id ? (this.directory.nameOf(id) ?? id) : null;
  });

  protected readonly neighborNames = computed(() =>
    this.focusState
      .neighborRegimeIds()
      .map((id) => this.directory.nameOf(id) ?? id)
      // 用 zh-Hant collator 排序，不是保留後端回傳/相鄰運算的原始順序——那個順序沒有
      // 對使用者有意義的語意（取決於 Set 迭代順序跟浮點座標排序細節），字母/筆畫排序
      // 至少是一個穩定、使用者看得懂的呈現方式。
      .sort((a, b) => a.localeCompare(b, 'zh-Hant')),
  );

  /** AC#2：聚焦政權若已超出（或還沒進入）存續區間要提示。`lifetimeRange` 為 `null`
      代表還在載入中或沒有聚焦政權，這時不顯示警告——避免載入過程中的暫時性 `null`
      被誤判成「超出範圍」而閃一下錯誤訊息。 */
  protected readonly outOfLifetimeWarning = computed(() => {
    const range = this.focusState.lifetimeRange();
    if (!range) {
      return null;
    }
    const year = this.timeline.year();
    if (year < range.minYear) {
      return `此政權於西元 ${year} 年尚未建立`;
    }
    if (year >= range.maxYear) {
      return `此政權於西元 ${year} 年已不存在`;
    }
    return null;
  });

  protected close(): void {
    this.focusState.clear();
  }
}
