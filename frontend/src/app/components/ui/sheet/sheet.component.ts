import { ChangeDetectionStrategy, Component, inject, model } from '@angular/core';
import { _IdGenerator } from '@angular/cdk/a11y';

@Component({
  selector: 'sanring-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<ng-content></ng-content>`,
})
export class SheetComponent {
  private readonly _id = inject(_IdGenerator).getId('sanring-sheet-', true);

  readonly isOpen = model(false);

  /** 面板 id，供 trigger aria-controls 指向 */
  readonly panelId = `${this._id}-panel`;
  /** 供 SheetTitle 綁定 id，讓面板 aria-labelledby 自動關聯 */
  readonly titleId = `${this._id}-title`;
  /** 供 SheetDescription 綁定 id，讓面板 aria-describedby 自動關聯 */
  readonly descId = `${this._id}-desc`;

  setOpen(open: boolean): void {
    this.isOpen.set(open);
  }
}
