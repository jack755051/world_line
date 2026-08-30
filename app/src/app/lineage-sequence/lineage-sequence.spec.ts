import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { LineageSequenceComponent } from './lineage-sequence';

describe('LineageSequenceComponent', () => {
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  function flushDefaultLineage(): void {
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/lineage-presets').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: [
        { id: 'preset-alt', presetName: '蜀漢正統論史觀', description: null, isDefault: false },
        { id: 'preset-default', presetName: '傳統教科書史觀', description: null, isDefault: true },
      ],
    });
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/lineage-presets/preset-default/regimes').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: [
        {
          sortOrder: 1,
          id: 'r-han',
          selfName: '漢',
          status: 'split',
          predecessorRegimeId: null,
          originTransitionType: null,
          destroyedByRegimeId: null,
        },
        {
          sortOrder: 2,
          id: 'r-wei',
          selfName: '魏',
          status: 'succeeded',
          predecessorRegimeId: 'r-han',
          originTransitionType: 'split',
          destroyedByRegimeId: null,
        },
        {
          sortOrder: 3,
          id: 'r-jin',
          selfName: '晉',
          status: 'active',
          predecessorRegimeId: 'r-wei',
          originTransitionType: 'succeeded',
          destroyedByRegimeId: null,
        },
      ],
    });
  }

  it('顯示預設 preset 名稱 + 依序排列的政權 Tag，箭頭數量比政權數量少一', () => {
    const fixture = TestBed.createComponent(LineageSequenceComponent);
    fixture.detectChanges();
    flushDefaultLineage();
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.lineage-sequence-label')?.textContent).toBe('傳統教科書史觀主線：');
    const names = [...el.querySelectorAll('sanring-tag')].map((t) => t.textContent?.trim());
    expect(names).toEqual(['漢', '魏', '晉']);
    expect(el.querySelectorAll('.lineage-sequence-arrow')).toHaveLength(2);
  });

  it('查無 isDefault preset 時，不渲染任何內容（不報錯、不顯示空殼）', () => {
    const fixture = TestBed.createComponent(LineageSequenceComponent);
    fixture.detectChanges();

    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/lineage-presets').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: [],
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.lineage-sequence')).toBeNull();
  });
});
