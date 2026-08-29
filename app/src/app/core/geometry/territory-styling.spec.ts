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
  it('把色格索引寫回每個 feature.properties.colorSlot，相鄰的兩塊拿到不同色格', () => {
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

  it('不相鄰的兩塊可以共用同一個色格', () => {
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

  it('回傳的 assignment map 跟寫回 properties 的結果一致，可以直接當下次呼叫的 previousAssignment', () => {
    const fc: FeatureCollection<MultiPolygon, TerritoryFeatureProperties> = {
      type: 'FeatureCollection',
      features: [feature('a', 'regime-a', rect(100, 20, 110, 30))],
    };

    const assignment = assignTerritoryColorSlots(fc, 5);

    expect(assignment.get('a')).toBe(fc.features[0].properties.colorSlot);
  });
});

describe('buildColorSlotMatchExpression', () => {
  it('組出 match expression，每個色格索引對應到對應位置的色碼', () => {
    const expr = buildColorSlotMatchExpression(['#111', '#222', '#333']);

    expect(expr).toEqual(['match', ['get', 'colorSlot'], 0, '#111', 1, '#222', 2, '#333', '#111']);
  });
});
