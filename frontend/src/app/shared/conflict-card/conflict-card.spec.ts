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
    // 與國界卡片同一種做法：標籤 → 日期 → 事件名稱；出處是上標編號
    for (const key of ['start', 'end']) {
      const row = q(el, 'conflict-card-' + key)!;
      const kids = [...row.children].map((c) => c.getAttribute('data-testid')).filter((x) => x && x !== 'conflict-card-no-citation');
      expect(kids).toEqual(['conflict-card-evidence', 'conflict-card-event-date', 'conflict-card-event-name']);
    }
    expect(q(el, 'conflict-card-start')?.querySelector('[data-testid="conflict-card-verified"]')).not.toBeNull();
    expect(q(el, 'conflict-card-start')?.querySelector('[data-testid="conflict-card-sup"]')).not.toBeNull();
    expect(q(el, 'conflict-card-sources-panel')?.textContent).toContain('Doc. 403, pp. 402–403');
    const end = q(el, 'conflict-card-end')!;
    expect(end.querySelector('[data-testid="conflict-card-pending"]')?.textContent).toBe('待查證');
    expect(end.querySelector('[data-testid="conflict-card-no-citation"]')).not.toBeNull();
    expect(end.querySelector('[data-testid="conflict-card-sup"]')).toBeNull();
    expect(end.querySelector('[data-testid="conflict-card-pending"]')?.getAttribute('title')).toContain('尚無正式出處');
    expect(q(el, 'conflict-card-location')).toBeNull(); // §13 K3：一般模式不顯示技術說明
  });

  it('除錯模式才顯示圖示位置（§13 K3）', async () => {
    const fixture = TestBed.createComponent(ConflictCard);
    fixture.componentRef.setInput('props', props());
    fixture.componentRef.setInput('debug', true);
    await fixture.whenStable();
    expect(q(fixture.nativeElement, 'conflict-card-location')?.textContent).toContain('中點');
  });

  it('動作列（§13 K1／K2）：在時間線上看一定有；戰役簡報只在有符合的戰役時出現；點交戰方名稱切換政權', async () => {
    const { fixture, el } = await render(props());
    expect(q(el, 'conflict-card-timeline')).not.toBeNull();
    expect(q(el, 'conflict-card-campaign')).toBeNull();
    const seen: string[] = [];
    fixture.componentInstance.regimeSelect.subscribe((s) => seen.push(s));
    fixture.componentInstance.timelineShow.subscribe(() => seen.push('tl'));
    (q(el, 'conflict-card-side-a') as HTMLButtonElement).click();
    (q(el, 'conflict-card-timeline') as HTMLButtonElement).click();
    expect(seen).toEqual(['a', 'tl']);
    fixture.componentRef.setInput('campaigns', [{ key: 'poland_1939', name_zh: '閃擊波蘭' }]);
    await fixture.whenStable();
    expect(q(el, 'conflict-card-campaign')?.textContent).toContain('戰役簡報');
  });

  it('點上標編號展開「資料來源」，列出完整書目與說明', async () => {
    const { fixture, el } = await render(props());
    const panel = q(el, 'conflict-card-sources-panel') as HTMLElement;
    expect(panel.hidden).toBe(true);
    (q(el, 'conflict-card-sup') as HTMLButtonElement).click();
    await fixture.whenStable();
    expect(panel.hidden).toBe(false);
    expect(panel.textContent).toContain('Foreign Relations of the United States');
    expect(panel.textContent).toContain('但澤領事');
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
