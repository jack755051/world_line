import { TestBed } from '@angular/core/testing';
import { AtlasData } from './atlas-data';
import { WorldLineApi } from './api/world-line-api';
import type { SovereigntyMapDto } from './api/api-types';

const sov = (date: string) => ({ date, featureCollection: { type: 'FeatureCollection', features: [] } }) as unknown as SovereigntyMapDto;

describe('AtlasData：快速連續跳日期', () => {
  it('新日期開始載入時中止舊請求；舊請求晚到也不蓋掉新資料；mapDataLoading 反映載入中', async () => {
    const pending: { date: string; signal?: AbortSignal; resolve: (v: SovereigntyMapDto) => void; reject: (e: unknown) => void }[] = [];
    const api = {
      sovereignty: (date: string, signal?: AbortSignal) =>
        new Promise<SovereigntyMapDto>((resolve, reject) => {
          pending.push({ date, signal, resolve, reject });
          signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
        }),
      regime: async (id: string) => ({ id }),
    };
    TestBed.configureTestingModule({ providers: [{ provide: WorldLineApi, useValue: api }] });
    const data = TestBed.inject(AtlasData);
    const a = data.loadSovereignty('1939-09-01');
    expect(data.mapDataLoading()).toBe(true);
    const b = data.loadSovereignty('1944-10-01');
    expect(pending[0].signal?.aborted).toBe(true);
    expect(pending[1].signal?.aborted).toBe(false);
    // 舊請求的回應（即使沒被瀏覽器取消、仍然晚到）不會套用
    pending[0].resolve(sov('1939-09-01'));
    pending[1].resolve(sov('1944-10-01'));
    await Promise.all([a, b]);
    expect(data.sovereignty()?.date).toBe('1944-10-01');
    expect(data.sovereigntyStatus()).toBe('ok');
    expect(data.mapDataLoading()).toBe(false);
  });

  it('被中止的請求不把狀態標成錯誤', async () => {
    const api = {
      sovereignty: (_d: string, signal?: AbortSignal) =>
        new Promise<SovereigntyMapDto>((resolve, reject) => {
          signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
          if (_d === '1944-10-01') resolve(sov(_d));
        }),
      regime: async (id: string) => ({ id }),
    };
    TestBed.configureTestingModule({ providers: [{ provide: WorldLineApi, useValue: api }] });
    const data = TestBed.inject(AtlasData);
    const a = data.loadSovereignty('1939-09-01');
    const b = data.loadSovereignty('1944-10-01');
    await Promise.all([a, b]);
    expect(data.sovereigntyStatus()).toBe('ok');
  });
});
