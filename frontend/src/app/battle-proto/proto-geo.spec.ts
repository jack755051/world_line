import rawJson from '../../../public/assets/proto/dunkirk-1940.json';
import { describe, expect, it } from 'vitest';
import { validateProtoData, type ProtoData } from './proto-data';
import { aggregateUnits, buildArrows, clipLineToLand, dateToIndex, effectiveT, generateFront, interpolateUnits, isInterpolating, levelForZoom, type UnitPoint } from './proto-geo';
import { battleProtoEnabled } from '../core/features';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const raw: any = rawJson;
const data: ProtoData = validateProtoData(raw);
const opts = { theater: data.meta.theater, land: data.meta.land_mask };

describe('示例資料校驗', () => {
  it('is_example 為 true、3 個日期、20 個師、3–5 個交戰', () => {
    expect(data.meta.is_example).toBe(true);
    expect(data.meta.dates).toHaveLength(3);
    expect(data.units.filter((u) => u.echelon === 'division')).toHaveLength(20);
    expect(data.engagements.length).toBeGreaterThanOrEqual(3);
    expect(data.engagements.length).toBeLessThanOrEqual(5);
    expect(data.fronts.some((f) => f.override !== null)).toBe(true);
  });
  it('is_example 不是 true 就拒絕；來源非 example 也拒絕', () => {
    expect(() => validateProtoData({ ...raw, meta: { ...raw.meta, is_example: false } })).toThrow(/is_example/);
    const bad = structuredClone(raw);
    bad.positions[0].source = '史料';
    expect(() => validateProtoData(bad)).toThrow(/source/);
  });
});

describe('內插與聚合', () => {
  it('整日取記錄位置；半日為兩日中點且標 inferred', () => {
    const p0 = interpolateUnits(data, 0).find((p) => p.id === 'de-7pz')!;
    const a = data.positions.find((p) => p.unit_id === 'de-7pz' && p.date === data.meta.dates[0])!;
    const b = data.positions.find((p) => p.unit_id === 'de-7pz' && p.date === data.meta.dates[1])!;
    expect([p0.lng, p0.lat]).toEqual([a.lng, a.lat]);
    const mid = interpolateUnits(data, 0.5).find((p) => p.id === 'de-7pz')!;
    expect(mid.lng).toBeCloseTo((a.lng + b.lng) / 2, 9);
    expect(mid.lat).toBeCloseTo((a.lat + b.lat) / 2, 9);
    expect(mid.status).toBe('inferred');
    expect(isInterpolating(0.5)).toBe(true);
    expect(isInterpolating(1)).toBe(false);
  });
  it('z<7 軍級、z≥7 師級；軍級位置為子師平均', () => {
    expect(levelForZoom(6.99)).toBe('corps');
    expect(levelForZoom(7)).toBe('division');
    const pts = interpolateUnits(data, 0);
    const corps = aggregateUnits(data.units, pts, 'corps');
    expect(corps).toHaveLength(7);
    const kids = pts.filter((p) => ['de-5pz', 'de-7pz', 'de-32i'].includes(p.id));
    const xv = corps.find((c) => c.id === 'de-xv')!;
    expect(xv.count).toBe(3);
    expect(xv.lng).toBeCloseTo(kids.reduce((s, k) => s + k.lng, 0) / 3, 9);
    expect(aggregateUnits(data.units, pts, 'division')).toHaveLength(20);
  });
  it('reduced-motion 跳格：進度四捨五入、不內插', () => {
    expect(effectiveT(0.4, true)).toBe(0);
    expect(effectiveT(0.6, true)).toBe(1);
    expect(effectiveT(0.4, false)).toBe(0.4);
  });
  it('日期對應索引、無效值回 0', () => {
    expect(dateToIndex(data.meta.dates, '1940-05-20')).toBe(1);
    expect(dateToIndex(data.meta.dates, '1940-05-25')).toBe(2);
    expect(dateToIndex(data.meta.dates, 'oops')).toBe(0);
  });
  it('有位移的單位產生推進箭頭', () => {
    expect(buildArrows(data, 'division', 0).length).toBeGreaterThan(5);
  });
});

describe('Voronoi 前線', () => {
  const inLandFn = (p: number[]) => clipLineToLand([p, [p[0] + 1e-6, p[1]]], opts.land).length > 0;
  it('每個示例日（無 override 時）都產出前線，且全部在陸地上', () => {
    for (const i of [0, 1, 2]) {
      const r = generateFront(interpolateUnits(data, i), opts);
      expect(r.manual).toBe(false);
      expect(r.lines.length).toBeGreaterThan(0);
      for (const l of r.lines) for (const p of l) expect(inLandFn(p)).toBe(true);
      expect(r.bands.length).toBe(r.lines.length * 2);
    }
  });
  it('海上線段被丟掉', () => {
    const land = [[0, 0], [2, 0], [2, 1], [0, 1], [0, 0]]; // lat>1 為海
    const pts: UnitPoint[] = [
      { id: 'a', side: 'axis', lng: 0.5, lat: 1.5, status: 'recorded' },
      { id: 'b', side: 'allied', lng: 1.5, lat: 1.5, status: 'recorded' },
      { id: 'c', side: 'axis', lng: 0.5, lat: 0.5, status: 'recorded' },
      { id: 'd', side: 'allied', lng: 1.5, lat: 0.5, status: 'recorded' },
    ];
    const r = generateFront(pts, { theater: [0, 0, 2, 2], land });
    expect(r.lines.length).toBeGreaterThan(0);
    for (const l of r.lines) for (const p of l) expect(p[1]).toBeLessThanOrEqual(1 + 1e-9);
    const noLand = generateFront(pts, { theater: [0, 0, 2, 2], land: [[0, 1.6], [2, 1.6], [2, 2], [0, 2], [0, 1.6]] });
    expect(noLand.lines.length).toBeGreaterThan(0); // 陸地只剩上方：上半的線留下
    for (const l of noLand.lines) for (const p of l) expect(p[1]).toBeGreaterThanOrEqual(1.6 - 1e-9);
  });
  it('override 取代自動結果', () => {
    const f = data.fronts.find((x) => x.override)!;
    const r = generateFront(interpolateUnits(data, 2), { ...opts, override: f.override!.coordinates });
    expect(r.manual).toBe(true);
    const auto = generateFront(interpolateUnits(data, 2), opts);
    expect(JSON.stringify(r.lines)).not.toBe(JSON.stringify(auto.lines));
    expect(r.lines[0][0][0]).toBeCloseTo(2.85, 1);
  });
});

describe('feature flag', () => {
  it('production（devMode=false）永遠關閉；dev 且開關關閉也關閉', () => {
    expect(battleProtoEnabled(false, true)).toBe(false);
    expect(battleProtoEnabled(true, false)).toBe(false);
    expect(battleProtoEnabled(true, true)).toBe(true);
  });
});
