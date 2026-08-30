import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { NamingViewpointSelectorComponent } from './naming-viewpoint-selector';
import { NamingViewpointState } from '../core/regime/naming-viewpoint-state';

describe('NamingViewpointSelectorComponent', () => {
  let httpMock: HttpTestingController;
  let viewpoint: NamingViewpointState;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    httpMock = TestBed.inject(HttpTestingController);
    viewpoint = TestBed.inject(NamingViewpointState);
  });

  afterEach(() => {
    httpMock.verify();
  });

  function flushRegimes(): void {
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: [
        { id: 'r-wu', selfName: '吳', status: 'conquered', predecessorRegimeId: null, originTransitionType: null, destroyedByRegimeId: null },
        { id: 'r-wei', selfName: '魏', status: 'succeeded', predecessorRegimeId: null, originTransitionType: null, destroyedByRegimeId: null },
      ],
    });
  }

  it('選單第一個選項固定是「全球客觀視角」，其餘依政權名稱排序', () => {
    const fixture = TestBed.createComponent(NamingViewpointSelectorComponent);
    fixture.detectChanges();
    flushRegimes();
    fixture.detectChanges();

    const select: HTMLSelectElement = fixture.nativeElement.querySelector('select');
    const optionLabels = [...select.options].map((o) => o.textContent);
    expect(optionLabels).toEqual(['全球客觀視角', '以吳視角', '以魏視角']); // localeCompare('zh-Hant') 排序
  });

  it('預設選中「全球客觀視角」（NamingViewpointState 預設 null）', () => {
    const fixture = TestBed.createComponent(NamingViewpointSelectorComponent);
    fixture.detectChanges();
    flushRegimes();
    fixture.detectChanges();

    const select: HTMLSelectElement = fixture.nativeElement.querySelector('select');
    expect(select.value).toBe('');
  });

  it('選擇某個政權會寫入 NamingViewpointState.observerRegimeId', () => {
    const fixture = TestBed.createComponent(NamingViewpointSelectorComponent);
    fixture.detectChanges();
    flushRegimes();
    fixture.detectChanges();

    const select: HTMLSelectElement = fixture.nativeElement.querySelector('select');
    select.value = 'r-wei';
    select.dispatchEvent(new Event('change'));

    expect(viewpoint.observerRegimeId()).toBe('r-wei');
  });

  it('選回「全球客觀視角」會把 observerRegimeId 寫回 null', () => {
    viewpoint.setObserver('r-wei');
    const fixture = TestBed.createComponent(NamingViewpointSelectorComponent);
    fixture.detectChanges();
    flushRegimes();
    fixture.detectChanges();

    const select: HTMLSelectElement = fixture.nativeElement.querySelector('select');
    select.value = '';
    select.dispatchEvent(new Event('change'));

    expect(viewpoint.observerRegimeId()).toBeNull();
  });
});
