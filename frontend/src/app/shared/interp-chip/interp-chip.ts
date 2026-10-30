import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { SANRING_POPOVER_IMPORTS } from '../../components/ui/popover';
import { SpinnerComponent } from '../../components/ui/spinner';
import type { TheaterStateDto } from '../../core/api/api-types';
import type { LoadStatus } from '../../core/atlas-data';
import { t, type I18nKey, type Lang } from '../../core/i18n';
import { theaterLabel } from '../../core/theater-tracks';

export type ChipMode = 'hidden' | 'loading' | 'attested' | 'interpolated' | 'unknown';

/** PRD §8.5：依各戰區狀態決定 chip。查不到狀態時一律「無法判斷」（保守原則），不預設成史料。 */
export function chipMode(status: LoadStatus, theaters: readonly TheaterStateDto[] | null, featureCount: number): ChipMode {
  if (status === 'loading' && !theaters) return 'loading';
  if (status === 'error') return 'unknown';
  // PRD §8.5 empty：畫面中沒有任何控制資料時不顯示 chip
  if (!theaters || featureCount === 0) return 'hidden';
  if (theaters.some((x) => x.state !== 'attested')) return 'interpolated';
  return 'attested';
}

/** 頂部「史料快照／推估過渡」chip（PRD §8.5）。 */
@Component({
  selector: 'wl-interp-chip',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SANRING_POPOVER_IMPORTS, SpinnerComponent],
  template: `
    @switch (mode()) {
      @case ('loading') { <span data-testid="interp-chip" class="wl-text2 text-wl-on-surface-variant"><sanring-spinner size="sm" [ariaLabel]="'loading'" /></span> }
      @case ('attested') { <span data-testid="interp-chip" data-state="attested" class="wl-stamp">{{ tr('chip.attested') }}</span> }
      @case ('unknown') { <span data-testid="interp-chip" data-state="unknown" class="wl-chip-warn" role="status">{{ tr('chip.unknown') }}</span> }
      @case ('interpolated') {
        <sanring-popover [(isOpen)]="open">
          <button sanringPopoverTrigger type="button" data-testid="interp-chip" data-state="interpolated" class="wl-chip-interp cursor-pointer">
            {{ label() }}
          </button>
          <sanring-popover-content class="w-[360px] rounded-[var(--wl-radius-lg)] bg-wl-surface border-wl-outline-variant p-4 shadow-[var(--wl-shadow-panel)]">
            <div data-testid="interp-popover" class="flex flex-col gap-3 wl-text2">
              <h2 class="wl-sub-title">{{ tr('chip.popover.title') }}</h2>
              @for (row of rows(); track row.theaterCode; let first = $first) {
                <div data-testid="interp-theater-row" class="flex flex-col gap-2" [class.border-t]="!first" [class.border-wl-outline-variant]="!first" [class.pt-3]="!first">
                  <span>{{ name(row.theaterCode) }}：{{ rowText(row) }}</span>
                  <span class="grid grid-cols-2 gap-2">
                    <button type="button" class="wl-btn-secondary h-7 px-2 wl-text2" data-testid="interp-jump-prev" [disabled]="!row.prevSnapshot"
                      [attr.title]="row.prevSnapshot?.asOf ?? null" (click)="row.prevSnapshot && jumpTo(row.prevSnapshot.asOf)">{{ tr('chip.jumpPrev') }}</button>
                    <button type="button" class="wl-btn-secondary h-7 px-2 wl-text2" data-testid="interp-jump-next" [disabled]="!row.nextSnapshot"
                      [attr.title]="row.nextSnapshot?.asOf ?? null" (click)="row.nextSnapshot && jumpTo(row.nextSnapshot.asOf)">{{ tr('chip.jumpNext') }}</button>
                  </span>
                </div>
              }
            </div>
          </sanring-popover-content>
        </sanring-popover>
      }
    }
  `,
})
export class InterpChip {
  readonly status = input<LoadStatus>('idle');
  readonly theaters = input<TheaterStateDto[] | null>(null);
  readonly featureCount = input(0);
  readonly lang = input<Lang>('zh-Hant');
  readonly jump = output<string>();

  protected readonly open = signal(false);
  readonly mode = computed(() => chipMode(this.status(), this.theaters(), this.featureCount()));
  protected readonly rows = computed(() => (this.theaters() ?? []).filter((x) => x.state !== 'attested'));
  protected readonly label = computed(() => t('chip.interpolated', this.lang(), { n: this.rows().length }));

  protected tr(key: I18nKey): string {
    return t(key, this.lang());
  }
  protected name(code: string): string {
    return theaterLabel(code, this.lang());
  }
  protected rowText(row: TheaterStateDto): string {
    if (row.state === 'interpolated')
      return t('chip.popover.between', this.lang(), { prev: row.prevSnapshot?.asOf ?? '?', next: row.nextSnapshot?.asOf ?? '?' });
    const ref = row.prevSnapshot?.asOf ?? row.nextSnapshot?.asOf ?? '—';
    return t('chip.popover.outside', this.lang(), { ref });
  }
  protected jumpTo(d: string): void {
    this.open.set(false);
    this.jump.emit(d);
  }
}
