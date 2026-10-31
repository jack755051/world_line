import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { RegimeSheet } from './regime-sheet';

@Component({
  imports: [RegimeSheet],
  template: `<wl-regime-sheet [open]="open()" [side]="side()" [size]="300" title="德意志國" description="Deutsches Reich" descriptionLang="de"
    titleTestId="sovereignty-card-title" closeTestId="sovereignty-card-close" (closed)="closes = closes + 1" (hidden)="hides = hides + 1">
    <p data-testid="sheet-content">內容</p></wl-regime-sheet>`,
})
class Host {
  open = signal(false);
  side = signal<'right' | 'bottom'>('right');
  closes = 0;
  hides = 0;
}
const q = (el: HTMLElement, id: string) => el.querySelector(`[data-testid="${id}"]`) as HTMLElement | null;

describe('RegimeSheet（政權資訊側邊面板，參考 sanring Sheet）', () => {
  async function setup() {
    const fixture = TestBed.createComponent(Host);
    await fixture.whenStable();
    return { fixture, host: fixture.componentInstance, el: fixture.nativeElement as HTMLElement };
  }

  it('關著時不渲染；打開後有標題／描述區、內容、右上關閉鈕，非 modal', async () => {
    const { fixture, host, el } = await setup();
    expect(q(el, 'regime-sheet')).toBeNull();
    host.open.set(true);
    await fixture.whenStable();
    const panel = q(el, 'regime-sheet')!;
    expect(panel.getAttribute('role')).toBe('dialog');
    expect(panel.getAttribute('aria-modal')).toBe('false');
    expect(panel.getAttribute('data-side')).toBe('right');
    expect(panel.style.width).toBe('300px');
    expect(panel.className).toContain('right-0');
    const title = q(el, 'sovereignty-card-title')!;
    expect(title.textContent).toContain('德意志國');
    expect(panel.getAttribute('aria-labelledby')).toBe(title.id);
    expect(q(el, 'regime-sheet-description')?.getAttribute('lang')).toBe('de');
    expect(q(el, 'sheet-content')?.textContent).toBe('內容');
    expect(q(el, 'sovereignty-card-close')?.getAttribute('aria-label')).toBe('關閉面板');
  });

  it('關閉鈕與 Esc 送出 closed；關掉後（減少動態：無動畫）移除並送出 hidden', async () => {
    const { fixture, host, el } = await setup();
    host.open.set(true);
    await fixture.whenStable();
    q(el, 'sovereignty-card-close')!.click();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(host.closes).toBe(2);
    host.open.set(false);
    await fixture.whenStable();
    await new Promise((r) => setTimeout(r));
    await fixture.whenStable();
    expect(q(el, 'regime-sheet')).toBeNull();
    expect(host.hides).toBe(1);
  });

  it('窄螢幕從底部滑出（高度用 size）', async () => {
    const { fixture, host, el } = await setup();
    host.side.set('bottom');
    host.open.set(true);
    await fixture.whenStable();
    const panel = q(el, 'regime-sheet')!;
    expect(panel.getAttribute('data-side')).toBe('bottom');
    expect(panel.style.height).toBe('300px');
    expect(panel.className).toContain('bottom-0');
  });
});
