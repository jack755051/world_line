import { AXIS_PAINT, CONTROL_ONLY_LAYERS, buildBaseStyle, overlaps, regimeLabelSortKey, buildRegimeLabelFeatureCollection, obstacleGridFeatures, REGIME_OBSTACLE_ICON_SIZE, shortRegimeText, regimeLabelArea } from './atlas-map';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { type ControlLabel } from './map-style';

describe('實際控制／主權切換（地圖圖層）', () => {
  const ids = new Set(buildBaseStyle().layers.map((l) => l.id));

  it('兩個檢視設定同一組圖層與屬性，且圖層都存在於底圖樣式', () => {
    const key = (a: [string, string, number][]) => a.map(([l, p]) => `${l}:${p}`).sort();
    expect(key(AXIS_PAINT.control)).toEqual(key(AXIS_PAINT.sovereignty));
    for (const [layer] of AXIS_PAINT.control) expect(ids.has(layer)).toBe(true);
    for (const layer of CONTROL_ONLY_LAYERS) expect(ids.has(layer)).toBe(true);
  });

  it('主權檢視：國界填色加深、控制區常數圖層淡出到 0；實際控制檢視：國界淡色當底圖', () => {
    const v = (axis: 'control' | 'sovereignty', layer: string) => AXIS_PAINT[axis].find(([l]) => l === layer)![2];
    expect(v('sovereignty', 'sov-fill')).toBeGreaterThan(v('control', 'sov-fill'));
    expect(v('sovereignty', 'control-regime-outline')).toBe(0);
    expect(v('control', 'control-regime-outline')).toBeGreaterThan(0);
  });

  it('只對常數不透明度做 transition：資料驅動的控制區圖層不在 AXIS_PAINT 裡', () => {
    const style = buildBaseStyle();
    for (const [layer, prop] of AXIS_PAINT.control) {
      const l = style.layers.find((x) => x.id === layer) as { paint?: Record<string, unknown> };
      const value = l.paint?.[prop];
      expect(value === undefined || typeof value === 'number').toBe(true);
    }
    for (const layer of CONTROL_ONLY_LAYERS) expect(AXIS_PAINT.control.some(([l]) => l === layer)).toBe(false);
  });

  it('標籤互撞判斷', () => {
    expect(overlaps({ x: 0, y: 0, w: 100, h: 20 }, { x: 50, y: 5, w: 100, h: 20 })).toBe(true);
    expect(overlaps({ x: 0, y: 0, w: 100, h: 20 }, { x: 120, y: 0, w: 100, h: 20 })).toBe(false);
    expect(overlaps({ x: 0, y: 0, w: 100, h: 20 }, { x: 0, y: 30, w: 100, h: 20 })).toBe(false);
  });
});

describe('regimeLabelSortKey', () => {
  it('大 bbox 面積→小 sort key（優先）', () => {
    const bigBbox: [number, number, number, number] = [0, 0, 50, 30];
    const smallBbox: [number, number, number, number] = [0, 0, 2, 2];
    expect(regimeLabelSortKey(bigBbox)).toBeLessThan(regimeLabelSortKey(smallBbox));
  });

  it('控制區標籤（fit=undefined）比國名標籤（fit 有值）優先', () => {
    const bbox: [number, number, number, number] = [0, 0, 10, 10];
    expect(regimeLabelSortKey(bbox, undefined)).toBeLessThan(regimeLabelSortKey(bbox, 1.6));
  });

  it('面積為 0 時不拋出錯誤，回傳有限數值', () => {
    const result = regimeLabelSortKey([0, 0, 0, 0]);
    expect(isFinite(result)).toBe(true);
  });
});

describe('shortRegimeText', () => {
  it('無括號後綴的名稱不變', () => {
    expect(shortRegimeText('義大利')).toBe('義大利');
    expect(shortRegimeText('匈牙利')).toBe('匈牙利');
  });

  it('去掉結尾全形括號段', () => {
    expect(shortRegimeText('埃及（英國保護國）')).toBe('埃及');
    expect(shortRegimeText('伊拉克（英國委任統治）')).toBe('伊拉克');
  });

  it('去掉後綴後有空白時修剪', () => {
    expect(shortRegimeText('西藏 （英屬）')).toBe('西藏');
  });

  it('整個名稱都是括號時回傳原始文字（避免空字串）', () => {
    const t = '（無名）';
    expect(shortRegimeText(t)).toBe(t);
  });

  it('去掉政體後綴「王國」', () => {
    expect(shortRegimeText('匈牙利王國')).toBe('匈牙利');
    expect(shortRegimeText('義大利王國')).toBe('義大利');
    expect(shortRegimeText('埃及王國')).toBe('埃及');
  });

  it('去掉政體後綴「共和國」', () => {
    expect(shortRegimeText('拉脫維亞共和國')).toBe('拉脫維亞');
  });

  it('去掉政體後綴「保護國」', () => {
    expect(shortRegimeText('法屬突尼西亞保護國')).toBe('法屬突尼西亞');
  });

  it('去掉政體後綴「帝國」', () => {
    expect(shortRegimeText('大英帝國')).toBe('大英');
  });

  it('殘餘少於 2 字時不去後綴（保留原名）', () => {
    // 假設有個「X王國」，去後綴只剩 1 字，應保留
    expect(shortRegimeText('X王國')).toBe('X王國');
  });
});

describe('regimeLabelArea', () => {
  it('赤道上的矩形面積等於 width × height（cos(0)=1）', () => {
    const bbox: [number, number, number, number] = [10, -5, 20, 5];
    expect(regimeLabelArea(bbox)).toBeCloseTo(10 * 10 * 1, 3);
  });

  it('中緯度（60°）面積縮小為約原來一半', () => {
    const bbox: [number, number, number, number] = [10, 55, 20, 65];
    const expected = 10 * 10 * Math.cos(60 * Math.PI / 180);
    expect(regimeLabelArea(bbox)).toBeCloseTo(expected, 2);
  });

  it('面積恆非負', () => {
    expect(regimeLabelArea([0, 0, 0, 0])).toBeGreaterThanOrEqual(0);
    expect(regimeLabelArea([5, 20, 0, 15])).toBeGreaterThanOrEqual(0);
  });
});

describe('buildRegimeLabelFeatureCollection', () => {
  const label: ControlLabel = {
    versionId: 'v1', regimeId: 'r1', text: '測試', lngLat: [10, 50],
    bbox: [8, 48, 15, 53],
  };

  it('每個 label 對應一個 Point feature', () => {
    const fc = buildRegimeLabelFeatureCollection([label]);
    expect(fc.features).toHaveLength(1);
    expect(fc.features[0].geometry.type).toBe('Point');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((fc.features[0].geometry as any).coordinates).toEqual([10, 50]);
  });

  it('properties 包含 versionId、regimeId、text、shortText、area、sortKey、rotation', () => {
    const fc = buildRegimeLabelFeatureCollection([label]);
    const p = fc.features[0].properties!;
    expect(p['versionId']).toBe('v1');
    expect(p['regimeId']).toBe('r1');
    expect(p['text']).toBe('測試');
    expect(p['shortText']).toBe('測試');
    expect(typeof p['area']).toBe('number');
    expect(p['area']).toBeGreaterThanOrEqual(0);
    expect(typeof p['sortKey']).toBe('number');
    expect(p['rotation']).toBe(0);
  });

  it('有括號後綴時 shortText 不同於 text', () => {
    const withSuffix: ControlLabel = { ...label, text: '埃及（英國保護國）' };
    const fc = buildRegimeLabelFeatureCollection([withSuffix]);
    const p = fc.features[0].properties!;
    expect(p['text']).toBe('埃及（英國保護國）');
    expect(p['shortText']).toBe('埃及');
  });

  it('rotation 有值時帶入', () => {
    const withRot: ControlLabel = { ...label, rotation: 15 };
    const fc = buildRegimeLabelFeatureCollection([withRot]);
    expect(fc.features[0].properties!['rotation']).toBe(15);
  });

  it('空陣列回傳空 FeatureCollection', () => {
    const fc = buildRegimeLabelFeatureCollection([]);
    expect(fc.features).toHaveLength(0);
  });
});

describe('obstacleGridFeatures', () => {
  const identityUnproject = (px: [number, number]): [number, number] => px;

  it('空 boxes → 空 features', () => {
    expect(obstacleGridFeatures([], identityUnproject)).toHaveLength(0);
  });

  it('非空 box 產生若干格點 features', () => {
    const box = { x: 50, y: 50, w: 100, h: 100 };
    const features = obstacleGridFeatures([box], identityUnproject);
    expect(features.length).toBeGreaterThan(0);
  });

  it('所有 feature 都是 Point 型別', () => {
    const box = { x: 100, y: 100, w: 200, h: 150 };
    const features = obstacleGridFeatures([box], identityUnproject);
    for (const f of features) {
      expect(f.geometry.type).toBe('Point');
      expect(f.geometry.coordinates).toHaveLength(2);
    }
  });
});

describe('regime-label symbol layer（MapLibre GL 碰撞引擎）', () => {
  const style = buildBaseStyle();
  const layers = style.layers;
  const layerIds = layers.map((l) => l.id);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const regimeLayer = layers.find((l) => l.id === 'regime-label') as any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const obstacleLayer = layers.find((l) => l.id === 'regime-label-obstacles') as any;
  const capDotIdx = layerIds.indexOf('capital-dot');
  const capLabelIdx = layerIds.indexOf('capital-label');
  const regimeLabelIdx = layerIds.indexOf('regime-label');
  const obstacleIdx = layerIds.indexOf('regime-label-obstacles');

  it('regime-label 圖層存在於底圖樣式', () => {
    expect(regimeLabelIdx).toBeGreaterThanOrEqual(0);
  });

  it('text-allow-overlap false（交給 MapLibre 碰撞引擎）', () => {
    expect(regimeLayer.layout?.['text-allow-overlap']).toBe(false);
    expect(regimeLayer.layout?.['text-ignore-placement']).toBe(false);
  });

  it('text-variable-anchor 包含必要的五個錨點與四個斜角（共九個）', () => {
    const anchors: string[] = regimeLayer.layout?.['text-variable-anchor'] ?? [];
    for (const a of ['center', 'top', 'bottom', 'left', 'right', 'top-left', 'top-right', 'bottom-left', 'bottom-right']) {
      expect(anchors).toContain(a);
    }
    expect(anchors).toHaveLength(9);
  });

  it('text-size 為 data-driven 表達式（非固定值 12）', () => {
    const textSize = regimeLayer.layout?.['text-size'];
    expect(Array.isArray(textSize)).toBe(true);
    expect(textSize).not.toBe(12);
    // 必須是 interpolate + zoom + step(area) 複合表達式
    expect(textSize?.[0]).toBe('interpolate');
    // 輸出值中須包含讀取 'area' 屬性的 step 表達式
    const hasAreaStep = (v: unknown): boolean => {
      if (!Array.isArray(v)) return false;
      if (v[0] === 'step' && Array.isArray(v[1]) && v[1][0] === 'get' && v[1][1] === 'area') return true;
      return v.some((x) => hasAreaStep(x));
    };
    expect(hasAreaStep(textSize)).toBe(true);
  });

  it('text-field 使用 shortText 屬性', () => {
    const textField = regimeLayer.layout?.['text-field'];
    expect(Array.isArray(textField)).toBe(true);
    expect(textField?.[0]).toBe('get');
    expect(textField?.[1]).toBe('shortText');
  });

  it('icon-text-fit-padding 上下不超過 2px、左右不超過 6px（碰撞框緊縮）', () => {
    const p: number[] = regimeLayer.layout?.['icon-text-fit-padding'] ?? [];
    expect(p).toHaveLength(4);
    expect(p[0]).toBeLessThanOrEqual(2); // top
    expect(p[2]).toBeLessThanOrEqual(2); // bottom
    expect(p[1]).toBeLessThanOrEqual(6); // right
    expect(p[3]).toBeLessThanOrEqual(6); // left
  });

  it('capital-dot 與 capital-label 在 regime-label 之後（先處理上層圖層＝優先）', () => {
    expect(capDotIdx).toBeGreaterThan(regimeLabelIdx);
    expect(capLabelIdx).toBeGreaterThan(regimeLabelIdx);
  });

  it('regime-label-obstacles 在 regime-label 之後、capital-dot 之前', () => {
    expect(obstacleIdx).toBeGreaterThan(regimeLabelIdx);
    expect(obstacleIdx).toBeLessThan(capDotIdx);
  });

  it('regime-label-obstacles：icon-allow-overlap true、icon-ignore-placement false', () => {
    expect(obstacleLayer.layout?.['icon-allow-overlap']).toBe(true);
    expect(obstacleLayer.layout?.['icon-ignore-placement']).toBe(false);
  });

  it('symbol-sort-key 為 data-driven 表達式（讀取 sortKey 屬性）', () => {
    const sortKey = regimeLayer.layout?.['symbol-sort-key'];
    // data-driven expression: ['get', 'sortKey']
    expect(Array.isArray(sortKey)).toBe(true);
    expect(sortKey?.[0]).toBe('get');
    expect(sortKey?.[1]).toBe('sortKey');
  });
});
