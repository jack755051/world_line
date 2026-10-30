import type { ControlMapDto } from '../../core/api/api-types';
import { CAMP_TONES, CAMP_UNASSIGNED_TONE, darken, decorateFeatures, evidenceFor, hatchImageId } from './map-style';

// 測試用假資料（只存在於測試檔，不進畫面、不寫入資料庫）
function fixture(state: string, controlType = 'military_occupation'): ControlMapDto {
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

  it('darken', () => {
    expect(darken('#ffffff', 0.25)).toBe('#bfbfbf');
  });
});
