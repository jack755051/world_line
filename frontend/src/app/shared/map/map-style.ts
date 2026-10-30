/**
 * 地圖樣式（DESIGN.md「Map Styles」）的純函式部分：把 API 的控制區 feature 加上繪圖用屬性。
 * 不含 MapLibre 物件，方便單元測試。
 */
import type { FeatureCollection, Geometry } from 'geojson';
import type { ControlMapDto, RegimeAlignmentDto, TheaterStateDto } from '../../core/api/api-types';

export const MAP_COLORS = {
  land: '#ece4d2',
  sea: '#cfdbe0',
  coast: '#9fb2ba',
  ink: '#3a2f28',
} as const;

/** 陣營色系（憲法 §6「陣營」、DESIGN.md Camp colors）。 */
export const CAMP_TONES = {
  axis: ['#c8964a', '#b8743d', '#d3ad6a', '#a5683f', '#c98a5e', '#8f6a3a'],
  allies: ['#6f8fb0', '#5f9a8f', '#8aa7c4', '#4f7d99', '#7fae9a', '#9bb3a0'],
  cobelligerent: ['#9c7fa3', '#b394a8', '#85738f', '#a88aa0'],
  neutral: ['#c9c2ad', '#b9b4a4', '#d6cfba', '#aaa596'],
} as const;
export type Camp = keyof typeof CAMP_TONES;

/**
 * 「陣營未建置」色：API 沒有回傳該政權當日的陣營切片（`controllerAlignment` 為 null）時使用。
 * 陣營歸屬須依有來源的正式加入日期判定（憲法 §6），前端不自行推定；這個色刻意避開四個色系、朱紅、error 與控制資料缺候選灰。
 */
export const CAMP_UNASSIGNED_TONE = '#8b7f6c';

/** API 的 camp 值（PRD §6.3）→ 前端色系鍵。 */
const API_CAMP: Record<string, Camp> = { axis: 'axis', allies: 'allies', co_belligerent: 'cobelligerent', neutral: 'neutral' };

export function campOf(alignment: Pick<RegimeAlignmentDto, 'camp'> | null | undefined): Camp | null {
  return (alignment && API_CAMP[alignment.camp]) ?? null;
}

export interface CampTones {
  /** 政權 → 色；沒有陣營資料的政權回「陣營未建置」色 */
  toneFor: ToneFor;
  /** 政權 → 陣營；沒有陣營資料回 null */
  campFor: (regimeId: string | null | undefined) => Camp | null;
}

/**
 * 填色＝陣營（Tai 2026-10-31 拍板）：每個陣營只用一個代表色（色系第一個色票），政權不另配填色；
 * 政權之間用邊框與名稱標籤區分，控制類型用紋理／邊框區分（DESIGN.md Control types）。
 * ⚠ 與 DESIGN.md「Camp colors」不同：DESIGN.md 原本要在同陣營內依圖著色輪用色票，讓相鄰政權不同色；此處依拍板改成同陣營同色。
 */
export const CAMP_FILL: Record<Camp, string> = {
  axis: CAMP_TONES.axis[0],
  allies: CAMP_TONES.allies[0],
  cobelligerent: CAMP_TONES.cobelligerent[0],
  neutral: CAMP_TONES.neutral[0],
};

/** 依 API 回傳的 `controllerAlignment` 決定每個控制方的陣營與填色（PRD §12 Q11：色系由 regime_alignments 決定）。 */
export function campTonesFrom(dto: ControlMapDto | null | undefined): CampTones {
  const camps = new Map<string, Camp>();
  for (const f of dto?.featureCollection.features ?? []) {
    const id = f.properties.controllerRegimeId;
    if (camps.has(id)) continue;
    const camp = campOf(f.properties.controllerAlignment);
    if (camp) camps.set(id, camp);
  }
  const campFor = (id: string | null | undefined): Camp | null => (id && camps.get(id)) || null;
  return {
    toneFor: (id) => {
      const c = campFor(id);
      return c ? CAMP_FILL[c] : CAMP_UNASSIGNED_TONE;
    },
    campFor,
  };
}

/** 控制資料缺候選 A（DESIGN.md：紙底＋6px 網格細墨點 35%）。M1 實測前先用 A。 */
export const GAP_STYLE = { dotColor: 'rgba(58,47,40,0.35)', grid: 6 } as const;
export const GAP_IMAGE_ID = 'wl-gap-dots';

export interface GapProps {
  gapId: string;
  reason: string;
}

/**
 * 控制資料缺（R9）：API 回傳的涵蓋備註幾何（`coverageNotes`）。只畫 API 給的範圍，前端不推導、不以任何控制類型代替。
 * 戰區範圍與 reference_land 尚未建置，所以只有寫了涵蓋備註的地方會出現（PRD §6.4，2026-10-31 暫代，待拍板）。
 */
export function gapFeatures(dto: ControlMapDto | null | undefined): FeatureCollection<Geometry, GapProps> {
  return {
    type: 'FeatureCollection',
    features: (dto?.coverageNotes ?? []).map((n) => ({
      type: 'Feature',
      id: n.id,
      geometry: n.geometry as unknown as Geometry,
      properties: { gapId: n.id, reason: n.reason },
    })),
  };
}

export const CONTROL_TYPES = ['direct_rule', 'military_occupation', 'puppet_administration', 'partial', 'contested'] as const;
export type ControlType = (typeof CONTROL_TYPES)[number];

export type Evidence = 'attested' | 'interpolated' | 'outside' | 'unknown';

/** 憲法 §9／PRD §8.5：依戰區狀態判斷史料或推估；查不到狀態時一律視為不明（以推估樣式呈現，保守原則）。 */
export function evidenceFor(theaterCode: string, theaters: readonly TheaterStateDto[] | null | undefined): Evidence {
  const s = theaters?.find((x) => x.theaterCode === theaterCode)?.state;
  if (s === 'attested' || s === 'interpolated' || s === 'outside') return s;
  return 'unknown';
}

export function darken(hex: string, amount: number): string {
  const n = parseInt(hex.slice(1), 16);
  const f = (v: number) => Math.max(0, Math.min(255, Math.round(v * (1 - amount))));
  const r = f((n >> 16) & 255);
  const g = f((n >> 8) & 255);
  const b = f(n & 255);
  return `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`;
}

export interface DecoratedProps {
  versionId: string;
  controlRecordId: string;
  controllerRegimeId: string;
  controlType: string;
  theaterCode: string;
  /** 控制方當日陣營；'unassigned'＝陣營未建置 */
  camp: Camp | 'unassigned';
  evidence: Evidence;
  /** 線條樣式群組：solid（史料）／dotted（傀儡代管扶植方邊框）／dashed（推估或不明） */
  wlLineKind: 'solid' | 'dotted' | 'dashed';
  wlFill: string;
  wlFillOpacity: number;
  wlPattern: string;
  wlLine: string;
  wlLineWidth: number;
  wlLineOpacity: number;
}

export type ToneFor = (regimeId: string | null | undefined) => string;

/** 預設：還沒有陣營資料，所有政權都用「陣營未建置」色。 */
export const unassignedTone: ToneFor = () => CAMP_UNASSIGNED_TONE;

export function hatchImageId(color: string, kind: 'partial' | 'contested'): string {
  return `wl-hatch-${kind}-${color.replace('#', '')}`;
}

/** 推估過渡：填色不透明度 ×0.55、邊框虛線（DESIGN.md Evidence states）。 */
export const INTERPOLATED_OPACITY_FACTOR = 0.55;

export function decorateFeatures(
  dto: ControlMapDto | null | undefined,
  toneFor: ToneFor = unassignedTone,
): FeatureCollection<Geometry, DecoratedProps> {
  const features = dto?.featureCollection.features ?? [];
  return {
    type: 'FeatureCollection',
    features: features.map((f) => {
      const p = f.properties;
      const evidence = evidenceFor(p.theaterCode, dto?.theaters);
      const attested = evidence === 'attested';
      const tone = toneFor(p.controllerRegimeId);
      const k = attested ? 1 : INTERPOLATED_OPACITY_FACTOR;
      let fillOpacity = 0.85;
      let pattern = '';
      let line: string = MAP_COLORS.ink;
      let lineWidth = 0.75;
      let lineOpacity = 0.4;
      let lineKind: DecoratedProps['wlLineKind'] = 'solid';
      switch (p.controlType) {
        case 'military_occupation':
          fillOpacity = 0.6;
          line = darken(tone, 0.25);
          lineWidth = 2;
          lineOpacity = 1;
          break;
        case 'puppet_administration':
          line = toneFor(p.patronRegimeId);
          lineWidth = 1.5;
          lineOpacity = 1;
          lineKind = 'dotted';
          break;
        case 'partial':
        case 'contested':
          fillOpacity = 1;
          pattern = hatchImageId(tone, p.controlType);
          line = tone;
          lineWidth = 0.75;
          lineOpacity = 0.8;
          break;
      }
      if (!attested) lineKind = 'dashed';
      const props: DecoratedProps = {
        versionId: p.versionId,
        controlRecordId: p.controlRecordId,
        controllerRegimeId: p.controllerRegimeId,
        controlType: p.controlType,
        theaterCode: p.theaterCode,
        camp: campOf(p.controllerAlignment) ?? 'unassigned',
        evidence,
        wlLineKind: lineKind,
        wlFill: tone,
        wlFillOpacity: +(fillOpacity * k).toFixed(3),
        wlPattern: pattern,
        wlLine: line,
        wlLineWidth: lineWidth,
        wlLineOpacity: lineOpacity,
      };
      return { type: 'Feature', id: p.versionId, geometry: f.geometry as unknown as Geometry, properties: props };
    }),
  };
}

export interface ControlLabel {
  versionId: string;
  regimeId: string;
  text: string;
  /** 標籤位置：控制區（最大的那塊多邊形）內離邊界最遠的點 */
  lngLat: [number, number];
  /** 該多邊形的經緯度外框 [minX, minY, maxX, maxY]，畫面上太小就不標 */
  bbox: [number, number, number, number];
}

type Ring = number[][];

function ringArea(r: Ring): number {
  let a = 0;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) a += (r[j][0] - r[i][0]) * (r[j][1] + r[i][1]);
  return Math.abs(a / 2);
}

function pointInRing(x: number, y: number, r: Ring): boolean {
  let inside = false;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    const [xi, yi] = r[i];
    const [xj, yj] = r[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function segDist2(px: number, py: number, a: number[], b: number[]): number {
  let x = a[0];
  let y = a[1];
  let dx = b[0] - x;
  let dy = b[1] - y;
  if (dx !== 0 || dy !== 0) {
    const t = Math.max(0, Math.min(1, ((px - x) * dx + (py - y) * dy) / (dx * dx + dy * dy)));
    x += dx * t;
    y += dy * t;
  }
  dx = px - x;
  dy = py - y;
  return dx * dx + dy * dy;
}

/** 多邊形內離邊界最遠的點（格點搜尋＋兩輪細化；標籤用，不需精確）。洞內的點不算。 */
export function labelPoint(poly: Ring[]): [number, number] {
  const outer = poly[0];
  let [minX, minY, maxX, maxY] = [Infinity, Infinity, -Infinity, -Infinity];
  for (const [x, y] of outer) {
    minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
  }
  const inside = (x: number, y: number) => pointInRing(x, y, outer) && !poly.slice(1).some((h) => pointInRing(x, y, h));
  const dist = (x: number, y: number) => {
    let d = Infinity;
    for (const r of poly) for (let i = 0, j = r.length - 1; i < r.length; j = i++) d = Math.min(d, segDist2(x, y, r[i], r[j]));
    return d;
  };
  let best: [number, number] = [(minX + maxX) / 2, (minY + maxY) / 2];
  let bestD = inside(...best) ? dist(...best) : -1;
  let cx = best[0];
  let cy = best[1];
  let w = maxX - minX;
  let h = maxY - minY;
  for (let round = 0; round < 3; round++) {
    const n = 24;
    for (let i = 0; i <= n; i++)
      for (let j = 0; j <= n; j++) {
        const x = cx - w / 2 + (w * i) / n;
        const y = cy - h / 2 + (h * j) / n;
        if (!inside(x, y)) continue;
        const d = dist(x, y);
        if (d > bestD) { bestD = d; best = [x, y]; }
      }
    [cx, cy] = best;
    w /= 4;
    h /= 4;
  }
  return best;
}

/**
 * 政權名稱標籤（PRD §8.2：政權標籤預設顯示自稱）。每個控制區標一次，位置在其最大多邊形內。
 * 文字只來自 API 的政權名稱；查不到名稱就不標（不自行命名）。
 */
export function controlLabels(dto: ControlMapDto | null | undefined, nameFor: (regimeId: string) => string | null): ControlLabel[] {
  const out: ControlLabel[] = [];
  for (const f of dto?.featureCollection.features ?? []) {
    const p = f.properties;
    const text = nameFor(p.controllerRegimeId);
    if (!text) continue;
    const g = f.geometry as unknown as Geometry;
    const polys: Ring[][] = g.type === 'Polygon' ? [g.coordinates as Ring[]] : g.type === 'MultiPolygon' ? (g.coordinates as Ring[][]) : [];
    if (polys.length === 0) continue;
    const biggest = polys.reduce((a, b) => (ringArea(b[0]) > ringArea(a[0]) ? b : a));
    let [minX, minY, maxX, maxY] = [Infinity, Infinity, -Infinity, -Infinity];
    for (const [x, y] of biggest[0]) {
      minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
    }
    out.push({ versionId: p.versionId, regimeId: p.controllerRegimeId, text, lngLat: labelPoint(biggest), bbox: [minX, minY, maxX, maxY] });
  }
  return out;
}
