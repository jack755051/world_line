import { API_MESSAGE_CODE_TEXT, messageCodeToText } from './message-codes';

// 跟 api/Contracts/ApiMessageCodes.cs 目前的完整代碼清單一致（2026-08-31）——這裡刻意
// 手動列一份清單斷言「完全相等」，不是只挑幾個代碼測，理由：這份字典本身就是「跟後端
// 那份權威清單手動同步」的產物，沒有機制自動偵測漂移，用一條測試鎖住目前已知的完整
// 集合，之後任一邊漏改都至少會在這裡出現落差（雖然還是要人工比對兩份清單本身，但至少
// 這裡不會安靜地漏掉某個代碼忘記加顯示文字）。
const EXPECTED_CODES = [
  'FETCH_SUCCESS',
  'CREATE_SUCCESS',
  'VALIDATION_ERROR',
  'NOT_FOUND',
  'INTERNAL_ERROR',
  'UNAUTHORIZED',
  'YEAR_REQUIRED',
  'REGIME_NOT_FOUND',
  'EVENT_NOT_FOUND',
  'EVENT_ID_ALREADY_EXISTS',
  'INVALID_EDTF',
  'EVENT_END_BEFORE_START',
  'PARENT_EVENT_NOT_FOUND',
  'RELATION_SAME_REGIME',
  'RELATION_OTHER_REGIME_NOT_FOUND',
  'RELATION_END_BEFORE_START',
  'LINEAGE_PRESET_NOT_FOUND',
  'OBSERVER_REGIME_NOT_FOUND',
  'INVALID_ALIAS_TYPE',
  'PERSPECTIVE_PARTY_REQUIRED',
  'OBSERVER_CATEGORY_NOT_FOUND',
].sort();

describe('message-codes', () => {
  it('涵蓋 api/Contracts/ApiMessageCodes.cs 目前的完整代碼清單，且每個都有非空白顯示文字', () => {
    expect(Object.keys(API_MESSAGE_CODE_TEXT).sort()).toEqual(EXPECTED_CODES);
    for (const code of EXPECTED_CODES) {
      expect(API_MESSAGE_CODE_TEXT[code].trim().length).toBeGreaterThan(0);
    }
  });

  it('messageCodeToText() 查得到對應代碼時回傳中文顯示文字', () => {
    expect(messageCodeToText('EVENT_NOT_FOUND')).toBe('找不到指定的事件');
  });

  it('messageCodeToText() 查無對應代碼時 fallback 回傳原始代碼字串，不是空字串', () => {
    expect(messageCodeToText('SOME_FUTURE_CODE_NOT_YET_IN_DICTIONARY')).toBe(
      'SOME_FUTURE_CODE_NOT_YET_IN_DICTIONARY',
    );
  });
});
