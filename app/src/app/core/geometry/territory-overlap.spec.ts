import type { MultiPolygon } from 'geojson';
import { computeTerritoryOverlaps, type TerritoryWithRegime } from './territory-overlap';

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
  it('兩個不同政權有實際面積重疊，回傳交集多邊形', () => {
    const territories: TerritoryWithRegime[] = [
      { id: 'shuHan', regimeId: 'shu-han', geometry: rect(100, 26, 114, 32) },
      { id: 'wu', regimeId: 'wu', geometry: rect(112, 22, 116, 32) }, // 跟 shuHan 在經度 112-114 重疊
    ];

    const overlaps = computeTerritoryOverlaps(territories);

    expect(overlaps).toHaveLength(1);
  });

  it('同一個政權自己底下兩筆疆域記錄互相重疊，不算「政權重疊」，不畫斜線（2026-08-29 拍板：規則只看不同政權之間，同政權一律用顏色表示）', () => {
    const territories: TerritoryWithRegime[] = [
      { id: 'shuHan-v1', regimeId: 'shu-han', geometry: rect(100, 26, 114, 32) },
      { id: 'shuHan-v2', regimeId: 'shu-han', geometry: rect(100, 26, 111, 32) }, // 跟 v1 同政權、幾何重疊
    ];

    const overlaps = computeTerritoryOverlaps(territories);

    expect(overlaps).toHaveLength(0);
  });

  it('只共邊接觸（沒有實際面積重疊）的不同政權疆域，不算重疊', () => {
    const territories: TerritoryWithRegime[] = [
      { id: 'a', regimeId: 'regime-a', geometry: rect(100, 20, 110, 30) },
      { id: 'b', regimeId: 'regime-b', geometry: rect(110, 20, 120, 30) }, // 只在 x=110 這條邊接觸
    ];

    const overlaps = computeTerritoryOverlaps(territories);

    expect(overlaps).toHaveLength(0);
  });

  it('完全不接觸、不重疊的不同政權疆域，不算重疊', () => {
    const territories: TerritoryWithRegime[] = [
      { id: 'a', regimeId: 'regime-a', geometry: rect(100, 20, 110, 30) },
      { id: 'far', regimeId: 'regime-c', geometry: rect(200, 20, 210, 30) },
    ];

    const overlaps = computeTerritoryOverlaps(territories);

    expect(overlaps).toHaveLength(0);
  });

  it('三個不同政權兩兩都重疊時，回傳三組交集（不是只算一次，也不會被同政權排除規則誤刪）', () => {
    const territories: TerritoryWithRegime[] = [
      { id: 'a', regimeId: 'regime-a', geometry: rect(100, 20, 110, 30) },
      { id: 'b', regimeId: 'regime-b', geometry: rect(105, 20, 115, 30) }, // 跟 a 重疊
      { id: 'c', regimeId: 'regime-c', geometry: rect(108, 20, 118, 30) }, // 跟 a、b 都重疊
    ];

    const overlaps = computeTerritoryOverlaps(territories);

    expect(overlaps).toHaveLength(3); // a-b、a-c、b-c
  });

  it('同政權自己重疊 + 跟別的政權重疊同時發生時，只有跟別的政權那組算數', () => {
    const territories: TerritoryWithRegime[] = [
      { id: 'shuHan-v1', regimeId: 'shu-han', geometry: rect(100, 26, 114, 32) },
      { id: 'shuHan-v2', regimeId: 'shu-han', geometry: rect(100, 26, 111, 32) }, // 跟 v1 同政權，重疊但不算
      { id: 'wu', regimeId: 'wu', geometry: rect(112, 22, 116, 32) }, // 跟 shuHan-v1 重疊，不同政權，算
    ];

    const overlaps = computeTerritoryOverlaps(territories);

    expect(overlaps).toHaveLength(1); // 只有 shuHan-v1 跟 wu 那組
  });

  it('沒有帶 morphOpacity 時，重疊區透明度預設為 1（非動畫的一般情況維持原本行為）', () => {
    const territories: TerritoryWithRegime[] = [
      { id: 'shuHan', regimeId: 'shu-han', geometry: rect(100, 26, 114, 32) },
      { id: 'wu', regimeId: 'wu', geometry: rect(112, 22, 116, 32) },
    ];

    const overlaps = computeTerritoryOverlaps(territories);

    expect(overlaps[0].opacity).toBe(1);
  });

  it('重疊區透明度取兩個來源政權疆域列 morphOpacity 的較小值（任務 3.6：一邊還在淡入時，重疊斜線也該跟著淡）', () => {
    const territories: TerritoryWithRegime[] = [
      { id: 'shuHan', regimeId: 'shu-han', geometry: rect(100, 26, 114, 32), morphOpacity: 1 },
      { id: 'wu', regimeId: 'wu', geometry: rect(112, 22, 116, 32), morphOpacity: 0.3 }, // 東吳這筆還在淡入
    ];

    const overlaps = computeTerritoryOverlaps(territories);

    expect(overlaps[0].opacity).toBeCloseTo(0.3);
  });
});
