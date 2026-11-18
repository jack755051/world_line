import type { SourceItem } from '../shared/source-disclosure/source-disclosure';

/** 某個欄位（或段落）用到的來源。 */
export interface FieldSources { key: string; label: string; items: SourceItem[] }
/** 編了號的來源：n＝上標編號；usedFor＝哪些欄位用到它。 */
export interface Footnote { n: number; item: SourceItem; usedFor: string[] }

/**
 * 把各欄位的來源編成一份不重複的編號清單（人物彈窗與國界卡片共用，Tai 2026-11-14：資料來源統一成人物彈窗那種）。
 * 內容旁邊只放上標編號；出處本身統一列在「資料來源」區。同一筆來源被多個欄位用到時只列一次、共用同一個編號。
 */
export function numberSources(fields: readonly FieldSources[]): { list: Footnote[]; fieldNotes: Map<string, number[]> } {
  const list: Footnote[] = [];
  const byKey = new Map<string, Footnote>();
  const fieldNotes = new Map<string, number[]>();
  for (const f of fields) {
    const ns: number[] = [];
    for (const it of f.items) {
      const k = [it.kind, it.title, it.url ?? '', it.locator ?? '', it.note ?? '', it.licenseCode ?? '', it.quote ?? ''].join('\u0001');
      let fn = byKey.get(k);
      if (!fn) { fn = { n: list.length + 1, item: it, usedFor: [] }; byKey.set(k, fn); list.push(fn); }
      if (!fn.usedFor.includes(f.label)) fn.usedFor.push(f.label);
      if (!ns.includes(fn.n)) ns.push(fn.n);
    }
    fieldNotes.set(f.key, ns);
  }
  return { list, fieldNotes };
}
