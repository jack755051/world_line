import type { FeatureCollection, MultiPolygon } from 'geojson';
import { computeTerritoryLabelPoints } from './territory-labels';
import type { TerritoryFeatureProperties } from './territory-styling';

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

describe('computeTerritoryLabelPoints', () => {
  it('回傳矩形疆域的幾何中心點', () => {
    const fc: FeatureCollection<MultiPolygon, TerritoryFeatureProperties> = {
      type: 'FeatureCollection',
      features: [feature('a', 'regime-a', rect(100, 20, 110, 30))],
    };

    const points = computeTerritoryLabelPoints(fc);

    const [lon, lat] = points.get('regime-a')!;
    expect(lon).toBeCloseTo(105, 5);
    expect(lat).toBeCloseTo(25, 5);
  });

  it('同一個政權有多筆疆域快照（例如 I3 並存爭議版本）時，只取第一筆當標籤點', () => {
    const fc: FeatureCollection<MultiPolygon, TerritoryFeatureProperties> = {
      type: 'FeatureCollection',
      features: [
        feature('v1', 'shu-han', rect(100, 26, 114, 32)),
        feature('v2', 'shu-han', rect(100, 26, 111, 32)), // 並存的第二個爭議版本
      ],
    };

    const points = computeTerritoryLabelPoints(fc);

    expect(points.size).toBe(1);
    expect(points.has('shu-han')).toBe(true);
  });

  it('不同政權各自拿到自己的標籤點', () => {
    const fc: FeatureCollection<MultiPolygon, TerritoryFeatureProperties> = {
      type: 'FeatureCollection',
      features: [
        feature('a', 'regime-a', rect(100, 20, 110, 30)),
        feature('b', 'regime-b', rect(110, 20, 120, 30)),
      ],
    };

    const points = computeTerritoryLabelPoints(fc);

    expect(points.size).toBe(2);
    expect(points.get('regime-a')).not.toEqual(points.get('regime-b'));
  });
});
