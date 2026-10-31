import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { cn } from '../shared/utils';

@Component({
  selector: 'sanring-sheet-footer',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { '[class]': 'hostClass()' },
  template: `<ng-content></ng-content>`,
})
export class SheetFooterComponent {
  readonly class = input<string | undefined>();
  protected readonly hostClass = computed(() => cn('flex flex-col gap-2', this.class()));
}
