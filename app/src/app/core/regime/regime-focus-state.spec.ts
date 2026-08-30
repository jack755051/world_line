import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import type { FeatureCollection, MultiPolygon } from 'geojson';
import { RegimeFocusState } from './regime-focus-state';
import { TimelineState } from '../time/timeline-state';
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

// toggle() 除了查存續區間（territories），2026-08-30 起也會同步查 AC#3 的兩個互動端點
// （events/relations，見 RegimeFocusState 類別文件的「離散動作直接同步查，不用等
// debounce」說明）——不 flush 掉這兩個，httpMock.verify() 在 afterEach 會噴「還有
// 未處理的請求」。
function flushInteractions(
  httpMock: HttpTestingController,
  regimeId: string,
  year: number,
  events: unknown[] = [],
  relations: unknown[] = [],
): void {
  httpMock
    .expectOne((r) => r.urlWithParams === `/api/v1/regimes/${regimeId}/events?year=${year}`)
    .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: events });
  httpMock
    .expectOne((r) => r.urlWithParams === `/api/v1/regimes/${regimeId}/relations?year=${year}`)
    .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: relations });
}

function waitForDebounce(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 200));
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
    flushInteractions(httpMock, 'r-a', TimelineState.DEFAULT_YEAR);

    expect(state.lifetimeRange()).toEqual({ minYear: 220, maxYear: 249 });
  });

  it('再次 toggle 同一個政權會取消聚焦（toggle 行為），不會再打一次 API', () => {
    state.toggle('r-a');
    httpMock
      .expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-a/territories')
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: territoryFeatureCollection([{ startYear: 220, endYear: 226 }]) });
    flushInteractions(httpMock, 'r-a', TimelineState.DEFAULT_YEAR);

    state.toggle('r-a');

    expect(state.focusedRegimeId()).toBeNull();
    expect(state.lifetimeRange()).toBeNull();
    expect(state.neighborRegimeIds()).toEqual([]);
    httpMock.expectNone(() => true);
  });

  it('聚焦另一個政權時，前一個政權還沒回應的過期請求就算之後被 flush，也不會覆蓋新的聚焦狀態', () => {
    state.toggle('r-a');
    const staleReq = httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-a/territories');
    const staleEventsReq = httpMock.expectOne((r) => r.urlWithParams === `/api/v1/regimes/r-a/events?year=${TimelineState.DEFAULT_YEAR}`);
    const staleRelationsReq = httpMock.expectOne((r) => r.urlWithParams === `/api/v1/regimes/r-a/relations?year=${TimelineState.DEFAULT_YEAR}`);

    state.toggle('r-b'); // 還沒等 r-a 的請求回來就換聚焦目標
    const currentReq = httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-b/territories');

    // 過期的 r-a 請求這時候才回應——不該影響目前已經是 r-b 的聚焦狀態。
    staleReq.flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: territoryFeatureCollection([{ startYear: 1, endYear: 2 }]),
    });
    staleEventsReq.flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: [{ eventId: 'stale', eventName: 'stale', otherRegimeId: 'x', startEdtf: '0001', endEdtf: '0001' }] });
    staleRelationsReq.flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: [] });
    expect(state.focusedRegimeId()).toBe('r-b');
    expect(state.lifetimeRange()).toBeNull(); // 還沒被過期請求誤植
    expect(state.eventInteractions()).toEqual([]); // 過期請求的事件互動也沒有滲進來

    currentReq.flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: territoryFeatureCollection([{ startYear: 265, endYear: 280 }]),
    });
    flushInteractions(httpMock, 'r-b', TimelineState.DEFAULT_YEAR);
    expect(state.lifetimeRange()).toEqual({ minYear: 265, maxYear: 280 });
  });

  it('clear() 重置所有聚焦相關狀態', () => {
    state.toggle('r-a');
    httpMock
      .expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-a/territories')
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: territoryFeatureCollection([{ startYear: 220, endYear: 226 }]) });
    flushInteractions(httpMock, 'r-a', TimelineState.DEFAULT_YEAR);
    state.setNeighbors(['r-b']);
    state.setOtherContemporaryRegimes(['r-c']);

    state.clear();

    expect(state.focusedRegimeId()).toBeNull();
    expect(state.lifetimeRange()).toBeNull();
    expect(state.neighborRegimeIds()).toEqual([]);
    expect(state.otherContemporaryRegimeIds()).toEqual([]);
    expect(state.eventInteractions()).toEqual([]);
    expect(state.relationInteractions()).toEqual([]);
  });

  it('setNeighbors() 直接寫入周邊政權清單', () => {
    state.setNeighbors(['r-b', 'r-c']);
    expect(state.neighborRegimeIds()).toEqual(['r-b', 'r-c']);
  });

  it('setOtherContemporaryRegimes() 直接寫入「同時期但不相鄰」的政權清單', () => {
    state.setOtherContemporaryRegimes(['r-d']);
    expect(state.otherContemporaryRegimeIds()).toEqual(['r-d']);
  });

  describe('AC#3 互動清單（task 2.9/2.10）', () => {
    it('toggle() 會同步（不用等 debounce）查詢離散事件互動跟持續性關係互動，並換算出 otherRegimeId', () => {
      state.toggle('r-a');
      httpMock
        .expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-a/territories')
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: territoryFeatureCollection([{ startYear: 220, endYear: 226 }]) });

      httpMock
        .expectOne((r) => r.urlWithParams === `/api/v1/regimes/r-a/events?year=${TimelineState.DEFAULT_YEAR}`)
        .flush({
          statusCode: 200,
          message: 'FETCH_SUCCESS',
          data: [{ eventId: 'event-x', eventName: '某戰役', otherRegimeId: 'r-b', startEdtf: '0225', endEdtf: '0225' }],
        });
      httpMock
        .expectOne((r) => r.urlWithParams === `/api/v1/regimes/r-a/relations?year=${TimelineState.DEFAULT_YEAR}`)
        .flush({
          statusCode: 200,
          message: 'FETCH_SUCCESS',
          // regimeAId 是 r-b（不是查詢用的 r-a）——驗證 otherRegimeId 換算不是硬取
          // 某一個固定欄位，是真的比對查詢的 regimeId。
          data: [{ id: 'rel-1', regimeAId: 'r-b', regimeBId: 'r-a', relationType: '同盟', description: null }],
        });

      expect(state.eventInteractions()).toEqual([{ eventId: 'event-x', eventName: '某戰役', otherRegimeId: 'r-b', startEdtf: '0225', endEdtf: '0225' }]);
      expect(state.relationInteractions()).toEqual([
        { id: 'rel-1', relationType: '同盟', otherRegimeId: 'r-b', description: null },
      ]);
    });

    it('已經聚焦時拖拉桿換年份，debounce 過後會重新查詢互動清單（用新年份）', async () => {
      state.toggle('r-a');
      httpMock
        .expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-a/territories')
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: territoryFeatureCollection([{ startYear: 200, endYear: 300 }]) });
      flushInteractions(httpMock, 'r-a', TimelineState.DEFAULT_YEAR);

      const timeline = TestBed.inject(TimelineState);
      timeline.year.set(230);
      await waitForDebounce();

      flushInteractions(httpMock, 'r-a', 230, [{ eventId: 'event-y', eventName: '換年份後的事件', otherRegimeId: 'r-c', startEdtf: '0230', endEdtf: '0230' }]);
      expect(state.eventInteractions()).toEqual([{ eventId: 'event-y', eventName: '換年份後的事件', otherRegimeId: 'r-c', startEdtf: '0230', endEdtf: '0230' }]);
    });

    it('沒有聚焦任何政權時，拖拉桿換年份不會打互動查詢', async () => {
      const timeline = TestBed.inject(TimelineState);
      timeline.year.set(230);
      await waitForDebounce();

      httpMock.expectNone(() => true);
    });
  });
});
