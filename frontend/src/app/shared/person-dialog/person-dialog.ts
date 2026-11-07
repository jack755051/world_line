import { CdkTrapFocus } from '@angular/cdk/a11y';
import { afterNextRender, ChangeDetectionStrategy, Component, computed, ElementRef, inject, Injector, input, output, signal, viewChild } from '@angular/core';
import { LucideUserRound, LucideX } from '@lucide/angular';
import type { LeaderBio } from '../../core/api/world-line-api';
import type { Lang } from '../../core/i18n';
import { formatPartialDate, formatTerm, pickLocalized, portraitDisplayable } from '../../core/person-format';
import { fieldSourceItems, portraitSourceItems, termSourceItems } from '../../core/person-sources';
import { SourceDisclosure, type ExpandCommand } from '../source-disclosure/source-disclosure';

export type PersonDialogState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ok'; data: LeaderBio };

const TXT = {
  'zh-Hant': {
    close: '關閉', loading: '載入中…', error: '人物資料載入失敗', basics: '基本資料', name: '姓名', life: '生卒', birth: '出生', death: '去世',
    birthPlace: '出生地', party: '政黨', summary: '簡介', terms: '職位與任期', noValue: '尚無資料', notApplicable: '不適用',
    expandAll: '全部展開來源', collapseAll: '全部收合來源', photo: '照片', noPhoto: '無授權照片', test: '測試資料',
    termNote: '任期迄日不含當天，畫面顯示最後在任日。', dialog: '人物詳情', portraitOf: '的肖像',
    role: { head_of_state: '國家元首', head_of_government: '政府首腦' } as Record<string, string>,
  },
  en: {
    close: 'Close', loading: 'Loading…', error: 'Could not load this person', basics: 'Basic facts', name: 'Name', life: 'Life', birth: 'Born', death: 'Died',
    birthPlace: 'Birthplace', party: 'Party', summary: 'Summary', terms: 'Offices and terms', noValue: 'No data', notApplicable: 'Not applicable',
    expandAll: 'Expand all sources', collapseAll: 'Collapse all sources', photo: 'Photo', noPhoto: 'No licensed photo', test: 'Test data',
    termNote: 'Term end dates are exclusive; the last day in office is shown.', dialog: 'Person details', portraitOf: ' — portrait',
    role: { head_of_state: 'Head of State', head_of_government: 'Head of Gov\'t' } as Record<string, string>,
  },
} as const;

/**
 * 人物閱讀對話框（設計 §3.1-2、§4、§6）：桌機置中大視窗、手機全螢幕；role="dialog" aria-modal="true"、焦點鎖定、Esc 由頁面統一關閉。
 * 每個欄位與段落各自掛來源（預設收合）；沒有來源顯示「待補來源」；舊格式出處只當備註，不標已查證。
 */
@Component({
  selector: 'wl-person-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CdkTrapFocus, LucideX, LucideUserRound, SourceDisclosure],
  template: `
    <div class="fixed inset-0 z-[70]" data-testid="person-dialog-root">
      <div class="absolute inset-0 bg-black/45" aria-hidden="true" data-testid="person-dialog-backdrop" (click)="closed.emit()"></div>
      <section #panel data-testid="person-dialog" role="dialog" aria-modal="true" [attr.aria-labelledby]="titleId" tabindex="-1"
        cdkTrapFocus [cdkTrapFocusAutoCapture]="false"
        class="absolute inset-0 flex flex-col bg-wl-surface shadow-[var(--wl-shadow-panel)] outline-none md:inset-auto md:left-1/2 md:top-1/2 md:h-[min(88vh,820px)] md:w-[min(880px,92vw)] md:-translate-x-1/2 md:-translate-y-1/2 md:rounded-xl">
        <header class="flex flex-none items-center gap-2 border-b border-wl-outline-variant px-4 py-2 md:px-6 md:py-3">
          <h2 [id]="titleId" data-testid="person-dialog-title" class="wl-title2 min-w-0 flex-1 truncate">{{ title() }}</h2>
          @if (bio(); as b) {
            <button type="button" data-testid="person-dialog-expand-all" class="min-h-11 rounded-sm px-2 text-[12px] text-wl-secondary hover:underline md:min-h-8"
              (click)="toggleAll()">{{ allOpen() ? t().collapseAll : t().expandAll }}</button>
          }
          <button #closeBtn type="button" data-testid="person-dialog-close" [attr.aria-label]="t().close"
            class="inline-flex size-11 flex-none items-center justify-center rounded-full hover:bg-wl-surface-container-high focus-visible:outline-2 focus-visible:outline-wl-secondary"
            (click)="closed.emit()"><svg lucideX class="size-5" aria-hidden="true"></svg></button>
        </header>
        <div data-testid="person-dialog-body" class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4 md:px-6">
          @switch (state().status) {
            @case ('loading') { <p class="wl-text2 text-wl-on-surface-variant" role="status">{{ t().loading }}</p> }
            @case ('error') { <p class="wl-text2 text-wl-error" role="alert">{{ t().error }}</p> }
          }
          @if (bio(); as b) {
            <div class="flex flex-col gap-5 md:flex-row">
              <!-- 照片：只有授權欄位齊全才顯示；否則中性佔位圖（不用 AI 生成肖像） -->
              <figure class="flex-none md:w-[200px]" data-testid="person-dialog-figure">
                <div class="mx-auto h-[220px] w-[170px] overflow-hidden rounded-md bg-wl-surface-container-high md:mx-0 md:h-[250px] md:w-[200px]">
                  @if (portrait() && !imgFailed()) {
                    <img data-testid="person-dialog-photo" [src]="portrait()!.url" [alt]="title() + t().portraitOf" referrerpolicy="no-referrer"
                      class="size-full object-cover object-top" (error)="imgFailed.set(true)" />
                  } @else {
                    <div data-testid="person-dialog-placeholder" class="flex size-full items-center justify-center text-wl-outline" role="img" [attr.aria-label]="t().noPhoto">
                      <svg lucideUserRound class="size-16" aria-hidden="true"></svg></div>
                  }
                </div>
                @if (portrait(); as p) {
                  <figcaption class="mt-1.5 text-[11px] text-wl-on-surface-variant">
                    <div data-testid="person-dialog-photo-credit" class="break-words">{{ p.attribution }}</div>
                    <wl-source-disclosure [items]="portraitItems()" [lang]="lang()" [label]="t().photo" [expand]="expand()" />
                  </figcaption>
                }
              </figure>
              <div class="min-w-0 flex-1">
                @if (b.isTest) { <span class="mb-2 inline-block rounded-sm bg-wl-surface-container-high px-1 text-[11px]">{{ t().test }}</span> }
                <h3 class="wl-sub-title mb-2">{{ t().basics }}</h3>
                <dl data-testid="person-dialog-basics" class="grid grid-cols-[72px_1fr] gap-x-3 gap-y-2.5 wl-text2">
                  @for (row of rows(); track row.key) {
                    <dt class="pt-0.5 text-wl-on-surface-variant">{{ row.label }}</dt>
                    <dd [attr.data-testid]="'person-field-' + row.key" class="min-w-0">
                      @if (row.value) { <span [attr.lang]="row.valueLang">{{ row.value }}</span> }
                      @else { <span data-testid="person-field-empty" class="text-wl-on-surface-variant">{{ row.empty }}</span> }
                      <wl-source-disclosure class="mt-0.5" [items]="row.sources" [lang]="lang()" [label]="row.label" [expand]="expand()" />
                    </dd>
                  }
                </dl>
                <h3 class="wl-sub-title mb-2 mt-5">{{ t().summary }}</h3>
                <!-- 簡介：目前一筆 summary 視為一段；各段各自掛來源 -->
                @for (p of paragraphs(); track $index) {
                  <div data-testid="person-paragraph" class="mb-3">
                    <p class="wl-text1 leading-relaxed">{{ p }}</p>
                    <wl-source-disclosure class="mt-0.5" [items]="summarySources()" [lang]="lang()" [label]="t().summary" [expand]="expand()" />
                  </div>
                } @empty {
                  <p data-testid="person-paragraph-empty" class="wl-text2 text-wl-on-surface-variant">{{ t().noValue }}</p>
                  <wl-source-disclosure class="mt-0.5" [items]="summarySources()" [lang]="lang()" [label]="t().summary" [expand]="expand()" />
                }
                <h3 class="wl-sub-title mb-1 mt-5">{{ t().terms }}</h3>
                <p class="mb-2 text-[11px] text-wl-on-surface-variant">{{ t().termNote }}</p>
                <ol data-testid="person-terms" class="space-y-2">
                  @for (term of terms(); track term.recordId) {
                    <li data-testid="person-term" [attr.data-record-id]="term.recordId" [attr.data-role]="term.role" class="rounded-sm border border-wl-outline-variant px-3 py-2 wl-text2">
                      <div class="flex flex-wrap items-baseline gap-x-2">
                        <span class="font-semibold">{{ term.regime }}</span>
                        <span class="rounded-sm bg-wl-surface-container-high px-1 text-[11px] text-wl-on-surface-variant">{{ term.roleText }}</span>
                        @if (term.title) { <span class="text-wl-on-surface-variant">{{ term.title }}</span> }
                      </div>
                      <div data-testid="person-term-period" class="font-mono text-[12px] tabular-nums text-wl-on-surface-variant">{{ term.period }}</div>
                      <wl-source-disclosure class="mt-0.5" [items]="term.sources" [lang]="lang()" [label]="t().terms" [expand]="expand()" />
                    </li>
                  } @empty {
                    <li class="wl-text2 text-wl-on-surface-variant">{{ t().noValue }}</li>
                  }
                </ol>
              </div>
            </div>
          }
        </div>
      </section>
    </div>
  `,
})
export class PersonDialog {
  readonly state = input.required<PersonDialogState>();
  readonly lang = input<Lang>('zh-Hant');
  readonly closed = output<void>();

  protected readonly titleId = 'wl-person-dialog-title';
  protected readonly imgFailed = signal(false);
  protected readonly expand = signal<ExpandCommand | null>(null);
  protected readonly allOpen = signal(false);
  private readonly panel = viewChild<ElementRef<HTMLElement>>('panel');
  private readonly closeBtn = viewChild<ElementRef<HTMLButtonElement>>('closeBtn');
  private readonly injector = inject(Injector);

  protected readonly t = computed(() => TXT[this.lang() === 'en' ? 'en' : 'zh-Hant']);
  protected readonly bio = computed(() => { const s = this.state(); return s.status === 'ok' ? s.data : null; });
  protected readonly title = computed(() => {
    const b = this.bio();
    if (!b) return this.t().dialog;
    return (this.lang() === 'en' ? b.name : b.nameZh || b.name) || b.name;
  });
  protected readonly portrait = computed(() => { const p = this.bio()?.portrait; return portraitDisplayable(p) ? p : null; });
  protected readonly portraitItems = computed(() => { const p = this.portrait(); return p ? portraitSourceItems(p) : []; });

  protected readonly rows = computed(() => {
    const b = this.bio();
    if (!b) return [];
    const t = this.t();
    const lang = this.lang();
    const other = lang === 'en' ? b.nameZh : b.name !== this.title() ? b.name : b.nameZh;
    const partyStatus = b.fieldSources?.['party']?.status;
    return [
      { key: 'name', label: t.name, value: other && other !== this.title() ? `${this.title()}（${other}）` : this.title(), valueLang: null, empty: t.noValue,
        sources: [...fieldSourceItems(b, 'name'), ...fieldSourceItems(b, 'nameZh')] },
      { key: 'birthDate', label: t.birth, value: formatPartialDate(b.birthDate, b.birthDatePrecision), valueLang: null, empty: t.noValue, sources: fieldSourceItems(b, 'birthDate') },
      { key: 'deathDate', label: t.death, value: formatPartialDate(b.deathDate, b.deathDatePrecision), valueLang: null, empty: t.noValue, sources: fieldSourceItems(b, 'deathDate') },
      { key: 'birthPlace', label: t.birthPlace, value: pickLocalized(b.birthPlace, lang), valueLang: null, empty: t.noValue, sources: fieldSourceItems(b, 'birthPlace') },
      { key: 'party', label: t.party, value: pickLocalized(b.party, lang), valueLang: null,
        empty: partyStatus === '不適用' ? t.notApplicable : t.noValue, sources: fieldSourceItems(b, 'party') },
    ];
  });
  protected readonly paragraphs = computed(() => {
    const b = this.bio();
    const s = b ? pickLocalized(b.summary, this.lang()) : '';
    return s ? s.split(/\n{2,}/).map((x) => x.trim()).filter(Boolean) : [];
  });
  protected readonly summarySources = computed(() => { const b = this.bio(); return b ? fieldSourceItems(b, 'summary') : []; });
  protected readonly terms = computed(() => {
    const b = this.bio();
    const t = this.t();
    return (b?.terms ?? []).map((x) => ({
      recordId: x.recordId, role: x.role, roleText: t.role[x.role] ?? x.role, title: x.title,
      regime: pickLocalized(x.regimeName, this.lang()) || x.regimeSlug,
      period: formatTerm(x.validPeriod, this.lang()), sources: termSourceItems(x),
    }));
  });

  protected toggleAll(): void {
    const next = !this.allOpen();
    this.allOpen.set(next);
    this.expand.set({ open: next, v: (this.expand()?.v ?? 0) + 1 });
  }

  constructor() {
    // 開啟時焦點移到關閉鈕（標題可被讀到：aria-labelledby）
    afterNextRender(() => (this.closeBtn()?.nativeElement ?? this.panel()?.nativeElement)?.focus({ preventScroll: true }), { injector: this.injector });
  }
}
