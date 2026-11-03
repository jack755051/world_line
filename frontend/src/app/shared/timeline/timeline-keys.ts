/** 時間軸全域快捷鍵（M3-a 方案 A）：空白鍵播放／暫停，←／→ 移一週，Shift＋←／→ 移一年。 */
export type TimelineShortcut = { kind: 'toggle' } | { kind: 'step'; unit: 'week' | 'year'; dir: 1 | -1 };

export interface KeyLike {
  key: string;
  shiftKey?: boolean;
  ctrlKey?: boolean;
  metaKey?: boolean;
  altKey?: boolean;
  defaultPrevented?: boolean;
  target?: EventTarget | null;
}

/** 正在打字或操作表單、選單、滑桿把手（把手自己處理方向鍵）的元素：快捷鍵一律不作用，避免和輸入框衝突。 */
export function isTypingTarget(t: EventTarget | null | undefined): boolean {
  const el = t as (HTMLElement & { isContentEditable?: boolean }) | null | undefined;
  if (!el || typeof el !== 'object' || !('tagName' in el)) return false;
  const tag = String(el.tagName).toUpperCase();
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if (el.isContentEditable) return true;
  const role = el.getAttribute?.('role');
  return role === 'textbox' || role === 'combobox' || role === 'menu' || role === 'menuitem' || role === 'menuitemradio' || role === 'searchbox' || role === 'slider';
}

export function timelineShortcut(e: KeyLike): TimelineShortcut | null {
  if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey) return null;
  if (isTypingTarget(e.target)) return null;
  const tag = (e.target as HTMLElement | null)?.tagName?.toUpperCase?.();
  if (e.key === ' ' || e.key === 'Spacebar') {
    // 焦點在按鈕或連結上時，空白鍵交給該元素本身（避免按播放鍵時切換兩次）
    if (tag === 'BUTTON' || tag === 'A') return null;
    return { kind: 'toggle' };
  }
  if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
    return { kind: 'step', unit: e.shiftKey ? 'year' : 'week', dir: e.key === 'ArrowLeft' ? -1 : 1 };
  }
  return null;
}
