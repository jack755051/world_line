import type { BioDetailCitation, LeaderBio, LeaderBioFieldSource, LeaderPortrait, LeaderRecord, LeaderTerm } from './api/world-line-api';
import type { SourceItem } from '../shared/source-disclosure/source-disclosure';

/** 舊格式自由文字出處 → legacy 來源項（有文字或網址才算；只有「待查證」狀態不算來源）。 */
export function legacyItem(fs: LeaderBioFieldSource | null | undefined): SourceItem | null {
  if (!fs) return null;
  // 說法衝突（兩個合格出處說法不同，docs/source-rules.md §5）：沒有出處文字也要顯示兩說，否則畫面只看得到一個值
  if (fs.status === '說法衝突' && (fs.note ?? '').trim()) {
    return { kind: 'legacy', title: '說法衝突', note: stripRunTag(fs.note!) };
  }
  const text = (fs.source ?? '').trim();
  const url = (fs.url ?? '').trim() || null;
  if (!text && !url) return null;
  return { kind: 'legacy', title: text || url!, url, note: fs.note ?? null };
}

/** 去掉說明文字結尾的內部批次代號（例：「（rule-corrections-2026-11-14）」），不顯示給讀者。 */
export function stripRunTag(note: string): string {
  return note.replace(/（[a-z0-9-]+-\d{4}-\d{2}-\d{2}）/g, '').trim();
}

/** 某個生平欄位的全部來源：先列結構化引用，再列舊格式出處備註。每個欄位各自判斷，不互相借用。 */
export function fieldSourceItems(bio: LeaderBio, field: string): SourceItem[] {
  const structured: SourceItem[] = (bio.fieldCitations ?? [])
    .filter((c) => c.field === field)
    .map((c) => ({
      kind: 'structured', title: c.source.title, publisher: c.source.publisher, locator: c.locator,
      licenseCode: c.source.licenseCode, url: c.source.url ?? c.source.archiveUrl, note: c.evidenceNote, accessedOn: c.accessedOn,
      quote: c.quote ?? null, quoteLang: c.quoteLang ?? null, grade: c.grade ?? null, sourceKind: c.source.sourceKind ?? null,
    }));
  const legacy = legacyItem(bio.fieldSources?.[field]);
  return legacy ? [...structured, legacy] : structured;
}

/** 任期的出處：先列結構化引文（leader_record_citations，帶等級），再列舊格式自由文字出處（leader_records.source＋網址）。 */
export function termSourceItems(t: Pick<LeaderTerm | LeaderRecord, 'source' | 'sourceUrl'> & { citations?: readonly BioDetailCitation[] | null }): SourceItem[] {
  const structured = detailCitationItems(t.citations);
  const text = (t.source ?? '').trim();
  if (!text && !t.sourceUrl) return structured;
  return [...structured, { kind: 'legacy', title: text || t.sourceUrl!, url: t.sourceUrl ?? null }];
}

/** 照片出處（授權、作者、署名、查證日期）。 */
export function portraitSourceItems(p: LeaderPortrait): SourceItem[] {
  return [{
    kind: 'structured', title: p.attribution, publisher: p.author, url: p.sourceUrl,
    licenseCode: p.licenseCode, accessedOn: p.retrievedOn, note: p.licenseUrl ? `License: ${p.licenseUrl}` : null,
  }];
}

/** B3 段落／經歷／角色的引文 → 來源項（結構化；帶等級）。 */
export function detailCitationItems(cs: readonly BioDetailCitation[] | null | undefined): SourceItem[] {
  return (cs ?? []).map((c) => ({
    kind: 'structured', title: c.source.title, publisher: c.source.publisher, locator: c.locator,
    licenseCode: c.source.licenseCode, url: c.source.url ?? c.source.archiveUrl, note: c.evidenceNote, accessedOn: c.accessedOn,
    quote: c.quote || null, quoteLang: c.quoteLang ?? null, grade: c.grade ?? null, sourceKind: c.source.sourceKind ?? null,
  }));
}
