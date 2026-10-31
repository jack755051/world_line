/**
 * 出處簡短引用（資訊卡預設顯示；點開才看完整書目）。
 * 只從 API 回傳的 sourceTitle／locator 縮寫，不新增任何書目資訊：
 * - Foreign Relations of the United States, Diplomatic Papers, 1939, General, Volume I → FRUS 1939 I
 * - Documents on German Foreign Policy 1918–1945, Series D (1937–1945), Volume VIII … → DGFP D/VIII
 * 其他來源：取書名第一段（逗號前），過長截斷。
 */
const ROMAN = '([IVXLC]+)';

export function shortSourceTitle(title: string): string {
  const t = title.trim();
  const frus = new RegExp(`^Foreign Relations of the United States\\b.*?\\b(1[89]\\d{2})\\b.*?\\bVol(?:ume|\\.)\\s*${ROMAN}\\b`).exec(t);
  if (frus) return `FRUS ${frus[1]} ${frus[2]}`;
  const dgfp = new RegExp(`^Documents on German Foreign Policy\\b.*?\\bSeries\\s+([A-E])\\b.*?\\bVol(?:ume|\\.)\\s*${ROMAN}\\b`).exec(t);
  if (dgfp) return `DGFP ${dgfp[1]}/${dgfp[2]}`;
  const head = t.split(/[,，（(:：]/)[0].trim() || t;
  return head.length > 40 ? `${head.slice(0, 39)}…` : head;
}

export function shortCitation(c: { sourceTitle: string; locator: string }): string {
  const loc = (c.locator ?? '').trim();
  const src = shortSourceTitle(c.sourceTitle ?? '');
  return loc ? `${src}, ${loc}` : src;
}
