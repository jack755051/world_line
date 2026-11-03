import { labelMinZoom, mercatorY, minZoomFromScreenWidth, visibleIds } from './label-fit';

describe('label-fit（名字寬度 vs 國家螢幕寬度）', () => {
  it('國家寬度剛好等於名字寬度時的縮放', () => {
    // 寬 36° = 0.1 世界；z=0 時 51.2px；名字 102.4px → z=1
    expect(labelMinZoom(102.4, [0, 0, 36, 10])).toBeCloseTo(1, 6);
  });
  it('國家越大門檻越低、名字越長門檻越高', () => {
    expect(labelMinZoom(80, [0, 0, 40, 10])).toBeLessThan(labelMinZoom(80, [0, 0, 10, 10]));
    expect(labelMinZoom(120, [0, 0, 20, 10])).toBeGreaterThan(labelMinZoom(60, [0, 0, 20, 10]));
  });
  it('旋轉的名字用外框長邊（狹長國家）', () => {
    const tall: [number, number, number, number] = [0, -40, 2, 0];
    expect(labelMinZoom(80, tall, true)).toBeLessThan(labelMinZoom(80, tall, false));
  });
  it('外框無效 → 不顯示', () => {
    expect(labelMinZoom(80, [5, 5, 5, 9])).toBe(Infinity);
  });
  it('mercatorY 赤道 0.5、北半球較小', () => {
    expect(mercatorY(0)).toBeCloseTo(0.5, 9);
    expect(mercatorY(60)).toBeLessThan(0.5);
  });
  it('首都：由目前縮放的螢幕寬度換算，同一條規則', () => {
    expect(minZoomFromScreenWidth(100, 50, 3)).toBeCloseTo(4, 9);
    expect(minZoomFromScreenWidth(50, 100, 3)).toBeCloseTo(2, 9);
    expect(minZoomFromScreenWidth(50, 0, 3)).toBe(Infinity);
  });
  it('visibleIds：裝得下才顯示，被選政權一律排除', () => {
    const fs = [
      { id: 'a', regimeId: 'R1', minZoom: 2 },
      { id: 'b', regimeId: 'R2', minZoom: 5 },
      { id: 'c', regimeId: 'R3', minZoom: 1 },
    ];
    expect(visibleIds(fs, 3, null)).toEqual(['a', 'c']);
    expect(visibleIds(fs, 6, null)).toEqual(['a', 'b', 'c']);
    expect(visibleIds(fs, 6, 'R1')).toEqual(['b', 'c']);
  });
});
