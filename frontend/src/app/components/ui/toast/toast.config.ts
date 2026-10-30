import { InjectionToken } from '@angular/core';

export interface ToastConfig {
  /** 同時保留在佇列中的最大數量（超過舊的會被移除）。預設 5 */
  maxVisible: number;
  /** 自動關閉延遲（ms）；0 = 永久顯示。預設 5000 */
  defaultDuration: number;
  /** 關閉按鈕的 aria-label，供 i18n 覆蓋。預設 'Dismiss notification' */
  dismissLabel: string;
}

export const TOAST_CONFIG = new InjectionToken<ToastConfig>('sanring.TOAST_CONFIG', {
  factory: () => ({
    maxVisible: 5,
    defaultDuration: 5000,
    dismissLabel: 'Dismiss notification',
  }),
});
