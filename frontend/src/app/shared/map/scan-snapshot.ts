import type { Map as MlMap } from 'maplibre-gl';

/**
 * 在下一幀 render 事件內，把地圖 WebGL canvas 複製到普通 2D canvas 並回傳。
 * 不開 preserveDrawingBuffer（避免拖慢 GPU 渲染）。
 * 超過 300ms 未觸發 render 回傳 null。
 */
export function captureMapCanvas(map: MlMap): Promise<HTMLCanvasElement | null> {
  return new Promise((resolve) => {
    let settled = false;

    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      resolve(null);
    }, 300);

    map.once('render', () => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);

      const src = map.getCanvas();
      const dst = document.createElement('canvas');
      dst.width = src.width;
      dst.height = src.height;
      dst.style.width = '100%';
      dst.style.height = '100%';

      const ctx = dst.getContext('2d');
      if (!ctx) { resolve(null); return; }
      ctx.drawImage(src, 0, 0);
      resolve(dst);
    });

    map.triggerRepaint();
  });
}

/**
 * 深拷貝政權名稱 HTML 標籤圖層（`map-regime-label` 那層 div）。
 * 移除所有子元素的 data-testid（改標成 data-snapshot），避免 e2e 選到快照裡的舊標籤。
 */
export function cloneLabelLayer(el: HTMLElement): HTMLElement {
  const clone = el.cloneNode(true) as HTMLElement;

  // 根元素本身若有 data-testid 也一併替換
  if (clone.hasAttribute('data-testid')) {
    clone.removeAttribute('data-testid');
    clone.setAttribute('data-snapshot', 'true');
  }

  clone.querySelectorAll<HTMLElement>('[data-testid]').forEach((node) => {
    node.removeAttribute('data-testid');
    node.setAttribute('data-snapshot', 'true');
  });

  return clone;
}
