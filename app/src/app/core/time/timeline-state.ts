import { Injectable, signal } from '@angular/core';

/**
 * 全域「目前顯示年份」狀態（任務 3.3）——時間拉桿寫入，地圖（任務 3.5）跟未來其他跟
 * 時間有關的元件（事件圖層、政權聚焦模式等）讀取。用 service + signal，不是在 `App`
 * 元件裡開一個欄位、透過 `@Input()`/`@Output()` 逐層傳遞——時間拉桿跟地圖是同一層級的
 * 兄弟元件（都掛在 `App` 底下，不是父子關係），用 service 集中管理比一路傳遞乾淨，
 * 之後更多元件需要讀「目前年份」時也不用重新設計傳遞路徑。
 *
 * **拉桿範圍暫定 1-300 年，只涵蓋目前唯一有的種子資料（三國史，約西元 25-280 年）**，
 * 不是「世界史」最終該有的範圍——之後真的匯入更多時代/地區的史料，這裡要跟著擴大，
 * 甚至改成依實際資料動態計算上下限（例如加一個 `/api/v1/territories/bounds` 端點），
 * 現在沒有更多資料可以驗證那個設計，先寫死一個涵蓋現有資料的合理範圍就好。
 */
@Injectable({ providedIn: 'root' })
export class TimelineState {
  static readonly MIN_YEAR = 1;
  static readonly MAX_YEAR = 300;
  static readonly DEFAULT_YEAR = 225;

  readonly year = signal(TimelineState.DEFAULT_YEAR);
}
