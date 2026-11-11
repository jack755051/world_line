import { ChangeDetectionStrategy, Component, computed, effect, input, signal, untracked } from '@angular/core';
import type { Lang } from '../../core/i18n';
import { licenseLabel } from '../../core/licenses';

/** 一筆可顯示的來源。structured＝接到 sources 表的引用；legacy＝舊格式自由文字出處（不算已查證）。 */
export interface SourceItem {
  kind: 'structured' | 'legacy';
  title: string;
  publisher?: string | null;
  locator?: string | null;
  licenseCode?: string | null;
  url?: string | null;
  note?: string | null;
  accessedOn?: string | null;
  /** 引自該來源的原文短引（逐字；API 為 null 時不帶）。 */
  quote?: string | null;
  /** 引文語言（BCP 47），用於 lang 屬性。 */
  quoteLang?: string | null;
}

/** 「全部展開／收合」指令：v 每次遞增才會套用（不保存狀態）。 */
export interface ExpandCommand { open: boolean; v: number }

const TXT = {
  'zh-Hant': { sources: '來源', pending: '待補來源', legacy: '出處備註（未接結構化來源，非查證標記）', locator: '位置', license: '授權', accessed: '查證日期', open: '開啟', quote: '引文', qOpen: '「', qClose: '」' },
  en: { sources: 'Sources', pending: 'Source needed', legacy: 'Source note (not a structured citation; not marked verified)', locator: 'Locator', license: 'Licence', accessed: 'Checked', open: 'Open', quote: 'Quotation', qOpen: '“', qClose: '”' },
} as const;

let seq = 0;

/**
 * 來源收合元件（設計 §6.1）：預設收合；按鈕位置固定，展開區在按鈕下方推開內容。
 * 沒有任何來源時只渲染靜態文字「待補來源」（不渲染按鈕、不只靠顏色）。
 */
@Component({
  selector: 'wl-source-disclosure',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'block' },
  template: `
    @if (items().length === 0) {
      <span data-testid="source-pending" class="inline-flex min-h-6 items-center rounded-sm border border-dashed border-wl-outline px-1.5 text-[11px] text-wl-on-surface-variant">{{ t().pending }}</span>
    } @else {
      @if (!inline()) {
      <button type="button" data-testid="source-toggle" [attr.aria-expanded]="open() ? 'true' : 'false'" [attr.aria-controls]="panelId"
        [attr.aria-label]="(label() ? label() + ' — ' : '') + t().sources + '（' + items().length + '）'"
        class="inline-flex min-h-11 items-center gap-1 rounded-sm px-1 text-[11px] text-wl-secondary md:min-h-6 hover:underline focus-visible:outline-2 focus-visible:outline-wl-secondary"
        [attr.data-kind]="hasStructured() ? 'structured' : 'legacy'" (click)="open.set(!open())">
        <span aria-hidden="true" class="inline-block w-2 text-center">{{ open() ? '▾' : '▸' }}</span>{{ t().sources }}（{{ items().length }}）
      </button>
      }
      <div [id]="panelId" data-testid="source-panel" [hidden]="!inline() && !open()" [class.mt-1]="!inline()" class="space-y-1.5 rounded-sm border-l-2 border-wl-outline-variant bg-wl-surface-container-low py-1 pl-2 pr-1 text-[12px]">
        @for (s of items(); track $index) {
          <div data-testid="source-item" [attr.data-kind]="s.kind">
            @if (s.kind === 'legacy') { <div class="text-[11px] text-wl-on-surface-variant">{{ t().legacy }}</div> }
            <div class="break-words">
              @if (s.url) { <a data-testid="source-link" [href]="s.url" target="_blank" rel="noopener noreferrer" class="text-wl-secondary hover:underline max-md:py-3.5">{{ s.title }}</a> } @else { {{ s.title }} }
              @if (s.publisher && s.publisher !== s.title) { <span class="text-wl-on-surface-variant">·{{ s.publisher }}</span> }
            </div>
            @if (s.locator) { <div class="text-wl-on-surface-variant">{{ t().locator }}：{{ s.locator }}</div> }
            <!-- 引文：逐字、不截斷；與出處備註相同時只列引文一次 -->
            @if (s.quote) {
              <blockquote data-testid="source-quote" class="my-0.5 whitespace-pre-line break-words border-l-2 border-wl-outline pl-2 font-wl-serif text-[13px] leading-relaxed text-wl-on-surface"><span class="sr-only">{{ t().quote }}：</span><span aria-hidden="true">{{ t().qOpen }}</span><span data-testid="source-quote-text" [attr.lang]="s.quoteLang || null">{{ s.quote }}</span><span aria-hidden="true">{{ t().qClose }}</span></blockquote>
            }
            @if (s.note && s.note !== s.quote) { <div class="whitespace-pre-line text-wl-on-surface-variant">{{ s.note }}</div> }
            @if (s.licenseCode || s.accessedOn) {
              <div class="text-[11px] text-wl-on-surface-variant">
                @if (s.licenseCode) { {{ t().license }}：{{ license(s.licenseCode) }} }
                @if (s.licenseCode && s.accessedOn) { · }
                @if (s.accessedOn) { {{ t().accessed }}：{{ s.accessedOn }} }
              </div>
            }
          </div>
        }
      </div>
    }
  `,
})
export class SourceDisclosure {
  readonly items = input<SourceItem[]>([]);
  readonly lang = input<Lang>('zh-Hant');
  /** 給螢幕閱讀器的欄位名（例：「出生」）。 */
  readonly label = input('');
  readonly expand = input<ExpandCommand | null>(null);
  /** 直接列出來源、不渲染收合按鈕（外層已有統一的收合，例如人物詳情底部「資料來源」）。 */
  readonly inline = input(false);

  protected readonly panelId = `wl-src-${++seq}`;
  protected readonly open = signal(false);
  protected readonly t = computed(() => TXT[this.lang() === 'en' ? 'en' : 'zh-Hant']);
  protected readonly hasStructured = computed(() => this.items().some((s) => s.kind === 'structured'));
  protected license(code: string): string { return licenseLabel(code, this.lang()) ?? code; }

  constructor() {
    effect(() => {
      const c = this.expand();
      if (c) untracked(() => this.open.set(c.open));
    });
  }
}
