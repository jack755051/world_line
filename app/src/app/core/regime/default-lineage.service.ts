import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { type Observable, map, of, shareReplay, switchMap, tap } from 'rxjs';
import type { RegimeSummary } from './regime-directory.service';

interface ApiEnvelope<T> {
  data: T;
}

/** `GET /api/v1/lineage-presets` 回應的一列（見 `api/Contracts/LineagePresetResponse.cs`）。 */
interface LineagePresetApiRow {
  id: string;
  presetName: string;
  description: string | null;
  isDefault: boolean;
}

/** `GET /api/v1/lineage-presets/:id/regimes` 回應的一列（見
    `api/Contracts/LineagePresetRegimeResponse.cs`）——刻意跟 `RegimeSummary` 同一組
    欄位（後端也是照 `RegimeResponse` 的欄位設計，見 task 2.8 的說明），額外多一個
    `sortOrder`。 */
export interface LineageSequenceRegime extends RegimeSummary {
  sortOrder: number;
}

/**
 * 任務 3.9（Story 4 AC#3）：「使用者未指定特定史觀時，依 `lineage_presets` 中的
 * 預設 preset 顯示主線」。跟 `RegimeDirectoryService` 同樣的 `shareReplay(1)` 快取
 * 模式（只在第一個訂閱者觸發真正的 HTTP 請求），但這裡要串兩個請求：先查
 * `GET /lineage-presets` 找出 `isDefault===true` 的那筆，再用它的 id 查
 * `GET /lineage-presets/:id/regimes` 拿實際的政權序列，用 `switchMap` 串接。
 *
 * **應用層不強制「剛好一筆 isDefault」**——跟後端 task 2.8 的說明一致（目前只有唯讀
 * 端點，沒有寫入端點會製造出兩筆預設）：找不到任何 `isDefault` 的 preset 時視為資料
 * 尚未妥善設定，記一筆 `console.error` 並保持 `sequence` 為空陣列，不擋住整個頁面；
 * 找到多筆時直接取第一筆，不特別報錯（理論上不該發生，發生了也不是使用者能處理的
 * 錯誤）。
 */
@Injectable({ providedIn: 'root' })
export class DefaultLineageService {
  private readonly http = inject(HttpClient);

  readonly presetName = signal<string | null>(null);
  readonly sequence = signal<readonly LineageSequenceRegime[]>([]);

  private loaded$?: Observable<void>;

  ensureLoaded(): Observable<void> {
    if (!this.loaded$) {
      this.loaded$ = this.http.get<ApiEnvelope<LineagePresetApiRow[]>>('/api/v1/lineage-presets').pipe(
        switchMap((response) => {
          const defaultPreset = response.data.find((p) => p.isDefault);
          if (!defaultPreset) {
            console.error('[DefaultLineageService] 沒有找到標記 isDefault 的史觀 preset，主線序列將維持空白');
            return of(null);
          }
          this.presetName.set(defaultPreset.presetName);
          return this.http
            .get<ApiEnvelope<LineageSequenceRegime[]>>(`/api/v1/lineage-presets/${defaultPreset.id}/regimes`)
            .pipe(tap((regimesResponse) => this.sequence.set(regimesResponse.data)));
        }),
        map(() => undefined),
        shareReplay(1),
      );
    }
    return this.loaded$;
  }
}
