import type { Geometry } from 'geojson';
import { focusMaskPath, focusPadding, geometryBounds, measuredPadding, polygonRings, sheetLayout } from './focus';

const square = (x: number, y: number, s: number) => [[x, y], [x + s, y], [x + s, y + s], [x, y + s], [x, y]];
const multi: Geometry = { type: 'MultiPolygon', coordinates: [[square(0, 0, 10), square(2, 2, 2)], [[...square(20, 5, 1)]]] };

describe('政權聚焦（focus.ts）', () => {
  it('取出所有環（含洞與飛地）並算外框', () => {
    expect(polygonRings(multi)).toHaveLength(3);
    expect(polygonRings({ type: 'Point', coordinates: [0, 0] })).toEqual([]);
    expect(geometryBounds(multi)).toEqual([[0, 0], [21, 10]]);
    expect(geometryBounds(null)).toBeNull();
  });

  it('遮罩路徑：先畫整個地圖區，再畫各環；太近的點略過、不足三點的環不畫', () => {
    const d = focusMaskPath(polygonRings(multi), ([x, y]) => ({ x: x * 10, y: y * 10 }), 800, 600);
    expect(d.startsWith('M0 0H800V600H0Z')).toBe(true);
    expect(d.match(/Z/g)).toHaveLength(4); // 矩形＋外環＋洞＋飛地
    const tiny = focusMaskPath([square(0, 0, 0.01)], ([x, y]) => ({ x, y }), 100, 100);
    expect(tiny).toBe('M0 0H100V100H0Z');
  });

  it('置中邊距扣掉右側面板；空間不夠時等比縮小', () => {
    expect(focusPadding({ right: 384, bottom: 0 }, 1280, 700)).toEqual({ top: 48, right: 432, bottom: 48, left: 48 });
    const p = focusPadding({ right: 384, bottom: 0 }, 500, 400);
    expect(500 - p.left - p.right).toBeGreaterThanOrEqual(120);
    expect(focusPadding({ right: 0, bottom: 300 }, 400, 600).bottom).toBe(348);
  });

  it('面板寬度（§10 v2 W1）：≥1440 寬 432；1024–1439 寬 384；768–1023 寬 360 蓋在地圖上；<768 底部三段高度；都不能拖拉', () => {
    expect(sheetLayout(1440, 900)).toEqual({ side: 'right', size: 432, overlay: false });
    expect(sheetLayout(1920, 900)).toMatchObject({ size: 432 });
    expect(sheetLayout(1439, 900)).toEqual({ side: 'right', size: 384, overlay: false });
    expect(sheetLayout(1024, 900)).toMatchObject({ size: 384 });
    expect(sheetLayout(1023, 900)).toEqual({ side: 'right', size: 360, overlay: true });
    expect(sheetLayout(768, 900)).toMatchObject({ size: 360 });
    expect(sheetLayout(767, 800)).toEqual({ side: 'bottom', size: 400, overlay: false });
    expect(sheetLayout(400, 800, 'peek')).toMatchObject({ size: 96 });
    expect(sheetLayout(400, 800, 'full')).toMatchObject({ size: 720 });
    expect(sheetLayout(400, 800, 'full', 600)).toMatchObject({ size: 600 });
  });

  it('measuredPadding：圖例展開時左側加到圖例右緣＋16；sheet 量到時右側取最大值；量不到時不變', () => {
    const base = focusPadding({ right: 384, bottom: 0 }, 1280, 700); // {top:48, right:432, bottom:48, left:48}
    // 圖例右緣 = 200，在容器內，剩餘寬度 1280-216-432=632 ≥ 200 → left=216
    expect(measuredPadding(base, 1280, 200, true, null).left).toBe(216);
    // 圖例在容器外（legendInBounds=false）→ left 不變
    expect(measuredPadding(base, 1280, 200, false, null).left).toBe(48);
    // 圖例讓完後剩餘寬度不足 200（legendRight=640）→ left 不動
    expect(measuredPadding(base, 1280, 640, true, null).left).toBe(48);
    // sheet 量到（gap=400）→ right = max(432, 400+48) = 448
    expect(measuredPadding(base, 1280, null, false, 400).right).toBe(448);
    // sheet gap < base.right（gap=100）→ right 不變（max(432, 148)=432）
    expect(measuredPadding(base, 1280, null, false, 100).right).toBe(432);
    // sheet 量不到（null）→ right 不變
    expect(measuredPadding(base, 1280, null, false, null).right).toBe(432);
  });

  it('override bounds 優先：有 override 時用 override，否則退回 feature bounds', () => {
    const featureBounds = geometryBounds(multi); // [[0,0],[21,10]]
    // override 非 null：cameraBounds = overrideBounds ?? featureBounds → override
    const override = geometryBounds({ type: 'Polygon', coordinates: [[[5, 5], [10, 5], [10, 10], [5, 10], [5, 5]]] });
    expect(override ?? featureBounds).toEqual([[5, 5], [10, 10]]);
    // override 為 null（無傳入）：退回 feature bounds
    const noOverride = geometryBounds(null);
    expect(noOverride ?? featureBounds).toEqual([[0, 0], [21, 10]]);
  });
});
