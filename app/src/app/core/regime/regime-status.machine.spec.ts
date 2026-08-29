import { createActor } from 'xstate';
import { regimeStatusMachine } from './regime-status.machine';
import { REGIME_STATUSES, isLegalRegimeStatusTransition, type RegimeStatus } from './regime-status.enum';

const EVENT_FOR_TARGET: Record<'split' | 'succeeded' | 'conquered', 'SPLIT' | 'SUCCEED' | 'CONQUER'> = {
  split: 'SPLIT',
  succeeded: 'SUCCEED',
  conquered: 'CONQUER',
};

describe('regimeStatusMachine', () => {
  it('starts in active', () => {
    const actor = createActor(regimeStatusMachine).start();
    expect(actor.getSnapshot().value).toBe('active');
  });

  it.each(['split', 'succeeded', 'conquered'] as const)(
    'transitions active -> %s and lands in a final state',
    (target) => {
      const actor = createActor(regimeStatusMachine).start();
      actor.send({ type: EVENT_FOR_TARGET[target] });
      const snapshot = actor.getSnapshot();
      expect(snapshot.value).toBe(target);
      expect(snapshot.status).toBe('done'); // final state
    },
  );

  it.each(['split', 'succeeded', 'conquered'] as const)(
    '%s is terminal — no event moves it anywhere else (憲法 §4：不可逆轉、不可合併)',
    (terminalStatus) => {
      const actor = createActor(regimeStatusMachine).start();
      actor.send({ type: EVENT_FOR_TARGET[terminalStatus] });

      for (const event of ['SPLIT', 'SUCCEED', 'CONQUER'] as const) {
        actor.send({ type: event });
        expect(actor.getSnapshot().value).toBe(terminalStatus);
      }
    },
  );

  // 兩份手寫表示（這支狀態機 vs. regime-status.enum.ts 的 isLegalRegimeStatusTransition）
  // 逐一比對是否一致，避免手動維護的兩份規則日後各自飄掉沒被發現。
  it('agrees with isLegalRegimeStatusTransition on every (from, to) pair reachable from active', () => {
    for (const to of REGIME_STATUSES) {
      if (to === 'active') continue; // 沒有任何轉換的目標是 active（憲法 §4：不可逆轉）

      const actor = createActor(regimeStatusMachine).start();
      actor.send({ type: EVENT_FOR_TARGET[to as 'split' | 'succeeded' | 'conquered'] });
      const reached = actor.getSnapshot().value === to;

      expect(reached).toBe(isLegalRegimeStatusTransition('active', to as RegimeStatus));
    }
  });
});
