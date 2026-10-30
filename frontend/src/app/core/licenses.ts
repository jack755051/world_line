import type { Lang } from './i18n';

/** 授權代碼顯示名（R7 允許清單內的代碼；未知代碼原樣顯示）。 */
const LICENSES: Record<string, Record<Lang, string>> = {
  cc0: { 'zh-Hant': 'CC0（公有領域貢獻）', en: 'CC0' },
  public_domain: { 'zh-Hant': '公有領域', en: 'Public domain' },
  us_federal_pd: { 'zh-Hant': '美國聯邦政府著作（公有領域）', en: 'US federal work (public domain)' },
  cc_by: { 'zh-Hant': 'CC BY', en: 'CC BY' },
  cc_by_sa: { 'zh-Hant': 'CC BY-SA', en: 'CC BY-SA' },
  licence_ouverte_2: { 'zh-Hant': 'Licence Ouverte 2.0（法國開放授權）', en: 'Licence Ouverte 2.0' },
};

export function licenseLabel(code: string | null | undefined, lang: Lang): string | null {
  if (!code) return null;
  return LICENSES[code]?.[lang] ?? code;
}
