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
    expect(items[0].sourceKind).toBe('official_record');
    expect(fieldSourceItems(b, 'deathDate')).toEqual([]);
  });

  it('引文：帶出 quote／quoteLang（逐字）；API 為 null 或未帶時為 null', () => {
    const src = { id: 's', sourceKind: 'reference_work', title: 'DIB', publisher: 'RIA', authors: null, publishedText: null, licenseCode: null, licenseEvidenceUrl: null, url: 'https://dib', archiveUrl: null };
    const b = bio({
      fieldCitations: [
        { id: 'c1', field: 'birthDate', locator: '670', evidenceNote: 'born 14 October 1882', accessedOn: '2026-11-07', source: src, quote: 'born 14 October 1882', quoteLang: 'en' },
        { id: 'c2', field: 'birthDate', locator: 'p. 2', evidenceNote: null, accessedOn: '2026-11-07', source: src, quote: null },
        { id: 'c3', field: 'birthDate', locator: 'p. 3', evidenceNote: null, accessedOn: '2026-11-07', source: src },
      ],
    });
    const items = fieldSourceItems(b, 'birthDate');
    expect(items.map((i) => [i.quote, i.quoteLang])).toEqual([['born 14 October 1882', 'en'], [null, null], [null, null]]);
  });

  it('欄位引用帶出等級（Tai 2026-11-12：每筆來源都顯示等級）；API 未帶時為 null', () => {
    const src = { id: 's', sourceKind: 'encyclopedia', title: 'Gale', publisher: 'Gale', authors: null, publishedText: null, licenseCode: null, licenseEvidenceUrl: null, url: 'https://g', archiveUrl: null };
    const b = bio({
      fieldCitations: [
        { id: 'c1', field: 'summary', locator: 'entry', evidenceNote: null, accessedOn: '2026-11-14', source: src, grade: 'C' },
        { id: 'c2', field: 'summary', locator: 'entry 2', evidenceNote: null, accessedOn: '2026-11-14', source: src },
      ],
    });
    expect(fieldSourceItems(b, 'summary').map((i) => i.grade)).toEqual(['C', null]);
  });

  it('說法衝突：沒有出處文字也列出兩說，並去掉內部批次代號', () => {
    const it1 = legacyItem({ status: '說法衝突', note: 'BnF、GND 記 1883，LC 記 1882（rule-corrections-2026-11-14）' });
    expect(it1).toEqual({ kind: 'legacy', title: '說法衝突', note: 'BnF、GND 記 1883，LC 記 1882' });
    expect(legacyItem({ status: '說法衝突', note: '  ' })).toBeNull();
    expect(legacyItem({ status: '待查證', note: '原出處評為 X（rule-corrections-2026-11-14）' })).toBeNull();
  });

  it('任期出處是舊格式文字', () => {
    expect(termSourceItems({ source: 'Archontology', sourceUrl: 'https://www.archontology.org/' })[0].kind).toBe('legacy');
    expect(termSourceItems({ source: '', sourceUrl: null })).toEqual([]);
  });
});
