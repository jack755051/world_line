import { Directive, inject } from '@angular/core';
import { CollapsibleComponent } from './collapsible.component';

@Directive({
  selector: '[sanringCollapsibleContent]',
  standalone: true,
  host: {
    // No role="region" here: the WAI-ARIA disclosure pattern doesn't require
    // one on the panel (aria-labelledby is enough), and a hardcoded role would
    // silently clobber a host element's own semantic role — e.g. sidebar's
    // submenu (sanring-sidebar-menu-sub, role="list") used with this directive,
    // which broke its listitem children's required-parent relationship.
    '[id]': 'collapsible.contentId',
    '[hidden]': '!collapsible.open()',
    '[attr.aria-labelledby]': 'collapsible.triggerId',
  },
})
export class CollapsibleContentDirective {
  protected readonly collapsible = inject(CollapsibleComponent);
}
