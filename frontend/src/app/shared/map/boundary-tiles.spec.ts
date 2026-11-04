import { describe, expect, it } from 'vitest';
import { boundaryTileLayers, tileDateFilter, tileFillColor, tileFilters, tileFilterUpdate, tileLabelFilter, tileLabelText, TILE_LAYER_IDS } from './boundary-tiles';
import { labelMinZoom } from './label-fit';
import { REGIME_FALLBACK_COLORS } from './sovereignty-style';

describe('boundary tiles', () => {
  it('date filter is start_day <= d < end_day', () => {
    expect(tileDateFilter(14805)).toEqual(['all', ['<=', ['get', 'start_day'], 14805], ['>', ['get', 'end_day'], 14805]]);
  });
  it('fill color: known regimes by id, others by color_idx palette', () => {
    // 後備色用 match 展開（fill-color 不收 'at' + literal 陣列，MapLibre 會判成 array<string>）
    const fb = ['match', ['get', 'color_idx'], ...REGIME_FALLBACK_COLORS.flatMap((c, i) => [i, c]), REGIME_FALLBACK_COLORS[0]];
    expect(tileFillColor({})).toEqual(fb);
    expect(JSON.stringify(tileFillColor({}))).not.toContain('"literal"');
    expect(tileFillColor({ b: '#222222', a: '#111111' })).toEqual(['match', ['get', 'regime_id'], 'a', '#111111', 'b', '#222222', fb]);
  });
  it('label text: API self names by regime_id, unknown regimes get no label', () => {
    expect(tileLabelText({})).toEqual(['literal', '']);
    expect(tileLabelText({ b: '乙', a: '甲', c: '' })).toEqual(['match', ['get', 'regime_id'], 'a', '甲', 'b', '乙', '']);
  });
  it('label filter: date, fits-on-screen (same threshold as labelMinZoom), excludes selected regime', () => {
    const f = tileLabelFilter(100, { a: 64 }, 'sel') as unknown[];
    expect(f[0]).toBe('all');
    expect(f[1]).toEqual(tileDateFilter(100));
    expect(f[3]).toEqual(['!=', ['get', 'regime_id'], 'sel']);
    // minZoom 表達式與 labelMinZoom 同式：log2(px / (span × 512))
    const ge = f[2] as unknown[];
    expect(ge[0]).toBe('>=');
    const span = 10 / 360; // 外框經度寬 10°
    const expected = labelMinZoom(64, [0, 0, 10, 1]);
    expect(Math.log(64 / (span * 512)) / Math.LN2).toBeCloseTo(expected, 9);
    expect(JSON.stringify(ge[2])).toContain('"span_x"');
    expect(tileLabelFilter(1, {})).toEqual(['boolean', false]);
    expect((tileLabelFilter(1, { a: 10 }) as unknown[]).length).toBe(3);
  });
  it('layers: all four use the date filter on the right source-layer', () => {
    const ls = boundaryTileLayers(100, {}, { names: { a: '甲' }, labelPx: { a: 30 } }) as Array<{ id: string; filter: unknown; 'source-layer': string }>;
    expect(ls.map((l) => l.id)).toEqual([...TILE_LAYER_IDS]);
    for (const l of ls) expect(JSON.stringify(l.filter)).toContain(JSON.stringify(tileDateFilter(100)));
    expect(ls.map((l) => l['source-layer'])).toEqual(['boundaries', 'boundaries', 'boundaries', 'labels']);
  });
  it('filter only updates when the change-point interval changes', () => {
    expect(tileFilterUpdate(null, '1940-06-22', 14783)).toEqual({ key: '1940-06-22', filters: tileFilters(14783) });
    expect(tileFilterUpdate('1940-06-22', '1940-06-22', 14790)).toBeNull();
  });
});
