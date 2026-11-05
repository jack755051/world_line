import { describe, expect, it } from 'vitest';
import { tileCampColor, tileCampFilter, tileHatchBase, tileHatchPattern, boundaryTileLayers, tileDateFilter, tileFillColor, tileFilters, tileFilterUpdate, tileLabelFilter, tileLabelText, pickTileLabels, TILE_LAYER_IDS, byIdExpr, dataDrivenPaint, overlayFilter } from './boundary-tiles';
import { labelMinZoom } from './label-fit';
import { MAP_COLORS } from './map-style';
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
    expect((tileLabelFilter(1, { a: 10 }) as unknown[]).length).toBe(4);
    // 尚未挑候選點：只放行最大塊
    expect(f[4]).toEqual(['==', ['coalesce', ['get', 'part'], 1], 1]);
    const g = tileLabelFilter(1, { a: 10 }, null, ['b:2', 'a:1']) as unknown[];
    expect(JSON.stringify(g[3])).toContain('["literal",["a:1","b:2"]]');
  });
  it('pickTileLabels: one candidate per regime, largest visible part that fits; selected regime skipped', () => {
    const c = (regimeId: string, part: number, area: number, lng: number, spanX = 0.1) => ({ regimeId, part, area, spanX, lng, lat: 50 });
    const view = { west: -10, east: 40, south: 30, north: 70, zoom: 3 };
    const px = { fr: 40, su: 40, se: 40, tiny: 1e6 };
    const cands = [c('fr', 1, 600000, -60), c('fr', 2, 500000, 2), c('fr', 3, 30000, 5), c('su', 1, 2e7, 100), c('su', 2, 3e5, 30),
      c('se', 1, 4e5, 15), c('se', 1, 4e5, 15), c('tiny', 1, 10, 0)];
    expect(pickTileLabels(cands, view, px)).toEqual(['fr:2', 'se:1', 'su:2']);
    expect(pickTileLabels(cands, view, px, 'fr')).toEqual(['se:1', 'su:2']);
    // 跨換日線的視窗、與名字裝不下
    expect(pickTileLabels([c('su', 1, 2e7, 170)], { west: 160, east: 200, south: 0, north: 80, zoom: 3 }, px)).toEqual(['su:1']);
    expect(pickTileLabels([c('su', 1, 2e7, -175)], { west: 160, east: 200, south: 0, north: 80, zoom: 3 }, px)).toEqual(['su:1']);
    expect(pickTileLabels([c('fr', 2, 5e5, 2, 1e-4)], view, px)).toEqual([]);
  });
  it('layers: all four use the date filter on the right source-layer', () => {
    const ls = boundaryTileLayers(100, {}, { names: { a: '甲' }, labelPx: { a: 30 } }) as Array<{ id: string; filter: unknown; 'source-layer': string }>;
    expect(ls.map((l) => l.id)).toEqual([...TILE_LAYER_IDS]);
    for (const l of ls) if (l.id !== 'tiles-camp-line') expect(JSON.stringify(l.filter)).toContain(JSON.stringify(tileDateFilter(100)));
    expect(ls.map((l) => l['source-layer'])).toEqual(['boundaries', 'boundaries', 'boundaries', 'boundaries', 'boundaries', 'boundaries', 'labels']);
  });
  it('filter only updates when the change-point interval changes', () => {
    expect(tileFilterUpdate(null, '1940-06-22', 14783)).toEqual({ key: '1940-06-22', filters: tileFilters(14783) });
    expect(tileFilterUpdate('1940-06-22', '1940-06-22', 14790)).toBeNull();
  });
});

describe('非主權斜線（tiles）', () => {
  it('填色只畫主權政權；非主權畫底色＋斜線（與 sov-fill／sov-hatch 相同分法）', () => {
    const f = tileFilters(5) as Record<string, unknown>;
    expect(JSON.stringify(f['tiles-fill'])).toContain('["!",["==",["get","control_type"],"not_sovereign"]]');
    expect(JSON.stringify(f['tiles-hatch'])).toContain('["==",["get","control_type"],"not_sovereign"]');
    expect(f['tiles-hatch']).toEqual(f['tiles-hatch-base']);
  });
  it('斜線圖樣：政權色（佔領區用覆蓋色），其餘依 color_idx；底色預設紙底', () => {
    const p = tileHatchPattern({ a: '#aabbcc' }, { b: '#112233' }) as unknown[];
    expect(p.slice(0, 6)).toEqual(['match', ['get', 'regime_id'], 'a', 'wl-hatch-contested-aabbcc', 'b', 'wl-hatch-contested-112233']);
    expect(JSON.stringify(p[6])).toContain('color_idx');
    expect(tileHatchBase()).toEqual(['literal', MAP_COLORS.land]);
    expect(tileHatchBase({ x: '#123456' })).toEqual(['match', ['get', 'regime_id'], 'x', '#123456', MAP_COLORS.land]);
  });
});

describe('陣營外框（tiles）', () => {
  it('只描當日有陣營的政權，顏色依陣營；沒有就不畫', () => {
    expect(tileCampFilter(9, {})).toEqual(['boolean', false]);
    expect(tileCampFilter(9, { b: '#2', a: '#1' })).toEqual(['all', tileDateFilter(9), ['in', ['get', 'regime_id'], ['literal', ['a', 'b']]]]);
    expect(tileCampColor({ b: '#2', a: '#1' })).toEqual(['match', ['get', 'regime_id'], 'a', '#1', 'b', '#2', MAP_COLORS.ink]);
  });
});

describe('overlay 圖層（§9 步驟 5-5）', () => {
  const rows = new Map<string, Record<string, unknown>>([
    ['v2', { wlFill: '#222', wlFillOpacity: 0.6, wlPattern: '' }],
    ['v1', { wlFill: '#111', wlFillOpacity: 0.85, wlPattern: 'wl-hatch-partial-111111' }],
  ]);
  it('byIdExpr：屬性換成依 versionId 的 match（id 排序、預設值依型別），id 本身與 literal 不動', () => {
    expect(byIdExpr(['get', 'wlFill'], 'versionId', rows)).toEqual(['match', ['get', 'versionId'], 'v1', '#111', 'v2', '#222', '#111']);
    expect(byIdExpr(['get', 'wlFillOpacity'], 'versionId', rows)).toEqual(['match', ['get', 'versionId'], 'v1', 0.85, 'v2', 0.6, 0.85]);
    expect(byIdExpr(['==', ['get', 'versionId'], 'x'], 'versionId', rows)).toEqual(['==', ['get', 'versionId'], 'x']);
    expect(byIdExpr(['literal', ['get', 'a']], 'versionId', rows)).toEqual(['literal', ['get', 'a']]);
    expect(byIdExpr(['get', 'wlFill'], 'versionId', new Map())).toEqual(['get', 'wlFill']);
  });
  it('overlayFilter：當日清單 ∧ 原 filter；清單空時不畫', () => {
    expect(overlayFilter(['==', ['get', 'wlPattern'], ''], 'versionId', rows)).toEqual([
      'all', ['in', ['get', 'versionId'], ['literal', ['v1', 'v2']]],
      ['==', ['match', ['get', 'versionId'], 'v1', 'wl-hatch-partial-111111', 'v2', '', 'wl-hatch-partial-111111'], ''],
    ]);
    expect(overlayFilter(undefined, 'gapId', new Map([['g', {}]]))).toEqual(['in', ['get', 'gapId'], ['literal', ['g']]]);
    expect(overlayFilter(undefined, 'versionId', new Map())).toEqual(['boolean', false]);
  });
  it('dataDrivenPaint：只挑有 get 的屬性', () => {
    expect(dataDrivenPaint({ 'fill-color': ['get', 'wlFill'], 'fill-opacity': 0.5, 'line-width': ['*', 2, ['get', 'w']] })).toEqual(['fill-color', 'line-width']);
  });
});
