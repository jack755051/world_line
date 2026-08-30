import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { type Observable, forkJoin, map, of, shareReplay, switchMap, tap } from 'rxjs';
import { RegimeDirectoryService } from './regime-directory.service';

interface ApiEnvelope<T> {
  data: T;
}

/** `GET /api/v1/regimes/:id/aliases` 回應的一筆（見 `api/Contracts/RegimeAliasResponse.cs`）。 */
export interface RegimeAliasSummary {
  id: string;
  regimeId: string;
  observerRegimeId: string | null;
  aliasName: string;
  aliasType: string | null;
}

/**
 * 任務 3.8（Story 3「觀察視角切換與名稱可追溯性」）：政權代稱目錄——`MapComponent` 要
 * 在切換命名視角（`NamingViewpointState`）時，知道「某個政權在某個觀察視角下有沒有
 * 代稱」，這個 service 負責把全部政權的代稱一次載入、快取，暴露同步查詢方法，跟
 * `RegimeDirectoryService` 同一套「載入一次、signal 快取、同步查找」的設計。
 *
 * **後端沒有「一次查全部代稱」的端點**（`GET /regimes/:id/aliases` 只能查單一政權），
 * 所以 `ensureLoaded()` 依賴 `RegimeDirectoryService.all()` 先知道有哪些政權 id，
 * 再用 `forkJoin` 對每個政權各發一次請求——目前種子資料規模（5 個政權）下這是可接受
 * 的 N 次請求，之後政權數量大到這個做法不划算時，再回頭跟後端談新增一個批次查詢端點，
 * 不在這裡預先設計還沒有需求佐證的 API。
 *
 * **刻意延後載入，不在地圖初始化時就跟著 `RegimeDirectoryService` 一起預先抓**：見
 * `map.ts` 對 `NamingViewpointState` 訂閱處的說明——多數使用者全程停留在「全球客觀
 * 視角」（AC#1），這些請求在那個情境下完全用不到，只有使用者第一次切換到某個特定
 * 觀察視角時才觸發（`ensureLoaded()` 本身沿用 `shareReplay(1)` 快取，之後切換視角
 * 不會重複載入）。
 */
@Injectable({ providedIn: 'root' })
export class RegimeAliasDirectoryService {
  private readonly http = inject(HttpClient);
  private readonly regimeDirectory = inject(RegimeDirectoryService);

  private readonly aliasesByRegime = signal<ReadonlyMap<string, readonly RegimeAliasSummary[]>>(new Map());
  private loaded$?: Observable<void>;

  ensureLoaded(): Observable<void> {
    if (!this.loaded$) {
      this.loaded$ = this.regimeDirectory.ensureLoaded().pipe(
        switchMap(() => {
          const regimes = this.regimeDirectory.all();
          if (regimes.length === 0) {
            return of([] as Array<{ regimeId: string; aliases: RegimeAliasSummary[] }>);
          }
          return forkJoin(
            regimes.map((r) =>
              this.http
                .get<ApiEnvelope<RegimeAliasSummary[]>>(`/api/v1/regimes/${r.id}/aliases`)
                .pipe(map((response) => ({ regimeId: r.id, aliases: response.data }))),
            ),
          );
        }),
        tap((results) => {
          this.aliasesByRegime.set(new Map(results.map((r) => [r.regimeId, r.aliases])));
        }),
        map(() => undefined),
        shareReplay(1),
      );
    }
    return this.loaded$;
  }

  /** 查「`targetRegimeId` 這個政權，在 `observerRegimeId` 這個視角下有沒有代稱」——
      找不到（沒有這筆代稱資料，或 `ensureLoaded()` 還沒完成）時回傳 `undefined`，
      呼叫端（`MapComponent`）fallback 回自稱名稱，跟翻譯 fallback 同一個原則
      （沒寫的內容顯示原文，不是錯誤狀態）。 */
  aliasFor(targetRegimeId: string, observerRegimeId: string): RegimeAliasSummary | undefined {
    return this.aliasesByRegime().get(targetRegimeId)?.find((a) => a.observerRegimeId === observerRegimeId);
  }
}
