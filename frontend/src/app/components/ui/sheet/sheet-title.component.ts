import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { cn } from '../shared/utils';
import { TITLE_TEXT_CLASS } from '../shared/component-styles';
import { SheetComponent } from './sheet.component';

@Component({
  selector: 'sanring-sheet-title',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '[class]': 'hostClass()',
    '[id]': 'sheet?.titleId',
  },
  template: `<ng-content></ng-content>`,
})
export class SheetTitleComponent {
  protected readonly sheet = inject(SheetComponent, { optional: true });
  readonly class = input<string | undefined>();
  protected readonly hostClass = computed(() =>
    cn(TITLE_TEXT_CLASS, 'text-[var(--sanring-foreground)]', this.class()),
  );
}
