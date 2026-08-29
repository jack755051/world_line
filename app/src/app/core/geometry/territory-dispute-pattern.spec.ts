import { darkenHex } from './territory-dispute-pattern';

// createDiagonalHatchImageData() 需要真的 Canvas 2D context，JSDOM 測試環境沒有
// （getContext('2d') 回傳 null）——見該函式的文件註解，不在這裡測；只測這個檔案裡
// 純函式的部分。MapComponent 消費這個函式的路徑是透過 TerritoryHatchPatternService
// （見 territory-hatch-pattern.service.ts），那層才是給 map.spec.ts 用 TestBed
// provider 替換掉的地方——Angular 的 Vitest 整合不支援對相對路徑的模組用 vi.mock()，
// 只能透過 DI 替換，這也是拆一個 service 出來的直接原因。

describe('darkenHex', () => {
  it('把顏色的每個色頻依比例調暗', () => {
    expect(darkenHex('#ffffff', 0.5)).toBe('rgb(128, 128, 128)');
  });

  it('amount=0 時原色不變', () => {
    expect(darkenHex('#1baf7a', 0)).toBe('rgb(27, 175, 122)');
  });

  it('黑色調暗後還是黑色（沒有負值）', () => {
    expect(darkenHex('#000000', 0.5)).toBe('rgb(0, 0, 0)');
  });
});
