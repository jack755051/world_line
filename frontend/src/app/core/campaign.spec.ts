import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { CAMPAIGNS_ENABLED, CampaignService } from './campaign';
import { CampaignPlayer, campaignsForConflict, formatCampaignDate, inclusiveEnd, campaignsForEvent, campaignsForRegime, phaseForDate } from './campaign';

describe('CampaignPlayer（§11.2 階段播放）', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('開啟時停在 P1、不自動播放', () => {
    const p = new CampaignPlayer(5, () => {});
    vi.advanceTimersByTime(10000);
    expect(p.status).toBe('ready');
    expect(p.phase).toBe(1);
  });
  it('播放每 3 秒前進一階段，到最後一階段結束', () => {
    const p = new CampaignPlayer(3, () => {});
    p.play();
    expect(p.status).toBe('playing');
    vi.advanceTimersByTime(3000);
    expect(p.phase).toBe(2);
    vi.advanceTimersByTime(3000);
    expect(p.phase).toBe(3);
    expect(p.status).toBe('ended');
    vi.advanceTimersByTime(9000);
    expect(p.phase).toBe(3);
  });
  it('暫停後不再前進；結束後再播放從 P1 開始', () => {
    const p = new CampaignPlayer(3, () => {});
    p.play(); vi.advanceTimersByTime(3000); p.pause();
    expect(p.status).toBe('paused');
    vi.advanceTimersByTime(9000);
    expect(p.phase).toBe(2);
    p.play(); vi.advanceTimersByTime(3000);
    expect(p.status).toBe('ended');
    p.play();
    expect(p.phase).toBe(1);
  });
  it('上一步／下一步夾在範圍內', () => {
    const p = new CampaignPlayer(2, () => {});
    p.prev(); expect(p.phase).toBe(1);
    p.next(); expect(p.phase).toBe(2); expect(p.status).toBe('ended');
    p.next(); expect(p.phase).toBe(2);
    p.prev(); expect(p.phase).toBe(1); expect(p.status).toBe('paused');
  });
});

describe('戰役查詢', () => {
  const phases = [
    { seq: 1, start: '1940-05-26', end: '1940-05-28' },
    { seq: 2, start: '1940-05-28', end: '1940-06-01' },
  ] as never;
  it('phaseForDate：start 含、end 不含，超出夾到首尾', () => {
    expect(phaseForDate({ phases }, '1940-05-27')).toBe(1);
    expect(phaseForDate({ phases }, '1940-05-28')).toBe(2);
    expect(phaseForDate({ phases }, '1939-01-01')).toBe(1);
    expect(phaseForDate({ phases }, '1941-01-01')).toBe(2);
  });
  it('依政權或事件找戰役', () => {
    const idx = [{ key: 'd', name_zh: 'd', start: '', end: '', regime_slugs: ['united-kingdom'], event_ids: ['e1'] }];
    expect(campaignsForRegime(idx, 'united-kingdom').length).toBe(1);
    expect(campaignsForRegime(idx, 'japan').length).toBe(0);
    expect(campaignsForEvent(idx, 'e1').length).toBe(1);
    expect(campaignsForEvent(idx, null).length).toBe(0);
  });
});

describe('戰役日期精度', () => {
  it('early-month 顯示為上旬；缺欄位照原樣', () => {
    expect(formatCampaignDate('1937-10-01', 'early-month')).toBe('1937 年 10 月上旬');
    expect(formatCampaignDate('1937-10-01', null)).toBe('1937-10-01');
    expect(formatCampaignDate('1937-10-01', 'weird')).toBe('1937-10-01');
    expect(formatCampaignDate(null)).toBe('待考證');
    expect(inclusiveEnd('1937-10-01')).toBe('1937-09-30');
  });
});

describe('衝突是否符合戰役定義（§13 K2）', () => {
  const idx = [{ key: 'p', name_zh: 'p', start: '1939-09-01', end: '1939-10-07', regime_slugs: ['deutsches-reich', 'polish-republic'], event_ids: [] }];
  it('雙方都是交戰方且期間重疊才算', () => {
    expect(campaignsForConflict(idx, 'deutsches-reich', 'polish-republic', '1939-09-01', null).length).toBe(1);
    expect(campaignsForConflict(idx, 'soviet-union', 'republic-of-finland', '1939-11-30', '1940-03-13').length).toBe(0);
    expect(campaignsForConflict(idx, 'deutsches-reich', 'polish-republic', '1940-01-01', '1940-02-01').length).toBe(0);
  });
});

describe('戰役功能開關（production 關閉）', () => {
  const idx = { campaigns: [{ key: 'dunkirk_1940', name_zh: 'd', start: '1940-05-26', end: '1940-06-05', regime_slugs: ['united-kingdom'], event_ids: [] }] };
  afterEach(() => vi.unstubAllGlobals());
  for (const enabled of [true, false]) {
    it(enabled ? '開啟：載入 index、可開啟戰役' : '關閉：不載入任何戰役 JSON、open 無作用', async () => {
      const fetchMock = vi.fn(async (u: string) => ({ ok: true, json: async () => (u.endsWith('index.json') ? idx : { key: 'dunkirk_1940', phases: [{ seq: 1 }] }) }));
      vi.stubGlobal('fetch', fetchMock);
      TestBed.resetTestingModule();
      TestBed.configureTestingModule({ providers: [{ provide: CAMPAIGNS_ENABLED, useValue: enabled }] });
      const svc = TestBed.inject(CampaignService);
      await svc.loadIndex();
      await svc.open('dunkirk_1940');
      expect(svc.index().length).toBe(enabled ? 1 : 0);
      expect(svc.status()).toBe(enabled ? 'ready' : 'idle');
      expect(fetchMock).toHaveBeenCalledTimes(enabled ? 3 : 0); // index＋API（無 data）＋靜態 fallback
      svc.close();
    });
  }
});

describe('戰役資料來源：API 優先、靜態檔 fallback', () => {
  const apiCampaign = { schema: 'wl-campaign-web/0.1', key: 'poland_1939', name_zh: 'api', phases: [{ seq: 1 }, { seq: 2 }] };
  const staticCampaign = { schema: 'wl-campaign-web/0.1', key: 'poland_1939', name_zh: 'static', phases: [{ seq: 1 }] };
  const envelope = (data: unknown) => ({ statusCode: 200, message: 'ok', data, code: 0 });
  const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body });
  const notFound = { ok: false, status: 404, json: async () => envelope(null) };
  type Reply = () => unknown;
  function setup(api: Reply, stat: Reply = () => ok(staticCampaign)) {
    const fetchMock = vi.fn(async (u: string) => (u.startsWith('/api/v1/') ? api() : stat()));
    vi.stubGlobal('fetch', fetchMock);
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [{ provide: CAMPAIGNS_ENABLED, useValue: true }] });
    return { svc: TestBed.inject(CampaignService), fetchMock };
  }
  afterEach(() => vi.unstubAllGlobals());

  it('API 成功：用 API 資料、origin=api、不讀靜態檔', async () => {
    const { svc, fetchMock } = setup(() => ok(envelope(apiCampaign)));
    expect(svc.origin()).toBeNull();
    await svc.open('poland_1939');
    expect(fetchMock.mock.calls.map((c) => c[0])).toEqual(['/api/v1/campaigns/poland_1939']);
    expect(svc.status()).toBe('ready');
    expect(svc.campaign()?.name_zh).toBe('api');
    expect(svc.origin()).toBe('api');
    svc.close();
    expect(svc.origin()).toBeNull();
  });

  const failures: [string, Reply][] = [
    ['404', () => notFound],
    ['網路錯誤（throw）', () => { throw new TypeError('Failed to fetch'); }],
    ['data 為 null', () => ok(envelope(null))],
    ['phases 為空陣列', () => ok(envelope({ ...apiCampaign, phases: [] }))],
  ];
  for (const [name, api] of failures) {
    it(`API ${name}：fallback 靜態檔、origin=static`, async () => {
      const { svc, fetchMock } = setup(api);
      await svc.open('poland_1939');
      expect(fetchMock.mock.calls.map((c) => c[0])).toEqual(['/api/v1/campaigns/poland_1939', 'campaigns/poland_1939.json']);
      expect(svc.status()).toBe('ready');
      expect(svc.campaign()?.name_zh).toBe('static');
      expect(svc.origin()).toBe('static');
      svc.close();
    });
  }

  it('API 與靜態檔都失敗：status=error、origin=null', async () => {
    const { svc, fetchMock } = setup(() => notFound, () => ({ ok: false, status: 404, json: async () => ({}) }));
    await svc.open('nope');
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(svc.status()).toBe('error');
    expect(svc.campaign()).toBeNull();
    expect(svc.origin()).toBeNull();
  });
  it('API 失敗且靜態檔 throw：status=error', async () => {
    const { svc } = setup(() => { throw new Error('x'); }, () => { throw new Error('y'); });
    await svc.open('nope');
    expect(svc.status()).toBe('error');
    expect(svc.origin()).toBeNull();
  });
});
