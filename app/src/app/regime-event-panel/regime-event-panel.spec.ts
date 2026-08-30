import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { RegimeEventPanelComponent } from './regime-event-panel';
import { RegimeFocusState } from '../core/regime/regime-focus-state';
import { RegimeDirectoryService } from '../core/regime/regime-directory.service';
import { TimelineState } from '../core/time/timeline-state';
import { EventDrawerState } from '../core/event/event-drawer-state';

describe('RegimeEventPanelComponent', () => {
  let httpMock: HttpTestingController;
  let focusState: RegimeFocusState;
  let directory: RegimeDirectoryService;
  let timeline: TimelineState;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    httpMock = TestBed.inject(HttpTestingController);
    focusState = TestBed.inject(RegimeFocusState);
    directory = TestBed.inject(RegimeDirectoryService);
    timeline = TestBed.inject(TimelineState);

    directory.ensureLoaded().subscribe();
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: [
        {
          id: 'r-wei',
          selfName: '魏',
          status: 'succeeded',
          predecessorRegimeId: null,
          originTransitionType: null,
          destroyedByRegimeId: null,
        },
        {
          id: 'r-shuhan',
          selfName: '蜀漢',
          status: 'conquered',
          predecessorRegimeId: null,
          originTransitionType: null,
          destroyedByRegimeId: 'r-wei',
        },
        {
          id: 'r-wu',
          selfName: '吳',
          status: 'conquered',
          predecessorRegimeId: null,
          originTransitionType: null,
          destroyedByRegimeId: null,
        },
      ],
    });
  });

  afterEach(() => {
    httpMock.verify();
  });

  // 同 regime-focus-panel.spec.ts 的理由：toggle() 除了查存續區間（territories），
  // 2026-08-30 起也會同步查 AC#3 的兩個互動端點（events/relations）。
  function flushFocusRequests(
    regimeId: string,
    territoryRows: Array<{ startYear: number; endYear: number }>,
    events: unknown[] = [],
    relations: unknown[] = [],
  ): void {
    httpMock.expectOne((r) => r.urlWithParams === `/api/v1/regimes/${regimeId}/territories`).flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: {
        type: 'FeatureCollection',
        features: territoryRows.map((row, i) => ({
          type: 'Feature',
          properties: { id: `row-${i}`, regimeId, isDisputed: false, ...row },
          geometry: { type: 'MultiPolygon', coordinates: [[[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]] },
        })),
      },
    });

    const year = timeline.year();
    httpMock
      .expectOne((r) => r.urlWithParams === `/api/v1/regimes/${regimeId}/events?year=${year}`)
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: events });
    httpMock
      .expectOne((r) => r.urlWithParams === `/api/v1/regimes/${regimeId}/relations?year=${year}`)
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: relations });
  }

  it('沒有聚焦任何政權時，不渲染任何內容', () => {
    const fixture = TestBed.createComponent(RegimeEventPanelComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-event-panel')).toBeNull();
  });

  it('沒有跟周邊政權的互動記錄時，不渲染任何內容（跟側欄面板的空狀態文案不同）', () => {
    focusState.toggle('r-wei');
    flushFocusRequests('r-wei', [{ startYear: 220, endYear: 226 }]);
    focusState.setNeighbors(['r-shuhan']);

    const fixture = TestBed.createComponent(RegimeEventPanelComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-event-panel')).toBeNull();
  });

  it('離散事件跟持續性關係都只顯示跟目前周邊政權有交集的那些', () => {
    focusState.toggle('r-wei');
    flushFocusRequests(
      'r-wei',
      [{ startYear: 220, endYear: 226 }],
      [
        { eventId: 'event-a', eventName: '跟蜀漢的戰役', otherRegimeId: 'r-shuhan', startEdtf: '0221', endEdtf: '0221' }, // r-shuhan 是周邊，該顯示
        { eventId: 'event-b', eventName: '跟吳的戰役', otherRegimeId: 'r-wu', startEdtf: '0222', endEdtf: '0222' }, // r-wu 不是周邊，不該顯示
      ],
      [{ id: 'rel-a', regimeAId: 'r-shuhan', regimeBId: 'r-wei', relationType: '同盟', description: '測試關係' }],
    );
    focusState.setNeighbors(['r-shuhan']);

    const fixture = TestBed.createComponent(RegimeEventPanelComponent);
    fixture.detectChanges();

    const items = [...fixture.nativeElement.querySelectorAll('.regime-event-panel-list li')].map((el: Element) =>
      el.textContent?.replace(/\s+/g, ' ').trim(),
    );
    expect(items).toHaveLength(2);
    expect(items[0]).toContain('跟蜀漢的戰役');
    expect(items[0]).toContain('蜀漢');
    expect(items[0]).toContain('西元 221 年');
    expect(items[1]).toContain('同盟');
    expect(items[1]).toContain('測試關係');
  });

  it('點擊離散事件會打開事件詳情抽屜（EventDrawerState.open）', () => {
    focusState.toggle('r-wei');
    flushFocusRequests(
      'r-wei',
      [{ startYear: 220, endYear: 226 }],
      [{ eventId: 'event-a', eventName: '跟蜀漢的戰役', otherRegimeId: 'r-shuhan', startEdtf: '0221', endEdtf: '0221' }],
    );
    focusState.setNeighbors(['r-shuhan']);

    const fixture = TestBed.createComponent(RegimeEventPanelComponent);
    fixture.detectChanges();

    const trigger: HTMLButtonElement = fixture.nativeElement.querySelector('.regime-event-panel-trigger');
    trigger.click();

    const eventDrawer = TestBed.inject(EventDrawerState);
    expect(eventDrawer.openEventId()).toBe('event-a');
  });
});
