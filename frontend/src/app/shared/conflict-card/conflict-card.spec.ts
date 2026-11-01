import { TestBed } from '@angular/core/testing';
import type { ConflictFeatureProperties } from '../../core/api/api-types';
import { ConflictCard } from './conflict-card';

const cite = { sourceId: 's', sourceTitle: 'Foreign Relations of the United States, Diplomatic Papers, 1939, General, Volume I', publisher: 'GPO', licenseCode: 'us_federal_pd', locator: 'Doc. 403, pp. 402–403', role: 'primary', evidenceNote: '但澤領事 9/1 電' };
const ev = (id: string, date: string, verification: 'verified' | 'pending', citations: unknown[] = []) => ({
  id, eventKind: 'war', occurred: { start: date, end: date }, summary: { 'zh-Hant': `事件 ${id}`, en: `Event ${id}` }, verification, citations,
});
const props = (over: Partial<Record<string, unknown>> = {}) => ({
  recordId: 'c1', regimeAId: 'a', regimeASlug: 'deutsches-reich', regimeBId: 'b', regimeBSlug: 'polish-republic',
  validPeriod: { start: '1939-09-01', end: '1939-10-07' },
  startEvent: ev('s1', '1939-09-01', 'verified', [cite]), endEvent: ev('e1', '1939-10-06', 'pending'),
  locationMethod: 'OHM 共同邊界最長一段的中點', note: null, ...over,
}) as unknown as ConflictFeatureProperties;

async function render(p: ConflictFeatureProperties) {
  const fixture = TestBed.createComponent(ConflictCard);
  fixture.componentRef.setInput('props', p);
  fixture.componentRef.setInput('nameA', '德意志國');
  fixture.componentRef.setInput('nameB', '波蘭共和國');
  await fixture.whenStable();
  return { fixture, el: fixture.nativeElement as HTMLElement };
}
const q = (el: HTMLElement, id: string) => el.querySelector(`[data-testid="${id}"]`);

describe('ConflictCard（衝突資訊卡）', () => {
  it('標題為雙方政權；開戰／停戰與政權卡同一結構（名稱 → 日期 → 徽章＋出處）', async () => {
    const { el } = await render(props());
    expect(q(el, 'conflict-card-title')?.textContent).toContain('德意志國 — 波蘭共和國');
    expect(q(el, 'conflict-card-period')?.textContent).toContain('1939-09-01 至 1939-10-06'); // 含停戰當日，不顯示 API 的開區間終點
    for (const key of ['start', 'end']) {
      const ref = q(el, 'conflict-card-' + key)!.querySelector('wl-event-ref')!;
      expect([...ref.children].map((c) => c.getAttribute('data-testid'))).toEqual(['conflict-card-event-name', 'conflict-card-event-date', 'conflict-card-evidence']);
    }
    expect(q(el, 'conflict-card-start')?.querySelector('[data-testid="conflict-card-verified"]')).not.toBeNull();
    expect(q(el, 'conflict-card-citation-toggle')?.textContent?.trim()).toBe('FRUS 1939 I, Doc. 403, pp. 402–403');
    const end = q(el, 'conflict-card-end')!;
    expect(end.querySelector('[data-testid="conflict-card-pending"]')?.textContent).toBe('待查證');
    expect(end.querySelector('[data-testid="conflict-card-no-citation"]')).not.toBeNull();
    expect(end.querySelector('[data-testid="conflict-card-citation"]')).toBeNull();
    expect(q(el, 'conflict-card-location')?.textContent).toContain('中點');
  });

  it('點簡短引用展開完整書目', async () => {
    const { fixture, el } = await render(props());
    (q(el, 'conflict-card-citation-toggle') as HTMLButtonElement).click();
    await fixture.whenStable();
    expect(q(el, 'conflict-card-citation-full')?.textContent).toContain('Foreign Relations of the United States');
    expect(q(el, 'conflict-card-citation-full')?.textContent).toContain('但澤領事');
  });

  it('沒有停戰事件 → 本試驗範圍內未結束；關閉鈕送出 closed', async () => {
    const { fixture, el } = await render(props({ endEvent: null, validPeriod: { start: '1940-10-28', end: null } }));
    expect(q(el, 'conflict-card-end')?.textContent).toContain('本試驗範圍內未結束');
    let n = 0;
    fixture.componentInstance.closed.subscribe(() => n++);
    (q(el, 'conflict-card-close') as HTMLButtonElement).click();
    expect(n).toBe(1);
  });
});
