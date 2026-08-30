import { ChangeDetectionStrategy, booleanAttribute, Component, computed, input, output } from '@angular/core';
import { LucideX } from '@lucide/angular';
import { cn } from '../shared/utils';
import { BadgeDirective, type BadgeVariant } from '../badge';
import { TAG_CLOSE_BUTTON_CLASS, TAG_CLOSE_ICON_CLASS } from './tag.styles';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'sanring-tag',
  standalone: true,
  imports: [BadgeDirective, LucideX],
  template: `
    <span sanringBadge [variant]="variant()" [class]="tagClass()">
      <ng-content />

      @if (closable()) {
        <button
          type="button"
          [class]="tagCloseButtonClass"
          [attr.aria-label]="removeAriaLabel()"
          (click)="onRemove($event)"
        >
          <svg [class]="tagCloseIconClass" lucideX></svg>
        </button>
      }
    </span>
  `,
})
export class TagComponent {
  protected readonly tagCloseButtonClass = TAG_CLOSE_BUTTON_CLASS;
  protected readonly tagCloseIconClass = TAG_CLOSE_ICON_CLASS;

  readonly class = input<string | undefined>();
  readonly variant = input<BadgeVariant>('secondary');
  readonly closable = input(false, { transform: booleanAttribute });
  readonly removeAriaLabel = input('Remove tag');

  readonly remove = output<MouseEvent>();

  protected readonly tagClass = computed(() =>
    cn('pl-2.5', this.closable() ? 'pr-1' : 'pr-2.5', this.class()),
  );

  protected onRemove(event: MouseEvent) {
    event.stopPropagation();
    this.remove.emit(event);
  }
}
