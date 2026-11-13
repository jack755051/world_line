import { describe, expect, it } from 'vitest';
import type { Campaign } from '../../core/campaign';
import { CAMPAIGN_LAYER_IDS, FRONT_COLOR, INFERRED_LABEL, campaignFilters, campaignLayers, campaignSourceData, isInferredFront } from './campaign-layers';

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

  it('label：文字推定前線後加「（文字推定・待查證）」；沒有 geom_basis 的靜態檔（Dunkirk／Shanghai）不變', () => {
    const d = campaignSourceData(campaign([
      front('derived', 1, false, { geom_basis: 'derived' }),
      front('text', 1, true, { inference: '文字推定' }),
      front('plain-unverified', 1, false),
      front('plain-verified', 1, true),
    ]));
    const label = Object.fromEntries(d['campaign-fronts'].features.map((f) => [f.properties.id, f.properties['label']]));
    expect(label['derived']).toBe('待考證' + INFERRED_LABEL);
    expect(label['text']).toBe('（文字推定・待查證）');
    expect(label['plain-unverified']).toBe('待考證');
    expect(label['plain-verified']).toBe('');
  });
});
