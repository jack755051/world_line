import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';
import type { CitationDto, SovereigntyEventRefDto } from '../../core/api/api-types';
import { shortCitation } from '../../core/citation-short';
import { localized, type Lang } from '../../core/i18n';

const TXT = {
  'zh-Hant': { pending: '待查證', verified: '已查證', noCitation: '尚無正式出處', showFull: '展開完整書目', hideFull: '收合書目', publisher: '出版', note: '說明' },
  en: { pending: 'Pending verification', verified: 'Verified', noCitation: 'No formal source yet', showFull: 'Show full reference', hideFull: 'Hide full reference', publisher: 'Publisher', note: 'Note' },
} as const;

/**
 * 資訊卡裡的一筆事件（政權卡的起訖疆界變動、衝突卡的開戰／停戰事件共用，Tai 2026-10-31）：
 * 事件名稱 → 日期 → 查證狀態＋出處。出處預設只顯示簡短引用，點一下展開完整書目；
 * 沒有正式出處就標「待查證」與「尚無正式出處」，不補造。testid 以 `prefix` 開頭，讓兩種卡片的測試各自定位。
 */
@Component({
  selector: 'wl-event-ref',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @let p = prefix();
    @if (head()) {
      <div [attr.data-testid]="p + '-event-name'">{{ summary() }}</div>
      <div class="text-wl-on-surface-variant" [attr.data-testid]="p + '-event-date'">{{ ev().occurred.start }}</div>
    }
    <div class="flex flex-col items-start gap-1" [class.mt-1]="head()" [attr.data-testid]="p + '-evidence'">
      @if (ev().verification === 'pending') {
        <span class="wl-chip-interp" [attr.data-testid]="p + '-pending'">{{ t().pending }}</span>
      } @else {
        <span class="wl-stamp" [attr.data-testid]="p + '-verified'">{{ t().verified }}</span>
      }
      @for (c of ev().citations; track $index) {
        <div class="w-full" [attr.data-testid]="p + '-citation'" [attr.data-expanded]="isOpen($index) ? 'true' : 'false'">
          <button type="button" class="w-full text-left text-wl-on-surface-variant underline decoration-dotted underline-offset-2 hover:text-wl-on-surface"
            [attr.data-testid]="p + '-citation-toggle'" [attr.aria-expanded]="isOpen($index)" [attr.title]="isOpen($index) ? t().hideFull : t().showFull"
            (click)="toggle($index)">{{ short(c) }}</button>
          @if (isOpen($index)) {
            <div class="mt-0.5 border-l-2 border-wl-outline-variant pl-2 text-wl-on-surface-variant" [attr.data-testid]="p + '-citation-full'">
              <div>{{ c.sourceTitle }}</div>
              <div>{{ c.locator }}</div>
              @if (c.publisher) { <div>{{ t().publisher }}：{{ c.publisher }}</div> }
              @if (c.evidenceNote) { <div>{{ t().note }}：{{ c.evidenceNote }}</div> }
            </div>
          }
        </div>
      } @empty {
        <div class="text-wl-on-surface-variant" [attr.data-testid]="p + '-no-citation'">{{ t().noCitation }}</div>
      }
    </div>
  `,
})
export class EventRef {
  readonly ev = input.required<SovereigntyEventRefDto>();
  readonly prefix = input('sovereignty-card');
  readonly lang = input<Lang>('zh-Hant');
  /** false：不重複事件名稱與日期（§10 v2：卡片已顯示）。 */
  readonly head = input(true);

  protected readonly t = computed(() => TXT[this.lang() === 'en' ? 'en' : 'zh-Hant']);
  protected readonly summary = computed(
    () => localized((this.ev().summary ?? {}) as Record<string, string>, this.lang()).text || this.ev().eventKind,
  );

  /** 展開的出處序號（綁事件 id；換事件時自動收合）。 */
  private readonly expanded = signal<{ eventId: string; open: ReadonlySet<number> }>({ eventId: '', open: new Set() });
  protected isOpen(i: number): boolean {
    const e = this.expanded();
    return e.eventId === this.ev().id && e.open.has(i);
  }
  protected toggle(i: number): void {
    const eventId = this.ev().id;
    const cur = this.expanded();
    const open = new Set(cur.eventId === eventId ? cur.open : []);
    if (open.has(i)) open.delete(i);
    else open.add(i);
    this.expanded.set({ eventId, open });
  }
  protected short(c: CitationDto): string {
    return shortCitation(c);
  }
}
