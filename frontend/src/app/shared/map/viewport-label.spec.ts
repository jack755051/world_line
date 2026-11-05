import { clipRing, fromWorld, geometryPieces, placeInViewport, polylabel, ringArea, simplifyRing, labelBoxPx, toWorld, type Ring } from './viewport-label';

const sq = (x: number, y: number, s: number): Ring => [[x, y], [x + s, y], [x + s, y + s], [x, y + s], [x, y]];

describe('viewport-label（國名依視窗定位）', () => {
  it('toWorld／fromWorld 互逆', () => {
    const [x, y] = toWorld(30, 50);
    const [lng, lat] = fromWorld(x, y);
    expect(lng).toBeCloseTo(30, 6);
    expect(lat).toBeCloseTo(50, 6);
  });
  it('clipRing 裁成矩形內的部分', () => {
    const r = clipRing(sq(0, 0, 10), [5, 0, 20, 20]);
    expect(ringArea(r)).toBeCloseTo(50, 6);
  });
  it('polylabel：正方形取中心、L 形取粗的那一段', () => {
    const p = polylabel([sq(0, 0, 10)], 0.01);
    expect(p.pt[0]).toBeCloseTo(5, 1);
    expect(p.pt[1]).toBeCloseTo(5, 1);
    const L: Ring = [[0, 0], [10, 0], [10, 2], [2, 2], [2, 10], [0, 10], [0, 0]];
    const q = polylabel([L], 0.01);
    expect(q.dist).toBeGreaterThan(0.9);
  });
  it('多塊國土：取「可見範圍內」面積最大的那塊（殖民地一律）', () => {
    // 兩塊：大塊在畫面外，小塊在畫面內 → 用小塊
    const pieces = [
      { rings: [sq(0.0, 0.4, 0.2)], bbox: [0.0, 0.4, 0.2, 0.6] as [number, number, number, number] },
      { rings: [sq(0.6, 0.4, 0.05)], bbox: [0.6, 0.4, 0.65, 0.45] as [number, number, number, number] },
    ];
    const v = placeInViewport(pieces, [0.5, 0.3, 0.9, 0.7], 2048)!;
    const [x] = toWorld(v.lngLat[0], v.lngLat[1]);
    expect(x).toBeGreaterThan(0.6);
    expect(v.widthPx).toBeCloseTo(0.05 * 2048, 3);
  });
  it('大塊只露出一部分時，點落在露出的部分內', () => {
    const pieces = [{ rings: [sq(0.2, 0.2, 0.6)], bbox: [0.2, 0.2, 0.8, 0.8] as [number, number, number, number] }];
    const v = placeInViewport(pieces, [0.6, 0.0, 1.0, 1.0], 1024)!;
    const [x] = toWorld(v.lngLat[0], v.lngLat[1]);
    expect(x).toBeGreaterThan(0.6);
    expect(x).toBeLessThan(0.8);
    expect(v.widthPx).toBeCloseTo(0.2 * 1024, 3);
  });
  it('跨世界副本：畫面在世界右側外延時也找得到', () => {
    const pieces = [{ rings: [sq(0.05, 0.4, 0.1)], bbox: [0.05, 0.4, 0.15, 0.5] as [number, number, number, number] }];
    expect(placeInViewport(pieces, [0.95, 0.3, 1.2, 0.6], 1024)).not.toBeNull();
  });
  it('完全不可見 → null', () => {
    const pieces = geometryPieces({ type: 'Polygon', coordinates: [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]] });
    expect(placeInViewport(pieces, [0.9, 0.0, 0.95, 0.1], 1024)).toBeNull();
  });
});

describe('viewport-label：避開 UI 與簡化', () => {
  it('polylabel 避開 UI 矩形：點不落在圖例下', () => {
    const p = polylabel([sq(0, 0, 10)], 0.01, [[0, 0, 6, 10]]);
    expect(p.pt[0]).toBeGreaterThan(6);
  });
  it('可見塊全被 UI 蓋住 → clearPx ≤ 0', () => {
    const pieces = [{ rings: [sq(0.4, 0.4, 0.1)], bbox: [0.4, 0.4, 0.5, 0.5] as [number, number, number, number] }];
    const v = placeInViewport(pieces, [0, 0, 1, 1], 1024, [[0.3, 0.3, 0.6, 0.6]])!;
    expect(v.clearPx).toBeLessThanOrEqual(0);
  });
  it('simplifyRing 去掉過密的點但保留首尾', () => {
    const r: Ring = Array.from({ length: 101 }, (_, i) => [i / 1000, 0] as [number, number]);
    const s = simplifyRing(r, 0.01);
    expect(s.length).toBeLessThan(20);
    expect(s[0]).toEqual(r[0]);
    expect(s[s.length - 1]).toEqual(r[100]);
  });
});

describe('viewport-label：依名字框長寬定位', () => {
  it('橫長名字在「上寬下窄」的 T 形裡放在寬的那一段', () => {
    // 上方橫條 0.1~0.9 × 0.1~0.2；下方直條 0.45~0.55 × 0.2~0.9
    const T: Ring = [[0.1, 0.1], [0.9, 0.1], [0.9, 0.2], [0.55, 0.2], [0.55, 0.9], [0.45, 0.9], [0.45, 0.2], [0.1, 0.2], [0.1, 0.1]];
    const pieces = [{ rings: [T], bbox: [0.1, 0.1, 0.9, 0.9] as [number, number, number, number] }];
    const v = placeInViewport(pieces, [0, 0, 1, 1], 1000, [], { w: 300, h: 20 })!;
    const [, y] = toWorld(v.lngLat[0], v.lngLat[1]);
    expect(y).toBeLessThan(0.2);
  });
  it('名字框不超出畫面左右', () => {
    const pieces = [{ rings: [sq(0.0, 0.4, 0.2)], bbox: [0.0, 0.4, 0.2, 0.6] as [number, number, number, number] }];
    const v = placeInViewport(pieces, [0.15, 0.3, 0.6, 0.7], 1000, [], { w: 100, h: 20 })!;
    const [x] = toWorld(v.lngLat[0], v.lngLat[1]);
    expect(x).toBeGreaterThanOrEqual(0.15 + 0.05 - 1e-9);
  });
});

describe('viewport-label：上下不超出畫面與實際行數（M1-i-B）', () => {
  it('名字框不超出畫面上下', () => {
    const pieces = [{ rings: [sq(0.2, 0.0, 0.4)], bbox: [0.2, 0.0, 0.6, 0.4] as [number, number, number, number] }];
    // 畫面上緣切在 0.39 → 可見塊只剩一條 0.01 高的帶（10px），名字高 20px → 中心不得高於上緣 + 10px
    const v = placeInViewport(pieces, [0.0, 0.39, 1.0, 0.9], 1000, [], { w: 60, h: 20 })!;
    const [, y] = toWorld(v.lngLat[0], v.lngLat[1]);
    expect(y).toBeGreaterThanOrEqual(0.39 + 0.01 - 1e-9);
  });
  it('labelBoxPx：一行與兩行', () => {
    expect(labelBoxPx(100, 120, 15, { x: 6, y: 3 })).toEqual({ w: 112, h: 21, lines: 1 });
    const two = labelBoxPx(200, 120, 15, { x: 6, y: 3 });
    expect(two.lines).toBe(2);
    expect(two.h).toBe(36);
    expect(two.w).toBeLessThan(200);
  });
});
