import { TestBed } from '@angular/core/testing';
import type { BioDetailCitation, LeaderBio } from '../../core/api/world-line-api';
import { PersonDialog } from './person-dialog';

const q = (el: HTMLElement, id: string) => el.querySelector<HTMLElement>(`[data-testid="${id}"]`);
const qa = (el: HTMLElement, id: string) => [...el.querySelectorAll<HTMLElement>(`[data-testid="${id}"]`)];
const txt = (e: Element | null | undefined) => (e?.textContent ?? '').replace(/\s+/g, ' ').trim();

const cite = (id: string, quote: string, locator: string, title: string): BioDetailCitation => ({
  id, locator, quote, quoteLang: 'zh-Hant', evidenceNote: null, accessedOn: '2026-11-01', grade: 'A', datePrecision: null,
  source: { id: `s-${id}`, sourceKind: 'encyclopedia', title, publisher: '測試出版社', authors: null, publishedText: null, licenseCode: null, licenseEvidenceUrl: null, url: `https://example.org/${id}`, archiveUrl: null },
});

/** 測試夾具（非真實史料）。 */
const base = (over: Partial<LeaderBio> = {}): LeaderBio => ({
  id: 'p1', name: 'Test Person', nameZh: '測試人物', birthDate: '1900-01-01', birthDatePrecision: 'day', deathDate: null,
  birthPlace: null, party: null, summary: { 'zh-Hant': '一句話摘要。' }, fieldSources: null, isTest: true, portrait: null, fieldCitations: [],
  terms: [{ recordId: 't1', regimeId: 'r', regimeSlug: 'x', regimeName: { 'zh-Hant': '測試國' }, role: 'head_of_state', title: null, validPeriod: { start: '1930-01-01', end: '1940-01-01' }, source: '', sourceUrl: null }],
  ...over,
});
const paras = [
  { id: 'g2', ord: 2, period: { start: '1920-01-01', end: '1930-01-01' }, periodStartPrecision: 'year', periodEndPrecision: 'year', heading: { 'zh-Hant': '第二段標題' }, body: { 'zh-Hant': '第二段正文。' }, citations: [] },
  { id: 'g1', ord: 1, period: null, periodStartPrecision: null, periodEndPrecision: null, heading: { 'zh-Hant': '第一段標題' }, body: { 'zh-Hant': '第一段甲。\n\n第一段乙。' }, citations: [cite('c1', '引文甲', 'p.12', '來源甲')] },
];
const pos = (id: string, start: string, title: string) => ({ id, seedKey: id, regimeId: null, organization: { 'zh-Hant': '某機構' }, title: { 'zh-Hant': title }, positionKind: 'office', period: { start, end: null }, startPrecision: 'year', endPrecision: null, note: '備註X', citations: id === 'q1' ? [cite('c2', '經歷引文', '§3', '來源乙')] : [] });
const roles = [{ id: 'r1', seedKey: 'r1', regimeId: null, organization: null, title: { 'zh-Hant': '代理總理' }, roleKind: 'head_of_government', period: { start: '1935-01-01', end: '1936-01-01' }, startPrecision: 'day', endPrecision: 'day', acting: true, t14Rule: null, note: null, citations: [] }];

async function render(data: LeaderBio) {
  const fixture = TestBed.createComponent(PersonDialog);
  fixture.componentRef.setInput('state', { status: 'ok', data });
  await fixture.whenStable();
  return { fixture, el: fixture.nativeElement as HTMLElement };
}

describe('PersonDialog：B3 分段生平／經歷／角色', () => {
  it('有多段 paragraphs：依 ord 顯示 heading、period、正文；不再顯示一句話摘要', async () => {
    const { el } = await render(base({ paragraphs: paras }));
    expect(qa(el, 'person-segment').map((x) => x.dataset['ord'])).toEqual(['1', '2']);
    expect(qa(el, 'person-segment-heading').map(txt)).toEqual(['第一段標題', '第二段標題']);
    expect(qa(el, 'person-segment-period').map(txt)).toEqual(['1920 – 1929']);
    expect(qa(el, 'person-segment-body').map((x) => txt(x).replace(/\d+$/, ''))).toEqual(['第一段甲。', '第一段乙。', '第二段正文。']);
    expect(el.textContent).not.toContain('一句話摘要');
    expect(q(el, 'person-paragraph')).toBeNull();
  });

  it('paragraphs 缺欄、空陣列或正文全空：退回一句話摘要', async () => {
    for (const p of [undefined, [], [{ ...paras[0], body: { 'zh-Hant': '  ' } }]]) {
      const { el } = await render(base({ paragraphs: p }));
      expect(qa(el, 'person-paragraph').map(txt)).toEqual(['一句話摘要。']);
      expect(q(el, 'person-segment')).toBeNull();
    }
  });

  it('有 positions：依起日列出經歷（title／機構／種類／期間／備註）；沒有則不放區塊也沒有分頁', async () => {
    const { el } = await render(base({ positions: [pos('q2', '1925-01-01', '後任'), pos('q1', '1910-01-01', '前任')] }));
    expect(qa(el, 'person-position-title').map(txt)).toEqual(['前任', '後任']);
    expect(qa(el, 'person-position-kind').map(txt)).toEqual(['office', 'office']);
    expect(qa(el, 'person-position-period').map(txt)[0]).toBe('1910 – 迄今不明');
    expect(txt(q(el, 'person-position-org'))).toBe('某機構');
    expect(txt(q(el, 'person-position-note'))).toBe('備註X');
    expect(q(el, 'person-dialog-tab-positions')).not.toBeNull();
    expect(qa(el, 'person-term').length).toBe(1); // 既有「職位與任期」保留

    const empty = await render(base({ positions: [] }));
    expect(q(empty.el, 'person-dialog-section-positions')).toBeNull();
    expect(q(empty.el, 'person-dialog-tab-positions')).toBeNull();
  });

  it('有 roles：顯示 title／roleKind／代理／期間；版頭角色標籤仍只來自 terms', async () => {
    const { el } = await render(base({ roles }));
    expect(txt(q(el, 'person-role-title'))).toBe('代理總理');
    expect(txt(q(el, 'person-role-kind'))).toBe('head_of_government');
    expect(q(el, 'person-role-acting')).not.toBeNull();
    expect(txt(q(el, 'person-role-period'))).toBe('1935-01-01 – 1936-01-01'.replace('1936-01-01', '1935-12-31'));
    expect(qa(el, 'person-dialog-role').map(txt)).toEqual(['國家元首 1930–1939']);
    expect(q((await render(base())).el, 'person-dialog-section-roles')).toBeNull();
  });

  it('引文進底部資料來源區：預設收合，展開後看得到 quote／locator／grade／來源；正文內不夾引文', async () => {
    const { fixture, el } = await render(base({ paragraphs: paras, positions: [pos('q1', '1910-01-01', '前任')] }));
    expect(q(el, 'person-sources-label')?.textContent?.trim()).toBe('資料來源 (2)');
    expect(q(el, 'person-sources-toggle')?.getAttribute('aria-expanded')).toBe('false');
    expect(q(el, 'person-sources-panel')?.hidden).toBe(true);
    expect(q(el, 'person-dialog-section-paragraphs')?.querySelector('[data-testid="source-quote"]')).toBeNull();
    q(el, 'person-sources-toggle')!.click();
    await fixture.whenStable();
    const panel = q(el, 'person-sources-panel')!;
    expect(panel.hidden).toBe(false);
    expect(qa(panel, 'source-quote-text').map(txt)).toEqual(['引文甲', '經歷引文']);
    expect(txt(panel)).toContain('位置：p.12');
    expect(qa(panel, 'source-grade').map(txt)).toEqual(['等級：A', '等級：A']);
    expect(txt(panel)).toContain('來源甲');
    expect(txt(panel)).toContain('來源乙');
  });
});
