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
 */
@Injectable({ providedIn: 'root' })
export class RegimeFocusState {
  private readonly http = inject(HttpClient);

  /** 目前聚焦的政權 id，`null` 代表沒有聚焦（全域客觀視角）。 */
  readonly focusedRegimeId = signal<string | null>(null);
  /** 聚焦政權在「目前這一年」的周邊政權 id 清單——`MapComponent` 每次渲染疆域或聚焦
      對象改變時重算並寫入這裡（見 `regime-focus.ts` 的 `findNeighboringRegimeIds()`）。 */
  readonly neighborRegimeIds = signal<readonly string[]>([]);
  /** 見 `RegimeLifetimeRange` 說明。`null` 代表沒有聚焦政權，或存續區間還在載入中。 */
  readonly lifetimeRange = signal<RegimeLifetimeRange | null>(null);

  /** 點擊某個政權的疆域——再次點擊同一個政權會取消聚焦（toggle），這是比較直覺的
      互動行為（點兩次回到原狀），不是每次點擊都只會「切換到新政權」。 */
  toggle(regimeId: string): void {
    if (this.focusedRegimeId() === regimeId) {
      this.clear();
      return;
    }
    this.focusedRegimeId.set(regimeId);
    this.neighborRegimeIds.set([]);
    this.lifetimeRange.set(null);
    this.loadLifetimeRange(regimeId);
  }

  clear(): void {
    this.focusedRegimeId.set(null);
    this.neighborRegimeIds.set([]);
    this.lifetimeRange.set(null);
  }

  setNeighbors(regimeIds: readonly string[]): void {
    this.neighborRegimeIds.set(regimeIds);
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
}
