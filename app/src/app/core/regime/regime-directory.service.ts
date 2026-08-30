import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { type Observable, map, shareReplay, tap } from 'rxjs';

/** `GET /api/v1/regimes` 回應的最小形狀（見 api/Contracts/RegimeResponse.cs）——這裡
    只取畫標籤/聚焦面板用得到的 id/selfName，其餘欄位（status、轉換邊）暫時用不到不列。 */
export interface RegimeSummary {
  id: string;
  selfName: string;
}

interface ApiEnvelope<T> {
  data: T;
}

/**
 * 政權 id→名稱對照表——原本是 `MapComponent` 私有欄位（畫標籤用），任務 3.7 政權聚焦
 * 面板（`RegimeFocusPanelComponent`）也需要同一份對照（顯示聚焦政權/周邊政權的名稱），
 * 抽成 `providedIn: 'root'` 的共用 service，兩邊都讀同一份、只打一次 API，不是各自
 * 重複查詢。
 *
 * 政權清單不隨年份變動（政權本身的存在跟時間拉桿無關，變動的是「哪些政權的疆域快照
 * 落在這個年份」，見 `map.ts` 開頭說明），所以用 `shareReplay(1)` 快取：第一個訂閱者
 * 觸發真正的 HTTP 請求，之後任何人呼叫 `ensureLoaded()` 都直接拿到同一份快取結果，
 * 不重複打 API。
 */
@Injectable({ providedIn: 'root' })
export class RegimeDirectoryService {
  private readonly http = inject(HttpClient);
  private readonly nameById = signal<ReadonlyMap<string, string>>(new Map());
  private loaded$?: Observable<void>;

  /** 觸發載入（idempotent，重複呼叫不會重複打 API，見上方類別說明）。回傳的
      Observable 在名稱對照表就緒後 complete——呼叫端（`MapComponent`）藉此確保開始
      渲染疆域/標籤時，政權名稱已經可以查得到。 */
  ensureLoaded(): Observable<void> {
    if (!this.loaded$) {
      this.loaded$ = this.http.get<ApiEnvelope<RegimeSummary[]>>('/api/v1/regimes').pipe(
        tap((response) => {
          this.nameById.set(new Map(response.data.map((r) => [r.id, r.selfName])));
        }),
        map(() => undefined),
        shareReplay(1),
      );
    }
    return this.loaded$;
  }

  /** 查無資料（理論上不該發生，除非 `ensureLoaded()` 還沒完成或疆域/政權資料不一致）
      時回傳 `undefined`，呼叫端自行決定 fallback 顯示什麼（例如直接顯示 regimeId）。 */
  nameOf(regimeId: string): string | undefined {
    return this.nameById().get(regimeId);
  }
}
