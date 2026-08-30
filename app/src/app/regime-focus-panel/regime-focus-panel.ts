import { Component, computed, inject } from '@angular/core';
import { RegimeFocusState } from '../core/regime/regime-focus-state';
import { RegimeDirectoryService } from '../core/regime/regime-directory.service';
import { TimelineState } from '../core/time/timeline-state';
import { EventDrawerState } from '../core/event/event-drawer-state';
import { SANRING_COLLAPSIBLE_IMPORTS } from '../components/ui/collapsible';
import { TagComponent } from '../components/ui/tag';
import { EdtfDateComponent } from '../edtf-date/edtf-date';
import { describeRegimeEnd, describeRegimeOrigin } from '../core/regime/regime-transition-display';

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
 * 全部已知互動（不限周邊），過濾在這個元件的 computed 裡做。**2026-08-31（task 3.12）：
 * 離散事件可點開了**——點擊清單裡的事件會呼叫 `EventDrawerState.open(eventId)`，
 * 觸發 `app-event-drawer` 顯示詳情。**持續性關係（`relationInteractionItems`）維持
 * 純文字，刻意不能點擊**：task 3.12 範圍只有 `historical_events` 詳情抽屜，
 * `regime_relations` 沒有對應的詳情畫面（也沒有像 `sections` 那樣的結構化敘事內容
 * 可以顯示），沒有東西可以點開，硬做一個空的詳情畫面沒有意義。
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
 *
 * **2026-08-30 追加 Story 5（模糊/爭議年份呈現）**：離散事件互動每一筆下方加一行起訖
 * 日期，用 `<app-edtf-date>`（`edtf-date.ts`）呈現——只顯示史料實際記載到的精度（年/
 * 月/日），`?`/`~` 不確定標記轉成「推測年份」/「約略年份」提示。後端 `GET /regimes/
 * :id/events` 原本只回 `startDecimal`/`endDecimal`（純數字，任務 3.7 AC#3 當時只需要
 * 拿來判斷年份是否落在查詢範圍內），這次追加了 `startEdtf`/`endEdtf` 兩個原始字串
 * 欄位——decimal 換算的過程本身就會把「精度層級」跟「不確定標記」這些資訊丟失，只有
 * 原始字串留得住，UI 要呈現這些資訊沒有其他資料來源可以用。持續性關係（`regime_
 * relations`）維持只用整數年份（`valid_period` 本來就是 `INT4RANGE`，不是 EDTF），
 * 不套用這個元件。
 *
 * **2026-08-30 追加 Story 4 AC#2（政權狀態轉換視覺呈現）**：標題下方新增「起源／終止」
 * 兩個 `sanring-tag`——文字/variant 由純函式模組 `regime-transition-display.ts` 決定
 * （這個元件只負責把 `RegimeDirectoryService` 查到的 id 轉成名稱餵進去，見
 * `originDescription`/`endDescription` 兩個 computed 的說明）。AC#2 憲法原話「取代跟
 * 消滅應該是兩種不同的定義」——`succeeded`（禪讓）用 `default` variant，`conquered`
 * （被滅亡）用 `destructive`（紅）variant，兩者在畫面上一定是不同顏色，不會混淆；
 * `status==='active'` 時 `endDescription().text` 是 `null`，不顯示終止 Tag（政權仍
 * 存續，沒有「終止」可以描述）。
 */
@Component({
  selector: 'app-regime-focus-panel',
  standalone: true,
  imports: [SANRING_COLLAPSIBLE_IMPORTS, TagComponent, EdtfDateComponent],
  templateUrl: './regime-focus-panel.html',
  styleUrl: './regime-focus-panel.scss',
})
export class RegimeFocusPanelComponent {
  private readonly focusState = inject(RegimeFocusState);
  private readonly directory = inject(RegimeDirectoryService);
  private readonly timeline = inject(TimelineState);
  private readonly eventDrawer = inject(EventDrawerState);

  protected readonly focusedRegimeId = this.focusState.focusedRegimeId;

  protected readonly focusedRegimeName = computed(() => {
    const id = this.focusedRegimeId();
    return id ? (this.directory.nameOf(id) ?? id) : null;
  });

  /** 任務 3.9 AC#2：聚焦政權「怎麼來的」——見 `regime-transition-display.ts` 說明，
      這裡只負責把 `RegimeDirectoryService` 查到的原始 id 轉成名稱字串餵給純函式。 */
  protected readonly originDescription = computed(() => {
    const id = this.focusedRegimeId();
    if (!id) {
      return null;
    }
    const regime = this.directory.regimeOf(id);
    if (!regime) {
      return null;
    }
    return describeRegimeOrigin({
      predecessorRegimeId: regime.predecessorRegimeId,
      originTransitionType: regime.originTransitionType,
      predecessorName: regime.predecessorRegimeId ? this.directory.nameOf(regime.predecessorRegimeId) : undefined,
    });
  });

  /** 任務 3.9 AC#2：聚焦政權「怎麼終止的」——`status==='active'` 時回傳 `text: null`，
      模板用這個判斷是否要顯示終止 Tag（仍存續的政權沒有終止可以描述）。 */
  protected readonly endDescription = computed(() => {
    const id = this.focusedRegimeId();
    if (!id) {
      return null;
    }
    const regime = this.directory.regimeOf(id);
    if (!regime) {
      return null;
    }
    return describeRegimeEnd({
      status: regime.status,
      destroyedByRegimeId: regime.destroyedByRegimeId,
      destroyedByName: regime.destroyedByRegimeId ? this.directory.nameOf(regime.destroyedByRegimeId) : undefined,
      successorNames: this.directory.successorOf(id).map((r) => r.selfName),
      splitChildrenNames: this.directory.splitChildrenOf(id).map((r) => r.selfName),
    });
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
        eventId: interaction.eventId,
        label: interaction.eventName,
        otherRegimeName: this.directory.nameOf(interaction.otherRegimeId) ?? interaction.otherRegimeId,
        // 任務 3.10：事件用起訖兩個 EDTF 日期都顯示——跟疆域/存續區間那種「一個範圍」
        // 不同，這裡的兩個日期分別可能有各自獨立的精度/不確定性（例如起始日期確定、
        // 結束日期是推測），不能只挑一個顯示。
        startEdtf: interaction.startEdtf,
        endEdtf: interaction.endEdtf,
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

  /** task 3.12：點擊互動清單裡的事件，打開事件詳情抽屜。 */
  protected openEvent(eventId: string): void {
    this.eventDrawer.open(eventId);
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
