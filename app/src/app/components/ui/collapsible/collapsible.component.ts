import {
  ChangeDetectionStrategy,
  Component,
  booleanAttribute,
  computed,
  inject,
  input,
  model,
} from '@angular/core';
import { _IdGenerator } from '@angular/cdk/a11y';
import { cn } from '../shared/utils';

@Component({
  selector: 'sanring-collapsible',
  standalone: true,
  template: `<ng-content></ng-content>`,
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '[class]': 'hostClass()',
    '[attr.data-state]': 'open() ? "open" : "closed"',
    '[attr.data-disabled]': 'disabled() ? "" : null',
  },
})
export class CollapsibleComponent {
  readonly class = input<string | undefined>();
  readonly open = model<boolean>(false);
  readonly disabled = input(false, { transform: booleanAttribute });

  private readonly _id = inject(_IdGenerator).getId('sanring-collapsible-', true);
  readonly contentId = `${this._id}-content`;
  readonly triggerId = `${this._id}-trigger`;

  toggle(): void {
    if (this.disabled()) return;
    this.open.update((v) => !v);
  }

  protected readonly hostClass = computed(() => cn(this.class()));
}
