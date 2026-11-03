import type { Feature, FeatureCollection, Geometry } from 'geojson';
import type { SovereigntyMapDto } from '../../core/api/api-types';
import { CAMP_FILL, campOf, darken, hatchImageId, labelPoint, MAP_COLORS, type Camp, type ControlLabel } from './map-style';

/**
 * 主權圖層（國界）樣式（2026-10-31 試驗）：
 * - 填色依政權（Tai：政權優先於陣營），一個政權一種顏色；同一政權換版（疆界變動）顏色不變。
 * - 陣營只作補充：資訊卡顯示，或開「陣營外框」圖層時以陣營色描外框；不改填色。
 * - layerStatus = not_sovereign（例：比利時與北法軍政府）以斜線＋虛線外框表示「非主權」。
 * - 佔領區（Tai 2026-10-31「德國佔領大半歐陸但地圖上看不出來」）：有佔領歸屬（properties.occupation）時，
 *   底色改用佔領國的顏色，依控制程度分三種深淺（參考 Wikipedia Greater German Reich 1942 圖）：
 *   併入（正式或事實）最深、接近本土色；民政（帝國專員轄區、保護國、總督府）中等；軍事管理最淺。仍疊斜線＋虛線邊（非主權）。
 *   沒有佔領歸屬的非主權政權（例：滿洲國）維持原樣（紙底＋自己顏色的斜線）。
 */

/** 政權 slug → 填色。手動指定主要政權，讓相鄰國家明顯不同；其餘依 slug 雜湊取色盤。 */
export const REGIME_COLORS: Record<string, string> = {
  'deutsches-reich': '#a7a3c9',
  'french-third-republic': '#c9b48a',
  'french-state-vichy': '#d4c08f',
  'united-kingdom': '#a9c3d6',
  'kingdom-of-italy': '#c7a3b8',
  'soviet-union': '#d6a99a',
  'polish-republic': '#e0cf9a',
  'free-city-of-danzig': '#e6b8a2',
  'czechoslovak-republic': '#9fc7b0',
  'slovak-state-1939': '#b9d3a0',
  'kingdom-of-hungary': '#9cc3c9',
  'kingdom-of-romania': '#e2c29c',
  'tsardom-of-bulgaria': '#b4c99a',
  'kingdom-of-yugoslavia': '#cfa9a3',
  'kingdom-of-greece': '#a3bfd9',
  'albanian-kingdom': '#d9b38c',
  'albania-under-italy': '#d1b0c2',
  'republic-of-turkey': '#c9b39f',
  'federal-state-of-austria': '#d8c7a0',
  'swiss-confederation': '#e3a9a9',
  'kingdom-of-belgium': '#d9cc8f',
  'kingdom-of-the-netherlands': '#e0b48f',
  'grand-duchy-of-luxembourg': '#b7cfe0',
  'kingdom-of-denmark': '#d7b0a0',
  'kingdom-of-norway': '#b4cfb4',
  'kingdom-of-sweden': '#c2c8e0',
  'republic-of-finland': '#a8d0c4',
  'republic-of-estonia': '#c6b4d6',
  'republic-of-latvia': '#d6c3a0',
  'republic-of-lithuania': '#b0c8a0',
  'estonian-ssr': '#d2aca4',
  'latvian-ssr': '#d2aca4',
  'lithuanian-ssr': '#d2aca4',
  'spanish-republic': '#d8b4a6',
  'spanish-state': '#d8b4a6',
  'portuguese-republic': '#a9cdb9',
  'ireland-eire': '#b9d6a6',
  'mil-admin-belgium-northern-france': '#a7a3c9',
  // 德佔波蘭軍事管理（1939-10-06→10-26，非主權、斜線）：與比北軍政府同用德國色系
  'german-military-administration-poland': '#a7a3c9',
};
/** 英國屬地與義屬愛琴海群島沿用母國色（Tai 2026-10-31：屬地維持獨立政權，只共用顏色）。 */
const SAME_COLOR_AS: Record<string, string> = {
  'gibraltar-crown-colony': 'united-kingdom',
  'malta-crown-colony': 'united-kingdom',
  'isle-of-man': 'united-kingdom',
  'bailiwick-of-guernsey': 'united-kingdom',
  'bailiwick-of-jersey': 'united-kingdom',
  'italian-aegean-islands': 'kingdom-of-italy',
};
/** 佔領國色往紙底（陸地色）混合的比例：0＝本土色，越大越淡。 */
export const OCCUPATION_TINT: Record<string, number> = { annexed: 0.12, civil_administration: 0.42, military_administration: 0.68 };
export const OCCUPATION_KINDS = ['annexed', 'civil_administration', 'military_administration'] as const;

/** 兩色線性混合：t=0 → a，t=1 → b。 */
export function mixHex(a: string, b: string, t: number): string {
  const pa = parseInt(a.slice(1), 16);
  const pb = parseInt(b.slice(1), 16);
  const ch = (sh: number) => Math.round(((pa >> sh) & 255) * (1 - t) + ((pb >> sh) & 255) * t);
  return `#${((1 << 24) | (ch(16) << 16) | (ch(8) << 8) | ch(0)).toString(16).slice(1)}`;
}

/** 佔領區底色：佔領國色依控制程度淡化（未知程度當軍事管理，最淡）。 */
export function occupationTint(occupierSlug: string, controlKind: string): string {
  return mixHex(regimeColor(occupierSlug), MAP_COLORS.land, OCCUPATION_TINT[controlKind] ?? OCCUPATION_TINT['military_administration']);
}

const FALLBACK = ['#cdb8a0', '#b8c8b0', '#c0b8d0', '#d0c0a8', '#a8c0c8', '#d0b0b8', '#b8d0c0', '#c8c0a0'];

/** 測試資料的 slug 會帶 `-<tag>` 尾碼；比對時先試完整 slug，再去掉最後一段。 */
export function regimeColor(slug: string): string {
  const base = SAME_COLOR_AS[slug] ?? slug;
  if (REGIME_COLORS[base]) return REGIME_COLORS[base];
  const trimmed = base.replace(/-[0-9a-f]{8}$/, '');
  const t = SAME_COLOR_AS[trimmed] ?? trimmed;
  if (REGIME_COLORS[t]) return REGIME_COLORS[t];
  let h = 0;
  for (const ch of t) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return FALLBACK[h % FALLBACK.length];
}

export interface SovereigntyProps {
  recordId: string;
  regimeId: string;
  regimeSlug: string;
  layerStatus: string;
  wlFill: string;
  /** not_sovereign → 斜線圖樣 id；否則空字串 */
  wlPattern: string;
  /** 斜線圖層的底色：佔領區＝佔領國色（依控制程度淡化）；其他非主權＝紙底 */
  wlBase: string;
  /** 佔領方（沒有佔領歸屬 → 空字串） */
  occupierRegimeId: string;
  occupierSlug: string;
  /** annexed／civil_administration／military_administration；沒有 → 空字串 */
  controlKind: string;
  /** 陣營外框色（沒有陣營切片 → 空字串，不推定） */
  wlCampLine: string;
  camp: Camp | '';
  /** 起訖事件是否有待查證（沒有合格引用） */
  pending: boolean;
}

export function decorateSovereignty(dto: SovereigntyMapDto | null | undefined): FeatureCollection<Geometry, SovereigntyProps> {
  const features: Feature<Geometry, SovereigntyProps>[] = (dto?.featureCollection.features ?? []).map((f) => {
    const p = f.properties;
    const fill = regimeColor(p.regimeSlug);
    const camp = campOf(p.regimeAlignment ?? null);
    const notSovereign = p.layerStatus === 'not_sovereign';
    const occ = p.occupation ?? null;
    // 佔領區：底色＝佔領國色（淡化），斜線用佔領國色加深，在底色上仍看得出來
    const base = occ ? occupationTint(occ.occupierSlug, occ.controlKind) : MAP_COLORS.land;
    const hatchColor = occ ? darken(regimeColor(occ.occupierSlug), 0.3) : fill;
    return {
      type: 'Feature',
      id: p.recordId,
      geometry: f.geometry as unknown as Geometry,
      properties: {
        recordId: p.recordId,
        regimeId: p.regimeId,
        regimeSlug: p.regimeSlug,
        layerStatus: p.layerStatus,
        wlFill: fill,
        wlPattern: notSovereign ? hatchImageId(hatchColor, 'contested') : '',
        wlBase: base,
        occupierRegimeId: occ?.occupierRegimeId ?? '',
        occupierSlug: occ?.occupierSlug ?? '',
        controlKind: occ?.controlKind ?? '',
        wlCampLine: camp ? CAMP_FILL[camp] : '',
        camp: camp ?? '',
        pending: p.startEvent?.verification === 'pending' || p.endEvent?.verification === 'pending',
      },
    };
  });
  return { type: 'FeatureCollection', features };
}

type Ring = [number, number][];
function ringArea(r: Ring): number {
  let a = 0;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) a += (r[j][0] + r[i][0]) * (r[j][1] - r[i][1]);
  return Math.abs(a / 2);
}

/**
 * 手動指定標籤點與旋轉角度覆寫（鍵為 regimeSlug）。
 * 用於自動算法仍有偏差的政權（如資料特殊的狹長形）；優先於自動計算。
 * 座標為 WGS84 [lng, lat]；rotation 為 CSS 度（順時針為正）。
 */
export const LABEL_OVERRIDES: Record<string, { lngLat?: [number, number]; rotation?: number }> = {
  // 第二次世界大戰期間西藏：東西向極狹長，自動算法偏西
  'tibet': { lngLat: [88.5, 32.2] },
  // 西藏地方（各歷史時期 slug 可能不同）
  'tibetan-local-government': { lngLat: [88.5, 32.2] },
};

/** 國名標籤：每筆主權紀錄取最大的多邊形放標籤（地圖元件再依畫面大小決定顯示與否）。 */
/**
 * 標籤位置快取（依主權紀錄 id）：紀錄只會撤回、不會改幾何，所以同一筆紀錄在每個日期的標籤點都一樣。
 * labelPoint 對大多邊形要數百毫秒；播放、跳日期時重算全部會卡住主執行緒（Tai 2026-11-01 效能問題）。
 */
const LABEL_CACHE_MAX = 3000;
const labelCache = new Map<string, { lngLat: [number, number]; bbox: [number, number, number, number]; rotation: number; ring: number[][] }>();
function labelGeometry(recordId: string, regimeSlug: string, g: Geometry) {
  const hit = labelCache.get(recordId);
  if (hit) return hit;
  const polys: Ring[][] = g.type === 'Polygon' ? [g.coordinates as Ring[]] : g.type === 'MultiPolygon' ? (g.coordinates as Ring[][]) : [];
  if (polys.length === 0) return null;
  const biggest = polys.reduce((a, b) => (ringArea(b[0]) > ringArea(a[0]) ? b : a));
  let [minX, minY, maxX, maxY] = [Infinity, Infinity, -Infinity, -Infinity];
  for (const [x, y] of biggest[0]) {
    minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
  }
  const ov = LABEL_OVERRIDES[regimeSlug] ?? {};
  const lngLat = ov.lngLat ?? labelPoint(biggest);
  const rotation = ov.rotation ?? 0;
  const v = { lngLat, bbox: [minX, minY, maxX, maxY] as [number, number, number, number], rotation, ring: biggest[0] };
  if (labelCache.size >= LABEL_CACHE_MAX) labelCache.delete(labelCache.keys().next().value as string);
  labelCache.set(recordId, v);
  return v;
}

export function sovereigntyLabels(dto: SovereigntyMapDto | null | undefined, nameFor: (regimeId: string) => string | null): ControlLabel[] {
  const out: ControlLabel[] = [];
  for (const f of dto?.featureCollection.features ?? []) {
    const p = f.properties;
    const text = nameFor(p.regimeId);
    if (!text) continue;
    const lg = labelGeometry(p.recordId, p.regimeSlug, f.geometry as unknown as Geometry);
    if (!lg) continue;
    out.push({ versionId: `sov-${p.recordId}`, regimeId: p.regimeId, text, lngLat: lg.lngLat, bbox: lg.bbox, fit: 1, rotation: lg.rotation || undefined, ring: lg.ring });
  }
  // 大的先放：互撞時保留大國名稱
  return out.sort((a, b) => (b.bbox[2] - b.bbox[0]) * (b.bbox[3] - b.bbox[1]) - (a.bbox[2] - a.bbox[0]) * (a.bbox[3] - a.bbox[1]));
}
