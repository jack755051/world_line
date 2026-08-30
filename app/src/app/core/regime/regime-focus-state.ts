import { Injectable, Injector, computed, inject, signal } from '@angular/core';
import { toObservable } from '@angular/core/rxjs-interop';
import { HttpClient } from '@angular/common/http';
import { debounceTime } from 'rxjs';
import type { FeatureCollection, MultiPolygon } from 'geojson';
import type { TerritoryFeatureProperties } from '../geometry/territory-styling';
import { TimelineState } from '../time/timeline-state';

interface ApiEnvelope<T> {
  data: T;
}

/** 聚焦政權的整體存續年份範圍（跨所有疆域快照的 startYear/endYear 邊界），任務 3.7
    AC#2 用來在時間拉桿上標示存續區間、超出範圍時提示「尚未建立/已不存在」。用 min/max
    邊界近似「存續期間」，不逐年精確——疆域快照本身就是事件驅動的離散記錄，這是目前
    資料精度下唯一可行的定義，跟 `regimes.status`/`destroyed_by_regime_id` 這些欄位
    互補但不重複（那些是狀態機層面的「合法/終止」，這裡是地圖時間軸層面的「查得到疆域
    的年份範圍」）。 */
export interface RegimeLifetimeRange {
  minYear: number;
  maxYear: number;
}

/** `GET /api/v1/regimes/:id/events` 回應的最小形狀（見
    `api/Contracts/RegimeEventInteractionResponse.cs`）——AC#3「互動清單」的離散事件
    那一半，一筆代表聚焦政權跟 `otherRegimeId` 在 `eventId` 這個事件裡有記錄在案的
    互動（判斷來源見後端 `EventsController.GetInteractionsByRegime()` 的說明）。 */
export interface EventInteraction {
  eventId: string;
  eventName: string;
  otherRegimeId: string;
}

/** `GET /api/v1/regimes/:id/relations` 回應的形狀（見
    `api/Contracts/RegimeRelationResponse.cs`）——關係表本身對稱（`regimeAId`/
    `regimeBId` 沒有主從之分），這裡先保留原始形狀，`otherRegimeId` 由
    `toRelationInteraction()` 依查詢時的 `regimeId` 算出來，不是後端直接給的欄位。 */
interface RegimeRelationApiRow {
  id: string;
  regimeAId: string;
  regimeBId: string;
  relationType: string;
  description: string | null;
}

/** AC#3「互動清單」的持續性關係那一半——`RegimeRelationApiRow` 換算出「對這次查詢的
    政權來說，另一端是誰」之後的呈現用形狀。 */
export interface RelationInteraction {
  id: string;
  relationType: string;
  otherRegimeId: string;
  description: string | null;
}

/**
 * 政權聚焦模式（任務 3.7，對應 PRD Story 2）的狀態——`MapComponent` 處理點擊、寫入
 * `focusedRegimeId`／`neighborRegimeIds`；`RegimeFocusPanelComponent` 只讀，不自己算。
 * `providedIn: 'root'`，跟 `TimelineState` 同一個理由：地圖跟聚焦面板是掛在 `App`
 * 底下的兄弟元件，不是父子關係，用 service 集中管理比一路傳遞 `@Input()`/`@Output()`
 * 乾淨。
 *
 * **2026-08-30 追加 AC#3「互動清單」**：聚焦政權改變、或拖拉桿換年份時（兩者都會影響
 * 「這個政權在這個年份的互動記錄」），重新查 `GET /regimes/:id/events`（task 2.10 的
 * 離散事件互動端點）跟 `GET /regimes/:id/relations`（task 2.9 的持續性關係端點）。跟
 * 年份改變綁在一起，用 `toObservable` 訂閱 `[focusedRegimeId, timeline.year]` 的組合
 * （debounce 150ms，理由跟 `map.ts` 訂閱 `timeline.year` 一樣：避免拖拉桿時每個中間值
 * 都打一次 API）。**面板只顯示跟目前周邊政權清單有交集的互動**（見
 * `RegimeFocusPanelComponent`）——AC#3 原文是「聚焦政權與周邊政權之間」，不是任意兩個
 * 政權只要有記錄就列出來，這個 service 本身回傳的是「這個政權所有已知互動」（不限
 * 周邊），過濾交給面板做，這裡保持單純的資料載入職責。
 */
@Injectable({ providedIn: 'root' })
export class RegimeFocusState {
  private readonly http = inject(HttpClient);
  private readonly timeline = inject(TimelineState);
  private readonly injector = inject(Injector);

  /** 目前聚焦的政權 id，`null` 代表沒有聚焦（全域客觀視角）。 */
  readonly focusedRegimeId = signal<string | null>(null);
  /** 聚焦政權在「目前這一年」的周邊政權 id 清單——`MapComponent` 每次渲染疆域或聚焦
      對象改變時重算並寫入這裡（見 `regime-focus.ts` 的 `findNeighboringRegimeIds()`）。 */
  readonly neighborRegimeIds = signal<readonly string[]>([]);
  /** 「同時期、但不相鄰」的其他政權 id 清單（例如聚焦唐朝時的阿拉伯帝國）——見
      `regime-focus.ts` 的 `findOtherContemporaryRegimeIds()` 說明。跟
      `neighborRegimeIds` 同樣的更新時機。 */
  readonly otherContemporaryRegimeIds = signal<readonly string[]>([]);
  /** 見 `RegimeLifetimeRange` 說明。`null` 代表沒有聚焦政權，或存續區間還在載入中。 */
  readonly lifetimeRange = signal<RegimeLifetimeRange | null>(null);
  /** AC#3：聚焦政權在目前年份的離散事件互動（未過濾周邊，見類別文件說明）。 */
  readonly eventInteractions = signal<readonly EventInteraction[]>([]);
  /** AC#3：聚焦政權在目前年份的持續性關係互動（未過濾周邊，見類別文件說明）。 */
  readonly relationInteractions = signal<readonly RelationInteraction[]>([]);

  /** 每次真的觸發一輪互動清單查詢就遞增——回應回來時比對，擋下「年份/聚焦目標又變了，
      但舊請求晚回來」蓋掉新結果的競態，跟 `loadLifetimeRange()` 用
      `focusedRegimeId() !== regimeId` 判斷是同一個目的，這裡額外需要 token 是因為
      「同一個政權、換了年份」這種情況光比對 regimeId 擋不住（regimeId 沒變）。 */
  private interactionToken = 0;

  constructor() {
    // 只訂閱 timeline.year——聚焦目標改變（toggle()）本身是離散動作，直接同步呼叫
    // loadInteractions()（見下方），不需要透過這個訂閱、也不需要 debounce（跟
    // loadLifetimeRange() 在 toggle() 裡同步呼叫是同一個道理）。這裡只處理「已經聚焦
    // 某個政權時，拖拉桿換年份」這種連續動作，才需要 debounce 避免拖動時每個中間值
    // 都打一次 API。刻意不把 focusedRegimeId 也放進這個訂閱的來源信號裡（那樣會變成
    // toggle() 呼叫一次、這個訂閱的第一次 emit 又呼叫一次，同一次聚焦動作打兩次
    // 一模一樣的請求）。
    toObservable(this.timeline.year, { injector: this.injector })
      .pipe(debounceTime(150))
      .subscribe((year) => {
        const regimeId = this.focusedRegimeId();
        if (regimeId) {
          this.loadInteractions(regimeId, year);
        }
      });
  }

  /** 點擊某個政權的疆域——再次點擊同一個政權會取消聚焦（toggle），這是比較直覺的
      互動行為（點兩次回到原狀），不是每次點擊都只會「切換到新政權」。 */
  toggle(regimeId: string): void {
    if (this.focusedRegimeId() === regimeId) {
      this.clear();
      return;
    }
    this.focusedRegimeId.set(regimeId);
    this.neighborRegimeIds.set([]);
    this.otherContemporaryRegimeIds.set([]);
    this.lifetimeRange.set(null);
    this.eventInteractions.set([]);
    this.relationInteractions.set([]);
    this.loadLifetimeRange(regimeId);
    // 聚焦是離散動作（一次點擊），直接同步查，不用等建構子裡那個是給「拖拉桿換年份」
    // 用的 debounce 訂閱——理由跟上面 loadLifetimeRange() 同步呼叫一致。
    this.loadInteractions(regimeId, this.timeline.year());
  }

  clear(): void {
    this.focusedRegimeId.set(null);
    this.neighborRegimeIds.set([]);
    this.otherContemporaryRegimeIds.set([]);
    this.lifetimeRange.set(null);
    this.eventInteractions.set([]);
    this.relationInteractions.set([]);
  }

  setNeighbors(regimeIds: readonly string[]): void {
    this.neighborRegimeIds.set(regimeIds);
  }

  setOtherContemporaryRegimes(regimeIds: readonly string[]): void {
    this.otherContemporaryRegimeIds.set(regimeIds);
  }

  private loadLifetimeRange(regimeId: string): void {
    this.http
      .get<ApiEnvelope<FeatureCollection<MultiPolygon, TerritoryFeatureProperties>>>(
        `/api/v1/regimes/${regimeId}/territories`,
      )
      .subscribe({
        next: (response) => {
          // 使用者可能在請求還沒回來前就再點了別的政權，或直接取消聚焦——這裡要確認
          // 回應對應的還是目前聚焦的政權，不然會把過期請求的結果套用到新的聚焦目標，
          // 或在使用者已經取消聚焦後又把區間重新顯示回來。
          if (this.focusedRegimeId() !== regimeId) {
            return;
          }
          const features = response.data.features;
          if (features.length === 0) {
            this.lifetimeRange.set(null);
            return;
          }
          const minYear = Math.min(...features.map((f) => f.properties.startYear));
          const maxYear = Math.max(...features.map((f) => f.properties.endYear));
          this.lifetimeRange.set({ minYear, maxYear });
        },
        // 存續區間只是輔助提示，查詢失敗不影響聚焦模式本身（高亮/周邊清單照常運作），
        // 一樣先用 console.error 讓問題在開發時看得到，跟 map.ts 目前的錯誤處理水準一致。
        error: (err: unknown) => console.error('[RegimeFocusState] 載入政權存續區間失敗', err),
      });
  }

  private loadInteractions(regimeId: string, year: number): void {
    const token = ++this.interactionToken;

    this.http
      .get<ApiEnvelope<EventInteraction[]>>(`/api/v1/regimes/${regimeId}/events?year=${year}`)
      .subscribe({
        next: (response) => {
          if (token !== this.interactionToken) {
            return; // 過期請求（年份或聚焦目標又變了），見 interactionToken 的說明
          }
          this.eventInteractions.set(response.data);
        },
        error: (err: unknown) => console.error('[RegimeFocusState] 載入離散事件互動失敗', err),
      });

    this.http
      .get<ApiEnvelope<RegimeRelationApiRow[]>>(`/api/v1/regimes/${regimeId}/relations?year=${year}`)
      .subscribe({
        next: (response) => {
          if (token !== this.interactionToken) {
            return;
          }
          this.relationInteractions.set(response.data.map((row) => toRelationInteraction(row, regimeId)));
        },
        error: (err: unknown) => console.error('[RegimeFocusState] 載入持續性關係互動失敗', err),
      });
  }
}

function toRelationInteraction(row: RegimeRelationApiRow, regimeId: string): RelationInteraction {
  return {
    id: row.id,
    relationType: row.relationType,
    otherRegimeId: row.regimeAId === regimeId ? row.regimeBId : row.regimeAId,
    description: row.description,
  };
}
