import { conflictArc, worldShift } from './conflict-arc';

describe('conflictArc（遠距交戰虛線弧）', () => {
  it('柏林—華盛頓：兩端為端點、中點在大西洋上且往北彎，雙劍放中點', () => {
    const a = conflictArc([10.58, 50.64], [-99.7, 37.25]);
    expect(a.path[0]).toEqual([10.58, 50.64]);
    expect(a.path[a.path.length - 1]).toEqual([-99.7, 37.25]);
    expect(a.path.length).toBe(49);
    expect(a.mid).toEqual(a.path[24]);
    expect(a.mid[0]).toBeGreaterThan(-60);
    expect(a.mid[0]).toBeLessThan(-20);
    // 比兩端緯度平均值更北
    expect(a.mid[1]).toBeGreaterThan((50.64 + 37.25) / 2);
  });

  it('日本—美國：經度差超過 180 度時走太平洋（跨換日線），路徑經度連續', () => {
    const a = conflictArc([143.3, 43.5], [-99.7, 37.25]);
    expect(a.path[a.path.length - 1][0]).toBeCloseTo(260.3, 1);
    for (let i = 1; i < a.path.length; i++) expect(Math.abs(a.path[i][0] - a.path[i - 1][0])).toBeLessThan(20);
    expect(a.mid[0]).toBeGreaterThan(180);
    expect(a.mid[0]).toBeLessThan(220);
  });

  it('緯度不超過 85 度', () => {
    const a = conflictArc([0, 80], [0.1, 84], 16, 3);
    for (const [, y] of a.path) expect(Math.abs(y)).toBeLessThanOrEqual(85);
  });

  it('worldShift：平移到離地圖中心最近的世界副本', () => {
    expect(worldShift(200, -100)).toBe(-360);
    expect(worldShift(-40, 10)).toBe(0);
    expect(worldShift(-170, 170)).toBe(360);
  });
});
