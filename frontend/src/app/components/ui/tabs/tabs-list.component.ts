import { ChangeDetectionStrategy, AfterContentInit, Component, computed, effect, inject, input, untracked } from '@angular/core';
import { TabList as NgTabList } from '@angular/aria/tabs';
import { cn } from '../shared/utils';
import { TabsComponent } from './tabs.component';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'sanring-tabs-list',
  standalone: true,
  template: `<ng-content></ng-content>`,
  hostDirectives: [
    {
      directive: NgTabList,
      // orientation 在這裡是獨立的 pass-through input，跟 sanring-tabs 自己的 orientation
      // 沒有自動同步——sanring-tabs 的 orientation 只影響版面 CSS grid 排列跟
      // [attr.data-orientation]，真正驅動鍵盤導覽方向（Arrow Left/Right vs Up/Down）的是
      // 這裡 NgTabList 的 orientation。兩處都要設成一樣的值，否則版面看起來是一個方向、
      // 鍵盤實際導覽卻是另一個方向。曾嘗試用 host binding 讓這裡自動讀 sanring-tabs 的值、
      // 不讓消費者個別覆寫，但 Angular 的 host binding 語法無法綁定到 hostDirectives
      // pass-through 以外的 input（NG8002），只能維持兩處都要手動設定，已在文件中說明。
      inputs: ['orientation', 'selectionMode', 'wrap', 'softDisabled', 'focusMode', 'disabled'],
    },
  ],
  host: {
    '[class]': 'tabsListClass()',
  },
})
export class TabsListComponent implements AfterContentInit {
  readonly class = input<string | undefined>();

  protected tabs = inject(TabsComponent);
  private tabList = inject(NgTabList);
  protected readonly tabsListClass = computed(() => {
    const variant = this.tabs.variant();

    return cn(
      this.tabs.orientation() === 'vertical'
        ? 'inline-grid w-max items-stretch'
        : 'inline-flex w-max items-center justify-center',
      variant === 'default' &&
        'rounded-[var(--sanring-radius)] border border-[var(--sanring-border)] bg-[var(--sanring-surface-strong)] p-0.5 text-[var(--sanring-muted)] shadow-sm',
      variant === 'line' &&
        (this.tabs.orientation() === 'vertical'
          ? 'border-l border-[var(--sanring-border)] bg-transparent p-0'
          : 'justify-start border-b border-[var(--sanring-border)] bg-transparent p-0'),
      this.class(),
    );
  });

  constructor() {
    // 只訂閱 NgTabList 的選取變動；讀 tabs.value() 用 untracked 避免 value 變動再次觸發
    effect(() => {
      const selectedTab = this.tabList.selectedTab();
      if (selectedTab && selectedTab !== untracked(() => this.tabs.value())) {
        this.tabs.setValue(selectedTab);
      }
    });
  }

  ngAfterContentInit() {
    const value = this.tabs.value();

    if (value) {
      this.tabList.selectedTab.set(value);
    }
  }
}
