import { TestBed } from '@angular/core/testing';
import { AtlasData } from './atlas-data';
import { WorldLineApi } from './api/world-line-api';
import { BOUNDARY_SOURCE_KEY } from './boundary-source';
import type { SovereigntyMapDto } from './api/api-types';

const feat = (recordId: string, regimeId: string) => ({ type: 'Feature', id: recordId, geometry: { type: 'MultiPolygon', coordinates: [] }, properties: { recordId, regimeId } });
const dto = (date: string, ...f: ReturnType<typeof feat>[]) => ({ date, featureCollection: { type: 'FeatureCollection', features: f } }) as unknown as SovereigntyMapDto;

describe('AtlasData（tiles 模式，§9 步驟 5）', () => {
  beforeEach(() => localStorage.setItem(BOUNDARY_SOURCE_KEY, 'tiles'));
  afterEach(() => localStorage.removeItem(BOUNDARY_SOURCE_KEY));

  it('換日期不取 /sovereignty；點選政權才取該政權幾何，放進 sovereignty；取消選取清掉', async () => {
    const calls: string[] = [];
    const api = {
      sovereignty: async () => { calls.push('sovereignty'); return dto('x'); },
      regimeGeometry: async (id: string, date: string) => { calls.push(`geom:${id}:${date}`); return dto(date, feat('r1', id)); },
      regimesBatch: async () => [],
    };
    TestBed.configureTestingModule({ providers: [{ provide: WorldLineApi, useValue: api }] });
    const data = TestBed.inject(AtlasData);
    expect(data.boundarySource).toBe('tiles');
    await data.loadSovereignty('1940-07-15');
    expect(calls).toEqual([]);
    const got = await data.loadRegimeSovereignty('g1', '1940-07-15');
    expect(got?.featureCollection.features.length).toBe(1);
    expect(data.sovereignty()?.featureCollection.features[0].properties.regimeId).toBe('g1');
    expect(data.sovereigntyShownFor()).toBe('1940-07-15');
    // 同政權同日同縮放：快取，不再請求
    await data.loadRegimeSovereignty('g1', '1940-07-15');
    expect(calls).toEqual(['geom:g1:1940-07-15']);
    data.clearRegimeSovereignty();
    expect(data.sovereignty()).toBeNull();
  });

  it('連續點兩個政權：先發的晚到不蓋掉後點的', async () => {
    const resolvers: Record<string, (v: SovereigntyMapDto) => void> = {};
    const api = {
      regimeGeometry: (id: string, date: string) => new Promise<SovereigntyMapDto>((r) => { resolvers[id] = (v) => r(v); void date; }),
      regimesBatch: async () => [],
    };
    TestBed.configureTestingModule({ providers: [{ provide: WorldLineApi, useValue: api }] });
    const data = TestBed.inject(AtlasData);
    const a = data.loadRegimeSovereignty('a', '1940-07-15');
    const b = data.loadRegimeSovereignty('b', '1940-07-15');
    resolvers['b'](dto('1940-07-15', feat('rb', 'b')));
    resolvers['a'](dto('1940-07-15', feat('ra', 'a')));
    await Promise.all([a, b]);
    expect(data.sovereignty()?.featureCollection.features[0].properties.regimeId).toBe('b');
  });

  it('蒙版：放大到更細的容差桶才重取被選政權幾何（5-3）；縮小或同桶不取', async () => {
    const calls: string[] = [];
    const api = {
      regimeGeometry: async (id: string, date: string, zoom?: number) => { calls.push(`${id}:${zoom}`); return dto(date, feat('r1', id)); },
      regimesBatch: async () => [],
    };
    TestBed.configureTestingModule({ providers: [{ provide: WorldLineApi, useValue: api }] });
    const data = TestBed.inject(AtlasData);
    const state = TestBed.inject((await import('./atlas-state')).AtlasState);
    state.mapZoom.set(4);
    await data.loadRegimeSovereignty('g1', '1940-07-15');
    data.refineRegimeSovereignty(4.4);
    state.mapZoom.set(7);
    data.refineRegimeSovereignty(7);
    await new Promise((r) => setTimeout(r, 0));
    state.mapZoom.set(3);
    data.refineRegimeSovereignty(3);
    expect(calls).toEqual(['g1:4', 'g1:7']);
    data.clearRegimeSovereignty();
    data.refineRegimeSovereignty(9);
    expect(calls.length).toBe(2);
  });
});
