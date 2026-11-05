import type { LocalizedText } from './api/api-types';

export type Lang = 'zh-Hant' | 'en';

/**
 * 介面文字（R4：中英雙語）。內容資料（政權名、快照標題）來自 API 的 LocalizedText，不在這裡。
 * 文案依 PRD §8 與 DESIGN.md；英文為對應翻譯。
 */
const DICT = {
  'app.copyright': { 'zh-Hant': '© 2026 Sanring Tech. All rights reserved.', en: '© 2026 Sanring Tech. All rights reserved.' },
  'app.credit': { 'zh-Hant': '開發者 Charlie Tai', en: 'Developed by Charlie Tai' },
  'app.name': { 'zh-Hant': 'Sanring World Line', en: 'Sanring World Line' },
  'axis.control': { 'zh-Hant': '實際控制', en: 'Control' },
  'axis.sovereignty': { 'zh-Hant': '主權', en: 'Sovereignty' },
  'axis.sovereignty.unavailable': { 'zh-Hant': '主權檢視尚未建置（主權資料與 API 屬 M1 之後）', en: 'Sovereignty view not built yet (after M1)' },
  'legend.toggle': { 'zh-Hant': '圖例', en: 'Legend' },
  'legend.controlTypes.note': { 'zh-Hant': '填色＝陣營；紋理與邊框＝控制類型。樣本以四個陣營色並排示意，不代表任何一個陣營。', en: 'Fill = camp; texture and border = control type. Samples show all four camp colors side by side and do not stand for any one camp.' },
  'legend.regimes.note': { 'zh-Hant': '同陣營同填色；政權以邊框和地圖上的名稱標籤區分。', en: 'Regimes in one camp share a fill; they are told apart by borders and name labels on the map.' },
  'legend.title': { 'zh-Hant': '圖例', en: 'Legend' },
  'legend.mode.control': { 'zh-Hant': '實際控制模式', en: 'Control view' },
  'legend.controlTypes': { 'zh-Hant': '控制類型', en: 'Control types' },
  'legend.evidence': { 'zh-Hant': '史料狀態', en: 'Evidence' },
  'legend.camps': { 'zh-Hant': '陣營', en: 'Camps' },
  'legend.camps.unassigned': { 'zh-Hant': '陣營依有來源的正式加入日判定；當日沒有陣營資料的政權以「陣營未建置」色顯示', en: 'Camps follow sourced formal accession dates; regimes without camp data for the date use the “camp not built” tone' },
  'legend.campUnassigned': { 'zh-Hant': '陣營未建置', en: 'Camp not built' },
  'legend.regimes': { 'zh-Hant': '目前畫面中的政權', en: 'Regimes on the map' },
  'legend.regimes.empty': { 'zh-Hant': '目前畫面無資料', en: 'No data on the map' },
  'legend.regimes.error': { 'zh-Hant': '清單載入失敗', en: 'Failed to load list' },
  'legend.gap': { 'zh-Hant': '控制資料缺', en: 'No control data' },
  'legend.gap.note': { 'zh-Hant': '沒有合格來源可判斷實際控制，並非不完全控制', en: 'No qualified source to judge actual control; not “partial control”' },
  'gap.reason': { 'zh-Hant': '原因', en: 'Reason' },
  'gap.reason.no_qualified_source': { 'zh-Hant': '已調查，沒有合格來源', en: 'Researched; no qualified source' },
  'gap.reason.not_yet_digitized': { 'zh-Hant': '尚未建置（地圖未涵蓋）', en: 'Not yet built (not covered by the map)' },
  'gap.note': { 'zh-Hant': '說明', en: 'Note' },
  'gap.ref': { 'zh-Hant': '研究紀錄', en: 'Research ref.' },
  'card.supplement': { 'zh-Hant': '補充', en: 'Supplement' },
  'card.supplement.note': { 'zh-Hant': '有紀錄，但不作為陣營判定依據', en: 'On record; not used to determine the camp' },
  'legend.frontline': { 'zh-Hant': '戰線', en: 'Front line' },
  'control.direct_rule': { 'zh-Hant': '直接統治', en: 'Direct rule' },
  'control.military_occupation': { 'zh-Hant': '軍事佔領', en: 'Military occupation' },
  'control.puppet_administration': { 'zh-Hant': '傀儡代管', en: 'Puppet administration' },
  'control.partial': { 'zh-Hant': '不完全控制', en: 'Partial control' },
  'control.contested': { 'zh-Hant': '交戰中', en: 'Contested' },
  'camp.axis': { 'zh-Hant': '軸心', en: 'Axis' },
  'camp.allies': { 'zh-Hant': '同盟', en: 'Allies' },
  'camp.cobelligerent': { 'zh-Hant': '共同交戰／合作', en: 'Co-belligerent' },
  'camp.neutral': { 'zh-Hant': '中立／未結盟', en: 'Neutral' },
  'evidence.attested': { 'zh-Hant': '史料快照', en: 'Attested snapshot' },
  'evidence.interpolated': { 'zh-Hant': '推估過渡', en: 'Interpolated' },
  'evidence.unknown': { 'zh-Hant': '無法判斷史料或推估', en: 'Cannot tell attested or interpolated' },
  'evidence.outside': { 'zh-Hant': '在史料快照範圍外（以推估樣式呈現）', en: 'Outside snapshot range (shown as interpolated)' },
  'chip.attested': { 'zh-Hant': '史料快照', en: 'Attested' },
  'chip.interpolated': { 'zh-Hant': '推估過渡・{n} 個戰區', en: 'Interpolated · {n} theaters' },
  'chip.unknown': { 'zh-Hant': '無法判斷史料或推估', en: 'Cannot tell attested or interpolated' },
  'chip.popover.title': { 'zh-Hant': '推估過渡，非史料', en: 'Interpolated, not attested' },
  'chip.popover.between': { 'zh-Hant': '介於 {prev} 與 {next} 史料快照之間', en: 'Between snapshots {prev} and {next}' },
  'chip.popover.outside': { 'zh-Hant': '在史料快照範圍外（{ref}）', en: 'Outside snapshot range ({ref})' },
  'chip.jumpPrev': { 'zh-Hant': '跳到前一快照', en: 'Previous snapshot' },
  'chip.jumpNext': { 'zh-Hant': '跳到後一快照', en: 'Next snapshot' },
  'map.loading': { 'zh-Hant': '載入 {date} 的資料…', en: 'Loading data for {date}…' },
  'map.busy': { 'zh-Hant': '載入中', en: 'Loading' },
  'map.empty': { 'zh-Hant': '此日期尚無資料', en: 'No data for this date' },
  'map.emptyJump': { 'zh-Hant': '跳到最近有資料的日期', en: 'Jump to nearest date with data' },
  'map.error': { 'zh-Hant': '地圖資料載入失敗', en: 'Failed to load map data' },
  'map.errorShowing': { 'zh-Hant': '顯示的是 {date} 的資料', en: 'Showing data for {date}' },
  'map.retry': { 'zh-Hant': '重試', en: 'Retry' },
  'notFound.title': { 'zh-Hant': '找不到頁面', en: 'Page not found' },
  'notFound.back': { 'zh-Hant': '回主地圖', en: 'Back to the map' },
  'map.incomplete': { 'zh-Hant': '本時段資料不保證完整', en: 'Data for this period may be incomplete' },
  'map.engineError': { 'zh-Hant': '地圖引擎無法啟動（瀏覽器不支援 WebGL）', en: 'Map engine failed to start (WebGL unavailable)' },
  'map.basemapAttribution': { 'zh-Hant': '底圖：Natural Earth（公有領域）', en: 'Base map: Natural Earth (public domain)' },
  'card.evidence': { 'zh-Hant': '史料狀態', en: 'Evidence' },
  'card.validPeriod': { 'zh-Hant': '有效期間', en: 'Valid period' },
  'card.theater': { 'zh-Hant': '戰區', en: 'Theater' },
  'card.camp': { 'zh-Hant': '陣營', en: 'Camp' },
  'card.campBasis': { 'zh-Hant': '依據', en: 'Basis' },
  'card.disputed': { 'zh-Hant': '爭議並存', en: 'Disputed' },
  'card.close': { 'zh-Hant': '關閉', en: 'Close' },
  'card.uncertain': { 'zh-Hant': '不確定區間', en: 'uncertain' },
  'citation.button': { 'zh-Hant': '來源', en: 'Sources' },
  'citation.title': { 'zh-Hant': '來源', en: 'Sources' },
  'citation.publisher': { 'zh-Hant': '出版者', en: 'Publisher' },
  'citation.authors': { 'zh-Hant': '作者', en: 'Authors' },
  'citation.published': { 'zh-Hant': '出版日期', en: 'Published' },
  'citation.locator': { 'zh-Hant': '圖號／頁碼', en: 'Locator' },
  'citation.role': { 'zh-Hant': '引用角色', en: 'Role' },
  'citation.note': { 'zh-Hant': '依據說明', en: 'Evidence note' },
  'citation.license': { 'zh-Hant': '授權', en: 'License' },
  'citation.licenseEvidence': { 'zh-Hant': '授權依據', en: 'License basis' },
  'citation.licenseNone': { 'zh-Hant': '未標註（非主要地圖來源）', en: 'Not stated (not a primary map source)' },
  'citation.catalog': { 'zh-Hant': '館藏號', en: 'Catalog no.' },
  'citation.url': { 'zh-Hant': '原始連結', en: 'Original' },
  'citation.archive': { 'zh-Hant': '存檔連結', en: 'Archive' },
  'citation.missing': { 'zh-Hant': '此紀錄缺少來源（資料錯誤）', en: 'This record has no source (data error)' },
  'citation.loading': { 'zh-Hant': '正在載入來源…', en: 'Loading sources…' },
  'citation.detailError': { 'zh-Hant': '來源詳情載入失敗', en: 'Failed to load source details' },
  'citation.role.primary': { 'zh-Hant': '主要', en: 'Primary' },
  'citation.role.auxiliary_geometry': { 'zh-Hant': '輔助幾何', en: 'Auxiliary geometry' },
  'citation.role.date_check': { 'zh-Hant': '日期核對', en: 'Date check' },
  'timeline.prev': { 'zh-Hant': '上一個快照', en: 'Previous snapshot' },
  'timeline.next': { 'zh-Hant': '下一個快照', en: 'Next snapshot' },
  'timeline.play': { 'zh-Hant': '播放', en: 'Play' },
  'timeline.pause': { 'zh-Hant': '暫停', en: 'Pause' },
  'timeline.speed': { 'zh-Hant': '播放速度', en: 'Speed' },
  'timeline.speed.week': { 'zh-Hant': '1 週/秒', en: '1 wk/s' },
  'timeline.speed.month': { 'zh-Hant': '1 月/秒', en: '1 mo/s' },
  'timeline.speed.toggle': { 'zh-Hant': '點擊切換每秒 1 週／1 月', en: 'Click to switch 1 week / 1 month per second' },
  'timeline.dateInput': { 'zh-Hant': '日期', en: 'Date' },
  'timeline.error': { 'zh-Hant': '快照標記載入失敗', en: 'Failed to load snapshot markers' },
  'timeline.noSnapshots': { 'zh-Hant': '控制資料缺', en: 'No control data' },
  'timeline.incomplete': { 'zh-Hant': '資料不保證完整', en: 'Data not guaranteed complete' },
  'timeline.handle': { 'zh-Hant': '目前日期', en: 'Current date' },
  'timeline.speed.day': { 'zh-Hant': '1 日/秒', en: '1 day/s' },
  'timeline.menu': { 'zh-Hant': '更多選項', en: 'More options' },
  'timeline.key.space': { 'zh-Hant': '空白鍵', en: 'Space' },
  'timeline.keys': { 'zh-Hant': '空白鍵 播放／暫停・←／→ 一週・Shift＋←／→ 一年', en: 'Space play/pause · ←/→ one week · Shift+←/→ one year' },
  'timeline.incomplete.toast': { 'zh-Hant': '1937 年 7 月以前的資料不保證完整；日期旁的 ⓘ 表示目前位於這段期間', en: 'Data before July 1937 may be incomplete; the ⓘ next to the date marks this period' },
  'offline.title': { 'zh-Hant': '無法連線到 Sanring World Line API', en: 'Cannot reach the Sanring World Line API' },
  'offline.health': { 'zh-Hant': '服務狀態：{status}', en: 'Service status: {status}' },
  'offline.noResponse': { 'zh-Hant': '無回應', en: 'No response' },
  'toast.invalidDate': { 'zh-Hant': '網址中的日期格式無效，已回到預設日期', en: 'Invalid date in URL; reset to the default date' },
  'untranslated': { 'zh-Hant': '未翻譯', en: 'Untranslated' },
  'theater.west-europe': { 'zh-Hant': '西歐', en: 'Western Europe' },
} as const satisfies Record<string, Record<Lang, string>>;

export type I18nKey = keyof typeof DICT;

export function t(key: I18nKey, lang: Lang, vars?: Record<string, string | number>): string {
  let s: string = DICT[key][lang];
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v));
  return s;
}

export function hasKey(key: string): key is I18nKey {
  return key in DICT;
}

/**
 * 取 LocalizedText 的目前語言；缺翻譯時改用另一語言並回報 untranslated（PRD §8.10）。
 */
export function localized(text: LocalizedText | null | undefined, lang: Lang): { text: string; untranslated: boolean } {
  if (!text) return { text: '', untranslated: false };
  const own = text[lang];
  if (own) return { text: own, untranslated: false };
  const other = text[lang === 'en' ? 'zh-Hant' : 'en'] ?? Object.values(text).find((v) => !!v) ?? '';
  return { text: other, untranslated: !!other };
}
