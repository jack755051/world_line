import { TestBed } from '@angular/core/testing';
import type { LeaderBio } from '../../core/api/world-line-api';
import { PersonDialog } from './person-dialog';

const q = (el: HTMLElement, id: string) => el.querySelector(`[data-testid="${id}"]`);
const qa = (el: HTMLElement, id: string) => [...el.querySelectorAll<HTMLElement>(`[data-testid="${id}"]`)];

const SRC = { source: 'NDB 9 (1972)', url: 'https://example.org/ndb', status: 'verified' };
const bio = (over: Partial<LeaderBio> = {}): LeaderBio => ({
  id: 'p1', name: 'Adolf Hitler', nameZh: '阿道夫·希特勒', birthDate: '1889-04-20', birthDatePrecision: 'day', deathDate: '1945-04-30', deathDatePrecision: 'day',
  birthPlace: { 'zh-Hant': '布勞瑙' }, party: null, summary: { 'zh-Hant': '第一段。\n\n第二段。' },
  fieldSources: { birthDate: SRC, deathDate: SRC, summary: SRC }, isTest: false, portrait: null, fieldCitations: [],
  terms: [
    { recordId: 'l2', regimeId: 'g', regimeSlug: 'deutsches-reich', regimeName: { 'zh-Hant': '德意志國' }, role: 'head_of_state', title: 'Führer', validPeriod: { start: '1934-08-02', end: '1945-04-30' }, source: 'RGBl', sourceUrl: null },
    { recordId: 'l1', regimeId: 'g', regimeSlug: 'deutsches-reich', regimeName: { 'zh-Hant': '德意志國' }, role: 'head_of_government', title: 'Reichskanzler', validPeriod: { start: '1933-01-30', end: '1945-04-30' }, source: '', sourceUrl: null },
  ],
  ...over,
});

async function render(data: LeaderBio) {
  const fixture = TestBed.createComponent(PersonDialog);
  fixture.componentRef.setInput('state', { status: 'ok', data });
  await fixture.whenStable();
  return { fixture, el: fixture.nativeElement as HTMLElement };
}

describe('PersonDialog（Stitch 版面、羊皮紙配色）', () => {
  it('標頭：中文名、原文名、每個角色一個標籤、生卒；無授權照片＝佔位', async () => {
    const { el } = await render(bio());
    expect(q(el, 'person-dialog-title')?.textContent?.trim()).toBe('阿道夫·希特勒');
    expect(q(el, 'person-dialog-original-name')?.textContent).toContain('Adolf Hitler');
    expect(qa(el, 'person-dialog-role').map((x) => x.textContent?.trim())).toEqual(['國家元首 1934–1945', '政府首腦 1933–1945']);
    expect(q(el, 'person-dialog-life')?.textContent).toContain('1889-04-20 – 1945-04-30');
    expect(q(el, 'person-dialog-placeholder')).not.toBeNull();
  });

  it('區塊分頁籤：基本資料／生平／任期／來源；沒有戰役或事件資料就不出現該分頁', async () => {
    const { el } = await render(bio());
    const tabs = qa(el, 'person-dialog-tabs').flatMap((n) => [...n.querySelectorAll('button')]).map((b) => b.getAttribute('data-testid'));
    expect(tabs).toEqual(['person-dialog-tab-basics', 'person-dialog-tab-bio', 'person-dialog-tab-terms', 'person-dialog-tab-sources']);
  });

  it('來源：欄位只放上標編號；同一出處去重；底部「資料來源 (N)」預設收合；缺來源列出「待補來源」', async () => {
    const { fixture, el } = await render(bio());
    // 出生、逝世、生平共用同一筆 → 編號 1；國家元首任期 RGBl → 2
    expect(qa(q(el, 'person-field-birthDate') as HTMLElement, 'person-field-sup').map((x) => x.textContent?.trim())).toEqual(['1']);
    expect(qa(q(el, 'person-field-deathDate') as HTMLElement, 'person-field-sup').map((x) => x.textContent?.trim())).toEqual(['1']);
    expect(q(q(el, 'person-field-birthDate') as HTMLElement, 'source-toggle')).toBeNull();
    expect(q(el, 'person-sources-label')?.textContent?.trim()).toBe('資料來源 (2)');
    const toggle = q(el, 'person-sources-toggle') as HTMLButtonElement;
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    expect((q(el, 'person-sources-panel') as HTMLElement).hidden).toBe(true);
    expect(q(el, 'source-pending')?.textContent?.trim()).toBe('待補來源');
    toggle.click();
    await fixture.whenStable();
    expect((q(el, 'person-sources-panel') as HTMLElement).hidden).toBe(false);
    expect(qa(el, 'person-source-note').length).toBe(2);
    const missing = q(el, 'person-sources-missing')?.textContent ?? '';
    expect(missing).toContain('出生地');
    expect(missing).toContain('政府首腦');
    expect(missing).not.toContain('黨派'); // 沒有值的欄位顯示「尚無資料」，不列入待補來源
  });

  it('點上標編號：展開底部來源', async () => {
    const { fixture, el } = await render(bio());
    (q(el, 'person-field-sup') as HTMLButtonElement).click();
    await fixture.whenStable();
    expect(q(el, 'person-sources-toggle')?.getAttribute('aria-expanded')).toBe('true');
  });

  it('全部欄位都有來源時不顯示「待補來源」；完全沒有來源時 N = 0', async () => {
    let r = await render(bio({ fieldSources: {}, terms: [], birthPlace: null, summary: null, birthDate: null, deathDate: null }));
    expect(q(r.el, 'person-sources-label')?.textContent?.trim()).toBe('資料來源 (0)');
    expect(q(r.el, 'person-paragraph-empty')).not.toBeNull();
    r = await render(bio({ fieldSources: { name: SRC }, terms: [], birthPlace: null, summary: null, birthDate: null, deathDate: null }));
    expect(q(r.el, 'source-pending')).toBeNull();
  });
});
