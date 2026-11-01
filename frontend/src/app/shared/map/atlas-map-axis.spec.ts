import { AXIS_PAINT, CONTROL_ONLY_LAYERS, buildBaseStyle, overlaps } from './atlas-map';

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
