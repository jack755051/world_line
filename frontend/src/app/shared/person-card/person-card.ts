import { ChangeDetectionStrategy, Component, computed, input, output, signal, viewChild } from '@angular/core';
import { LucideUserRound } from '@lucide/angular';
import type { LeaderRecord } from '../../core/api/world-line-api';
import type { Lang } from '../../core/i18n';
import { formatTerm, portraitDisplayable } from '../../core/person-format';
import { termSourceItems } from '../../core/person-sources';
import { FootnoteList, FootnoteSups } from '../footnotes/footnote-ui';
import { numberSources } from '../../core/footnotes';


const TXT = {
  'zh-Hant': {
    role: { head_of_state: '國家元首', head_of_government: '政府首腦' } as Record<string, string>,
    term: '任期', details: '查看詳情', noPhoto: '無授權照片', portraitOf: '的肖像', tenureSource: '任期', roles: '職位與任期',
    sources: '資料來源', usedFor: '用於', sourceRef: '來源', pending: '待補來源',
  },
  en: {
    role: { head_of_state: 'Head of State', head_of_government: 'Head of Gov\'t' } as Record<string, string>,
    term: 'Term', details: 'View details', noPhoto: 'No licensed photo', portraitOf: ' — portrait', tenureSource: 'Term', roles: 'Offices and terms',
    sources: 'Sources', usedFor: 'Used for', sourceRef: 'Source', pending: 'Source needed',
  },
} as const;

/**
 * 人物分頁的人物卡：同一人（同 personId）多個角色合併成一張（ARCHITECTURE §14.8）。
 * 照片（無授權照片＝中性佔位）、姓名、每個角色各自一列（職位、任期＋來源上標編號）、底部統一的「資料來源」（預設收合）、查看詳情。
 */
@Component({
  selector: 'wl-person-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideUserRound, FootnoteSups, FootnoteList],
  host: { class: 'block' },
  template: `
    <article data-testid="person-card" [attr.data-record-id]="first().recordId" [attr.data-person-id]="first().personId" [attr.data-role-count]="records().length"
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
        <ul class="mt-1 space-y-1.5" [attr.aria-label]="t().roles">
          @for (r of roles(); track r.recordId) {
            <li data-testid="person-card-role-row" [attr.data-record-id]="r.recordId" [attr.data-role]="r.role"
              class="text-[12px] text-wl-on-surface-variant" [class.border-t]="!$first" [class.border-wl-outline-variant]="!$first" [class.pt-1.5]="!$first">
              <div class="flex flex-wrap items-center gap-1">
                <span data-testid="person-card-role" class="rounded-sm bg-wl-surface-container-high px-1" [attr.data-role]="r.role">{{ r.roleText }}</span>
                @if (r.title) { <span data-testid="person-card-title" class="min-w-0 break-words">{{ r.title }}</span> }
              </div>
              <!-- 任期旁只放上標編號，出處統一列在卡片底部「資料來源」（與人物彈窗、國界卡片同一種做法；Tai 2026-11-14） -->
              <div data-testid="person-card-term" class="mt-0.5 font-mono tabular-nums">
                <span class="sr-only">{{ t().term }}</span>{{ r.term }}<wl-footnote-sups [ns]="notesFor(r.recordId)" prefix="person-card" [lang]="lang()" (pick)="showNote($event)" /></div>
              @if (!r.sources.length) { <span data-testid="source-pending" class="mt-0.5 inline-flex min-h-6 items-center rounded-sm border border-dashed border-wl-outline px-1.5 text-[11px]">{{ t().pending }}</span> }
            </li>
          }
        </ul>
        <wl-footnote-list #srcList class="mt-2" prefix="person-card" [dense]="true" [footnotes]="footnotes()" [lang]="lang()" />
        @if (canOpen()) {
          <button type="button" data-testid="person-card-details" [attr.data-person-trigger]="first().personId"
            class="wl-btn-secondary mt-1.5 inline-flex min-h-11 items-center px-3 text-[13px] md:min-h-8"
            [attr.aria-label]="t().details + '：' + name()" (click)="open.emit({ personId: first().personId!, trigger: $any($event.currentTarget) })">{{ t().details }}</button>
        }
      </div>
    </article>
  `,
})
export class PersonCard {
  /** 同一人的全部角色（已依角色排序；至少一筆）。 */
  readonly records = input.required<LeaderRecord[]>();
  readonly lang = input<Lang>('zh-Hant');
  readonly open = output<{ personId: string; trigger: HTMLElement }>();

  protected readonly imgFailed = signal(false);
  protected readonly t = computed(() => TXT[this.lang() === 'en' ? 'en' : 'zh-Hant']);
  protected readonly first = computed(() => this.records()[0]);
  protected readonly name = computed(() => {
    const l = this.first();
    return (this.lang() === 'en' ? l.name : l.nameZh || l.name) || l.name;
  });
  protected readonly roles = computed(() => this.records().map((r) => ({
    recordId: r.recordId, role: r.role, roleText: this.t().role[r.role] ?? r.role, title: r.title,
    term: formatTerm(r.validPeriod, this.lang()), sources: termSourceItems(r),
  })));
  /** 各角色任期的來源 → 編號清單（core/footnotes.ts；同一筆來源只列一次）。 */
  private readonly notes = computed(() => numberSources(this.roles().map((r) => ({ key: r.recordId, label: `${r.roleText} ${this.t().tenureSource}`, items: r.sources }))));
  protected readonly footnotes = computed(() => this.notes().list);
  protected notesFor(key: string): number[] { return this.notes().fieldNotes.get(key) ?? []; }
  private readonly srcListRef = viewChild<FootnoteList>('srcList');
  /** 上標編號：展開「資料來源」並捲到該筆（樣板裡的 #srcList 會蓋掉同名成員，所以另取名）。 */
  protected showNote(n: number): void { this.srcListRef()?.reveal(n); }
  /** 同一人的生平摘要（任一角色帶到即可）。 */
  private readonly bio = computed(() => this.records().find((r) => r.bio)?.bio ?? null);
  protected readonly portrait = computed(() => {
    const p = this.bio()?.portrait;
    return portraitDisplayable(p) ? p : null;
  });
  /** 只有連到有效（未撤回、非測試）生平時才有「查看詳情」。 */
  protected readonly canOpen = computed(() => {
    const b = this.bio();
    return this.first().personId != null && b != null && !b.retractedAt;
  });
}
