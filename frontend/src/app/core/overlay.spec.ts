import { describe, expect, it } from 'vitest';
import { intervalIndex, overlayCapitals, overlayConflicts, overlayControl, overlayKey, type OverlayFile } from './overlay';

const o = {
  version: 'abc',
  range: ['1908-10-05', '1945-12-31'],
  control: {
    points: ['1908-10-05', '1940-06-01'],
    intervals: [
      { start: '1908-10-05', features: [], theaters: [], notes: [] },
      { start: '1940-06-01', features: ['h1'], theaters: [{ theaterCode: 'w', state: 'attested' }], notes: ['n1'] },
    ],
    features: { h1: { type: 'Feature', properties: { versionId: 'v1', controllerRegimeId: 'r' } } },
    shapes: { v1: { largest: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]] }, bbox: [0, 0, 5, 5] } },
    notes: { n1: { id: 'g1', reason: 'x' } },
    noteShapes: { g1: { largest: { type: 'Polygon', coordinates: [] }, bbox: null } },
  },
  conflicts: { points: ['1908-10-05', '1914-08-01'], intervals: [{ start: '1908-10-05', ids: [] }, { start: '1914-08-01', ids: ['c'] }], records: { c: { id: 'c1' } } },
  capitals: { points: ['1908-10-05'], intervals: [{ start: '1908-10-05', ids: ['k'] }], records: { k: { recordId: 'k1' } } },
} as unknown as OverlayFile;

describe('overlay（§9 步驟 5）', () => {
  it('intervalIndex：≤ 日期的最後一個變動點', () => {
    expect(intervalIndex(['a', 'c', 'e'], 'b')).toBe(0);
    expect(intervalIndex(['a', 'c', 'e'], 'e')).toBe(2);
    expect(intervalIndex(['b'], 'a')).toBe(-1);
  });
  it('控制區：區間內的 feature 帶最大多邊形與全幾何 bbox、戰區狀態與涵蓋備註；範圍外回 null', () => {
    const d = overlayControl(o, '1941-01-01')!;
    expect(d.date).toBe('1941-01-01');
    const f = d.featureCollection.features[0] as unknown as { bbox: number[]; geometry: { type: string }; properties: { versionId: string } };
    expect(f.properties.versionId).toBe('v1');
    expect(f.geometry.type).toBe('Polygon');
    expect(f.bbox).toEqual([0, 0, 5, 5]);
    expect(d.theaters).toEqual([{ theaterCode: 'w', state: 'attested' }]);
    expect(d.coverageNotes?.[0].id).toBe('g1');
    expect(overlayControl(o, '1930-01-01')!.featureCollection.features).toEqual([]);
    expect(overlayControl(o, '1907-01-01')).toBeNull();
    expect(overlayControl(o, '1946-01-01')).toBeNull();
  });
  it('衝突、首都：依區間；key 同區間相同', () => {
    expect(overlayConflicts(o, '1915-01-01')!.featureCollection.features).toEqual([{ id: 'c1' }]);
    expect(overlayCapitals(o, '1920-01-01')!.features).toEqual([{ recordId: 'k1' }]);
    expect(overlayKey(o, 'conflicts', '1915-01-01')).toBe(overlayKey(o, 'conflicts', '1916-01-01'));
    expect(overlayKey(o, 'conflicts', '1913-01-01')).not.toBe(overlayKey(o, 'conflicts', '1915-01-01'));
    expect(overlayKey(o, 'leaders', '1915-01-01')).toBeNull();
  });
});
