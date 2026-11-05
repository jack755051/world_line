import { describe, expect, it } from 'vitest';
import { isDebugMode } from './debug';

const win = (search: string, ls: string | null = null) => ({ location: { search }, localStorage: { getItem: () => ls } }) as unknown as Window;
describe('isDebugMode（§13 K3）', () => {
  it('預設關閉；debug=1 或 localStorage wl-debug=1 開啟', () => {
    expect(isDebugMode(win(''))).toBe(false);
    expect(isDebugMode(win('?debug=1'))).toBe(true);
    expect(isDebugMode(win('?debug=0'))).toBe(false);
    expect(isDebugMode(win('', '1'))).toBe(true);
    expect(isDebugMode(null)).toBe(false);
  });
});
