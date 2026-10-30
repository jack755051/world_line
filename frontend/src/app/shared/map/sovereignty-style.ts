import type { Feature, FeatureCollection, Geometry } from 'geojson';
import type { SovereigntyMapDto } from '../../core/api/api-types';
import { CAMP_FILL, campOf, hatchImageId, labelPoint, type Camp, type ControlLabel } from './map-style';

/**
 * 主權圖層（國界）樣式（2026-10-31 試驗）：
 * - 填色依政權（Tai：政權優先於陣營），一個政權一種顏色；同一政權換版（疆界變動）顏色不變。
 * - 陣營只作補充：資訊卡顯示，或開「陣營外框」圖層時以陣營色描外框；不改填色。
 * - layerStatus = not_sovereign（例：比利時與北法軍政府）以斜線＋虛線外框表示「非主權」。
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
        wlPattern: notSovereign ? hatchImageId(fill, 'contested') : '',
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

/** 國名標籤：每筆主權紀錄取最大的多邊形放標籤（地圖元件再依畫面大小決定顯示與否）。 */
export function sovereigntyLabels(dto: SovereigntyMapDto | null | undefined, nameFor: (regimeId: string) => string | null): ControlLabel[] {
  const out: ControlLabel[] = [];
  for (const f of dto?.featureCollection.features ?? []) {
    const p = f.properties;
    const text = nameFor(p.regimeId);
    if (!text) continue;
    const g = f.geometry as unknown as Geometry;
    const polys: Ring[][] = g.type === 'Polygon' ? [g.coordinates as Ring[]] : g.type === 'MultiPolygon' ? (g.coordinates as Ring[][]) : [];
    if (polys.length === 0) continue;
    const biggest = polys.reduce((a, b) => (ringArea(b[0]) > ringArea(a[0]) ? b : a));
    let [minX, minY, maxX, maxY] = [Infinity, Infinity, -Infinity, -Infinity];
    for (const [x, y] of biggest[0]) {
      minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
    }
    out.push({ versionId: `sov-${p.recordId}`, regimeId: p.regimeId, text, lngLat: labelPoint(biggest), bbox: [minX, minY, maxX, maxY], fit: 1 });
  }
  // 大的先放：互撞時保留大國名稱
  return out.sort((a, b) => (b.bbox[2] - b.bbox[0]) * (b.bbox[3] - b.bbox[1]) - (a.bbox[2] - a.bbox[0]) * (a.bbox[3] - a.bbox[1]));
}
