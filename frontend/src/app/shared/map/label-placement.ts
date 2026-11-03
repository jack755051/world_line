import type { FeatureCollection, Point } from 'geojson';

export interface Box { x: number; y: number; w: number; h: number; }

/** 矩形碰撞：中心距離小於寬度之和的一半即為重疊。 */
export function rectsOverlap(a: Box, b: Box): boolean {
  return Math.abs(a.x - b.x) * 2 < a.w + b.w && Math.abs(a.y - b.y) * 2 < a.h + b.h;
}

// ─── 首都圓點障礙常數（與 buildBaseStyle capital-dot 圖層共用數值）────────────
/** 首都圓點半徑（對應 circle-radius）。 */
export const CAPITAL_DOT_RADIUS = 3.5;
/** 首都圓點描邊寬度（對應 circle-stroke-width）。 */
export const CAPITAL_DOT_STROKE = 1.5;
/** 圓點障礙框最小間距（px）；確保 HTML 標籤不貼近圓點視覺邊緣。 */
export const CAPITAL_DOT_GAP = 3;

// ─── MapLibre capital-label 符號層常數 ─────────────────────────────────────────
// 對應 buildBaseStyle capital-label 圖層的 text-size / text-halo-width / text-radial-offset
const _CAP_LABEL_FONT_PX = 11;
const _CAP_LABEL_HALO_PX = 1.5;
const _CAP_LABEL_RADIAL_PX = Math.round(0.9 * _CAP_LABEL_FONT_PX); // ≈10px
const _CAP_LABEL_AVG_CHAR_PX = 6.5; // 11px Open Sans 平均字寬估計
const _CAP_LABEL_H_OBS = 16;        // 估算渲染高度（含 halo）

// ─── 標籤字型常數 ─────────────────────────────────────────────────────────────

/** 一般字體：每字元估計寬度（px）、框高、左右邊距。 */
export const LABEL_CHAR_PX = 14;
export const LABEL_H = 20;
export const LABEL_PAD = 8;
/** 縮小字體：對應 CSS class wl-regime-label--sm（10px font-size）。 */
export const LABEL_SMALL_CHAR_PX = 12;
export const LABEL_SMALL_H = 16;

/** 標籤候選位置的視窗邊界留白（px）：候選框必須完全在地圖容器內（含此邊距）。 */
export const VIEWPORT_MARGIN = 4;

// ─── Canvas 實測標籤寬度 ──────────────────────────────────────────────────────

const _labelWidthCache = new Map<string, number>();

/** 清除標籤寬度快取（測試或字型重載時使用）。 */
export function clearLabelWidthCache(): void { _labelWidthCache.clear(); }

/**
 * 計算 .wl-regime-label（或 --sm 變體）的渲染像素寬度：
 * - 使用 OffscreenCanvas / HTMLCanvasElement measureText（600 serif，模擬 wl-font-serif）
 * - 加上 letter-spacing 0.16em × 字元數 + 左右 padding（正常 12px 為 6px×2；小字 10px 為 4px×2）
 * - 結果快取（key = `${small?1:0}:${text}`）；不支援 canvas 時退回字元估算值（不觸發 layout）。
 */
export function measureLabelWidth(text: string, small: boolean): number {
  const key = `${small ? 1 : 0}:${text}`;
  const cached = _labelWidthCache.get(key);
  if (cached !== undefined) return cached;

  const fontSize = small ? 10 : 12;
  const letterSpacingPx = 0.16 * fontSize; // letter-spacing: 0.16em
  const paddingH = small ? 8 : 12;         // 2 × (4px | 6px)

  let w: number;
  try {
    let ctx2d: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D | null = null;
    if (typeof OffscreenCanvas !== 'undefined') {
      ctx2d = new OffscreenCanvas(1, 1).getContext('2d');
    } else if (typeof document !== 'undefined') {
      ctx2d = document.createElement('canvas').getContext('2d');
    }
    if (!ctx2d) throw new Error('no canvas');
    ctx2d.font = `600 ${fontSize}px serif`;
    w = Math.ceil(ctx2d.measureText(text).width + text.length * letterSpacingPx) + paddingH;
  } catch {
    const charPx = small ? LABEL_SMALL_CHAR_PX : LABEL_CHAR_PX;
    w = text.length * charPx + LABEL_PAD;
  }

  _labelWidthCache.set(key, w);
  return w;
}

/**
 * 計算地圖上所有首都的保留框（像素）：
 * - 每座首都貢獻一個圓點框（以 radius+stroke+gap 計算邊長，確保視覺間距 ≥ CAPITAL_DOT_GAP）。
 * - zoom ≥ 3.5 時額外加上名稱框：MapLibre text-variable-anchor 有 8 個可能位置；
 *   取以圓點為中心、覆蓋所有錨點位置的單一外框（穩健且不需預測 MapLibre 實際選擇方向）。
 * - 世界副本：取離地圖中心 mapCenterLng 最近的副本。
 */
export function capitalObstacleBoxes(
  capitals: FeatureCollection | null,
  project: (lngLat: [number, number]) => { x: number; y: number },
  mapCenterLng: number,
  zoom: number,
): Box[] {
  if (!capitals) return [];
  const showLabel = zoom >= 3.5;
  // 圓點障礙尺寸 = (半徑 + 描邊 + 間距) × 2
  const dotObsSize = (CAPITAL_DOT_RADIUS + CAPITAL_DOT_STROKE + CAPITAL_DOT_GAP) * 2; // 16px
  const boxes: Box[] = [];
  for (const f of capitals.features) {
    if (f.geometry.type !== 'Point') continue;
    const [rawLng, lat] = (f.geometry as Point).coordinates as [number, number];
    const k = Math.round((mapCenterLng - rawLng) / 360) * 360;
    const lng = rawLng + k;
    const p = project([lng, lat]);
    boxes.push({ x: p.x, y: p.y, w: dotObsSize, h: dotObsSize });
    if (showLabel) {
      const label = (f.properties as Record<string, unknown> | null)?.['label'] as string | undefined ?? '';
      const lw = Math.max(label.length * _CAP_LABEL_AVG_CHAR_PX + _CAP_LABEL_HALO_PX * 2, 1);
      // 單一外框覆蓋 text-variable-anchor 所有 8 方向：
      //   水平最遠 = radial偏移 + lw/2；垂直最遠 = radial偏移 + 高/2
      // 以圓點為中心（x=p.x, y=p.y），寬高確保任何方向的名稱都在框內
      const obsW = lw + 2 * (_CAP_LABEL_RADIAL_PX + _CAP_LABEL_HALO_PX + 3);
      const obsH = _CAP_LABEL_H_OBS + 2 * (_CAP_LABEL_RADIAL_PX + _CAP_LABEL_HALO_PX + 3);
      boxes.push({ x: p.x, y: p.y, w: obsW, h: obsH });
    }
  }
  return boxes;
}

/**
 * 在 `shifts`（像素，預設 [0, -18, 18, -30, 30]）中找到最小的垂直位移 dy，
 * 使置中於 (cx, cy + dy)、大小 (w × h) 的矩形不與任何 obstacle 重疊。
 *
 * 返回位移量（0 代表原位無衝突），或 null（所有候選皆仍重疊→隱藏標籤）。
 */
export function avoidCapitals(
  cx: number,
  cy: number,
  w: number,
  h: number,
  obstacles: Box[],
  shifts: number[] = [0, -18, 18, -30, 30],
): number | null {
  for (const dy of shifts) {
    const box: Box = { x: cx, y: cy + dy, w, h };
    if (!obstacles.some((o) => rectsOverlap(box, o))) return dy;
  }
  return null;
}

// ─── 浮動 UI 障礙物 ──────────────────────────────────────────────────────────

/** 地圖上方浮動 UI 的 CSS selector 清單（聚焦遮罩與標籤層本身不在此列）。 */
export const UI_OBSTACLE_SELECTORS: readonly string[] = [
  '[data-testid="legend"]',
  '[data-testid="camp-layer-toggle"]',
  '[data-testid="map-incomplete-period-hint"]',
  '.maplibregl-ctrl-attrib',
  'wl-regime-sheet [data-testid="regime-sheet"]',
];

/**
 * 量測浮動 UI 元素相對於地圖容器的障礙框（加 6px 邊距）。
 * 量不到（元素不存在或 size=0）的項目略過；適合每次 placeLabels 呼叫一次。
 */
export function uiObstacleBoxes(containerEl: HTMLElement): Box[] {
  const cr = containerEl.getBoundingClientRect();
  const out: Box[] = [];
  for (const sel of UI_OBSTACLE_SELECTORS) {
    const el = document.querySelector(sel);
    if (!el) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const x = (r.left + r.right) / 2 - cr.left;
    const y = (r.top + r.bottom) / 2 - cr.top;
    out.push({ x, y, w: r.width + 12, h: r.height + 12 });
  }
  return out;
}

// ─── 網格候選點 ──────────────────────────────────────────────────────────────

/** 投影座標環（像素）的點在環內測試（射線法）。 */
export function pointInProjectedRing(
  px: number,
  py: number,
  ring: ReadonlyArray<{ x: number; y: number }>,
): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const { x: xi, y: yi } = ring[i];
    const { x: xj, y: yj } = ring[j];
    if (yi > py !== yj > py && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

/**
 * 在 GeoJSON 外環（lng/lat）投影到像素後，取 gridSize×gridSize 網格，
 * 篩選落在多邊形內且中心點在地圖可視範圍內（含 VIEWPORT_MARGIN 邊距）的點，
 * 依離 labelPx 由近到遠排序，最多回傳 maxCandidates 筆。
 */
export function gridCandidates(
  ring: number[][],
  project: (lngLat: [number, number]) => { x: number; y: number },
  labelPx: { x: number; y: number },
  mapWidth: number,
  mapHeight: number,
  gridSize = 5,
  maxCandidates = 30,
): Array<{ x: number; y: number }> {
  if (ring.length < 3) return [];
  const projRing = ring.map(([lng, lat]) => project([lng, lat] as [number, number]));
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const { x, y } of projRing) {
    if (x < minX) minX = x; if (y < minY) minY = y;
    if (x > maxX) maxX = x; if (y > maxY) maxY = y;
  }
  const candidates: Array<{ x: number; y: number; d2: number }> = [];
  for (let gi = 0; gi <= gridSize; gi++) {
    for (let gj = 0; gj <= gridSize; gj++) {
      const x = minX + (maxX - minX) * gi / gridSize;
      const y = minY + (maxY - minY) * gj / gridSize;
      if (!pointInProjectedRing(x, y, projRing)) continue;
      // 候選點中心需在地圖可視範圍內（留 VIEWPORT_MARGIN 邊距）
      if (x < VIEWPORT_MARGIN || x > mapWidth - VIEWPORT_MARGIN ||
          y < VIEWPORT_MARGIN || y > mapHeight - VIEWPORT_MARGIN) continue;
      const dx = x - labelPx.x;
      const dy = y - labelPx.y;
      candidates.push({ x, y, d2: dx * dx + dy * dy });
    }
  }
  candidates.sort((a, b) => a.d2 - b.d2);
  return candidates.slice(0, maxCandidates).map(({ x, y }) => ({ x, y }));
}

/**
 * 為一個標籤找到可放置的位置（含縮小字回退）：
 *
 * 階段 1（一般字體）：在 labelPoint 垂直位移 shifts 中找第一個不與障礙物重疊、
 *   且完全在地圖可視範圍內（含 VIEWPORT_MARGIN）的位置。
 * 階段 2（一般字體）：依序嘗試 gridPts 中每個網格候選點（dy=0）。
 * 階段 3（縮小字體 wl-regime-label--sm）：同樣再試一輪 shifts + gridPts。
 * 全部失敗則回傳 null（略去標籤）。
 *
 * @param labelW 一般字體的完整標籤寬度（px），由 measureLabelWidth 或估算提供。
 *               縮小字體寬度由此按 LABEL_SMALL_CHAR_PX/LABEL_CHAR_PX 比例推算。
 * @param mapW   地圖容器寬度（px）；預設 Infinity（不做視窗裁切）。
 * @param mapH   地圖容器高度（px）；預設 Infinity。
 */
export function findLabelPlacement(
  cx: number,
  cy: number,
  labelW: number,
  obstacles: Box[],
  gridPts: ReadonlyArray<{ x: number; y: number }>,
  shifts: number[] = [0, -18, 18, -30, 30],
  mapW = Infinity,
  mapH = Infinity,
): { x: number; y: number; small: boolean } | null {
  // 從一般字體寬度反推縮小字體寬度（保持 padding 不變，按字元寬比例縮放）
  const smallW = Math.round((labelW - LABEL_PAD) * LABEL_SMALL_CHAR_PX / LABEL_CHAR_PX) + LABEL_PAD;

  const fits = (bx: number, by: number, bw: number, bh: number): boolean => {
    // 視窗邊界：標籤框必須完全在可視範圍內（留 VIEWPORT_MARGIN）
    if (mapW !== Infinity && (bx - bw / 2 < VIEWPORT_MARGIN || bx + bw / 2 > mapW - VIEWPORT_MARGIN)) return false;
    if (mapH !== Infinity && (by - bh / 2 < VIEWPORT_MARGIN || by + bh / 2 > mapH - VIEWPORT_MARGIN)) return false;
    return !obstacles.some((o) => rectsOverlap({ x: bx, y: by, w: bw, h: bh }, o));
  };

  for (const small of [false, true] as const) {
    const w = small ? smallW : labelW;
    const h = small ? LABEL_SMALL_H : LABEL_H;

    // 階段 1：labelPoint ± shifts
    for (const dy of shifts) {
      if (fits(cx, cy + dy, w, h)) return { x: cx, y: cy + dy, small };
    }
    // 階段 2：網格候選點
    for (const pt of gridPts) {
      if (fits(pt.x, pt.y, w, h)) return { x: pt.x, y: pt.y, small };
    }
  }
  return null;
}
