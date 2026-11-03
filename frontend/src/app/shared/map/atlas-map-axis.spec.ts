import { AXIS_PAINT, CONTROL_ONLY_LAYERS, buildBaseStyle, overlaps, regimeLabelSortKey, buildRegimeLabelFeatureCollection, obstacleGridFeatures, REGIME_OBSTACLE_ICON_SIZE } from './atlas-map';
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

  it('properties 包含 versionId、regimeId、text、sortKey、rotation', () => {
    const fc = buildRegimeLabelFeatureCollection([label]);
    const p = fc.features[0].properties!;
    expect(p['versionId']).toBe('v1');
    expect(p['regimeId']).toBe('r1');
    expect(p['text']).toBe('測試');
    expect(typeof p['sortKey']).toBe('number');
    expect(p['rotation']).toBe(0);
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

  it('text-variable-anchor 包含必要的五個錨點', () => {
    const anchors: string[] = regimeLayer.layout?.['text-variable-anchor'] ?? [];
    for (const a of ['center', 'top', 'bottom', 'left', 'right']) {
      expect(anchors).toContain(a);
    }
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
