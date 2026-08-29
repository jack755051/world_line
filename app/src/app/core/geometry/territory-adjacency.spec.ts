import type { MultiPolygon } from 'geojson';
import { computeAdjacency, type Territory } from './territory-adjacency';

// 跟 api/Data/SeedData.cs 的 Rect() 同一種寫法：矩形當測試用的簡化疆域幾何，不是正式史料。
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

describe('computeAdjacency', () => {
  it('回報共邊接觸的兩塊疆域為相鄰', () => {
    const territories: Territory[] = [
      { id: 'a', geometry: rect(100, 20, 110, 30) },
      { id: 'b', geometry: rect(110, 20, 120, 30) }, // 跟 a 在 x=110 這條邊接觸
    ];

    const adjacency = computeAdjacency(territories);

    expect(adjacency.get('a')).toEqual(new Set(['b']));
    expect(adjacency.get('b')).toEqual(new Set(['a']));
  });

  it('回報範圍重疊的兩塊疆域為相鄰（例如 I3 爭議並存的兩個版本）', () => {
    const territories: Territory[] = [
      { id: 'shuHan-v1', geometry: rect(100, 26, 114, 32) },
      { id: 'shuHan-v2', geometry: rect(100, 26, 111, 32) }, // 跟 v1 重疊
    ];

    const adjacency = computeAdjacency(territories);

    expect(adjacency.get('shuHan-v1')?.has('shuHan-v2')).toBe(true);
  });

  it('完全不接觸、不重疊的疆域不算相鄰', () => {
    const territories: Territory[] = [
      { id: 'a', geometry: rect(100, 20, 110, 30) },
      { id: 'far', geometry: rect(200, 20, 210, 30) }, // 遠在另一邊，bbox 都不重疊
    ];

    const adjacency = computeAdjacency(territories);

    expect(adjacency.get('a')?.size).toBe(0);
    expect(adjacency.get('far')?.size).toBe(0);
  });

  it('三塊疆域一字排開，中間那塊同時跟左右兩塊相鄰（各共用一整條邊），兩端彼此隔著空隙不相鄰', () => {
    const territories: Territory[] = [
      { id: 'shuHan', geometry: rect(90, 20, 105, 30) },
      { id: 'wei', geometry: rect(105, 20, 120, 30) }, // 跟 shuHan 共用 x=105 整條邊
      { id: 'wu', geometry: rect(120, 20, 135, 30) }, // 跟 wei 共用 x=120 整條邊，跟 shuHan 中間隔著 wei
    ];

    const adjacency = computeAdjacency(territories);

    expect(adjacency.get('wei')?.has('shuHan')).toBe(true);
    expect(adjacency.get('wei')?.has('wu')).toBe(true);
    expect(adjacency.get('shuHan')?.has('wu')).toBe(false);
  });
});
