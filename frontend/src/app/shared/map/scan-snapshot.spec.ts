import { captureMapCanvas, cloneLabelLayer } from './scan-snapshot';

// 測試用最小 map 介面（只用到 once, getCanvas, triggerRepaint）
interface FakeMap {
  once(event: string, cb: () => void): void;
  getCanvas(): HTMLCanvasElement;
  triggerRepaint(): void;
}

describe('captureMapCanvas', () => {
  it('render 事件觸發時，把 getCanvas() 的內容複製到新 canvas', async () => {
    let renderCb: (() => void) | null = null;
    const src = document.createElement('canvas');
    src.width = 120;
    src.height = 90;

    const fakeMap: FakeMap = {
      once(event, cb) { if (event === 'render') renderCb = cb; },
      getCanvas() { return src; },
      triggerRepaint() { renderCb?.(); },
    };

    // jsdom 不實作 canvas 2d context；mock HTMLCanvasElement.prototype.getContext 讓 drawImage 可執行
    const drawn: unknown[] = [];
    const fakeCtx = { drawImage: (...args: unknown[]) => drawn.push(args) };
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(fakeCtx as unknown as CanvasRenderingContext2D);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const result = await captureMapCanvas(fakeMap as any);
    vi.restoreAllMocks();

    expect(result).not.toBeNull();
    expect(result!.width).toBe(120);
    expect(result!.height).toBe(90);
    expect(result!.style.width).toBe('100%');
    expect(result!.style.height).toBe('100%');
    expect(drawn).toHaveLength(1);
  });

  it('超過 300ms 沒有 render 事件時回傳 null', async () => {
    vi.useFakeTimers();
    try {
      const fakeMap: FakeMap = {
        once() {},
        getCanvas() { return document.createElement('canvas'); },
        triggerRepaint() {},
      };

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const promise = captureMapCanvas(fakeMap as any);
      await vi.advanceTimersByTimeAsync(300);
      const result = await promise;
      expect(result).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });
});

describe('cloneLabelLayer', () => {
  it('深拷貝後移除所有 data-testid，改標成 data-snapshot', () => {
    const el = document.createElement('div');
    el.setAttribute('data-testid', 'map-regime-label-layer');
    const span1 = document.createElement('span');
    span1.setAttribute('data-testid', 'map-regime-label');
    span1.textContent = '德意志國';
    el.appendChild(span1);
    const span2 = document.createElement('span');
    span2.setAttribute('data-testid', 'map-regime-label');
    span2.textContent = '法蘭西';
    el.appendChild(span2);

    const clone = cloneLabelLayer(el);

    // 根元素
    expect(clone.hasAttribute('data-testid')).toBe(false);
    expect(clone.getAttribute('data-snapshot')).toBe('true');

    // 子元素
    const spans = clone.querySelectorAll('span');
    expect(spans).toHaveLength(2);
    spans.forEach((s) => {
      expect(s.hasAttribute('data-testid')).toBe(false);
      expect(s.getAttribute('data-snapshot')).toBe('true');
    });
  });

  it('不修改原始元素（深拷貝）', () => {
    const el = document.createElement('div');
    const span = document.createElement('span');
    span.setAttribute('data-testid', 'map-regime-label');
    el.appendChild(span);

    cloneLabelLayer(el);

    expect(span.getAttribute('data-testid')).toBe('map-regime-label');
  });
});
