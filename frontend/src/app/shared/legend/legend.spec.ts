import { TestBed } from '@angular/core/testing';
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
  });

  it('收合後只剩標題列', async () => {
    const fixture = TestBed.createComponent(Legend);
    fixture.componentRef.setInput('open', false);
    await fixture.whenStable();
    expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="legend-control-gap"]')).toBeNull();
  });
});
