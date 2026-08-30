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

  it('周邊政權清單依名稱排序顯示，用 Sanring Tag 呈現', () => {
    focusState.toggle('r-wei');
    flushLifetime('r-wei', [{ startYear: 220, endYear: 226 }]);
    focusState.setNeighbors(['r-wu', 'r-shuhan']); // 刻意用非排序順序傳入

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    const tagLists = fixture.nativeElement.querySelectorAll('.regime-focus-panel-tag-list');
    const items = [...tagLists[0].querySelectorAll('sanring-tag')].map((el: Element) => el.textContent?.trim());
    expect(items).toEqual(['吳', '蜀漢']); // localeCompare('zh-Hant') 排序結果
  });

  it('沒有周邊政權時顯示空狀態文案，不是空清單', () => {
    focusState.toggle('r-wei');
    flushLifetime('r-wei', [{ startYear: 220, endYear: 226 }]);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    const sections = fixture.nativeElement.querySelectorAll('sanring-collapsible');
    expect(sections[0].querySelector('.regime-focus-panel-tag-list')).toBeNull();
    expect(sections[0].querySelector('.regime-focus-panel-empty')).not.toBeNull();
  });

  it('存續期間顯示在標題下方（只有年份精度）', () => {
    focusState.toggle('r-wei');
    flushLifetime('r-wei', [{ startYear: 220, endYear: 226 }, { startYear: 226, endYear: 265 }]);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-focus-panel-lifespan').textContent).toBe('西元 220–265 年');
  });

  it('「同時期其他地區政權」清單依名稱排序顯示，用 Sanring Tag 呈現，不跟周邊政權混在一起', () => {
    focusState.toggle('r-wei');
    flushLifetime('r-wei', [{ startYear: 220, endYear: 226 }]);
    focusState.setNeighbors(['r-shuhan']);
    focusState.setOtherContemporaryRegimes(['r-wu']);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    const tagLists = fixture.nativeElement.querySelectorAll('.regime-focus-panel-tag-list');
    expect(tagLists).toHaveLength(2);
    const neighborItems = [...tagLists[0].querySelectorAll('sanring-tag')].map((el: Element) => el.textContent?.trim());
    const otherItems = [...tagLists[1].querySelectorAll('sanring-tag')].map((el: Element) => el.textContent?.trim());
    expect(neighborItems).toEqual(['蜀漢']);
    expect(otherItems).toEqual(['吳']);
  });

  it('沒有「同時期其他地區政權」時顯示空狀態文案', () => {
    focusState.toggle('r-wei');
    flushLifetime('r-wei', [{ startYear: 220, endYear: 226 }]);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    const sections = fixture.nativeElement.querySelectorAll('sanring-collapsible');
    expect(sections[1].querySelector('.regime-focus-panel-tag-list')).toBeNull();
    expect(sections[1].querySelector('.regime-focus-panel-empty')).not.toBeNull();
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

  it('周邊政權清單預設是展開的（不是預設收合，維持既有行為，只是加了可以收合的能力）', () => {
    focusState.toggle('r-wei');
    flushLifetime('r-wei', [{ startYear: 220, endYear: 226 }]);
    focusState.setNeighbors(['r-shuhan']);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    const content: HTMLElement = fixture.nativeElement.querySelector('[sanringCollapsibleContent]');
    expect(content.hidden).toBe(false);
  });

  it('點擊「同時期周邊政權」觸發鈕會收合/展開清單，不影響聚焦狀態本身', () => {
    focusState.toggle('r-wei');
    flushLifetime('r-wei', [{ startYear: 220, endYear: 226 }]);
    focusState.setNeighbors(['r-shuhan']);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    const trigger: HTMLElement = fixture.nativeElement.querySelector('.regime-focus-panel-section-trigger');
    const content: HTMLElement = fixture.nativeElement.querySelector('[sanringCollapsibleContent]');

    trigger.click();
    fixture.detectChanges();
    expect(content.hidden).toBe(true);
    expect(focusState.focusedRegimeId()).toBe('r-wei'); // 收合只影響這個區塊，不會連帶取消聚焦

    trigger.click();
    fixture.detectChanges();
    expect(content.hidden).toBe(false);
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
