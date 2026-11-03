import type { Geometry } from 'geojson';
import { focusMaskPath, focusPadding, geometryBounds, polygonRings, sheetLayout } from './focus';

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

  it('面板位置：桌面右側（最多 384px），窄螢幕底部', () => {
    expect(sheetLayout(1280, 700)).toEqual({ side: 'right', size: 384 });
    expect(sheetLayout(700, 500)).toEqual({ side: 'right', size: 384 });
    expect(sheetLayout(400, 600)).toEqual({ side: 'bottom', size: 330 });
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
