import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { cn } from '../shared/utils';

@Component({
  selector: 'sanring-sheet-header',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { '[class]': 'hostClass()' },
  template: `<ng-content></ng-content>`,
})
export class SheetHeaderComponent {
  readonly class = input<string | undefined>();

  readonly align = input<'start' | 'center' | undefined>(undefined);

  protected readonly hostClass = computed(() =>
    cn(
      'flex flex-col gap-1.5',
      this.align() === 'center' && 'items-center text-center',
      this.align() === 'start' && 'items-start text-left',
      !this.align() && 'text-center sm:text-left',
      this.class(),
    ),
  );
}
