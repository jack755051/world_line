import { conflictArc, staggerOnArcs, worldShift, worldShiftArc } from './conflict-arc';

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

describe('staggerOnArcs（雙劍錯開）', () => {
  const line = (x0: number, y0: number, x1: number, y1: number, n = 48) =>
    Array.from({ length: n + 1 }, (_, i) => ({ x: x0 + ((x1 - x0) * i) / n, y: y0 + ((y1 - y0) * i) / n }));
  it('五條幾乎重疊的弧：中點雙劍沿各自弧線錯開，彼此至少相距 minDist，且都在自己的弧線上', () => {
    const paths = [0, 4, 8, 12, 16].map((dy) => line(0, 300, 600, 100 + dy));
    const items = paths.map((p) => ({ ...p[24], path: p }));
    const out = staggerOnArcs(items, 34);
    for (let i = 0; i < out.length; i++)
      for (let j = i + 1; j < out.length; j++) expect(Math.hypot(out[i].x - out[j].x, out[i].y - out[j].y)).toBeGreaterThanOrEqual(34);
    out.forEach((p, i) => expect(paths[i].some((q) => q.x === p.x && q.y === p.y)).toBe(true));
    expect(out[0]).toEqual(paths[0][24]); // 第一個留在中點
  });
  it('沒有弧線的圖示固定不動，有弧線的避開它', () => {
    const p = line(0, 0, 480, 0);
    const out = staggerOnArcs([{ x: 240, y: 0, path: null }, { x: 240, y: 0, path: p }], 34);
    expect(out[0]).toEqual({ x: 240, y: 0 });
    expect(Math.abs(out[1].x - 240)).toBeGreaterThanOrEqual(34);
  });
});

describe('可視區與世界副本', () => {
  it('中點在可視區外：雙劍改放弧線上離中點最近、仍在可視區內的點', () => {
    const p = Array.from({ length: 49 }, (_, i) => ({ x: i * 20, y: 100 }));
    const [o] = staggerOnArcs([{ ...p[24], path: p }], 34, 3, (q) => q.x <= 300);
    expect(o).toEqual({ x: 300, y: 100 });
  });
  it('worldShiftArc：日本(143)→珍珠港(202，展開後) 在中心 -96 時平移 -360，珍珠港端落在 -158', () => {
    const path: [number, number][] = [[143, 43], [172, 50], [202.05, 21.36]];
    const k = worldShiftArc(path, -96);
    expect(k).toBe(-360);
    expect(path[2][0] + k).toBeCloseTo(-157.95, 2);
    // 以被選政權（美國＝終點）為準：中心在 0 度（美國屬地跨換日線，外框是全世界）時也讓珍珠港端落在 -158
    expect(worldShiftArc(path, 0, 1)).toBe(-360);
  });
});
