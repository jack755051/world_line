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
});
