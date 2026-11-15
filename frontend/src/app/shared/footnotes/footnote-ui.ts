import { ChangeDetectionStrategy, Component, ElementRef, computed, inject, input, model, output } from '@angular/core';
import type { Footnote } from '../../core/footnotes';
import type { Lang } from '../../core/i18n';
import { SourceDisclosure } from '../source-disclosure/source-disclosure';

/**
 * 出處的三個共用零件（國界卡片、衝突卡片、人物卡共用；人物彈窗是同一種做法）：
 *   wl-status-chip     狀態標籤（已查證／待查證）；有說明時做成提示
 *   wl-footnote-sups   內容旁的上標編號
 *   wl-footnote-list   統一的「資料來源 (n)」清單（預設收合；reveal(n) 展開並捲到那一筆）
 * 編號由 core/footnotes.ts 的 numberSources() 算；一筆來源怎麼顯示交給 wl-source-disclosure。
 * testid 一律是「前綴-名稱」（例：sovereignty-card-sup），前綴由使用的卡片給。
 */

const TXT = {
  'zh-Hant': { sources: '資料來源', usedFor: '用於', sourceRef: '來源' },
  en: { sources: 'Sources', usedFor: 'Used for', sourceRef: 'Source' },
} as const;

@Component({
  selector: 'wl-status-chip',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'inline-block align-baseline' },
  template: `
    @if (tip()) {
      <span class="group relative inline-block">
        <button type="button" [attr.data-testid]="testId()" [attr.title]="tip()" [attr.aria-label]="text() + '：' + tip()" [class]="verified() ? 'wl-stamp' : 'wl-chip-interp'" class="cursor-help">{{ text() }}</button>
        <span role="tooltip" [attr.data-testid]="testId() + '-tip'" class="pointer-events-none absolute left-0 top-full z-10 mt-1 hidden w-56 rounded-sm border border-wl-outline-variant bg-wl-surface px-2 py-1 text-[12px] font-normal leading-snug text-wl-on-surface shadow-md group-focus-within:block group-hover:block">{{ tip() }}</span>
      </span>
    } @else {
      <span [attr.data-testid]="testId()" [class]="verified() ? 'wl-stamp' : 'wl-chip-interp'">{{ text() }}</span>
    }
  `,
})
export class StatusChip {
  readonly text = input.required<string>();
  /** 說明（為什麼是這個狀態）；空字串＝只有標籤。滑鼠移上或鍵盤聚焦時顯示，同時給 title 與螢幕閱讀器。 */
  readonly tip = input('');
  readonly verified = input(false);
  readonly testId = input('status-chip');
}

@Component({
  selector: 'wl-footnote-sups',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'inline' },
  template: `@for (n of ns(); track n) {<button type="button" [attr.data-testid]="prefix() + '-sup'" [attr.data-n]="n" [attr.aria-label]="t().sourceRef + ' ' + n"
      class="relative ml-0.5 inline-block px-px align-super font-mono text-[10px] leading-none text-wl-primary after:absolute after:-inset-y-2.5 after:inset-x-0 after:content-[''] hover:underline focus-visible:outline-2 focus-visible:outline-wl-secondary"
      (click)="pick.emit(n)">{{ n }}</button>}`,
})
export class FootnoteSups {
  readonly ns = input<readonly number[]>([]);
  readonly prefix = input('footnote');
  readonly lang = input<Lang>('zh-Hant');
  readonly pick = output<number>();
  protected readonly t = computed(() => TXT[this.lang() === 'en' ? 'en' : 'zh-Hant']);
}

let listSeq = 0;

@Component({
  selector: 'wl-footnote-list',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SourceDisclosure],
  host: { class: 'block' },
  template: `
    @if (footnotes().length) {
      <section [attr.data-testid]="prefix() + '-sources'" class="border border-wl-outline-variant bg-wl-surface-container" [class]="dense() ? 'rounded-sm' : 'rounded-md'">
        <h3 class="m-0">
          <button type="button" [attr.data-testid]="prefix() + '-sources-toggle'" [attr.aria-expanded]="open() ? 'true' : 'false'" [attr.aria-controls]="uid + '-panel'"
            class="flex w-full items-center text-left font-semibold text-wl-on-surface focus-visible:outline-2 focus-visible:outline-wl-secondary"
            [class]="dense() ? 'min-h-11 gap-1.5 px-2 text-[12px] md:min-h-7' : 'min-h-9 gap-2 px-3 wl-text2'"
            (click)="open.set(!open())">
            <span aria-hidden="true" class="inline-block w-2 text-center">{{ open() ? '▾' : '▸' }}</span>
            <span [attr.data-testid]="prefix() + '-sources-label'" class="flex-1">{{ t().sources }} ({{ footnotes().length }})</span>
          </button>
        </h3>
        <div [id]="uid + '-panel'" [attr.data-testid]="prefix() + '-sources-panel'" [hidden]="!open()" class="border-t border-wl-outline-variant" [class]="dense() ? 'px-2 py-1.5' : 'px-3 py-2'">
          <ol [class]="dense() ? 'space-y-1.5' : 'space-y-2'">
            @for (f of footnotes(); track f.n) {
              <li [attr.data-testid]="prefix() + '-source-note'" [id]="uid + '-' + f.n" [attr.data-n]="f.n" tabindex="-1" class="flex rounded-sm outline-none focus-visible:outline-2 focus-visible:outline-wl-secondary" [class]="dense() ? 'gap-1.5' : 'gap-2'">
                <span class="flex-none pt-1 text-right font-mono text-wl-primary" [class]="dense() ? 'w-5 text-[11px]' : 'w-6 text-[12px]'">[{{ f.n }}]</span>
                <div class="min-w-0 flex-1">
                  <div [attr.data-testid]="prefix() + '-source-used-for'" class="mb-0.5 text-[11px] text-wl-on-surface-variant">{{ t().usedFor }}：{{ f.usedFor.join('、') }}</div>
                  <wl-source-disclosure [items]="[f.item]" [lang]="lang()" [inline]="true" />
                </div>
              </li>
            }
          </ol>
        </div>
      </section>
    }
  `,
})
export class FootnoteList {
  readonly footnotes = input<readonly Footnote[]>([]);
  readonly prefix = input('footnote');
  readonly lang = input<Lang>('zh-Hant');
  /** 小卡片用的緊湊版（人物卡）。 */
  readonly dense = input(false);
  readonly open = model(false);

  protected readonly uid = `wl-fn-${++listSeq}`;
  protected readonly t = computed(() => TXT[this.lang() === 'en' ? 'en' : 'zh-Hant']);
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  /** 上標編號被點：展開清單、捲到該筆並聚焦。 */
  reveal(n: number): void {
    this.open.set(true);
    setTimeout(() => {
      const el = this.host.nativeElement.querySelector<HTMLElement>(`#${this.uid}-${n}`);
      el?.scrollIntoView?.({ block: 'nearest' }); // 測試環境（jsdom）沒有 scrollIntoView
      el?.focus({ preventScroll: true });
    });
  }
}
