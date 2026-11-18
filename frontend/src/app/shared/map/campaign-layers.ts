import type { FilterSpecification, LayerSpecification } from 'maplibre-gl';
import type { Campaign, CampaignFC } from '../../core/campaign';

/**
 * 戰役圖層（§11.2）：campaign-fronts／campaign-arrows（線＋箭頭符號）／campaign-sites，依 phase 過濾。
 * source id 與 source-layer 名稱一致（fronts／arrows／sites），之後換成 PMTiles 向量圖磚時只改 source，不改圖層。
 * verified=false 的線畫虛線並標「待考證」，據點改為空心並標「待考證」。
 */
export const CAMPAIGN_SOURCES = ['campaign-fronts', 'campaign-front-labels', 'campaign-arrows', 'campaign-arrowheads', 'campaign-sites'] as const;
export const AXIS_COLOR = '#b42318';
export const ALLIED_COLOR = '#1d4ed8';
export const FRONT_COLOR = '#7c2d12';
const UNVERIFIED = '待考證';
/** 文字推定／待查證前線（幾何由文字敘述推定，非地圖描繪）：geom_basis='derived' 或 inference='文字推定'。 */
export const INFERRED_LABEL = '（文字推定・待查證）';
export function isInferredFront(p: Record<string, unknown>): boolean {
  return p['geom_basis'] === 'derived' || p['inference'] === '文字推定';
}
const INFERRED: FilterSpecification = ['any', ['==', ['get', 'geom_basis'], 'derived'], ['==', ['get', 'inference'], '文字推定']] as unknown as FilterSpecification;
/** 名稱：靜態檔用 name；API（DB）列用 place／label.zh-Hant；都沒有時給通用名，避免只剩「待考證」。 */
function textOf(v: unknown): string {
  if (typeof v === 'string') return v;
  if (v && typeof v === 'object') return String((v as Record<string, unknown>)['zh-Hant'] ?? (v as Record<string, unknown>)['en'] ?? '');
  return '';
}
export function siteName(p: Record<string, unknown>): string {
  return textOf(p['name']) || textOf(p['place']) || textOf(p['label']) || '地點';
}
export function frontName(p: Record<string, unknown>): string {
  return textOf(p['name']) || textOf(p['label']) || (typeof p['date'] === 'string' ? `前線 ${p['date']}` : '前線');
}
const LABEL_TEXT = ['format', ['get', 'labelBase'], {}, ['get', 'labelNote'], { 'font-scale': 0.78 }] as unknown as string;
/** 線（或多線第一段）沿長度的中點；平面近似即可（只用於放標籤）。 */
export function midpoint(g: { type: string; coordinates: unknown }): number[] | null {
  const cs = (g.type === 'LineString' ? g.coordinates : g.type === 'MultiLineString' ? (g.coordinates as number[][][])[0] : null) as number[][] | null;
  if (!cs || cs.length < 2) return null;
  const seg = cs.slice(1).map((b, i) => Math.hypot(b[0] - cs[i][0], b[1] - cs[i][1]));
  let half = seg.reduce((a, b) => a + b, 0) / 2;
  for (let i = 0; i < seg.length; i++) {
    if (half <= seg[i] && seg[i] > 0) { const t = half / seg[i]; return [cs[i][0] + (cs[i + 1][0] - cs[i][0]) * t, cs[i][1] + (cs[i + 1][1] - cs[i][1]) * t]; }
    half -= seg[i];
  }
  return cs[cs.length - 1];
}
/** 線的各段（LineString 一段；MultiLineString 多段）。 */
function lineParts(g: { type: string; coordinates: unknown }): number[][][] {
  return g.type === 'LineString' ? [g.coordinates as number[][]] : g.type === 'MultiLineString' ? (g.coordinates as number[][][]) : [];
}
const partLength = (cs: number[][]) => cs.slice(1).reduce((a, b, i) => a + Math.hypot(b[0] - cs[i][0], b[1] - cs[i][1]), 0);
/** 線總長（平面近似，只用來挑放標籤的那一段）。 */
export function lineLength(g: { type: string; coordinates: unknown }): number {
  return lineParts(g).reduce((a, cs) => a + partLength(cs), 0);
}
/** 多線中最長的一段（給中點用）；非線回傳 null。 */
export function longestPart(g: { type: string; coordinates: unknown }): { type: string; coordinates: unknown } | null {
  const ps = lineParts(g);
  if (!ps.length) return null;
  return { type: 'LineString', coordinates: ps.reduce((a, b) => (partLength(b) > partLength(a) ? b : a)) };
}
export const ARROWHEAD_IMAGE = 'campaign-arrowhead';
/** 箭頭符號：SDF 三角形（朝上＝北，icon-rotate 轉到線的方向；icon-color 依陣營上色）。 */
export function arrowheadImage(size = 40): { width: number; height: number; data: Uint8ClampedArray } {
  const data = new Uint8ClampedArray(size * size * 4);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const half = ((y + 1) / size) * (size / 2);
    const inside = Math.abs(x + 0.5 - size / 2) <= half;
    const i = (y * size + x) * 4;
    data[i] = data[i + 1] = data[i + 2] = 255; data[i + 3] = inside ? 255 : 0;
  }
  return { width: size, height: size, data };
}

function bearing(a: number[], b: number[]): number {
  const r = Math.PI / 180;
  const y = Math.sin((b[0] - a[0]) * r) * Math.cos(b[1] * r);
  const x = Math.cos(a[1] * r) * Math.sin(b[1] * r) - Math.sin(a[1] * r) * Math.cos(b[1] * r) * Math.cos((b[0] - a[0]) * r);
  return (Math.atan2(y, x) / r + 360) % 360;
}

export const SOVIET_COLOR = '#7e22ce';
export const CONTESTED_COLOR = '#6b7280';
/** 配色組：build.py 已算好 group（axis／allied／soviet／contested／unknown）；舊檔沒有 group 時用 side／controller 推。 */
function sideOf(p: Record<string, unknown>): string {
  if (typeof p['group'] === 'string') return p['group'] as string;
  const s = String(p['side'] ?? p['controller'] ?? '');
  if (s.startsWith('axis')) return 'axis';
  if (s.startsWith('allied')) return 'allied';
  return /^德/.test(String(p['unit'] ?? '')) ? 'axis' : 'allied';
}

/** 把戰役 JSON 轉成各 source 的 GeoJSON（補 side、label、箭頭方向）。 */
export function campaignSourceData(c: Campaign): Record<(typeof CAMPAIGN_SOURCES)[number], CampaignFC> {
  const fc = (features: CampaignFC['features']): CampaignFC => ({ type: 'FeatureCollection', features });
  // 標籤＝名稱＋小字註記（format 表達式）：未查證「（待考證）」、文字推定前線「（文字推定・待查證）」；不單獨顯示「待考證」。
  const note = (p: Record<string, unknown>) => (isInferredFront(p) ? INFERRED_LABEL : p['verified'] ? '' : `（${UNVERIFIED}）`);
  const lab = (p: Record<string, unknown>, base: string) => {
    const n = note(p);
    return { label: base + n, labelBase: base, labelNote: n };
  };
  const arrows = c.layers.arrows.features.map((f) => ({ ...f, properties: { ...f.properties, side: sideOf(f.properties), ...lab(f.properties, String(f.properties['name'] ?? '') || '進攻方向') } }));
  const heads = arrows
    .filter((f) => f.geometry.type === 'LineString' && (f.geometry.coordinates as number[][]).length >= 2)
    .map((f) => {
      const cs = f.geometry.coordinates as number[][];
      return { type: 'Feature' as const, properties: { ...f.properties, bearing: bearing(cs[cs.length - 2], cs[cs.length - 1]) }, geometry: { type: 'Point', coordinates: cs[cs.length - 1] } };
    });
  const fronts = c.layers.fronts.features.map((f) => ({ ...f, properties: { ...f.properties, ...lab(f.properties, frontName(f.properties)) } }));
  // 前線標籤：同一階段同一日期（同一標籤文字）只出一個，放在該日期最長的一段的線長中點（點標籤）；
  // 標籤圖層開碰撞避讓，避免多段同日前線的標籤互相疊在一起。
  const best = new Map<string, { f: (typeof fronts)[number]; len: number }>();
  for (const f of fronts) {
    const p = f.properties as Record<string, unknown>;
    const key = `${String(p['phase'] ?? '')}|${String(p['date'] ?? '')}|${String(p['labelBase'])}`;
    const len = lineLength(f.geometry);
    const cur = best.get(key);
    if (!cur || len > cur.len) best.set(key, { f, len });
  }
  const frontLabels = [...best.values()].flatMap(({ f }) => {
    const m = midpoint(longestPart(f.geometry) ?? f.geometry);
    return m ? [{ type: 'Feature' as const, properties: f.properties, geometry: { type: 'Point', coordinates: m } }] : [];
  });
  return {
    'campaign-fronts': fc(fronts),
    'campaign-front-labels': fc(frontLabels),
    'campaign-arrows': fc(arrows),
    'campaign-arrowheads': fc(heads),
    'campaign-sites': fc(c.layers.sites.features.map((f) => ({ ...f, properties: { ...f.properties, side: sideOf(f.properties), ...lab(f.properties, siteName(f.properties)) } }))),
  };
}

/** 前線：某階段沒有新前線時沿用最近一個有前線的階段。 */
export function frontPhaseFor(c: Campaign, phase: number): number {
  let best = 0;
  for (const f of c.layers.fronts.features) if (f.properties.phase <= phase && f.properties.phase > best) best = f.properties.phase;
  return best;
}

export function campaignFilters(c: Campaign, phase: number): Record<string, FilterSpecification> {
  const fp = frontPhaseFor(c, phase);
  const eq = (p: number, v?: boolean): FilterSpecification => (v === undefined ? ['==', ['get', 'phase'], p] : ['all', ['==', ['get', 'phase'], p], ['==', ['get', 'verified'], v]]) as FilterSpecification;
  const le = (p: number, v?: boolean): FilterSpecification => (v === undefined ? ['<=', ['get', 'phase'], p] : ['all', ['<=', ['get', 'phase'], p], ['==', ['get', 'verified'], v]]) as FilterSpecification;
  return {
    'campaign-fronts': ['all', eq(fp, true), ['!', INFERRED]] as unknown as FilterSpecification,
    'campaign-fronts-unverified': ['all', eq(fp, false), ['!', INFERRED]] as unknown as FilterSpecification,
    'campaign-fronts-inferred': ['all', eq(fp), INFERRED] as unknown as FilterSpecification,
    'campaign-fronts-label': ['all', eq(fp), ['any', ['==', ['get', 'verified'], false], INFERRED]] as unknown as FilterSpecification,
    'campaign-arrows': eq(phase, true), 'campaign-arrows-unverified': eq(phase, false), 'campaign-arrows-label': eq(phase, false),
    'campaign-arrowheads': eq(phase),
    'campaign-sites': le(phase), 'campaign-sites-label': le(phase),
  };
}

const sideColor = ['match', ['get', 'side'], 'axis', AXIS_COLOR, 'allied', ALLIED_COLOR, 'soviet', SOVIET_COLOR, CONTESTED_COLOR] as unknown as string;
const textFont = ['Open Sans Regular', 'Arial Unicode MS Regular'];
const halo = { 'text-halo-color': '#ffffff', 'text-halo-width': 1.6 };

export function campaignLayers(): LayerSpecification[] {
  return [
    { id: 'campaign-fronts', type: 'line', source: 'campaign-fronts', layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': FRONT_COLOR, 'line-width': 4 } },
    { id: 'campaign-fronts-unverified', type: 'line', source: 'campaign-fronts', layout: { 'line-join': 'round' }, paint: { 'line-color': FRONT_COLOR, 'line-width': 3, 'line-dasharray': [2, 2] } },
    { id: 'campaign-fronts-inferred', type: 'line', source: 'campaign-fronts', layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': FRONT_COLOR, 'line-width': 2.5, 'line-opacity': 0.9, 'line-dasharray': [0.6, 1.8] } },
    { id: 'campaign-arrows', type: 'line', source: 'campaign-arrows', layout: { 'line-cap': 'round' }, paint: { 'line-color': sideColor, 'line-width': 3.5, 'line-opacity': 0.9 } },
    { id: 'campaign-arrows-unverified', type: 'line', source: 'campaign-arrows', paint: { 'line-color': sideColor, 'line-width': 3, 'line-opacity': 0.85, 'line-dasharray': [2, 1.5] } },
    { id: 'campaign-arrowheads', type: 'symbol', source: 'campaign-arrowheads',
      layout: { 'icon-image': ARROWHEAD_IMAGE, 'icon-size': 0.5, 'icon-rotate': ['get', 'bearing'], 'icon-rotation-alignment': 'map', 'icon-allow-overlap': true, 'icon-ignore-placement': true },
      paint: { 'icon-color': sideColor } },
    { id: 'campaign-fronts-label', type: 'symbol', source: 'campaign-front-labels', layout: { 'text-allow-overlap': false, 'text-ignore-placement': false, 'text-variable-anchor': ['left', 'right', 'top', 'bottom'], 'text-radial-offset': 0.8, 'text-padding': 4, 'text-max-width': 30, 'text-field': LABEL_TEXT, 'text-font': textFont, 'text-size': 12 }, paint: { 'text-color': FRONT_COLOR, ...halo } },
    { id: 'campaign-arrows-label', type: 'symbol', source: 'campaign-arrows', layout: { 'symbol-placement': 'line-center', 'text-field': LABEL_TEXT, 'text-font': textFont, 'text-size': 12 }, paint: { 'text-color': sideColor, ...halo } },
    { id: 'campaign-sites', type: 'circle', source: 'campaign-sites',
      paint: { 'circle-radius': 6, 'circle-color': ['case', ['get', 'verified'], sideColor, '#ffffff'] as unknown as string, 'circle-stroke-color': sideColor, 'circle-stroke-width': 2 } },
    { id: 'campaign-sites-label', type: 'symbol', source: 'campaign-sites',
      layout: { 'text-field': LABEL_TEXT, 'text-font': textFont, 'text-size': 12, 'text-offset': [0, 1.1], 'text-anchor': 'top' }, paint: { 'text-color': '#1f2937', ...halo } },
  ] as LayerSpecification[];
}
export const CAMPAIGN_LAYER_IDS = campaignLayers().map((l) => l.id);
