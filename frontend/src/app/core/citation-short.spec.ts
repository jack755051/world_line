import { shortCitation, shortSourceTitle } from './citation-short';

describe('citation-short（出處簡短引用）', () => {
  it('FRUS：年份＋卷次', () => {
    expect(shortSourceTitle('Foreign Relations of the United States, Diplomatic Papers, 1939, General, Volume I')).toBe('FRUS 1939 I');
    expect(shortSourceTitle('Foreign Relations of the United States, Diplomatic Papers, 1940, The British Commonwealth, The Soviet Union, The Near East and Africa, Volume III')).toBe('FRUS 1940 III');
    expect(shortCitation({ sourceTitle: 'Foreign Relations of the United States, Diplomatic Papers, 1939, General, Volume I', locator: 'Doc. 514, p. 495' }))
      .toBe('FRUS 1939 I, Doc. 514, p. 495');
  });

  it('DGFP：系列／卷次（Volume 或 Vol.）', () => {
    expect(shortCitation({
      sourceTitle: 'Documents on German Foreign Policy 1918–1945, Series D (1937–1945), Volume VIII: The War Years, September 4, 1939–March 18, 1940（美國國務院版）',
      locator: 'Doc. 157, pp. 164–165',
    })).toBe('DGFP D/VIII, Doc. 157, pp. 164–165');
    expect(shortSourceTitle('Documents on German Foreign Policy 1918–1945, Series D (1937–1945), Vol. IX: The War Years, March 18–June 22, 1940')).toBe('DGFP D/IX');
  });

  it('NCA（Nazi Conspiracy and Aggression）：卷次', () => {
    expect(shortCitation({
      sourceTitle: 'Nazi Conspiracy and Aggression, Volume IV（Office of United States Chief of Counsel for Prosecution of Axis Criminality）',
      locator: 'Doc. 1997-PS, pp. 634–635',
    })).toBe('NCA IV, Doc. 1997-PS, pp. 634–635');
  });

  it('其他來源：取第一段，過長截斷；沒有 locator 只給書名', () => {
    expect(shortSourceTitle('OpenHistoricalMap')).toBe('OpenHistoricalMap');
    expect(shortSourceTitle('Some Very Long Source Title That Goes On And On Without Any Comma At All')).toHaveLength(40);
    expect(shortCitation({ sourceTitle: 'Treaty Series, vol. 1', locator: '' })).toBe('Treaty Series');
  });
});
