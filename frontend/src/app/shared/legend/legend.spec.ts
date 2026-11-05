import { TestBed } from '@angular/core/testing';
import { MotionService } from '../../core/motion';
import { Legend } from './legend';

describe('Legend（PRD §8.4）', () => {
  it('固定樣式說明：五種控制類型、控制資料缺說明、戰線、史料／推估', async () => {
    const fixture = TestBed.createComponent(Legend);
    fixture.componentRef.setInput('open', true);
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
    fixture.componentRef.setInput('open', true);
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

  it('§10-3：預設關閉，只有左下 40×40 ⓘ 按鈕；展開時按鈕上方 240px 浮動面板（最高 50vh）；按鈕與 Esc 送出 toggle', async () => {
    const fixture = TestBed.createComponent(Legend);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="legend"]')?.getAttribute('data-state')).toBe('collapsed');
    expect(el.querySelector('[data-testid="legend-control-gap"]')).toBeNull();
    const btn = el.querySelector('[data-testid="legend-expand"]') as HTMLButtonElement;
    expect(btn.className).toContain('size-10');
    expect(btn.getAttribute('aria-expanded')).toBe('false');
    let n = 0;
    fixture.componentInstance.toggle.subscribe(() => n++);
    btn.click();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(n).toBe(1); // 關著時 Esc 不動作
    fixture.componentRef.setInput('open', true);
    await fixture.whenStable();
    const panel = el.querySelector('[data-testid="legend-panel"]') as HTMLElement;
    expect(panel.className).toContain('w-[240px]');
    expect(panel.className).toContain('max-h-[50vh]');
    // 面板在按鈕上方
    expect(panel.compareDocumentPosition(el.querySelector('[data-testid="legend-expand"]')!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(n).toBe(2);
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
    fixture.componentRef.setInput('open', true);
    return { fixture, calls, finish: () => finish() };
  }
  const state = (f: { nativeElement: HTMLElement }) => f.nativeElement.querySelector('[data-testid="legend"]')?.getAttribute('data-state');

  it('實際控制檢視：國界說明（淡色底圖）＋原本控制類型；主權檢視：只留國界（主權圖層）說明，不列政權清單', async () => {
    const { fixture } = setup(true);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="legend-sovereignty"]')?.textContent).toContain('淡色底圖');
    expect(el.querySelector('[data-testid="legend-control-type-direct_rule"]')).not.toBeNull();
    fixture.componentRef.setInput('axis', 'sovereignty');
    await fixture.whenStable();
    expect(el.querySelector('[data-testid="legend-control-type-direct_rule"]')).toBeNull();
    expect(el.querySelector('[data-testid="legend-sov-regimes"]')).toBeNull();
    expect(el.querySelectorAll('[data-testid="legend-sov-regime-item"]').length).toBe(0);
    expect(el.textContent).not.toContain('目前畫面中的政權');
    expect(el.querySelector('[data-testid="legend-sov-fill"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="legend-sov-not-sovereign"]')).not.toBeNull();
    // 佔領區三種深淺
    expect(el.querySelector('[data-testid="legend-sov-occupation-annexed"]')?.textContent).toContain('併入');
    expect(el.querySelector('[data-testid="legend-sov-occupation-civil_administration"]')?.textContent).toContain('總督府');
    expect(el.querySelector('[data-testid="legend-sov-occupation-military_administration"]')?.textContent).toContain('軍事管理');
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
