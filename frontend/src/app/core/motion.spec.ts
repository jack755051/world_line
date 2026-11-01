import { TestBed } from '@angular/core/testing';
import { MotionService, prefersReducedMotion } from './motion';

function mockMatchMedia(matches: boolean) {
  const listeners: ((e: { matches: boolean }) => void)[] = [];
  const mq = {
    matches,
    media: '(prefers-reduced-motion: reduce)',
    addEventListener: (_: string, fn: (e: { matches: boolean }) => void) => listeners.push(fn),
    removeEventListener: () => undefined,
  };
  Object.defineProperty(window, 'matchMedia', { configurable: true, writable: true, value: () => mq });
  return {
    set(v: boolean) {
      mq.matches = v;
      listeners.forEach((fn) => fn({ matches: v }));
    },
  };
}

describe('MotionService（prefers-reduced-motion）', () => {
  const original = window.matchMedia;
  afterEach(() => Object.defineProperty(window, 'matchMedia', { configurable: true, writable: true, value: original }));

  it('沒有 matchMedia（jsdom／SSR）時視為減少動態', () => {
    Object.defineProperty(window, 'matchMedia', { configurable: true, writable: true, value: undefined });
    expect(prefersReducedMotion()).toBe(true);
  });

  it('使用者要求減少動態：animate 立即完成、不改元素樣式', async () => {
    mockMatchMedia(true);
    const motion = TestBed.inject(MotionService);
    expect(motion.reduced()).toBe(true);
    const el = document.createElement('div');
    await motion.animate(el, { opacity: [0, 1] });
    expect(el.style.opacity).toBe('');
  });

  it('系統設定改變時即時更新', () => {
    const mq = mockMatchMedia(false);
    const motion = TestBed.inject(MotionService);
    expect(motion.reduced()).toBe(false);
    mq.set(true);
    expect(motion.reduced()).toBe(true);
  });
});
