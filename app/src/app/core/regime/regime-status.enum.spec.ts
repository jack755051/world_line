import {
  REGIME_STATUSES,
  isRegimeStatus,
  isLegalRegimeStatusTransition,
  getLegalNextRegimeStatuses,
  type RegimeStatus,
} from './regime-status.enum';

describe('isRegimeStatus', () => {
  it.each(REGIME_STATUSES)('accepts %s', (status) => {
    expect(isRegimeStatus(status)).toBe(true);
  });

  it.each(['unknown', '', 'Active', '被取代(禪讓)'])('rejects %s', (value) => {
    expect(isRegimeStatus(value)).toBe(false);
  });
});

describe('isLegalRegimeStatusTransition', () => {
  // 憲法 §4：合法轉換只有這三條，全部只能從 active 出發。
  const legalPairs: [RegimeStatus, RegimeStatus][] = [
    ['active', 'split'],
    ['active', 'succeeded'],
    ['active', 'conquered'],
  ];

  it.each(legalPairs)('%s -> %s is legal', (from, to) => {
    expect(isLegalRegimeStatusTransition(from, to)).toBe(true);
  });

  // 窮舉所有 4x4 = 16 組配對，扣掉上面 3 組合法的，其餘 13 組都必須是不合法——
  // 包含同狀態（不構成轉換）、逆轉（從終止狀態變回 active）、終止狀態互轉（取代跟消滅
  // 是兩種不同定義，不可合併）。
  const illegalPairs: [RegimeStatus, RegimeStatus][] = REGIME_STATUSES.flatMap((from) =>
    REGIME_STATUSES.filter(
      (to) => !legalPairs.some(([legalFrom, legalTo]) => legalFrom === from && legalTo === to),
    ).map((to): [RegimeStatus, RegimeStatus] => [from, to]),
  );

  it('there are exactly 13 illegal pairs (16 total - 3 legal)', () => {
    expect(illegalPairs).toHaveLength(13);
  });

  it.each(illegalPairs)('%s -> %s is illegal', (from, to) => {
    expect(isLegalRegimeStatusTransition(from, to)).toBe(false);
  });
});

describe('getLegalNextRegimeStatuses', () => {
  it('active can go to split, succeeded, or conquered', () => {
    expect(getLegalNextRegimeStatuses('active').sort()).toEqual(['conquered', 'split', 'succeeded']);
  });

  it.each(['split', 'succeeded', 'conquered'] as const)('%s is terminal — no legal next status', (status) => {
    expect(getLegalNextRegimeStatuses(status)).toEqual([]);
  });
});
