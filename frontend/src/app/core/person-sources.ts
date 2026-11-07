import type { LeaderBio, LeaderBioFieldSource, LeaderPortrait, LeaderRecord, LeaderTerm } from './api/world-line-api';
import type { SourceItem } from '../shared/source-disclosure/source-disclosure';

/** 舊格式自由文字出處 → legacy 來源項（有文字或網址才算；只有「待查證」狀態不算來源）。 */
export function legacyItem(fs: LeaderBioFieldSource | null | undefined): SourceItem | null {
  if (!fs) return null;
  const text = (fs.source ?? '').trim();
  const url = (fs.url ?? '').trim() || null;
  if (!text && !url) return null;
  return { kind: 'legacy', title: text || url!, url, note: fs.note ?? null };
}

/** 某個生平欄位的全部來源：先列結構化引用，再列舊格式出處備註。每個欄位各自判斷，不互相借用。 */
export function fieldSourceItems(bio: LeaderBio, field: string): SourceItem[] {
  const structured: SourceItem[] = (bio.fieldCitations ?? [])
    .filter((c) => c.field === field)
    .map((c) => ({
      kind: 'structured', title: c.source.title, publisher: c.source.publisher, locator: c.locator,
      licenseCode: c.source.licenseCode, url: c.source.url ?? c.source.archiveUrl, note: c.evidenceNote, accessedOn: c.accessedOn,
    }));
  const legacy = legacyItem(bio.fieldSources?.[field]);
  return legacy ? [...structured, legacy] : structured;
}

/** 任期的出處（leader_records.source 自由文字＋網址，屬舊格式）。 */
export function termSourceItems(t: Pick<LeaderTerm | LeaderRecord, 'source' | 'sourceUrl'>): SourceItem[] {
  const text = (t.source ?? '').trim();
  if (!text && !t.sourceUrl) return [];
  return [{ kind: 'legacy', title: text || t.sourceUrl!, url: t.sourceUrl ?? null }];
}

/** 照片出處（授權、作者、署名、查證日期）。 */
export function portraitSourceItems(p: LeaderPortrait): SourceItem[] {
  return [{
    kind: 'structured', title: p.attribution, publisher: p.author, url: p.sourceUrl,
    licenseCode: p.licenseCode, accessedOn: p.retrievedOn, note: p.licenseUrl ? `License: ${p.licenseUrl}` : null,
  }];
}
