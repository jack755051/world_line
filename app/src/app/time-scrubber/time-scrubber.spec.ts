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

  /** 建立元件並立刻沖掉建構子觸發的 `RegimeDirectoryService.ensureLoaded()` 請求
      （任務 3.11 起這個元件也會注入政權目錄，用來把年號標籤跟政權名稱配對）——
      跟既有測試無關，但不沖掉的話 `httpMock.verify()` 會在 afterEach 噴「還有未
      處理的請求」。**刻意不在這裡呼叫 `fixture.detectChanges()`**：既有測試（例如
      色帶測試）需要先 flush 其他請求才 `detectChanges()`，由呼叫端自行決定順序。
      年號查詢本身（`/api/v1/reign-eras`）有 150ms debounce，不會在這裡同步發出，
      個別測試需要驗證年號標籤時再自行 flush。 */
  function createScrubber(regimes: ReadonlyArray<Record<string, unknown>> = []) {
    const fixture = TestBed.createComponent(TimeScrubberComponent);
    httpMock
      .expectOne((r) => r.urlWithParams === '/api/v1/regimes')
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: regimes });
    return fixture;
  }

  // time-scrubber.ts 訂閱 TimelineState.year 查年號時也用了跟 map.ts 同一節奏的
  // debounceTime(150)——理由同 map.spec.ts 的 waitForDebounce()：zoneless TestBed
  // 對 fake timers 相容性不夠肯定，用真時間換測試行為可信度。
  function waitForDebounce(): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, 200));
  }

  it('顯示 TimelineState 目前的年份', () => {
    const fixture = createScrubber();
    fixture.detectChanges();

    const yearText = fixture.nativeElement.querySelector('.time-scrubber-year').textContent;
    expect(yearText).toContain(String(TimelineState.DEFAULT_YEAR));
  });

  it('拖動 range input 會更新 TimelineState.year', () => {
    const fixture = createScrubber();
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
    const fixture = createScrubber();
    fixture.detectChanges();

    const input: HTMLInputElement = fixture.nativeElement.querySelector('.time-scrubber-input');
    expect(input.min).toBe(String(TimelineState.MIN_YEAR));
    expect(input.max).toBe(String(TimelineState.MAX_YEAR));
  });

  describe('政權存續區間色帶（任務 3.7 AC#2）', () => {
    it('沒有聚焦任何政權時，不顯示色帶', () => {
      const fixture = createScrubber();
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

      const fixture = createScrubber();
      fixture.detectChanges();

      // toggle() 2026-08-30 起也會同步查 AC#3 的兩個互動端點（events/relations），
      // 不 flush 掉會讓 httpMock.verify() 在 afterEach 噴「還有未處理的請求」——這個
      // 測試本身不關心互動清單，用空陣列打發掉就好。
      httpMock
        .expectOne((r) => r.urlWithParams === `/api/v1/regimes/r-a/events?year=${TimelineState.DEFAULT_YEAR}`)
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: [] });
      httpMock
        .expectOne((r) => r.urlWithParams === `/api/v1/regimes/r-a/relations?year=${TimelineState.DEFAULT_YEAR}`)
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: [] });

      const band: HTMLElement = fixture.nativeElement.querySelector('.time-scrubber-lifetime-band');
      expect(band).not.toBeNull();
      // 百分比算法本身依賴 TimelineState.MIN_YEAR/MAX_YEAR 動態算出的期望值，不寫死
      // 具體數字——2026-08-31 這兩個常數從 1-300 延伸到 1-950（見 timeline-state.ts），
      // 這裡照樣算得出正確結果，不用跟著改。
      const totalSpan = TimelineState.MAX_YEAR - TimelineState.MIN_YEAR;
      const expectedLeft = ((100 - TimelineState.MIN_YEAR) / totalSpan) * 100;
      const expectedWidth = (30 / totalSpan) * 100;
      expect(band.style.left).toBe(`${expectedLeft}%`);
      expect(band.style.width).toBe(`${expectedWidth}%`);
    });
  });

  describe('年號標籤（任務 3.11）', () => {
    it('顯示目前年份對應的年號，含政權名稱與年數', async () => {
      const fixture = createScrubber([
        {
          id: 'r-wei',
          selfName: '魏',
          status: 'active',
          predecessorRegimeId: null,
          originTransitionType: null,
          destroyedByRegimeId: null,
        },
      ]);

      await waitForDebounce();
      httpMock
        .expectOne((r) => r.urlWithParams === `/api/v1/reign-eras?year=${TimelineState.DEFAULT_YEAR}`)
        .flush({
          statusCode: 200,
          message: 'FETCH_SUCCESS',
          // 黃初 220-226（同真實種子資料），DEFAULT_YEAR=225 落在區間內，年數=6。
          data: [{ id: 'era-1', regimeId: 'r-wei', eraName: '黃初', startYear: 220, endYear: 226 }],
        });
      fixture.detectChanges();

      const erasText = fixture.nativeElement.querySelector('.time-scrubber-eras').textContent;
      expect(erasText).toBe('魏 黃初6年');
    });

    it('年號起始那一年顯示「元年」，不是「1年」', async () => {
      const fixture = createScrubber([
        {
          id: 'r-wei',
          selfName: '魏',
          status: 'active',
          predecessorRegimeId: null,
          originTransitionType: null,
          destroyedByRegimeId: null,
        },
      ]);

      await waitForDebounce();
      httpMock
        .expectOne((r) => r.urlWithParams === `/api/v1/reign-eras?year=${TimelineState.DEFAULT_YEAR}`)
        .flush({
          statusCode: 200,
          message: 'FETCH_SUCCESS',
          data: [{ id: 'era-1', regimeId: 'r-wei', eraName: '黃初', startYear: TimelineState.DEFAULT_YEAR, endYear: null }],
        });
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('.time-scrubber-eras').textContent).toBe('魏 黃初元年');
    });

    it('同一年多個政權各自使用中的年號都顯示，用頓號分隔（例如三國時期）', async () => {
      const fixture = createScrubber([
        {
          id: 'r-wei',
          selfName: '魏',
          status: 'active',
          predecessorRegimeId: null,
          originTransitionType: null,
          destroyedByRegimeId: null,
        },
        {
          id: 'r-shu',
          selfName: '蜀漢',
          status: 'active',
          predecessorRegimeId: null,
          originTransitionType: null,
          destroyedByRegimeId: null,
        },
      ]);

      await waitForDebounce();
      httpMock
        .expectOne((r) => r.urlWithParams === `/api/v1/reign-eras?year=${TimelineState.DEFAULT_YEAR}`)
        .flush({
          statusCode: 200,
          message: 'FETCH_SUCCESS',
          data: [
            { id: 'era-1', regimeId: 'r-wei', eraName: '黃初', startYear: 220, endYear: 226 },
            { id: 'era-2', regimeId: 'r-shu', eraName: '建興', startYear: 223, endYear: 237 },
          ],
        });
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('.time-scrubber-eras').textContent).toBe('魏 黃初6年、蜀漢 建興3年');
    });

    it('查無年號資料時不顯示年號區塊', async () => {
      const fixture = createScrubber();

      await waitForDebounce();
      httpMock
        .expectOne((r) => r.urlWithParams === `/api/v1/reign-eras?year=${TimelineState.DEFAULT_YEAR}`)
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: [] });
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('.time-scrubber-eras')).toBeNull();
    });
  });
});
