import { patternIds } from './hatch';

describe('patternIds', () => {
  it('collects distinct non-empty wlPattern ids', () => {
    const fc = {
      features: [
        { properties: { wlPattern: 'wl-hatch-contested-c8c0a0' } },
        { properties: { wlPattern: '' } },
        { properties: { wlPattern: 'wl-hatch-contested-c8c0a0' } },
        { properties: { wlPattern: 'wl-hatch-partial-768996' } },
        { properties: null },
      ],
    };
    expect(patternIds(fc)).toEqual(['wl-hatch-contested-c8c0a0', 'wl-hatch-partial-768996']);
  });
  it('handles null collections', () => {
    expect(patternIds(null)).toEqual([]);
  });
});
