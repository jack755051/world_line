import { TestBed } from '@angular/core/testing';
import { MotionService } from '../../core/motion';
import { TopBar } from './top-bar';

function setup(reduced: boolean) {
  const calls: { el: Element; kf: Record<string, unknown> }[] = [];
  const fake = { reduced: () => reduced, animate: async (el: Element, kf: Record<string, unknown>) => void calls.push({ el, kf }) };
  TestBed.configureTestingModule({ providers: [{ provide: MotionService, useValue: fake }] });
  const fixture = TestBed.createComponent(TopBar);
  fixture.componentRef.setInput('date', '1939-10-15');
  return { fixture, calls };
}

describe('TopBar：實際控制／主權切換', () => {
  it('兩個鈕都可用；aria-pressed 跟著 axis；點另一個才發 axisChange', async () => {
    const { fixture } = setup(true);
    const emitted: string[] = [];
    fixture.componentInstance.axisChange.subscribe((a) => emitted.push(a));
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    const ctl = el.querySelector<HTMLButtonElement>('[data-testid="axis-toggle-control"]')!;
    const sov = el.querySelector<HTMLButtonElement>('[data-testid="axis-toggle-sovereignty"]')!;
    expect(sov.disabled).toBe(false);
    expect(ctl.getAttribute('aria-pressed')).toBe('true');
    ctl.click();
    sov.click();
    expect(emitted).toEqual(['sovereignty']);
    fixture.componentRef.setInput('axis', 'sovereignty');
    await fixture.whenStable();
    expect(sov.getAttribute('aria-pressed')).toBe('true');
    expect(el.querySelector('[data-testid="axis-toggle"]')?.getAttribute('data-axis')).toBe('sovereignty');
  });

  it('切換時選取底塊用 motion 滑動', async () => {
    const { fixture, calls } = setup(false);
    await fixture.whenStable();
    expect(calls.length).toBe(0); // 第一次直接到位
    fixture.componentRef.setInput('axis', 'sovereignty');
    await fixture.whenStable();
    expect(calls.length).toBe(1);
    expect((calls[0].el as HTMLElement).dataset['testid']).toBe('axis-toggle-thumb');
    expect(Object.keys(calls[0].kf)).toContain('transform');
  });

  it('prefers-reduced-motion：不播動畫，底塊直接到位', async () => {
    const { fixture, calls } = setup(true);
    await fixture.whenStable();
    fixture.componentRef.setInput('axis', 'sovereignty');
    await fixture.whenStable();
    expect(calls.length).toBe(0);
    const thumb = (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('[data-testid="axis-toggle-thumb"]')!;
    expect(thumb.style.transform).toMatch(/^translateX\(/);
  });
});
