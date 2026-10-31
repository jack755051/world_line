import { Directive, inject } from '@angular/core';
import { SheetComponent } from './sheet.component';

@Directive({
  selector: '[sanringSheetClose]',
  standalone: true,
  host: {
    '(click)': 'onClick()',
  },
})
export class SheetCloseDirective {
  protected readonly sheet = inject(SheetComponent);

  protected onClick(): void {
    this.sheet.setOpen(false);
  }
}
