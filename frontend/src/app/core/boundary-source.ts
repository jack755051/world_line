import { isDevMode } from '@angular/core';
/**
 * 疆界來源功能開關（ARCHITECTURE.md §9 遷移步驟 4）：`boundarySource=geojson|tiles`，預設 tiles（Tai 2026-11-04 18:46）。
 * 正式上線（production build，isDevMode()=false）一律 tiles，忽略網址與 localStorage；開發環境保留 geojson 當備援。
 * - geojson：第 1 層，依日期向 API 取 /sovereignty（現行）。
 * - tiles：第 2、3 層，向量圖磚（開發期由 Martin 提供），換日期只改 filter，不向 API 取主權資料。
 * 設定方式：網址 `?boundarySource=tiles`（同時記到 localStorage，之後不帶參數也沿用；`?boundarySource=geojson` 切回）。
 * 圖磚 TileJSON 位址：`?tilesUrl=` 或 localStorage `wl.tilesUrl`，預設本機 Martin。
 */
export type BoundarySource = 'geojson' | 'tiles';

export const BOUNDARY_SOURCE_KEY = 'wl.boundarySource';
export const TILES_URL_KEY = 'wl.tilesUrl';
/** 開發：tools/tiles/martin.sh 起的 Martin（docker，127.0.0.1:3010），來源名 boundaries。 */
export const DEFAULT_TILES_URL = 'http://127.0.0.1:3010/boundaries';
/**
 * 正式上線（production build）的預設：與網站同源的 `/tiles/boundaries`（TileJSON，例：反向代理到 Martin 或 PMTiles 服務）
 * 與 `/tiles/overlay.json`；部署方式見 release-checklist。開發環境沿用本機 Martin／nginx。
 */
export const PROD_TILES_PATH = '/tiles/boundaries';
export const PROD_OVERLAY_PATH = '/tiles/overlay.json';
function prodUrl(path: string): string {
  return (globalThis.location?.origin ?? '') + path;
}

type Store = Pick<Storage, 'getItem' | 'setItem'>;

function safeStore(): Store | null {
  try {
    return typeof localStorage === 'undefined' ? null : localStorage;
  } catch {
    return null;
  }
}

export function readBoundarySource(search: string = globalThis.location?.search ?? '', store: Store | null = safeStore(), production = !isDevMode()): BoundarySource {
  if (production) return 'tiles';
  const q = new URLSearchParams(search).get('boundarySource');
  if (q === 'tiles' || q === 'geojson') {
    try { store?.setItem(BOUNDARY_SOURCE_KEY, q); } catch { /* 無法記住也照常 */ }
    return q;
  }
  const saved = store?.getItem(BOUNDARY_SOURCE_KEY);
  return saved === 'geojson' ? 'geojson' : 'tiles';
}

export function readTilesUrl(search: string = globalThis.location?.search ?? '', store: Store | null = safeStore(), production = !isDevMode()): string {
  if (production) return new URLSearchParams(search).get('tilesUrl') || prodUrl(PROD_TILES_PATH);
  const q = new URLSearchParams(search).get('tilesUrl');
  if (q) {
    try { store?.setItem(TILES_URL_KEY, q); } catch { /* 無法記住也照常 */ }
    return q;
  }
  return store?.getItem(TILES_URL_KEY) || DEFAULT_TILES_URL;
}

const EPOCH_MS = Date.UTC(1900, 0, 1);
/** 圖磚的整數日：從 1900-01-01 起算的天數（更早為負數），與 boundary_periods 一致。 */
export function dayNumber(iso: string): number {
  const [y, m, d] = iso.split('-').map(Number);
  const t = new Date(0);
  t.setUTCFullYear(y, m - 1, d); // 支援 0100 年前後等 Date.UTC 會誤解的年份
  t.setUTCHours(0, 0, 0, 0);
  return Math.round((t.getTime() - EPOCH_MS) / 86_400_000);
}

/** overlay 圖磚（控制區、控制資料缺；§9 步驟 5）：`?overlayTilesUrl=`，預設與疆界圖磚同一個 Martin 的 overlay 來源。 */
export const OVERLAY_TILES_URL_KEY = 'wl.overlayTilesUrl';
export function readOverlayTilesUrl(search: string = globalThis.location?.search ?? '', store: Store | null = safeStore(), production = !isDevMode()): string {
  if (production) return new URLSearchParams(search).get('overlayTilesUrl') || readTilesUrl(search, store, true).replace(/\/boundaries\/?$/, '/overlay');
  const q = new URLSearchParams(search).get('overlayTilesUrl');
  if (q) {
    try { store?.setItem(OVERLAY_TILES_URL_KEY, q); } catch { /* 無法記住也照常 */ }
    return q;
  }
  return store?.getItem(OVERLAY_TILES_URL_KEY) || readTilesUrl(search, store, false).replace(/\/boundaries\/?$/, '/overlay');
}

/** overlay JSON（各區間中繼資料；§9 步驟 5）：`?overlayUrl=`，預設本機 nginx（tools/tiles/overlay-nginx.sh，127.0.0.1:3011）。 */
export const OVERLAY_URL_KEY = 'wl.overlayUrl';
export const DEFAULT_OVERLAY_URL = 'http://127.0.0.1:3011/overlay.json';
export function readOverlayUrl(search: string = globalThis.location?.search ?? '', store: Store | null = safeStore(), production = !isDevMode()): string {
  if (production) return new URLSearchParams(search).get('overlayUrl') || prodUrl(PROD_OVERLAY_PATH);
  const q = new URLSearchParams(search).get('overlayUrl');
  if (q) {
    try { store?.setItem(OVERLAY_URL_KEY, q); } catch { /* 無法記住也照常 */ }
    return q;
  }
  return store?.getItem(OVERLAY_URL_KEY) || DEFAULT_OVERLAY_URL;
}
