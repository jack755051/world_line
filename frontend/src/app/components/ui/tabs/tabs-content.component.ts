import { TabContent as NgTabContent, TabPanel as NgTabPanel } from '@angular/aria/tabs';
import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { cn } from '../shared/utils';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'sanring-tabs-content',
  standalone: true,
  imports: [NgTabContent, NgTabPanel],
  template: `
    <div
      ngTabPanel
      #panel="ngTabPanel"
      [value]="value()"
      [preserveContent]="true"
      [hidden]="!panel.visible()"
      [attr.data-state]="panel.visible() ? 'active' : 'inactive'"
      [class]="tabsContentClass()"
    >
      <ng-template ngTabContent>
        <ng-content></ng-content>
      </ng-template>
    </div>
  `,
  host: {
    class: 'contents',
  },
})
export class TabsContentComponent {
  readonly value = input.required<string>();
  readonly class = input<string | undefined>();

  protected readonly tabsContentClass = computed(() =>
    cn(
      'block min-w-0 mt-2 ring-offset-[var(--sanring-surface)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sanring-border-strong)] focus-visible:ring-offset-2',
      this.class(),
    ),
  );
}
