export * from './sheet.component';
export * from './sheet-content.component';
export * from './sheet-header.component';
export * from './sheet-footer.component';
export * from './sheet-title.component';
export * from './sheet-description.component';
export * from './sheet-trigger.directive';
export * from './sheet-close.directive';
export * from './sheet.type';

// 便利陣列：imports: [SANRING_SHEET_IMPORTS] 一行搞定
import { SheetComponent } from './sheet.component';
import { SheetContentComponent } from './sheet-content.component';
import { SheetHeaderComponent } from './sheet-header.component';
import { SheetFooterComponent } from './sheet-footer.component';
import { SheetTitleComponent } from './sheet-title.component';
import { SheetDescriptionComponent } from './sheet-description.component';
import { SheetTriggerDirective } from './sheet-trigger.directive';
import { SheetCloseDirective } from './sheet-close.directive';

export const SANRING_SHEET_IMPORTS = [
  SheetComponent,
  SheetContentComponent,
  SheetHeaderComponent,
  SheetFooterComponent,
  SheetTitleComponent,
  SheetDescriptionComponent,
  SheetTriggerDirective,
  SheetCloseDirective,
];
