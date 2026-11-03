import { dateAt, fraction, monthTicks, nearestDate, nextSnapshotDate, prevSnapshotDate, rangeFor, yearTicks } from './timeline-scale';

describe('timeline-scale', () => {
  const r = rangeFor(null);

  it('預設範圍 1937-07-01～1945-09-30；資料更早時往前延伸（Q15）', () => {
    expect(r).toEqual({ start: '1937-07-01', end: '1945-09-30' });
    expect(rangeFor('1940-07-15')).toEqual(r);
    expect(rangeFor('1931-09-18').start).toBe('1931-09-18');
  });

  it('fraction／dateAt 互為反函數', () => {
    expect(fraction('1937-07-01', r)).toBe(0);
    expect(fraction('1945-09-30', r)).toBe(1);
    expect(dateAt(fraction('1940-07-15', r), r)).toBe('1940-07-15');
    expect(dateAt(-1, r)).toBe('1937-07-01');
  });

  it('年刻度 1938–1945，月刻度不含一月', () => {
    expect(yearTicks(r).map((x) => x.label)).toEqual(['1938', '1939', '1940', '1941', '1942', '1943', '1944', '1945']);
    expect(monthTicks(r).some((m) => m.date.endsWith('-01-01'))).toBe(false);
    expect(monthTicks(r)[0].date).toBe('1937-07-01');
  });

  it('範圍很長時（1908 起）年份每 5 年標一次，刻線照畫', () => {
    const w = rangeFor('1908-10-05');
    expect(w.start).toBe('1908-10-05');
    const ys = yearTicks(w);
    expect(ys[0].date).toBe('1909-01-01');
    expect(ys.length).toBe(37);
    expect(ys.filter((y) => y.label).map((y) => y.label)).toEqual(['1910', '1915', '1920', '1925', '1930', '1935', '1940', '1945']);
  });

  it('固定每 5 年標字（方案 A），短範圍也一樣；每年都有刻點', () => {
    const ys = yearTicks(r, 16, 5);
    expect(ys.length).toBe(8);
    expect(ys.filter((y) => y.label).map((y) => y.label)).toEqual(['1940', '1945']);
  });

  it('上一個／下一個／最近的快照', () => {
    const d = ['1940-07-15', '1940-08-15'];
    expect(prevSnapshotDate(d, '1940-07-30')).toBe('1940-07-15');
    expect(nextSnapshotDate(d, '1940-07-30')).toBe('1940-08-15');
    expect(prevSnapshotDate(d, '1940-07-15')).toBeNull();
    expect(nextSnapshotDate(d, '1940-08-15')).toBeNull();
    expect(nearestDate(d, '1938-03-01')).toBe('1940-07-15');
    expect(nearestDate([], '1938-03-01')).toBeNull();
  });
});
