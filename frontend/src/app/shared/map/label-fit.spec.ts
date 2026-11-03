import { NEVER_ZOOM, clampMinZoom, labelFilterExpr, labelMinZoom, mercatorY, minZoomFromScreenWidth } from './label-fit';

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
  it('clampMinZoom：Infinity／NaN 改成上限', () => {
    expect(clampMinZoom(Infinity)).toBe(NEVER_ZOOM);
    expect(clampMinZoom(NaN)).toBe(NEVER_ZOOM);
    expect(clampMinZoom(3.2)).toBe(3.2);
  });
  it('labelFilterExpr：未選取只比縮放；選取時排除該政權', () => {
    expect(labelFilterExpr(null)).toEqual(['>=', ['zoom'], ['coalesce', ['get', 'minZoom'], NEVER_ZOOM]]);
    const e = labelFilterExpr('R1') as unknown[];
    expect(e[0]).toBe('all');
    expect(e[2]).toEqual(['!=', ['coalesce', ['get', 'regimeId'], ''], 'R1']);
  });
});
