import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { RegimeAliasDirectoryService } from './regime-alias-directory.service';
import { RegimeDirectoryService } from './regime-directory.service';

describe('RegimeAliasDirectoryService', () => {
  let service: RegimeAliasDirectoryService;
  let directory: RegimeDirectoryService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(RegimeAliasDirectoryService);
    directory = TestBed.inject(RegimeDirectoryService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  function loadRegimes(ids: string[]): void {
    directory.ensureLoaded().subscribe();
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: ids.map((id) => ({
        id,
        selfName: id,
        status: 'active',
        predecessorRegimeId: null,
        originTransitionType: null,
        destroyedByRegimeId: null,
      })),
    });
  }

  it('ensureLoaded() 先確保政權清單載入，再對每個政權各查一次代稱（forkJoin），aliasFor() 能查到', () => {
    loadRegimes(['r-wei', 'r-wu']);

    service.ensureLoaded().subscribe();

    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-wei/aliases').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: [{ id: 'alias-1', regimeId: 'r-wei', observerRegimeId: 'r-shuhan', aliasName: '賊', aliasType: 'political' }],
    });
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-wu/aliases').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: [{ id: 'alias-2', regimeId: 'r-wu', observerRegimeId: null, aliasName: '孫吳', aliasType: 'scholarly' }],
    });

    expect(service.aliasFor('r-wei', 'r-shuhan')).toEqual({
      id: 'alias-1',
      regimeId: 'r-wei',
      observerRegimeId: 'r-shuhan',
      aliasName: '賊',
      aliasType: 'political',
    });
  });

  it('aliasFor() 查無代稱時回傳 undefined（呼叫端 fallback 回自稱名稱）', () => {
    loadRegimes(['r-wei']);
    service.ensureLoaded().subscribe();
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-wei/aliases').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: [],
    });

    expect(service.aliasFor('r-wei', 'r-shuhan')).toBeUndefined();
    expect(service.aliasFor('nonexistent', 'r-shuhan')).toBeUndefined();
  });

  it('觀察視角是 null（通用他稱）的代稱不會被特定 observerRegimeId 的查詢誤配到', () => {
    loadRegimes(['r-wu']);
    service.ensureLoaded().subscribe();
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-wu/aliases').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: [{ id: 'alias-2', regimeId: 'r-wu', observerRegimeId: null, aliasName: '孫吳', aliasType: 'scholarly' }],
    });

    expect(service.aliasFor('r-wu', 'r-wei')).toBeUndefined();
  });

  it('沒有任何政權時（理論上不該發生）不打任何代稱請求，直接完成', () => {
    loadRegimes([]);
    service.ensureLoaded().subscribe();
    httpMock.expectNone(() => true);
  });

  it('重複呼叫 ensureLoaded() 只打一次代稱請求集合（shareReplay 快取）', () => {
    loadRegimes(['r-wei']);
    service.ensureLoaded().subscribe();
    service.ensureLoaded().subscribe();

    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes/r-wei/aliases').flush({
      statusCode: 200,
      message: 'FETCH_SUCCESS',
      data: [],
    });
    httpMock.expectNone(() => true);
  });
});
