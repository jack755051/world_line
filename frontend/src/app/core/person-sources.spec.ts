import type { LeaderBio } from './api/world-line-api';
import { fieldSourceItems, legacyItem, termSourceItems } from './person-sources';

const bio = (over: Partial<LeaderBio> = {}): LeaderBio => ({
  id: 'b', name: 'X', nameZh: null, birthDate: null, birthDatePrecision: null, deathDate: null,
  birthPlace: null, party: null, summary: null, fieldSources: null, isTest: false, ...over,
});

describe('person-sources', () => {
  it('只有「待查證」狀態、沒有文字與網址 → 不算來源（前端顯示待補來源）', () => {
    expect(legacyItem({ status: '待查證', note: '線索' })).toBeNull();
    expect(legacyItem(null)).toBeNull();
  });

  it('逐欄位：結構化引用在前、舊格式備註在後；其他欄位的來源不借用', () => {
    const b = bio({
      fieldSources: { birthDate: { source: 'royal.uk', url: 'https://www.royal.uk/x', status: 'verified' } },
      fieldCitations: [{ id: 'c', field: 'birthDate', locator: 'para 1', evidenceNote: null, accessedOn: '2026-11-07',
        source: { id: 's', sourceKind: 'official_record', title: 'Bio', publisher: 'WH', authors: null, publishedText: null, licenseCode: 'us_federal_pd', licenseEvidenceUrl: null, url: 'https://a', archiveUrl: null } }],
    });
    const items = fieldSourceItems(b, 'birthDate');
    expect(items.map((i) => i.kind)).toEqual(['structured', 'legacy']);
    expect(items[0].locator).toBe('para 1');
    expect(fieldSourceItems(b, 'deathDate')).toEqual([]);
  });

  it('任期出處是舊格式文字', () => {
    expect(termSourceItems({ source: 'Archontology', sourceUrl: 'https://www.archontology.org/' })[0].kind).toBe('legacy');
    expect(termSourceItems({ source: '', sourceUrl: null })).toEqual([]);
  });
});
