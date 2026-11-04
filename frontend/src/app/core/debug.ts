/** 除錯模式（§13 K3）：網址帶 `debug=1`，或 localStorage `wl-debug`＝'1'。技術說明（例：衝突「圖示位置」）只在除錯模式顯示。 */
export function isDebugMode(win: Window | null | undefined = typeof window !== 'undefined' ? window : null): boolean {
  if (!win) return false;
  try {
    if (new URLSearchParams(win.location.search).get('debug') === '1') return true;
    return win.localStorage?.getItem('wl-debug') === '1';
  } catch {
    return false;
  }
}
