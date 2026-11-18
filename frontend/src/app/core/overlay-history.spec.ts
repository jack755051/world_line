import { canGoBack, type OverlayMark } from './overlay-history';

describe('canGoBack（設計 §4.3）', () => {
  const mark: OverlayMark = { kind: 'person', token: 't1', baseToken: 'b1' };

  it('目前 entry 是 app 自己 push、緊接在記下的底層之後 → back', () => {
    expect(canGoBack({ wlOverlay: { kind: 'person', token: 't1', baseToken: 'b1' }, navigationId: 3 }, mark)).toBe(true);
  });
  it('深連結／重新整理（服務沒有記錄）→ replace', () => {
    expect(canGoBack({ wlOverlay: { kind: 'person', token: 't1', baseToken: 'b1' } }, null)).toBe(false);
  });
  it('entry 沒有標記（例如對話框開著時日期以 replaceUrl 改寫了這一筆）→ replace', () => {
    expect(canGoBack({ navigationId: 5 }, mark)).toBe(false);
    expect(canGoBack(null, mark)).toBe(false);
  });
  it('token 或底層不符 → replace', () => {
    expect(canGoBack({ wlOverlay: { kind: 'person', token: 'other', baseToken: 'b1' } }, mark)).toBe(false);
    expect(canGoBack({ wlOverlay: { kind: 'person', token: 't1', baseToken: 'b2' } }, mark)).toBe(false);
  });
});
