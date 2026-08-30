import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toObservable } from '@angular/core/rxjs-interop';
import { HttpClient } from '@angular/common/http';
import { debounceTime } from 'rxjs';
import { TimelineState } from '../core/time/timeline-state';
import { NamingViewpointState } from '../core/regime/naming-viewpoint-state';
import type { RegimeSummary } from '../core/regime/regime-directory.service';

/** `ApiResponse<T>` 的最小形狀，同 `time-scrubber.ts`/`map.ts` 的 `ApiEnvelope<T>`。 */
interface ApiEnvelope<T> {
  data: T;
}

/**
 * 任務 3.8（Story 3 AC#1/AC#2）：命名視角切換下拉選單——「全球客觀視角」（預設，AC#1
 * 一律自稱）或「以某政權的視角」（AC#2，其他政權標籤改顯示該視角下的代稱）。這個元件
 * 只負責寫入 `NamingViewpointState`，實際套用代稱、決定要顯示什麼名稱是 `MapComponent`
 * 的事（跟 `TimeScrubberComponent`「只管拉到哪一年，不管拉動後要做什麼」同一個職責
 * 單一原則）。
 *
 * **2026-08-31 從「列出全部政權」改成「依目前拉桿年份過濾」**（使用者提出的規模疑慮：
 * 這個專案的終局目標是世界史規模，全部政權攤開在一個原生 `<select>` 裡，政權數一多
 * 就是不可用的落落長清單，而且「用還沒存在/已滅亡的政權視角看這個年份」本身也沒有
 * 敘事意義）。改用 `GET /api/v1/regimes?year=` — task 2.4 既有端點，跟 task 2.6
 * 疆域查詢同一套「當年有效（未被 I5 取代）疆域快照」判斷，語意一致，不用新增後端
 * 程式碼。訂閱 `TimelineState.year` 的節奏跟 `TimeScrubberComponent`/`MapComponent`
 * 一致：`debounceTime(150)`，不是每個拖動中間值都打一次 API。
 *
 * **選到的觀察者在換年份後不再是當代政權時，自動清回「全球客觀視角」**：不讓選單留著
 * 一個使用者看不到、也不在選項清單裡的殘留選取值（原生 `<select>` 的 value 對不到任何
 * `<option>` 時瀏覽器行為本身就不明確），比「保留選取但暫時沒視覺效果」更誠實——跟這個
 * 專案一貫「不留使用者猜不到在幹嘛的隱性狀態」原則一致。
 */
@Component({
  selector: 'app-naming-viewpoint-selector',
  standalone: true,
  templateUrl: './naming-viewpoint-selector.html',
  styleUrl: './naming-viewpoint-selector.scss',
})
export class NamingViewpointSelectorComponent {
  private readonly timeline = inject(TimelineState);
  private readonly viewpoint = inject(NamingViewpointState);
  private readonly http = inject(HttpClient);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly currentObserverId = this.viewpoint.observerRegimeId;

  private readonly contemporaryRegimes = signal<readonly RegimeSummary[]>([]);

  protected readonly regimes = computed(() =>
    [...this.contemporaryRegimes()].sort((a, b) => a.selfName.localeCompare(b.selfName, 'zh-Hant')),
  );

  constructor() {
    toObservable(this.timeline.year)
      .pipe(debounceTime(150), takeUntilDestroyed(this.destroyRef))
      .subscribe((year) => this.loadContemporaryRegimes(year));
  }

  protected onChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.viewpoint.setObserver(value === '' ? null : value);
  }

  private loadContemporaryRegimes(year: number): void {
    this.http.get<ApiEnvelope<RegimeSummary[]>>(`/api/v1/regimes?year=${year}`).subscribe({
      next: (response) => {
        this.contemporaryRegimes.set(response.data);

        const currentObserver = this.viewpoint.observerRegimeId();
        if (currentObserver !== null && !response.data.some((r) => r.id === currentObserver)) {
          this.viewpoint.setObserver(null);
        }
      },
      // 同 `TimeScrubberComponent.loadReignEras()`：第一版先求資料管線走得通，還沒有
      // loading/error 狀態的 UI 呈現，用 console.error 讓問題在開發時看得到。
      error: (err: unknown) => console.error('[NamingViewpointSelectorComponent] 載入當代政權清單失敗', err),
    });
  }
}
