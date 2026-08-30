import { Injectable, signal } from '@angular/core';

/**
 * 任務 3.12（事件詳情抽屜）：目前打開中的事件 id，`null` 代表抽屜關閉。
 *
 * **刻意跟 `RegimeFocusState`（任務 3.7）分開**——同樣理由見 `NamingViewpointState`
 * 的類別文件：聚焦政權跟打開事件詳情是兩個獨立的使用者動作，硬共用同一個 signal 會讓
 * 兩件事的意圖糾纏在一起（例如關閉聚焦面板不該連帶關掉事件抽屜，反之亦然）。
 */
@Injectable({ providedIn: 'root' })
export class EventDrawerState {
  readonly openEventId = signal<string | null>(null);

  open(eventId: string): void {
    this.openEventId.set(eventId);
  }

  close(): void {
    this.openEventId.set(null);
  }
}
