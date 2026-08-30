import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { RegimeEventPanelComponent } from './regime-event-panel';
import { RegimeFocusState } from '../core/regime/regime-focus-state';
import { RegimeDirectoryService } from '../core/regime/regime-directory.service';
import { TimelineState } from '../core/time/timeline-state';

describe('RegimeEventPanelComponent', () => {
  let httpMock: HttpTestingController;
  let focusState: RegimeFocusState;
  let directory: RegimeDirectoryService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    httpMock = TestBed.inject(HttpTestingController);
    focusState = TestBed.inject(RegimeFocusState);
    directory = TestBed.inject(RegimeDirectoryService);

    directory.ensureLoaded().subscribe();
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: [
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

  function focusAndFlushTerritories(regimeId: string): void {
    focusState.toggle(regimeId);
    httpMock.expectOne((r) => r.urlWithParams === `/api/v1/regimes/${regimeId}/territories`).flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: { type: 'FeatureCollection', features: [] },
    });
  }

  function flushEvents(regimeId: string, data: unknown[]): void {
    httpMock
      .expectOne((r) => r.urlWithParams === `/api/v1/regimes/${regimeId}/events`)
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data });
  }

  it('沒有聚焦任何政權時，不渲染任何內容', () => {
    const fixture = TestBed.createComponent(RegimeEventPanelComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-event-panel')).toBeNull();
  });

  it('查無事件時，不渲染任何內容', () => {
    focusAndFlushTerritories('r-wu');

    const fixture = TestBed.createComponent(RegimeEventPanelComponent);
    fixture.detectChanges();
    flushEvents('r-wu', []);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-event-panel')).toBeNull();
  });

  it('抬頭顯示政權名稱，清單依 startDecimal 排序、同一事件去重，最多顯示 5 筆', () => {
    focusAndFlushTerritories('r-wu');

    const fixture = TestBed.createComponent(RegimeEventPanelComponent);
    fixture.detectChanges();
    flushEvents('r-wu', [
      { eventId: 'event-b', eventName: '第二戰役', otherRegimeId: 'r-x', startEdtf: '0225', endEdtf: '0225', startDecimal: 225 },
      { eventId: 'event-a', eventName: '赤壁之戰', otherRegimeId: 'r-y', startEdtf: '0208', endEdtf: '0208', startDecimal: 208 },
      // event-a 因為跟另一個政權也有互動而重複出現一次——去重後應該只剩一筆。
      { eventId: 'event-a', eventName: '赤壁之戰', otherRegimeId: 'r-z', startEdtf: '0208', endEdtf: '0208', startDecimal: 208 },
      { eventId: 'event-c', eventName: '第三事件', otherRegimeId: 'r-x', startEdtf: '0230', endEdtf: '0230', startDecimal: 230 },
      { eventId: 'event-d', eventName: '第四事件', otherRegimeId: 'r-x', startEdtf: '0240', endEdtf: '0240', startDecimal: 240 },
      { eventId: 'event-e', eventName: '第五事件', otherRegimeId: 'r-x', startEdtf: '0250', endEdtf: '0250', startDecimal: 250 },
      { eventId: 'event-f', eventName: '第六事件（超過上限，不該顯示）', otherRegimeId: 'r-x', startEdtf: '0260', endEdtf: '0260', startDecimal: 260 },
    ]);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-event-panel-title').textContent).toBe('吳');
    const items = [...fixture.nativeElement.querySelectorAll('.regime-event-panel-trigger')].map(
      (el: Element) => el.textContent?.replace(/\s+/g, ' ').trim(),
    );
    expect(items).toEqual(['208年赤壁之戰 ▸', '225年第二戰役 ▸', '230年第三事件 ▸', '240年第四事件 ▸', '250年第五事件 ▸']);
  });

  it('點擊標題展開事件：查 GET /api/v1/events/:id、時間拉桿跳到事件年份、顯示三段內容', () => {
    focusAndFlushTerritories('r-wu');

    const fixture = TestBed.createComponent(RegimeEventPanelComponent);
    fixture.detectChanges();
    flushEvents('r-wu', [
      { eventId: 'event-a', eventName: '赤壁之戰', otherRegimeId: 'r-y', startEdtf: '0208', endEdtf: '0208', startDecimal: 208 },
    ]);
    fixture.detectChanges();

    const trigger: HTMLButtonElement = fixture.nativeElement.querySelector('.regime-event-panel-trigger');
    trigger.click();
    fixture.detectChanges();

    const timeline = TestBed.inject(TimelineState);
    expect(timeline.year()).toBe(208);
    expect(fixture.nativeElement.querySelector('.regime-event-panel-status')?.textContent).toContain('載入中');

    httpMock.expectOne((r) => r.url === '/api/v1/events/event-a').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: {
        id: 'event-a',
        name: '赤壁之戰',
        startEdtf: '0208',
        endEdtf: '0208',
        sections: {
          background: '曹操率軍南下',
          turning_points: ['黃蓋詐降'],
          impact: '奠定三國鼎立',
        },
      },
    });
    fixture.detectChanges();

    const detailText = fixture.nativeElement.querySelector('.regime-event-panel-detail').textContent as string;
    expect(detailText).toContain('背景起因');
    expect(detailText).toContain('曹操率軍南下');
    expect(detailText).toContain('關鍵轉折時間點');
    expect(detailText).toContain('黃蓋詐降');
    expect(detailText).toContain('歷史影響');
    expect(detailText).toContain('奠定三國鼎立');
  });

  it('sections 為 null 時顯示空狀態文案', () => {
    focusAndFlushTerritories('r-wu');

    const fixture = TestBed.createComponent(RegimeEventPanelComponent);
    fixture.detectChanges();
    flushEvents('r-wu', [
      { eventId: 'event-a', eventName: '漢禪魏', otherRegimeId: 'r-y', startEdtf: '0220', endEdtf: '0220', startDecimal: 220 },
    ]);
    fixture.detectChanges();

    fixture.nativeElement.querySelector('.regime-event-panel-trigger').click();
    fixture.detectChanges();
    httpMock.expectOne((r) => r.url === '/api/v1/events/event-a').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: { id: 'event-a', name: '漢禪魏', startEdtf: '0220', endEdtf: '0220', sections: null },
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-event-panel-empty')?.textContent).toContain('還沒有詳細內容');
  });

  it('再次點擊已展開的標題會收合', () => {
    focusAndFlushTerritories('r-wu');

    const fixture = TestBed.createComponent(RegimeEventPanelComponent);
    fixture.detectChanges();
    flushEvents('r-wu', [
      { eventId: 'event-a', eventName: '赤壁之戰', otherRegimeId: 'r-y', startEdtf: '0208', endEdtf: '0208', startDecimal: 208 },
    ]);
    fixture.detectChanges();

    const trigger: HTMLButtonElement = fixture.nativeElement.querySelector('.regime-event-panel-trigger');
    trigger.click();
    fixture.detectChanges();
    httpMock.expectOne((r) => r.url === '/api/v1/events/event-a').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: { id: 'event-a', name: '赤壁之戰', startEdtf: '0208', endEdtf: '0208', sections: null },
    });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.regime-event-panel-detail')).not.toBeNull();

    trigger.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-event-panel-detail')).toBeNull();
  });

  it('收合後重新展開同一筆事件，會用快取，不會重打 API', () => {
    focusAndFlushTerritories('r-wu');

    const fixture = TestBed.createComponent(RegimeEventPanelComponent);
    fixture.detectChanges();
    flushEvents('r-wu', [
      { eventId: 'event-a', eventName: '赤壁之戰', otherRegimeId: 'r-y', startEdtf: '0208', endEdtf: '0208', startDecimal: 208 },
    ]);
    fixture.detectChanges();

    const trigger: HTMLButtonElement = fixture.nativeElement.querySelector('.regime-event-panel-trigger');
    trigger.click();
    fixture.detectChanges();
    httpMock.expectOne((r) => r.url === '/api/v1/events/event-a').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: { id: 'event-a', name: '赤壁之戰', startEdtf: '0208', endEdtf: '0208', sections: null },
    });
    fixture.detectChanges();

    trigger.click(); // 收合
    fixture.detectChanges();
    trigger.click(); // 重新展開——不該再打一次 GET /api/v1/events/event-a
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-event-panel-empty')?.textContent).toContain('還沒有詳細內容');
  });

  it('切換聚焦到別的政權時，清單與展開狀態會重置，並重新查詢新政權的事件', () => {
    focusAndFlushTerritories('r-wu');

    const fixture = TestBed.createComponent(RegimeEventPanelComponent);
    fixture.detectChanges();
    flushEvents('r-wu', [
      { eventId: 'event-a', eventName: '赤壁之戰', otherRegimeId: 'r-y', startEdtf: '0208', endEdtf: '0208', startDecimal: 208 },
    ]);
    fixture.detectChanges();
    fixture.nativeElement.querySelector('.regime-event-panel-trigger').click();
    fixture.detectChanges();
    httpMock.expectOne((r) => r.url === '/api/v1/events/event-a').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: { id: 'event-a', name: '赤壁之戰', startEdtf: '0208', endEdtf: '0208', sections: null },
    });
    fixture.detectChanges();

    focusAndFlushTerritories('r-wei'); // toggle 到新政權——r-wu 已聚焦，toggle('r-wei') 直接切換不用先取消
    fixture.detectChanges();

    // 舊政權沒有 flush 過的事件請求已經被上面的 flushEvents('r-wu', ...) 處理掉，這裡
    // 應該看到新政權 r-wei 的事件查詢，且畫面上舊的展開內容已經收合。
    expect(fixture.nativeElement.querySelector('.regime-event-panel-detail')).toBeNull();
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-wei/events').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: [],
    });
  });
});
