import { Directive, inject } from '@angular/core';
import { SheetComponent } from './sheet.component';

@Directive({
  selector: '[sanringSheetTrigger]',
  standalone: true,
  host: {
    '(click)': 'onClick()',
    'aria-haspopup': 'dialog',
    '[attr.aria-expanded]': 'sheet.isOpen() ? "true" : "false"',
    // aria-controls 只在 open 時出現，關閉後移除（避免指向已 inert 的面板）
    '[attr.aria-controls]': 'sheet.isOpen() ? sheet.panelId : null',
  },
})
export class SheetTriggerDirective {
  protected readonly sheet = inject(SheetComponent);

  protected onClick(): void {
    this.sheet.setOpen(true);
  }
}
