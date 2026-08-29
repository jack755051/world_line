/**
 * 憲法 §4 政權狀態機的四種狀態（存續／分裂／被取代(禪讓)／被滅亡），對齊後端
 * `api/Domain/RegimeStatus.cs` 的字串代碼（`RegimeStatusCodes.ToCode()`）——這裡直接用
 * TypeScript 字串聯集當作代碼本身，不需要像 C# enum 那樣另外開一張代碼對照表，因為
 * TS 沒有「數字底層值」的問題，字串字面值本來就是可以直接拿來用的代碼。
 *
 * 前端這份定義**不是信任來源**——後端 `RegimeTransitionValidator` 才是（PRD §5「XState
 * 前後端狀態機驗證分工」已拍板），這裡只做 UI 層防呆／進度圖顯示用。憲法 §4 若修訂，
 * 這裡要跟著 `api/Domain/RegimeStatus.cs`／`RegimeTransitionValidator.cs` 同步更新，
 * 避免規則飄移（跟後端同一份風險，兩邊各自維護但必須同步）。
 */
export const REGIME_STATUSES = ['active', 'split', 'succeeded', 'conquered'] as const;

export type RegimeStatus = (typeof REGIME_STATUSES)[number];

export function isRegimeStatus(value: string): value is RegimeStatus {
  return (REGIME_STATUSES as readonly string[]).includes(value);
}

/**
 * 憲法 §4：合法轉換只有這三條，全部只能從 active 出發；一旦進入三個終止狀態
 * （split/succeeded/conquered），沒有任何合法的後續轉換——「取代跟消滅是兩種不同的
 * 定義」，不可合併，也不可逆轉。跟後端 `RegimeTransitionValidator.LegalStatusTransitions`
 * 是同一份規則的兩份獨立實作，不是同一份程式碼共用（C# 跟 TypeScript 沒辦法直接共用
 * library，見 PRD §5 驗證分工說明）。
 */
const LEGAL_STATUS_TRANSITIONS: ReadonlySet<string> = new Set([
  'active->split',
  'active->succeeded',
  'active->conquered',
]);

export function isLegalRegimeStatusTransition(from: RegimeStatus, to: RegimeStatus): boolean {
  return LEGAL_STATUS_TRANSITIONS.has(`${from}->${to}`);
}

/** 給進度圖/防呆 UI 用：某個狀態底下有哪些合法的下一步（沒有就是終止狀態）。 */
export function getLegalNextRegimeStatuses(from: RegimeStatus): RegimeStatus[] {
  return REGIME_STATUSES.filter((to) => isLegalRegimeStatusTransition(from, to));
}
