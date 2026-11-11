/** 戰役 P0 示例資料（public/assets/proto/dunkirk-1940.json）：型別與校驗。全部是示例，非史料。 */
export type ProtoSide = 'axis' | 'allied';
export type ProtoEchelon = 'division' | 'corps';
export type ProtoStatus = 'recorded' | 'inferred';

export interface ProtoUnit {
  id: string; side: ProtoSide; name_zh: string; echelon: ProtoEchelon;
  branch: string; parent_id: string | null; sidc: string;
}
export interface ProtoPosition {
  unit_id: string; date: string; lng: number; lat: number; precision_m: number; status: ProtoStatus; source: string;
}
export interface ProtoFront {
  date: string; status: ProtoStatus; method: string;
  override: { type: 'MultiLineString'; coordinates: number[][][] } | null;
}
export interface ProtoEngagement {
  id: string; date: string; lng: number; lat: number;
  units: { unit_id: string; role: 'attacker' | 'defender' }[];
  interaction_tag: string; outcome: string | null; source: string;
}
export interface ProtoData {
  meta: { campaign: string; is_example: true; note?: string; dates: string[]; theater: [number, number, number, number]; land_mask: number[][] };
  units: ProtoUnit[]; positions: ProtoPosition[]; fronts: ProtoFront[]; engagements: ProtoEngagement[];
}

const ISO = /^\d{4}-\d{2}-\d{2}$/;
const fail = (msg: string): never => { throw new Error(`proto data: ${msg}`); };

/** 校驗並回傳型別化資料；`meta.is_example` 必須嚴格為 true（P0 不接受任何非示例資料）。 */
export function validateProtoData(raw: unknown): ProtoData {
  const d = raw as Partial<ProtoData> | null;
  if (!d || typeof d !== 'object') return fail('not an object');
  if (d.meta?.is_example !== true) return fail('meta.is_example must be true');
  const dates = d.meta.dates;
  if (!Array.isArray(dates) || dates.length < 2 || !dates.every((x) => ISO.test(x))) return fail('meta.dates');
  if (!Array.isArray(d.meta.theater) || d.meta.theater.length !== 4) return fail('meta.theater');
  if (!Array.isArray(d.meta.land_mask) || d.meta.land_mask.length < 4) return fail('meta.land_mask');
  for (const k of ['units', 'positions', 'fronts', 'engagements'] as const) if (!Array.isArray(d[k])) return fail(k);
  const ids = new Set<string>();
  for (const u of d.units!) {
    if (!u.id || ids.has(u.id)) return fail(`unit id ${u.id}`);
    ids.add(u.id);
    if (u.side !== 'axis' && u.side !== 'allied') return fail(`unit ${u.id} side`);
    if (typeof u.sidc !== 'string' || u.sidc.length !== 15) return fail(`unit ${u.id} sidc`);
  }
  for (const u of d.units!) if (u.parent_id && !ids.has(u.parent_id)) return fail(`unit ${u.id} parent_id`);
  for (const p of d.positions!) {
    if (!ids.has(p.unit_id)) return fail(`position unit ${p.unit_id}`);
    if (!dates.includes(p.date)) return fail(`position date ${p.date}`);
    if (!Number.isFinite(p.lng) || !Number.isFinite(p.lat)) return fail(`position ${p.unit_id} coords`);
    if (p.source !== 'example') return fail(`position ${p.unit_id} source must be "example"`);
  }
  for (const f of d.fronts!) if (!dates.includes(f.date)) return fail(`front date ${f.date}`);
  for (const e of d.engagements!) {
    if (!dates.includes(e.date)) return fail(`engagement ${e.id} date`);
    if (!e.units.every((x) => ids.has(x.unit_id))) return fail(`engagement ${e.id} units`);
  }
  return d as ProtoData;
}
