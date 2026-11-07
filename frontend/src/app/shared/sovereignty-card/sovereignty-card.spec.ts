import { TestBed } from '@angular/core/testing';
import type { SovereigntyFeatureProperties } from '../../core/api/api-types';
import type { LeaderBioSummary } from '../../core/api/world-line-api';
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
    expect(items.map((i) => i.getAttribute('data-when'))).toEqual(['past', 'past', 'future']);
    // T2：目前日期標線插在第一個晚於目前日期的事件前；T1：未發生的事件 60% 透明
    expect(items[2].compareDocumentPosition(q(el, 'sovereignty-card-timeline-now')!) & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy();
    expect(items[1].compareDocumentPosition(q(el, 'sovereignty-card-timeline-now')!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(q(el, 'sovereignty-card-timeline-now')?.textContent).toContain('1939-10-23');
    expect(items[2].classList.contains('opacity-60')).toBe(true);
    expect(items[0].classList.contains('opacity-60')).toBe(false);
    expect(items[1].textContent).toContain('交戰方');
    expect(items[1].textContent).toContain('開戰');
    expect(items[2].querySelector('[data-testid="sovereignty-card-timeline-pending"]')?.textContent).toBe('待考證');
    expect(items[2].getAttribute('data-pending')).toBe('true');
    (items[0].querySelector('[data-testid="sovereignty-card-timeline-card"]') as HTMLElement).click();
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
    const items = () => [...el.querySelectorAll('[data-testid="sovereignty-card-timeline-item"]')];
    const card = (i: number) => items()[i].querySelector('[data-testid="sovereignty-card-timeline-card"]') as HTMLElement;
    card(0).click();
    await fixture.whenStable();
    const add = items()[0].querySelector('[data-testid="sovereignty-card-timeline-addition"]');
    expect(add?.getAttribute('data-role')).toBe('belligerent');
    expect(add?.textContent).toContain('事後追加・交戰方');
    expect(add?.textContent).toContain('2026-10-31');
    expect(add?.textContent).toContain('美軍為火炬行動登陸主力');
    card(1).click();
    await fixture.whenStable();
    expect(items()[0].querySelector('[data-testid="sovereignty-card-timeline-detail"]')).toBeNull(); // 同時只有一張被選取
    expect(items()[1].querySelector('[data-testid="sovereignty-card-timeline-detail"]')).not.toBeNull();
    expect(items()[1].querySelector('[data-testid="sovereignty-card-timeline-addition"]')).toBeNull();
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

  it('面板內有「人物」分頁（Tai 2026-11-07 由「領導人」改名；data-testid 不變）', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    const tab = q(el, 'sovereignty-card-tab-leaders') as HTMLElement;
    expect(tab).not.toBeNull();
    expect(tab.textContent?.trim()).toBe('人物');
    expect(tab.getAttribute('role')).toBe('tab');
  });

  it('人物分頁：卡片依角色排序（國家元首在前）、姓名、職位、任期（迄日顯示最後在任日）、來源預設收合', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('leaders', [
      { recordId: 'l2', regimeId: 'g1', regimeSlug: 'deutsches-reich', name: 'Adolf Hitler', nameZh: '阿道夫·希特勒', role: 'head_of_government', title: 'Reichskanzler', validPeriod: { start: '1933-01-30', end: '1945-04-30' }, source: 'Berliner Tageblatt', sourceUrl: null, verified: true, personId: null, bio: null },
      { recordId: 'l1', regimeId: 'g1', regimeSlug: 'deutsches-reich', name: 'Adolf Hitler', nameZh: '阿道夫·希特勒', role: 'head_of_state', title: 'Führer und Reichskanzler', validPeriod: { start: '1934-08-02', end: null }, source: '', sourceUrl: null, verified: true, personId: null, bio: null },
    ]);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();
    const cards = [...el.querySelectorAll('[data-testid="person-card"]')];
    expect(cards.length).toBe(2);
    expect(cards[0].querySelector('[data-testid="person-card-role"]')?.getAttribute('data-role')).toBe('head_of_state');
    expect(cards[1].querySelector('[data-testid="person-card-name"]')?.textContent?.trim()).toBe('阿道夫·希特勒');
    expect(cards[1].querySelector('[data-testid="person-card-title"]')?.textContent?.trim()).toBe('Reichskanzler');
    expect(cards[1].querySelector('[data-testid="person-card-term"]')?.textContent).toContain('1933-01-30 – 1945-04-29');
    expect(cards[0].querySelector('[data-testid="person-card-term"]')?.textContent).toContain('迄今不明');
    // 來源：有出處 → 收合按鈕（aria-expanded=false，內容 hidden）；沒有 → 靜態「待補來源」
    const toggle = cards[1].querySelector('[data-testid="source-toggle"]') as HTMLButtonElement;
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    expect((cards[1].querySelector('[data-testid="source-panel"]') as HTMLElement).hidden).toBe(true);
    toggle.click();
    await fixture.whenStable();
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    expect(cards[0].querySelector('[data-testid="source-toggle"]')).toBeNull();
    expect(cards[0].querySelector('[data-testid="source-pending"]')?.textContent?.trim()).toBe('待補來源');
    // 沒有生平 → 沒有「查看詳情」；沒有照片 → 中性佔位
    expect(cards[0].querySelector('[data-testid="person-card-details"]')).toBeNull();
    expect(cards[0].querySelector('[data-testid="person-card-placeholder"]')).not.toBeNull();
  });

  it('人物分頁空態：顯示「無資料」文案', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('leaders', []);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();
    const panel = q(el, 'sovereignty-card-panel-leaders')!;
    expect(panel.querySelector('[data-testid="person-card"]')).toBeNull();
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

  // ── 人物卡：查看詳情、照片 ─────────────────────────────────────────────────────

  const bioSummary = (over: Partial<LeaderBioSummary> = {}): LeaderBioSummary => ({
    id: 'p1', name: 'Adolf Hitler', nameZh: null, birthDate: null, birthDatePrecision: null, deathDate: null, summary: null, retractedAt: null, ...over,
  });
  const leaderWithPerson = (personId: string | null = 'p1', bio: LeaderBioSummary | null = personId ? bioSummary() : null) => ({
    recordId: 'l1', regimeId: 'g1', regimeSlug: 'deutsches-reich', name: 'Adolf Hitler', nameZh: '阿道夫·希特勒',
    role: 'head_of_state' as const, title: 'Führer', validPeriod: { start: '1934-08-02', end: null },
    source: 'RGBl. 1934', sourceUrl: null, verified: true, personId, bio,
  });
  const renderLeaders = async (leaders: ReturnType<typeof leaderWithPerson>[], lang: 'zh-Hant' | 'en' = 'zh-Hant') => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('lang', lang);
    fixture.componentRef.setInput('leaders', leaders);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    (q(el, 'sovereignty-card-tab-leaders') as HTMLElement).click();
    await fixture.whenStable();
    return { fixture, el };
  };

  it('有效生平 → 「查看詳情」按鈕，點了送出 personOpen（含觸發元素）', async () => {
    const { fixture, el } = await renderLeaders([leaderWithPerson('p1')]);
    const opened: { personId: string; trigger: HTMLElement }[] = [];
    fixture.componentInstance.personOpen.subscribe((e) => opened.push(e));
    const btn = q(el, 'person-card-details') as HTMLButtonElement;
    expect(btn.getAttribute('data-person-trigger')).toBe('p1');
    btn.click();
    expect(opened.length).toBe(1);
    expect(opened[0].personId).toBe('p1');
    expect(opened[0].trigger).toBe(btn);
  });

  it('同一人多段任期：兩張卡片各自有「查看詳情」，都指向同一份生平', async () => {
    const a = leaderWithPerson('p1');
    const b = { ...leaderWithPerson('p1'), recordId: 'l2', role: 'head_of_government' as 'head_of_state', title: 'Reichskanzler' };
    const { el } = await renderLeaders([a, b]);
    const btns = [...el.querySelectorAll('[data-testid="person-card-details"]')];
    expect(btns.length).toBe(2);
    expect(btns.map((x) => x.getAttribute('data-person-trigger'))).toEqual(['p1', 'p1']);
  });

  it('沒有生平、生平為 null、生平已撤回 → 不顯示「查看詳情」', async () => {
    for (const l of [leaderWithPerson(null), leaderWithPerson('p1', null), leaderWithPerson('p1', bioSummary({ retractedAt: '2026-11-01T00:00:00Z' }))]) {
      const { el } = await renderLeaders([l]);
      expect(q(el, 'person-card-details')).toBeNull();
    }
  });

  it('照片：授權在允許清單才顯示；不在清單（或沒有）→ 中性佔位', async () => {
    const portrait = { url: 'https://upload.wikimedia.org/a.jpg', sourceUrl: 'https://commons.wikimedia.org/wiki/File:a.jpg', author: null, licenseCode: 'pd_expired', licenseUrl: null, attribution: 'Unknown author', retrievedOn: '2026-11-07' };
    let r = await renderLeaders([leaderWithPerson('p1', bioSummary({ portrait }))]);
    expect((q(r.el, 'person-card-photo') as HTMLImageElement).getAttribute('src')).toBe(portrait.url);
    r = await renderLeaders([leaderWithPerson('p1', bioSummary({ portrait: { ...portrait, licenseCode: 'cc_by_nc' } }))]);
    expect(q(r.el, 'person-card-photo')).toBeNull();
    expect(q(r.el, 'person-card-placeholder')).not.toBeNull();
  });

  it('英文介面：分頁 People、角色英文、姓名用 name', async () => {
    const { el } = await renderLeaders([leaderWithPerson('p1')], 'en');
    expect(q(el, 'sovereignty-card-tab-leaders')?.textContent?.trim()).toBe('People');
    expect(q(el, 'person-card-name')?.textContent?.trim()).toBe('Adolf Hitler');
    expect(q(el, 'person-card-role')?.textContent?.trim()).toBe('Head of State');
    expect(q(el, 'person-card-details')?.textContent?.trim()).toBe('View details');
  });

  it('事件卡片（§10 v2）：同月份一組、月份標頭；不收合（無展開按鈕）；選取才顯示出處與「在地圖上看」且不重複標題日期；再點一次收起；節點與戰役圖示；目前日期標線', async () => {
    const fixture = TestBed.createComponent(SovereigntyCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('embedded', true);
    fixture.componentRef.setInput('tab', 'events');
    const tev = (id: string, start: string, kind = 'treaty') => ({ ...ev('verified'), id, eventKind: kind, occurred: { start, end: start }, roles: ['belligerent'] });
    fixture.componentRef.setInput('regimeEvents', [tev('a', '1940-05-10', 'battle'), tev('b', '1940-05-28'), { ...tev('c', '1940-06-22'), verification: 'pending' }]);
    fixture.componentRef.setInput('eventsStatus', 'ok');
    fixture.componentRef.setInput('currentDate', '1940-06-01');
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    const groups = [...el.querySelectorAll('[data-testid="sovereignty-card-timeline-group"]')];
    expect(groups.map((g) => g.getAttribute('data-month'))).toEqual(['1940-05', '1940-06']);
    expect(groups[0].querySelector('[data-testid="sovereignty-card-timeline-month"]')?.textContent?.trim()).toBe('1940年5月');
    const items = () => [...el.querySelectorAll<HTMLElement>('[data-testid="sovereignty-card-timeline-item"]')];
    const card = (i: number) => items()[i].querySelector<HTMLElement>('[data-testid="sovereignty-card-timeline-card"]')!;
    expect(el.querySelector('[data-testid="sovereignty-card-timeline-toggle"]')).toBeNull();
    expect(q(el, 'sovereignty-card-timeline-rail')).not.toBeNull();
    expect(items().map((i) => i.querySelector('[data-testid="sovereignty-card-timeline-node"]')?.getAttribute('data-kind'))).toEqual(['battle', 'verified', 'pending']);
    expect(items().map((i) => i.querySelector('[data-testid="sovereignty-card-timeline-status"]')?.textContent?.trim())).toEqual(['⚔', '✓', '?']);
    expect(groups[1].previousElementSibling?.getAttribute('data-testid')).toBe('sovereignty-card-timeline-now'); // 落在月份交界時畫在月份標頭前
    expect(items()[0].querySelector('[data-testid="sovereignty-card-timeline-battle"]')).not.toBeNull();
    expect(items()[0].querySelector('[data-testid="sovereignty-card-timeline-detail"]')).toBeNull();
    expect(el.querySelector('[data-testid="sovereignty-card-timeline-detail-citation"], [data-testid="sovereignty-card-timeline-detail-no-citation"]')).toBeNull(); // C1
    let jumped = '';
    fixture.componentInstance.eventJump.subscribe((d) => (jumped = d));
    card(1).click();
    await fixture.whenStable();
    expect(jumped).toBe('1940-05-28');
    expect(items()[1].getAttribute('data-selected')).toBe('true');
    expect(items()[1].querySelector('[data-testid="sovereignty-card-timeline-detail-citation"], [data-testid="sovereignty-card-timeline-detail-no-citation"]')).not.toBeNull();
    expect(items()[1].querySelector('[data-testid="sovereignty-card-timeline-detail-event-name"]')).toBeNull(); // 不重複標題
    expect(items()[1].querySelector('[data-testid="sovereignty-card-timeline-detail-event-date"]')).toBeNull();
    jumped = '';
    (items()[1].querySelector('[data-testid="sovereignty-card-timeline-map"]') as HTMLButtonElement).click();
    expect(jumped).toBe('1940-05-28');
    card(1).click();
    await fixture.whenStable();
    expect(items()[1].getAttribute('data-selected')).toBeNull();
    expect(items()[1].querySelector('[data-testid="sovereignty-card-timeline-detail"]')).toBeNull();
  });
});
