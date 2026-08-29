import type { MultiPolygon } from 'geojson';
import { computeTerritoryOverlaps } from './territory-overlap';
import type { Territory } from './territory-adjacency';

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

describe('computeTerritoryOverlaps', () => {
  it('兩塊有實際面積重疊的疆域，回傳交集多邊形', () => {
    const territories: Territory[] = [
      { id: 'shuHan', geometry: rect(100, 26, 114, 32) },
      { id: 'wu', geometry: rect(112, 22, 116, 32) }, // 跟 shuHan 在經度 112-114 重疊
    ];

    const overlaps = computeTerritoryOverlaps(territories);

    expect(overlaps).toHaveLength(1);
  });

  it('只共邊接觸（沒有實際面積重疊）的疆域，不算重疊', () => {
    const territories: Territory[] = [
      { id: 'a', geometry: rect(100, 20, 110, 30) },
      { id: 'b', geometry: rect(110, 20, 120, 30) }, // 只在 x=110 這條邊接觸
    ];

    const overlaps = computeTerritoryOverlaps(territories);

    expect(overlaps).toHaveLength(0);
  });

  it('完全不接觸、不重疊的疆域，不算重疊', () => {
    const territories: Territory[] = [
      { id: 'a', geometry: rect(100, 20, 110, 30) },
      { id: 'far', geometry: rect(200, 20, 210, 30) },
    ];

    const overlaps = computeTerritoryOverlaps(territories);

    expect(overlaps).toHaveLength(0);
  });

  it('同一個政權自己兩筆爭議版本互相重疊，也算重疊（I3 史觀分歧跟不同政權的邊界爭奪，語意上是同一件事）', () => {
    const territories: Territory[] = [
      { id: 'shuHan-v1', geometry: rect(100, 26, 114, 32) },
      { id: 'shuHan-v2', geometry: rect(100, 26, 111, 32) },
    ];

    const overlaps = computeTerritoryOverlaps(territories);

    expect(overlaps).toHaveLength(1);
  });

  it('三塊兩兩都重疊時，回傳三組交集（不是只算一次）', () => {
    const territories: Territory[] = [
      { id: 'a', geometry: rect(100, 20, 110, 30) },
      { id: 'b', geometry: rect(105, 20, 115, 30) }, // 跟 a 重疊
      { id: 'c', geometry: rect(108, 20, 118, 30) }, // 跟 a、b 都重疊
    ];

    const overlaps = computeTerritoryOverlaps(territories);

    expect(overlaps).toHaveLength(3); // a-b、a-c、b-c
  });
});
