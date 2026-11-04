import { TestBed } from '@angular/core/testing';
import type { SovereigntyFeatureProperties } from '../../core/api/api-types';
import type { LeaderBio, LeaderBioSummary } from '../../core/api/world-line-api';
import { SovereigntyCard } from './sovereignty-card';

const ev = (verification: 'verified' | 'pending', citations: unknown[] = []) => ({
  id: 'e1', eventKind: 'treaty', occurred: { start: '1938-09-29', end: '1938-10-01' },
  summary: { 'zh-Hant': '慕尼黑協定', en: 'Munich Agreement' }, verification, citations,
});
const props = (over: Partial<Record<string, unknown>> = {}) => ({
  recordId: 'r1', regimeId: 'g1', regimeSlug: 'deutsches-reich', layerStatus: 'de_jure',
  validPeriod: { start: '1938-10-10', end: '1938-11-21' },
  startEvent: ev('verified', [{ sourceId: 's', sourceTitle: 'FRUS 1938, vol. I', publisher: 'GPO', licenseCode: 'us_federal_pd', locator: 'Doc. 710, p. 734', role: 'primary', evidenceNote: '' }]),
  endEvent: ev('pending'),
  geometry: {
    sourceId: 's2', sourceTitle: 'OpenHistoricalMap', publisher: 'OHM', sourceLicenseCode: 'cc0', locator: 'relation/2704712 v208',
    geometryLicense: 'cc_by', attribution: '© GURS, CC BY 4.0', ohmRelationId: 2704712, ohmVersion: 208,
    flags: { osmDerivedWayCount: 232 },
  },
  note: null, regimeAlignment: null, ...over,
}) as unknown as SovereigntyFeatureProperties;

async function render(p: SovereigntyFeatureProperties, lang: 'zh-Hant' | 'en' = 'zh-Hant') {
  const fixture = TestBed.createComponent(SovereigntyCard);
  fixture.componentRef.setInput('props', p);
  fixture.componentRef.setInput('regimeName', '德意志國');
  fixture.componentRef.setInput('originalName', 'Deutsches Reich');
  fixture.componentRef.setInput('lang', lang);
  await fixture.whenStable();
  return { fixture, el: fixture.nativeElement as HTMLElement };
}
const q = (el: HTMLElement, id: string) => el.querySelector(`[data-testid="${id}"]`);

describe('SovereigntyCard（國界資訊卡）', () => {
  it('政權名、期間、起訖變動：有引用＝已查證附 locator；沒有＝待查證', async () => {
    const { el } = await render(props());
    expect(q(el, 'sovereignty-card-title')?.textContent).toContain('德意志國');
    expect(el.textContent).toContain('Deutsches Reich');
    expect(el.textContent).toContain('1938-10-10');
    expect(q(el, 'sovereignty-card-start')?.textContent).toContain('已查證');
    expect(q(el, 'sovereignty-card-citation')?.textContent).toContain('Doc. 710, p. 734');
    expect(q(el, 'sovereignty-card-end')?.querySelector('[data-testid="sovereignty-card-pending"]')?.textContent).toBe('待查證');
  });

  it('起訖變動同一結構：事件名稱 → 日期 → 徽章＋出處；徽章在名稱下方、與出處同一區塊', async () => {
    const { el } = await render(props());
    for (const key of ['start', 'end']) {
      const row = q(el, 'sovereignty-card-' + key)!;
      const kids = [...row.querySelector('wl-event-ref')!.children].map((c) => c.getAttribute('data-testid'));
      expect(kids).toEqual(['sovereignty-card-event-name', 'sovereignty-card-event-date', 'sovereignty-card-evidence']);
      expect(row.querySelector('[data-testid="sovereignty-card-event-date"]')?.textContent?.trim()).toBe('1938-09-29');
      const evidence = row.querySelector('[data-testid="sovereignty-card-evidence"]')!;
      expect(evidence.firstElementChild?.getAttribute('data-testid')).toMatch(/^sovereignty-card-(verified|pending)$/);
    }
    // 結束變動沒有出處：只標待查證與「尚無正式出處」，不補造
    const end = q(el, 'sovereignty-card-end')!;
    expect(end.querySelector('[data-testid="sovereignty-card-citation"]')).toBeNull();
    expect(end.querySelector('[data-testid="sovereignty-card-no-citation"]')?.textContent).toContain('尚無正式出處');
  });

  it('出處預設只顯示簡短引用，點一下展開完整書目、再點收合', async () => {
    const title = 'Documents on German Foreign Policy 1918–1945, Series D (1937–1945), Volume VIII: The War Years, September 4, 1939–March 18, 1940（美國國務院版）';
    const { fixture, el } = await render(props({
      startEvent: ev('verified', [{ sourceId: 's', sourceTitle: title, publisher: 'U.S. Department of State', licenseCode: 'us_federal_pd', locator: 'Doc. 157, pp. 164–165', role: 'primary', evidenceNote: '' }]),
    }));
    const start = q(el, 'sovereignty-card-start')!;
    const toggle = start.querySelector('[data-testid="sovereignty-card-citation-toggle"]') as HTMLButtonElement;
    expect(toggle.textContent?.trim()).toBe('DGFP D/VIII, Doc. 157, pp. 164–165');
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    expect(start.querySelector('[data-testid="sovereignty-card-citation-full"]')).toBeNull();
    expect(start.textContent).not.toContain('The War Years');
    toggle.click();
    await fixture.whenStable();
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    expect(start.querySelector('[data-testid="sovereignty-card-citation-full"]')?.textContent).toContain(title);
    expect(start.querySelector('[data-testid="sovereignty-card-citation-full"]')?.textContent).toContain('U.S. Department of State');
    toggle.click();
    await fixture.whenStable();
    expect(start.querySelector('[data-testid="sovereignty-card-citation-full"]')).toBeNull();
  });

  it('卡片內容可捲動（太高時不超出外框）', async () => {
    const { el } = await render(props());
    expect(q(el, 'sovereignty-card')?.className).toContain('max-h-[inherit]');
    expect(q(el, 'sovereignty-card-body')?.className).toContain('overflow-y-auto');
  });

  it('幾何出處：OHM 關係／版本、授權與署名；含 OSM 線段時標 ODbL', async () => {
    const { el } = await render(props());
    const g = q(el, 'sovereignty-card-geometry')!.textContent!;
    expect(g).toContain('relation/2704712 v208');
    expect(g).toContain('cc_by');
    expect(g).toContain('© GURS');
    expect(q(el, 'sovereignty-card-osm')?.textContent).toContain('ODbL');
    const clean = await render(props({ geometry: { ...props().geometry, flags: { osmDerivedWayCount: 0 } } }));
    expect(q(clean.el, 'sovereignty-card-osm')).toBeNull();
  });

  it('非主權：data-layer-status 與文字；沒有起訖事件時說明不追溯／未結束', async () => {
    const { el } = await render(props({ layerStatus: 'not_sovereign', startEvent: null, endEvent: null }));
    expect(q(el, 'sovereignty-card')?.getAttribute('data-layer-status')).toBe('not_sovereign');
    expect(q(el, 'sovereignty-card-status')?.textContent).toContain('非主權');
    expect(q(el, 'sovereignty-card-start')?.textContent).toContain('不追溯');
    expect(q(el, 'sovereignty-card-end')?.textContent).toContain('未結束');
  });

  it('陣營只作補充：沒有陣營資料顯示「陣營未建置」，不推定', async () => {
    const { el } = await render(props());
    expect(q(el, 'sovereignty-card-camp')?.getAttribute('data-camp')).toBe('unassigned');
    expect(q(el, 'sovereignty-card-camp')?.textContent).toContain('陣營未建置');
    expect(q(el, 'sovereignty-card-camp')?.textContent).toContain('不影響填色');
  });

  it('英文介面與關閉事件', async () => {
    const { fixture, el } = await render(props(), 'en');
    let closed = 0;
    fixture.componentInstance.closed.subscribe(() => closed++);
    expect(q(el, 'sovereignty-card-end')?.textContent).toContain('Pending verification');
    (el.querySelector('button[aria-label="Close"]') as HTMLButtonElement).click();
    expect(closed).toBe(1);
  });

  it('放在面板內：列出當日相關衝突（點一項送出 conflictSelect）與事件時間線（目前日期標示、點日期送出 eventJump）', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('conflicts', [{ recordId: 'c1', title: '德意志國 — 波蘭共和國', since: '1939-09-01' }]);
    const tev = (id: string, start: string, verification: 'verified' | 'pending', roles: string[]) => ({ ...ev(verification), id, occurred: { start, end: start }, roles });
    fixture.componentRef.setInput('regimeEvents', [tev('a', '1938-03-13', 'verified', ['border_start']), tev('b', '1939-09-01', 'verified', ['belligerent', 'conflict_start']), tev('c', '1940-05-10', 'pending', ['belligerent'])]);
    fixture.componentRef.setInput('eventsStatus', 'ok');
    fixture.componentRef.setInput('currentDate', '1939-10-23');
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    expect(q(el, 'sovereignty-card-title')).toBeNull(); // 標題由面板提供
    let picked = '';
    let jumped = '';
    fixture.componentInstance.conflictSelect.subscribe((id) => (picked = id));
    fixture.componentInstance.eventJump.subscribe((d) => (jumped = d));
    (q(el, 'sovereignty-card-conflict') as HTMLButtonElement).click();
    expect(picked).toBe('c1');
    (q(el, 'sovereignty-card-tab-events') as HTMLElement).click();
    await fixture.whenStable();
    const items = [...el.querySelectorAll('[data-testid="sovereignty-card-timeline-item"]')];
    expect(items.map((i) => i.getAttribute('data-when'))).toEqual(['past', 'now', 'future']);
    expect(items[1].textContent).toContain('交戰方');
    expect(items[1].textContent).toContain('開戰');
    expect(items[2].querySelector('[data-testid="sovereignty-card-timeline-pending"]')?.textContent).toBe('待考證');
    expect(items[2].getAttribute('data-pending')).toBe('true');
    (items[0].querySelector('[data-testid="sovereignty-card-timeline-jump"]') as HTMLButtonElement).click();
    expect(jumped).toBe('1938-03-13');
  });

  it('事件時間線：事後追加的參與方顯示「事後追加・角色（追加於 日期）」與理由；隨事件寫入的不顯示', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('tab', 'events');
    fixture.componentRef.setInput('regimeEvents', [
      { ...ev('verified'), id: 'a', occurred: { start: '1942-11-08', end: '1942-11-09' }, roles: ['belligerent'],
        additions: [{ role: 'belligerent', addedAt: '2026-10-31T14:46:35Z', note: { 'zh-Hant': '美軍為火炬行動登陸主力', en: 'US forces led Torch' } }] },
      { ...ev('verified'), id: 'b', occurred: { start: '1943-09-08', end: '1943-09-09' }, roles: ['signatory'] },
    ]);
    fixture.componentRef.setInput('eventsStatus', 'ok');
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    let items = [...el.querySelectorAll('[data-testid="sovereignty-card-timeline-item"]')];
    for (const it of items) (it.querySelector('[data-testid="sovereignty-card-timeline-toggle"]') as HTMLButtonElement).click();
    await fixture.whenStable();
    items = [...el.querySelectorAll('[data-testid="sovereignty-card-timeline-item"]')];
    const add = items[0].querySelector('[data-testid="sovereignty-card-timeline-addition"]');
    expect(add?.getAttribute('data-role')).toBe('belligerent');
    expect(add?.textContent).toContain('事後追加・交戰方');
    expect(add?.textContent).toContain('2026-10-31');
    expect(add?.textContent).toContain('美軍為火炬行動登陸主力');
    expect(items[1].querySelector('[data-testid="sovereignty-card-timeline-addition"]')).toBeNull();
  });

  it('面板內分頁：概要（含相關衝突）與事件；tablist／tab／tabpanel 的 aria、方向鍵切換、送出 tabChange、依 tab 輸入開在指定分頁', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('conflicts', [{ recordId: 'c1', title: '德意志國 — 波蘭共和國', since: '1939-09-01' }]);
    fixture.componentRef.setInput('regimeEvents', [{ ...ev('verified'), id: 'a', occurred: { start: '1938-03-13', end: '1938-03-13' }, roles: ['border_start'] }]);
    fixture.componentRef.setInput('eventsStatus', 'ok');
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    const tabs: string[] = [];
    fixture.componentInstance.tabChange.subscribe((t) => tabs.push(t));
    const list = el.querySelector('[role="tablist"]') as HTMLElement;
    expect(list).not.toBeNull();
    expect(list.getAttribute('aria-label')).toBe('政權資訊分頁');
    const ov = q(el, 'sovereignty-card-tab-overview') as HTMLElement;
    const evt = q(el, 'sovereignty-card-tab-events') as HTMLElement;
    expect(ov.getAttribute('role')).toBe('tab');
    expect(ov.getAttribute('aria-selected')).toBe('true');
    expect(evt.getAttribute('aria-selected')).toBe('false');
    expect(evt.textContent).toContain('事件');
    expect(q(el, 'sovereignty-card-tab-events-count')?.textContent?.trim()).toBe('1');
    const panelOf = (tab: HTMLElement) => el.querySelector('#' + tab.getAttribute('aria-controls')) as HTMLElement;
    expect(panelOf(ov).getAttribute('role')).toBe('tabpanel');
    expect(panelOf(ov).hidden).toBe(false);
    expect(panelOf(evt).hidden).toBe(true);
    expect(q(el, 'sovereignty-card-status')).not.toBeNull();
    expect(q(el, 'sovereignty-card-conflicts')).not.toBeNull();
    // 方向鍵（follow 模式：焦點移動即切換）
    ov.focus();
    ov.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    await fixture.whenStable();
    expect(evt.getAttribute('aria-selected')).toBe('true');
    expect(panelOf(evt).hidden).toBe(false);
    expect(panelOf(ov).hidden).toBe(true);
    expect(tabs).toEqual(['events']);
    expect(el.querySelectorAll('[data-testid="sovereignty-card-timeline-item"]').length).toBe(1);
    // 點擊切回概要
    ov.click();
    await fixture.whenStable();
    expect(ov.getAttribute('aria-selected')).toBe('true');
    expect(tabs).toEqual(['events', 'overview']);

    // 頁面保存的分頁：新建卡片時直接開在「事件」
    const f2 = TestBed.createComponent(SovereigntyCard);
    f2.componentRef.setInput('props', props());
    f2.componentRef.setInput('embedded', true);
    f2.componentRef.setInput('tab', 'events');
    await f2.whenStable();
    const e2 = f2.nativeElement as HTMLElement;
    expect(q(e2, 'sovereignty-card-tab-events')?.getAttribute('aria-selected')).toBe('true');
  });

  it('有註記時在概要顯示（依語言，缺則用另一語言）', async () => {
    const { el } = await render(props({ note: { 'zh-Hant': 'OHM 沒有分區幾何，這裡簡化。', en: '' } }), 'en');
    expect(q(el, 'sovereignty-card-note')?.textContent).toContain('簡化');
    const r2 = await render(props());
    expect(q(r2.el, 'sovereignty-card-note')).toBeNull();
  });

  it('佔領區：性質顯示「德國佔領（非主權）」、控制程度、依據事件；依據沒有出處＝待查證', async () => {
    const o = { id: 'o', occupierRegimeId: 'de', occupierSlug: 'deutsches-reich', controlKind: 'civil_administration', coOccupied: false,
      validPeriod: { start: '1941-09-01', end: null }, basisEvent: ev('pending'), verification: 'pending', note: { 'zh-Hant': '帝國專員轄區。', en: '' } };
    const { el } = await render(props({ layerStatus: 'not_sovereign', regimeSlug: 'reichskommissariat-ukraine', occupation: o }));
    expect(q(el, 'sovereignty-card-status')?.textContent?.trim()).toBe('德國佔領（非主權）');
    expect(q(el, 'sovereignty-card-occupation')?.textContent).toContain('民政管理');
    expect(q(el, 'sovereignty-card-occupation')?.textContent).toContain('帝國專員轄區');
    expect(q(el, 'sovereignty-card-occupation-basis')?.querySelector('[data-testid="sovereignty-card-occupation-pending"]')?.textContent).toBe('待查證');
    expect(q(el, 'sovereignty-card-co-occupied')).toBeNull();
  });

  it('併入＝「德國併入（非主權）」；共同佔領標主要佔領方並註記；英文', async () => {
    const o = { id: 'o', occupierRegimeId: 'it', occupierSlug: 'kingdom-of-italy', controlKind: 'military_administration', coOccupied: true,
      validPeriod: { start: '1941-04-30', end: '1943-09-08' }, basisEvent: null, verification: 'pending', note: null };
    const { el } = await render(props({ layerStatus: 'not_sovereign', occupation: o }));
    expect(q(el, 'sovereignty-card-status')?.textContent?.trim()).toBe('義大利佔領（非主權）');
    expect(q(el, 'sovereignty-card-co-occupied')?.textContent).toContain('主要佔領方');
    expect(q(el, 'sovereignty-card-occupation-basis')?.textContent).toContain('待查證');
    const a = await render(props({ layerStatus: 'not_sovereign', occupation: { ...o, occupierSlug: 'deutsches-reich', controlKind: 'annexed', coOccupied: false } }));
    expect(q(a.el, 'sovereignty-card-status')?.textContent?.trim()).toBe('德國併入（非主權）');
    const en = await render(props({ layerStatus: 'not_sovereign', occupation: { ...o, occupierSlug: 'deutsches-reich' } }), 'en');
    expect(q(en.el, 'sovereignty-card-status')?.textContent?.trim()).toBe('German occupation (not sovereign)');
  });

  it('概要顯示首都名稱（依語言）與出處文字', async () => {
    const cap = {
      recordId: 'cap1', regimeId: 'g1', regimeSlug: 'deutsches-reich',
      cityName: { 'zh-Hant': '柏林', en: 'Berlin' },
      location: { type: 'Point' as const, coordinates: [13.4, 52.5] as [number, number] },
      validPeriod: { start: '1933-01-30', end: null },
      sourceRef: 'Wikipedia: Berlin',
    };
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('capital', cap);
    fixture.componentRef.setInput('lang', 'zh-Hant');
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    expect(q(el, 'sovereignty-card-capital-name')?.textContent?.trim()).toBe('柏林');
    expect(q(el, 'sovereignty-card-capital-source')?.textContent?.trim()).toBe('Wikipedia: Berlin');
    expect(q(el, 'sovereignty-card-capital-none')).toBeNull();
    // 英文介面
    fixture.componentRef.setInput('lang', 'en');
    await fixture.whenStable();
    expect(q(el, 'sovereignty-card-capital-name')?.textContent?.trim()).toBe('Berlin');
  });

  it('首都無資料時概要顯示「無資料」', async () => {
    const { el } = await render(props());
    // capital 預設 null
    expect(q(el, 'sovereignty-card-capital-none')?.textContent?.trim()).toBe('無資料');
    expect(q(el, 'sovereignty-card-capital-name')).toBeNull();
  });

  it('面板內有「領導人」分頁（data-testid 與文案）', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    const tab = q(el, 'sovereignty-card-tab-leaders') as HTMLElement;
    expect(tab).not.toBeNull();
    expect(tab.textContent?.trim()).toBe('領導人');
    expect(tab.getAttribute('role')).toBe('tab');
  });

  it('領導人分頁：依角色排序（國家元首在前）、顯示姓名與職銜、出處；未驗證顯示「待查證」', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('leaders', [
      { recordId: 'l2', regimeId: 'g1', regimeSlug: 'deutsches-reich', name: 'Adolf Hitler', nameZh: '阿道夫·希特勒', role: 'head_of_government', title: '德意志國總理', validPeriod: { start: '1933-01-30', end: null }, source: 'Wikipedia: Adolf Hitler', sourceUrl: null, verified: true },
      { recordId: 'l1', regimeId: 'g1', regimeSlug: 'deutsches-reich', name: 'Adolf Hitler', nameZh: '阿道夫·希特勒', role: 'head_of_state', title: '元首兼帝國總理', validPeriod: { start: '1934-08-02', end: null }, source: 'BGBL 1934', sourceUrl: null, verified: false },
    ]);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    const leaderTab = q(el, 'sovereignty-card-tab-leaders') as HTMLElement;
    leaderTab.click();
    await fixture.whenStable();
    const panel = q(el, 'sovereignty-card-panel-leaders')!;
    expect(panel).not.toBeNull();
    const items = [...panel.querySelectorAll('[data-testid="sovereignty-card-leader"]')];
    expect(items.length).toBe(2);
    // 排序：head_of_state 在前
    expect(items[0].querySelector('[data-role]')?.getAttribute('data-role')).toBe('head_of_state');
    expect(items[1].querySelector('[data-role]')?.getAttribute('data-role')).toBe('head_of_government');
    // 姓名（zh 優先）
    expect(items[0].querySelector('[data-testid="sovereignty-card-leader-name"]')?.textContent?.trim()).toBe('阿道夫·希特勒');
    // 職銜
    expect(items[0].querySelector('[data-testid="sovereignty-card-leader-title"]')?.textContent?.trim()).toBe('元首兼帝國總理');
    // 未驗證顯示「待查證」
    expect(items[0].querySelector('[data-testid="sovereignty-card-leader-unverified"]')?.textContent?.trim()).toBe('待查證');
    expect(items[1].querySelector('[data-testid="sovereignty-card-leader-unverified"]')).toBeNull();
    // 出處
    expect(items[0].querySelector('[data-testid="sovereignty-card-leader-source"]')?.textContent?.trim()).toBe('BGBL 1934');
  });

  it('同一人多段任期獨立展開：點第一筆只展開第一筆，第二筆 aria-expanded 仍為 false', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    // 同一個 personId（'p-hitler'），但兩筆不同 recordId（任期）
    const activeBio: import('../../core/api/world-line-api').LeaderBioSummary = {
      id: 'p-hitler', name: 'Adolf Hitler', nameZh: null,
      birthDate: null, birthDatePrecision: null, deathDate: null, summary: null, retractedAt: null,
    };
    fixture.componentRef.setInput('leaders', [
      { recordId: 'l-hog', regimeId: 'g1', regimeSlug: 'deutsches-reich', name: 'Adolf Hitler', nameZh: '阿道夫·希特勒',
        role: 'head_of_government', title: '德意志國總理', validPeriod: { start: '1933-01-30', end: '1934-08-02' },
        source: '', sourceUrl: null, verified: true, personId: 'p-hitler', bio: activeBio },
      { recordId: 'l-hos', regimeId: 'g1', regimeSlug: 'deutsches-reich', name: 'Adolf Hitler', nameZh: '阿道夫·希特勒',
        role: 'head_of_state', title: '元首兼帝國總理', validPeriod: { start: '1934-08-02', end: null },
        source: '', sourceUrl: null, verified: true, personId: 'p-hitler', bio: activeBio },
    ] satisfies import('../../core/api/world-line-api').LeaderRecord[]);
    // loadBio：永遠等待（只驗展開狀態，不需要資料回傳）
    fixture.componentRef.setInput('loadBio', () => new Promise(() => undefined));
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();
    const items = [...el.querySelectorAll('[data-testid="sovereignty-card-leader"]')];
    expect(items.length).toBe(2);
    const btn0 = items[0].querySelector('[data-testid="sovereignty-card-leader-name"]') as HTMLButtonElement;
    const btn1 = items[1].querySelector('[data-testid="sovereignty-card-leader-name"]') as HTMLButtonElement;
    expect(btn0.getAttribute('aria-expanded')).toBe('false');
    expect(btn1.getAttribute('aria-expanded')).toBe('false');
    btn0.click();
    await fixture.whenStable();
    expect(btn0.getAttribute('aria-expanded')).toBe('true');
    expect(btn1.getAttribute('aria-expanded')).toBe('false');
  });

  it('領導人分頁空態：顯示「無資料」文案', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('leaders', []);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();
    const panel = q(el, 'sovereignty-card-panel-leaders')!;
    expect(panel.querySelector('[data-testid="sovereignty-card-leader"]')).toBeNull();
    expect(panel.textContent).toContain('無資料');
  });

  it('控制區區塊：evidence、有效期間、陣營、補充（預設收合，僅限 currentDate 以前）、爭議、來源', async () => {
    const czProps = {
      versionId: 'v1', controllerRegimeId: 'g1', controlType: 'occupation',
      validPeriod: { start: '1939-09-01', end: '1945-05-08', startUncertainty: null, endUncertainty: null },
      theaterCode: 'europe',
      controllerAlignment: {
        camp: 'axis',
        validPeriod: { start: '1939-09-01', end: null }, citations: [
          { sourceId: 's1', sourceTitle: 'FRUS 1939', publisher: 'GPO', licenseCode: 'us_federal_pd', locator: 'p. 1', role: 'primary', evidenceNote: '' },
        ],
      },
      controllerSupplements: [
        { eventId: 'sup1', occurred: { start: '1940-06-22', end: null }, summary: { 'zh-Hant': '法國停戰', en: 'Fall of France' }, citations: [] },
        { eventId: 'sup2', occurred: { start: '1946-01-01', end: null }, summary: { 'zh-Hant': '未來事件（不顯示）', en: 'Future' }, citations: [] },
      ],
      isDisputed: true,
      citations: [{ sourceId: 's2', sourceTitle: 'Source', publisher: 'P', licenseCode: 'cc0', locator: 'p.1', role: 'primary', evidenceNote: '' }],
    } as unknown as import('../../core/api/api-types').ControlFeatureProperties;

    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('currentDate', '1941-06-22');
    fixture.componentRef.setInput('controlZone', { props: czProps, evidence: 'attested', theater: { attestingSnapshot: { asOf: '1941-06-22' } } });
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;

    // 史料狀態：已查證
    expect(q(el, 'feature-card-evidence')?.textContent).toContain('已查證');
    // 陣營
    expect(q(el, 'feature-card-camp')?.getAttribute('data-camp')).not.toBe('unassigned');
    // 依據
    expect(q(el, 'feature-card-camp-basis')?.textContent).toContain('FRUS 1939');
    // 補充：sup2 的日期 1946 > currentDate 1941，不顯示；sup1 顯示
    const supplements = q(el, 'feature-card-supplements');
    expect(supplements).not.toBeNull();
    const supItems = [...el.querySelectorAll('[data-testid="feature-card-supplement"]')];
    expect(supItems.length).toBe(1);
    expect(supItems[0].textContent).toContain('法國停戰');
    // 爭議
    expect(el.textContent).toContain('爭議領土');
    // 補充預設收合（details 元素）
    const details = supplements?.querySelector('details');
    expect(details).not.toBeNull();
    expect(details?.hasAttribute('open')).toBe(false);
  });

  // ── 生平展開測試 ─────────────────────────────────────────────────────────────

  const mockBio = (over: Partial<LeaderBio> = {}): LeaderBio => ({
    id: 'p1', name: 'Adolf Hitler', nameZh: '阿道夫·希特勒',
    birthDate: '1889-04-20', birthDatePrecision: 'day',
    deathDate: '1945-04-30',
    birthPlace: { 'zh-Hant': '布勞瑙', en: 'Braunau am Inn' },
    party: { 'zh-Hant': '納粹黨', en: 'Nazi Party' },
    summary: { 'zh-Hant': '德國獨裁者。', en: 'German dictator.' },
    fieldSources: { birthDate: { source: 'Wikipedia', url: 'https://example.com' } },
    isTest: false, ...over,
  });

  const mockBioSummary = (over: Partial<LeaderBioSummary> = {}): LeaderBioSummary => ({
    id: 'p1', name: 'Adolf Hitler', nameZh: null,
    birthDate: null, birthDatePrecision: null, deathDate: null, summary: null,
    retractedAt: null, ...over,
  });

  const leaderWithPerson = (personId: string | null = 'p1', bio: LeaderBioSummary | null = personId ? mockBioSummary() : null) => ({
    recordId: 'l1', regimeId: 'g1', regimeSlug: 'deutsches-reich',
    name: 'Adolf Hitler', nameZh: '阿道夫·希特勒',
    role: 'head_of_state' as const, title: '元首兼帝國總理',
    validPeriod: { start: '1934-08-02', end: null },
    source: 'BGBL 1934', sourceUrl: null, verified: true, personId, bio,
  });

  it('有 personId 且 loadBio 設定時，名字為可點按鈕（aria-expanded=false）', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('leaders', [leaderWithPerson('p1')]);
    fixture.componentRef.setInput('loadBio', () => Promise.resolve(mockBio()));
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();
    const nameEl = q(el, 'sovereignty-card-leader-name')!;
    expect(nameEl.tagName).toBe('BUTTON');
    expect(nameEl.getAttribute('aria-expanded')).toBe('false');
    expect(nameEl.textContent?.trim()).toBe('阿道夫·希特勒');
  });

  it('沒有 personId 或沒有 loadBio 時，名字為純文字 div', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('leaders', [leaderWithPerson(null)]);
    fixture.componentRef.setInput('loadBio', () => Promise.resolve(mockBio()));
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();
    const nameEl = q(el, 'sovereignty-card-leader-name')!;
    expect(nameEl.tagName).toBe('DIV');
    expect(nameEl.getAttribute('aria-expanded')).toBeNull();

    // loadBio 為 null 時即使有 personId 也是純文字
    const f2 = TestBed.createComponent(SovereigntyCard);
    f2.componentRef.setInput('props', props());
    f2.componentRef.setInput('embedded', true);
    f2.componentRef.setInput('leaders', [leaderWithPerson('p1')]);
    // loadBio 不設定，預設 null
    await f2.whenStable();
    const el2 = f2.nativeElement as HTMLElement;
    (q(el2, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await f2.whenStable();
    expect(q(el2, 'sovereignty-card-leader-name')?.tagName).toBe('DIV');
  });

  it('點擊有 personId 的按鈕 → 展開 bio 區塊（aria-expanded=true）；再點 → 收合', async () => {
    let resolveBio!: (b: LeaderBio) => void;
    const bioPromise = new Promise<LeaderBio>((r) => (resolveBio = r));
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('leaders', [leaderWithPerson('p1')]);
    fixture.componentRef.setInput('loadBio', () => bioPromise);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();

    const btn = q(el, 'sovereignty-card-leader-name') as HTMLButtonElement;
    // 點擊展開（loading 狀態）
    btn.click();
    await fixture.whenStable();
    expect(btn.getAttribute('aria-expanded')).toBe('true');
    expect(q(el, 'sovereignty-card-leader-bio')).not.toBeNull();

    // 解析 bio 資料
    resolveBio(mockBio());
    await fixture.whenStable();
    expect(q(el, 'sovereignty-card-leader-bio')).not.toBeNull();

    // 再點收合
    btn.click();
    await fixture.whenStable();
    expect(btn.getAttribute('aria-expanded')).toBe('false');
    expect(q(el, 'sovereignty-card-leader-bio')).toBeNull();
  });

  it('生平資料載入後顯示完整內容：生卒日期、出生地、黨派、簡介；isTest 顯示測試資料徽章', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('leaders', [leaderWithPerson('p1')]);
    fixture.componentRef.setInput('loadBio', () => Promise.resolve(mockBio({ isTest: true })));
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();
    (q(el, 'sovereignty-card-leader-name') as HTMLButtonElement).click();
    await fixture.whenStable();
    const bio = q(el, 'sovereignty-card-leader-bio')!;
    expect(bio).not.toBeNull();
    expect(bio.textContent).toContain('1889-04-20');
    expect(bio.textContent).toContain('1945-04-30');
    expect(bio.textContent).toContain('布勞瑙');
    expect(bio.textContent).toContain('納粹黨');
    expect(bio.textContent).toContain('德國獨裁者');
    // isTest 徽章
    expect(q(el, 'sovereignty-card-leader-bio-test')?.textContent?.trim()).toBe('測試資料');
    // 出處連結
    const srcLink = bio.querySelector('a[target="_blank"]') as HTMLAnchorElement;
    expect(srcLink).not.toBeNull();
    expect(srcLink.getAttribute('rel')).toBe('noopener');
    expect(srcLink.getAttribute('href')).toBe('https://example.com');
  });

  it('hasBio：personId 有但 bio 為 null → 名字為純文字（不可點）', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('leaders', [leaderWithPerson('p1', null)]);
    fixture.componentRef.setInput('loadBio', () => Promise.resolve(mockBio()));
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();
    const nameEl = q(el, 'sovereignty-card-leader-name')!;
    expect(nameEl.tagName).toBe('DIV');
    expect(nameEl.getAttribute('aria-expanded')).toBeNull();
  });

  it('hasBio：bio 帶 retractedAt → 名字為純文字（不可點）', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('leaders', [leaderWithPerson('p1', mockBioSummary({ retractedAt: '2026-01-01T00:00:00Z' }))]);
    fixture.componentRef.setInput('loadBio', () => Promise.resolve(mockBio()));
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();
    const nameEl = q(el, 'sovereignty-card-leader-name')!;
    expect(nameEl.tagName).toBe('DIV');
    expect(nameEl.getAttribute('aria-expanded')).toBeNull();
  });

  it('hasBio：bio 非 null 且 retractedAt 為 null → 名字為可點按鈕', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('leaders', [leaderWithPerson('p1', mockBioSummary())]);
    fixture.componentRef.setInput('loadBio', () => Promise.resolve(mockBio()));
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();
    const nameEl = q(el, 'sovereignty-card-leader-name')!;
    expect(nameEl.tagName).toBe('BUTTON');
    expect(nameEl.getAttribute('aria-expanded')).toBe('false');
  });

  it('hasBio：bio 摘要沒有 retractedAt 欄位（後端已過濾，欄位缺失）→ 視為活躍，名字為可點按鈕', async () => {
    const bioNoRetracted = {
      id: 'p1', name: 'Adolf Hitler', nameZh: null,
      birthDate: null, birthDatePrecision: null, deathDate: null, summary: null,
      // retractedAt 欄位刻意省略，模擬 GET /leaders 實際回應
    } as LeaderBioSummary;
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('leaders', [leaderWithPerson('p1', bioNoRetracted)]);
    fixture.componentRef.setInput('loadBio', () => Promise.resolve(mockBio()));
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();
    const nameEl = q(el, 'sovereignty-card-leader-name')!;
    expect(nameEl.tagName).toBe('BUTTON');
    expect(nameEl.getAttribute('aria-expanded')).toBe('false');
  });

  it('生平欄位缺失：birthDate null 不出現「出生」列；party 空物件不出現「政黨」列', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('leaders', [leaderWithPerson('p1')]);
    fixture.componentRef.setInput('loadBio', () => Promise.resolve(mockBio({
      birthDate: null,
      party: {},
    })));
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();
    (q(el, 'sovereignty-card-leader-name') as HTMLButtonElement).click();
    await fixture.whenStable();
    const bio = q(el, 'sovereignty-card-leader-bio')!;
    expect(bio).not.toBeNull();
    // birthDate null → 不顯示出生日期（1889-04-20）
    expect(bio.textContent).not.toContain('1889-04-20');
    // party 空物件 → localizedBioField 回傳 '' → 不顯示「政黨」標籤
    expect(bio.textContent).not.toContain('政黨');
    // 其他有值的欄位仍顯示（去世日期）
    expect(bio.textContent).toContain('1945-04-30');
  });

  it('生平全部欄位為空時顯示占位文字「尚無生平資料」', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('leaders', [leaderWithPerson('p1')]);
    fixture.componentRef.setInput('loadBio', () => Promise.resolve(mockBio({
      birthDate: null, deathDate: null,
      birthPlace: null, party: null, summary: null,
      fieldSources: null,
    })));
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();
    (q(el, 'sovereignty-card-leader-name') as HTMLButtonElement).click();
    await fixture.whenStable();
    const bio = q(el, 'sovereignty-card-leader-bio')!;
    expect(bio).not.toBeNull();
    expect(q(el, 'sovereignty-card-leader-bio-empty')?.textContent?.trim()).toBe('尚無生平資料');
    // 不應有空的 dl
    expect(bio.querySelector('dl')).toBeNull();
  });

  it('英文介面 bio：出生地、黨派、簡介用英文；isTest 顯示 Test data', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('lang', 'en');
    fixture.componentRef.setInput('leaders', [leaderWithPerson('p1')]);
    fixture.componentRef.setInput('loadBio', () => Promise.resolve(mockBio({ isTest: true })));
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();
    (q(el, 'sovereignty-card-leader-name') as HTMLButtonElement).click();
    await fixture.whenStable();
    const bio = q(el, 'sovereignty-card-leader-bio')!;
    expect(bio.textContent).toContain('Braunau am Inn');
    expect(bio.textContent).toContain('Nazi Party');
    expect(bio.textContent).toContain('German dictator');
    expect(q(el, 'sovereignty-card-leader-bio-test')?.textContent?.trim()).toBe('Test data');
  });

  it('領導人分頁英文介面：角色標籤英文、名稱用 name 欄位、unverified 顯示 Unverified', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('lang', 'en');
    fixture.componentRef.setInput('leaders', [
      { recordId: 'l1', regimeId: 'g1', regimeSlug: 'deutsches-reich', name: 'Adolf Hitler', nameZh: '阿道夫·希特勒', role: 'head_of_state', title: 'Führer und Reichskanzler', validPeriod: { start: '1934-08-02', end: null }, source: 'BGBL 1934', sourceUrl: null, verified: false },
    ]);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();
    const panel = q(el, 'sovereignty-card-panel-leaders')!;
    const item = panel.querySelector('[data-testid="sovereignty-card-leader"]')!;
    expect(item.querySelector('[data-role]')?.textContent?.trim()).toBe('Head of State');
    expect(item.querySelector('[data-testid="sovereignty-card-leader-name"]')?.textContent?.trim()).toBe('Adolf Hitler');
    expect(item.querySelector('[data-testid="sovereignty-card-leader-unverified"]')?.textContent?.trim()).toBe('Unverified');
  });

  it('事件卡片（§10-1）：同月份一組、月份標頭；摺疊只顯示日期／標題／tag，展開顯示出處與「在地圖上看」；點卡片選取並跳日期；戰役 tag', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('tab', 'events');
    const tev = (id: string, start: string, kind = 'treaty') => ({ ...ev('verified'), id, eventKind: kind, occurred: { start, end: start }, roles: ['belligerent'] });
    fixture.componentRef.setInput('regimeEvents', [tev('a', '1940-05-10', 'battle'), tev('b', '1940-05-28'), tev('c', '1940-06-22')]);
    fixture.componentRef.setInput('eventsStatus', 'ok');
    fixture.componentRef.setInput('currentDate', '1940-06-01');
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    const groups = [...el.querySelectorAll('[data-testid="sovereignty-card-timeline-group"]')];
    expect(groups.map((g) => g.getAttribute('data-month'))).toEqual(['1940-05', '1940-06']);
    expect(groups[0].querySelector('[data-testid="sovereignty-card-timeline-month"]')?.textContent?.trim()).toBe('1940年5月');
    const items = () => [...el.querySelectorAll<HTMLElement>('[data-testid="sovereignty-card-timeline-item"]')];
    expect(items()[0].querySelector('[data-testid="sovereignty-card-timeline-battle"]')).not.toBeNull();
    expect(items()[1].querySelector('[data-testid="sovereignty-card-timeline-battle"]')).toBeNull();
    expect(items()[0].querySelector('[data-testid="sovereignty-card-timeline-detail"]')).toBeNull();
    let jumped = '';
    fixture.componentInstance.eventJump.subscribe((d) => (jumped = d));
    items()[2].click();
    await fixture.whenStable();
    expect(jumped).toBe('1940-06-22');
    expect(items()[2].getAttribute('data-selected')).toBe('true');
    (items()[1].querySelector('[data-testid="sovereignty-card-timeline-toggle"]') as HTMLButtonElement).click();
    await fixture.whenStable();
    expect(items()[1].getAttribute('data-expanded')).toBe('true');
    expect(items()[1].querySelector('[data-testid="sovereignty-card-timeline-detail-citation"], [data-testid="sovereignty-card-timeline-detail-no-citation"]')).not.toBeNull();
    (items()[1].querySelector('[data-testid="sovereignty-card-timeline-map"]') as HTMLButtonElement).click();
    expect(jumped).toBe('1940-05-28');
  });
});
