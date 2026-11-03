import { FeatureCollection } from 'geojson';
import {
  avoidCapitals, capitalObstacleBoxes, findLabelPlacement, gridCandidates,
  CAPITAL_DOT_RADIUS, CAPITAL_DOT_STROKE, CAPITAL_DOT_GAP,
  CAP_LABEL_H,
  LABEL_CHAR_PX, LABEL_H, LABEL_PAD, LABEL_SMALL_CHAR_PX, LABEL_SMALL_H,
  VIEWPORT_MARGIN, measureLabelWidth, clearLabelWidthCache,
  pointInProjectedRing, rectsOverlap,
} from './label-placement';

/** 單點 GeoJSON helper */
const oneCapital = (lng: number, lat: number, label = 'AB'): FeatureCollection => ({
  type: 'FeatureCollection',
  features: [{ type: 'Feature', geometry: { type: 'Point', coordinates: [lng, lat] }, properties: { label } }],
});

/** 恆等投影（直接用 lng/lat 當像素，方便計算）*/
const identityProject = (lngLat: [number, number]) => ({ x: lngLat[0], y: lngLat[1] });

/** 預期圓點障礙尺寸（px）。 */
const DOT_OBS_SIZE = (CAPITAL_DOT_RADIUS + CAPITAL_DOT_STROKE + CAPITAL_DOT_GAP) * 2; // 16

describe('rectsOverlap', () => {
  it('中心重疊的矩形回傳 true', () => {
    expect(rectsOverlap({ x: 0, y: 0, w: 10, h: 10 }, { x: 5, y: 5, w: 10, h: 10 })).toBe(true);
  });

  it('完全分離的矩形回傳 false', () => {
    expect(rectsOverlap({ x: 0, y: 0, w: 10, h: 10 }, { x: 20, y: 20, w: 10, h: 10 })).toBe(false);
  });

  it('邊緣恰好相接（不重疊）回傳 false', () => {
    expect(rectsOverlap({ x: 0, y: 0, w: 10, h: 10 }, { x: 10, y: 0, w: 10, h: 10 })).toBe(false);
  });
});

describe('capitalObstacleBoxes', () => {
  it('capitals 為 null 時回傳空陣列', () => {
    expect(capitalObstacleBoxes(null, identityProject, 0, 5)).toEqual([]);
  });

  it('zoom < 3.5 只產生圓點框（含間距的 DOT_OBS_SIZE×DOT_OBS_SIZE）', () => {
    const boxes = capitalObstacleBoxes(oneCapital(10, 20), identityProject, 0, 3);
    expect(boxes).toHaveLength(1);
    expect(boxes[0]).toEqual({ x: 10, y: 20, w: DOT_OBS_SIZE, h: DOT_OBS_SIZE });
  });

  it('圓點障礙框比舊版（10px）更大，確保含描邊與間距', () => {
    const boxes = capitalObstacleBoxes(oneCapital(0, 0), identityProject, 0, 3);
    // DOT_OBS_SIZE = 16 > 10（舊版），確保半徑+描邊+間距都被包含
    expect(boxes[0].w).toBeGreaterThan(10);
    expect(boxes[0].h).toBeGreaterThan(10);
    expect(boxes[0].w).toBe(DOT_OBS_SIZE);
  });

  it('zoom >= 3.5 產生圓點框與左右兩個名稱框（共 3 個）', () => {
    const boxes = capitalObstacleBoxes(oneCapital(10, 20, 'AB'), identityProject, 0, 4);
    expect(boxes).toHaveLength(3);
    // 圓點框含間距
    expect(boxes[0]).toEqual({ x: 10, y: 20, w: DOT_OBS_SIZE, h: DOT_OBS_SIZE });
    // 右側名稱框：x 大於圓點中心，與圓點同高，高度 = CAP_LABEL_H（不膨脹）
    expect(boxes[1].x).toBeGreaterThan(10);
    expect(boxes[1].y).toBe(20);
    expect(boxes[1].h).toBe(CAP_LABEL_H);
    expect(boxes[1].w).toBeGreaterThan(0);
    // 左側名稱框：x 小於圓點中心，與右側對稱
    expect(boxes[2].x).toBeLessThan(10);
    expect(boxes[2].y).toBe(20);
    expect(boxes[2].w).toBe(boxes[1].w); // 左右對稱
    expect(boxes[2].h).toBe(CAP_LABEL_H);
  });

  it('名稱框高度精確（CAP_LABEL_H=16），使 dy=±18 的 HTML 標籤恰好不碰撞', () => {
    // 圓點在 (0,0)；HTML 國名標籤 w=148, h=20，dy=18
    // rectsOverlap 條件：|dy|*2=36 < h1+h2=20+16=36 → false（恰好不重疊）
    const boxes = capitalObstacleBoxes(oneCapital(0, 0, 'Praha'), identityProject, 0, 4);
    const rightBox = boxes[1]; // right side
    const nationalLabel = { x: 0, y: 18, w: 148, h: 20 };
    expect(rectsOverlap(nationalLabel, rightBox)).toBe(false);
    const leftBox = boxes[2];
    expect(rectsOverlap(nationalLabel, leftBox)).toBe(false);
  });

  it('世界副本：取離地圖中心最近的副本', () => {
    const boxes = capitalObstacleBoxes(oneCapital(-170, 0, 'A'), identityProject, 170, 3);
    expect(boxes[0].x).toBeCloseTo(190, 1);
  });

  it('非 Point 幾何的 feature 被略過', () => {
    const fc: FeatureCollection = {
      type: 'FeatureCollection',
      features: [{ type: 'Feature', geometry: { type: 'LineString', coordinates: [[0, 0], [1, 1]] }, properties: {} }],
    };
    expect(capitalObstacleBoxes(fc, identityProject, 0, 5)).toHaveLength(0);
  });
});

describe('measureLabelWidth', () => {
  beforeEach(() => clearLabelWidthCache());

  it('相同文字相同字級回傳一致結果（有快取）', () => {
    const w1 = measureLabelWidth('Poland', false);
    const w2 = measureLabelWidth('Poland', false);
    expect(w1).toBe(w2);
    expect(w1).toBeGreaterThan(0);
  });

  it('一般字體比縮小字體寬（相同文字）', () => {
    const wNormal = measureLabelWidth('Poland', false);
    const wSmall = measureLabelWidth('Poland', true);
    expect(wNormal).toBeGreaterThan(wSmall);
  });

  it('較長文字比較短文字寬', () => {
    const wShort = measureLabelWidth('AB', false);
    const wLong = measureLabelWidth('ABCDEFGH', false);
    expect(wLong).toBeGreaterThan(wShort);
  });

  it('包含 padding：空字串仍有最小寬度', () => {
    const w = measureLabelWidth('', false);
    // 至少含 padding（canvas 路徑 ≥12px；fallback 路徑 = LABEL_PAD = 8px）
    expect(w).toBeGreaterThanOrEqual(LABEL_PAD);
  });
});

describe('avoidCapitals', () => {
  it('未重疊時不動：回傳 0', () => {
    const dy = avoidCapitals(100, 100, 20, 14, []);
    expect(dy).toBe(0);
  });

  it('重疊時位移：重疊時找到非零的可用位移', () => {
    const obs = [{ x: 100, y: 100, w: 10, h: 10 }];
    const dy = avoidCapitals(100, 100, 20, 14, obs);
    expect(dy).not.toBeNull();
    expect(dy).not.toBe(0);
    const resultBox = { x: 100, y: 100 + dy!, w: 20, h: 14 };
    expect(obs.some((o) => rectsOverlap(resultBox, o))).toBe(false);
  });

  it('無法位移時隱藏：所有 shifts 都重疊時回傳 null', () => {
    const obs = [{ x: 100, y: 100, w: 200, h: 200 }];
    const dy = avoidCapitals(100, 100, 20, 14, obs, [0, -18, 18, -30, 30]);
    expect(dy).toBeNull();
  });

  it('自訂 shifts 清單：只在指定位移中選擇', () => {
    const obs = [{ x: 100, y: 100, w: 10, h: 10 }];
    const dy = avoidCapitals(100, 100, 20, 14, obs, [50]);
    expect(dy).toBe(50);
  });
});

describe('avoidCapitals 作為通用位移查找（標籤互撞）', () => {
  it('兩標籤重疊：後放者以已放置 box 為障礙找位移', () => {
    const placedBoxes = [{ x: 100, y: 100, w: 80, h: 20 }];
    const dy = avoidCapitals(100, 100, 80, 20, placedBoxes);
    expect(dy).not.toBeNull();
    expect(dy).not.toBe(0);
    const result = { x: 100, y: 100 + dy!, w: 80, h: 20 };
    expect(placedBoxes.some((b) => rectsOverlap(result, b))).toBe(false);
  });

  it('無空位時略去：所有 shifts 都與已放置標籤重疊時回傳 null', () => {
    const placedBoxes = [{ x: 100, y: 100, w: 400, h: 400 }];
    const dy = avoidCapitals(100, 100, 80, 20, placedBoxes, [0, -18, 18, -30, 30]);
    expect(dy).toBeNull();
  });

  it('控制區優先：先放控制區可佔原位，後放的國名標籤須位移', () => {
    const placedBoxes: { x: number; y: number; w: number; h: number }[] = [];
    const controlDy = avoidCapitals(100, 100, 80, 20, placedBoxes);
    expect(controlDy).toBe(0);
    placedBoxes.push({ x: 100, y: 100 + controlDy!, w: 80, h: 20 });
    const countryDy = avoidCapitals(100, 100, 80, 20, placedBoxes);
    expect(countryDy).not.toBeNull();
    expect(countryDy).not.toBe(0);
  });
});

// ─── 新函式測試 ───────────────────────────────────────────────────────────────

describe('pointInProjectedRing', () => {
  const square = [
    { x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 },
  ];

  it('正方形中心在內', () => {
    expect(pointInProjectedRing(50, 50, square)).toBe(true);
  });

  it('正方形外的點在外', () => {
    expect(pointInProjectedRing(150, 50, square)).toBe(false);
    expect(pointInProjectedRing(50, 150, square)).toBe(false);
  });

  it('頂點邊界附近（角點外）', () => {
    expect(pointInProjectedRing(-1, -1, square)).toBe(false);
  });

  it('環長度不足 3 回傳 false', () => {
    expect(pointInProjectedRing(5, 5, [{ x: 0, y: 0 }, { x: 10, y: 0 }])).toBe(false);
  });
});

describe('gridCandidates', () => {
  const squareRing = [[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]];
  const center = { x: 50, y: 50 };

  it('所有回傳點都在多邊形內', () => {
    const pts = gridCandidates(squareRing, identityProject, center, 200, 200);
    expect(pts.length).toBeGreaterThan(0);
    const projRing = squareRing.map(([x, y]) => ({ x, y }));
    for (const { x, y } of pts) {
      expect(pointInProjectedRing(x, y, projRing)).toBe(true);
    }
  });

  it('依離 labelPx 由近到遠排序', () => {
    const pts = gridCandidates(squareRing, identityProject, center, 200, 200);
    expect(pts.length).toBeGreaterThan(1);
    const dist2 = (p: { x: number; y: number }) => (p.x - center.x) ** 2 + (p.y - center.y) ** 2;
    for (let i = 1; i < pts.length; i++) {
      expect(dist2(pts[i])).toBeGreaterThanOrEqual(dist2(pts[i - 1]));
    }
  });

  it('超出地圖可視範圍（含 4px 邊距）的點被過濾', () => {
    // 地圖只有 60×60，正方形右半超出邊界（減去 4px margin 後為 56px）
    const pts = gridCandidates(squareRing, identityProject, center, 60, 60);
    for (const { x, y } of pts) {
      expect(x).toBeLessThanOrEqual(60 - VIEWPORT_MARGIN);
      expect(y).toBeLessThanOrEqual(60 - VIEWPORT_MARGIN);
      expect(x).toBeGreaterThanOrEqual(VIEWPORT_MARGIN);
      expect(y).toBeGreaterThanOrEqual(VIEWPORT_MARGIN);
    }
  });

  it('回傳數量上限 maxCandidates', () => {
    const pts = gridCandidates(squareRing, identityProject, center, 200, 200, 10, 3);
    expect(pts.length).toBeLessThanOrEqual(3);
  });

  it('環少於 3 個頂點回傳空陣列', () => {
    expect(gridCandidates([[0, 0], [1, 0]], identityProject, center, 200, 200)).toHaveLength(0);
  });
});

describe('findLabelPlacement', () => {
  // 使用預計算寬度（對應 textLen=5 的舊公式）
  const textLen = 5;
  const fullW = textLen * LABEL_CHAR_PX + LABEL_PAD;   // 5*14+8 = 78
  const smallW = textLen * LABEL_SMALL_CHAR_PX + LABEL_PAD; // 5*12+8 = 68

  it('無障礙時回傳 labelPoint，small=false', () => {
    const r = findLabelPlacement(100, 100, fullW, [], []);
    expect(r).not.toBeNull();
    expect(r!.x).toBe(100);
    expect(r!.y).toBe(100);
    expect(r!.small).toBe(false);
  });

  it('UI 障礙（大方塊蓋住 shifts）時使用網格候選點', () => {
    const bigObs = [{ x: 100, y: 100, w: fullW + 10, h: 140 }];
    const gridPts = [{ x: 200, y: 200 }];
    const r = findLabelPlacement(100, 100, fullW, bigObs, gridPts);
    expect(r).not.toBeNull();
    expect(r!.x).toBe(200);
    expect(r!.y).toBe(200);
    expect(r!.small).toBe(false);
  });

  it('一般字體全部失敗時回退縮小字體（small=true）', () => {
    // 障礙中心在 x=137，與 labelPoint x=100 距離 37px
    //   一般字體 fullW=78：37*2=74 < 78+2=80 → 重疊
    //   縮小字體 smallW=68：74 < 68+2=70 → 不重疊（可放置，small=true）
    // 高度 200px 確保所有 shifts 都被 y 方向覆蓋
    const narrowXObs = [{ x: 137, y: 100, w: 2, h: 200 }];
    const r = findLabelPlacement(100, 100, fullW, narrowXObs, []);
    expect(r).not.toBeNull();
    expect(r!.small).toBe(true);
    const box = { x: r!.x, y: r!.y, w: smallW, h: LABEL_SMALL_H };
    expect(narrowXObs.some((o) => rectsOverlap(box, o))).toBe(false);
  });

  it('所有候選（含縮小字）都撞時回傳 null', () => {
    const hugeObs = [{ x: 100, y: 100, w: 10000, h: 10000 }];
    const r = findLabelPlacement(100, 100, fullW, hugeObs, []);
    expect(r).toBeNull();
  });

  it('capitalOnlyObs 最後手段：全部障礙擋住但首都障礙不擋時可放置', () => {
    // 大障礙物蓋住所有位置（含國名、UI 等），但首都障礙集只有一個小圓點框不在候選位置上
    const hugeObs = [{ x: 100, y: 100, w: 10000, h: 10000 }];
    const capitalOnlyObs = [{ x: 200, y: 200, w: 16, h: 16 }]; // 首都在別處
    // 大障礙（hugeObs）阻止所有正常放置，但 capitalOnlyObs 不擋 cx,cy±shifts
    const r = findLabelPlacement(100, 100, fullW, hugeObs, [], undefined, Infinity, Infinity, capitalOnlyObs);
    // shifts=[0,-18,18,-30,30] 都不與 capitalOnlyObs 碰撞 → 應有結果
    expect(r).not.toBeNull();
    expect(r!.small).toBe(true); // 階段 5 只用縮小字
  });

  it('capitalOnlyObs 最後手段：首都也擋住時回傳 null', () => {
    const hugeObs = [{ x: 100, y: 100, w: 10000, h: 10000 }];
    const capitalOnlyObs = [{ x: 100, y: 100, w: 10000, h: 10000 }]; // 首都障礙也很大
    const r = findLabelPlacement(100, 100, fullW, hugeObs, [], undefined, Infinity, Infinity, capitalOnlyObs);
    expect(r).toBeNull();
  });

  it('網格候選點避讓 UI 障礙物（整合場景）', () => {
    const legendObs = [{ x: 140, y: 700, w: 280 + 12, h: 300 + 12 }];
    const gridPts = [{ x: 400, y: 400 }];
    const r = findLabelPlacement(140, 700, fullW, legendObs, gridPts);
    expect(r).not.toBeNull();
    expect(r!.x).toBe(400);
    expect(r!.y).toBe(400);
  });

  it('標籤框超出視窗左邊界（4px）的候選被略過', () => {
    // cx=10, labelW=80 → shift=0: left edge=10-40=-30 < 4 → 不符合視窗邊界
    // gridPt at (50,300) → left edge=10, right edge=90 → fits in 100px wide map
    const gridPts = [{ x: 50, y: 300 }];
    const r = findLabelPlacement(10, 300, 80, [], gridPts, undefined, 100, 600);
    expect(r).not.toBeNull();
    expect(r!.x).toBe(50);
  });

  it('標籤框超出視窗右邊界（4px）的候選被略過', () => {
    // mapW=100, cx=95, labelW=80 → right edge=95+40=135 > 96 → 不符合
    // shift=0,-18,18,-30,30 都超出右邊界
    const r = findLabelPlacement(95, 300, 80, [], [], undefined, 100, 600);
    // 全部超出，回傳 null
    expect(r).toBeNull();
  });
});
