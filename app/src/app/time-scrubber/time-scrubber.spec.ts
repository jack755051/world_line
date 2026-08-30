import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TimeScrubberComponent } from './time-scrubber';
import { TimelineState } from '../core/time/timeline-state';
import { RegimeFocusState } from '../core/regime/regime-focus-state';

describe('TimeScrubberComponent', () => {
  let httpMock: HttpTestingController;

  // TimelineState 是 providedIn: 'root' 的單例——不 reset 的話，前一個 it() 改過的
  // year 值會留到下一個 it()，測試結果會互相影響（跟 map.spec.ts 需要
  // resetTestingModule() 是同一個道理）。RegimeFocusState（任務 3.7 AC#2）內部用
  // HttpClient 查存續區間，這個元件現在會注入它，需要提供 HttpClient/HttpClientTesting。
  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('顯示 TimelineState 目前的年份', () => {
    const fixture = TestBed.createComponent(TimeScrubberComponent);
    fixture.detectChanges();

    const yearText = fixture.nativeElement.querySelector('.time-scrubber-year').textContent;
    expect(yearText).toContain(String(TimelineState.DEFAULT_YEAR));
  });

  it('拖動 range input 會更新 TimelineState.year', () => {
    const fixture = TestBed.createComponent(TimeScrubberComponent);
    fixture.detectChanges();
    const timeline = TestBed.inject(TimelineState);

    const input: HTMLInputElement = fixture.nativeElement.querySelector('.time-scrubber-input');
    input.value = '150';
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    expect(timeline.year()).toBe(150);
    expect(fixture.nativeElement.querySelector('.time-scrubber-year').textContent).toContain('150');
  });

  it('range input 的上下限對到 TimelineState 定義的範圍', () => {
    const fixture = TestBed.createComponent(TimeScrubberComponent);
    fixture.detectChanges();

    const input: HTMLInputElement = fixture.nativeElement.querySelector('.time-scrubber-input');
    expect(input.min).toBe(String(TimelineState.MIN_YEAR));
    expect(input.max).toBe(String(TimelineState.MAX_YEAR));
  });

  describe('政權存續區間色帶（任務 3.7 AC#2）', () => {
    it('沒有聚焦任何政權時，不顯示色帶', () => {
      const fixture = TestBed.createComponent(TimeScrubberComponent);
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('.time-scrubber-lifetime-band')).toBeNull();
    });

    it('聚焦政權後，色帶依存續區間換算成拉桿範圍內的百分比定位', () => {
      const focusState = TestBed.inject(RegimeFocusState);
      focusState.toggle('r-a');
      httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-a/territories').flush({
        statusCode: 200,
        message: 'FETCH_SUCCESS',
        data: {
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              properties: { id: 'row-0', regimeId: 'r-a', isDisputed: false, startYear: 100, endYear: 130 },
              geometry: { type: 'MultiPolygon', coordinates: [[[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]] },
            },
          ],
        },
      });

      const fixture = TestBed.createComponent(TimeScrubberComponent);
      fixture.detectChanges();

      const band: HTMLElement = fixture.nativeElement.querySelector('.time-scrubber-lifetime-band');
      expect(band).not.toBeNull();
      // TimelineState 範圍是 1-300（見 timeline-state.ts），存續區間 100-130：
      // left = (100-1)/(300-1)*100 ≈ 33.11%，width = (130-100)/(300-1)*100 ≈ 10.03%。
      const totalSpan = TimelineState.MAX_YEAR - TimelineState.MIN_YEAR;
      const expectedLeft = ((100 - TimelineState.MIN_YEAR) / totalSpan) * 100;
      const expectedWidth = (30 / totalSpan) * 100;
      expect(band.style.left).toBe(`${expectedLeft}%`);
      expect(band.style.width).toBe(`${expectedWidth}%`);
    });
  });
});
