export type ToastType = 'default' | 'success' | 'error' | 'warning' | 'info';

export type ToastPosition =
  | 'top-right'
  | 'top-left'
  | 'top-center'
  | 'bottom-right'
  | 'bottom-left'
  | 'bottom-center';

export interface ToastAction {
  label: string;
  class?: string;
  /** 支援 async action（例如 retry API）；promise settle 後再 dismiss */
  onClick: () => void | Promise<void>;
  /** 點擊 action 後是否自動關閉 toast。預設 true */
  dismissOnAction?: boolean;
}

export interface Toast {
  id: string;
  type: ToastType;
  title?: string;
  description?: string;
  duration: number;   // ms; 0 = persistent
  closable: boolean;
  action?: ToastAction;
  class?: string;
  /** 內部狀態：true 表示退場動畫播放中，DOM 尚未移除。不可由 ToastOptions 設定。 */
  leaving?: boolean;
}

/** 呼叫端可傳入的欄位。不暴露 id（由 service 自動產生）。 */
export interface ToastOptions {
  type?: ToastType;
  title?: string;
  description?: string;
  duration?: number;
  closable?: boolean;
  action?: ToastAction;
  class?: string;
}
