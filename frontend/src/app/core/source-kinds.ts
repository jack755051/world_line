import type { Lang } from './i18n';

/** 來源種類（sources.source_kind）的中英標籤；用詞對齊 PRD §6.3／後端 Vocabulary.SourceKinds。 */
const LABELS: Record<string, { 'zh-Hant': string; en: string }> = {
  map: { 'zh-Hant': '地圖', en: 'Map' },
  atlas_map: { 'zh-Hant': '圖集地圖', en: 'Atlas map' },
  treaty: { 'zh-Hant': '條約', en: 'Treaty' },
  official_record: { 'zh-Hant': '官方紀錄', en: 'Official record' },
  trial_record: { 'zh-Hant': '審判紀錄', en: 'Trial record' },
  peer_reviewed: { 'zh-Hant': '同行審查研究', en: 'Peer-reviewed research' },
  official_history: { 'zh-Hant': '官方戰史', en: 'Official history' },
  dataset: { 'zh-Hant': '開放資料集', en: 'Dataset' },
  encyclopedia: { 'zh-Hant': '百科', en: 'Encyclopedia' },
  official_website: { 'zh-Hant': '官方網站', en: 'Official website' },
  archive: { 'zh-Hant': '檔案典藏', en: 'Archives' },
};

/** 種類標籤；未知種類回傳 null（不顯示，也不顯示原始代碼）。 */
export function sourceKindLabel(kind: string | null | undefined, lang: Lang): string | null {
  if (!kind) return null;
  return LABELS[kind]?.[lang === 'en' ? 'en' : 'zh-Hant'] ?? null;
}
