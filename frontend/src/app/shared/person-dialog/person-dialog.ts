import { CdkTrapFocus } from '@angular/cdk/a11y';
import { NgTemplateOutlet } from '@angular/common';
import { afterNextRender, ChangeDetectionStrategy, Component, computed, ElementRef, inject, Injector, input, output, signal, viewChild } from '@angular/core';
import { LucideCalendar, LucideChevronDown, LucideIdCard, LucideLandmark, LucideLibrary, LucideScrollText, LucideUserRound, LucideX } from '@lucide/angular';
import type { LeaderBio } from '../../core/api/world-line-api';
import type { Lang } from '../../core/i18n';
import { formatPartialDate, formatTerm, inclusiveEnd, pickLocalized, portraitDisplayable } from '../../core/person-format';
import { fieldSourceItems, portraitSourceItems, termSourceItems } from '../../core/person-sources';
import { SourceDisclosure, type SourceItem } from '../source-disclosure/source-disclosure';

export type PersonDialogState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ok'; data: LeaderBio };

const TXT = {
  'zh-Hant': {
    close: '關閉', loading: '載入中…', error: '人物資料載入失敗', basics: '基本資料', birth: '出生', death: '逝世',
    birthPlace: '出生地', party: '黨派', summary: '生平', terms: '職位與任期', noValue: '尚無資料', notApplicable: '不適用',
    photo: '照片', noPhoto: '無授權照片', test: '測試資料', name: '姓名', dossier: '人物詳情', sections: '詳情區塊',
    termNote: '任期迄日不含當天，畫面顯示最後在任日。', dialog: '人物詳情', portraitOf: '的肖像',
    sources: '資料來源', pending: '待補來源', usedFor: '用於', missing: '以下欄位待補來源', sourceRef: '來源',
    role: { head_of_state: '國家元首', head_of_government: '政府首腦' } as Record<string, string>,
  },
  en: {
    close: 'Close', loading: 'Loading…', error: 'Could not load this person', basics: 'Basic facts', birth: 'Born', death: 'Died',
    birthPlace: 'Birthplace', party: 'Party', summary: 'Biography', terms: 'Offices and terms', noValue: 'No data', notApplicable: 'Not applicable',
    photo: 'Photo', noPhoto: 'No licensed photo', test: 'Test data', name: 'Name', dossier: 'Person details', sections: 'Sections',
    termNote: 'Term end dates are exclusive; the last day in office is shown.', dialog: 'Person details', portraitOf: ' — portrait',
    sources: 'Sources', pending: 'Source needed', usedFor: 'Used for', missing: 'Fields without a source', sourceRef: 'Source',
    role: { head_of_state: 'Head of State', head_of_government: 'Head of Gov\'t' } as Record<string, string>,
  },
} as const;

type SectionKey = 'basics' | 'bio' | 'terms' | 'sources';

/** 一筆去重後的來源（底部註腳）：編號、內容、用在哪些欄位。 */
interface Footnote { n: number; item: SourceItem; usedFor: string[] }

let seq = 0;
const roleRank = (r: string): number => ({ head_of_state: 0, head_of_government: 1 } as Record<string, number>)[r] ?? 2;

/**
 * 人物詳情對話框（ARCHITECTURE §14.8；版面參考 Stitch 人物檔案稿，配色沿用羊皮紙 --wl-* 變數）。
 * 桌機置中大視窗、手機全螢幕；role="dialog" aria-modal="true"、焦點鎖定、Esc 由頁面統一關閉。
 * 區塊：標頭（照片 3:4、中文名、原文名、角色、生卒）→ 區塊分頁籤（吸頂）→ 基本資料格 → 生平 → 職位與任期時間軸 → 資料來源（底部統一收合）。
 * 欄位值旁只放上標來源編號；完整出處集中在底部「資料來源 (N)」。沒有來源的欄位明示「待補來源」；舊格式出處只當備註，不標已查證。
 * 戰役／事件：目前沒有人物↔事件資料（§14.0 戰役先不做），不顯示該區塊，也不放假資料。
 */
@Component({
  selector: 'wl-person-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CdkTrapFocus, NgTemplateOutlet, LucideX, LucideUserRound, LucideCalendar, LucideIdCard, LucideScrollText, LucideLandmark, LucideLibrary, LucideChevronDown, SourceDisclosure],
  template: `
    <div class="fixed inset-0 z-[70]" data-testid="person-dialog-root">
      <div class="absolute inset-0 bg-black/45" aria-hidden="true" data-testid="person-dialog-backdrop" (click)="closed.emit()"></div>
      <section #panel data-testid="person-dialog" role="dialog" aria-modal="true" [attr.aria-labelledby]="titleId" tabindex="-1"
        cdkTrapFocus [cdkTrapFocusAutoCapture]="false"
        class="absolute inset-0 flex flex-col overflow-hidden bg-wl-surface shadow-[var(--wl-shadow-panel)] outline-none md:inset-auto md:left-1/2 md:top-1/2 md:h-[min(90vh,860px)] md:w-[min(920px,94vw)] md:-translate-x-1/2 md:-translate-y-1/2 md:rounded-xl md:border md:border-wl-outline-variant">
        <!-- 頂列：檔案標記（政權）＋關閉；不隨內容捲動 -->
        <header class="flex flex-none items-center gap-2 border-b border-wl-outline-variant bg-wl-surface-container px-4 md:px-6">
          <span aria-hidden="true" class="size-2 flex-none bg-wl-primary"></span>
          <p data-testid="person-dialog-eyebrow" class="min-w-0 flex-1 truncate font-mono text-[11px] uppercase tracking-[0.12em] text-wl-on-surface-variant">
            {{ t().dossier }}@if (regimeLabel()) { <span> // {{ regimeLabel() }}</span> }</p>
          <button #closeBtn type="button" data-testid="person-dialog-close" [attr.aria-label]="t().close"
            class="inline-flex size-11 flex-none items-center justify-center rounded-full hover:bg-wl-surface-container-high focus-visible:outline-2 focus-visible:outline-wl-secondary"
            (click)="closed.emit()"><svg lucideX class="size-5" aria-hidden="true"></svg></button>
        </header>
        <div #body data-testid="person-dialog-body" class="relative min-h-0 flex-1 overflow-y-auto overscroll-contain" (scroll)="onScroll()">
          @switch (state().status) {
            @case ('loading') { <p class="px-4 py-4 wl-text2 text-wl-on-surface-variant md:px-8" role="status">{{ t().loading }}</p> }
            @case ('error') { <p class="px-4 py-4 wl-text2 text-wl-error md:px-8" role="alert">{{ t().error }}</p> }
          }
          @if (bio(); as b) {
            <!-- 標頭：照片 3:4（無授權＝中性佔位）＋姓名、原文名、角色、生卒 -->
            <div data-testid="person-dialog-hero" class="flex gap-4 border-b border-wl-outline-variant px-4 py-4 md:gap-6 md:px-8 md:py-6">
              <figure class="w-24 flex-none md:w-40" data-testid="person-dialog-figure">
                <div class="aspect-[3/4] w-full overflow-hidden rounded-sm border border-wl-outline-variant bg-wl-surface-container-high">
                  @if (portrait() && !imgFailed()) {
                    <img data-testid="person-dialog-photo" [src]="portrait()!.url" [alt]="title() + t().portraitOf" referrerpolicy="no-referrer"
                      class="size-full object-cover object-top" (error)="imgFailed.set(true)" />
                  } @else {
                    <div data-testid="person-dialog-placeholder" class="flex size-full flex-col items-center justify-center gap-1 text-wl-outline" role="img" [attr.aria-label]="t().noPhoto">
                      <svg lucideUserRound class="size-10 md:size-14" aria-hidden="true"></svg>
                      <span class="px-1 text-center text-[11px] text-wl-on-surface-variant" aria-hidden="true">{{ t().noPhoto }}</span>
                    </div>
                  }
                </div>
                @if (portrait(); as p) {
                  <figcaption data-testid="person-dialog-photo-credit" class="mt-1 break-words text-[11px] leading-snug text-wl-on-surface-variant">
                    {{ p.attribution }}<ng-container *ngTemplateOutlet="sup; context: { $implicit: notesFor('portrait') }" /></figcaption>
                }
              </figure>
              <div class="min-w-0 flex-1">
                @if (b.isTest) { <span class="mb-1 inline-block rounded-sm bg-wl-surface-container-high px-1 text-[11px]">{{ t().test }}</span> }
                <h2 [id]="titleId" data-testid="person-dialog-title" class="font-wl-serif text-[24px] font-semibold leading-tight text-wl-on-surface md:text-[32px]">{{ title() }}</h2>
                @if (originalName(); as on) {
                  <p data-testid="person-dialog-original-name" class="mt-0.5 font-wl-serif text-[15px] italic text-wl-primary md:text-[18px]" lang="und">{{ on }}<ng-container *ngTemplateOutlet="sup; context: { $implicit: notesFor('name') }" /></p>
                }
                @if (roleChips().length) {
                  <ul data-testid="person-dialog-roles" class="mt-2 flex flex-wrap gap-1.5">
                    @for (c of roleChips(); track c.key; let i = $index) {
                      <li data-testid="person-dialog-role" class="rounded-sm border px-1.5 py-0.5 text-[12px]"
                        [class.border-wl-primary]="i === 0" [class.bg-wl-primary-container]="i === 0" [class.text-wl-on-surface]="i === 0"
                        [class.border-wl-outline-variant]="i !== 0" [class.bg-wl-surface-container]="i !== 0" [class.text-wl-on-surface-variant]="i !== 0">{{ c.text }}</li>
                    }
                  </ul>
                }
                @if (lifeText()) {
                  <p data-testid="person-dialog-life" class="mt-3 inline-flex items-center gap-2 rounded-sm border border-wl-outline-variant bg-wl-surface-container-lowest px-2.5 py-1.5 font-mono text-[13px] tabular-nums text-wl-on-surface md:text-[14px]">
                    <svg lucideCalendar class="size-4 flex-none text-wl-primary" aria-hidden="true"></svg>{{ lifeText() }}</p>
                }
              </div>
            </div>

            <!-- 區塊分頁籤：捲動時吸頂；點了捲到該區塊 -->
            <nav data-testid="person-dialog-tabs" [attr.aria-label]="t().sections"
              class="sticky top-0 z-[2] flex gap-1 overflow-x-auto border-b border-wl-outline-variant bg-wl-surface/95 px-2 backdrop-blur-sm md:px-6">
              @for (s of sections(); track s.key) {
                <button type="button" [attr.data-testid]="'person-dialog-tab-' + s.key" [attr.aria-current]="activeSection() === s.key ? 'true' : null"
                  class="relative inline-flex min-h-11 flex-none items-center gap-1 whitespace-nowrap px-3 text-[13px] focus-visible:outline-2 focus-visible:outline-wl-secondary"
                  [class.font-semibold]="activeSection() === s.key" [class.text-wl-primary]="activeSection() === s.key" [class.text-wl-on-surface-variant]="activeSection() !== s.key"
                  (click)="goTo(s.key)">{{ s.label }}
                  @if (s.count !== null) { <span class="rounded-sm bg-wl-surface-container-high px-1 text-[11px] tabular-nums text-wl-on-surface-variant">{{ s.count }}</span> }
                  @if (activeSection() === s.key) { <span aria-hidden="true" class="absolute inset-x-2 bottom-0 h-[2px] bg-wl-primary"></span> }
                </button>
              }
            </nav>

            <div class="space-y-8 px-4 py-6 md:px-8">
              <!-- 基本資料格：值旁只放上標來源編號 -->
              <section [id]="sectionId('basics')" data-section="basics" data-testid="person-dialog-section-basics" [attr.aria-labelledby]="sectionId('basics') + '-h'">
                <h3 [id]="sectionId('basics') + '-h'" class="mb-3 flex items-center gap-2 border-b border-wl-outline-variant pb-2 font-wl-serif text-[18px] font-semibold text-wl-on-surface">
                  <svg lucideIdCard class="size-5 text-wl-primary" aria-hidden="true"></svg>{{ t().basics }}</h3>
                <dl data-testid="person-dialog-basics" class="grid grid-cols-2 border-l border-t border-wl-outline-variant md:grid-cols-4">
                  @for (row of rows(); track row.key) {
                    <div [attr.data-testid]="'person-field-' + row.key" class="min-w-0 border-b border-r border-wl-outline-variant px-3 py-3">
                      <dt class="text-[12px] text-wl-on-surface-variant">{{ row.label }}</dt>
                      <dd class="mt-1 break-words text-[15px] leading-snug text-wl-on-surface md:text-[16px]">
                        @if (row.value) { <span>{{ row.value }}</span> }
                        @else { <span data-testid="person-field-empty" class="text-wl-on-surface-variant">{{ row.empty }}</span> }
                        <ng-container *ngTemplateOutlet="sup; context: { $implicit: notesFor(row.key) }" />
                      </dd>
                    </div>
                  }
                </dl>
              </section>

              <!-- 生平：舒適閱讀寬度與行高 -->
              <section [id]="sectionId('bio')" data-section="bio" data-testid="person-dialog-section-bio" [attr.aria-labelledby]="sectionId('bio') + '-h'">
                <h3 [id]="sectionId('bio') + '-h'" class="mb-3 flex items-center gap-2 border-b border-wl-outline-variant pb-2 font-wl-serif text-[18px] font-semibold text-wl-on-surface">
                  <svg lucideScrollText class="size-5 text-wl-primary" aria-hidden="true"></svg>{{ t().summary }}</h3>
                <div class="max-w-[68ch]">
                  @for (p of paragraphs(); track $index; let last = $last) {
                    <p data-testid="person-paragraph" class="mb-3 text-[15px] leading-[1.9] text-wl-on-surface md:text-[16px]">{{ p }}@if (last) {<ng-container *ngTemplateOutlet="sup; context: { $implicit: notesFor('summary') }" />}</p>
                  } @empty {
                    <p data-testid="person-paragraph-empty" class="wl-text2 text-wl-on-surface-variant">{{ t().noValue }}</p>
                  }
                </div>
              </section>

              <!-- 職位與任期時間軸 -->
              <section [id]="sectionId('terms')" data-section="terms" data-testid="person-dialog-section-terms" [attr.aria-labelledby]="sectionId('terms') + '-h'">
                <h3 [id]="sectionId('terms') + '-h'" class="mb-1 flex items-center gap-2 border-b border-wl-outline-variant pb-2 font-wl-serif text-[18px] font-semibold text-wl-on-surface">
                  <svg lucideLandmark class="size-5 text-wl-primary" aria-hidden="true"></svg>{{ t().terms }}</h3>
                <p class="mb-3 text-[11px] text-wl-on-surface-variant">{{ t().termNote }}</p>
                <ol data-testid="person-terms" class="relative ml-2 border-l-2 border-wl-outline-variant">
                  @for (term of terms(); track term.recordId) {
                    <li data-testid="person-term" [attr.data-record-id]="term.recordId" [attr.data-role]="term.role" class="relative mb-4 pl-5 last:mb-0">
                      <span aria-hidden="true" class="absolute -left-[7px] top-1.5 size-3 rounded-full border-2 border-wl-primary bg-wl-surface"></span>
                      <div data-testid="person-term-period" class="font-mono text-[13px] tabular-nums text-wl-primary">{{ term.period }}</div>
                      <div class="mt-0.5 flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-[15px]">
                        <span class="font-semibold text-wl-on-surface">{{ term.roleText }}</span>
                        @if (term.title) { <span class="text-wl-on-surface-variant">{{ term.title }}</span> }
                        <ng-container *ngTemplateOutlet="sup; context: { $implicit: notesFor('term:' + term.recordId) }" />
                      </div>
                      <div class="text-[13px] text-wl-on-surface-variant">{{ term.regime }}</div>
                    </li>
                  } @empty {
                    <li class="pl-5 wl-text2 text-wl-on-surface-variant">{{ t().noValue }}</li>
                  }
                </ol>
              </section>

              <!-- 資料來源：底部統一收合；N＝去重後的來源數；缺來源明示「待補來源」 -->
              <section [id]="sectionId('sources')" data-section="sources" data-testid="person-dialog-sources" class="rounded-md border border-wl-outline-variant bg-wl-surface-container">
                <h3 class="m-0">
                  <button type="button" data-testid="person-sources-toggle" [attr.aria-expanded]="sourcesOpen() ? 'true' : 'false'" [attr.aria-controls]="sectionId('sources') + '-panel'"
                    class="flex min-h-11 w-full items-center gap-2 px-3 text-left font-wl-serif text-[16px] font-semibold text-wl-on-surface focus-visible:outline-2 focus-visible:outline-wl-secondary"
                    (click)="sourcesOpen.set(!sourcesOpen())">
                    <svg lucideLibrary class="size-5 text-wl-primary" aria-hidden="true"></svg>
                    <span data-testid="person-sources-label" class="flex-1">{{ t().sources }} ({{ footnotes().length }})</span>
                    @if (missing().length) { <span data-testid="source-pending" class="rounded-sm border border-dashed border-wl-outline px-1.5 font-wl-sans text-[11px] font-normal text-wl-on-surface-variant">{{ t().pending }}</span> }
                    <svg lucideChevronDown class="size-4 transition-transform" [class.rotate-180]="sourcesOpen()" aria-hidden="true"></svg>
                  </button>
                </h3>
                <div [id]="sectionId('sources') + '-panel'" data-testid="person-sources-panel" [hidden]="!sourcesOpen()" class="border-t border-wl-outline-variant px-3 py-3">
                  @if (footnotes().length) {
                    <ol class="space-y-3">
                      @for (f of footnotes(); track f.n) {
                        <li data-testid="person-source-note" [id]="sectionId('src-' + f.n)" [attr.data-n]="f.n" tabindex="-1" class="flex gap-2 rounded-sm outline-none focus-visible:outline-2 focus-visible:outline-wl-secondary">
                          <span class="w-6 flex-none pt-1 text-right font-mono text-[12px] text-wl-primary">[{{ f.n }}]</span>
                          <div class="min-w-0 flex-1">
                            <div data-testid="person-source-used-for" class="mb-0.5 text-[11px] text-wl-on-surface-variant">{{ t().usedFor }}：{{ f.usedFor.join('、') }}</div>
                            <wl-source-disclosure [items]="[f.item]" [lang]="lang()" [inline]="true" />
                          </div>
                        </li>
                      }
                    </ol>
                  }
                  @if (missing().length) {
                    <p data-testid="person-sources-missing" class="wl-text2 text-wl-on-surface-variant" [class.mt-3]="footnotes().length">
                      <span class="rounded-sm border border-dashed border-wl-outline px-1.5 text-[11px]">{{ t().pending }}</span>
                      {{ t().missing }}：{{ missing().join('、') }}</p>
                  }
                </div>
              </section>
            </div>
          }
        </div>
      </section>
    </div>
    <!-- 上標來源編號：點了展開底部來源並捲到該筆；沒有來源時不放（底部列出待補欄位）。
         手機：點擊區高 44px；每個編號實寬 ≥32px，同組第一個往左、最後一個往右再延伸，單一編號 44×44、相鄰編號不重疊 -->
    <ng-template #sup let-ns>
      @for (n of ns; track n) {
        <button type="button" data-testid="person-field-sup" [attr.data-n]="n" [attr.aria-label]="t().sourceRef + ' ' + n"
          class="relative ml-0.5 inline-block align-super font-mono px-px text-center after:absolute after:-inset-y-2.5 after:inset-x-0 after:content-[''] text-[10px] leading-none text-wl-primary hover:underline focus-visible:outline-2 focus-visible:outline-wl-secondary max-md:ml-0 max-md:min-w-8 max-md:after:bottom-auto max-md:after:top-1/2 max-md:after:h-11 max-md:after:-translate-y-1/2 max-md:first-of-type:after:-left-1.5 max-md:last-of-type:after:-right-1.5"
          (click)="showNote(n)">{{ n }}</button>
      }
    </ng-template>
  `,
})
export class PersonDialog {
  readonly state = input.required<PersonDialogState>();
  readonly lang = input<Lang>('zh-Hant');
  readonly closed = output<void>();

  protected readonly titleId = 'wl-person-dialog-title';
  private readonly uid = `wl-pd-${++seq}`;
  protected readonly imgFailed = signal(false);
  protected readonly sourcesOpen = signal(false);
  protected readonly activeSection = signal<SectionKey>('basics');
  private readonly panel = viewChild<ElementRef<HTMLElement>>('panel');
  private readonly closeBtn = viewChild<ElementRef<HTMLButtonElement>>('closeBtn');
  private readonly body = viewChild<ElementRef<HTMLElement>>('body');
  private readonly injector = inject(Injector);

  protected readonly t = computed(() => TXT[this.lang() === 'en' ? 'en' : 'zh-Hant']);
  protected readonly bio = computed(() => { const s = this.state(); return s.status === 'ok' ? s.data : null; });
  protected readonly title = computed(() => {
    const b = this.bio();
    if (!b) return this.t().dialog;
    return (this.lang() === 'en' ? b.name : b.nameZh || b.name) || b.name;
  });
  /** 原文名（另一種寫法；與標題相同就不重複）。 */
  protected readonly originalName = computed(() => {
    const b = this.bio();
    if (!b) return '';
    const other = this.lang() === 'en' ? b.nameZh : b.name;
    return other && other !== this.title() ? other : '';
  });
  protected readonly portrait = computed(() => { const p = this.bio()?.portrait; return portraitDisplayable(p) ? p : null; });
  protected sectionId(k: string): string { return `${this.uid}-${k}`; }

  private readonly sortedTerms = computed(() => [...(this.bio()?.terms ?? [])].sort((a, b) => (a.validPeriod.start ?? '').localeCompare(b.validPeriod.start ?? '')));
  /** 頂列檔案標記：第一個任期的政權顯示名（來自資料）。 */
  protected readonly regimeLabel = computed(() => {
    const x = this.sortedTerms()[0];
    return x ? pickLocalized(x.regimeName, this.lang()) || x.regimeSlug : '';
  });
  /** 角色標籤：每個角色一個（含任期年份），國家元首在前（與人物卡一致），同角色依任期開始。 */
  protected readonly roleChips = computed(() => [...this.sortedTerms()].sort((a, b) => roleRank(a.role) - roleRank(b.role)).map((x) => {
    const end = inclusiveEnd(x.validPeriod.end);
    const years = `${(x.validPeriod.start ?? '').slice(0, 4)}–${end ? end.slice(0, 4) : ''}`;
    return { key: x.recordId, text: `${this.t().role[x.role] ?? x.role} ${years}` };
  }));
  protected readonly lifeText = computed(() => {
    const b = this.bio();
    if (!b) return '';
    const born = formatPartialDate(b.birthDate, b.birthDatePrecision);
    const died = formatPartialDate(b.deathDate, b.deathDatePrecision);
    return born || died ? `${born || '?'} – ${died || '?'}` : '';
  });

  protected readonly rows = computed(() => {
    const b = this.bio();
    if (!b) return [];
    const t = this.t();
    const lang = this.lang();
    const partyStatus = b.fieldSources?.['party']?.status;
    return [
      { key: 'birthDate', label: t.birth, value: formatPartialDate(b.birthDate, b.birthDatePrecision), empty: t.noValue },
      { key: 'deathDate', label: t.death, value: formatPartialDate(b.deathDate, b.deathDatePrecision), empty: t.noValue },
      { key: 'birthPlace', label: t.birthPlace, value: pickLocalized(b.birthPlace, lang), empty: t.noValue },
      { key: 'party', label: t.party, value: pickLocalized(b.party, lang), empty: partyStatus === '不適用' ? t.notApplicable : t.noValue },
    ];
  });
  protected readonly paragraphs = computed(() => {
    const b = this.bio();
    const s = b ? pickLocalized(b.summary, this.lang()) : '';
    return s ? s.split(/\n{2,}/).map((x) => x.trim()).filter(Boolean) : [];
  });
  protected readonly terms = computed(() => {
    const t = this.t();
    return this.sortedTerms().map((x) => ({
      recordId: x.recordId, role: x.role, roleText: t.role[x.role] ?? x.role, title: x.title,
      regime: pickLocalized(x.regimeName, this.lang()) || x.regimeSlug,
      period: formatTerm(x.validPeriod, this.lang()),
    }));
  });

  /** 每個欄位（含照片、各任期）各自的來源；不互相借用。 */
  private readonly fieldItems = computed((): { key: string; label: string; items: SourceItem[] }[] => {
    const b = this.bio();
    if (!b) return [];
    const t = this.t();
    const out = [
      { key: 'name', label: t.name, items: [...fieldSourceItems(b, 'name'), ...fieldSourceItems(b, 'nameZh')] },
      ...this.rows().map((r) => ({ key: r.key, label: r.label, items: fieldSourceItems(b, r.key) })),
      { key: 'summary', label: t.summary, items: fieldSourceItems(b, 'summary') },
      ...this.terms().map((x) => ({ key: `term:${x.recordId}`, label: `${t.terms}·${x.roleText}`, items: termSourceItems(this.sortedTerms().find((y) => y.recordId === x.recordId)!) })),
    ];
    const p = this.portrait();
    if (p) out.push({ key: 'portrait', label: t.photo, items: portraitSourceItems(p) });
    return out;
  });
  /** 去重後的註腳（同一出處用在多個欄位只列一次）＋每個欄位對應的編號。 */
  private readonly notes = computed(() => {
    const list: Footnote[] = [];
    const byKey = new Map<string, Footnote>();
    const fieldNotes = new Map<string, number[]>();
    for (const f of this.fieldItems()) {
      const ns: number[] = [];
      for (const it of f.items) {
        const k = [it.kind, it.title, it.url ?? '', it.locator ?? '', it.note ?? '', it.licenseCode ?? '', it.quote ?? ''].join('\u0001');
        let fn = byKey.get(k);
        if (!fn) { fn = { n: list.length + 1, item: it, usedFor: [] }; byKey.set(k, fn); list.push(fn); }
        if (!fn.usedFor.includes(f.label)) fn.usedFor.push(f.label);
        if (!ns.includes(fn.n)) ns.push(fn.n);
      }
      fieldNotes.set(f.key, ns);
    }
    return { list, fieldNotes };
  });
  protected readonly footnotes = computed(() => this.notes().list);
  protected notesFor(key: string): number[] { return this.notes().fieldNotes.get(key) ?? []; }
  /** 缺來源的欄位（只列有值或有段落的；沒有值的欄位本來就顯示「尚無資料」）。 */
  protected readonly missing = computed(() => {
    const b = this.bio();
    if (!b) return [];
    const hasValue = new Set<string>(['name', ...this.rows().filter((r) => r.value).map((r) => r.key), ...this.terms().map((x) => `term:${x.recordId}`)]);
    if (this.paragraphs().length) hasValue.add('summary');
    return this.fieldItems().filter((f) => hasValue.has(f.key) && f.items.length === 0).map((f) => f.label);
  });

  protected readonly sections = computed((): { key: SectionKey; label: string; count: number | null }[] => {
    const t = this.t();
    return [
      { key: 'basics', label: t.basics, count: null },
      { key: 'bio', label: t.summary, count: null },
      { key: 'terms', label: t.terms, count: this.terms().length || null },
      { key: 'sources', label: t.sources, count: this.footnotes().length },
    ];
  });

  /** 分頁籤：捲到區塊（只捲對話框內容區，不用 scrollIntoView 以免動到底層）。 */
  protected goTo(k: SectionKey): void {
    this.activeSection.set(k);
    this.spyPausedUntil = performance.now() + 500;
    if (k === 'sources') this.sourcesOpen.set(true);
    afterNextRender(() => this.scrollToEl(document.getElementById(this.sectionId(k))), { injector: this.injector });
  }
  /** 上標編號：展開底部來源、捲到該筆並聚焦。 */
  protected showNote(n: number): void {
    this.sourcesOpen.set(true);
    afterNextRender(() => {
      const el = document.getElementById(this.sectionId('src-' + n));
      this.scrollToEl(el);
      el?.focus({ preventScroll: true });
    }, { injector: this.injector });
  }
  private scrollToEl(el: HTMLElement | null): void {
    const box = this.body()?.nativeElement;
    if (!el || !box) return;
    const nav = box.querySelector<HTMLElement>('[data-testid="person-dialog-tabs"]');
    const delta = el.getBoundingClientRect().top - box.getBoundingClientRect().top - (nav?.offsetHeight ?? 0) - 8;
    box.scrollTo({ top: box.scrollTop + delta, behavior: 'auto' });
  }
  /** 捲動時更新目前區塊（最後一個頂端已過分頁籤的區塊）。 */
  private spyPausedUntil = 0;
  protected onScroll(): void {
    // 分頁籤點擊造成的捲動：保留使用者點的分頁（區塊太短時捲不到頂，不要被改成下一個）
    if (performance.now() < this.spyPausedUntil) return;
    const box = this.body()?.nativeElement;
    if (!box) return;
    const nav = box.querySelector<HTMLElement>('[data-testid="person-dialog-tabs"]');
    const line = box.getBoundingClientRect().top + (nav?.offsetHeight ?? 0) + 24;
    let cur: SectionKey = 'basics';
    for (const s of box.querySelectorAll<HTMLElement>('[data-section]')) if (s.getBoundingClientRect().top <= line) cur = s.dataset['section'] as SectionKey;
    if (box.scrollTop + box.clientHeight >= box.scrollHeight - 2) cur = 'sources';
    if (cur !== this.activeSection()) this.activeSection.set(cur);
  }

  constructor() {
    // 開啟時焦點移到關閉鈕（標題可被讀到：aria-labelledby）
    afterNextRender(() => (this.closeBtn()?.nativeElement ?? this.panel()?.nativeElement)?.focus({ preventScroll: true }), { injector: this.injector });
  }
}
