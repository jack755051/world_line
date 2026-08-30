import type { Feature, FeatureCollection, MultiPolygon } from 'geojson';
import { buildMorphPlan, easeInOutCubic, sampleMorphPlan } from './territory-morph';
import type { TerritoryFeatureProperties } from './territory-styling';

type TerritoryFeature = Feature<MultiPolygon, TerritoryFeatureProperties>;

// 跟其他 geometry 測試檔（territory-overlap.spec.ts 等）同一種寫法：矩形當簡化疆域幾何。
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

function feature(id: string, regimeId: string, geom: MultiPolygon): TerritoryFeature {
  return {
    type: 'Feature',
    properties: { id, regimeId, startYear: 200, endYear: 210, isDisputed: false },
    geometry: geom,
  };
}

function fc(features: TerritoryFeature[]): FeatureCollection<MultiPolygon, TerritoryFeatureProperties> {
  return { type: 'FeatureCollection', features };
}

describe('buildMorphPlan', () => {
  it('同一個政權在兩個年份都只有一筆疆域列，配成一組 matched pair', () => {
    const from = fc([feature('wei-a', 'wei', rect(100, 30, 110, 40))]);
    const to = fc([feature('wei-b', 'wei', rect(102, 30, 112, 40))]);

    const plan = buildMorphPlan(from, to);

    expect(plan.matched).toHaveLength(1);
    expect(plan.entering).toHaveLength(0);
    expect(plan.leaving).toHaveLength(0);
  });

  it('政權只在新年份出現（例如剛建國），歸類到 entering，不強行配對', () => {
    const from = fc([feature('wei-a', 'wei', rect(100, 30, 110, 40))]);
    const to = fc([feature('wei-b', 'wei', rect(102, 30, 112, 40)), feature('jin-a', 'jin', rect(100, 30, 108, 38))]);

    const plan = buildMorphPlan(from, to);

    expect(plan.matched).toHaveLength(1);
    expect(plan.entering).toHaveLength(1);
    expect(plan.entering[0].properties.regimeId).toBe('jin');
    expect(plan.leaving).toHaveLength(0);
  });

  it('政權只在舊年份出現（例如被滅亡），歸類到 leaving，不強行配對', () => {
    const from = fc([feature('wei-a', 'wei', rect(100, 30, 110, 40)), feature('shu-a', 'shu-han', rect(100, 26, 108, 32))]);
    const to = fc([feature('wei-b', 'wei', rect(100, 26, 112, 40))]); // 蜀漢已滅亡（魏疆域擴張吃下原本蜀漢的範圍）

    const plan = buildMorphPlan(from, to);

    expect(plan.matched).toHaveLength(1);
    expect(plan.entering).toHaveLength(0);
    expect(plan.leaving).toHaveLength(1);
    expect(plan.leaving[0].properties.regimeId).toBe('shu-han');
  });

  it('同一個政權底下疆域列數量從 1 筆變 2 筆（例如進入爭議期間新增爭議地帶），多出來的那筆歸類到 entering', () => {
    const from = fc([feature('shu-core-a', 'shu-han', rect(100, 26, 111, 32))]);
    const to = fc([
      feature('shu-core-b', 'shu-han', rect(100, 26, 111, 32)),
      feature('shu-dispute-b', 'shu-han', rect(111, 26, 116, 32)),
    ]);

    const plan = buildMorphPlan(from, to);

    expect(plan.matched).toHaveLength(1);
    expect(plan.entering).toHaveLength(1);
    expect(plan.entering[0].properties.id).toBe('shu-dispute-b');
    expect(plan.leaving).toHaveLength(0);
  });

  it('同一個政權在兩個年份都有 2 筆疆域列，依形心座標決定性配對——輸入陣列順序不影響配對結果', () => {
    const westFrom = feature('west-a', 'shu-han', rect(100, 26, 108, 32));
    const eastFrom = feature('east-a', 'shu-han', rect(108, 26, 116, 32));
    const westTo = feature('west-b', 'shu-han', rect(101, 26, 109, 32));
    const eastTo = feature('east-b', 'shu-han', rect(109, 26, 117, 32));

    // 刻意把「to」陣列的順序反過來，驗證配對是依形心座標排序決定的，不是依陣列原始順序。
    const planNormalOrder = buildMorphPlan(fc([westFrom, eastFrom]), fc([westTo, eastTo]));
    const planReversedOrder = buildMorphPlan(fc([westFrom, eastFrom]), fc([eastTo, westTo]));

    expect(planNormalOrder.matched).toHaveLength(2);
    expect(planReversedOrder.matched).toHaveLength(2);
    const idsOf = (plan: typeof planNormalOrder) => plan.matched.map((m) => m.to.properties.id).sort();
    expect(idsOf(planNormalOrder)).toEqual(idsOf(planReversedOrder));
  });
});

describe('sampleMorphPlan', () => {
  it('matched pair 在 t=0.5 時，插值後的環是合法閉環（首尾座標相同）', () => {
    const from = fc([feature('wei-a', 'wei', rect(100, 30, 110, 40))]);
    const to = fc([feature('wei-b', 'wei', rect(102, 30, 112, 40))]);
    const plan = buildMorphPlan(from, to);

    const sampled = sampleMorphPlan(plan, 0.5);

    expect(sampled.features).toHaveLength(1);
    const ring = sampled.features[0].geometry.coordinates[0][0];
    expect(ring[0]).toEqual(ring[ring.length - 1]);
    expect(sampled.features[0].properties.morphOpacity).toBe(1);
  });

  it('matched pair 沒有 morphRole（不是 entering/leaving，避免跟真正的 entering/leaving feature 混淆）', () => {
    const from = fc([feature('wei-a', 'wei', rect(100, 30, 110, 40))]);
    const to = fc([feature('wei-b', 'wei', rect(102, 30, 112, 40))]);
    const plan = buildMorphPlan(from, to);

    const sampled = sampleMorphPlan(plan, 0.5);

    expect(sampled.features[0].properties.morphRole).toBeUndefined();
  });

  it('矩形只有一條邊移動、其餘角不動時，插值結果是逐點線性插值，不是 flubber 的形狀比對——不動的角在 t=0.5 時仍然完全不動（2026-08-30，使用者實機回報形變看起來像旋轉/不對稱拉伸）', () => {
    // 東邊界從經度 111 縮到 108，其餘三個角（西/南/北邊界）完全不動——這正是種子資料
    // 蜀漢 219 年失荊州那種「單邊內縮」的真實案例形狀。
    const from = fc([feature('shu-a', 'shu-han', rect(100, 26, 111, 32))]);
    const to = fc([feature('shu-b', 'shu-han', rect(100, 26, 108, 32))]);
    const plan = buildMorphPlan(from, to);

    const sampled = sampleMorphPlan(plan, 0.5);
    const ring = sampled.features[0].geometry.coordinates[0][0];

    // 兩個西邊角（經度 100）跟兩個緯度邊界（26、32）在 from/to 兩邊完全相同，t=0.5
    // 時每個點都該精確落在 from/to 對應點的中點——不該有任何點跑到矩形範圍以外
    // （旋轉/歪斜的插值演算法可能讓某些點暫時偏移到 [100,108]x[26,32] 這個外接框以外）。
    for (const [lon, lat] of ring) {
      expect(lon).toBeGreaterThanOrEqual(100);
      expect(lon).toBeLessThanOrEqual(111);
      expect(lat).toBeGreaterThanOrEqual(26);
      expect(lat).toBeLessThanOrEqual(32);
    }
    // 東邊界應該精確插值到 (111+108)/2 = 109.5，不是 flubber 重新取樣後的近似值。
    const eastLongitudes = ring.filter(([, lat]) => lat > 26 && lat < 32).map(([lon]) => lon);
    for (const lon of eastLongitudes) {
      expect(lon).toBeCloseTo(109.5, 5);
    }
  });

  it('entering feature 的形狀維持目標年份原樣，只有 morphOpacity 隨 t 淡入，morphRole 標成 entering', () => {
    const from = fc([]);
    const to = fc([feature('jin-a', 'jin', rect(100, 30, 108, 38))]);
    const plan = buildMorphPlan(from, to);

    const sampled = sampleMorphPlan(plan, 0.3);

    expect(sampled.features).toHaveLength(1);
    expect(sampled.features[0].geometry).toEqual(to.features[0].geometry);
    expect(sampled.features[0].properties.morphOpacity).toBeCloseTo(0.3);
    expect(sampled.features[0].properties.morphRole).toBe('entering');
  });

  it('頂點數不同時（例如之後真的匯入形狀被重新繪製過的史料），退回用 flubber 的形狀比對插值，一樣輸出合法閉環', () => {
    const triangle: MultiPolygon = {
      type: 'MultiPolygon',
      coordinates: [[[[100, 26], [105, 32], [100, 32], [100, 26]]]], // 3 個相異頂點
    };
    const from = fc([feature('shu-a', 'shu-han', triangle)]);
    const to = fc([feature('shu-b', 'shu-han', rect(100, 26, 108, 32))]); // 4 個相異頂點
    const plan = buildMorphPlan(from, to);

    const sampled = sampleMorphPlan(plan, 0.5);
    const ring = sampled.features[0].geometry.coordinates[0][0];

    expect(ring.length).toBeGreaterThan(0);
    expect(ring[0]).toEqual(ring[ring.length - 1]); // 仍然是合法閉環
  });

  it('leaving feature 的形狀維持起始年份原樣，只有 morphOpacity 隨 t 淡出，morphRole 標成 leaving', () => {
    const from = fc([feature('shu-a', 'shu-han', rect(100, 26, 108, 32))]);
    const to = fc([]);
    const plan = buildMorphPlan(from, to);

    const sampled = sampleMorphPlan(plan, 0.3);

    expect(sampled.features).toHaveLength(1);
    expect(sampled.features[0].geometry).toEqual(from.features[0].geometry);
    expect(sampled.features[0].properties.morphOpacity).toBeCloseTo(0.7);
    expect(sampled.features[0].properties.morphRole).toBe('leaving');
  });
});

describe('easeInOutCubic', () => {
  it('端點固定在 0 跟 1（動畫起訖點跟輸入進度一致，不會跳掉）', () => {
    expect(easeInOutCubic(0)).toBe(0);
    expect(easeInOutCubic(1)).toBe(1);
  });

  it('中點是 0.5（對稱曲線，加速段跟減速段時間相等）', () => {
    expect(easeInOutCubic(0.5)).toBeCloseTo(0.5);
  });

  it('全程單調遞增（不會中途倒退，疆域形變不該有「先變過頭再變回來」的視覺跳動）', () => {
    const samples = Array.from({ length: 11 }, (_, i) => easeInOutCubic(i / 10));
    for (let i = 1; i < samples.length; i++) {
      expect(samples[i]).toBeGreaterThanOrEqual(samples[i - 1]);
    }
  });
});
