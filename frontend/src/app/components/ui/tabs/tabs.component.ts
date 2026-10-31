import { ChangeDetectionStrategy, Component, computed, input, linkedSignal, output } from '@angular/core';
import { Tabs as NgTabs } from '@angular/aria/tabs';
import { cn } from '../shared/utils';
import { TabsOrientation, TabsVariant } from './tabs.type';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'sanring-tabs',
  standalone: true,
  template: `<ng-content></ng-content>`,
  hostDirectives: [NgTabs],
  host: {
    '[attr.data-orientation]': 'orientation()',
    '[class]': 'tabsClass()',
  },
})
export class TabsComponent {
  readonly class = input<string | undefined>();
  readonly orientation = input<TabsOrientation>('horizontal');
  readonly defaultValue = input<string | undefined>();
  readonly variant = input<TabsVariant>('default');

  readonly valueChange = output<string>();

  // linkedSignal: 初始值從 defaultValue 取，使用者切換後保留手動值
  readonly value = linkedSignal<string | undefined, string | undefined>({
    source: this.defaultValue,
    computation: (defaultValue, previous) =>
      previous?.value !== undefined ? previous.value : defaultValue,
  });

  protected readonly tabsClass = computed(() =>
    cn(
      this.orientation() === 'vertical' ? 'grid gap-4 sm:grid-cols-[180px_1fr]' : 'grid gap-3',
      this.class(),
    ),
  );

  setValue(newValue: string | undefined) {
    if (newValue && this.value() !== newValue) {
      this.value.set(newValue);
      this.valueChange.emit(newValue);
    }
  }
}
