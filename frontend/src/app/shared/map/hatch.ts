/** 斜線網底圖片（DESIGN.md：45° 斜線，1.5px 線、間距 6px，無填色）。交戰中用反向斜線，兩方紀錄疊在一起時呈交錯網底。 */
export function hatchImage(color: string, kind: 'partial' | 'contested', pixelRatio = 2): ImageData | null {
  const size = 6 * pixelRatio;
  if (typeof document === 'undefined') return null;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5 * pixelRatio;
  ctx.lineCap = 'square';
  ctx.beginPath();
  if (kind === 'partial') {
    // 由左下到右上，加兩個角讓圖磚無縫
    ctx.moveTo(0, size);
    ctx.lineTo(size, 0);
    ctx.moveTo(-size / 2, size / 2);
    ctx.lineTo(size / 2, -size / 2);
    ctx.moveTo(size / 2, size * 1.5);
    ctx.lineTo(size * 1.5, size / 2);
  } else {
    ctx.moveTo(0, 0);
    ctx.lineTo(size, size);
    ctx.moveTo(-size / 2, size / 2);
    ctx.lineTo(size / 2, size * 1.5);
    ctx.moveTo(size / 2, -size / 2);
    ctx.lineTo(size * 1.5, size / 2);
  }
  ctx.stroke();
  return ctx.getImageData(0, 0, size, size);
}
