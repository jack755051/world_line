import { createMachine } from 'xstate';

/**
 * 憲法 §4 政權狀態機的前端 XState 定義——**只做 UI 層防呆與進度圖顯示，不是信任來源**
 * （PRD §5「XState 前後端狀態機驗證分工」已拍板）。後端 `api/Domain/
 * RegimeTransitionValidator.cs` 才是唯一信任來源，即使前端沒擋住、request 直接打 API，
 * 後端也會獨立擋下非法轉換。
 *
 * 這裡刻意手寫成 XState 慣用的字面量狀態圖（不是從 `regime-status.enum.ts` 的規則表
 * 動態產生），理由：狀態圖本身要能直接拿去用 XState 的視覺化工具檢視/除錯，手寫的字面量
 * 結構才是這些工具預期的形狀；反過來，`regime-status.enum.ts` 提供的
 * `isLegalRegimeStatusTransition()` 是給不需要真的跑一個 actor、只想問「這個轉換合不
 * 合法」的地方用（例如靜態渲染一張進度圖、不需要維護 actor 生命週期）。兩份手寫表示
 * 會不會飄掉，靠 `regime-status.machine.spec.ts` 逐一比對兩邊的判斷結果來抓，不是
 * 假設寫的時候對了就永遠對。
 *
 * 三個終止狀態（split/succeeded/conquered）都標記成 `type: 'final'`——憲法 §4：
 * 「取代跟消滅是兩種不同的定義」，不可合併也不可逆轉，不會有政權從被滅亡變回存續。
 */
export const regimeStatusMachine = createMachine({
  id: 'regimeStatus',
  initial: 'active',
  states: {
    active: {
      on: {
        SPLIT: 'split',
        SUCCEED: 'succeeded',
        CONQUER: 'conquered',
      },
    },
    split: { type: 'final' },
    succeeded: { type: 'final' },
    conquered: { type: 'final' },
  },
});
