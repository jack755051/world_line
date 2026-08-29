import { Injectable } from '@angular/core';
import { createDiagonalHatchImageData } from './territory-dispute-pattern';

/**
 * `createDiagonalHatchImageData()`（territory-dispute-pattern.ts）需要真的 Canvas 2D
 * context，JSDOM 測試環境沒有——但 Angular 的 Vitest 整合**不支援**對相對路徑模組用
 * `vi.mock()`（「Please use Angular TestBed for mocking dependencies」），只能透過 DI
 * 替換。這個 service 存在的唯一理由就是把這個「需要真瀏覽器環境」的函式包成可注入的
 * 依賴，讓 `MapComponent` 的測試能用 `TestBed` provider 換成假的實作，不需要真的
 * Canvas——不是為了任何其他抽象化目的，純函式版本（`darkenHex`）不需要這層包裝，直接
 * 匯入用就好，見 `territory-dispute-pattern.spec.ts` 開頭說明。
 */
@Injectable({ providedIn: 'root' })
export class TerritoryHatchPatternService {
  create(baseColorHex: string): ImageData {
    return createDiagonalHatchImageData(baseColorHex);
  }
}
