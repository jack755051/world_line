import type { components } from './api-schema';
import type { CapitalRecord } from './api/world-line-api';
import type { SourceItem } from '../shared/source-disclosure/source-disclosure';

type CitationDto = components['schemas']['CitationDto'];

/**
 * 國界卡片的資料來源 → 共用的來源項（與人物卡同一個 wl-source-disclosure 元件；Tai 2026-11-14：出處獨立成自己的區塊）。
 * 卡片只負責決定「哪一欄用哪一組來源」，怎麼顯示交給來源元件。
 */

/** 結構化引文（主權紀錄本身的引文、事件引文）：帶等級。 */
export function citationItems(cs: readonly CitationDto[] | null | undefined): SourceItem[] {
  return (cs ?? []).map((c) => ({
    kind: 'structured', title: c.sourceTitle, publisher: c.publisher ?? null, locator: c.locator,
    licenseCode: c.licenseCode ?? null, note: c.evidenceNote ?? null, grade: c.grade ?? null,
  }));
}

/** 首都的出處：目前是自由文字（capital_records.source_ref，尚未接到來源登記），列為舊格式出處備註；「待查證」開頭的不算出處。 */
export function capitalSourceItems(cap: Pick<CapitalRecord, 'sourceRef'> | null | undefined, title: string): SourceItem[] {
  const text = (cap?.sourceRef ?? '').trim();
  if (!text || text.startsWith('待查證')) return [];
  // 短的（一行）直接當標題；長的放進說明，標題用欄位名，避免整段擠在標題列
  return text.length <= 60 ? [{ kind: 'legacy', title: text }] : [{ kind: 'legacy', title, note: text }];
}
