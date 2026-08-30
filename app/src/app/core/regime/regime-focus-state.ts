import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import type { FeatureCollection, MultiPolygon } from 'geojson';
import type { TerritoryFeatureProperties } from '../geometry/territory-styling';

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

/**
 * 政權聚焦模式（任務 3.7，對應 PRD Story 2）的狀態——`MapComponent` 處理點擊、寫入
 * `focusedRegimeId`／`neighborRegimeIds`；`RegimeFocusPanelComponent` 只讀，不自己算。
 * `providedIn: 'root'`，跟 `TimelineState` 同一個理由：地圖跟聚焦面板是掛在 `App`
 * 底下的兄弟元件，不是父子關係，用 service 集中管理比一路傳遞 `@Input()`/`@Output()`
 * 乾淨。
 *
 * **AC#3「互動清單」（task 2.9/2.10/3.7，2026-08-30 加入這個 service）已於
 * 2026-08-31 整個搬到 `RegimeEventPanelComponent` 自己管**（使用者提案：互動記錄改
 * 顯示「這個政權全部已知事件」，不拘泥於目前拉桿停在哪一年，不再是「聚焦目標 × 目前
 * 年份」這個組合鍵才需要重新查——既然不用跟著年份變動重新查，也就不用放在這個 service
 * 裡（這裡的職責是「聚焦狀態本身」，不是「跟聚焦政權有關的所有資料」）。這個 service
 * 因此收斂回任務 3.7 原本的範圍：聚焦目標、周邊政權清單、存續區間，不再耦合事件/關係
 * 查詢，詳見 `regime-event-panel.ts` 的類別文件。
 *
 * **任務 3.14（2026-08-31）：補上 `lifetimeLoadState`**，對應 PRD §8「政權聚焦頁」
 * 四態齊備——原本存續區間查詢失敗只有 `console.error`，`RegimeFocusPanelComponent`
 * 沒有任何畫面反應（使用者看起來就像「什麼都沒發生」）。現在明確分開 loading/loaded/
 * error 三態，empty 態（該政權於當前時間點尚未建立/已不存在）維持既有的
 * `RegimeFocusPanelComponent.outOfLifetimeWarning`，不需要另外處理——那本來就是
 * `lifetimeRange` 查到之後、拿現在年份跟區間比對算出來的，屬於「loaded 但比對結果」
 * 的呈現邏輯，不是這裡的載入狀態機。
 */
@Injectable({ providedIn: 'root' })
export class RegimeFocusState {
  private readonly http = inject(HttpClient);

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
  /** 任務 3.14（PRD §8「政權聚焦頁」四態齊備）：`loadLifetimeRange()` 這筆查詢本身的
      loading/error 狀態——`lifetimeRange` 是 `null` 沒辦法區分「還在載入」跟「查詢
      失敗」跟「查到了但沒有任何疆域列」，UI 需要明確分開這三種情況才能各自顯示對應
      的畫面，不能只看 `lifetimeRange` 是不是 `null` 猜。 */
  readonly lifetimeLoadState = signal<'loading' | 'loaded' | 'error'>('loading');

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
    this.loadLifetimeRange(regimeId);
  }

  clear(): void {
    this.focusedRegimeId.set(null);
    this.neighborRegimeIds.set([]);
    this.otherContemporaryRegimeIds.set([]);
    this.lifetimeRange.set(null);
  }

  /** 任務 3.14：面板的「重試」按鈕——重新查詢目前聚焦政權的存續區間。沒有聚焦政權
      時是 no-op（理論上不該被呼叫到，按鈕只在有聚焦政權時才會渲染出來）。 */
  retryLifetimeRange(): void {
    const regimeId = this.focusedRegimeId();
    if (regimeId) {
      this.loadLifetimeRange(regimeId);
    }
  }

  setNeighbors(regimeIds: readonly string[]): void {
    this.neighborRegimeIds.set(regimeIds);
  }

  setOtherContemporaryRegimes(regimeIds: readonly string[]): void {
    this.otherContemporaryRegimeIds.set(regimeIds);
  }

  private loadLifetimeRange(regimeId: string): void {
    this.lifetimeLoadState.set('loading');

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
          this.lifetimeLoadState.set('loaded');
          const features = response.data.features;
          if (features.length === 0) {
            this.lifetimeRange.set(null);
            return;
          }
          const minYear = Math.min(...features.map((f) => f.properties.startYear));
          const maxYear = Math.max(...features.map((f) => f.properties.endYear));
          this.lifetimeRange.set({ minYear, maxYear });
        },
        // 任務 3.14：從「只有 console.error」補上 lifetimeLoadState，讓
        // RegimeFocusPanelComponent 能顯示錯誤提示+重試按鈕（見該元件樣板），
        // console.error 保留給開發時看堆疊用。
        error: (err: unknown) => {
          console.error('[RegimeFocusState] 載入政權存續區間失敗', err);
          if (this.focusedRegimeId() === regimeId) {
            this.lifetimeLoadState.set('error');
          }
        },
      });
  }
}
