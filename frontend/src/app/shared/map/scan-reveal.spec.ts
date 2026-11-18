import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ScanRevealComponent } from './scan-reveal';

describe('ScanRevealComponent', () => {
  let fixture: ComponentFixture<ScanRevealComponent>;
  let el: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ScanRevealComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ScanRevealComponent);
    el = fixture.nativeElement as HTMLElement;
    fixture.detectChanges();
  });

  it('host element has data-testid="map-scan"', () => {
    expect(el.getAttribute('data-testid')).toBe('map-scan');
  });

  describe('data-scan-phase', () => {
    it('reflects phase input changes', () => {
      fixture.componentRef.setInput('phase', 'waiting');
      fixture.detectChanges();
      expect(el.getAttribute('data-scan-phase')).toBe('waiting');

      fixture.componentRef.setInput('phase', 'sweeping');
      fixture.detectChanges();
      expect(el.getAttribute('data-scan-phase')).toBe('sweeping');

      fixture.componentRef.setInput('phase', 'idle');
      fixture.detectChanges();
      expect(el.getAttribute('data-scan-phase')).toBe('idle');
    });

    it('is "idle" by default', () => {
      expect(el.getAttribute('data-scan-phase')).toBe('idle');
    });
  });

  describe('map-busy', () => {
    it('is absent in idle phase (default)', () => {
      expect(el.querySelector('[data-testid="map-busy"]')).toBeNull();
    });

    it('exists in waiting phase', () => {
      fixture.componentRef.setInput('phase', 'waiting');
      fixture.detectChanges();
      expect(el.querySelector('[data-testid="map-busy"]')).not.toBeNull();
    });

    it('shows busyText content when waiting', () => {
      fixture.componentRef.setInput('busyText', '載入中');
      fixture.componentRef.setInput('phase', 'waiting');
      fixture.detectChanges();
      const busyEl = el.querySelector('[data-testid="map-busy"]');
      expect(busyEl?.textContent?.trim()).toBe('載入中');
    });

    it('disappears when phase leaves waiting', () => {
      fixture.componentRef.setInput('phase', 'waiting');
      fixture.detectChanges();
      expect(el.querySelector('[data-testid="map-busy"]')).not.toBeNull();

      fixture.componentRef.setInput('phase', 'idle');
      fixture.detectChanges();
      expect(el.querySelector('[data-testid="map-busy"]')).toBeNull();
    });

    it('is absent in sweeping phase', () => {
      fixture.componentRef.setInput('phase', 'sweeping');
      fixture.detectChanges();
      expect(el.querySelector('[data-testid="map-busy"]')).toBeNull();
    });
  });

  describe('snapshot', () => {
    it('canvas and labels are appended to .wl-scan-old', () => {
      const canvas = document.createElement('canvas');
      const labels = document.createElement('div');

      fixture.componentRef.setInput('snapshot', { canvas, labels });
      fixture.detectChanges();

      const container = el.querySelector('.wl-scan-old');
      expect(container).not.toBeNull();
      expect(container!.contains(canvas)).toBe(true);
      expect(container!.contains(labels)).toBe(true);
    });

    it('clears .wl-scan-old when snapshot becomes null', () => {
      const canvas = document.createElement('canvas');
      const labels = document.createElement('div');

      fixture.componentRef.setInput('snapshot', { canvas, labels });
      fixture.detectChanges();

      fixture.componentRef.setInput('snapshot', null);
      fixture.detectChanges();

      const container = el.querySelector('.wl-scan-old');
      expect(container!.children).toHaveLength(0);
    });
  });

  describe('sweeping — jsdom fallback (no element.animate)', () => {
    it('emits done after durationMs via setTimeout when element.animate is unavailable', async () => {
      // jsdom does not implement element.animate, so the fallback path is used
      vi.useFakeTimers();
      try {
        const doneCalls: void[] = [];
        fixture.componentInstance.done.subscribe(() => doneCalls.push(undefined));

        fixture.componentRef.setInput('durationMs', 300);
        fixture.componentRef.setInput('phase', 'sweeping');
        fixture.detectChanges();

        // done should not have been emitted yet
        expect(doneCalls).toHaveLength(0);

        await vi.advanceTimersByTimeAsync(300);

        expect(doneCalls).toHaveLength(1);
      } finally {
        vi.useRealTimers();
      }
    });

    it('does not emit done before the timeout expires', async () => {
      vi.useFakeTimers();
      try {
        const doneCalls: void[] = [];
        fixture.componentInstance.done.subscribe(() => doneCalls.push(undefined));

        fixture.componentRef.setInput('durationMs', 500);
        fixture.componentRef.setInput('phase', 'sweeping');
        fixture.detectChanges();

        await vi.advanceTimersByTimeAsync(499);
        expect(doneCalls).toHaveLength(0);

        await vi.advanceTimersByTimeAsync(1);
        expect(doneCalls).toHaveLength(1);
      } finally {
        vi.useRealTimers();
      }
    });
  });
});
