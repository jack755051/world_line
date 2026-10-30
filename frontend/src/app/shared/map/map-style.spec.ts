import type { ControlMapDto } from '../../core/api/api-types';
import { CAMP_TONES, CAMP_UNASSIGNED_TONE, campOf, campTonesFrom, darken, decorateFeatures, evidenceFor, gapFeatures, hatchImageId } from './map-style';

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
