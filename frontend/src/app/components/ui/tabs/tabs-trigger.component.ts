import { Tab as NgTab } from '@angular/aria/tabs';
import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { cn } from '../shared/utils';
import { NAV_ITEM_TEXT_CLASS } from './tabs.styles';
import { TabsComponent } from './tabs.component';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'sanring-tabs-trigger',
  standalone: true,
  template: `
    <ng-content></ng-content>
  `,
  hostDirectives: [
    {
      directive: NgTab,
      inputs: ['value', 'disabled'],
    },
  ],
  host: {
    '[attr.data-state]': "tab.selected() ? 'active' : 'inactive'",
    '[attr.data-disabled]': "tab.disabled() ? '' : null",
    '[class]': 'tabsTriggerClass()',
  },
})
export class TabsTriggerComponent {
  readonly class = input<string | undefined>();

  protected tab = inject(NgTab);
  protected tabs = inject(TabsComponent);
  protected readonly tabsTriggerClass = computed(() => {
    const variant = this.tabs.variant();
    return cn(
      'inline-flex shrink-0 cursor-pointer items-center justify-center gap-1.5 whitespace-nowrap px-3 py-1.5 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sanring-border-strong)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--sanring-background)] data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
      NAV_ITEM_TEXT_CLASS,
      variant === 'default' &&
        'rounded-[var(--sanring-radius-sm)] border border-transparent px-2.5 py-1 text-[var(--sanring-muted)] hover:bg-[var(--sanring-elevated)] hover:text-[var(--sanring-foreground)] data-[state=active]:border-[var(--sanring-border-strong)] data-[state=active]:bg-[var(--sanring-active)] data-[state=active]:text-[var(--sanring-foreground)] data-[state=active]:shadow-sm',
      variant === 'line' &&
        cn(
          'rounded-none border-transparent text-[var(--sanring-muted)] data-[state=active]:border-[var(--sanring-foreground)] data-[state=active]:text-[var(--sanring-foreground)]',
          this.tabs.orientation() === 'vertical'
            ? 'justify-start border-l-2 px-3 py-2'
            : 'border-b-2 pb-2.5 pt-2',
        ),
      this.class(),
    );
  });
}
