import type { SovereigntyMapDto } from '../../core/api/api-types';
import { CAMP_FILL, hatchImageId } from './map-style';
import { REGIME_COLORS, decorateSovereignty, regimeColor, sovereigntyLabels } from './sovereignty-style';

// 測試用假資料（只存在於測試檔，不進畫面、不寫入資料庫）
function feature(id: string, slug: string, opts: { status?: string; camp?: string; pending?: boolean } = {}) {
  return {
    id, type: 'Feature',
    geometry: { type: 'MultiPolygon', coordinates: [[[[0, 0], [4, 0], [4, 3], [0, 3], [0, 0]]], [[[10, 10], [10.5, 10], [10.5, 10.5], [10, 10]]]] },
    properties: {
      recordId: id, regimeId: `g-${slug}`, regimeSlug: slug, layerStatus: opts.status ?? 'de_jure',
      validPeriod: { start: '1938-03-13', end: '1938-11-21' },
      startEvent: { id: 'e1', eventKind: 'political', occurred: { start: '1938-03-13', end: '1938-03-14' }, summary: null, verification: 'verified', citations: [] },
      endEvent: opts.pending ? { id: 'e2', eventKind: 'treaty', occurred: { start: '1938-11-20', end: '1938-11-22' }, summary: null, verification: 'pending', citations: [] } : null,
      geometry: { sourceId: 's', sourceTitle: 'OHM', publisher: 'p', sourceLicenseCode: 'cc0', locator: 'relation/1 v1', geometryLicense: 'cc0', attribution: null,
        ohmRelationId: 1, ohmVersion: 1, ohmFetchedAt: null, ohmStartRaw: null, ohmEndRaw: null, flags: null },
      note: null,
      regimeAlignment: opts.camp ? { id: 'a', regimeId: `g-${slug}`, camp: opts.camp, validPeriod: { start: '1936-01-01', end: null }, basisEventId: null, note: null, citations: [] } : null,
    },
  };
}
const dto = (...f: ReturnType<typeof feature>[]) => ({ date: '1938-10-15', featureCollection: { type: 'FeatureCollection', features: f } }) as unknown as SovereigntyMapDto;

describe('sovereignty-style', () => {
  it('填色依政權：同政權同色、不同政權不同色；陣營不改填色', () => {
    const fc = decorateSovereignty(dto(feature('r1', 'deutsches-reich', { camp: 'axis' }), feature('r2', 'deutsches-reich'), feature('r3', 'kingdom-of-italy', { camp: 'axis' })));
    const [a, b, c] = fc.features.map((f) => f.properties);
    expect(a.wlFill).toBe(REGIME_COLORS['deutsches-reich']);
    expect(b.wlFill).toBe(a.wlFill);
    expect(c.wlFill).not.toBe(a.wlFill);
    expect(a.wlFill).not.toBe(CAMP_FILL.axis);
  });

  it('陣營只作補充：有切片才有外框色，沒有就是空字串（不推定）', () => {
    const [a, b] = decorateSovereignty(dto(feature('r1', 'deutsches-reich', { camp: 'axis' }), feature('r2', 'swiss-confederation'))).features.map((f) => f.properties);
    expect(a.camp).toBe('axis');
    expect(a.wlCampLine).toBe(CAMP_FILL.axis);
    expect(b.camp).toBe('');
    expect(b.wlCampLine).toBe('');
  });

  it('非主權實體（比北軍政府）用斜線圖樣', () => {
    const p = decorateSovereignty(dto(feature('r1', 'mil-admin-belgium-northern-france', { status: 'not_sovereign' }))).features[0].properties;
    expect(p.wlPattern).toBe(hatchImageId(p.wlFill, 'contested'));
    expect(decorateSovereignty(dto(feature('r2', 'kingdom-of-belgium'))).features[0].properties.wlPattern).toBe('');
  });

  it('待查證事件會標 pending', () => {
    expect(decorateSovereignty(dto(feature('r1', 'deutsches-reich', { pending: true }))).features[0].properties.pending).toBe(true);
    expect(decorateSovereignty(dto(feature('r1', 'deutsches-reich'))).features[0].properties.pending).toBe(false);
  });

  it('英國屬地沿用英國色；測試尾碼與未列政權有穩定的後備色', () => {
    expect(regimeColor('gibraltar-crown-colony')).toBe(REGIME_COLORS['united-kingdom']);
    expect(regimeColor('deutsches-reich-1a2b3c4d')).toBe(REGIME_COLORS['deutsches-reich']);
    expect(regimeColor('some-unknown-regime')).toBe(regimeColor('some-unknown-regime'));
  });

  it('國名標籤放在最大的多邊形', () => {
    const labels = sovereigntyLabels(dto(feature('r1', 'deutsches-reich')), () => '德意志國');
    expect(labels).toHaveLength(1);
    expect(labels[0].bbox).toEqual([0, 0, 4, 3]);
    expect(labels[0].versionId).toBe('sov-r1');
    expect(sovereigntyLabels(dto(feature('r1', 'x')), () => null)).toHaveLength(0);
  });
});

describe('sovereigntyLabels：國名標籤放寬尺寸門檻（fit=1）並由大到小排序', () => {
  it('fit=1、大國在前', () => {
    const sq = (x0: number, y0: number, s: number) => [[[[x0, y0], [x0 + s, y0], [x0 + s, y0 + s], [x0, y0 + s], [x0, y0]]]];
    const dto = {
      date: '1938-10-15',
      featureCollection: {
        type: 'FeatureCollection',
        features: [
          { id: 'a', type: 'Feature', geometry: { type: 'MultiPolygon', coordinates: sq(0, 0, 1) }, properties: { recordId: 'a', regimeId: 'A' } },
          { id: 'b', type: 'Feature', geometry: { type: 'MultiPolygon', coordinates: sq(10, 10, 5) }, properties: { recordId: 'b', regimeId: 'B' } },
        ],
      },
    } as never;
    const out = sovereigntyLabels(dto, (id) => `名${id}`);
    expect(out.map((l) => l.regimeId)).toEqual(['B', 'A']);
    expect(out.every((l) => l.fit === 1)).toBe(true);
  });
});
