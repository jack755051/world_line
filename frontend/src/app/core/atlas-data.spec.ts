import { TestBed } from '@angular/core/testing';
import { BOUNDARY_SOURCE_KEY } from './boundary-source';

// 這兩組測試針對 GeoJSON 備援路徑（開發環境 ?boundarySource=geojson）；預設已改 tiles（2026-11-04）
beforeEach(() => localStorage.setItem(BOUNDARY_SOURCE_KEY, 'geojson'));
afterEach(() => localStorage.removeItem(BOUNDARY_SOURCE_KEY));
import { AtlasData } from './atlas-data';
import { WorldLineApi } from './api/world-line-api';
import type { ControlMapDto, SovereigntyMapDto } from './api/api-types';

const sov = (date: string) => ({ date, featureCollection: { type: 'FeatureCollection', features: [] } }) as unknown as SovereigntyMapDto;

describe('AtlasData：快速連續跳日期', () => {
  it('新日期開始載入時中止舊請求；舊請求晚到也不蓋掉新資料；mapDataLoading 反映載入中', async () => {
    const pending: { date: string; signal?: AbortSignal; resolve: (v: SovereigntyMapDto) => void; reject: (e: unknown) => void }[] = [];
    const api = {
      sovereignty: (date: string, _zoom?: number, signal?: AbortSignal) =>
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
      sovereignty: (_d: string, _zoom?: number, signal?: AbortSignal) =>
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

describe('AtlasData：控制區依變動區間快取（移植自 992baba）', () => {
  const ctl = (date: string) => ({ date, featureCollection: { type: 'FeatureCollection', features: [] } }) as unknown as ControlMapDto;
  it('同一控制區區間換日期不重新請求；套用後預先載入前後相鄰區間；跨區間才請求新的', async () => {
    const calls: string[] = [];
    const api = {
      control: async (date: string) => {
        calls.push(date);
        return ctl(date);
      },
      timelineChangePoints: async () => ({ version: 1, points: ['1940-06-01'], controlPoints: ['1940-06-04', '1940-06-13', '1940-07-15'] }),
      regime: async (id: string) => ({ id }),
    };
    TestBed.configureTestingModule({ providers: [{ provide: WorldLineApi, useValue: api }] });
    const data = TestBed.inject(AtlasData);
    await data.loadChangePoints();
    expect(data.controlPoints()).toEqual(['1940-06-04', '1940-06-13', '1940-07-15']);
    await data.loadControl('1940-06-05');
    await new Promise((r) => setTimeout(r, 0));
    // 前景 1 次＋預先載入下一區間（06-13）與上一區間（06-03）
    expect(calls).toEqual(['1940-06-05', '1940-06-13', '1940-06-03']);
    await data.loadControl('1940-06-10'); // 同區間
    expect(calls.length).toBe(3);
    expect(data.controlDate()).toBe('1940-06-10');
    expect(data.controlStatus()).toBe('ok');
    await data.loadControl('1940-06-20'); // 06-13 區間已預先載入
    expect(calls.slice(0, 3)).toEqual(['1940-06-05', '1940-06-13', '1940-06-03']);
    expect(calls).not.toContain('1940-06-20');
  });

  it('沒有控制區變動點時退回逐日快取', async () => {
    const calls: string[] = [];
    const api = {
      control: async (date: string) => {
        calls.push(date);
        return ctl(date);
      },
      regime: async (id: string) => ({ id }),
    };
    TestBed.configureTestingModule({ providers: [{ provide: WorldLineApi, useValue: api }] });
    const data = TestBed.inject(AtlasData);
    await data.loadControl('1940-06-05');
    await data.loadControl('1940-06-06');
    await data.loadControl('1940-06-05');
    expect(calls).toEqual(['1940-06-05', '1940-06-06']);
  });
});
