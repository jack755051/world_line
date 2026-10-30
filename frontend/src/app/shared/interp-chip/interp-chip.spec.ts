import type { TheaterStateDto } from '../../core/api/api-types';
import { chipMode } from './interp-chip';

// 測試用假資料（只存在於測試檔）
const attested: TheaterStateDto = { theaterCode: 'west-europe', state: 'attested', attestingSnapshot: { id: 'a', asOf: '1940-07-15' }, prevSnapshot: null, nextSnapshot: null };
const interp: TheaterStateDto = { theaterCode: 'west-europe', state: 'interpolated', attestingSnapshot: null, prevSnapshot: { id: 'a', asOf: '1940-07-15' }, nextSnapshot: { id: 'b', asOf: '1940-08-15' } };

describe('chipMode（PRD §8.5）', () => {
  it('全部史料 → 史料快照', () => expect(chipMode('ok', [attested], 1)).toBe('attested'));
  it('任一戰區推估 → 推估過渡', () => expect(chipMode('ok', [interp], 1)).toBe('interpolated'));
  it('outside 也不能當成史料', () => expect(chipMode('ok', [{ ...attested, state: 'outside' }], 1)).toBe('interpolated'));
  it('取得失敗 → 無法判斷（不預設成史料）', () => expect(chipMode('error', [attested], 1)).toBe('unknown'));
  it('沒有任何控制資料 → 不顯示', () => {
    expect(chipMode('ok', [], 0)).toBe('hidden');
    expect(chipMode('ok', [{ ...attested, state: 'outside' }], 0)).toBe('hidden');
  });
  it('首次載入 → spinner', () => expect(chipMode('loading', null, 0)).toBe('loading'));
});
