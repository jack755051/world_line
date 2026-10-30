import { AtlasState, parseAtlasQuery } from './atlas-state';

describe('parseAtlasQuery', () => {
  it('有效日期與語言', () => {
    expect(parseAtlasQuery({ date: '1940-08-15', lang: 'en' })).toEqual({ date: '1940-08-15', lang: 'en', axis: 'control', invalidDate: false });
  });

  it('日期格式錯 → 預設日期並標記（PRD §8.11）', () => {
    const q = parseAtlasQuery({ date: '1940-13-99' });
    expect(q.date).toBe(AtlasState.defaultDate);
    expect(q.invalidDate).toBe(true);
  });

  it('沒帶日期不算錯；主權檢視未建置時一律回到實際控制', () => {
    const q = parseAtlasQuery({ axis: 'sovereignty' });
    expect(q.invalidDate).toBe(false);
    expect(q.axis).toBe('control');
    expect(q.lang).toBe('zh-Hant');
  });
});
