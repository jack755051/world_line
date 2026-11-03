import type { FeatureCollection } from 'geojson';
import {
  avoidCapitals, capitalObstacleBoxes, findLabelPlacement, gridCandidates,
  LABEL_CHAR_PX, LABEL_H, LABEL_PAD, LABEL_SMALL_CHAR_PX, LABEL_SMALL_H,
  pointInProjectedRing, rectsOverlap,
} from './label-placement';

/** 單點 GeoJSON helper */
const oneCapital = (lng: number, lat: number, label = 'AB'): FeatureCollection => ({
  type: 'FeatureCollection',
  features: [{ type: 'Feature', geometry: { type: 'Point', coordinates: [lng, lat] }, properties: { label } }],
});

/** 恆等投影（直接用 lng/lat 當像素，方便計算）*/
const identityProject = (lngLat: [number, number]) => ({ x: lngLat[0], y: lngLat[1] });

describe('rectsOverlap', () => {
  it('中心重疊的矩形回傳 true', () => {
    expect(rectsOverlap({ x: 0, y: 0, w: 10, h: 10 }, { x: 5, y: 5, w: 10, h: 10 })).toBe(true);
  });

  it('完全分離的矩形回傳 false', () => {
    expect(rectsOverlap({ x: 0, y: 0, w: 10, h: 10 }, { x: 20, y: 20, w: 10, h: 10 })).toBe(false);
  });

  it('邊緣恰好相接（不重疊）回傳 false', () => {
    // x 差 = 10，w/2+w/2 = 10 → 剛好不重疊
    expect(rectsOverlap({ x: 0, y: 0, w: 10, h: 10 }, { x: 10, y: 0, w: 10, h: 10 })).toBe(false);
  });
});

describe('capitalObstacleBoxes', () => {
  it('capitals 為 null 時回傳空陣列', () => {
    expect(capitalObstacleBoxes(null, identityProject, 0, 5)).toEqual([]);
  });

  it('zoom < 3.5 只產生圓點框（10×10）', () => {
    const boxes = capitalObstacleBoxes(oneCapital(10, 20), identityProject, 0, 3);
    expect(boxes).toHaveLength(1);
    expect(boxes[0]).toEqual({ x: 10, y: 20, w: 10, h: 10 });
  });

  it('zoom >= 3.5 同時產生圓點框與名稱框', () => {
    const boxes = capitalObstacleBoxes(oneCapital(10, 20, 'AB'), identityProject, 0, 4);
    expect(boxes).toHaveLength(2);
    // 圓點框
    expect(boxes[0]).toEqual({ x: 10, y: 20, w: 10, h: 10 });
    // 名稱框在圓點右側（x 應大於圓點中心）
    expect(boxes[1].x).toBeGreaterThan(10);
    expect(boxes[1].h).toBe(14);
  });

  it('世界副本：取離地圖中心最近的副本', () => {
    // 首都在 lng=-170，地圖中心在 170 → 最近副本為 -170+360=190
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

describe('avoidCapitals', () => {
  it('未重疊時不動：回傳 0', () => {
    const dy = avoidCapitals(100, 100, 20, 14, []);
    expect(dy).toBe(0);
  });

  it('重疊時位移：重疊時找到非零的可用位移', () => {
    // 小型障礙物置中於 (100, 100)：shift=0 時重疊，shift=-18 時跳脫
    const obs = [{ x: 100, y: 100, w: 10, h: 10 }];
    const dy = avoidCapitals(100, 100, 20, 14, obs);
    expect(dy).not.toBeNull();
    expect(dy).not.toBe(0);
    // 驗證返回位置確實不重疊
    const resultBox = { x: 100, y: 100 + dy!, w: 20, h: 14 };
    expect(obs.some((o) => rectsOverlap(resultBox, o))).toBe(false);
  });

  it('無法位移時隱藏：所有 shifts 都重疊時回傳 null', () => {
    // 一個超大障礙物覆蓋所有候選位移範圍（[-30, 30] + 半高度 margin）
    const obs = [{ x: 100, y: 100, w: 200, h: 200 }];
    const dy = avoidCapitals(100, 100, 20, 14, obs, [0, -18, 18, -30, 30]);
    expect(dy).toBeNull();
  });

  it('自訂 shifts 清單：只在指定位移中選擇', () => {
    const obs = [{ x: 100, y: 100, w: 10, h: 10 }];
    // 只允許 shift=50（不重疊）
    const dy = avoidCapitals(100, 100, 20, 14, obs, [50]);
    expect(dy).toBe(50);
  });
});

describe('avoidCapitals 作為通用位移查找（標籤互撞）', () => {
  it('兩標籤重疊：後放者以已放置 box 為障礙找位移', () => {
    // 第一個標籤已放在 (100, 100)，占 80×20
    const placedBoxes = [{ x: 100, y: 100, w: 80, h: 20 }];
    // 第二個標籤中心也在 (100, 100)，與第一個重疊 → 必須位移
    const dy = avoidCapitals(100, 100, 80, 20, placedBoxes);
    expect(dy).not.toBeNull();
    expect(dy).not.toBe(0);
    // 驗證位移後確實不重疊
    const result = { x: 100, y: 100 + dy!, w: 80, h: 20 };
    expect(placedBoxes.some((b) => rectsOverlap(result, b))).toBe(false);
  });

  it('無空位時略去：所有 shifts 都與已放置標籤重疊時回傳 null', () => {
    // 超大障礙物覆蓋所有候選位移範圍
    const placedBoxes = [{ x: 100, y: 100, w: 400, h: 400 }];
    const dy = avoidCapitals(100, 100, 80, 20, placedBoxes, [0, -18, 18, -30, 30]);
    expect(dy).toBeNull();
  });

  it('控制區優先：先放控制區可佔原位，後放的國名標籤須位移', () => {
    const placedBoxes: { x: number; y: number; w: number; h: number }[] = [];

    // 控制區標籤（優先放置）：無既有障礙 → shift=0 即可
    const controlDy = avoidCapitals(100, 100, 80, 20, placedBoxes);
    expect(controlDy).toBe(0);
    placedBoxes.push({ x: 100, y: 100 + controlDy!, w: 80, h: 20 });

    // 國名標籤（次優先）：與控制區標籤重疊 → 必須找非零位移
    const countryDy = avoidCapitals(100, 100, 80, 20, placedBoxes);
    expect(countryDy).not.toBeNull();
    expect(countryDy).not.toBe(0);
  });
});

// ─── 新函式測試 ───────────────────────────────────────────────────────────────

describe('pointInProjectedRing', () => {
  // 100×100 正方形（原點到 (100,100)）
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
  // 100×100 正方形（lng/lat），使用恆等投影
  const squareRing = [[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]];
  const center = { x: 50, y: 50 };

  it('所有回傳點都在多邊形內', () => {
    const pts = gridCandidates(squareRing, identityProject, center, 200, 200);
    expect(pts.length).toBeGreaterThan(0);
    // 恆等投影下，點在像素環內等同在 lng/lat 環內
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

  it('超出地圖可視範圍的點被過濾', () => {
    // 地圖只有 60×60，正方形右半超出邊界 → 應只保留 x,y < 60 的點
    const pts = gridCandidates(squareRing, identityProject, center, 60, 60);
    for (const { x, y } of pts) {
      expect(x).toBeLessThanOrEqual(60);
      expect(y).toBeLessThanOrEqual(60);
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
  const textLen = 5;
  const fullW = textLen * LABEL_CHAR_PX + LABEL_PAD;
  const smallW = textLen * LABEL_SMALL_CHAR_PX + LABEL_PAD;

  it('無障礙時回傳 labelPoint，small=false', () => {
    const r = findLabelPlacement(100, 100, textLen, [], []);
    expect(r).not.toBeNull();
    expect(r!.x).toBe(100);
    expect(r!.y).toBe(100);
    expect(r!.small).toBe(false);
  });

  it('UI 障礙（大方塊蓋住 shifts）時使用網格候選點', () => {
    // 大障礙物蓋住所有 shifts（中心在 (100,100)，寬高足以蓋 [100-18,100+30]）
    const bigObs = [{ x: 100, y: 100, w: fullW + 10, h: 140 }];
    // 網格候選點在 (200, 200)，不與障礙重疊
    const gridPts = [{ x: 200, y: 200 }];
    const r = findLabelPlacement(100, 100, textLen, bigObs, gridPts);
    expect(r).not.toBeNull();
    expect(r!.x).toBe(200);
    expect(r!.y).toBe(200);
    expect(r!.small).toBe(false);
  });

  it('一般字體全部失敗時回退縮小字體（small=true）', () => {
    // 目標：障礙物只在 x 方向擋住一般字體（fullW=78），但小字體（smallW=68）夠窄可以通過。
    // 障礙中心在 x=137，與 labelPoint x=100 距離 37 px。
    //   一般字體 x-overlap: 37*2=74 < 78+2=80 → 重疊 ✓
    //   小字體   x-overlap: 74 < 68+2=70 → 不重疊 ✓（得以放置，small=true）
    // 高度 200 px 使所有 shifts (±30) 都被 y 方向覆蓋。
    const narrowXObs = [{ x: 137, y: 100, w: 2, h: 200 }];
    // 沒有網格候選點（強迫走 small 回退）
    const r = findLabelPlacement(100, 100, textLen, narrowXObs, []);
    expect(r).not.toBeNull();
    expect(r!.small).toBe(true);
    // 縮小字體框不應與障礙重疊
    const box = { x: r!.x, y: r!.y, w: smallW, h: LABEL_SMALL_H };
    expect(narrowXObs.some((o) => rectsOverlap(box, o))).toBe(false);
  });

  it('所有候選（含縮小字）都撞時回傳 null', () => {
    // 超大障礙物覆蓋所有可能位置
    const hugeObs = [{ x: 100, y: 100, w: 10000, h: 10000 }];
    const r = findLabelPlacement(100, 100, textLen, hugeObs, []);
    expect(r).toBeNull();
  });

  it('網格候選點避讓 UI 障礙物（整合場景）', () => {
    // 模擬圖例在左下角（x=140, y=700, w=280, h=300）擋住 labelPoint 及所有 shifts
    const legendObs = [{ x: 140, y: 700, w: 280 + 12, h: 300 + 12 }];
    // labelPoint 在圖例上方（x=140, y=600）→ shifts 都撞
    // 網格候選點在不受遮擋的地方（x=400, y=400）
    const gridPts = [{ x: 400, y: 400 }];
    const r = findLabelPlacement(140, 700, textLen, legendObs, gridPts);
    expect(r).not.toBeNull();
    expect(r!.x).toBe(400);
    expect(r!.y).toBe(400);
  });
});
