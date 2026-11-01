/**
 * 地圖資訊卡定位：依點擊位置放在點的右側（放不下就左側），上半部點擊往下長、下半部點擊往上長，
 * 一律留在地圖容器內（容器下緣就是時間軸上緣，所以不會被時間軸擋住）；卡片太高時用 maxHeight 讓卡片內部捲動。
 */
export interface CardPlacement {
  left: number;
  top: number | null;
  bottom: number | null;
  maxHeight: number;
}

export const CARD_MARGIN = 8;
const GAP = 12;
const LIFT = 40;
const MIN_H = 200;

export function placeCard(x: number, y: number, containerW: number, containerH: number, cardW = 340): CardPlacement {
  const m = CARD_MARGIN;
  let left: number;
  if (x + GAP + cardW <= containerW - m) left = x + GAP;
  else if (x - GAP - cardW >= m) left = x - GAP - cardW;
  else left = Math.max(m, containerW - m - cardW);
  const room = Math.max(MIN_H, containerH - 2 * m);
  const clampEdge = (v: number) => Math.max(m, Math.min(v, Math.max(m, containerH - m - Math.min(MIN_H, room))));
  if (y <= containerH / 2) {
    const top = clampEdge(y - LIFT);
    return { left, top, bottom: null, maxHeight: Math.max(0, containerH - top - m) };
  }
  const bottom = clampEdge(containerH - (y + LIFT));
  return { left, top: null, bottom, maxHeight: Math.max(0, containerH - bottom - m) };
}
