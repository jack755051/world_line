import { TestBed } from '@angular/core/testing';
import type { SovereigntyFeatureProperties } from '../../core/api/api-types';
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
    expect(items[2].querySelector('[data-testid="sovereignty-card-timeline-pending"]')?.textContent).toBe('待查證');
    (items[0].querySelector('[data-testid="sovereignty-card-timeline-jump"]') as HTMLButtonElement).click();
    expect(jumped).toBe('1938-03-13');
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
});
