import type { Feature, FeatureCollection, MultiPolygon } from 'geojson';
import { findNeighboringRegimeIds, findOtherContemporaryRegimeIds } from './regime-focus';
import type { TerritoryFeatureProperties } from './territory-styling';

type TerritoryFeature = Feature<MultiPolygon, TerritoryFeatureProperties>;

// 跟其他 geometry 測試檔同一種寫法：矩形當簡化疆域幾何。
function rect(minLon: number, minLat: number, maxLon: number, maxLat: number): MultiPolygon {
  return {
    type: 'MultiPolygon',
    coordinates: [[[[minLon, minLat], [minLon, maxLat], [maxLon, maxLat], [maxLon, minLat], [minLon, minLat]]]],
  };
}

function feature(id: string, regimeId: string, geom: MultiPolygon): TerritoryFeature {
  return {
    type: 'Feature',
    properties: { id, regimeId, startYear: 200, endYear: 300, isDisputed: false },
    geometry: geom,
  };
}

function fc(features: TerritoryFeature[]): FeatureCollection<MultiPolygon, TerritoryFeatureProperties> {
  return { type: 'FeatureCollection', features };
}

describe('findNeighboringRegimeIds', () => {
  it('回傳跟聚焦政權有實際拓撲相交的其他政權 id', () => {
    const featureCollection = fc([
      feature('wei-a', 'wei', rect(104, 32, 123, 42)),
      feature('shu-a', 'shu-han', rect(100, 26, 108, 32)), // 跟魏在緯度 32 這條邊接觸，算相鄰
      feature('far-a', 'far-regime', rect(200, 32, 210, 42)), // 完全不接觸，不算相鄰
    ]);

    const neighbors = findNeighboringRegimeIds(featureCollection, 'wei');

    expect(neighbors).toEqual(new Set(['shu-han']));
  });

  it('同一個政權自己底下多筆疆域記錄不會被算成自己的鄰居', () => {
    const featureCollection = fc([
      feature('wei-north', 'wei', rect(104, 32, 123, 42)),
      feature('wei-south', 'wei', rect(100, 26, 108, 32)), // 同一個政權（魏），跟北方那筆接觸但不算「鄰居」
    ]);

    const neighbors = findNeighboringRegimeIds(featureCollection, 'wei');

    expect(neighbors.size).toBe(0);
  });

  it('聚焦政權在這批資料裡完全不存在時，回傳空集合而不是拋例外', () => {
    const featureCollection = fc([feature('wei-a', 'wei', rect(104, 32, 123, 42))]);

    const neighbors = findNeighboringRegimeIds(featureCollection, 'nonexistent-regime');

    expect(neighbors.size).toBe(0);
  });

  it('沒有任何政權跟聚焦政權相鄰時，回傳空集合', () => {
    const featureCollection = fc([
      feature('wei-a', 'wei', rect(104, 32, 123, 42)),
      feature('far-a', 'far-regime', rect(200, 32, 210, 42)),
    ]);

    const neighbors = findNeighboringRegimeIds(featureCollection, 'wei');

    expect(neighbors.size).toBe(0);
  });
});

describe('findOtherContemporaryRegimeIds', () => {
  it('回傳除了聚焦政權跟已知周邊政權以外，這批資料裡其餘的政權 id（例如唐朝聚焦時，不接壤的阿拉伯帝國）', () => {
    const featureCollection = fc([
      feature('tang-a', 'tang', rect(100, 26, 120, 42)),
      feature('arab-a', 'arab-empire', rect(-10, 20, 40, 40)), // 完全不接壤，但同時期存在
    ]);

    const others = findOtherContemporaryRegimeIds(featureCollection, 'tang', new Set());

    expect(others).toEqual(new Set(['arab-empire']));
  });

  it('已經被算成周邊政權的，不會重複出現在「其他地區政權」清單', () => {
    const featureCollection = fc([
      feature('wei-a', 'wei', rect(104, 32, 123, 42)),
      feature('shu-a', 'shu-han', rect(100, 26, 108, 32)), // 跟魏相鄰
      feature('arab-a', 'arab-empire', rect(-10, 20, 40, 40)), // 不相鄰
    ]);

    const others = findOtherContemporaryRegimeIds(featureCollection, 'wei', new Set(['shu-han']));

    expect(others).toEqual(new Set(['arab-empire'])); // 蜀漢已經在周邊清單了，不重複列
  });

  it('目前種子資料規模下（政權彼此地理相鄰）大概率回傳空集合，這是預期行為，不是邏輯錯誤', () => {
    const featureCollection = fc([
      feature('wei-a', 'wei', rect(104, 32, 123, 42)),
      feature('shu-a', 'shu-han', rect(100, 26, 108, 32)),
      feature('wu-a', 'wu', rect(108, 20, 122, 32)),
    ]);
    const neighbors = findNeighboringRegimeIds(featureCollection, 'wei');

    const others = findOtherContemporaryRegimeIds(featureCollection, 'wei', neighbors);

    expect(others.size).toBe(0);
  });
});
