import { TestBed } from '@angular/core/testing';
import { MotionService } from '../../core/motion';
import { Legend } from './legend';

describe('Legend（PRD §8.4）', () => {
  it('固定樣式說明：五種控制類型、控制資料缺說明、戰線、史料／推估', async () => {
    const fixture = TestBed.createComponent(Legend);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    for (const ct of ['direct_rule', 'military_occupation', 'puppet_administration', 'partial', 'contested'])
      expect(el.querySelector(`[data-testid="legend-control-type-${ct}"]`)).not.toBeNull();
    expect(el.querySelector('[data-testid="legend-control-gap"]')?.textContent).toContain('並非不完全控制');
    expect(el.querySelector('[data-testid="legend-frontline"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="legend-attested"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="legend-interpolated"]')).not.toBeNull();
  });

  it('政權清單：empty 與 success', async () => {
    const fixture = TestBed.createComponent(Legend);
    fixture.componentRef.setInput('regimesStatus', 'ok');
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('目前畫面無資料');
    fixture.componentRef.setInput('regimes', [{ id: 'x', name: '測試政權', tone: '#8b7f6c' }]);
    await fixture.whenStable();
    expect(el.querySelectorAll('[data-testid="legend-regime-item"]').length).toBe(1);
    expect(el.querySelector('[data-testid="legend-regime-item"]')?.getAttribute('data-camp')).toBe('unassigned');
    expect(el.querySelector('[data-testid="legend-regime-item"]')?.textContent).toContain('陣營未建置');
    fixture.componentRef.setInput('regimes', [{ id: 'x', name: '測試政權', tone: '#c8964a', camp: 'axis' }]);
    await fixture.whenStable();
    expect(el.querySelector('[data-testid="legend-regime-item"]')?.getAttribute('data-camp')).toBe('axis');
    expect(el.querySelector('[data-testid="legend-regime-item"]')?.textContent).toContain('軸心');
  });

  it('收合後只剩標題列', async () => {
    const fixture = TestBed.createComponent(Legend);
    fixture.componentRef.setInput('open', false);
    await fixture.whenStable();
    expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="legend-control-gap"]')).toBeNull();
  });
});

describe('Legend：主權圖層與收合動畫', () => {
  function setup(reduced: boolean) {
    let finish: () => void = () => undefined;
    const calls: Record<string, unknown>[] = [];
    const fake = {
      reduced: () => reduced,
      animate: (_el: Element, kf: Record<string, unknown>) => {
        calls.push(kf);
        return new Promise<void>((r) => (finish = r));
      },
    };
    TestBed.configureTestingModule({ providers: [{ provide: MotionService, useValue: fake }] });
    const fixture = TestBed.createComponent(Legend);
    return { fixture, calls, finish: () => finish() };
  }
  const state = (f: { nativeElement: HTMLElement }) => f.nativeElement.querySelector('[data-testid="legend"]')?.getAttribute('data-state');

  it('實際控制檢視：國界說明（淡色底圖）＋原本控制類型；主權檢視：國界政權清單取代控制區清單', async () => {
    const { fixture } = setup(true);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="legend-sovereignty"]')?.textContent).toContain('淡色底圖');
    expect(el.querySelector('[data-testid="legend-control-type-direct_rule"]')).not.toBeNull();
    fixture.componentRef.setInput('axis', 'sovereignty');
    fixture.componentRef.setInput('sovRegimesStatus', 'ok');
    fixture.componentRef.setInput('sovRegimes', [
      { id: 'a', name: '德意志國', color: '#a99dc4', pending: true },
      { id: 'b', name: '比利時與北法軍政府', color: '#a99dc4', notSovereign: true },
    ]);
    await fixture.whenStable();
    expect(el.querySelector('[data-testid="legend-control-type-direct_rule"]')).toBeNull();
    const items = el.querySelectorAll('[data-testid="legend-sov-regime-item"]');
    expect(items.length).toBe(2);
    expect(items[0].textContent).toContain('變動待查證');
    expect(items[1].getAttribute('data-not-sovereign')).toBe('true');
    expect(el.querySelector('[data-testid="legend-sov-blank"]')?.textContent).toContain('待查證');
  });

  it('收合：先播 motion 收合（data-state=closing），結束後才換成收合按鈕；展開也播', async () => {
    const { fixture, calls, finish } = setup(false);
    await fixture.whenStable();
    fixture.componentRef.setInput('open', false);
    await fixture.whenStable();
    expect(state(fixture)).toBe('closing');
    expect(calls.at(-1)?.['opacity']).toEqual([1, 0]);
    finish();
    await new Promise((r) => setTimeout(r));
    await fixture.whenStable();
    expect(state(fixture)).toBe('collapsed');
    fixture.componentRef.setInput('open', true);
    await fixture.whenStable();
    expect(state(fixture)).toBe('open');
    expect(calls.at(-1)?.['opacity']).toEqual([0.4, 1]);
  });

  it('prefers-reduced-motion：直接切換，不播動畫', async () => {
    const { fixture, calls } = setup(true);
    await fixture.whenStable();
    fixture.componentRef.setInput('open', false);
    await fixture.whenStable();
    expect(state(fixture)).toBe('collapsed');
    expect(calls.length).toBe(0);
  });
});
