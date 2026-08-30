import { Injectable, signal } from '@angular/core';

/**
 * 全域「目前顯示年份」狀態（任務 3.3）——時間拉桿寫入，地圖（任務 3.5）跟未來其他跟
 * 時間有關的元件（事件圖層、政權聚焦模式等）讀取。用 service + signal，不是在 `App`
 * 元件裡開一個欄位、透過 `@Input()`/`@Output()` 逐層傳遞——時間拉桿跟地圖是同一層級的
 * 兄弟元件（都掛在 `App` 底下，不是父子關係），用 service 集中管理比一路傳遞乾淨，
 * 之後更多元件需要讀「目前年份」時也不用重新設計傳遞路徑。
 *
 * **2026-08-31 從 1-300 延伸到 1-950**（task 3.8 後補的唐朝/阿拉伯帝國種子資料，見
 * `SeedData.cs` 該區塊說明，疆域資料最遠到 907/900 年）——依然是寫死一個涵蓋現有資料
 * 的合理範圍，不是「世界史」最終該有的範圍；之後真的匯入更多時代/地區的史料還要繼續
 * 擴大，甚至改成依實際資料動態計算上下限（例如加一個 `/api/v1/territories/bounds`
 * 端點）。**189-618 年之間刻意留白**（三國種子資料結束跟唐朝/阿拉伯帝國種子資料開始
 * 之間沒有串連資料）——拖拉桿經過這段年份地圖會正確顯示「查無疆域」，不是 bug；這正是
 * 稍早討論過、刻意延後到 M4 才處理的「拉桿精度隨史料密度調整」問題的一個具體例子（見
 * PRD §12 M4 TODO），現在還是先接受這段留白，不在這裡搶先解決。
 */
@Injectable({ providedIn: 'root' })
export class TimelineState {
  static readonly MIN_YEAR = 1;
  static readonly MAX_YEAR = 950;
  static readonly DEFAULT_YEAR = 225;

  readonly year = signal(TimelineState.DEFAULT_YEAR);
}
