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
 * 依 API 回傳的 `controllerAlignment` 決定每個控制方的陣營與色（PRD §12 Q11：色系由 regime_alignments 決定）。
 * 同色系內依政權在資料中出現的順序輪用色票（相鄰政權可區分的圖著色留待多政權資料，TODO）。
 * 只看控制方自己的陣營切片；扶植方若不是任何區塊的控制方，沒有資料 → 陣營未建置色。
 */
export function campTonesFrom(dto: ControlMapDto | null | undefined): CampTones {
  const camps = new Map<string, Camp>();
  const tones = new Map<string, string>();
  const used: Record<Camp, number> = { axis: 0, allies: 0, cobelligerent: 0, neutral: 0 };
  for (const f of dto?.featureCollection.features ?? []) {
    const id = f.properties.controllerRegimeId;
    if (tones.has(id)) continue;
    const camp = campOf(f.properties.controllerAlignment);
    if (!camp) {
      tones.set(id, CAMP_UNASSIGNED_TONE);
      continue;
    }
    const palette = CAMP_TONES[camp];
    camps.set(id, camp);
    tones.set(id, palette[used[camp]++ % palette.length]);
  }
  return {
    toneFor: (id) => (id && tones.get(id)) || CAMP_UNASSIGNED_TONE,
    campFor: (id) => (id && camps.get(id)) || null,
  };
}

/** 控制資料缺候選 A（DESIGN.md：紙底＋6px 網格細墨點 35%）。M1 實測前先用 A。 */
export const GAP_STYLE = { dotColor: 'rgba(58,47,40,0.35)', grid: 6 } as const;

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
