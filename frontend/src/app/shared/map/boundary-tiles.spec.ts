import { describe, expect, it } from 'vitest';
import { boundaryTileLayers, tileDateFilter, tileFillColor, tileFilters, tileFilterUpdate, tileLabelText, TILE_LAYER_IDS } from './boundary-tiles';
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
  it('label text follows language', () => {
    expect(tileLabelText('zh-Hant')).toEqual(['coalesce', ['get', 'name_zh'], ['get', 'name_local']]);
    expect(tileLabelText('en')).toEqual(['coalesce', ['get', 'name_local'], ['get', 'name_zh']]);
  });
  it('layers: all four use the date filter on the right source-layer', () => {
    const ls = boundaryTileLayers(100, {}, 'zh-Hant') as Array<{ id: string; filter: unknown; 'source-layer': string }>;
    expect(ls.map((l) => l.id)).toEqual([...TILE_LAYER_IDS]);
    for (const l of ls) expect(JSON.stringify(l.filter)).toContain(JSON.stringify(tileDateFilter(100)));
    expect(ls.map((l) => l['source-layer'])).toEqual(['boundaries', 'boundaries', 'boundaries', 'labels']);
  });
  it('filter only updates when the change-point interval changes', () => {
    expect(tileFilterUpdate(null, '1940-06-22', 14783)).toEqual({ key: '1940-06-22', filters: tileFilters(14783) });
    expect(tileFilterUpdate('1940-06-22', '1940-06-22', 14790)).toBeNull();
  });
});
