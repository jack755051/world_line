import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { EventDrawerComponent } from './event-drawer';
import { EventDrawerState } from '../core/event/event-drawer-state';

describe('EventDrawerComponent', () => {
  let httpMock: HttpTestingController;
  let drawerState: EventDrawerState;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    httpMock = TestBed.inject(HttpTestingController);
    drawerState = TestBed.inject(EventDrawerState);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('openEventId 為 null 時不渲染任何內容', () => {
    const fixture = TestBed.createComponent(EventDrawerComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.event-drawer')).toBeNull();
  });

  it('打開事件時查 GET /api/v1/events/:id，載入中顯示 loading 文案', () => {
    const fixture = TestBed.createComponent(EventDrawerComponent);
    fixture.detectChanges();

    drawerState.open('event-chibi-208');
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.event-drawer')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('.event-drawer-status')?.textContent).toContain('載入中');

    httpMock.expectOne((r) => r.url === '/api/v1/events/event-chibi-208').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: { id: 'event-chibi-208', name: '赤壁之戰', startEdtf: '0208', endEdtf: '0208', sections: null },
    });
  });

  it('成功回應含 sections 時，三層手風琴依 background/turning_points/impact 個別顯示', () => {
    const fixture = TestBed.createComponent(EventDrawerComponent);
    fixture.detectChanges();

    drawerState.open('event-chibi-208');
    fixture.detectChanges();

    httpMock.expectOne((r) => r.url === '/api/v1/events/event-chibi-208').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: {
        id: 'event-chibi-208',
        name: '赤壁之戰',
        startEdtf: '0208',
        endEdtf: '0208',
        sections: {
          background: '曹操率軍南下欲統一天下',
          turning_points: ['黃蓋詐降', '火攻連環船'],
          impact: '奠定日後三國鼎立雛形',
        },
      },
    });
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('赤壁之戰');
    expect(text).toContain('西元 208 年');
    expect(text).toContain('背景起因');
    expect(text).toContain('曹操率軍南下欲統一天下');
    expect(text).toContain('關鍵轉折時間點');
    expect(text).toContain('黃蓋詐降');
    expect(text).toContain('火攻連環船');
    expect(text).toContain('歷史影響');
    expect(text).toContain('奠定日後三國鼎立雛形');
  });

  it('成功回應 sections 為 null 時，顯示空狀態文案，不顯示手風琴', () => {
    const fixture = TestBed.createComponent(EventDrawerComponent);
    fixture.detectChanges();

    drawerState.open('event-han-abdicates-wei-220');
    fixture.detectChanges();

    httpMock.expectOne((r) => r.url === '/api/v1/events/event-han-abdicates-wei-220').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: {
        id: 'event-han-abdicates-wei-220',
        name: '漢禪魏',
        startEdtf: '0220',
        endEdtf: '0220',
        sections: null,
      },
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.event-drawer-empty')?.textContent).toContain('還沒有詳細內容');
    expect(fixture.nativeElement.querySelectorAll('sanring-collapsible').length).toBe(0);
  });

  it('查詢失敗時顯示錯誤文案', () => {
    const fixture = TestBed.createComponent(EventDrawerComponent);
    fixture.detectChanges();

    drawerState.open('event-not-found');
    fixture.detectChanges();

    httpMock
      .expectOne((r) => r.url === '/api/v1/events/event-not-found')
      .flush(
        { statusCode: 404, message: 'EVENT_NOT_FOUND', data: null },
        { status: 404, statusText: 'Not Found' },
      );
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.event-drawer-status-error')?.textContent).toContain('載入失敗');
  });

  it('點擊關閉按鈕會把 EventDrawerState.openEventId 清回 null，畫面隨之收起', () => {
    const fixture = TestBed.createComponent(EventDrawerComponent);
    fixture.detectChanges();

    drawerState.open('event-chibi-208');
    fixture.detectChanges();
    httpMock.expectOne((r) => r.url === '/api/v1/events/event-chibi-208').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: { id: 'event-chibi-208', name: '赤壁之戰', startEdtf: '0208', endEdtf: '0208', sections: null },
    });
    fixture.detectChanges();

    const closeButton: HTMLButtonElement = fixture.nativeElement.querySelector('.event-drawer-close');
    closeButton.click();
    fixture.detectChanges();

    expect(drawerState.openEventId()).toBeNull();
    expect(fixture.nativeElement.querySelector('.event-drawer')).toBeNull();
  });
});
