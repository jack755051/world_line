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
  sources: CampaignSource[]; notes?: string | null;
}
export interface CampaignFeatureProps { id: string; phase: number; verified: boolean; [k: string]: unknown }
export interface CampaignFC { type: 'FeatureCollection'; features: { type: 'Feature'; properties: CampaignFeatureProps; geometry: { type: string; coordinates: unknown } }[] }
export interface Campaign {
  schema: string; key: string; name_zh: string; name_en?: string | null;
  start: string; end: string; end_inclusive: string; scale?: string;
  belligerents: { allied: string[]; axis: string[] };
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
