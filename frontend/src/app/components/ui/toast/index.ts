export * from './toast.component';
export * from './toast.config';
export * from './toast.service';
export * from './toaster.component';
export * from './toast.types';

import { ToastComponent } from './toast.component';
import { ToasterComponent } from './toaster.component';

export const SANRING_TOAST_IMPORTS = [
  ToasterComponent,
  ToastComponent,
];
