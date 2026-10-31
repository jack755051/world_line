export * from './tabs.component';
export * from './tabs-content.component';
export * from './tabs-list.component';
export * from './tabs-trigger.component';
export * from './tabs.type';

import { TabsContentComponent } from './tabs-content.component';
import { TabsListComponent } from './tabs-list.component';
import { TabsTriggerComponent } from './tabs-trigger.component';
import { TabsComponent } from './tabs.component';

export const SANRING_TABS_IMPORTS = [
  TabsComponent,
  TabsListComponent,
  TabsTriggerComponent,
  TabsContentComponent,
];
