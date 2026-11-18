import { breakpointOf, isCompact, isPhone } from './viewport';

describe('viewport（§12 斷點）', () => {
  it('xs 360–599、sm 600–767、md 768–1023、lg 1024–1439、xl ≥1440', () => {
    expect([360, 599, 600, 767, 768, 1023, 1024, 1439, 1440, 1920].map(breakpointOf)).toEqual(['xs', 'xs', 'sm', 'sm', 'md', 'md', 'lg', 'lg', 'xl', 'xl']);
    expect(isPhone('sm')).toBe(true);
    expect(isPhone('md')).toBe(false);
  });
  it('精簡版：手機寬度，或高度小於 500px（手機橫放）', () => {
    expect(isCompact(390, 844)).toBe(true);
    expect(isCompact(844, 390)).toBe(true);
    expect(isCompact(1024, 768)).toBe(false);
  });
});
