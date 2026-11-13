import { InjectionToken, isDevMode } from '@angular/core';

/**
 * 實驗功能開關（與 CAMPAIGNS_ENABLED 無關，不要混用）。
 * `BATTLE_PROTO_DEV_SWITCH`：戰役 P0 手感原型（/campaigns/dunkirk-1940/proto）的原始碼開關，語意預設為關閉；
 * feature/battle-proto 分支為了 4203 驗收與 e2e 暫設 true。合回主線前必須改回 false。
 * 即使為 true，`isDevMode()===false`（production build）仍永遠關閉。
 * 測試可用 `{ provide: BATTLE_PROTO_ENABLED, useValue: false }` 覆寫。
 */
export const BATTLE_PROTO_DEV_SWITCH = true;

export function battleProtoEnabled(devMode: boolean, devSwitch: boolean = BATTLE_PROTO_DEV_SWITCH): boolean {
  return devMode && devSwitch;
}

export const BATTLE_PROTO_ENABLED = new InjectionToken<boolean>('BATTLE_PROTO_ENABLED', {
  providedIn: 'root',
  factory: () => battleProtoEnabled(isDevMode()),
});
