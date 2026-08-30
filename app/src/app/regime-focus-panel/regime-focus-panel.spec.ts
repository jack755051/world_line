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
      // 2026-08-30 起這份 fixture 貼近真實種子資料的傳承關係（漢→魏→晉、漢→蜀漢／吳
      // 分裂），不是任意值——task 3.9 AC#2 的測試需要真的有「succeeded」/「split」的
      // 反查對象才測得到 describeRegimeEnd() 的正常路徑，不能只測 fallback 文案。
      data: [
        {
          id: 'r-han',
          selfName: '漢',
          status: 'split',
          predecessorRegimeId: null,
          originTransitionType: null,
          destroyedByRegimeId: null,
        },
        {
          id: 'r-wei',
          selfName: '魏',
          status: 'succeeded',
          predecessorRegimeId: 'r-han',
          originTransitionType: 'split',
          destroyedByRegimeId: null,
        },
        {
          id: 'r-shuhan',
          selfName: '蜀漢',
          status: 'conquered',
          predecessorRegimeId: 'r-han',
          originTransitionType: 'split',
          destroyedByRegimeId: 'r-wei',
        },
        {
          id: 'r-wu',
          selfName: '吳',
          status: 'conquered',
          predecessorRegimeId: 'r-han',
          originTransitionType: 'split',
          destroyedByRegimeId: null,
        },
        {
          id: 'r-jin',
          selfName: '晉',
          status: 'active',
          predecessorRegimeId: 'r-wei',
          originTransitionType: 'succeeded',
          destroyedByRegimeId: null,
        },
      ],
    });
  });

  afterEach(() => {
    httpMock.verify();
  });

  // toggle() 除了查存續區間（territories），2026-08-30 起也會同步查 AC#3 的兩個互動
  // 端點（events/relations，見 RegimeFocusState 類別文件說明）——這個 helper 一次把
  // toggle() 觸發的三個請求都 flush 掉，不用每個測試各自重複寫。
  // 2026-08-31 起 RegimeFocusState.toggle() 只查存續區間（events/relations 的互動
  // 查詢已經整個搬到 RegimeEventPanelComponent 自己管，見該元件類別文件），這個 helper
  // 因此只需要 flush 一筆請求，不再是「events/relations」複數形。
  function flushFocusRequests(
    regimeId: string,
    territoryRows: Array<{ startYear: number; endYear: number }>,
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
  }

  it('沒有聚焦任何政權時，不渲染面板', () => {
    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-focus-panel')).toBeNull();
  });

  it('聚焦政權後顯示面板，標題是該政權的名稱', () => {
    focusState.toggle('r-wei');
    flushFocusRequests('r-wei', [{ startYear: 220, endYear: 226 }]);
    focusState.setNeighbors(['r-shuhan', 'r-wu']);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    const panel = fixture.nativeElement.querySelector('.regime-focus-panel');
    expect(panel).not.toBeNull();
    expect(fixture.nativeElement.querySelector('h2').textContent).toBe('魏');
  });

  it('周邊政權清單依名稱排序顯示，用 Sanring Tag 呈現', () => {
    focusState.toggle('r-wei');
    flushFocusRequests('r-wei', [{ startYear: 220, endYear: 226 }]);
    focusState.setNeighbors(['r-wu', 'r-shuhan']); // 刻意用非排序順序傳入

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    const tagLists = fixture.nativeElement.querySelectorAll('.regime-focus-panel-tag-list');
    const items = [...tagLists[0].querySelectorAll('sanring-tag')].map((el: Element) => el.textContent?.trim());
    expect(items).toEqual(['吳', '蜀漢']); // localeCompare('zh-Hant') 排序結果
  });

  it('沒有周邊政權時顯示空狀態文案，不是空清單', () => {
    focusState.toggle('r-wei');
    flushFocusRequests('r-wei', [{ startYear: 220, endYear: 226 }]);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    const sections = fixture.nativeElement.querySelectorAll('sanring-collapsible');
    expect(sections[0].querySelector('.regime-focus-panel-tag-list')).toBeNull();
    expect(sections[0].querySelector('.regime-focus-panel-empty')).not.toBeNull();
  });

  it('存續期間顯示在標題下方（只有年份精度）', () => {
    focusState.toggle('r-wei');
    flushFocusRequests('r-wei', [{ startYear: 220, endYear: 226 }, { startYear: 226, endYear: 265 }]);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-focus-panel-lifespan').textContent).toBe('西元 220–265 年');
  });

  describe('任務 3.14：存續區間 loading/error 態（PRD §8「政權聚焦頁」四態齊備）', () => {
    it('回應還沒回來前顯示「載入中」，不顯示存續期間文字', () => {
      focusState.toggle('r-wei');

      const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('.regime-focus-panel-lifespan-status')?.textContent).toContain(
        '載入中',
      );
      expect(fixture.nativeElement.querySelector('.regime-focus-panel-lifespan')).toBeNull();

      // 這個測試不關心後續狀態，flush 掉避免 httpMock.verify() 噴錯。
      httpMock
        .expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-wei/territories')
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: { type: 'FeatureCollection', features: [] } });
    });

    it('查詢失敗時顯示錯誤提示+重試按鈕，點擊重試會重新查詢', () => {
      focusState.toggle('r-wei');
      httpMock
        .expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-wei/territories')
        .flush({ statusCode: 500, message: 'INTERNAL_ERROR', data: null }, { status: 500, statusText: 'Server Error' });

      const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
      fixture.detectChanges();

      const warning = fixture.nativeElement.querySelector('.regime-focus-panel-warning');
      expect(warning?.textContent).toContain('存續區間載入失敗');

      const retryButton: HTMLButtonElement = fixture.nativeElement.querySelector('.regime-focus-panel-retry');
      retryButton.click();

      flushFocusRequests('r-wei', [{ startYear: 220, endYear: 226 }]);
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('.regime-focus-panel-lifespan').textContent).toBe('西元 220–226 年');
    });
  });

  it('「同時期其他地區政權」清單依名稱排序顯示，用 Sanring Tag 呈現，不跟周邊政權混在一起', () => {
    focusState.toggle('r-wei');
    flushFocusRequests('r-wei', [{ startYear: 220, endYear: 226 }]);
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
    flushFocusRequests('r-wei', [{ startYear: 220, endYear: 226 }]);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    const sections = fixture.nativeElement.querySelectorAll('sanring-collapsible');
    expect(sections[1].querySelector('.regime-focus-panel-tag-list')).toBeNull();
    expect(sections[1].querySelector('.regime-focus-panel-empty')).not.toBeNull();
  });

  it('目前年份早於聚焦政權存續區間時，顯示「尚未建立」警告', () => {
    timeline.year.set(100);
    focusState.toggle('r-wei');
    flushFocusRequests('r-wei', [{ startYear: 220, endYear: 226 }]);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-focus-panel-warning').textContent).toContain('尚未建立');
  });

  it('目前年份晚於聚焦政權存續區間時，顯示「已不存在」警告', () => {
    timeline.year.set(300);
    focusState.toggle('r-wei');
    flushFocusRequests('r-wei', [{ startYear: 220, endYear: 226 }]);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-focus-panel-warning').textContent).toContain('已不存在');
  });

  it('目前年份落在存續區間內時，不顯示警告', () => {
    timeline.year.set(222);
    focusState.toggle('r-wei');
    flushFocusRequests('r-wei', [{ startYear: 220, endYear: 226 }]);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.regime-focus-panel-warning')).toBeNull();
  });

  it('周邊政權清單預設是展開的（不是預設收合，維持既有行為，只是加了可以收合的能力）', () => {
    focusState.toggle('r-wei');
    flushFocusRequests('r-wei', [{ startYear: 220, endYear: 226 }]);
    focusState.setNeighbors(['r-shuhan']);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    const content: HTMLElement = fixture.nativeElement.querySelector('[sanringCollapsibleContent]');
    expect(content.hidden).toBe(false);
  });

  it('點擊「同時期周邊政權」觸發鈕會收合/展開清單，不影響聚焦狀態本身', () => {
    focusState.toggle('r-wei');
    flushFocusRequests('r-wei', [{ startYear: 220, endYear: 226 }]);
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
    flushFocusRequests('r-wei', [{ startYear: 220, endYear: 226 }]);

    const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
    fixture.detectChanges();

    fixture.nativeElement.querySelector('.regime-focus-panel-close').click();

    expect(focusState.focusedRegimeId()).toBeNull();
  });

  describe('任務 3.9 AC#2：起源／終止狀態視覺呈現', () => {
    it('魏（承漢分裂而立、後由晉禪讓取代）顯示對應的起源/終止 Tag，終止 variant 是 default 不是 destructive', () => {
      focusState.toggle('r-wei');
      flushFocusRequests('r-wei', [{ startYear: 220, endYear: 226 }]);

      const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
      fixture.detectChanges();

      const tags = fixture.nativeElement.querySelectorAll('.regime-focus-panel-transition-tags sanring-tag');
      expect(tags[0].textContent.trim()).toBe('承 漢 分裂而立');
      expect(tags[1].textContent.trim()).toBe('禪讓予 晉');
      // AC#2 核心：variant 決定實際渲染出來的顏色 class（BadgeDirective 把 variant 轉成
      // `[class]` host binding，見 badge.directive.ts），不是憑文字內容猜——這裡直接比對
      // class 字串，確保「禪讓」用的是 default（中性色），不是 conquered 那個紅色 class。
      const endBadge = tags[1].querySelector('[sanringbadge]') as HTMLElement;
      expect(endBadge.className).toContain('--sanring-control)'); // default variant 的識別 class 片段
      expect(endBadge.className).not.toContain('--sanring-error-50)');
    });

    it('蜀漢（被魏所滅）終止 Tag 文字含滅亡方，variant 用 destructive（紅色，跟禪讓明確視覺區分）', () => {
      focusState.toggle('r-shuhan');
      flushFocusRequests('r-shuhan', [{ startYear: 221, endYear: 263 }]);

      const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
      fixture.detectChanges();

      const tags = fixture.nativeElement.querySelectorAll('.regime-focus-panel-transition-tags sanring-tag');
      expect(tags[0].textContent.trim()).toBe('承 漢 分裂而立');
      expect(tags[1].textContent.trim()).toBe('被 魏 所滅');
      const endBadge = tags[1].querySelector('[sanringbadge]') as HTMLElement;
      expect(endBadge.className).toContain('--sanring-error-50)'); // destructive variant 的識別 class 片段
    });

    it('漢（分裂為魏／蜀漢／吳，沒有前身政權）起源顯示「獨立起始」，終止列出全部分裂政權', () => {
      focusState.toggle('r-han');
      flushFocusRequests('r-han', [{ startYear: 189, endYear: 220 }]);

      const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
      fixture.detectChanges();

      const tags = fixture.nativeElement.querySelectorAll('.regime-focus-panel-transition-tags sanring-tag');
      expect(tags[0].textContent.trim()).toBe('獨立起始（無前身政權）');
      expect(tags[1].textContent.trim()).toBe('分裂為 魏／蜀漢／吳');
    });

    it('晉（仍存續中）只顯示起源 Tag，不顯示終止 Tag', () => {
      focusState.toggle('r-jin');
      flushFocusRequests('r-jin', [{ startYear: 265, endYear: 280 }]);

      const fixture = TestBed.createComponent(RegimeFocusPanelComponent);
      fixture.detectChanges();

      const tags = fixture.nativeElement.querySelectorAll('.regime-focus-panel-transition-tags sanring-tag');
      expect(tags).toHaveLength(1);
      expect(tags[0].textContent.trim()).toBe('承 魏 禪讓而立');
    });
  });

  // AC#3 互動記錄的顯示/點擊測試 2026-08-31 搬到 regime-event-panel.spec.ts——見
  // RegimeFocusPanelComponent 類別文件說明，這個元件不再處理互動記錄。
});
