import type { LeaderRecord } from './api/world-line-api';
import { formatPartialDate, groupLeaders, formatTerm, inclusiveEnd, pickLocalized, portraitDisplayable } from './person-format';

describe('person-format', () => {
  const rec = (recordId: string, personId: string | null, role: 'head_of_state' | 'head_of_government'): LeaderRecord => ({
    recordId, regimeId: 'g', regimeSlug: 'g', name: recordId, nameZh: null, role, title: '', validPeriod: { start: '1933-01-30', end: null },
    source: '', sourceUrl: null, verified: true, personId, bio: null,
  });

  it('groupLeaders：同 personId 合併（角色依元首在前）；沒有 personId 各自一張；卡片依最高角色排序', () => {
    const g = groupLeaders([rec('a', 'p1', 'head_of_government'), rec('b', null, 'head_of_government'), rec('c', 'p1', 'head_of_state'), rec('d', null, 'head_of_government')]);
    expect(g.map((x) => x.records.map((r) => r.recordId))).toEqual([['c', 'a'], ['b'], ['d']]);
    expect(g[0].personId).toBe('p1');
  });

  it('inclusiveEnd：半開區間迄日減一天（含跨月、跨年、閏年）', () => {
    expect(inclusiveEnd('1945-10-01')).toBe('1945-09-30');
    expect(inclusiveEnd('1945-01-01')).toBe('1944-12-31');
    expect(inclusiveEnd('1944-03-01')).toBe('1944-02-29');
    expect(inclusiveEnd(null)).toBeNull();
  });

  it('formatTerm：顯示最後在任日；沒有迄日顯示迄今不明', () => {
    expect(formatTerm({ start: '1933-01-30', end: '1945-04-30' }, 'zh-Hant')).toBe('1933-01-30 – 1945-04-29');
    expect(formatTerm({ start: '1940-01-01', end: null }, 'zh-Hant')).toBe('1940-01-01 – 迄今不明');
    expect(formatTerm({ start: '1940-01-01', end: null }, 'en')).toBe('1940-01-01 – end unknown');
  });

  it('formatPartialDate：依精度，不補造月日', () => {
    expect(formatPartialDate('1913-01-01', 'year')).toBe('1913');
    expect(formatPartialDate('1935-12-01', 'month')).toBe('1935-12');
    expect(formatPartialDate('1882-01-30', 'day')).toBe('1882-01-30');
    expect(formatPartialDate('1882-01-30', null)).toBe('1882-01-30');
    expect(formatPartialDate(null, 'day')).toBe('');
  });

  it('portraitDisplayable：授權不在允許清單或欄位不全就不顯示', () => {
    const ok = { url: 'https://upload.wikimedia.org/a.jpg', sourceUrl: 'https://commons.wikimedia.org/wiki/File:a.jpg', author: null, licenseCode: 'pd_expired', licenseUrl: null, attribution: 'x', retrievedOn: '2026-11-07' };
    expect(portraitDisplayable(ok)).toBe(true);
    expect(portraitDisplayable({ ...ok, licenseCode: 'cc_by_nc' })).toBe(false);
    expect(portraitDisplayable({ ...ok, attribution: '' })).toBe(false);
    expect(portraitDisplayable({ ...ok, url: 'http://example.com/a.jpg' })).toBe(false);
    expect(portraitDisplayable(null)).toBe(false);
  });

  it('pickLocalized：依語言，缺就用另一語言', () => {
    expect(pickLocalized({ 'zh-Hant': '柏林' }, 'en')).toBe('柏林');
    expect(pickLocalized({ 'zh-Hant': '柏林', en: 'Berlin' }, 'en')).toBe('Berlin');
    expect(pickLocalized(null, 'zh-Hant')).toBe('');
  });
});
