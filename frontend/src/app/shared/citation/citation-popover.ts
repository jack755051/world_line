import { ChangeDetectionStrategy, Component, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { LucideCircleAlert, LucideExternalLink, LucideNotebookText, LucideTriangleAlert, LucideX } from '@lucide/angular';
import { SpinnerComponent } from '../../components/ui/spinner';
import type { CitationDto, SourceDto } from '../../core/api/api-types';
import { WorldLineApi } from '../../core/api/world-line-api';
import { hasKey, t, type I18nKey, type Lang } from '../../core/i18n';
import { licenseLabel } from '../../core/licenses';

/** 來源詳情快取（跨 popover 共用，只讀）。 */
const sourceCache = new Map<string, Promise<SourceDto>>();

/**
 * 來源 popover（PRD §8.9，`shared/citation`）。
 * 引用本身（locator、角色、evidence note、授權代碼）隨控制紀錄一起來；開啟時再取 `/sources/{id}` 補作者、出版日期、
 * 館藏號、授權依據與連結。I6 規定必有來源：清單為空時顯示資料錯誤警示。
 */
@Component({
  selector: 'wl-citation-popover',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SpinnerComponent, LucideNotebookText, LucideExternalLink, LucideX, LucideTriangleAlert, LucideCircleAlert],
  template: `
    <button type="button" data-testid="citation-button" [attr.aria-expanded]="open()" aria-haspopup="dialog" (click)="open.set(!open())"
        class="wl-btn-secondary inline-flex h-7 items-center gap-1.5 px-2 text-[length:var(--wl-type-text2-size)]">
        <svg lucideNotebookText class="size-3.5"></svg>{{ tr('citation.button') }}
        <span class="text-wl-on-surface-variant">{{ citations().length }}</span>
      </button>
      @if (open()) {
        <!-- Stitch W6：360px 檔案目錄卡，停靠在右側（頂部列下方 16px、時間軸上方），不蓋住頂部列 -->
        <section data-testid="citation-popover" role="dialog" [attr.aria-label]="tr('citation.title')" tabindex="-1" (keydown.escape)="open.set(false)"
          class="wl-paper fixed right-4 top-[calc(var(--wl-topbar-height)+16px)] z-30 flex w-[360px] max-h-[calc(100vh-var(--wl-topbar-height)-var(--wl-timeline-height)-32px)] flex-col">
          <header class="flex items-center justify-between px-4 pt-3 pb-2">
            <h2 class="wl-title2">{{ tr('citation.title') }}（{{ citations().length }}）</h2>
            <button type="button" class="wl-icon-btn" [attr.aria-label]="tr('card.close')" (click)="open.set(false)"><svg lucideX class="size-4"></svg></button>
          </header>
          <div class="overflow-y-auto px-4 pb-4">
            @if (citations().length === 0) {
              <div data-testid="citation-missing-warning" role="alert" class="wl-alert-error"><svg lucideTriangleAlert class="size-4 flex-none"></svg>{{ tr('citation.missing') }}</div>
            }
            <ol class="flex flex-col gap-3">
              @for (c of sorted(); track c.sourceId + c.locator; let i = $index) {
                <li data-testid="citation-item" class="rounded-wl-md border border-wl-outline-variant bg-wl-surface-container p-3">
                  <h3 class="font-wl-serif text-[length:var(--wl-type-sub-title-size)] font-semibold leading-[1.5]">{{ c.sourceTitle }}</h3>
                  <div class="mt-1.5 flex flex-col gap-1.5 wl-text2">
                    <p class="text-wl-on-surface-variant">{{ tr('citation.publisher') }}：<span class="text-wl-on-surface">{{ c.publisher }}</span>
                      @if (detail(c.sourceId)?.publishedText; as pt) { <span class="mx-1 text-wl-outline">｜</span>{{ pt }} }</p>
                    @if (detail(c.sourceId)?.authors; as au) { <p class="text-wl-on-surface-variant">{{ tr('citation.authors') }}：<span class="text-wl-on-surface">{{ au }}</span></p> }
                    @if (detail(c.sourceId)?.catalogId; as cat) {
                      <p><span data-testid="citation-catalog" class="inline-block rounded-wl-sm border border-wl-tertiary px-1.5 py-0.5 wl-archival">{{ tr('citation.catalog') }} {{ cat }}</span></p>
                    }
                    <p class="text-wl-on-surface-variant">{{ tr('citation.locator') }}：<span data-testid="citation-locator" class="wl-archival">{{ c.locator }}</span></p>
                    <p class="text-wl-on-surface-variant">{{ tr('citation.role') }}：<span class="font-semibold text-wl-on-surface">{{ roleLabel(c.role) }}</span></p>
                    <p class="text-wl-on-surface-variant">{{ tr('citation.note') }}：<span class="text-wl-on-surface">{{ c.evidenceNote }}</span></p>
                  </div>
                  <div class="mt-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-t border-wl-outline-variant pt-2 wl-text2">
                    <span data-testid="citation-license" class="text-wl-on-surface-variant">{{ tr('citation.license') }}：<span class="font-semibold text-wl-on-surface">{{ license(c.licenseCode) ?? tr('citation.licenseNone') }}</span>
                      @if (detail(c.sourceId)?.licenseEvidenceUrl; as u) {
                        <a class="wl-link ml-1" [href]="u" target="_blank" rel="noopener noreferrer">{{ tr('citation.licenseEvidence') }}</a>
                      }
                    </span>
                    @if (detail(c.sourceId); as s) {
                      @if (s.url || s.archiveUrl) {
                        <span class="flex items-center gap-2">
                          @if (s.url) { <a class="wl-link inline-flex items-center gap-1" [href]="s.url" target="_blank" rel="noopener noreferrer">{{ tr('citation.url') }}<svg lucideExternalLink class="size-3"></svg></a> }
                          @if (s.url && s.archiveUrl) { <span class="text-wl-outline" aria-hidden="true">｜</span> }
                          @if (s.archiveUrl) { <a class="wl-link inline-flex items-center gap-1" [href]="s.archiveUrl" target="_blank" rel="noopener noreferrer">{{ tr('citation.archive') }}<svg lucideExternalLink class="size-3"></svg></a> }
                        </span>
                      }
                    } @else if (status()[c.sourceId] === 'loading') {
                      <span class="flex items-center gap-1.5 text-wl-on-surface-variant"><sanring-spinner size="sm" [ariaLabel]="tr('citation.loading')" />{{ tr('citation.loading') }}</span>
                    } @else if (status()[c.sourceId] === 'error') {
                      <span class="flex items-center gap-1 text-wl-error"><svg lucideCircleAlert class="size-3.5"></svg>{{ tr('citation.detailError') }}
                        <button type="button" class="wl-link" (click)="fetch(c.sourceId, true)">{{ tr('map.retry') }}</button></span>
                    }
                  </div>
                </li>
              }
            </ol>
          </div>
        </section>
      }
  `,
})
export class CitationPopover {
  private readonly api = inject(WorldLineApi);
  readonly citations = input.required<CitationDto[]>();
  readonly lang = input<Lang>('zh-Hant');

  protected readonly open = signal(false);
  protected readonly details = signal<Record<string, SourceDto>>({});
  protected readonly status = signal<Record<string, 'loading' | 'error'>>({});

  /** 主要地圖來源排前面，其餘照 API 順序 */
  protected readonly sorted = computed(() => {
    const order = ['primary', 'auxiliary_geometry', 'date_check'];
    return [...this.citations()].sort((a, b) => order.indexOf(a.role) - order.indexOf(b.role));
  });

  constructor() {
    effect(() => {
      if (!this.open()) return;
      const ids = [...new Set(this.citations().map((c) => c.sourceId))];
      untracked(() => ids.forEach((id) => void this.fetch(id)));
    });
  }

  protected tr(key: I18nKey): string {
    return t(key, this.lang());
  }

  protected roleLabel(role: string): string {
    const key = `citation.role.${role}`;
    return hasKey(key) ? t(key, this.lang()) : role;
  }

  protected license(code: string | null | undefined): string | null {
    return licenseLabel(code, this.lang());
  }

  protected detail(id: string): SourceDto | undefined {
    return this.details()[id];
  }

  async fetch(id: string, retry = false): Promise<void> {
    if (this.details()[id]) return;
    if (retry) sourceCache.delete(id);
    this.status.update((s) => ({ ...s, [id]: 'loading' }));
    let p = sourceCache.get(id);
    if (!p) {
      p = this.api.source(id);
      sourceCache.set(id, p);
    }
    try {
      const s = await p;
      this.details.update((d) => ({ ...d, [id]: s }));
      this.status.update(({ [id]: _, ...rest }) => rest);
    } catch {
      sourceCache.delete(id);
      this.status.update((s) => ({ ...s, [id]: 'error' }));
    }
  }
}

/** 測試用：清掉跨元件快取 */
export function _resetCitationCache(): void {
  sourceCache.clear();
}
