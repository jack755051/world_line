import type { FilterSpecification, LayerSpecification } from 'maplibre-gl';
import type { Campaign, CampaignFC } from '../../core/campaign';

/**
 * 戰役圖層（§11.2）：campaign-fronts／campaign-arrows（線＋箭頭符號）／campaign-sites，依 phase 過濾。
 * source id 與 source-layer 名稱一致（fronts／arrows／sites），之後換成 PMTiles 向量圖磚時只改 source，不改圖層。
 * verified=false 的線畫虛線並標「待考證」，據點改為空心並標「待考證」。
 */
export const CAMPAIGN_SOURCES = ['campaign-fronts', 'campaign-arrows', 'campaign-arrowheads', 'campaign-sites'] as const;
export const AXIS_COLOR = '#b42318';
export const ALLIED_COLOR = '#1d4ed8';
export const FRONT_COLOR = '#7c2d12';
const UNVERIFIED = '待考證';

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
  const lab = (p: Record<string, unknown>, base: string) => (p['verified'] ? base : base ? `${base}（${UNVERIFIED}）` : UNVERIFIED);
  const arrows = c.layers.arrows.features.map((f) => ({ ...f, properties: { ...f.properties, side: sideOf(f.properties), label: lab(f.properties, '') } }));
  const heads = arrows
    .filter((f) => f.geometry.type === 'LineString' && (f.geometry.coordinates as number[][]).length >= 2)
    .map((f) => {
      const cs = f.geometry.coordinates as number[][];
      return { type: 'Feature' as const, properties: { ...f.properties, bearing: bearing(cs[cs.length - 2], cs[cs.length - 1]) }, geometry: { type: 'Point', coordinates: cs[cs.length - 1] } };
    });
  return {
    'campaign-fronts': fc(c.layers.fronts.features.map((f) => ({ ...f, properties: { ...f.properties, label: lab(f.properties, '') } }))),
    'campaign-arrows': fc(arrows),
    'campaign-arrowheads': fc(heads),
    'campaign-sites': fc(c.layers.sites.features.map((f) => ({ ...f, properties: { ...f.properties, side: sideOf(f.properties), label: lab(f.properties, String(f.properties['name'] ?? '')) } }))),
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
    'campaign-fronts': eq(fp, true), 'campaign-fronts-unverified': eq(fp, false), 'campaign-fronts-label': eq(fp, false),
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
    { id: 'campaign-arrows', type: 'line', source: 'campaign-arrows', layout: { 'line-cap': 'round' }, paint: { 'line-color': sideColor, 'line-width': 3.5, 'line-opacity': 0.9 } },
    { id: 'campaign-arrows-unverified', type: 'line', source: 'campaign-arrows', paint: { 'line-color': sideColor, 'line-width': 3, 'line-opacity': 0.85, 'line-dasharray': [2, 1.5] } },
    { id: 'campaign-arrowheads', type: 'symbol', source: 'campaign-arrowheads',
      layout: { 'text-field': '▲', 'text-font': textFont, 'text-size': 18, 'text-rotate': ['get', 'bearing'], 'text-rotation-alignment': 'map', 'text-allow-overlap': true, 'text-ignore-placement': true },
      paint: { 'text-color': sideColor } },
    { id: 'campaign-fronts-label', type: 'symbol', source: 'campaign-fronts', layout: { 'symbol-placement': 'line-center', 'text-field': ['get', 'label'], 'text-font': textFont, 'text-size': 12 }, paint: { 'text-color': FRONT_COLOR, ...halo } },
    { id: 'campaign-arrows-label', type: 'symbol', source: 'campaign-arrows', layout: { 'symbol-placement': 'line-center', 'text-field': ['get', 'label'], 'text-font': textFont, 'text-size': 12 }, paint: { 'text-color': sideColor, ...halo } },
    { id: 'campaign-sites', type: 'circle', source: 'campaign-sites',
      paint: { 'circle-radius': 6, 'circle-color': ['case', ['get', 'verified'], sideColor, '#ffffff'] as unknown as string, 'circle-stroke-color': sideColor, 'circle-stroke-width': 2 } },
    { id: 'campaign-sites-label', type: 'symbol', source: 'campaign-sites',
      layout: { 'text-field': ['get', 'label'], 'text-font': textFont, 'text-size': 12, 'text-offset': [0, 1.1], 'text-anchor': 'top' }, paint: { 'text-color': '#1f2937', ...halo } },
  ] as LayerSpecification[];
}
export const CAMPAIGN_LAYER_IDS = campaignLayers().map((l) => l.id);
