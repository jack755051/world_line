import { describe, expect, it } from 'vitest';
import { addDaysIso, intervalKey } from './change-points';

describe('change-points：變動區間', () => {
  const pts = ['1914-07-29', '1914-08-20', '1918-11-11'];
  it('區間鍵＝不大於日期的最大變動點（半開區間：變動點當天屬於新區間）', () => {
    expect(intervalKey(pts, '1914-07-28')).toBe('-');
    expect(intervalKey(pts, '1914-07-29')).toBe('1914-07-29');
    expect(intervalKey(pts, '1914-08-19')).toBe('1914-07-29');
    expect(intervalKey(pts, '1914-08-20')).toBe('1914-08-20');
    expect(intervalKey(pts, '1945-01-01')).toBe('1918-11-11');
  });
  it('沒有變動點資料時退回用日期本身', () => {
    expect(intervalKey(null, '1942-12-01')).toBe('1942-12-01');
  });
  it('addDaysIso 跨月、跨年、閏年', () => {
    expect(addDaysIso('1942-12-28', 7)).toBe('1943-01-04');
    expect(addDaysIso('1916-02-28', 1)).toBe('1916-02-29');
    expect(addDaysIso('1908-10-06', 0)).toBe('1908-10-06');
  });
});
