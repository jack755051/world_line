import type { FeatureCollection } from 'geojson';
import { avoidCapitals, capitalObstacleBoxes, rectsOverlap } from './label-placement';

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
