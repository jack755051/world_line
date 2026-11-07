import { Injectable, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

/** 人物對話框 push 的 history entry 標記（設計 §4.3）。 */
export interface OverlayMark { kind: 'person'; token: string; baseToken: string }

const newToken = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36);

/**
 * 只有「目前 entry 是本次執行期間 app 自己 push 的人物 entry」，且它是緊接在記下的底層之後 push 的，才可以 history.back()。
 * 深連結、重新整理、token 對不上、服務已遺失（pushed 為 null）一律回 false → 改用 replace 只移除 person。
 */
export function canGoBack(state: unknown, pushed: OverlayMark | null): boolean {
  const o = (state as { wlOverlay?: Partial<OverlayMark> } | null)?.wlOverlay;
  return !!pushed && !!o && o.kind === 'person' && o.token === pushed.token && o.baseToken === pushed.baseToken;
}

/** 人物對話框的開關與 history（只動 `person` 參數，其他參數 merge 保留）。 */
@Injectable({ providedIn: 'root' })
export class OverlayHistory {
  private readonly router = inject(Router);
  private pushed: OverlayMark | null = null;

  /** 在目前（底層）entry 蓋上 base token；已有就沿用。 */
  private stampBase(): string {
    const st = (history.state ?? {}) as Record<string, unknown>;
    if (typeof st['wlBase'] === 'string') return st['wlBase'];
    const tok = newToken();
    history.replaceState({ ...st, wlBase: tok }, '', location.href);
    return tok;
  }

  /** 開人物：底層 → push 一筆 `?person=`。對話框已開著時改用 replace（不疊第二層）。 */
  open(route: ActivatedRoute, personId: string, alreadyOpen: boolean): void {
    if (alreadyOpen) {
      void this.router.navigate([], { relativeTo: route, queryParams: { person: personId }, queryParamsHandling: 'merge', replaceUrl: true });
      return;
    }
    const baseToken = this.stampBase();
    const mark: OverlayMark = { kind: 'person', token: newToken(), baseToken };
    this.pushed = mark;
    void this.router.navigate([], { relativeTo: route, queryParams: { person: personId }, queryParamsHandling: 'merge', state: { wlOverlay: mark } });
  }

  /** 關人物：符合 canGoBack 才 back，否則 replace 只移除 person。回傳實際採用的方式（測試／除錯用）。 */
  close(route: ActivatedRoute): 'back' | 'replace' {
    const back = canGoBack(history.state, this.pushed);
    this.pushed = null;
    if (back) { history.back(); return 'back'; }
    void this.router.navigate([], { relativeTo: route, queryParams: { person: null }, queryParamsHandling: 'merge', replaceUrl: true });
    return 'replace';
  }

  /** 換掉 person 參數（例：生平已撤回、指向新版本），不新增 history。 */
  replacePerson(route: ActivatedRoute, personId: string | null): void {
    void this.router.navigate([], { relativeTo: route, queryParams: { person: personId }, queryParamsHandling: 'merge', replaceUrl: true });
  }
}
