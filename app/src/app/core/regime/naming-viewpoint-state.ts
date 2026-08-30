import { Injectable, signal } from '@angular/core';

/**
 * 任務 3.8（Story 3「觀察視角切換與名稱可追溯性」）：目前選擇的「命名視角」。
 *
 * `null`＝「全球客觀視角」（AC#1：地圖標籤一律顯示各政權自稱名稱）；非 `null` 時代表
 * 「聚焦於某個政權的觀察視角」（AC#2：其他政權的標籤改顯示這個政權視角下的代稱——
 * 查無代稱時 fallback 回自稱名稱，跟翻譯 fallback 同一個原則，不是資料缺陷）。
 *
 * **刻意跟 `RegimeFocusState`（任務 3.7）分開，不是同一個狀態**：3.7 的「聚焦」是
 * 點擊疆域→高亮該政權＋顯示它的周邊政權/互動資訊面板，一次只服務「使用者現在關注
 * 哪個政權」；這裡的「視角」是全域性地改變地圖上*所有*政權標籤怎麼命名，服務的是
 * 完全不同的問題（「這些名稱是誰取的」）。兩者剛好都可能被指派同一個政權 id，觸發的
 * UI 也不同（一個是點擊疆域，一個是下拉選單，見 `naming-viewpoint-selector/`），硬共用
 * 同一個 signal 會讓兩件事的意圖糾纏在一起，之後任一邊要獨立演進都綁手綁腳。
 */
@Injectable({ providedIn: 'root' })
export class NamingViewpointState {
  readonly observerRegimeId = signal<string | null>(null);

  setObserver(regimeId: string | null): void {
    this.observerRegimeId.set(regimeId);
  }
}
