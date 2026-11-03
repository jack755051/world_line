import { TestBed } from '@angular/core/testing';
import { RegimeMapLabel, regimeLabelStyle } from './regime-label';

/** 現代 `rgb(… / a)` 與瀏覽器正規化後的 `rgba(r, g, b, a)` 都認。 */
function plateAlpha(background: string): number {
  const slash = background.match(/\/\s*([0-9.]+)/);
  const comma = background.match(/rgba\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*([0-9.]+)\s*\)/i);
  const m = slash ?? comma;
  if (!m) throw new Error(`底板沒有透明度：${background}`);
  return Number(m[1]);
}

describe('政權／國名標籤樣式', () => {
  it('細長政權也不順著長軸轉，一律水平', () => {
    const tall = regimeLabelStyle({ w: 40, h: 420 });
    const wide = regimeLabelStyle({ w: 420, h: 40 });
    const square = regimeLabelStyle({ w: 120, h: 120 });
    expect(tall.transform).toBe('translate(-50%, -50%) rotate(0deg)');
    expect(wide.transform).toBe(tall.transform);
    expect(square.transform).toBe(tall.transform);
    expect(tall.transform).not.toMatch(/rotate\(-?[1-9]/);
  });

  it('底板是一小塊半透明紙色', () => {
    const s = regimeLabelStyle();
    const alpha = plateAlpha(s.background);
    expect(alpha).toBeGreaterThan(0);
    expect(alpha).toBeLessThan(1);
    expect(s.background).toContain('250 247 240');
    expect(s.padding).toBe('2px 6px');
    expect(s.borderRadius).toBe('2px');
    expect(s.boxShadow).toContain('1px');
  });

  it('畫出來的標籤水平，而且帶半透明底板（高瘦外框也不轉）', async () => {
    TestBed.configureTestingModule({ imports: [RegimeMapLabel] });
    const fixture = TestBed.createComponent(RegimeMapLabel);
    fixture.componentRef.setInput('regimeId', 'cz');
    fixture.componentRef.setInput('text', '捷克斯洛伐克');
    fixture.componentRef.setInput('x', 120);
    fixture.componentRef.setInput('y', 80);
    fixture.componentRef.setInput('screenW', 48);
    fixture.componentRef.setInput('screenH', 360);
    await fixture.whenStable();
    const el = (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>(
      '[data-testid="map-regime-label"]',
    );
    expect(el).not.toBeNull();
    expect(el!.textContent).toContain('捷克斯洛伐克');
    expect(el!.getAttribute('data-orientation')).toBe('horizontal');
    expect(el!.getAttribute('data-regime-id')).toBe('cz');
    expect(el!.style.transform).toBe('translate(-50%, -50%) rotate(0deg)');
    expect(el!.style.left).toBe('120px');
    expect(el!.style.top).toBe('80px');
    const alpha = plateAlpha(el!.style.background);
    expect(alpha).toBeGreaterThan(0);
    expect(alpha).toBeLessThan(1);
    expect(el!.style.padding).toBe('2px 6px');
    expect(el!.classList.contains('wl-regime-label')).toBe(true);
  });
});
