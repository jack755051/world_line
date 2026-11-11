import { TestBed } from '@angular/core/testing';
import { MOTION_TIME_SCALE, MotionService, prefersReducedMotion } from './motion';

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

  it('沒有 matchMedia 時 canAnimate=false，animate 立即完成', async () => {
    Object.defineProperty(window, 'matchMedia', { configurable: true, writable: true, value: undefined });
    const motion = TestBed.inject(MotionService);
    expect(motion.canAnimate()).toBe(false);
    const el = document.createElement('div');
    await motion.animate(el, { opacity: [0, 1] });
    expect(el.style.opacity).toBe('');
  });

  it('時間倍率 0（測試用）：一律走終態', () => {
    mockMatchMedia(false);
    TestBed.configureTestingModule({ providers: [{ provide: MOTION_TIME_SCALE, useValue: 0 }] });
    expect(TestBed.inject(MotionService).canAnimate()).toBe(false);
  });

  it('GSAP 補間只動 transform／opacity，結束時 resolve；同元素再呼叫會接手、舊 promise 立即 resolve', async () => {
    mockMatchMedia(false);
    TestBed.configureTestingModule({ providers: [{ provide: MOTION_TIME_SCALE, useValue: 1000 }] });
    const motion = TestBed.inject(MotionService);
    expect(motion.canAnimate()).toBe(true);
    const el = document.createElement('div');
    document.body.appendChild(el);
    const first = motion.animate(el, { opacity: [0, 1] }, { duration: 10 });
    const second = motion.animate(el, { opacity: [0, 1], y: [8, 0] }, { duration: 0.2 });
    await first;
    await second;
    expect(el.style.opacity).toBe('1');
    el.remove();
  });

  it('P5 頁面轉場只預留介面（no-op）', async () => {
    await expect(TestBed.inject(MotionService).pageTransition(null, null)).resolves.toBeUndefined();
  });

  it('系統設定改變時即時更新', () => {
    const mq = mockMatchMedia(false);
    const motion = TestBed.inject(MotionService);
    expect(motion.reduced()).toBe(false);
    mq.set(true);
    expect(motion.reduced()).toBe(true);
  });
});
