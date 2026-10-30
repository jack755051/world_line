import { ChangeDetectionStrategy, Component, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { LucideExternalLink, LucideNotebookText, LucideX } from '@lucide/angular';
import { SANRING_POPOVER_IMPORTS } from '../../components/ui/popover';
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
  imports: [SANRING_POPOVER_IMPORTS, SpinnerComponent, LucideNotebookText, LucideExternalLink, LucideX],
  template: `
    <sanring-popover [(isOpen)]="open" align="start">
      <button sanringPopoverTrigger type="button" data-testid="citation-button"
        class="wl-btn-secondary inline-flex h-7 items-center gap-1.5 px-2 text-[length:var(--wl-type-text2-size)]">
        <svg lucideNotebookText class="size-3.5"></svg>{{ tr('citation.button') }}
        <span class="text-wl-on-surface-variant">{{ citations().length }}</span>
      </button>
      <sanring-popover-content side="right" class="w-[400px] p-0 rounded-[var(--wl-radius-lg)] shadow-[var(--wl-shadow-panel)] bg-wl-surface border-wl-outline-variant">
        <section data-testid="citation-popover" class="flex max-h-[70vh] flex-col">
          <header class="flex items-center justify-between border-b border-wl-outline-variant px-4 py-3">
            <h2 class="wl-title2">{{ tr('citation.title') }} <span class="wl-text2 text-wl-on-surface-variant">({{ citations().length }})</span></h2>
            <button type="button" class="wl-icon-btn" [attr.aria-label]="tr('card.close')" (click)="open.set(false)"><svg lucideX class="size-4"></svg></button>
          </header>
          <div class="overflow-y-auto px-4 py-3">
            @if (citations().length === 0) {
              <div data-testid="citation-missing-warning" role="alert" class="wl-alert-error">{{ tr('citation.missing') }}</div>
            }
            <ol class="flex flex-col gap-3">
              @for (c of sorted(); track c.sourceId + c.locator; let i = $index) {
                <li data-testid="citation-item" class="rounded-wl-md border border-wl-outline-variant bg-wl-surface-container-lowest p-3">
                  <div class="flex items-start justify-between gap-2">
                    <h3 class="wl-sub-title">{{ c.sourceTitle }}</h3>
                    <span class="wl-badge shrink-0" [class.wl-badge-primary]="c.role === 'primary'">{{ roleLabel(c.role) }}</span>
                  </div>
                  <dl class="mt-2 grid grid-cols-[88px_1fr] gap-x-2 gap-y-1 wl-text2">
                    <dt class="text-wl-on-surface-variant">{{ tr('citation.publisher') }}</dt><dd>{{ c.publisher }}</dd>
                    @if (detail(c.sourceId); as s) {
                      @if (s.authors) { <dt class="text-wl-on-surface-variant">{{ tr('citation.authors') }}</dt><dd>{{ s.authors }}</dd> }
                      @if (s.publishedText) { <dt class="text-wl-on-surface-variant">{{ tr('citation.published') }}</dt><dd>{{ s.publishedText }}</dd> }
                    }
                    <dt class="text-wl-on-surface-variant">{{ tr('citation.locator') }}</dt>
                    <dd data-testid="citation-locator" class="wl-archival">{{ c.locator }}</dd>
                    <dt class="text-wl-on-surface-variant">{{ tr('citation.note') }}</dt><dd>{{ c.evidenceNote }}</dd>
                    <dt class="text-wl-on-surface-variant">{{ tr('citation.license') }}</dt>
                    <dd data-testid="citation-license">
                      {{ license(c.licenseCode) ?? tr('citation.licenseNone') }}
                      @if (detail(c.sourceId)?.licenseEvidenceUrl; as u) {
                        · <a class="wl-link" [href]="u" target="_blank" rel="noopener noreferrer">{{ tr('citation.licenseEvidence') }}</a>
                      }
                    </dd>
                    @if (detail(c.sourceId)?.catalogId; as cat) {
                      <dt class="text-wl-on-surface-variant">{{ tr('citation.catalog') }}</dt><dd class="wl-archival">{{ cat }}</dd>
                    }
                  </dl>
                  @if (detail(c.sourceId); as s) {
                    @if (s.url || s.archiveUrl) {
                      <div class="mt-2 flex gap-3 wl-text2">
                        @if (s.url) { <a class="wl-link inline-flex items-center gap-1" [href]="s.url" target="_blank" rel="noopener noreferrer">{{ tr('citation.url') }}<svg lucideExternalLink class="size-3"></svg></a> }
                        @if (s.archiveUrl) { <a class="wl-link inline-flex items-center gap-1" [href]="s.archiveUrl" target="_blank" rel="noopener noreferrer">{{ tr('citation.archive') }}<svg lucideExternalLink class="size-3"></svg></a> }
                      </div>
                    }
                  } @else if (status()[c.sourceId] === 'loading') {
                    <sanring-spinner size="sm" class="mt-2 text-wl-on-surface-variant" [ariaLabel]="tr('citation.title')" />
                  } @else if (status()[c.sourceId] === 'error') {
                    <p class="mt-2 wl-text2 text-wl-error">{{ tr('citation.detailError') }}
                      <button type="button" class="wl-link" (click)="fetch(c.sourceId, true)">{{ tr('map.retry') }}</button></p>
                  }
                </li>
              }
            </ol>
          </div>
        </section>
      </sanring-popover-content>
    </sanring-popover>
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
