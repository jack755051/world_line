import { Component, computed, inject } from '@angular/core';
import { RegimeFocusState } from '../core/regime/regime-focus-state';
import { RegimeDirectoryService } from '../core/regime/regime-directory.service';
import { TimelineState } from '../core/time/timeline-state';
import { SANRING_COLLAPSIBLE_IMPORTS } from '../components/ui/collapsible';
import { TagComponent } from '../components/ui/tag';

/**
 * 政權聚焦模式的資訊面板（任務 3.7，對應 PRD Story 2）——點擊地圖上的疆域後顯示，列出
 * 聚焦政權名稱、同時期周邊政權清單，以及存續區間警示（AC#2：拖動時間拉桿超出聚焦政權
 * 存續區間時提示「尚未建立/已不存在」）。這個元件本身**只讀** `RegimeFocusState`，
 * 不自己算高亮/相鄰關係——那些是 `MapComponent` 的責任（見 map.ts 開頭說明），職責
 * 單一，跟 `TimeScrubberComponent`「只管拖到哪一年，不管拖動後要做什麼」是同一個
 * 分工原則。
 *
 * **AC#3（互動清單）2026-08-30 完成**：task 2.9（政權關係）、2.10（事件骨幹，含
 * `GET /regimes/:id/events` 這個專門給 AC#3 用的互動查詢端點）都已完成，離散事件用
 * `RegimeFocusState.eventInteractions`、持續性關係用 `relationInteractions`。
 * **只顯示跟目前「同時期周邊政權」有交集的互動**——AC#3 原文是「聚焦政權與周邊政權
 * 之間」，不是任意兩個政權只要有記錄就列出來；`RegimeFocusState` 回傳的是這個政權
 * 全部已知互動（不限周邊），過濾在這個元件的 computed 裡做。**「可點擊追溯」目前只是
 * 純文字，還不能真的點開**——事件/關係的詳情畫面（task 3.12 事件詳情抽屜）還沒做，
 * 沒有東西可以追溯過去，先把「有哪些互動」列出來，可點擊的部分等 3.12 做出來再補。
 *
 * **2026-08-30 改用 Sanring `Collapsible` 收納周邊政權清單，不是 `Sheet`**——使用者
 * 一開始提議改用 `Sheet`，但 Sanring 的 `Sheet` 是包在 CDK Dialog 之上的真．模態框
 * （鎖 `<body>` 捲動、背景其他元素標 `aria-hidden`、有可點擊關閉的遮罩、focus trap），
 * 這些行為都是「讓使用者專心看這塊內容、暫時不管背景」設計的，跟「同時看地圖高亮+讀
 * 面板」這個需求方向相反，沒有內建選項可以關掉模態行為（使用者自己也在提案的同一句話
 * 裡發現了這個問題）。`Collapsible` 沒有遮罩、不鎖畫面，單純是可展開/收合的內容區塊，
 * 拿來包「同時期周邊政權」這個區塊，讓使用者可以視情況收起來、面板佔用的畫面更小，
 * 面板本身仍然是固定在角落的一般 DOM 元素，不會蓋住地圖操作。政權名稱（標題列）跟
 * 存續區間警告刻意留在 Collapsible 外面、永遠可見——警告是「這個政權現在不存在」這種
 * 重要資訊，不該被收合狀態藏起來。
 *
 * **2026-08-30 追加兩塊內容**：
 * - **存續期間**（標題下方）：跟使用者確認過先只用年份精度（`RegimeFocusState.
 *   lifetimeRange`，已經有這份資料，不用新增查詢）——日期精度（例如「221年5月15日」）
 *   需要查 `historical_events` 裡禪讓/滅國事件的確切 EDTF 日期，那個查詢端點
 *   （task 2.10）還沒做，先不做，等 2.10 做出來再回頭補精確日期。
 * - **同時期其他地區政權**（新的 Collapsible 區塊，見 `map.ts` 的
 *   `findOtherContemporaryRegimeIds()` 說明）：跟「周邊政權」不是同一件事——周邊是
 *   地理相鄰，這塊是「同時期存在、但不相鄰」（例如唐朝聚焦時的阿拉伯帝國）。
 *
 * 政權名稱改用 Sanring `Tag` 呈現（`npx @sanring/cli add tag`，同批裝了它的依賴
 * `Badge`）——**跟使用者確認過**：`Tag`/`Badge` 的配色是走固定的語意 variant
 * （`default`/`secondary`/`destructive`/`outline`/`ghost`，見 `badge.directive.ts`），
 * 沒有設計成讓每個實例帶入任意顏色，這裡刻意不硬套「文字色＝該政權在地圖上的
 * colorSlot 色」這種每個政權都不同的動態配色（會需要繞過它內部的 Tailwind class
 * 合併機制），固定用同一個 `variant` 呈現所有政權名稱，不嘗試精確對應地圖顏色。
 *
 * **「三國」這種歷史分期標籤——使用者提過，先記下來、還沒做**：目前 `regimes` schema
 * 完全沒有「歷史分期」這個概念，`lineage_presets` 是史觀方案不是分期；現有種子資料
 * 也全部落在同一個分期（三國），加了也沒有區分度。等之後真的匯入跨分期的世界史資料
 * （例如唐朝/阿拉伯帝國那個時代）再回頭設計這塊怎麼從資料庫查出來，不要用前端寫死的
 * 對照表撐過去。
 */
@Component({
  selector: 'app-regime-focus-panel',
  standalone: true,
  imports: [SANRING_COLLAPSIBLE_IMPORTS, TagComponent],
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

  /** 存續期間文字，例如「西元 221–263 年」——只有年份精度，見上方類別文件說明。 */
  protected readonly lifespanText = computed(() => {
    const range = this.focusState.lifetimeRange();
    return range ? `西元 ${range.minYear}–${range.maxYear} 年` : null;
  });

  protected readonly neighborNames = computed(() => this.toSortedNames(this.focusState.neighborRegimeIds()));

  protected readonly otherContemporaryNames = computed(() =>
    this.toSortedNames(this.focusState.otherContemporaryRegimeIds()),
  );

  /** AC#3 離散事件互動——只保留跟目前周邊政權有交集的，見類別文件說明。 */
  protected readonly eventInteractionItems = computed(() => {
    const neighborIds = new Set(this.focusState.neighborRegimeIds());
    return this.focusState
      .eventInteractions()
      .filter((interaction) => neighborIds.has(interaction.otherRegimeId))
      .map((interaction) => ({
        key: `${interaction.eventId}-${interaction.otherRegimeId}`,
        label: interaction.eventName,
        otherRegimeName: this.directory.nameOf(interaction.otherRegimeId) ?? interaction.otherRegimeId,
      }));
  });

  /** AC#3 持續性關係互動——同樣只保留跟目前周邊政權有交集的。 */
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

  /** regimeId 清單→排序過的名稱清單——`neighborNames`/`otherContemporaryNames` 共用
      同一套轉換邏輯，不重複寫兩次。 */
  private toSortedNames(regimeIds: readonly string[]): string[] {
    return regimeIds
      .map((id) => this.directory.nameOf(id) ?? id)
      // 用 zh-Hant collator 排序，不是保留後端回傳/相鄰運算的原始順序——那個順序沒有
      // 對使用者有意義的語意（取決於 Set 迭代順序跟浮點座標排序細節），字母/筆畫排序
      // 至少是一個穩定、使用者看得懂的呈現方式。
      .sort((a, b) => a.localeCompare(b, 'zh-Hant'));
  }
}
