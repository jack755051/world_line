import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { cn } from '../shared/utils';
import { DESCRIPTION_TEXT_CLASS } from '../shared/component-styles';
import { SheetComponent } from './sheet.component';

@Component({
  selector: 'sanring-sheet-description',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '[class]': 'hostClass()',
    '[id]': 'sheet?.descId',
  },
  template: `<ng-content></ng-content>`,
})
export class SheetDescriptionComponent {
  protected readonly sheet = inject(SheetComponent, { optional: true });
  readonly class = input<string | undefined>();
  protected readonly hostClass = computed(() => cn(DESCRIPTION_TEXT_CLASS, this.class()));
}
