import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { RegimeDirectoryService, type RegimeSummary } from './regime-directory.service';

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

  function loadRegimes(regimes: RegimeSummary[]): void {
    service.ensureLoaded().subscribe();
    httpMock
      .expectOne((r) => r.urlWithParams === '/api/v1/regimes')
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: regimes });
  }

  it('ensureLoaded() 打一次 GET /api/v1/regimes，載入後 nameOf() 能查到名稱', () => {
    loadRegimes([
      { id: 'r-a', selfName: '魏', status: 'succeeded', predecessorRegimeId: null, originTransitionType: null, destroyedByRegimeId: null },
      { id: 'r-b', selfName: '吳', status: 'conquered', predecessorRegimeId: null, originTransitionType: null, destroyedByRegimeId: null },
    ]);

    expect(service.nameOf('r-a')).toBe('魏');
    expect(service.nameOf('r-b')).toBe('吳');
  });

  it('nameOf() 查無資料時回傳 undefined，不拋例外', () => {
    loadRegimes([]);

    expect(service.nameOf('nonexistent')).toBeUndefined();
  });

  it('重複呼叫 ensureLoaded() 只打一次 API（shareReplay 快取，不重複查詢）', () => {
    service.ensureLoaded().subscribe();
    service.ensureLoaded().subscribe();
    service.ensureLoaded().subscribe();

    httpMock
      .expectOne((r) => r.urlWithParams === '/api/v1/regimes')
      .flush({
        statusCode: 200,
        message: 'FETCH_SUCCESS',
        data: [{ id: 'r-a', selfName: '魏', status: 'succeeded', predecessorRegimeId: null, originTransitionType: null, destroyedByRegimeId: null }],
      });

    httpMock.expectNone(() => true); // 確認真的沒有第二次請求
  });

  it('regimeOf() 回傳完整政權記錄，不只是名稱', () => {
    loadRegimes([
      { id: 'r-wei', selfName: '魏', status: 'succeeded', predecessorRegimeId: 'r-han', originTransitionType: 'split', destroyedByRegimeId: null },
    ]);

    expect(service.regimeOf('r-wei')).toEqual({
      id: 'r-wei',
      selfName: '魏',
      status: 'succeeded',
      predecessorRegimeId: 'r-han',
      originTransitionType: 'split',
      destroyedByRegimeId: null,
    });
    expect(service.regimeOf('nonexistent')).toBeUndefined();
  });

  describe('反向查詢（任務 3.9）', () => {
    it('successorOf() 找出「接續這個政權」的政權（origin_transition_type=succeeded）', () => {
      loadRegimes([
        { id: 'r-wei', selfName: '魏', status: 'succeeded', predecessorRegimeId: null, originTransitionType: null, destroyedByRegimeId: null },
        { id: 'r-jin', selfName: '晉', status: 'active', predecessorRegimeId: 'r-wei', originTransitionType: 'succeeded', destroyedByRegimeId: null },
        // 同時放一筆 predecessor 相同、但是 split 而非 succeeded 的，確認不會混進來
        { id: 'r-other', selfName: '其他', status: 'active', predecessorRegimeId: 'r-wei', originTransitionType: 'split', destroyedByRegimeId: null },
      ]);

      expect(service.successorOf('r-wei').map((r) => r.id)).toEqual(['r-jin']);
    });

    it('successorOf() 沒有接續者時回傳空陣列', () => {
      loadRegimes([
        { id: 'r-wei', selfName: '魏', status: 'succeeded', predecessorRegimeId: null, originTransitionType: null, destroyedByRegimeId: null },
      ]);

      expect(service.successorOf('r-wei')).toEqual([]);
    });

    it('splitChildrenOf() 找出「這個政權分裂出的」所有政權（origin_transition_type=split），可以是多筆', () => {
      loadRegimes([
        { id: 'r-han', selfName: '漢', status: 'split', predecessorRegimeId: null, originTransitionType: null, destroyedByRegimeId: null },
        { id: 'r-wei', selfName: '魏', status: 'succeeded', predecessorRegimeId: 'r-han', originTransitionType: 'split', destroyedByRegimeId: null },
        { id: 'r-shuhan', selfName: '蜀漢', status: 'conquered', predecessorRegimeId: 'r-han', originTransitionType: 'split', destroyedByRegimeId: 'r-wei' },
        { id: 'r-wu', selfName: '吳', status: 'conquered', predecessorRegimeId: 'r-han', originTransitionType: 'split', destroyedByRegimeId: null },
      ]);

      expect(service.splitChildrenOf('r-han').map((r) => r.id).sort()).toEqual(['r-shuhan', 'r-wei', 'r-wu']);
    });
  });
});
