import type { Lang } from './i18n';

export interface TheaterTrack {
  code: string;
  label: Record<Lang, string>;
  /** true＝資料庫已有此戰區（目前只有 west-europe）；false＝依設計稿列出、尚未建置的戰區。 */
  provisional: boolean;
}

/**
 * 時間軸的五條戰區軌道（DESIGN.md Timeline；docs/ww2-stitch.md：「西歐」「東線」「北非」「太平洋」「中國」）。
 * ⚠ PRD §12 Q5（戰區劃分與清單）尚未拍板：除 `west-europe`（資料庫既有代碼）外，其餘四個代碼是前端暫定的顯示用代碼，
 * 不代表資料庫有這些戰區；它們沒有任何快照，依 R9 以「控制資料缺」樣式顯示。API 回傳清單外的戰區時會自動追加一條軌道。
 */
export const THEATER_TRACKS: readonly TheaterTrack[] = [
  { code: 'west-europe', label: { 'zh-Hant': '西歐', en: 'W. Europe' }, provisional: false },
  { code: 'east-front', label: { 'zh-Hant': '東線', en: 'Eastern' }, provisional: true },
  { code: 'north-africa', label: { 'zh-Hant': '北非', en: 'N. Africa' }, provisional: true },
  { code: 'pacific', label: { 'zh-Hant': '太平洋', en: 'Pacific' }, provisional: true },
  { code: 'china', label: { 'zh-Hant': '中國', en: 'China' }, provisional: true },
];

export function theaterLabel(code: string, lang: Lang): string {
  return THEATER_TRACKS.find((t) => t.code === code)?.label[lang] ?? code;
}

/** 五條固定軌道＋API 出現但不在清單內的戰區。 */
export function tracksFor(codes: readonly string[]): TheaterTrack[] {
  const extra = codes
    .filter((c, i) => codes.indexOf(c) === i && !THEATER_TRACKS.some((t) => t.code === c))
    .map((c) => ({ code: c, label: { 'zh-Hant': c, en: c }, provisional: false }));
  return [...THEATER_TRACKS, ...extra];
}
