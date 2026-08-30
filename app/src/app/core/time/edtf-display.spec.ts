import { formatEdtfDateLabel, formatEdtfQualifierLabel, formatEdtfYear, parseEdtf } from './edtf-display';

describe('parseEdtf', () => {
  it('年精度：只有 4 位數字年份', () => {
    expect(parseEdtf('0208')).toEqual({ precision: 'year', qualifier: 'certain', year: 208, month: undefined, day: undefined });
  });

  it('月精度：年-月', () => {
    expect(parseEdtf('0208-10')).toEqual({ precision: 'month', qualifier: 'certain', year: 208, month: 10, day: undefined });
  });

  it('日精度：年-月-日', () => {
    expect(parseEdtf('0208-10-15')).toEqual({ precision: 'day', qualifier: 'certain', year: 208, month: 10, day: 15 });
  });

  it('尾綴 ? 代表不確定（uncertain）', () => {
    expect(parseEdtf('1046?')).toEqual({ precision: 'year', qualifier: 'uncertain', year: 1046, month: undefined, day: undefined });
  });

  it('尾綴 ~ 代表約略（approximate）', () => {
    expect(parseEdtf('1046~')).toEqual({ precision: 'year', qualifier: 'approximate', year: 1046, month: undefined, day: undefined });
  });

  it('負年份（西元前，絕對紀年慣例）', () => {
    expect(parseEdtf('-0099')).toEqual({ precision: 'year', qualifier: 'certain', year: -99, month: undefined, day: undefined });
  });

  it('負年份加不確定標記可以同時成立', () => {
    expect(parseEdtf('-1045?')).toEqual({ precision: 'year', qualifier: 'uncertain', year: -1045, month: undefined, day: undefined });
  });

  it('不符合支援子集的字串回傳 null（例如完整 EDTF 規格的世紀/年代語法，這個專案沒實作）', () => {
    expect(parseEdtf('20XX')).toBeNull(); // EDTF 十年精度語法
    expect(parseEdtf('not-a-date')).toBeNull();
    expect(parseEdtf('')).toBeNull();
  });

  it('這個解析器只做語法結構判斷，不驗證月/日數值是否真的存在（例如月份 21）——那是後端 EdtfService 用 NodaTime 做的曆法驗證，資料庫裡的字串本來就是通過那層驗證才寫進去的，前端不重做一次同樣的驗證，只負責把已知合法的字串拆解成顯示用的結構', () => {
    expect(parseEdtf('2004-21')).not.toBeNull();
  });
});

describe('formatEdtfYear', () => {
  it('正年份顯示「西元 X 年」', () => {
    expect(formatEdtfYear(220)).toBe('西元 220 年');
  });

  it('絕對紀年 0 年對應「西元前 1 年」（不是西元前 0 年）', () => {
    expect(formatEdtfYear(0)).toBe('西元前 1 年');
  });

  it('絕對紀年 -99 對應「西元前 100 年」', () => {
    expect(formatEdtfYear(-99)).toBe('西元前 100 年');
  });
});

describe('formatEdtfDateLabel', () => {
  it('年精度只顯示到年，不偽造月/日精度', () => {
    expect(formatEdtfDateLabel({ precision: 'year', qualifier: 'certain', year: 208 })).toBe('西元 208 年');
  });

  it('月精度顯示到月', () => {
    expect(formatEdtfDateLabel({ precision: 'month', qualifier: 'certain', year: 208, month: 10 })).toBe('西元 208 年 10 月');
  });

  it('日精度顯示到日', () => {
    expect(formatEdtfDateLabel({ precision: 'day', qualifier: 'certain', year: 208, month: 10, day: 15 })).toBe(
      '西元 208 年 10 月 15 日',
    );
  });

  it('西元前年份也套用同一套精度規則', () => {
    expect(formatEdtfDateLabel({ precision: 'year', qualifier: 'certain', year: -1045 })).toBe('西元前 1046 年');
  });
});

describe('formatEdtfQualifierLabel', () => {
  it('certain 沒有提示文字（回傳 null，呼叫端據此決定不顯示額外提示）', () => {
    expect(formatEdtfQualifierLabel('certain')).toBeNull();
  });

  it('uncertain 顯示「推測年份」', () => {
    expect(formatEdtfQualifierLabel('uncertain')).toBe('推測年份');
  });

  it('approximate 顯示「約略年份」', () => {
    expect(formatEdtfQualifierLabel('approximate')).toBe('約略年份');
  });
});
