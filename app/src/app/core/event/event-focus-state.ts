import { Injectable, signal } from '@angular/core';

/** 目前在 `RegimeEventPanelComponent` 手風琴裡展開的那一筆事件——只留下 task 3.4
    副軸需要的最小欄位（不是整份 `HistoricalEventDetail`，那份要等 API 回來才有，
    這裡在使用者一點開手風琴的當下就要能顯示，用列表列本身已經有的欄位就夠）。 */
export interface FocusedEventInfo {
  readonly id: string;
  readonly name: string;
  readonly startEdtf: string;
  readonly endEdtf: string;
}

/**
 * 任務 3.4（時間軸 Scrubber 副軸）的橋接狀態——`RegimeEventPanelComponent`（手風琴
 * 展開/收合）跟 `TimeScrubberComponent`（副軸要不要顯示）是同一層級的兄弟元件（都掛在
 * `App` 底下），不是父子關係，用 service + signal 集中管理，同 `RegimeFocusState`/
 * `TimelineState` 既有模式，不用 `@Input()`/`@Output()` 逐層傳遞。
 *
 * **只存「目前展開的是哪一筆」，不存副軸要不要顯示的判斷結果**——「這筆事件的 EDTF
 * 有沒有月/日精度」是純函式（`parseEdtf()`）就能從 `startEdtf`/`endEdtf` 算出來的
 * 衍生資訊，副軸自己 `computed()` 判斷，不要在這個 service 裡重複維護一份。
 */
@Injectable({ providedIn: 'root' })
export class EventFocusState {
  readonly expandedEvent = signal<FocusedEventInfo | null>(null);
}
