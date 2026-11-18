import { describe, expect, it } from 'vitest';
import type { Campaign } from '../../core/campaign';
import { CAMPAIGN_LAYER_IDS, FRONT_COLOR, INFERRED_LABEL, campaignFilters, campaignLayers, campaignSourceData, isInferredFront, midpoint } from './campaign-layers';

const line = { type: 'LineString', coordinates: [[0, 0], [1, 1]] };
const front = (id: string, phase: number, verified: boolean, extra: Record<string, unknown> = {}) => ({ type: 'Feature' as const, properties: { id, phase, verified, ...extra }, geometry: line });
const empty = { type: 'FeatureCollection' as const, features: [] };
const campaign = (features: ReturnType<typeof front>[]) => ({ phases: [{ seq: 1 }, { seq: 2 }], layers: { fronts: { type: 'FeatureCollection', features }, arrows: empty, sites: empty } }) as unknown as Campaign;

const INFERRED = ['any', ['==', ['get', 'geom_basis'], 'derived'], ['==', ['get', 'inference'], '文字推定']];
const PHASE1 = ['==', ['get', 'phase'], 1];

describe('戰役圖層：文字推定／待查證前線', () => {
  it('isInferredFront：geom_basis=derived 或 inference=文字推定', () => {
    expect(isInferredFront({ geom_basis: 'derived' })).toBe(true);
    expect(isInferredFront({ inference: '文字推定' })).toBe(true);
    expect(isInferredFront({ geom_basis: 'traced' })).toBe(false);
    expect(isInferredFront({})).toBe(false);
  });

  it('campaign-fronts-inferred 圖層：細點線、同前線色，且列在圖層清單與 filters（切換階段／關閉戰役時一併處理）', () => {
    const l = campaignLayers().find((x) => x.id === 'campaign-fronts-inferred') as unknown as { type: string; source: string; paint: Record<string, unknown> };
    expect(l.type).toBe('line');
    expect(l.source).toBe('campaign-fronts');
    expect(l.paint).toMatchObject({ 'line-color': FRONT_COLOR, 'line-width': 2.5, 'line-opacity': 0.9, 'line-dasharray': [0.6, 1.8] });
    expect(CAMPAIGN_LAYER_IDS).toContain('campaign-fronts-inferred');
    const fs = campaignFilters(campaign([front('f1', 1, false, { geom_basis: 'derived' })]), 1);
    for (const id of CAMPAIGN_LAYER_IDS) expect(fs[id], id).toBeDefined();
  });

  it('filter：inferred 圖層只收文字推定前線，一般／未查證前線圖層排除它', () => {
    const fs = campaignFilters(campaign([front('f1', 1, false, { geom_basis: 'derived' })]), 1);
    expect(fs['campaign-fronts-inferred']).toEqual(['all', PHASE1, INFERRED]);
    expect(fs['campaign-fronts']).toEqual(['all', ['all', PHASE1, ['==', ['get', 'verified'], true]], ['!', INFERRED]]);
    expect(fs['campaign-fronts-unverified']).toEqual(['all', ['all', PHASE1, ['==', ['get', 'verified'], false]], ['!', INFERRED]]);
    expect(fs['campaign-fronts-label']).toEqual(['all', PHASE1, ['any', ['==', ['get', 'verified'], false], INFERRED]]);
  });

  it('filter 沿用最近一個有前線的階段（inferred 也是）', () => {
    const fs = campaignFilters(campaign([front('f1', 1, false, { inference: '文字推定' })]), 2);
    expect(fs['campaign-fronts-inferred']).toEqual(['all', PHASE1, INFERRED]);
  });

  it('label：名稱＋小字註記；文字推定前線「（文字推定・待查證）」，不單獨顯示「待考證」', () => {
    const d = campaignSourceData(campaign([
      front('derived', 1, false, { geom_basis: 'derived', date: '1939-09-17' }),
      front('text', 1, true, { inference: '文字推定', name: 'Bug 河線' }),
      front('plain-unverified', 1, false),
      front('plain-verified', 1, true, { name: '運河線' }),
    ]));
    const p = Object.fromEntries(d['campaign-fronts'].features.map((f) => [f.properties.id, f.properties as Record<string, unknown>]));
    expect(p['derived']['label']).toBe('前線 1939-09-17' + INFERRED_LABEL);
    expect(p['derived']['labelNote']).toBe(INFERRED_LABEL);
    expect(p['text']['label']).toBe('Bug 河線（文字推定・待查證）');
    expect(p['plain-unverified']['label']).toBe('前線（待考證）');
    expect(p['plain-verified']['label']).toBe('運河線');
    expect(p['plain-verified']['labelNote']).toBe('');
  });

  it('據點標籤：靜態檔 name、API 列 place／label；未查證加小字「（待考證）」', () => {
    const pt = (id: string, verified: boolean, extra: Record<string, unknown>) => ({ type: 'Feature' as const, properties: { id, phase: 1, verified, ...extra }, geometry: { type: 'Point', coordinates: [0, 0] } });
    const c = { phases: [{ seq: 1 }], layers: { fronts: empty, arrows: empty, sites: { type: 'FeatureCollection', features: [
      pt('static', false, { name: 'Westerplatte' }), pt('api', false, { place: 'Brześć' }), pt('api-label', false, { label: { 'zh-Hant': '華沙' } }),
      pt('ok', true, { name: 'Dunkerque' }), pt('none', false, {}),
    ] } } } as unknown as Campaign;
    const p = Object.fromEntries(campaignSourceData(c)['campaign-sites'].features.map((f) => [f.properties.id, f.properties as Record<string, unknown>]));
    expect(p['static']['label']).toBe('Westerplatte（待考證）');
    expect(p['api']['labelBase']).toBe('Brześć');
    expect(p['api']['labelNote']).toBe('（待考證）');
    expect(p['api-label']['label']).toBe('華沙（待考證）');
    expect(p['ok']['label']).toBe('Dunkerque');
    expect(p['none']['label']).toBe('地點（待考證）');
    for (const v of Object.values(p)) expect(v['label']).not.toBe('待考證');
  });

  it('標籤圖層用 format：名稱＋縮小註記', () => {
    const l = campaignLayers().find((x) => x.id === 'campaign-sites-label') as { layout: Record<string, unknown> };
    expect(l.layout['text-field']).toEqual(['format', ['get', 'labelBase'], {}, ['get', 'labelNote'], { 'font-scale': 0.78 }]);
  });

  it('前線標籤：每條前線在線長中點產生一個點標籤（折線、短線都有）', () => {
    expect(midpoint({ type: 'LineString', coordinates: [[0, 0], [2, 0], [2, 2]] })).toEqual([2, 0]);
    expect(midpoint({ type: 'LineString', coordinates: [[0, 0]] })).toBeNull();
    const d = campaignSourceData(campaign([front('a', 1, false, { geom_basis: 'derived' }), front('b', 2, true)]));
    expect(d['campaign-front-labels'].features.map((f) => [f.properties.id, f.geometry.coordinates])).toEqual([['a', [0.5, 0.5]], ['b', [0.5, 0.5]]]);
    const l = campaignLayers().find((x) => x.id === 'campaign-fronts-label') as { source: string; layout: Record<string, unknown> };
    expect(l.source).toBe('campaign-front-labels');
    expect(l.layout['text-allow-overlap']).toBe(false);
    expect(l.layout['text-ignore-placement']).toBe(false);
  });

  it('前線標籤：同階段同日期只出一個，放在最長那段；不同日期／不同名稱各自保留', () => {
    const geo = (coordinates: number[][]) => ({ type: 'LineString', coordinates });
    const f = (id: string, date: string, coords: number[][], extra: Record<string, unknown> = {}) => ({ ...front(id, 1, false, { date, ...extra }), geometry: geo(coords) });
    const d = campaignSourceData(campaign([
      f('short', '1940-05-26', [[0, 0], [1, 0]]),
      f('long', '1940-05-26', [[0, 0], [0, 4]]),
      f('other', '1940-05-27', [[0, 0], [2, 0]]),
      f('named', '1940-05-26', [[0, 0], [1, 0]], { name: '某防線' }),
    ] as never));
    const labels = d['campaign-front-labels'].features.map((x) => [x.properties.id, x.geometry.coordinates]);
    expect(labels).toEqual([['long', [0, 2]], ['other', [1, 0]], ['named', [0.5, 0]]]);
    expect(d['campaign-fronts'].features.length).toBe(4);
  });
});
