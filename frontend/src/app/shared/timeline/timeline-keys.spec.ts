import { describe, expect, it } from 'vitest';
import { isTypingTarget, timelineShortcut } from './timeline-keys';

const el = (tagName: string, attrs: Record<string, string> = {}, editable = false) =>
  ({ tagName, isContentEditable: editable, getAttribute: (k: string) => attrs[k] ?? null }) as unknown as EventTarget;

describe('timelineShortcut', () => {
  it('空白鍵切換播放', () => {
    expect(timelineShortcut({ key: ' ', target: el('DIV') })).toEqual({ kind: 'toggle' });
  });
  it('←／→ 移一週，Shift 移一年', () => {
    expect(timelineShortcut({ key: 'ArrowLeft', target: el('BODY') })).toEqual({ kind: 'step', unit: 'week', dir: -1 });
    expect(timelineShortcut({ key: 'ArrowRight', target: el('BODY') })).toEqual({ kind: 'step', unit: 'week', dir: 1 });
    expect(timelineShortcut({ key: 'ArrowRight', shiftKey: true, target: el('BODY') })).toEqual({ kind: 'step', unit: 'year', dir: 1 });
    expect(timelineShortcut({ key: 'ArrowLeft', shiftKey: true, target: el('BODY') })).toEqual({ kind: 'step', unit: 'year', dir: -1 });
  });
  it('輸入框、textarea、contenteditable、選單裡不作用', () => {
    for (const t of [el('INPUT'), el('TEXTAREA'), el('SELECT'), el('DIV', {}, true), el('DIV', { role: 'menu' }), el('BUTTON', { role: 'menuitemradio' }), el('DIV', { role: 'slider' })]) {
      expect(isTypingTarget(t)).toBe(true);
      expect(timelineShortcut({ key: 'ArrowLeft', target: t })).toBeNull();
      expect(timelineShortcut({ key: ' ', target: t })).toBeNull();
    }
  });
  it('焦點在按鈕上時空白鍵交給按鈕；方向鍵仍作用', () => {
    expect(timelineShortcut({ key: ' ', target: el('BUTTON') })).toBeNull();
    expect(timelineShortcut({ key: 'ArrowRight', target: el('BUTTON') })).toEqual({ kind: 'step', unit: 'week', dir: 1 });
  });
  it('有修飾鍵或已被處理時不作用', () => {
    expect(timelineShortcut({ key: 'ArrowLeft', metaKey: true, target: el('BODY') })).toBeNull();
    expect(timelineShortcut({ key: 'ArrowLeft', ctrlKey: true, target: el('BODY') })).toBeNull();
    expect(timelineShortcut({ key: 'ArrowLeft', altKey: true, target: el('BODY') })).toBeNull();
    expect(timelineShortcut({ key: 'ArrowLeft', defaultPrevented: true, target: el('BODY') })).toBeNull();
    expect(timelineShortcut({ key: 'a', target: el('BODY') })).toBeNull();
  });
});
