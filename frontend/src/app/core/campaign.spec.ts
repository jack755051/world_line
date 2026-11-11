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
      // index.json＋API（回應缺 layers → 不採用）＋靜態 JSON 備援（§19.5 C1）
      expect(fetchMock).toHaveBeenCalledTimes(enabled ? 3 : 0);
      if (enabled) { expect(String(fetchMock.mock.calls[1][0])).toBe('/api/v1/campaigns/dunkirk_1940'); expect(svc.source()).toBe('static'); }
      svc.close();
    });
  }
});

describe('CampaignPlayer 播放時鐘（§19.2.4：GSAP timeline 只追隨狀態）', () => {
  /** 假時鐘：手動 tick，記錄呼叫，驗證 player 只透過 start／pause／resume／stop 驅動它。 */
  const fake = () => {
    const calls: string[] = [];
    let tick: () => void = () => undefined;
    const factory = (_ms: number, t: () => void) => { tick = t; return { start: () => calls.push('start'), pause: () => calls.push('pause'), resume: () => calls.push('resume'), stop: () => calls.push('stop') }; };
    return { calls, factory, tick: () => tick() };
  };
  it('暫停後再播放 → resume（接續本階段剩餘時間）；跳轉後再播放 → 重新 start', () => {
    const c = fake();
    const p = new CampaignPlayer(4, () => {}, 3000, c.factory);
    p.play(); expect(c.calls.at(-1)).toBe('start');
    c.tick(); expect(p.phase).toBe(2);
    p.pause(); expect(c.calls.at(-1)).toBe('pause');
    p.play(); expect(c.calls.at(-1)).toBe('resume');
    p.pause(); p.next(); expect(p.phase).toBe(3);
    p.play(); expect(c.calls.at(-1)).toBe('start');
  });
  it('播完停在 ended 並停掉時鐘', () => {
    const c = fake();
    const p = new CampaignPlayer(2, () => {}, 3000, c.factory);
    p.play(); c.tick();
    expect(p.status).toBe('ended');
    expect(c.calls.at(-1)).toBe('stop');
  });
});
