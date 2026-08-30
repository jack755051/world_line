import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import type { FeatureCollection, MultiPolygon } from 'geojson';
import { RegimeFocusState } from './regime-focus-state';
import type { TerritoryFeatureProperties } from '../geometry/territory-styling';

function territoryFeatureCollection(
  rows: Array<{ startYear: number; endYear: number }>,
): FeatureCollection<MultiPolygon, TerritoryFeatureProperties> {
  return {
    type: 'FeatureCollection',
    features: rows.map((row, i) => ({
      type: 'Feature',
      properties: { id: `row-${i}`, regimeId: 'r-a', isDisputed: false, ...row },
      geometry: { type: 'MultiPolygon', coordinates: [[[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]] },
    })),
  };
}

describe('RegimeFocusState', () => {
  let state: RegimeFocusState;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    state = TestBed.inject(RegimeFocusState);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('toggle(id) 聚焦一個政權，並打 GET /api/v1/regimes/:id/territories 查存續區間', () => {
    state.toggle('r-a');

    expect(state.focusedRegimeId()).toBe('r-a');

    httpMock
      .expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-a/territories')
      .flush({
        statusCode: 200,
        message: 'FETCH_SUCCESS',
        data: territoryFeatureCollection([{ startYear: 220, endYear: 226 }, { startYear: 226, endYear: 249 }]),
      });

    expect(state.lifetimeRange()).toEqual({ minYear: 220, maxYear: 249 });
  });

  it('再次 toggle 同一個政權會取消聚焦（toggle 行為），不會再打一次 API', () => {
    state.toggle('r-a');
    httpMock
      .expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-a/territories')
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: territoryFeatureCollection([{ startYear: 220, endYear: 226 }]) });

    state.toggle('r-a');

    expect(state.focusedRegimeId()).toBeNull();
    expect(state.lifetimeRange()).toBeNull();
    expect(state.neighborRegimeIds()).toEqual([]);
    httpMock.expectNone(() => true);
  });

  it('聚焦另一個政權時，前一個政權還沒回應的過期請求就算之後被 flush，也不會覆蓋新的聚焦狀態', () => {
    state.toggle('r-a');
    const staleReq = httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-a/territories');

    state.toggle('r-b'); // 還沒等 r-a 的請求回來就換聚焦目標
    const currentReq = httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-b/territories');

    // 過期的 r-a 請求這時候才回應——不該影響目前已經是 r-b 的聚焦狀態。
    staleReq.flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: territoryFeatureCollection([{ startYear: 1, endYear: 2 }]),
    });
    expect(state.focusedRegimeId()).toBe('r-b');
    expect(state.lifetimeRange()).toBeNull(); // 還沒被過期請求誤植

    currentReq.flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: territoryFeatureCollection([{ startYear: 265, endYear: 280 }]),
    });
    expect(state.lifetimeRange()).toEqual({ minYear: 265, maxYear: 280 });
  });

  it('clear() 重置所有聚焦相關狀態', () => {
    state.toggle('r-a');
    httpMock
      .expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-a/territories')
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: territoryFeatureCollection([{ startYear: 220, endYear: 226 }]) });
    state.setNeighbors(['r-b']);
    state.setOtherContemporaryRegimes(['r-c']);

    state.clear();

    expect(state.focusedRegimeId()).toBeNull();
    expect(state.lifetimeRange()).toBeNull();
    expect(state.neighborRegimeIds()).toEqual([]);
    expect(state.otherContemporaryRegimeIds()).toEqual([]);
  });

  it('setNeighbors() 直接寫入周邊政權清單', () => {
    state.setNeighbors(['r-b', 'r-c']);
    expect(state.neighborRegimeIds()).toEqual(['r-b', 'r-c']);
  });

  it('setOtherContemporaryRegimes() 直接寫入「同時期但不相鄰」的政權清單', () => {
    state.setOtherContemporaryRegimes(['r-d']);
    expect(state.otherContemporaryRegimeIds()).toEqual(['r-d']);
  });

  describe('任務 3.14：lifetimeLoadState（PRD §8「政權聚焦頁」四態齊備）', () => {
    it('toggle() 後、回應還沒回來前是 loading，成功回應後變成 loaded', () => {
      state.toggle('r-a');
      expect(state.lifetimeLoadState()).toBe('loading');

      httpMock
        .expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-a/territories')
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: territoryFeatureCollection([{ startYear: 220, endYear: 226 }]) });

      expect(state.lifetimeLoadState()).toBe('loaded');
    });

    it('查詢失敗時變成 error，retryLifetimeRange() 會重新查詢並在成功後變回 loaded', () => {
      state.toggle('r-a');
      httpMock
        .expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-a/territories')
        .flush({ statusCode: 500, message: 'INTERNAL_ERROR', data: null }, { status: 500, statusText: 'Server Error' });

      expect(state.lifetimeLoadState()).toBe('error');

      state.retryLifetimeRange();
      expect(state.lifetimeLoadState()).toBe('loading');

      httpMock
        .expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-a/territories')
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: territoryFeatureCollection([{ startYear: 220, endYear: 226 }]) });

      expect(state.lifetimeLoadState()).toBe('loaded');
      expect(state.lifetimeRange()).toEqual({ minYear: 220, maxYear: 226 });
    });

    it('沒有聚焦任何政權時 retryLifetimeRange() 是 no-op，不會打 API', () => {
      state.retryLifetimeRange();
      httpMock.expectNone(() => true);
    });
  });
});
