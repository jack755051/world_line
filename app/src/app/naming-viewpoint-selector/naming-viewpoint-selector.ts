import { Component, computed, inject } from '@angular/core';
import { RegimeDirectoryService } from '../core/regime/regime-directory.service';
import { NamingViewpointState } from '../core/regime/naming-viewpoint-state';

/**
 * 任務 3.8（Story 3 AC#1/AC#2）：命名視角切換下拉選單——「全球客觀視角」（預設，AC#1
 * 一律自稱）或「以某政權的視角」（AC#2，其他政權標籤改顯示該視角下的代稱）。這個元件
 * 只負責寫入 `NamingViewpointState`，實際套用代稱、決定要顯示什麼名稱是 `MapComponent`
 * 的事（跟 `TimeScrubberComponent`「只管拉到哪一年，不管拉動後要做什麼」同一個職責
 * 單一原則）。
 *
 * **選單列出全部政權，不是只列有代稱資料的政權**：「任何政權都可以是觀察者」這個概念
 * 本身成立，跟「這個觀察者目前有沒有留下代稱記錄」是兩回事——選了一個目前沒有代稱資料
 * 的觀察視角，地圖標籤就會全部 fallback 回自稱名稱（`MapComponent`/
 * `RegimeAliasDirectoryService` 的 fallback 邏輯），不是錯誤狀態，跟翻譯 fallback
 * 同一個原則，不需要在選單裡先篩掉「還沒有代稱資料的政權」。
 */
@Component({
  selector: 'app-naming-viewpoint-selector',
  standalone: true,
  templateUrl: './naming-viewpoint-selector.html',
  styleUrl: './naming-viewpoint-selector.scss',
})
export class NamingViewpointSelectorComponent {
  private readonly directory = inject(RegimeDirectoryService);
  private readonly viewpoint = inject(NamingViewpointState);

  protected readonly currentObserverId = this.viewpoint.observerRegimeId;

  protected readonly regimes = computed(() =>
    [...this.directory.all()].sort((a, b) => a.selfName.localeCompare(b.selfName, 'zh-Hant')),
  );

  constructor() {
    // 跟 LineageSequenceComponent 同一個理由：這個元件可能在 MapComponent 觸發
    // RegimeDirectoryService.ensureLoaded() 之前就先渲染，idempotent 呼叫確保選單
    // 選項不用等地圖初始化完成才有東西可選。
    this.directory.ensureLoaded().subscribe({
      error: (err: unknown) => console.error('[NamingViewpointSelectorComponent] 載入政權清單失敗', err),
    });
  }

  protected onChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.viewpoint.setObserver(value === '' ? null : value);
  }
}
