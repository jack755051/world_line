import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DelayedFlag, isAbort } from './delayed-flag';

describe('DelayedFlag（載入指示延遲 300ms 才顯示）', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('短於延遲的忙碌不顯示；超過延遲才顯示，結束立即隱藏', () => {
    const seen: boolean[] = [];
    const f = new DelayedFlag((v) => seen.push(v), 300);
    f.set(true);
    vi.advanceTimersByTime(200);
    f.set(false);
    vi.advanceTimersByTime(500);
    expect(seen).toEqual([]);
    f.set(true);
    vi.advanceTimersByTime(299);
    expect(seen).toEqual([]);
    f.set(true); // 重複 busy 不重設計時
    vi.advanceTimersByTime(1);
    expect(seen).toEqual([true]);
    f.set(false);
    expect(seen).toEqual([true, false]);
  });

  it('dispose 取消尚未觸發的計時', () => {
    const seen: boolean[] = [];
    const f = new DelayedFlag((v) => seen.push(v));
    f.set(true);
    f.dispose();
    vi.advanceTimersByTime(1000);
    expect(seen).toEqual([]);
  });

  it('isAbort 只認 AbortError', () => {
    expect(isAbort(new DOMException('x', 'AbortError'))).toBe(true);
    expect(isAbort(new Error('x'))).toBe(false);
    expect(isAbort(null)).toBe(false);
  });
});
