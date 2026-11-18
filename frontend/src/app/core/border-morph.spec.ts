import { describe, expect, it } from 'vitest';
import {
  MAX_VERTEX_RATIO, alignRing, incompatibility, interpolate, isSourced, planMorph, polysOf, resampleRing, signedArea, sourcedBorders,
  type BorderFC, type BorderFeature, type Poly,
} from './border-morph';

/** 測試資料（非史料）：方框／正多邊形，只為驗證插值與拓撲判斷。 */
const box = (x0: number, y0: number, x1: number, y1: number): Poly => [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]];
const ngon = (cx: number, cy: number, r: number, n: number): Poly => {
  const ring = Array.from({ length: n }, (_, i) => [cx + r * Math.cos((2 * Math.PI * i) / n), cy + r * Math.sin((2 * Math.PI * i) / n)] as [number, number]);
  return [[...ring, ring[0]]];
};
const feat = (regimeId: string, recordId: string, polys: Poly[], sourceId: string | null = 'src-test'): BorderFeature => ({
  type: 'Feature', id: recordId,
  geometry: polys.length === 1 ? { type: 'Polygon', coordinates: polys[0] } : { type: 'MultiPolygon', coordinates: polys },
  properties: { regimeId, recordId, geometry: sourceId ? { sourceId } : null },
});
const fc = (...f: BorderFeature[]): BorderFC => ({ type: 'FeatureCollection', features: f });

describe('§19.2.4 疆界漸變：重採樣與對齊', () => {
  it('resampleRing 依周長等距取 n 點，點都在原邊上', () => {
    const r = resampleRing(box(0, 0, 4, 4)[0], 8);
    expect(r).toHaveLength(8);
    expect(r[0]).toEqual([0, 0]);
    expect(r[1]).toEqual([2, 0]);
    expect(r[2]).toEqual([4, 0]);
    for (const [x, y] of r) expect(x === 0 || x === 4 || y === 0 || y === 4).toBe(true);
  });
  it('alignRing 方向相反時翻轉、並旋轉起點到最近點', () => {
    const a = resampleRing(box(0, 0, 4, 4)[0], 16);
    const reversed = a.slice().reverse();
    const rotated = [...reversed.slice(5), ...reversed.slice(0, 5)];
    const b = alignRing(a, rotated);
    expect(Math.sign(signedArea(b))).toBe(Math.sign(signedArea(a)));
    expect(b).toEqual(a);
  });
});

describe('§19.2.4 (iv) 拓撲判斷與 fallback', () => {
  it('同政權、單一多邊形、頂點數相近 → morph', () => {
    expect(incompatibility([box(0, 0, 4, 4)], [ngon(2, 2, 3, 12)])).toBeNull();
  });
  it('分裂／合併（多邊形數不同）→ polygon-count', () => {
    expect(incompatibility([box(0, 0, 4, 4)], [box(0, 0, 1, 1), box(2, 2, 3, 3)])).toBe('polygon-count');
  });
  it('島嶼增減（洞數不同）→ hole-count', () => {
    const withHole: Poly = [box(0, 0, 4, 4)[0], box(1, 1, 2, 2)[0].slice().reverse()];
    expect(incompatibility([box(0, 0, 4, 4)], [withHole])).toBe('hole-count');
  });
  it(`頂點數差超過 ${MAX_VERTEX_RATIO} 倍 → vertex-ratio`, () => {
    expect(incompatibility([box(0, 0, 4, 4)], [ngon(2, 2, 2, 4 * MAX_VERTEX_RATIO + 1)])).toBe('vertex-ratio');
  });
  it('planMorph：相容 → morph；不相容與只在一邊的 → fade；同一筆紀錄 → same', () => {
    const a = fc(
      feat('A', 'a1', [box(0, 0, 4, 4)]),
      feat('B', 'b1', [box(10, 0, 14, 4)]),
      feat('C', 'c1', [box(20, 0, 24, 4)]),
      feat('D', 'd1', [box(30, 0, 34, 4)]),
    );
    const b = fc(
      feat('A', 'a2', [box(0, 0, 5, 4)]),
      feat('B', 'b2', [box(10, 0, 11, 1), box(12, 2, 13, 3)]), // 分裂
      feat('C', 'c1', [box(20, 0, 24, 4)]), // 不變
      feat('E', 'e1', [box(40, 0, 44, 4)]), // 新出現
    );
    const p = planMorph(a, b);
    expect(p.morph.map((m) => m.key)).toEqual(['A']);
    expect(p.same.map((f) => f.properties?.['recordId'])).toEqual(['c1']);
    expect(p.fade.map((f) => `${f.key}:${f.reason}`).sort()).toEqual(['B:polygon-count', 'D:unpaired', 'E:unpaired']);
    expect(p.mode).toBe('mixed');
  });
  it('只有不相容的變化 → mode = fade（整段交叉淡入淡出）', () => {
    const p = planMorph(fc(feat('A', 'a1', [box(0, 0, 4, 4)])), fc(feat('A', 'a2', [box(0, 0, 1, 1), box(2, 2, 3, 3)])));
    expect(p.mode).toBe('fade');
  });
});

describe('§19.2.4 插值', () => {
  const plan = planMorph(fc(feat('A', 'a1', [box(0, 0, 4, 4)])), fc(feat('A', 'a2', [box(2, 0, 6, 4)])));
  it('t=0 等於起點、t=1 等於終點、t=0.5 在中間；中間形狀都標 transitional', () => {
    const xs = (t: number) => (polysOf(interpolate(plan, t).features[0].geometry)![0][0]).map((p) => p[0]);
    expect(Math.min(...xs(0))).toBeCloseTo(0);
    expect(Math.max(...xs(1))).toBeCloseTo(6);
    expect(Math.min(...xs(0.5))).toBeCloseTo(1);
    expect(Math.max(...xs(0.5))).toBeCloseTo(5);
    for (const f of interpolate(plan, 0.5).features) expect(f.properties?.['transitional']).toBe(true);
  });
  it('環保持封閉（首尾同點）', () => {
    const ring = polysOf(interpolate(plan, 0.3).features[0].geometry)![0][0];
    expect(ring[0]).toEqual(ring[ring.length - 1]);
  });
  it('fade：舊形狀不透明度 1−t、新形狀 t', () => {
    const p = planMorph(fc(feat('A', 'a1', [box(0, 0, 4, 4)])), fc(feat('A', 'a2', [box(0, 0, 1, 1), box(2, 2, 3, 3)])));
    const o = interpolate(p, 0.25).features.map((f) => f.properties?.['o']);
    expect(o).toEqual([0.75, 0.25]);
    expect(interpolate(p, 1).features.map((f) => f.properties?.['o'])).toEqual([1]);
  });
});

describe('§19.2.4 (ii)(iii) 停在階段時只剩有出處的疆界', () => {
  it('isSourced：幾何沒有 sourceId → 無出處', () => {
    expect(isSourced(feat('A', 'a', [box(0, 0, 1, 1)]))).toBe(true);
    expect(isSourced(feat('A', 'a', [box(0, 0, 1, 1)], null))).toBe(false);
  });
  it('sourcedBorders 去掉無出處與任何 transitional 要素', () => {
    const tx = { ...feat('T', 't', [box(0, 0, 1, 1)]), properties: { ...feat('T', 't', [box(0, 0, 1, 1)]).properties, transitional: true } };
    const out = sourcedBorders(fc(feat('A', 'a', [box(0, 0, 1, 1)]), feat('B', 'b', [box(0, 0, 1, 1)], null), tx));
    expect(out.features.map((f) => f.properties?.['recordId'])).toEqual(['a']);
  });
  it('無出處的疆界不參與漸變', () => {
    const p = planMorph(fc(feat('A', 'a1', [box(0, 0, 4, 4)], null)), fc(feat('A', 'a2', [box(0, 0, 5, 4)])));
    expect(p.morph).toHaveLength(0);
    expect(p.fade.map((f) => [f.from, !!f.to])).toEqual([[null, true]]);
  });
});
