export * from './collapsible.component';
export * from './collapsible-trigger.directive';
export * from './collapsible-content.directive';

import { CollapsibleContentDirective } from './collapsible-content.directive';
import { CollapsibleTriggerDirective } from './collapsible-trigger.directive';
import { CollapsibleComponent } from './collapsible.component';

export const SANRING_COLLAPSIBLE_IMPORTS = [
  CollapsibleComponent,
  CollapsibleTriggerDirective,
  CollapsibleContentDirective,
];
