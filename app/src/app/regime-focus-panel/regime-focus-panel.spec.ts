import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { RegimeFocusPanelComponent } from './regime-focus-panel';
import { RegimeFocusState } from '../core/regime/regime-focus-state';
import { RegimeDirectoryService } from '../core/regime/regime-directory.service';
import { TimelineState } from '../core/time/timeline-state';

describe('RegimeFocusPanelComponent', () => {
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
        { id: 'r-wei', selfName: '魏' },
        { id: 'r-shuhan', selfName: '蜀漢' },
        { id: 'r-wu', selfName: '吳' },
      ],
    });
  });

  afterEach(() => {
    httpMock.verify();
  });

  function flushLifetime(regimeId: string, rows: Array<{ startYear: number; endYear: number }>): void {
    httpMock.expectOne((r) => r.urlWithParams === `/api/v1/regimes/${regimeId}/territories`).flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: {
        type: 'FeatureCollection',
        features: rows.map((row, i) => ({
          type: 'Feature',
          properties: { id: `row-${i}`, regimeId, isDisputed: false, ...row },
          geometry: { type: 'MultiPolygon', coordinates: [[[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]] },
        })),
      },
    });
  }

  it('沒有聚焦任何政權時，不渲染面板', () => {
    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-focus-panel')).toBeNull();
  });

  it('聚焦政權後顯示面板，標題是該政權的名稱', () => {
    focusState.toggle('r-wei');
    flushLifetime('r-wei', [{ startYear: 220, endYear: 226 }]);
    focusState.setNeighbors(['r-shuhan', 'r-wu']);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    const panel = fixture.nativeElement.querySelector('.regime-focus-panel');
    expect(panel).not.toBeNull();
    expect(fixture.nativeElement.querySelector('h2').textContent).toBe('魏');
  });

  it('周邊政權清單依名稱排序顯示', () => {
    focusState.toggle('r-wei');
    flushLifetime('r-wei', [{ startYear: 220, endYear: 226 }]);
    focusState.setNeighbors(['r-wu', 'r-shuhan']); // 刻意用非排序順序傳入

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    const items = [...fixture.nativeElement.querySelectorAll('.regime-focus-panel-neighbor-list li')].map(
      (el: Element) => el.textContent,
    );
    expect(items).toEqual(['吳', '蜀漢']); // localeCompare('zh-Hant') 排序結果
  });

  it('沒有周邊政權時顯示空狀態文案，不是空清單', () => {
    focusState.toggle('r-wei');
    flushLifetime('r-wei', [{ startYear: 220, endYear: 226 }]);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-focus-panel-neighbor-list')).toBeNull();
    expect(fixture.nativeElement.querySelector('.regime-focus-panel-empty')).not.toBeNull();
  });

  it('目前年份早於聚焦政權存續區間時，顯示「尚未建立」警告', () => {
    timeline.year.set(100);
    focusState.toggle('r-wei');
    flushLifetime('r-wei', [{ startYear: 220, endYear: 226 }]);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-focus-panel-warning').textContent).toContain('尚未建立');
  });

  it('目前年份晚於聚焦政權存續區間時，顯示「已不存在」警告', () => {
    timeline.year.set(300);
    focusState.toggle('r-wei');
    flushLifetime('r-wei', [{ startYear: 220, endYear: 226 }]);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-focus-panel-warning').textContent).toContain('已不存在');
  });

  it('目前年份落在存續區間內時，不顯示警告', () => {
    timeline.year.set(222);
    focusState.toggle('r-wei');
    flushLifetime('r-wei', [{ startYear: 220, endYear: 226 }]);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-focus-panel-warning')).toBeNull();
  });

  it('點擊關閉按鈕會清除聚焦狀態', () => {
    focusState.toggle('r-wei');
    flushLifetime('r-wei', [{ startYear: 220, endYear: 226 }]);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    fixture.nativeElement.querySelector('.regime-focus-panel-close').click();

    expect(focusState.focusedRegimeId()).toBeNull();
  });
});
