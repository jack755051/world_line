import type { ControlMapDto } from '../../core/api/api-types';
import { CAMP_FILL, CAMP_TONES, CAMP_UNASSIGNED_TONE, campOf, campTonesFrom, controlLabels, darken, decorateFeatures, evidenceFor, gapFeatures, hatchImageId, labelPoint } from './map-style';

// 測試用假資料（只存在於測試檔，不進畫面、不寫入資料庫）
function fixture(state: string, controlType = 'military_occupation', camp: string | null = null): ControlMapDto {
  return {
    date: '1940-07-15',
    theaters: [{ theaterCode: 'test-theater', state, attestingSnapshot: null, prevSnapshot: null, nextSnapshot: null }],
    featureCollection: {
      type: 'FeatureCollection',
      features: [
        {
          id: 'v1',
          type: 'Feature',
          geometry: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]] },
          properties: {
            controlRecordId: 'r1', versionId: 'v1', controllerRegimeId: 'g1', controlType, patronRegimeId: null,
            theaterCode: 'test-theater', snapshotId: 's1', isDisputed: false,
            validPeriod: { start: '1940-07-01', end: '1940-08-01', startUncertainty: null, endUncertainty: null },
            citations: [],
            controllerAlignment: camp
              ? { id: 'a1', regimeId: 'g1', camp, validPeriod: { start: '1940-01-01', end: null }, basisEventId: null, note: null, citations: [] }
              : null,
          },
        },
      ],
    },
  } as unknown as ControlMapDto;
}

describe('map-style', () => {
  it('evidenceFor：查不到戰區狀態 → unknown', () => {
    expect(evidenceFor('x', [])).toBe('unknown');
    expect(evidenceFor('x', null)).toBe('unknown');
  });

  it('軍事佔領（史料）：0.6 不透明＋同色加深 25% 的 2px 實線（DESIGN.md）', () => {
    const p = decorateFeatures(fixture('attested')).features[0].properties;
    expect(p.evidence).toBe('attested');
    expect(p.wlFill).toBe(CAMP_UNASSIGNED_TONE);
    expect(p.wlFillOpacity).toBe(0.6);
    expect(p.wlLine).toBe(darken(CAMP_UNASSIGNED_TONE, 0.25));
    expect(p.wlLineWidth).toBe(2);
    expect(p.wlLineKind).toBe('solid');
  });

  it('推估過渡：不透明度 ×0.55、虛線', () => {
    const p = decorateFeatures(fixture('interpolated')).features[0].properties;
    expect(p.wlFillOpacity).toBe(0.33);
    expect(p.wlLineKind).toBe('dashed');
  });

  it('狀態不明也以推估樣式呈現（保守原則，PRD §8.5）', () => {
    const p = decorateFeatures(fixture('weird')).features[0].properties;
    expect(p.evidence).toBe('unknown');
    expect(p.wlLineKind).toBe('dashed');
  });

  it('不完全控制用斜線圖樣、不用實心填色', () => {
    const p = decorateFeatures(fixture('attested', 'partial')).features[0].properties;
    expect(p.wlPattern).toBe(hatchImageId(CAMP_UNASSIGNED_TONE, 'partial'));
  });

  it('陣營未建置色不在四色系內，也不接近朱紅／error', () => {
    const all: readonly string[] = Object.values(CAMP_TONES).flat();
    expect(all).not.toContain(CAMP_UNASSIGNED_TONE);
    expect(CAMP_UNASSIGNED_TONE).not.toBe('#b23a26');
  });

  it('沒有陣營切片（controllerAlignment = null）→ 陣營未建置色，camp = unassigned（不推定）', () => {
    const dto = fixture('attested');
    const tones = campTonesFrom(dto);
    expect(tones.toneFor('g1')).toBe(CAMP_UNASSIGNED_TONE);
    expect(tones.campFor('g1')).toBeNull();
    expect(decorateFeatures(dto, tones.toneFor).features[0].properties.camp).toBe('unassigned');
  });

  it('有陣營切片 → 用該色系的色票，API 的 co_belligerent 對到 cobelligerent', () => {
    const axis = fixture('attested', 'military_occupation', 'axis');
    const tones = campTonesFrom(axis);
    expect(tones.toneFor('g1')).toBe(CAMP_TONES.axis[0]);
    expect(tones.campFor('g1')).toBe('axis');
    const p = decorateFeatures(axis, tones.toneFor).features[0].properties;
    expect(p.wlFill).toBe(CAMP_TONES.axis[0]);
    expect(p.camp).toBe('axis');
    expect(campOf({ camp: 'co_belligerent' })).toBe('cobelligerent');
    expect(campOf({ camp: 'something-else' })).toBeNull();
    expect(campTonesFrom(null).toneFor('nobody')).toBe(CAMP_UNASSIGNED_TONE);
  });

  it('darken', () => {
    expect(darken('#ffffff', 0.25)).toBe('#bfbfbf');
  });

  it('填色＝陣營：同陣營的不同政權用同一個填色（政權靠邊框與標籤區分）', () => {
    const a = fixture('attested', 'military_occupation', 'axis');
    const f0 = a.featureCollection.features[0];
    const f1 = { ...f0, properties: { ...f0.properties, versionId: 'v2', controllerRegimeId: 'g2', controllerAlignment: { ...f0.properties.controllerAlignment!, regimeId: 'g2' } } };
    a.featureCollection.features.push(f1 as typeof f0);
    const tones = campTonesFrom(a);
    expect(tones.toneFor('g1')).toBe(CAMP_FILL.axis);
    expect(tones.toneFor('g2')).toBe(CAMP_FILL.axis);
  });

  it('labelPoint：凹多邊形的標籤點落在多邊形內', () => {
    // L 形：重心 (≈1.17, ≈1.17) 在缺角外側附近，標籤點必須在 L 內
    const L = [[[0, 0], [3, 0], [3, 1], [1, 1], [1, 3], [0, 3], [0, 0]]];
    const [x, y] = labelPoint(L);
    const inL = (x >= 0 && x <= 3 && y >= 0 && y <= 1) || (x >= 0 && x <= 1 && y >= 0 && y <= 3);
    expect(inL).toBe(true);
  });

  it('labelPoint：很長的環（如蘇聯、美國）先等間隔取點，仍落在多邊形內且不拖慢', () => {
    const n = 40000;
    const ring = Array.from({ length: n + 1 }, (_, i) => [10 * Math.cos((2 * Math.PI * i) / n), 5 * Math.sin((2 * Math.PI * i) / n)]);
    const t0 = performance.now();
    const [x, y] = labelPoint([ring]);
    expect(performance.now() - t0).toBeLessThan(500);
    expect((x / 10) ** 2 + (y / 5) ** 2).toBeLessThan(0.2);
  });

  it('controlLabels：文字只來自政權名稱；查不到名稱就不標', () => {
    const dto = fixture('attested');
    expect(controlLabels(dto, () => null)).toEqual([]);
    const labels = controlLabels(dto, (id) => (id === 'g1' ? '測試政權' : null));
    expect(labels).toHaveLength(1);
    expect(labels[0].text).toBe('測試政權');
    expect(labels[0].bbox).toEqual([0, 0, 1, 1]);
  });

  it('控制資料缺：只畫 API 的 coverageNotes，沒有就是空集合（R9，前端不推導）', () => {
    expect(gapFeatures(fixture('attested')).features).toEqual([]);
    expect(gapFeatures(null).features).toEqual([]);
    const dto: ControlMapDto = {
      ...fixture('attested'),
      coverageNotes: [
        {
          id: 'n1', theaterId: null, reason: 'no_qualified_source', note: null, researchRef: null,
          geometry: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]] },
          validPeriod: { start: '1940-07-15', end: '1942-11-11' },
        },
      ],
    };
    const g = gapFeatures(dto).features;
    expect(g.length).toBe(1);
    expect(g[0].properties).toEqual({ gapId: 'n1', reason: 'no_qualified_source' });
    expect(g[0].geometry.type).toBe('Polygon');
  });
});
