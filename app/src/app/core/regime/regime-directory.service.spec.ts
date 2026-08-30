import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { RegimeDirectoryService } from './regime-directory.service';

describe('RegimeDirectoryService', () => {
  let service: RegimeDirectoryService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(RegimeDirectoryService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('ensureLoaded() 打一次 GET /api/v1/regimes，載入後 nameOf() 能查到名稱', () => {
    service.ensureLoaded().subscribe();

    httpMock
      .expectOne((r) => r.urlWithParams === '/api/v1/regimes')
      .flush({
        statusCode: 200,
        message: 'FETCH_SUCCESS',
        data: [
          { id: 'r-a', selfName: '魏' },
          { id: 'r-b', selfName: '吳' },
        ],
      });

    expect(service.nameOf('r-a')).toBe('魏');
    expect(service.nameOf('r-b')).toBe('吳');
  });

  it('nameOf() 查無資料時回傳 undefined，不拋例外', () => {
    service.ensureLoaded().subscribe();
    httpMock
      .expectOne((r) => r.urlWithParams === '/api/v1/regimes')
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: [] });

    expect(service.nameOf('nonexistent')).toBeUndefined();
  });

  it('重複呼叫 ensureLoaded() 只打一次 API（shareReplay 快取，不重複查詢）', () => {
    service.ensureLoaded().subscribe();
    service.ensureLoaded().subscribe();
    service.ensureLoaded().subscribe();

    httpMock
      .expectOne((r) => r.urlWithParams === '/api/v1/regimes')
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: [{ id: 'r-a', selfName: '魏' }] });

    httpMock.expectNone(() => true); // 確認真的沒有第二次請求
  });
});
