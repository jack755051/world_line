import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { parseAtlasQuery } from './atlas-state';
import { fetchCampaign, type Campaign } from './campaign';
import { CampaignReturn, RETURN_STATE_KEY, atlasQueryFor, type ReturnSnapshot } from './campaign-return';
import { parsePhase, phaseHasPending, phaseHasVerified } from '../pages/campaign/campaign.page';

const snap: ReturnSnapshot = {
  route: 'atlas', date: '1940-05-28', lang: 'zh-Hant', axis: 'sovereignty',
  camera: { center: [1, 51], zoom: 5, bearing: 0 }, regimeId: '11111111-1111-4111-8111-111111111111', sheetTab: 'events', sheetScrollTop: 120,
};
const campaign = {
  phases: [{ seq: 1 }, { seq: 2 }],
  layers: {
    fronts: { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { id: 'f', phase: 1, verified: true }, geometry: { type: 'LineString', coordinates: [] } }] },
    arrows: { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { id: 'a', phase: 2, verified: false }, geometry: { type: 'LineString', coordinates: [] } }] },
    sites: { type: 'FeatureCollection', features: [] },
  },
} as unknown as Campaign;

describe('§19.2.5 ReturnSnapshot', () => {
  it('只存一格：戰役 → 戰役覆寫不累加；回到地圖取用一次後清空', () => {
    const r = TestBed.inject(CampaignReturn);
    r.save(snap);
    r.save({ ...snap, date: '1940-06-01' });
    expect(r.slot()?.date).toBe('1940-06-01');
    r.armRestore(r.slot()!);
    expect(r.takeRestore()?.date).toBe('1940-06-01');
    expect(r.slot()).toBeNull();
    history.replaceState({}, '');
    expect(r.takeRestore()).toBeNull();
  });
  it('記憶體沒有時讀 history.state（重新整理戰役頁後按上一頁）', () => {
    const r = TestBed.inject(CampaignReturn);
    history.replaceState({ [RETURN_STATE_KEY]: snap }, '');
    expect(r.takeRestore()).toEqual(snap);
    history.replaceState({}, '');
  });
  it('返回地圖的 query：overview 不寫 tab；沒選政權時不寫 regime／tab', () => {
    expect(atlasQueryFor(snap)).toEqual({ date: '1940-05-28', lang: null, axis: 'sovereignty', regime: snap.regimeId, tab: 'events' });
    expect(atlasQueryFor({ ...snap, sheetTab: 'overview' })['tab']).toBeNull();
    expect(atlasQueryFor({ ...snap, regimeId: null })).toMatchObject({ regime: null, tab: null });
  });
});

describe('§19.2.2 Q4＝b：regime／tab 進 URL', () => {
  it('只接受 uuid 與已知分頁', () => {
    expect(parseAtlasQuery({ regime: snap.regimeId!, tab: 'leaders' })).toMatchObject({ regime: snap.regimeId, tab: 'leaders' });
    expect(parseAtlasQuery({ regime: 'drop table', tab: 'x' })).toMatchObject({ regime: null, tab: null });
  });
});

describe('§19.5 C1：戰役資料來源', () => {
  const res = (ok: boolean, body: unknown) => ({ ok, status: ok ? 200 : 503, json: async () => body }) as Response;
  it('API 讀得到 → source=api（拆 data 信封）', async () => {
    const f = (async (u: string) => (u.startsWith('/api/') ? res(true, { data: campaign }) : res(false, null))) as typeof fetch;
    expect((await fetchCampaign('dunkirk_1940', 'campaigns/', f)).source).toBe('api');
  });
  it('API 失敗 → 退回靜態 JSON，source=static；兩者都失敗就丟錯', async () => {
    const f = (async (u: string) => (u.startsWith('/api/') ? res(false, null) : res(true, campaign))) as typeof fetch;
    expect((await fetchCampaign('dunkirk_1940', 'campaigns/', f)).source).toBe('static');
    const bad = (async () => res(false, null)) as typeof fetch;
    await expect(fetchCampaign('x', 'campaigns/', bad)).rejects.toThrow();
  });
});

describe('§19.2 戰役頁：階段與空狀態', () => {
  it('phase 參數夾在合法範圍，否則回 1', () => {
    expect(parsePhase('2', 6)).toBe(2);
    expect(parsePhase('7', 6)).toBe(1);
    expect(parsePhase(null, 6)).toBe(1);
  });
  it('沒有 verified 圖形的階段 → 顯示「此階段尚無有出處的戰線資料」；pending 圖形 → 「待考證」圖例', () => {
    expect(phaseHasVerified(campaign, 1)).toBe(true);
    expect(phaseHasVerified(campaign, 2)).toBe(false);
    expect(phaseHasPending(campaign, 1)).toBe(false);
    expect(phaseHasPending(campaign, 2)).toBe(true);
  });
});
