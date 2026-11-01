/**
 * 延遲顯示的忙碌旗標：busy 持續超過 delayMs 才變成可見，避免快速載入時 spinner 一閃而過；
 * busy 結束立即隱藏。給地圖角落的「載入中」指示用。
 */
export class DelayedFlag {
  private timer: ReturnType<typeof setTimeout> | null = null;
  private visible = false;

  constructor(
    private readonly onChange: (visible: boolean) => void,
    readonly delayMs = 300,
  ) {}

  set(busy: boolean): void {
    if (busy) {
      if (this.visible || this.timer) return;
      this.timer = setTimeout(() => {
        this.timer = null;
        this.visible = true;
        this.onChange(true);
      }, this.delayMs);
      return;
    }
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    if (this.visible) {
      this.visible = false;
      this.onChange(false);
    }
  }

  dispose(): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
  }
}

/** 被新請求取代而中止的請求（AbortController.abort()）：呼叫端應安靜忽略，不改載入狀態。 */
export function isAbort(e: unknown): boolean {
  return typeof e === 'object' && e !== null && (e as { name?: string }).name === 'AbortError';
}
