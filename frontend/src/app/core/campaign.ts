import { Injectable, computed, signal } from '@angular/core';

/**
 * 戰役模式（ARCHITECTURE.md §11.2）：靜態戰役 JSON（public/campaigns/<key>.json，schema wl-campaign-web/0.1）
 * 的型別、載入與階段播放狀態機。圖層按 source-layer 分成 fronts／arrows／sites 三個 FeatureCollection，
 * 每個 feature 帶 phase 與 verified，之後改由 PMTiles 供應時圖層與 filter 不變。
 */
export interface CampaignSource { type?: string; citation: string; url?: string | null; quote?: string | null }
export interface CampaignPhase {
  seq: number; key: string; name_zh: string; name_en?: string | null;
  start: string; end: string; summary_zh: string; summary_verified: boolean;
  sources: CampaignSource[]; notes?: string[] | string | null;
  /** 考證組可選欄位：日期精度（'early-month'＝上旬；缺＝精確到日）、日期是否查證、戰線未核實說明。 */
  start_precision?: string | null; end_precision?: string | null; dates_verified?: boolean; fronts_note?: string | null; note?: string | null;
}
export interface CampaignFeatureProps { id: string; phase: number; verified: boolean; [k: string]: unknown }
export interface CampaignFC { type: 'FeatureCollection'; features: { type: 'Feature'; properties: CampaignFeatureProps; geometry: { type: string; coordinates: unknown } }[] }
export interface Campaign {
  schema: string; key: string; name_zh: string; name_en?: string | null;
  start: string; end: string; end_inclusive: string; scale?: string;
  belligerents: Record<string, string[]>;
  end_verified?: boolean; note?: string | null;
  regime_slugs: string[]; event_ids: string[];
  totals?: { verified?: boolean; sources?: CampaignSource[]; [k: string]: unknown } | null;
  bounds: [[number, number], [number, number]];
  phases: CampaignPhase[];
  layers: { fronts: CampaignFC; arrows: CampaignFC; sites: CampaignFC };
  citations?: CampaignSource[];
}
export interface CampaignIndexEntry { key: string; name_zh: string; start: string; end: string; scale?: string; regime_slugs: string[]; event_ids: string[] }

export type CampaignStatus = 'idle' | 'loading' | 'ready' | 'playing' | 'paused' | 'ended' | 'error';
export const PHASE_MS = 3000;

/** 純狀態機：不自動播放；play 每 PHASE_MS 前進一階段，到最後一階段停在 ended。 */
export class CampaignPlayer {
  status: CampaignStatus = 'ready';
  phase = 1;
  private timer: ReturnType<typeof setInterval> | null = null;
  constructor(readonly count: number, private readonly onChange: () => void, readonly stepMs = PHASE_MS) {}
  go(n: number): void {
    this.phase = Math.max(1, Math.min(this.count, n));
    if (this.status !== 'playing') this.status = this.phase === this.count && this.count > 1 ? 'ended' : this.phase === 1 && this.status === 'ready' ? 'ready' : 'paused';
    this.onChange();
  }
  next(): void { this.pauseTimer(); if (this.status === 'playing') this.status = 'paused'; this.step(); }
  prev(): void { this.pauseTimer(); if (this.status === 'playing' || this.status === 'ended') this.status = 'paused'; this.go(this.phase - 1); }
  play(): void {
    if (this.count <= 1) return;
    if (this.phase >= this.count) this.phase = 1;
    this.status = 'playing';
    this.pauseTimer();
    this.timer = setInterval(() => this.step(), this.stepMs);
    this.onChange();
  }
  pause(): void { if (this.status !== 'playing') return; this.pauseTimer(); this.status = 'paused'; this.onChange(); }
  toggle(): void { this.status === 'playing' ? this.pause() : this.play(); }
  dispose(): void { this.pauseTimer(); }
  private step(): void {
    if (this.phase >= this.count) { this.pauseTimer(); this.status = 'ended'; this.onChange(); return; }
    this.phase++;
    if (this.phase >= this.count) { this.pauseTimer(); this.status = 'ended'; }
    else if (this.status === 'ready') this.status = 'paused';
    this.onChange();
  }
  private pauseTimer(): void { if (this.timer) { clearInterval(this.timer); this.timer = null; } }
}

/** 依日期精度顯示：early-month →「YYYY 年 M 月上旬」，mid-month 中旬，late-month 下旬，month 只到月；其他照原樣。 */
export function formatCampaignDate(iso: string | null | undefined, precision?: string | null): string {
  if (!iso) return '待考證';
  const [y, m] = iso.split('-').map(Number);
  const part: Record<string, string> = { 'early-month': '上旬', 'mid-month': '中旬', 'late-month': '下旬', month: '' };
  if (precision && precision in part) return `${y} 年 ${m} 月${part[precision]}`;
  return iso;
}
/** exclusive end → 含當日的最後一天。 */
export function inclusiveEnd(iso: string): string {
  const d = new Date(iso + 'T00:00:00Z');
  d.setUTCDate(d.getUTCDate() - 1);
  return d.toISOString().slice(0, 10);
}

/** 某日期落在哪個階段（start 含、end 不含）；超出範圍時夾到首尾。 */
export function phaseForDate(c: Pick<Campaign, 'phases'>, iso: string): number {
  const ps = c.phases;
  if (!ps.length) return 1;
  if (iso < ps[0].start) return ps[0].seq;
  for (const p of ps) if (iso >= p.start && iso < p.end) return p.seq;
  return ps[ps.length - 1].seq;
}

/** 交戰方 → 可用的政權 slug（給面板入口用）。 */
export function campaignsForRegime(index: CampaignIndexEntry[], slug: string | null | undefined): CampaignIndexEntry[] {
  if (!slug) return [];
  return index.filter((c) => c.regime_slugs.includes(slug));
}
export function campaignsForEvent(index: CampaignIndexEntry[], eventId: string | null | undefined): CampaignIndexEntry[] {
  if (!eventId) return [];
  return index.filter((c) => c.event_ids.includes(eventId));
}

/**
 * 衝突是否「符合戰役定義」（§13 K2）：有考證過的戰役資料、交戰雙方都在該戰役的交戰方裡、且期間重疊。
 * 否則只給「在時間線上看」。
 */
export function campaignsForConflict(index: CampaignIndexEntry[], slugA: string, slugB: string, start: string, end: string | null): CampaignIndexEntry[] {
  return index.filter((c) => c.regime_slugs.includes(slugA) && c.regime_slugs.includes(slugB) && c.start < (end ?? '9999-12-31') && start < c.end);
}

@Injectable({ providedIn: 'root' })
export class CampaignService {
  readonly index = signal<CampaignIndexEntry[]>([]);
  readonly campaign = signal<Campaign | null>(null);
  readonly status = signal<CampaignStatus>('idle');
  readonly phase = signal(1);
  readonly current = computed(() => this.campaign()?.phases.find((p) => p.seq === this.phase()) ?? null);
  private player: CampaignPlayer | null = null;
  private loaded = false;
  private base = 'campaigns/';

  async loadIndex(): Promise<void> {
    if (this.loaded) return;
    this.loaded = true;
    try {
      const r = await fetch(this.base + 'index.json');
      if (!r.ok) throw new Error(String(r.status));
      const j = await r.json();
      this.index.set(Array.isArray(j) ? j : (j.campaigns ?? []));
    } catch { this.index.set([]); }
  }

  async open(key: string): Promise<void> {
    this.close();
    this.status.set('loading');
    try {
      const r = await fetch(this.base + encodeURIComponent(key) + '.json');
      if (!r.ok) throw new Error(String(r.status));
      const c = (await r.json()) as Campaign;
      if (this.status() !== 'loading') return;
      this.campaign.set(c);
      this.player = new CampaignPlayer(c.phases.length, () => this.sync());
      this.sync();
    } catch {
      this.status.set('error');
    }
  }
  close(): void {
    this.player?.dispose();
    this.player = null;
    this.campaign.set(null);
    this.status.set('idle');
    this.phase.set(1);
  }
  play(): void { this.player?.toggle(); }
  next(): void { this.player?.next(); }
  prev(): void { this.player?.prev(); }
  go(n: number): void { this.player?.pause(); this.player?.go(n); }
  private sync(): void {
    if (!this.player) return;
    this.status.set(this.player.status);
    this.phase.set(this.player.phase);
  }
}
