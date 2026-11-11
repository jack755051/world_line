import { sourceKindLabel } from './source-kinds';

describe('sourceKindLabel', () => {
  it('archive＝檔案典藏／Archives', () => {
    expect(sourceKindLabel('archive', 'zh-Hant')).toBe('檔案典藏');
    expect(sourceKindLabel('archive', 'en')).toBe('Archives');
  });

  it('其他現有種類都有中英標籤', () => {
    const kinds = ['map', 'atlas_map', 'treaty', 'official_record', 'trial_record', 'peer_reviewed', 'official_history', 'dataset', 'encyclopedia', 'official_website', 'archive'];
    for (const k of kinds) {
      expect(sourceKindLabel(k, 'zh-Hant')).toBeTruthy();
      expect(sourceKindLabel(k, 'en')).toBeTruthy();
    }
    expect(sourceKindLabel('official_record', 'zh-Hant')).toBe('官方紀錄');
    expect(sourceKindLabel('official_history', 'zh-Hant')).toBe('官方戰史');
    expect(sourceKindLabel('encyclopedia', 'zh-Hant')).toBe('百科');
    expect(sourceKindLabel('official_website', 'zh-Hant')).toBe('官方網站');
  });

  it('未知或空值不顯示', () => {
    expect(sourceKindLabel('reference_work', 'zh-Hant')).toBeNull();
    expect(sourceKindLabel(null, 'en')).toBeNull();
  });
});
