import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { NamingViewpointSelectorComponent } from './naming-viewpoint-selector';
import { NamingViewpointState } from '../core/regime/naming-viewpoint-state';
import { TimelineState } from '../core/time/timeline-state';

// 跟 time-scrubber.spec.ts/map.spec.ts 同一個理由：這個元件訂閱 TimelineState.year
// 時用了 debounceTime(150)——不管是第一次載入還是換年份，都要等過這段 debounce 才會
// 真的發出 HTTP 請求，測試用真的時間等待，不用 fake timers（zoneless TestBed 對 fake
// timers 相容性不夠肯定）。
function waitForDebounce(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 200));
}

const DEFAULT_YEAR_REGIMES = [
  { id: 'r-wu', selfName: '吳', status: 'conquered', predecessorRegimeId: null, originTransitionType: null, destroyedByRegimeId: null },
  { id: 'r-wei', selfName: '魏', status: 'succeeded', predecessorRegimeId: null, originTransitionType: null, destroyedByRegimeId: null },
];

describe('NamingViewpointSelectorComponent', () => {
  let httpMock: HttpTestingController;
  let viewpoint: NamingViewpointState;

  beforeEach(() => {
    // TimelineState 是 providedIn: 'root' 的單例——前一個 it() 改過的 year 值會留到
    // 下一個 it()，需要跟 time-scrubber.spec.ts 一樣每個 it() 前重置。
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    httpMock = TestBed.inject(HttpTestingController);
    viewpoint = TestBed.inject(NamingViewpointState);
  });

  afterEach(() => {
    httpMock.verify();
  });

  /** 建立元件、等過建構子觸發的 debounce、沖掉 DEFAULT_YEAR 那筆當代政權查詢。 */
  async function createSelector(
    data: ReadonlyArray<Record<string, unknown>> = DEFAULT_YEAR_REGIMES,
  ): Promise<ComponentFixture<NamingViewpointSelectorComponent>> {
    const fixture = TestBed.createComponent(NamingViewpointSelectorComponent);
    fixture.detectChanges();

    await waitForDebounce();
    httpMock
      .expectOne((r) => r.urlWithParams === `/api/v1/regimes?year=${TimelineState.DEFAULT_YEAR}`)
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data });
    fixture.detectChanges();

    return fixture;
  }

  it('選單依目前拉桿年份查詢當代政權（依 task 2.4 ?year= 語意），不是列出全部政權', async () => {
    const fixture = await createSelector();

    const select: HTMLSelectElement = fixture.nativeElement.querySelector('select');
    const optionLabels = [...select.options].map((o) => o.textContent);
    // 第一個選項固定是「全球客觀視角」，其餘依政權名稱排序（localeCompare('zh-Hant')）。
    expect(optionLabels).toEqual(['全球客觀視角', '以吳視角', '以魏視角']);
  });

  it('預設選中「全球客觀視角」（NamingViewpointState 預設 null）', async () => {
    const fixture = await createSelector();

    const select: HTMLSelectElement = fixture.nativeElement.querySelector('select');
    expect(select.value).toBe('');
  });

  it('選擇某個政權會寫入 NamingViewpointState.observerRegimeId', async () => {
    const fixture = await createSelector();

    const select: HTMLSelectElement = fixture.nativeElement.querySelector('select');
    select.value = 'r-wei';
    select.dispatchEvent(new Event('change'));

    expect(viewpoint.observerRegimeId()).toBe('r-wei');
  });

  it('選回「全球客觀視角」會把 observerRegimeId 寫回 null', async () => {
    const fixture = await createSelector();
    viewpoint.setObserver('r-wei');
    fixture.detectChanges();

    const select: HTMLSelectElement = fixture.nativeElement.querySelector('select');
    select.value = '';
    select.dispatchEvent(new Event('change'));

    expect(viewpoint.observerRegimeId()).toBeNull();
  });

  describe('拉動拉桿到觀察者不再是當代政權的年份', () => {
    it('自動把 observerRegimeId 清回 null，選單也回到「全球客觀視角」', async () => {
      const fixture = await createSelector(); // 225 年：吳/魏都在
      viewpoint.setObserver('r-wei');
      fixture.detectChanges();

      const timeline = TestBed.inject(TimelineState);
      timeline.year.set(900); // 唐朝/阿拉伯帝國種子資料的年代，魏（三國）早已不存在
      await waitForDebounce();
      httpMock
        .expectOne((r) => r.urlWithParams === '/api/v1/regimes?year=900')
        .flush({
          statusCode: 200,
          message: 'FETCH_SUCCESS',
          data: [
            {
              id: 'r-abbasid',
              selfName: '阿拔斯王朝',
              status: 'active',
              predecessorRegimeId: null,
              originTransitionType: null,
              destroyedByRegimeId: null,
            },
          ],
        });
      fixture.detectChanges();

      expect(viewpoint.observerRegimeId()).toBeNull();
      const select: HTMLSelectElement = fixture.nativeElement.querySelector('select');
      expect(select.value).toBe('');
    });

    it('觀察者在新年份仍是當代政權時，維持選取不清空', async () => {
      const fixture = await createSelector(); // 225 年：吳/魏都在
      viewpoint.setObserver('r-wei');
      fixture.detectChanges();

      const timeline = TestBed.inject(TimelineState);
      timeline.year.set(224); // 仍在魏的存續區間內
      await waitForDebounce();
      httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes?year=224').flush({
        statusCode: 200,
        message: 'FETCH_SUCCESS',
        data: DEFAULT_YEAR_REGIMES,
      });
      fixture.detectChanges();

      expect(viewpoint.observerRegimeId()).toBe('r-wei');
    });
  });
});
