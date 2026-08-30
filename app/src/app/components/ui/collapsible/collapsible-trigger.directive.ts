import { Directive, ElementRef, inject } from '@angular/core';
import { CollapsibleComponent } from './collapsible.component';

@Directive({
  selector: '[sanringCollapsibleTrigger]',
  standalone: true,
  host: {
    '[id]': 'collapsible.triggerId',
    '(click)': 'collapsible.toggle()',
    '(keydown.enter)': 'onKeyActivation($event)',
    '(keydown.space)': 'onKeyActivation($event)',
    '[attr.aria-expanded]': 'collapsible.open()',
    '[attr.aria-controls]': 'collapsible.contentId',
    // native <button> 用 disabled 屬性讓瀏覽器擋事件；非 button 用 aria-disabled
    '[attr.disabled]': 'isNativeButton && collapsible.disabled() ? "" : null',
    '[attr.aria-disabled]': '!isNativeButton && collapsible.disabled() ? "true" : null',
    // 非 button 元素補齊原生 button 斷層
    '[attr.role]': 'isNativeButton ? null : "button"',
    '[attr.tabindex]': 'isNativeButton ? null : "0"',
  },
})
export class CollapsibleTriggerDirective {
  protected readonly collapsible = inject(CollapsibleComponent);

  protected readonly isNativeButton =
    inject(ElementRef<HTMLElement>).nativeElement.tagName.toLowerCase() === 'button';

  protected onKeyActivation(event: Event): void {
    event.preventDefault(); // Space 防捲頁，Enter 防 form submit
    this.collapsible.toggle();
  }
}
