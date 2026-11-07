import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { LucideUserRound } from '@lucide/angular';
import type { LeaderRecord } from '../../core/api/world-line-api';
import type { Lang } from '../../core/i18n';
import { formatTerm, portraitDisplayable } from '../../core/person-format';
import { termSourceItems } from '../../core/person-sources';
import { SourceDisclosure } from '../source-disclosure/source-disclosure';

const TXT = {
  'zh-Hant': {
    role: { head_of_state: '國家元首', head_of_government: '政府首腦' } as Record<string, string>,
    term: '任期', details: '查看詳情', noPhoto: '無授權照片', portraitOf: '的肖像', tenureSource: '任期',
  },
  en: {
    role: { head_of_state: 'Head of State', head_of_government: 'Head of Gov\'t' } as Record<string, string>,
    term: 'Term', details: 'View details', noPhoto: 'No licensed photo', portraitOf: ' — portrait', tenureSource: 'Term',
  },
} as const;

/** 人物分頁的人物卡：照片（無授權照片＝中性佔位）、姓名、職位、任期、查看詳情、任期來源（預設收合）。 */
@Component({
  selector: 'wl-person-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideUserRound, SourceDisclosure],
  host: { class: 'block' },
  template: `
    <article data-testid="person-card" [attr.data-record-id]="leader().recordId" [attr.data-person-id]="leader().personId"
      class="flex gap-3 rounded-wl-sm border border-wl-outline-variant bg-wl-surface p-2.5">
      <div class="h-[76px] w-[60px] flex-none overflow-hidden rounded-sm bg-wl-surface-container-high">
        @if (portrait() && !imgFailed()) {
          <img data-testid="person-card-photo" [src]="portrait()!.url" [alt]="name() + t().portraitOf" loading="lazy" referrerpolicy="no-referrer"
            class="size-full object-cover object-top" (error)="imgFailed.set(true)" />
        } @else {
          <div data-testid="person-card-placeholder" class="flex size-full items-center justify-center text-wl-outline" role="img" [attr.aria-label]="t().noPhoto">
            <svg lucideUserRound class="size-7" aria-hidden="true"></svg>
          </div>
        }
      </div>
      <div class="min-w-0 flex-1">
        <h4 data-testid="person-card-name" class="wl-text1 font-semibold leading-snug">{{ name() }}</h4>
        <div class="mt-0.5 flex flex-wrap items-center gap-1 text-[12px] text-wl-on-surface-variant">
          <span data-testid="person-card-role" class="rounded-sm bg-wl-surface-container-high px-1" [attr.data-role]="leader().role">{{ t().role[leader().role] ?? leader().role }}</span>
          @if (leader().title) { <span data-testid="person-card-title" class="min-w-0 break-words">{{ leader().title }}</span> }
        </div>
        <div data-testid="person-card-term" class="mt-0.5 font-mono text-[12px] tabular-nums text-wl-on-surface-variant">
          <span class="sr-only">{{ t().term }}</span>{{ term() }}</div>
        <div class="mt-1.5 flex flex-wrap items-start gap-x-3 gap-y-1">
          @if (canOpen()) {
            <button type="button" data-testid="person-card-details" [attr.data-person-trigger]="leader().personId"
              class="wl-btn-secondary inline-flex min-h-11 items-center px-3 text-[13px] md:min-h-8"
              [attr.aria-label]="t().details + '：' + name()" (click)="open.emit({ personId: leader().personId!, trigger: $any($event.currentTarget) })">{{ t().details }}</button>
          }
          <wl-source-disclosure class="min-w-0 flex-1 pt-1" [items]="sources()" [lang]="lang()" [label]="t().tenureSource" />
        </div>
      </div>
    </article>
  `,
})
export class PersonCard {
  readonly leader = input.required<LeaderRecord>();
  readonly lang = input<Lang>('zh-Hant');
  readonly open = output<{ personId: string; trigger: HTMLElement }>();

  protected readonly imgFailed = signal(false);
  protected readonly t = computed(() => TXT[this.lang() === 'en' ? 'en' : 'zh-Hant']);
  protected readonly name = computed(() => {
    const l = this.leader();
    return (this.lang() === 'en' ? l.name : l.nameZh || l.name) || l.name;
  });
  protected readonly term = computed(() => formatTerm(this.leader().validPeriod, this.lang()));
  protected readonly portrait = computed(() => {
    const p = this.leader().bio?.portrait;
    return portraitDisplayable(p) ? p : null;
  });
  /** 只有連到有效（未撤回、非測試）生平時才有「查看詳情」。 */
  protected readonly canOpen = computed(() => {
    const l = this.leader();
    return l.personId != null && l.bio != null && !l.bio.retractedAt;
  });
  protected readonly sources = computed(() => termSourceItems(this.leader()));
}
