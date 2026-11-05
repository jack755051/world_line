import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  effect,
  inject,
  input,
  isDevMode,
  output,
  untracked,
  viewChild,
} from '@angular/core';

export interface ScanSnapshot {
  canvas: HTMLCanvasElement;
  labels: HTMLElement;
}

export type ScanPhase = 'idle' | 'waiting' | 'sweeping';

/**
 * 舊圖快照蓋在新圖上，亮線從左往右掃。
 * 線左露出新圖（底層地圖），線右維持舊圖（快照）。
 *
 * 動畫一律用 Web Animations API，可透過 CDP Animation.setPlaybackRate 放慢截圖。
 * jsdom 沒有 element.animate 時退化為 setTimeout 後直接發 done。
 */
@Component({
  selector: 'wl-scan-reveal',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    'data-testid': 'map-scan',
    '[attr.data-scan-phase]': 'phase()',
    style: 'position:absolute;inset:0;pointer-events:none;z-index:5;overflow:hidden;display:block;',
  },
  styles: [`
    :host { display: block; }

    .wl-scan-old {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
    }

    .wl-scan-line {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 0;
      width: 2px;
      background: #ffffff;
      box-shadow:
        0 0 6px 3px rgba(150, 255, 255, 0.85),
        0 0 16px 8px rgba(80, 200, 255, 0.45);
    }
  `],
  template: `
    <div #oldContainer class="wl-scan-old"></div>
    <div #scanLine data-testid="map-scan-line" class="wl-scan-line"></div>
    @if (phase() === 'waiting') {
      <span data-testid="map-busy" class="sr-only" role="status" aria-live="polite">{{ busyText() }}</span>
    }
  `,
})
export class ScanRevealComponent {
  /** 02 步產出的快照（canvas + labels）；null 表示無快照。 */
  readonly snapshot = input<ScanSnapshot | null>(null);
  /** 掃描階段。 */
  readonly phase = input<ScanPhase>('idle');
  /** 掃描動畫時長（ms），預設 900。 */
  readonly durationMs = input<number>(900);
  /** 讀屏播報文字，waiting 期間顯示。 */
  readonly busyText = input<string>('');

  /** 掃完時發出。 */
  readonly done = output<void>();

  private readonly oldContainerRef = viewChild<ElementRef<HTMLElement>>('oldContainer');
  private readonly scanLineRef = viewChild<ElementRef<HTMLElement>>('scanLine');
  private readonly hostEl = inject<ElementRef<HTMLElement>>(ElementRef);

  private waitingAnim: Animation | null = null;
  private sweepAnims: Animation[] = [];

  constructor() {
    inject(DestroyRef).onDestroy(() => this.clearAnimations());

    // 掛載快照
    effect(() => {
      const snap = this.snapshot();
      const oldContainerEl = this.oldContainerRef();
      if (!oldContainerEl) return;
      const container = oldContainerEl.nativeElement;
      container.innerHTML = '';
      if (snap) {
        container.appendChild(snap.canvas);
        container.appendChild(snap.labels);
      }
    });

    // 處理 phase 切換
    effect(() => {
      const phase = this.phase();
      const oldContainerEl = this.oldContainerRef();
      const scanLineEl = this.scanLineRef();
      if (!oldContainerEl || !scanLineEl) return;

      const container = oldContainerEl.nativeElement;
      const line = scanLineEl.nativeElement;

      untracked(() => this.clearAnimations());

      if (phase === 'idle') {
        container.style.clipPath = 'inset(0 0 0 100%)';
        line.style.opacity = '0';
        line.style.transform = 'translateX(0)';
        return;
      }

      if (phase === 'waiting') {
        container.style.clipPath = 'inset(0 0 0 0%)';
        line.style.transform = 'translateX(0)';
        line.style.opacity = '1';

        if (typeof line.animate === 'function') {
          this.waitingAnim = line.animate(
            [{ opacity: 0.55 }, { opacity: 1 }],
            { duration: 1200, iterations: Infinity, direction: 'alternate', easing: 'ease-in-out' },
          );
        }
        return;
      }

      if (phase === 'sweeping') {
        untracked(() => this.runSweep(container, line));
      }
    });
  }

  private runSweep(container: HTMLElement, line: HTMLElement): void {
    const width = this.hostEl.nativeElement.offsetWidth || 800;

    let duration = this.durationMs();
    if (isDevMode()) {
      const w = window as Window & { __wlScanDurationMs?: number };
      if (typeof w.__wlScanDurationMs === 'number') {
        duration = w.__wlScanDurationMs;
      }
    }

    container.style.clipPath = 'inset(0 0 0 0px)';
    line.style.opacity = '1';
    line.style.transform = 'translateX(0px)';

    // jsdom 沒有 Web Animations API → setTimeout 直接 done
    if (typeof line.animate !== 'function') {
      setTimeout(() => this.done.emit(), duration);
      return;
    }

    // clip 與 beam 用相同 px 單位確保每幀對齊
    const clipAnim = container.animate(
      [
        { clipPath: 'inset(0 0 0 0px)' },
        { clipPath: `inset(0 0 0 ${width}px)` },
      ],
      { duration, easing: 'linear', fill: 'forwards' },
    );

    const lineAnim = line.animate(
      [
        { transform: 'translateX(0px)' },
        { transform: `translateX(${width}px)` },
      ],
      { duration, easing: 'linear', fill: 'forwards' },
    );

    this.sweepAnims = [clipAnim, lineAnim];

    lineAnim.finished.then(() => {
      this.done.emit();
      // 亮線 150ms 淡出
      line.animate(
        [{ opacity: 1 }, { opacity: 0 }],
        { duration: 150, fill: 'forwards' },
      );
    }).catch(() => {
      // Animation 被 cancel，無需處理
    });
  }

  private clearAnimations(): void {
    this.waitingAnim?.cancel();
    this.waitingAnim = null;
    this.sweepAnims.forEach(a => a.cancel());
    this.sweepAnims = [];
  }
}
