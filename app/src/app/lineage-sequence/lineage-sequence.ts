import { Component, inject } from '@angular/core';
import { DefaultLineageService } from '../core/regime/default-lineage.service';
import { TagComponent } from '../components/ui/tag';

/**
 * 任務 3.9（Story 4 AC#3）：「使用者未指定特定史觀時，依 `lineage_presets` 中的預設
 * preset 顯示主線」。這個元件本身**只讀** `DefaultLineageService`（跟
 * `RegimeFocusPanelComponent` 只讀 `RegimeFocusState` 同一個分工原則），第一次渲染時
 * 觸發載入——目前應用只有一份預設主線，不隨時間拉桿/聚焦狀態變動，所以不像
 * `RegimeFocusState` 需要訂閱年份變化重新查詢，`ensureLoaded()` 呼叫一次就夠。
 *
 * **只呈現「傳統教科書史觀」這一條預設序列，不是所有 preset 的選擇器**——AC#3 原文只
 * 要求「使用者未指定特定史觀時」顯示預設主線，沒有要求提供切換史觀的 UI；蜀漢/東吳
 * 等分裂期政權仍可在地圖上點擊聚焦查看（`RegimeFocusPanelComponent`），只是不會出現
 * 在這條主線序列裡——這是 PRD §6「方案 D」本來就拍板的設計（主線跟客觀政權資料是兩回
 * 事），不是這個元件遺漏了什麼。**切換史觀的 UI 目前不在範圍內**，留給之後真的有多份
 * preset 需要切換時再設計。
 *
 * 序列用箭頭串接的 `sanring-tag` 呈現，跟 `RegimeFocusPanelComponent` 的周邊政權清單
 * 同一套視覺語言（固定 `outline` variant，不套用任務 3.9 AC#2 那種依狀態變色的
 * `regime-transition-display.ts`——這裡是「主線序列本身」，不是在描述某一個政權的
 * 起源/終止狀態，用途不同，不強行共用）。
 */
@Component({
  selector: 'app-lineage-sequence',
  standalone: true,
  imports: [TagComponent],
  templateUrl: './lineage-sequence.html',
  styleUrl: './lineage-sequence.scss',
})
export class LineageSequenceComponent {
  private readonly lineage = inject(DefaultLineageService);

  protected readonly presetName = this.lineage.presetName;
  protected readonly sequence = this.lineage.sequence;

  constructor() {
    this.lineage.ensureLoaded().subscribe({
      error: (err: unknown) => console.error('[LineageSequenceComponent] 載入預設主線序列失敗', err),
    });
  }
}
