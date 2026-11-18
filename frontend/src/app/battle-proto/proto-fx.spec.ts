import rawJson from '../../../public/assets/proto/dunkirk-1940.json';
import { describe, expect, it } from 'vitest';
import { validateProtoData } from './proto-data';
import { interpolateUnits } from './proto-geo';
import { arrowCurve, arrowProgress, defaultFx, FX_KEYS, morphRing, pathToRing, pointOnLines, resample, ringArea, sliceCurve, territoryRings } from './proto-fx';

const data = validateProtoData(rawJson);

describe('箭頭曲線與進度', () => {
  it('曲線端點正確、有彎曲', () => {
    const c = arrowCurve([0, 0], [4, 0], 20);
    expect(c).toHaveLength(21);
    expect(c[0]).toEqual([0, 0]);
    expect(c[20][0]).toBeCloseTo(4); expect(c[20][1]).toBeCloseTo(0);
    expect(Math.abs(c[10][1])).toBeGreaterThan(0.1);
  });
  it('sliceCurve 隨 p 逐段變長，p=0 空線，p=1 到終點', () => {
    const c = arrowCurve([0, 0], [4, 0], 20);
    expect(sliceCurve(c, 0).line).toHaveLength(0);
    expect(sliceCurve(c, 0.5).line.length).toBeGreaterThan(5);
    expect(sliceCurve(c, 0.25).line.length).toBeLessThan(sliceCurve(c, 0.75).line.length);
    const full = sliceCurve(c, 1);
    expect(full.head[0]).toBeCloseTo(4);
    expect(Number.isFinite(full.bearing)).toBe(true);
  });
  it('arrowProgress：reduced／靜止＝1；播放中單調、80% 畫滿', () => {
    expect(arrowProgress(0.1, { reduced: true, settled: false })).toBe(1);
    expect(arrowProgress(0.1, { reduced: false, settled: true })).toBe(1);
    expect(arrowProgress(0, { reduced: false, settled: false })).toBe(0);
    expect(arrowProgress(0.4, { reduced: false, settled: false })).toBeCloseTo(0.5);
    expect(arrowProgress(0.9, { reduced: false, settled: false })).toBe(1);
  });
});

describe('領土多邊形與變形', () => {
  const theater = data.meta.theater, land = data.meta.land_mask;
  it('兩陣營各有領土環，且面積總和不超過陸地面積', () => {
    const pts = interpolateUnits(data, 0);
    const ax = territoryRings(pts, 'axis', theater, land), al = territoryRings(pts, 'allied', theater, land);
    expect(ax.length).toBeGreaterThan(0); expect(al.length).toBeGreaterThan(0);
    expect(ringArea(ax[0]) + ringArea(al[0])).toBeLessThanOrEqual(ringArea(land as [number, number][]) + 1e-6);
  });
  it('軸心領土在第 3 日比第 1 日更大（領土跟著推進擴張）', () => {
    const a0 = territoryRings(interpolateUnits(data, 0), 'axis', theater, land)[0];
    const a2 = territoryRings(interpolateUnits(data, 2), 'axis', theater, land)[0];
    expect(ringArea(a2)).toBeGreaterThan(ringArea(a0));
  });
  it('morphRing：f=0／1 等於端點，中間幀為閉合有限環、面積介於其間附近', () => {
    const a = territoryRings(interpolateUnits(data, 0), 'axis', theater, land)[0];
    const b = territoryRings(interpolateUnits(data, 1), 'axis', theater, land)[0];
    const m = morphRing(a, b);
    expect(m(0)).toBe(a); expect(m(1)).toBe(b);
    const mid = m(0.5);
    expect(mid.length).toBeGreaterThan(3);
    expect(mid[0]).toEqual(mid[mid.length - 1]);
    expect(mid.every((p) => Number.isFinite(p[0]) && Number.isFinite(p[1]))).toBe(true);
    const lo = Math.min(ringArea(a), ringArea(b)), hi = Math.max(ringArea(a), ringArea(b));
    expect(ringArea(mid)).toBeGreaterThan(lo * 0.6);
    expect(ringArea(mid)).toBeLessThan(hi * 1.4);
  });
  it('pathToRing／resample 基本行為', () => {
    expect(pathToRing('M0,0L1,0L1,1Z')).toEqual([[0, 0], [1, 0], [1, 1], [0, 0]]);
    const r = resample([[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]], 8);
    expect(r).toHaveLength(9); expect(r[0]).toEqual(r[8]);
  });
});

describe('火花取點與開關', () => {
  it('pointOnLines 在線上、無線回 null', () => {
    expect(pointOnLines([], 0.5)).toBeNull();
    const p = pointOnLines([[[0, 0], [2, 0]], [[5, 5], [5, 7]]], 0.25)!;
    expect(p[1]).toBeCloseTo(0); expect(p[0]).toBeCloseTo(1);
    const q = pointOnLines([[[0, 0], [2, 0]], [[5, 5], [5, 7]]], 0.75)!;
    expect(q[0]).toBeCloseTo(5); expect(q[1]).toBeCloseTo(6);
  });
  it('預設全開、共 7 項', () => {
    const fx = defaultFx();
    expect(FX_KEYS).toHaveLength(7);
    expect(FX_KEYS.every((k) => fx[k])).toBe(true);
  });
});
