import { addDays, addMonths, clampDate, formatDisplayDate, fromDayNumber, isIsoDate, toDayNumber } from './dates';

describe('dates', () => {
  it('isIsoDate 只接受存在的 YYYY-MM-DD', () => {
    expect(isIsoDate('1940-07-15')).toBe(true);
    expect(isIsoDate('1940-02-29')).toBe(true);
    expect(isIsoDate('1941-02-29')).toBe(false);
    expect(isIsoDate('1940-13-01')).toBe(false);
    expect(isIsoDate('1940-7-15')).toBe(false);
    expect(isIsoDate(undefined)).toBe(false);
  });

  it('日序號往返不失真', () => {
    expect(fromDayNumber(toDayNumber('1937-07-07'))).toBe('1937-07-07');
    expect(toDayNumber('1940-08-15') - toDayNumber('1940-07-15')).toBe(31);
  });

  it('加減日與月（月底截斷）', () => {
    expect(addDays('1940-07-15', 17)).toBe('1940-08-01');
    expect(addMonths('1940-01-31', 1)).toBe('1940-02-29');
    expect(addMonths('1940-07-15', -7)).toBe('1939-12-15');
  });

  it('clampDate', () => {
    expect(clampDate('1930-01-01', '1937-07-01', '1945-09-30')).toBe('1937-07-01');
    expect(clampDate('1950-01-01', '1937-07-01', '1945-09-30')).toBe('1945-09-30');
  });

  it('頂部列日期格式', () => {
    expect(formatDisplayDate('1940-07-15', 'zh-Hant')).toBe('1940年7月15日');
    expect(formatDisplayDate('1940-07-15', 'en')).toBe('15 July 1940');
  });
});
