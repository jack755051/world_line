import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { DefaultLineageService } from './default-lineage.service';

describe('DefaultLineageService', () => {
  let service: DefaultLineageService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(DefaultLineageService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('串接兩個請求：先查 lineage-presets 找出 isDefault 的那筆，再查它底下的政權序列', () => {
    service.ensureLoaded().subscribe();

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

    expect(service.presetName()).toBe('傳統教科書史觀');
    expect(service.sequence().map((r) => r.selfName)).toEqual(['漢', '魏', '晉']);
  });

  it('查無 isDefault 的 preset 時，sequence 維持空陣列，不拋例外，不打第二個請求', () => {
    service.ensureLoaded().subscribe();

    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/lineage-presets').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: [{ id: 'preset-alt', presetName: '蜀漢正統論史觀', description: null, isDefault: false }],
    });

    expect(service.presetName()).toBeNull();
    expect(service.sequence()).toEqual([]);
    httpMock.expectNone(() => true);
  });

  it('重複呼叫 ensureLoaded() 只打一次 API（shareReplay 快取）', () => {
    service.ensureLoaded().subscribe();
    service.ensureLoaded().subscribe();

    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/lineage-presets').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: [{ id: 'preset-default', presetName: '傳統教科書史觀', description: null, isDefault: true }],
    });
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/lineage-presets/preset-default/regimes').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: [],
    });

    httpMock.expectNone(() => true);
  });
});
