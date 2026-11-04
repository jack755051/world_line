import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { formatCampaignDate, inclusiveEnd, type Campaign, type CampaignPhase, type CampaignStatus } from '../../core/campaign';
import { ALLIED_COLOR, AXIS_COLOR, CONTESTED_COLOR, SOVIET_COLOR } from '../map/campaign-layers';

/**
 * 戰役說明卡（§11.2）：標題、日期、交戰方色票、階段 P1…Pn、播放／暫停／上一步／下一步、階段摘要、兵力／結果、出處。
 * 沒有出處的欄位標「待考證」。桌面 360px 浮在地圖左側；手機放在下方 40vh。
 */
@Component({
  selector: 'wl-campaign-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'flex min-h-0 flex-col' },
  template: `
    <section data-testid="campaign-card" class="wl-paper flex min-h-0 flex-1 flex-col overflow-hidden shadow-[var(--wl-shadow-panel)]" role="dialog" aria-modal="false"
      [attr.aria-label]="campaign()?.name_zh ?? '戰役簡報'" [attr.data-status]="status()" [attr.data-phase]="phase()">
      <header class="flex flex-none items-start gap-2 border-b border-wl-outline-variant px-4 py-3">
        <div class="min-w-0 flex-1">
          <div class="wl-text2 text-wl-on-surface-variant">⚔ 戰役簡報</div>
          <h2 data-testid="campaign-title" class="wl-title2 leading-tight">{{ campaign()?.name_zh ?? '載入中…' }}</h2>
          @if (campaign(); as c) {
            <div data-testid="campaign-dates" class="wl-text2 text-wl-on-surface-variant">{{ c.start }} – {{ c.end_inclusive }}
              @if (c.end_verified === false) { <span class="text-wl-error">（結束日待考證）</span> }</div>
          }
        </div>
        <button type="button" data-testid="campaign-close" class="flex size-8 flex-none items-center justify-center rounded hover:bg-wl-surface-container" aria-label="關閉戰役模式（Esc）" title="關閉（Esc）" (click)="closed.emit()">✕</button>
      </header>
      @if (status() === 'loading') {
        <p data-testid="campaign-loading" class="px-4 py-6 wl-text2 text-wl-on-surface-variant">載入戰役資料…</p>
      } @else if (status() === 'error') {
        <p data-testid="campaign-error" class="px-4 py-6 wl-text2 text-wl-error" role="alert">戰役資料載入失敗，地圖上不顯示戰役圖層。</p>
      } @else if (campaign(); as c) {
        <div class="flex flex-none flex-wrap gap-x-3 gap-y-1 px-4 pt-3 wl-text2">
          @for (b of sides(); track b.key) {
            <span class="inline-flex items-center gap-1"><i class="inline-block size-3 rounded-sm" [style.background]="b.color"></i>{{ b.names }}</span>
          }
        </div>
        <div class="flex flex-none items-center gap-1 px-4 pt-3" role="tablist" aria-label="階段">
          @for (p of c.phases; track p.seq) {
            <button type="button" role="tab" [attr.data-testid]="'campaign-phase-' + p.seq" [attr.aria-selected]="p.seq === phase()"
              class="h-7 min-w-9 rounded-full border px-2 wl-text2 font-semibold"
              [class.bg-wl-primary]="p.seq === phase()" [class.text-wl-on-primary]="p.seq === phase()" [class.border-wl-primary]="p.seq === phase()"
              [class.border-wl-outline-variant]="p.seq !== phase()" [title]="p.name_zh" (click)="go.emit(p.seq)">P{{ p.seq }}</button>
          }
        </div>
        <div class="flex flex-none items-center gap-2 px-4 pt-2">
          <button type="button" data-testid="campaign-prev" class="wl-btn-secondary h-8 px-3 wl-text2" [disabled]="phase() <= 1" (click)="prev.emit()" aria-label="上一階段">◀</button>
          <button type="button" data-testid="campaign-play" class="wl-btn-primary h-8 min-w-20 px-3 wl-text2" (click)="play.emit()" [attr.aria-pressed]="status() === 'playing'">
            {{ status() === 'playing' ? '❚❚ 暫停' : status() === 'ended' ? '↻ 重播' : '▶ 播放' }}</button>
          <button type="button" data-testid="campaign-next" class="wl-btn-secondary h-8 px-3 wl-text2" [disabled]="phase() >= c.phases.length" (click)="next.emit()" aria-label="下一階段">▶</button>
          <span class="ml-auto wl-text2 text-wl-on-surface-variant">{{ phase() }} / {{ c.phases.length }}</span>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto px-4 pb-4 pt-3">
          @if (current(); as p) {
            <h3 data-testid="campaign-phase-title" class="wl-sub-title">P{{ p.seq }}・{{ p.name_zh }}</h3>
            <div data-testid="campaign-phase-dates" class="wl-text2 text-wl-on-surface-variant">{{ phaseDates(p) }}
              @if (p.dates_verified === false) { <span class="text-wl-error">（日期待考證）</span> }</div>
            <p data-testid="campaign-summary" class="mt-2 wl-text1 leading-relaxed">{{ p.summary_zh }}
              @if (!p.summary_verified) { <span data-testid="campaign-unverified" class="ml-1 rounded bg-wl-surface-container px-1 wl-text2 text-wl-error">待考證</span> }</p>
            @if (p.fronts_note) { <p data-testid="campaign-fronts-note" class="mt-2 wl-text2"><span class="text-wl-error">戰線待考證：</span>{{ p.fronts_note }}</p> }
            @for (n of notesOf(p); track n) { <p class="mt-2 wl-text2 text-wl-on-surface-variant">{{ n }}</p> }
          }
          <h4 class="mt-4 wl-sub-title">兵力／結果</h4>
          <p data-testid="campaign-totals" class="wl-text2">
            @if (totalsText(); as t) { {{ t }}
              @if (!c.totals?.verified || !c.totals?.sources?.length) { <span class="ml-1 text-wl-error">待考證</span> }
            } @else { <span class="text-wl-error">待考證</span> }
          </p>
          <h4 class="mt-4 wl-sub-title">出處</h4>
          <ol data-testid="campaign-sources" class="mt-1 list-decimal space-y-1 pl-5 wl-text2">
            @for (s of sources(); track s.citation) {
              <li>@if (s.url) { <a class="underline" [href]="s.url" target="_blank" rel="noopener">{{ s.citation }}</a> } @else { {{ s.citation }} }</li>
            } @empty { <li class="list-none text-wl-error">待考證</li> }
          </ol>
          <p class="mt-3 wl-text2 text-wl-on-surface-variant">虛線與空心點＝待考證；箭頭為示意，非精確路線。</p>
        </div>
      }
    </section>
  `,
})
export class CampaignCard {
  readonly campaign = input<Campaign | null>(null);
  readonly status = input<CampaignStatus>('idle');
  readonly phase = input(1);
  readonly closed = output<void>();
  readonly play = output<void>();
  readonly prev = output<void>();
  readonly next = output<void>();
  readonly go = output<number>();
  protected readonly current = computed(() => this.campaign()?.phases.find((p) => p.seq === this.phase()) ?? null);
  protected readonly sources = computed(() => {
    const p = this.current();
    const seen = new Set<string>();
    return (p?.sources ?? []).filter((s) => !seen.has(s.citation) && !!seen.add(s.citation));
  });
  protected readonly totalsText = computed(() => {
    const t = this.campaign()?.totals;
    if (!t) return '';
    const n = t['evacuated_dynamo'];
    return typeof n === 'number' ? `發電機行動撤出 ${n.toLocaleString('en-US')} 人` : '';
  });
  protected readonly sides = computed(() => {
    const bel = this.campaign()?.belligerents ?? {};
    const color = (k: string) => (/^(axis|japan)/.test(k) ? AXIS_COLOR : /^soviet/.test(k) ? SOVIET_COLOR : /^(allied|china|pol)/.test(k) ? ALLIED_COLOR : CONTESTED_COLOR);
    return Object.entries(bel).map(([key, names]) => ({ key, color: color(key), names: (names ?? []).join('、') }));
  });
  protected phaseDates(p: CampaignPhase): string {
    const s = formatCampaignDate(p.start, p.start_precision);
    const endIso = p.end_precision ? p.end : inclusiveEnd(p.end);
    return `${s} – ${formatCampaignDate(endIso, p.end_precision)}`;
  }
  protected notesOf(p: CampaignPhase): string[] {
    const n = p.notes;
    return [...(Array.isArray(n) ? n : n ? [n] : []), ...(p.note ? [p.note] : [])];
  }
}
