import { Component, computed, inject } from '@angular/core';
import { RegimeFocusState } from '../core/regime/regime-focus-state';
import { RegimeDirectoryService } from '../core/regime/regime-directory.service';
import { EventDrawerState } from '../core/event/event-drawer-state';
import { EdtfDateComponent } from '../edtf-date/edtf-date';

/**
 * 政權互動記錄的地圖疊加面板（2026-08-31，使用者提案：把 AC#3 互動清單從
 * `RegimeFocusPanelComponent`（固定在左上角）搬出來，改成疊在聚焦政權的疆域正上方的
 * 獨立毛玻璃卡片，跟 task 3.12 事件詳情抽屜同一套視覺語言）。
 *
 * **這個元件本身不是用一般的 `<app-...>` 標籤掛在 `app.html` 裡**——它是被
 * `MapComponent` 用 `ViewContainerRef.createComponent()` 動態建立，把渲染出來的
 * DOM 元素交給 MapLibre 的 `Marker` 掛在地圖上、跟著政權疆域的地理座標定位（見
 * map.ts 的 `updateEventPanelMarker()`）。這是這個專案第一次把 Angular 元件（而不是
 * 純 DOM 元素，見 `renderLabels()` 的政權名稱標籤）當 Marker 內容用——因為政權名稱
 * 標籤只需要靜態文字，這裡需要完整的 Angular 響應式綁定（清單會隨互動資料/命名視角
 * 變動）跟事件處理（點擊開抽屜），純手刻 DOM 沒辦法重用既有的 computed/樣板語法。
 *
 * **`:host` 刻意不是 `display: contents`**（跟這個專案其他固定角落面板不同）：
 * MapLibre `Marker` 靠對它拿到的 DOM 元素本身套用 `position`/`transform` 樣式來定位，
 * `display: contents` 的元素不產生自己的 box，套用 transform 不會有效果——這個元件的
 * host 元素就是真正要被地圖定位的那個 box，樣式直接寫在它自己身上，不像其他面板把
 * 排版交給父層容器。
 *
 * **邏輯搬自 `RegimeFocusPanelComponent`（task 3.7 AC#3），資料來源不變**：
 * `eventInteractionItems`/`relationInteractionItems` 一樣只保留跟目前「同時期周邊
 * 政權」有交集的互動，離散事件一樣可點擊開 `EventDrawerState`，持續性關係一樣維持
 * 純文字（理由見 `EventDrawerComponent` 類別文件）。**沒有互動記錄時整個面板不渲染
 * 任何內容**（跟原本在側欄面板裡顯示「這個年份沒有查到...」空狀態文案不同）——這個
 * 面板疊在地圖上，多數年份沒有互動記錄時若還顯示一張空卡片，會變成每次點擊政權都冒出
 * 一個沒有內容的浮動卡片，比不顯示更干擾；空狀態的說明文字留在 `RegimeFocusPanel`
 * 的側欄裡就夠了。
 */
@Component({
  selector: 'app-regime-event-panel',
  standalone: true,
  imports: [EdtfDateComponent],
  templateUrl: './regime-event-panel.html',
  styleUrl: './regime-event-panel.scss',
})
export class RegimeEventPanelComponent {
  private readonly focusState = inject(RegimeFocusState);
  private readonly directory = inject(RegimeDirectoryService);
  private readonly eventDrawer = inject(EventDrawerState);

  /** 離散事件互動——只保留跟目前周邊政權有交集的，見類別文件說明。 */
  protected readonly eventInteractionItems = computed(() => {
    const neighborIds = new Set(this.focusState.neighborRegimeIds());
    return this.focusState
      .eventInteractions()
      .filter((interaction) => neighborIds.has(interaction.otherRegimeId))
      .map((interaction) => ({
        key: `${interaction.eventId}-${interaction.otherRegimeId}`,
        eventId: interaction.eventId,
        label: interaction.eventName,
        otherRegimeName: this.directory.nameOf(interaction.otherRegimeId) ?? interaction.otherRegimeId,
        startEdtf: interaction.startEdtf,
        endEdtf: interaction.endEdtf,
      }));
  });

  /** 持續性關係互動——同樣只保留跟目前周邊政權有交集的。 */
  protected readonly relationInteractionItems = computed(() => {
    const neighborIds = new Set(this.focusState.neighborRegimeIds());
    return this.focusState
      .relationInteractions()
      .filter((interaction) => neighborIds.has(interaction.otherRegimeId))
      .map((interaction) => ({
        key: interaction.id,
        label: interaction.relationType,
        otherRegimeName: this.directory.nameOf(interaction.otherRegimeId) ?? interaction.otherRegimeId,
        description: interaction.description,
      }));
  });

  /** task 3.12：點擊互動清單裡的事件，打開事件詳情抽屜。 */
  protected openEvent(eventId: string): void {
    this.eventDrawer.open(eventId);
  }
}
