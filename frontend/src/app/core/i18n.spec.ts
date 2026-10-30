import { localized, t } from './i18n';

describe('i18n', () => {
  it('t() 代入變數', () => {
    expect(t('chip.interpolated', 'zh-Hant', { n: 2 })).toBe('推估過渡・2 個戰區');
    expect(t('chip.interpolated', 'en', { n: 2 })).toBe('Interpolated · 2 theaters');
  });

  it('localized：缺翻譯時用另一語言並標記未翻譯（PRD §8.10）', () => {
    expect(localized({ 'zh-Hant': '德意志國', en: 'German Reich' }, 'en')).toEqual({ text: 'German Reich', untranslated: false });
    expect(localized({ 'zh-Hant': '德意志國' }, 'en')).toEqual({ text: '德意志國', untranslated: true });
    expect(localized(null, 'en')).toEqual({ text: '', untranslated: false });
  });
});
