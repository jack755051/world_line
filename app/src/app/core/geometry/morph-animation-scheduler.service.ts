import { Injectable } from '@angular/core';

/**
 * 疆域形變動畫（任務 3.6）的時序驅動——直接轉呼叫瀏覽器原生的
 * `requestAnimationFrame`/`cancelAnimationFrame`/`performance.now()`，唯一存在理由是
 * 讓測試能透過 Angular TestBed provider 換掉真實計時（JSDOM 雖然有提供合成的
 * `requestAnimationFrame`，但真的等待動畫時長跑完會讓測試又慢又不穩定）——跟
 * `TerritoryHatchPatternService` 包裝 Canvas 2D 是同一個處理原則：Angular 的 Vitest
 * 整合不支援對相對路徑模組用 `vi.mock()`，DI 替換是唯一可行的做法，見該檔案開頭說明。
 */
@Injectable({ providedIn: 'root' })
export class MorphAnimationScheduler {
  now(): number {
    return performance.now();
  }

  requestFrame(callback: FrameRequestCallback): number {
    return requestAnimationFrame(callback);
  }

  cancelFrame(handle: number): void {
    cancelAnimationFrame(handle);
  }
}
