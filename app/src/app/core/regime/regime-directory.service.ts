import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { type Observable, map, shareReplay, tap } from 'rxjs';

/** `GET /api/v1/regimes` 回應的形狀（見 `api/Contracts/RegimeResponse.cs`）。
    **2026-08-30 從只有 id/selfName 擴充成完整欄位**（任務 3.9，Story 4「政權狀態轉換
    視覺呈現」）：AC#2 要求呈現「被取代（禪讓）」跟「被滅亡」的視覺區分，需要
    `status`/`originTransitionType`/`destroyedByRegimeId` 這些欄位，不能只有名稱。 */
export interface RegimeSummary {
  id: string;
  selfName: string;
  status: 'active' | 'split' | 'succeeded' | 'conquered';
  predecessorRegimeId: string | null;
  originTransitionType: 'split' | 'succeeded' | null;
  destroyedByRegimeId: string | null;
}

interface ApiEnvelope<T> {
  data: T;
}

/**
 * 政權目錄——原本是 `MapComponent` 私有欄位（畫標籤用），任務 3.7 政權聚焦面板也需要
 * 同一份對照，抽成 `providedIn: 'root'` 的共用 service，兩邊都讀同一份、只打一次 API，
 * 不是各自重複查詢。
 *
 * 政權清單不隨年份變動（政權本身的存在跟時間拉桿無關，變動的是「哪些政權的疆域快照
 * 落在這個年份」，見 `map.ts` 開頭說明），所以用 `shareReplay(1)` 快取：第一個訂閱者
 * 觸發真正的 HTTP 請求，之後任何人呼叫 `ensureLoaded()` 都直接拿到同一份快取結果，
 * 不重複打 API。
 *
 * **2026-08-30 追加反向查詢**（任務 3.9）：`regimes.destroyed_by_regime_id` 依 PRD §6
 * 明確只在 `status='conquered'`（被滅亡）時才會填值，`status='succeeded'`（被取代/
 * 禪讓）時這個欄位刻意留 `NULL`——後繼者是誰只能反查「哪個政權的 predecessor_regime_id
 * 指向這個政權」，跟 `EventsController.GetInteractionsByRegime()` 反查政權轉換事件
 * 另一方是同一個模式（後端也沒有把這個反向關係另外存一份，前端跟後端都用同一套「正向
 * 欄位 + 反向查詢」的處理方式，不是各自發明）。`successorOf()`／`splitChildrenOf()`
 * 就是做這件事——都是對已經快取好的全部政權清單做記憶體內查找，不用額外打 API。
 */
@Injectable({ providedIn: 'root' })
export class RegimeDirectoryService {
  private readonly http = inject(HttpClient);
  private readonly regimesById = signal<ReadonlyMap<string, RegimeSummary>>(new Map());
  private loaded$?: Observable<void>;

  /** 觸發載入（idempotent，重複呼叫不會重複打 API，見上方類別說明）。回傳的
      Observable 在資料就緒後 complete——呼叫端（`MapComponent`）藉此確保開始渲染
      疆域/標籤時，政權資料已經可以查得到。 */
  ensureLoaded(): Observable<void> {
    if (!this.loaded$) {
      this.loaded$ = this.http.get<ApiEnvelope<RegimeSummary[]>>('/api/v1/regimes').pipe(
        tap((response) => {
          this.regimesById.set(new Map(response.data.map((r) => [r.id, r])));
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
    return this.regimesById().get(regimeId)?.selfName;
  }

  /** 完整政權記錄查詢，供任務 3.9 的狀態轉換呈現用。 */
  regimeOf(regimeId: string): RegimeSummary | undefined {
    return this.regimesById().get(regimeId);
  }

  /** 全部政權清單（任務 3.8：`RegimeAliasDirectoryService` 要對每個政權各查一次代稱，
      需要先知道有哪些政權 id，不用另外打一次 `/regimes` 拿清單）。 */
  all(): readonly RegimeSummary[] {
    return [...this.regimesById().values()];
  }

  /** 反查「誰接續了這個政權」（`status='succeeded'` 時用）——找出所有
      `predecessorRegimeId` 指向這個政權、且 `originTransitionType==='succeeded'` 的
      政權。理論上只會有 0 或 1 筆（禪讓是一對一），回傳陣列是為了跟
      `splitChildrenOf()` 介面一致，呼叫端自己視情況只取第一筆。 */
  successorOf(regimeId: string): readonly RegimeSummary[] {
    return this.all().filter(
      (r) => r.predecessorRegimeId === regimeId && r.originTransitionType === 'succeeded',
    );
  }

  /** 反查「這個政權分裂出了哪些政權」（`status='split'` 時用）——分裂本來就是一對多，
      不像禪讓/滅亡有單一對象，所以回傳的是整批清單，不是單一結果。 */
  splitChildrenOf(regimeId: string): readonly RegimeSummary[] {
    return this.all().filter(
      (r) => r.predecessorRegimeId === regimeId && r.originTransitionType === 'split',
    );
  }
}
