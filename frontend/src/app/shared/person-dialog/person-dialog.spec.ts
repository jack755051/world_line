import { TestBed } from '@angular/core/testing';
import type { LeaderBio } from '../../core/api/world-line-api';
import { ageAtDeath, lifeText } from './life-format';
import { PersonDialog } from './person-dialog';

const q = (el: HTMLElement, id: string) => el.querySelector(`[data-testid="${id}"]`);
/** 文字（去掉上標編號、空白正規化）。 */
const plain = (el: Element | null) => {
  if (!el) return '';
  const c = el.cloneNode(true) as Element;
  c.querySelectorAll('[data-testid="person-field-sup"]').forEach((x) => x.remove());
  return (c.textContent ?? '').replace(/[\s\u3000\u2003]+/g, ' ').trim();
};
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
    expect(q(el, 'person-dialog-life-years')?.textContent?.trim()).toBe('1889 – 1945');
    expect(plain(q(el, 'person-dialog-life-detail'))).toBe('生於 1889年4月20日·布勞瑙 卒於 1945年4月30日');
    expect(q(el, 'person-dialog-life-age')?.textContent?.trim()).toBe('享年 56 歲');
    expect(q(el, 'person-dialog-life')?.querySelector('svg')).toBeNull(); // 不再用日曆圖示
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

  it('引文：展開來源後掛在對應來源下（逐字、加引號、帶 lang）；沒有引文不佔位；與出處備註相同只列一次；同來源不同引文分列', async () => {
    const src = { id: 's', sourceKind: 'reference_work', title: 'Dictionary of Irish Biography', publisher: 'RIA', authors: null, publishedText: null, licenseCode: null, licenseEvidenceUrl: null, url: 'https://dib.ie/x', archiveUrl: null };
    const long = 'De Valera formed a government which lasted for 16 years, and during this period he introduced a new constitution';
    const { fixture, el } = await render(bio({
      fieldSources: {}, terms: [], summary: null,
      fieldCitations: [
        { id: 'c1', field: 'birthDate', locator: '670', evidenceNote: 'born 14 October 1882, Manhattan', accessedOn: '2026-11-07', source: src, quote: 'born 14 October 1882, Manhattan', quoteLang: 'en' },
        { id: 'c2', field: 'deathDate', locator: '670', evidenceNote: 'died 29 August 1975 … long evidence', accessedOn: '2026-11-07', source: src, quote: 'died 29 August 1975', quoteLang: null },
        { id: 'c3', field: 'birthPlace', locator: 'index', evidenceNote: null, accessedOn: '2026-11-07', source: { ...src, title: 'GND' }, quote: null },
        { id: 'c4', field: 'party', locator: 'career', evidenceNote: null, accessedOn: '2026-11-07', source: src, quote: long, quoteLang: 'en' },
      ],
      party: { 'zh-Hant': '共和黨' },
    }));
    expect((q(el, 'person-sources-panel') as HTMLElement).hidden).toBe(true); // 預設收合
    (q(el, 'person-sources-toggle') as HTMLButtonElement).click();
    await fixture.whenStable();
    const notes = qa(el, 'person-source-note');
    expect(notes.length).toBe(4);
    const quoteOf = (n: HTMLElement) => n.querySelector<HTMLElement>('[data-testid="source-quote-text"]');
    const byUse = (s: string) => notes.find((n) => n.querySelector('[data-testid="person-source-used-for"]')?.textContent?.trim() === `用於：${s}`)!;
    expect(quoteOf(byUse('出生'))?.textContent).toBe('born 14 October 1882, Manhattan');
    expect(quoteOf(byUse('出生'))?.getAttribute('lang')).toBe('en');
    expect(byUse('出生').querySelector('[data-testid="source-quote"]')?.textContent).toContain('「born 14 October 1882, Manhattan」');
    expect(byUse('出生').textContent?.split('born 14 October 1882').length).toBe(2); // 與備註相同：只出現一次
    expect(quoteOf(byUse('逝世'))?.textContent).toBe('died 29 August 1975');
    expect(quoteOf(byUse('逝世'))?.hasAttribute('lang')).toBe(false);
    expect(byUse('逝世').textContent).toContain('long evidence'); // 備註與引文不同：備註照列
    expect(quoteOf(byUse('出生地'))).toBeNull(); // 沒有引文：不佔位
    expect(byUse('出生地').querySelector('[data-testid="source-quote"]')).toBeNull();
    expect(quoteOf(byUse('黨派'))?.textContent).toBe(long); // 不截斷
    // 上標記號不塞引文
    expect(q(el, 'person-field-birthDate')?.textContent).not.toContain('born');
  });

  it('間隔號統一用 ·（U+00B7）：任期來源「用於」標籤、來源出版者、授權與查證日期之間', async () => {
    const src = { id: 's', sourceKind: 'official_record', title: 'Bio', publisher: 'WH', authors: null, publishedText: null, licenseCode: 'us_federal_pd', licenseEvidenceUrl: null, url: 'https://a', archiveUrl: null };
    const { fixture, el } = await render(bio({
      fieldCitations: [{ id: 'c', field: 'birthDate', locator: 'p', evidenceNote: null, accessedOn: '2026-11-07', source: src }],
    }));
    (q(el, 'person-sources-toggle') as HTMLButtonElement).click();
    await fixture.whenStable();
    const text = q(el, 'person-sources-panel')?.textContent ?? '';
    expect(text).toContain('職位與任期·國家元首');
    expect(text).toContain('·WH');
    expect(el.textContent).not.toContain('・');
  });

  it('全部欄位都有來源時不顯示「待補來源」；完全沒有來源時 N = 0', async () => {
    let r = await render(bio({ fieldSources: {}, terms: [], birthPlace: null, summary: null, birthDate: null, deathDate: null }));
    expect(q(r.el, 'person-sources-label')?.textContent?.trim()).toBe('資料來源 (0)');
    expect(q(r.el, 'person-paragraph-empty')).not.toBeNull();
    r = await render(bio({ fieldSources: { name: SRC }, terms: [], birthPlace: null, summary: null, birthDate: null, deathDate: null }));
    expect(q(r.el, 'source-pending')).toBeNull();
  });
});

describe('PersonDialog：版頭摘要與傳記式生卒', () => {
  it('版頭摘要：出生地、黨派、主要職位與任期、所屬政權；下方不再有基本資料大格；上標留在對應欄位', async () => {
    const { el } = await render(bio({ party: { 'zh-Hant': '國家社會主義德意志工人黨' }, fieldSources: { birthDate: SRC, deathDate: SRC, birthPlace: { source: 'GND', status: 'verified' } } }));
    const basics = q(el, 'person-dialog-basics') as HTMLElement;
    expect(basics.closest('[data-testid="person-dialog-hero"]')).not.toBeNull();
    expect(qa(basics, 'person-field-birthPlace')[0].textContent).toContain('布勞瑙');
    expect(qa(basics, 'person-field-party')[0].textContent).toContain('國家社會主義德意志工人黨');
    expect(qa(basics, 'person-field-mainRole')[0].textContent).toContain('國家元首·Führer');
    expect(qa(basics, 'person-field-mainRole')[0].textContent).toContain('1934-08-02 – 1945-04-29');
    expect(qa(basics, 'person-field-regime')[0].textContent).toContain('德意志國');
    expect(q(el, 'person-dialog-section-basics')).toBeNull();
    expect(qa(q(el, 'person-field-birthPlace') as HTMLElement, 'person-field-sup').map((x) => x.textContent?.trim())).toEqual(['2']);
    expect(qa(q(el, 'person-life-birthPlace') as HTMLElement, 'person-field-sup').map((x) => x.textContent?.trim())).toEqual(['2']);
    expect(qa(q(el, 'person-field-mainRole') as HTMLElement, 'person-field-sup').length).toBe(1); // 任期 RGBl
  });

  it('沒有黨派：摘要寫「尚無資料」；沒有任期：省略主要職位與所屬政權', async () => {
    const { el } = await render(bio({ terms: [] }));
    expect(q(el, 'person-field-party')?.textContent).toContain('尚無資料');
    expect(q(el, 'person-field-mainRole')).toBeNull();
    expect(q(el, 'person-field-regime')).toBeNull();
  });

  it('年份精度：只寫年、不寫享年', async () => {
    const { el } = await render(bio({ birthDate: '1868-01-01', birthDatePrecision: 'year', deathDate: '1943-01-01', deathDatePrecision: 'year' }));
    expect(q(el, 'person-dialog-life-years')?.textContent?.trim()).toBe('1868 – 1943');
    expect(plain(q(el, 'person-dialog-life-detail'))).toBe('生於 1868年·布勞瑙 卒於 1943年');
    expect(q(el, 'person-dialog-life-age')).toBeNull();
  });

  it('一端只有月或年精度：不寫享年', async () => {
    let r = await render(bio({ deathDate: '1945-04-01', deathDatePrecision: 'month' }));
    expect(q(r.el, 'person-field-deathDate')?.textContent).toContain('卒於 1945年4月');
    expect(q(r.el, 'person-dialog-life-age')).toBeNull();
    r = await render(bio({ birthDate: '1889-01-01', birthDatePrecision: 'year' }));
    expect(q(r.el, 'person-dialog-life-age')).toBeNull();
  });

  it('只有生年：大字「1889 –」、只寫生於、不寫享年；只有卒年：對稱；生卒都沒有：不顯示', async () => {
    let r = await render(bio({ deathDate: null, deathDatePrecision: null }));
    expect(q(r.el, 'person-dialog-life-years')?.textContent?.trim()).toBe('1889 –');
    expect(q(r.el, 'person-dialog-life-detail')?.textContent).not.toContain('卒於');
    expect(q(r.el, 'person-dialog-life-age')).toBeNull();
    r = await render(bio({ birthDate: null, birthDatePrecision: null }));
    expect(q(r.el, 'person-dialog-life-years')?.textContent?.trim()).toBe('– 1945');
    expect(plain(q(r.el, 'person-dialog-life-detail'))).toBe('卒於 1945年4月30日'); // 無生日不硬加出生地
    expect(q(r.el, 'person-dialog-life-age')).toBeNull();
    r = await render(bio({ birthDate: null, deathDate: null }));
    expect(q(r.el, 'person-dialog-life')).toBeNull();
  });

  it('有生日無出生地：不硬加出生地', async () => {
    const { el } = await render(bio({ birthPlace: null }));
    expect(q(el, 'person-life-birthPlace')).toBeNull();
    expect(q(el, 'person-field-birthDate')?.textContent).toContain('生於 1889年4月20日');
  });

  it('英文介面：英文月份、Born／Died、aged N', async () => {
    const fixture = TestBed.createComponent(PersonDialog);
    fixture.componentRef.setInput('state', { status: 'ok', data: bio({ birthPlace: { en: 'Braunau am Inn' } }) });
    fixture.componentRef.setInput('lang', 'en');
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    expect(q(el, 'person-dialog-life-years')?.textContent?.trim()).toBe('1889 – 1945');
    expect(plain(q(el, 'person-dialog-life-detail'))).toBe('Born 20 April 1889, Braunau am Inn Died 30 April 1945');
    expect(q(el, 'person-dialog-life-age')?.textContent?.trim()).toBe('aged 56');
  });
});

describe('lifeText／ageAtDeath（享年以生卒日計算）', () => {
  it('未過生日減一、卒日即生日算已滿', () => {
    expect(lifeText('1874-11-30', 'day', '1965-01-24', 'day', 'zh-Hant')).toEqual({ years: '1874 – 1965', born: '1874年11月30日', died: '1965年1月24日', age: '享年 90 歲' });
    expect(ageAtDeath({ y: 1900, m: 5, d: 10 }, { y: 1950, m: 5, d: 9 })).toBe(49);
    expect(ageAtDeath({ y: 1900, m: 5, d: 10 }, { y: 1950, m: 5, d: 10 })).toBe(50);
    expect(ageAtDeath({ y: 1900, m: 5, d: 10 }, { y: 1950, m: 6, d: 1 })).toBe(50);
    expect(lifeText('1874-11-30', 'day', '1965-01-24', 'day', 'en').born).toBe('30 November 1874');
    expect(lifeText('1874-11-30', 'day', '1965-01-24', 'day', 'en').age).toBe('aged 90');
  });
  it('精度未標：完整日期視為日；year／month 不寫享年', () => {
    expect(lifeText('1874-11-30', null, '1965-01-24', null, 'zh-Hant').age).toBe('享年 90 歲');
    expect(lifeText('1874-01-01', 'year', '1965-01-24', 'day', 'zh-Hant')).toEqual({ years: '1874 – 1965', born: '1874年', died: '1965年1月24日', age: '' });
    expect(lifeText('1874-11-01', 'month', '1965-01-24', 'day', 'en')).toEqual({ years: '1874 – 1965', born: 'November 1874', died: '24 January 1965', age: '' });
    expect(lifeText(null, null, null, null, 'zh-Hant').years).toBe('');
  });
});

describe('PersonDialog：§17 P1 開關狀態（測試環境無 matchMedia → 直接到終態）', () => {
  it('開啟即 data-motion-state=open；open=false 時進入 closing（inert、不可點）並送出 hidden', async () => {
    const { fixture, el } = await render(bio());
    const root = q(el, 'person-dialog-root') as HTMLElement;
    expect(root.getAttribute('data-motion-state')).toBe('open');
    expect(root.hasAttribute('inert')).toBe(false);
    let hidden = 0;
    fixture.componentInstance.hidden.subscribe(() => hidden++);
    fixture.componentRef.setInput('open', false);
    await fixture.whenStable();
    expect(hidden).toBe(1);
    expect(root.getAttribute('data-motion-state')).toBe('closing');
    expect(root.hasAttribute('inert')).toBe(true);
    expect(root.classList.contains('pointer-events-none')).toBe(true);
  });
});
