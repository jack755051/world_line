import type { FeatureCollection, MultiPolygon } from 'geojson';
import {
  assignTerritoryColorSlots,
  buildColorSlotMatchExpression,
  type TerritoryFeatureProperties,
} from './territory-styling';

// 跟 territory-adjacency.spec.ts 同一種寫法：矩形當測試用的簡化疆域幾何。
function rect(minLon: number, minLat: number, maxLon: number, maxLat: number): MultiPolygon {
  return {
    type: 'MultiPolygon',
    coordinates: [
      [
        [
          [minLon, minLat],
          [minLon, maxLat],
          [maxLon, maxLat],
          [maxLon, minLat],
          [minLon, minLat],
        ],
      ],
    ],
  };
}

function feature(id: string, regimeId: string, geometry: MultiPolygon) {
  return {
    type: 'Feature' as const,
    geometry,
    properties: { id, regimeId, startYear: 220, endYear: 226, isDisputed: false } as TerritoryFeatureProperties,
  };
}

describe('assignTerritoryColorSlots', () => {
  it('把色格索引寫回每個 feature.properties.colorSlot，相鄰的兩個政權拿到不同色格', () => {
    const fc: FeatureCollection<MultiPolygon, TerritoryFeatureProperties> = {
      type: 'FeatureCollection',
      features: [
        feature('a', 'regime-a', rect(100, 20, 110, 30)),
        feature('b', 'regime-b', rect(110, 20, 120, 30)), // 跟 a 共邊，相鄰
      ],
    };

    assignTerritoryColorSlots(fc, 5);

    const [a, b] = fc.features;
    expect(a.properties.colorSlot).toBeDefined();
    expect(b.properties.colorSlot).toBeDefined();
    expect(a.properties.colorSlot).not.toBe(b.properties.colorSlot);
  });

  it('不相鄰的兩個政權可以共用同一個色格', () => {
    const fc: FeatureCollection<MultiPolygon, TerritoryFeatureProperties> = {
      type: 'FeatureCollection',
      features: [
        feature('a', 'regime-a', rect(100, 20, 110, 30)),
        feature('far', 'regime-c', rect(200, 20, 210, 30)), // 遠在另一邊，不相鄰
      ],
    };

    assignTerritoryColorSlots(fc, 5);

    const [a, far] = fc.features;
    expect(a.properties.colorSlot).toBe(far.properties.colorSlot);
  });

  it('同一個政權底下多筆互相重疊的疆域記錄，永遠拿到同一個色格（2026-08-29 修正的 bug：不能因為同政權兩筆版本剛好幾何重疊，就被當成兩個要分開上色的節點）', () => {
    const fc: FeatureCollection<MultiPolygon, TerritoryFeatureProperties> = {
      type: 'FeatureCollection',
      features: [
        feature('shuHan-v1', 'shu-han', rect(100, 26, 114, 32)),
        feature('shuHan-v2', 'shu-han', rect(100, 26, 111, 32)), // 跟 v1 同政權、幾何重疊
        feature('wu', 'wu', rect(112, 22, 122, 32)), // 跟 shuHan-v1 重疊，是不同政權，該有不同色格
      ],
    };

    assignTerritoryColorSlots(fc, 5);

    const [v1, v2, wu] = fc.features;
    expect(v1.properties.colorSlot).toBe(v2.properties.colorSlot); // 同政權，同色格
    expect(v1.properties.colorSlot).not.toBe(wu.properties.colorSlot); // 不同政權且重疊，不同色格
  });

  it('同一個政權底下兩筆疆域只是彼此相鄰（共邊，不是同政權外的政權），不影響色格指派——政權層級的圖只看跟其他政權的關係', () => {
    const fc: FeatureCollection<MultiPolygon, TerritoryFeatureProperties> = {
      type: 'FeatureCollection',
      features: [
        feature('wu-core', 'wu', rect(116, 22, 122, 32)),
        feature('wu-strip', 'wu', rect(112, 22, 116, 32)), // 跟 wu-core 共邊，同政權
        feature('shuHan', 'shu-han', rect(100, 22, 112, 32)), // 跟 wu-strip 共邊，不同政權，該有不同色格
      ],
    };

    assignTerritoryColorSlots(fc, 5);

    const [wuCore, wuStrip, shuHan] = fc.features;
    expect(wuCore.properties.colorSlot).toBe(wuStrip.properties.colorSlot);
    expect(wuStrip.properties.colorSlot).not.toBe(shuHan.properties.colorSlot);
  });

  it('回傳的 assignment map 用 regimeId 當 key（不是疆域記錄自己的 id），可以直接當下次呼叫的 previousAssignment', () => {
    const fc: FeatureCollection<MultiPolygon, TerritoryFeatureProperties> = {
      type: 'FeatureCollection',
      features: [feature('a', 'regime-a', rect(100, 20, 110, 30))],
    };

    const assignment = assignTerritoryColorSlots(fc, 5);

    expect(assignment.get('regime-a')).toBe(fc.features[0].properties.colorSlot);
  });
});

describe('buildColorSlotMatchExpression', () => {
  it('組出 match expression，每個色格索引對應到對應位置的色碼', () => {
    const expr = buildColorSlotMatchExpression(['#111', '#222', '#333']);

    expect(expr).toEqual(['match', ['get', 'colorSlot'], 0, '#111', 1, '#222', 2, '#333', '#111']);
  });
});
