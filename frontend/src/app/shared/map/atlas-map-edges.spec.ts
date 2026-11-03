import { CAPITAL_ANCHOR_OFFSET, EDGE_OBSTACLE_OUTSIDE_PX, edgeObstacleBoxes, obstacleGridFeatures } from './atlas-map';

describe('畫面邊障礙列（§4 (c)-6）', () => {
  it('四邊各一列，格子中心都在畫面外，往內最多蓋 4px', () => {
    const W = 1440, H = 732;
    const boxes = edgeObstacleBoxes(W, H);
    expect(boxes).toHaveLength(4);
    const cells = obstacleGridFeatures(boxes, ([x, y]) => [x, y]).map((f) => f.geometry.coordinates);
    for (const [x, y] of cells) {
      const outside = x < 0 || x > W || y < 0 || y > H;
      expect(outside).toBe(true);
      // 24px 格子、中心在外 8px → 往內最多 12 − 8 = 4px
      const inward = Math.max(0, x < 0 ? 12 + x : x > W ? 12 - (x - W) : 0, y < 0 ? 12 + y : y > H ? 12 - (y - H) : 0);
      expect(inward).toBeLessThanOrEqual(4);
    }
    const ys = cells.filter(([x, y]) => y < 0 && x > 0 && x < W).map(([, y]) => y);
    expect(new Set(ys)).toEqual(new Set([-EDGE_OBSTACLE_OUTSIDE_PX]));
    // 上緣一列要蓋滿整個寬度
    const xs = cells.filter(([, y]) => y === -EDGE_OBSTACLE_OUTSIDE_PX).map(([x]) => x);
    expect(Math.min(...xs)).toBeLessThanOrEqual(0);
    expect(Math.max(...xs)).toBeGreaterThanOrEqual(W);
  });
});

describe('首都名選邊（§4 (c)-6）', () => {
  it('偏好側優先，碰撞時翻到另一側', () => {
    const [, , , left, other] = CAPITAL_ANCHOR_OFFSET as unknown as [string, unknown, string, ['literal', unknown[]], ['literal', unknown[]]];
    expect(left[1][0]).toBe('right');
    expect(left[1][2]).toBe('left');
    expect(other[1][0]).toBe('left');
    expect(other[1][2]).toBe('right');
  });
});
