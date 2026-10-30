import type { RegimeDto } from './api/api-types';
import { localized, type Lang } from './i18n';

/** 政權顯示名：預設用自稱（憲法 §6 命名機制、PRD §8.2「政權標籤預設顯示自稱」）。 */
export function regimeSelfName(r: RegimeDto | undefined, lang: Lang): { display: string; original: string; untranslated: boolean } | null {
  if (!r) return null;
  const self = r.names.find((n) => n.nameKind === 'self' && n.isPrimary) ?? r.names.find((n) => n.nameKind === 'self') ?? r.names[0];
  if (!self) return null;
  const l = localized(self.display as Record<string, string>, lang);
  return { display: l.text || self.originalText, original: self.originalText, untranslated: l.untranslated };
}
