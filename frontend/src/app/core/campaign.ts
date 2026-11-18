import { WorldLineApi } from './api/world-line-api';
import { Injectable, InjectionToken, computed, inject, isDevMode, signal } from '@angular/core';

/**
 * 戰役功能開關（Tai 2026-11-04 18:48：戰役不上第一版）：production build 關閉——不載入戰役 JSON、
 * 所有入口（政權面板「戰役簡報」、衝突小卡「戰役簡報」、日後事件卡 ⚔）都不出現；開發環境開啟。
 * 測試可用 `{ provide: CAMPAIGNS_ENABLED, useValue: false }` 覆寫。
 */
export const CAMPAIGNS_ENABLED = new InjectionToken<boolean>('CAMPAIGNS_ENABLED', { providedIn: 'root', factory: () => isDevMode() });

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

/**
 * 戰役名稱拆成「名稱」與「行動代號」。資料裡代號寫在全形括號內（例：「敦克爾克撤退（發電機行動）」）；
 * 括號內以「行動」「作戰」「計畫」結尾才當作代號，其他括號（例：「閃擊波蘭（波蘭戰役）」是別稱）不拆。
 */
export function splitCampaignName(name: string): { name: string; codename: string | null } {
  const m = /^(.+?)（([^（）]+(?:行動|作戰|計畫))）$/.exec(name.trim());
  return m ? { name: m[1].trim(), codename: m[2].trim() } : { name: name.trim(), codename: null };
}

export type CampaignOrigin = 'api' | 'static';
export type CampaignStatus = 'idle' | 'loading' | 'ready' | 'playing' | 'paused' | 'ended' | 'error';
export const PHASE_MS = 3000;

/**
 * 播放時鐘：每 stepMs 呼叫一次 onTick。預設用 setInterval；戰役頁改用 GSAP timeline（MotionService.phaseClock，§19.2.4）。
 * pause／resume 保留本階段已走的時間（GSAP 版），stop 歸零。
 */
export interface PhaseClock { start(): void; pause(): void; resume(): void; stop(): void }
export type PhaseClockFactory = (stepMs: number, onTick: () => void) => PhaseClock;
export const intervalClock: PhaseClockFactory = (stepMs, onTick) => {
  let timer: ReturnType<typeof setInterval> | null = null;
  const stop = () => { if (timer) { clearInterval(timer); timer = null; } };
  const start = () => { stop(); timer = setInterval(onTick, stepMs); };
  return { start, pause: stop, resume: start, stop };
};

/**
 * 純狀態機：不自動播放；play 每 PHASE_MS 前進一階段，到最後一階段停在 ended。
 * 狀態（status／phase）以這裡為準；時鐘（setInterval 或 GSAP timeline）只負責「時間到了 → step」。
 */
export class CampaignPlayer {
  status: CampaignStatus = 'ready';
  phase = 1;
  private readonly clock: PhaseClock;
  /** 暫停後沒有跳轉 → 再播放時接續本階段剩餘時間。 */
  private resumable = false;
  constructor(readonly count: number, private readonly onChange: () => void, readonly stepMs = PHASE_MS, clock: PhaseClockFactory = intervalClock) {
    this.clock = clock(stepMs, () => this.step());
  }
  go(n: number): void {
    this.resumable = false;
    this.phase = Math.max(1, Math.min(this.count, n));
    if (this.status !== 'playing') this.status = this.phase === this.count && this.count > 1 ? 'ended' : this.phase === 1 && this.status === 'ready' ? 'ready' : 'paused';
    this.onChange();
  }
  next(): void { this.stopClock(); if (this.status === 'playing') this.status = 'paused'; this.step(); }
  prev(): void { this.stopClock(); if (this.status === 'playing' || this.status === 'ended') this.status = 'paused'; this.go(this.phase - 1); }
  play(): void {
    if (this.count <= 1) return;
    const resume = this.resumable && this.status === 'paused' && this.phase < this.count;
    if (this.phase >= this.count) this.phase = 1;
    this.status = 'playing';
    if (resume) this.clock.resume(); else { this.clock.stop(); this.clock.start(); }
    this.resumable = false;
    this.onChange();
  }
  pause(): void { if (this.status !== 'playing') return; this.clock.pause(); this.resumable = true; this.status = 'paused'; this.onChange(); }
  toggle(): void { this.status === 'playing' ? this.pause() : this.play(); }
  dispose(): void { this.stopClock(); }
  private step(): void {
    this.resumable = false;
    if (this.phase >= this.count) { this.stopClock(); this.status = 'ended'; this.onChange(); return; }
    this.phase++;
    if (this.phase >= this.count) { this.stopClock(); this.status = 'ended'; }
    else if (this.status === 'ready') this.status = 'paused';
    this.onChange();
  }
  private stopClock(): void { this.resumable = false; this.clock.stop(); }
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

/** 戰役資料來源（§19.5 C1）：先讀唯讀 API；API 讀不到時退回靜態 JSON，畫面上明確標示。 */
export type CampaignSourceKind = 'api' | 'static';
export const CAMPAIGN_API_BASE = '/api/v1/campaigns/';

/** 讀一場戰役：API（`{ data: Campaign }` 信封）→ 失敗時靜態 `campaigns/<slug>.json`；兩者都失敗就丟錯。 */
export async function fetchCampaign(slug: string, staticBase = 'campaigns/', f: typeof fetch = fetch): Promise<{ campaign: Campaign; source: CampaignSourceKind }> {
  const key = encodeURIComponent(slug);
  try {
    const r = await f(CAMPAIGN_API_BASE + key, { headers: { accept: 'application/json' } });
    if (r.ok) {
      const j = await r.json();
      const c = (j && typeof j === 'object' && 'data' in j ? j.data : j) as Campaign | null;
      if (c && Array.isArray(c.phases) && c.layers) return { campaign: c, source: 'api' };
    }
  } catch { /* 退回靜態 JSON */ }
  const r = await f(staticBase + key + '.json');
  if (!r.ok) throw new Error(String(r.status));
  return { campaign: (await r.json()) as Campaign, source: 'static' };
}

@Injectable({ providedIn: 'root' })
export class CampaignService {
  readonly enabled = inject(CAMPAIGNS_ENABLED);
  readonly index = signal<CampaignIndexEntry[]>([]);
  readonly campaign = signal<Campaign | null>(null);
  readonly status = signal<CampaignStatus>('idle');
  readonly phase = signal(1);
  readonly current = computed(() => this.campaign()?.phases.find((p) => p.seq === this.phase()) ?? null);
  private readonly _origin = signal<CampaignOrigin | null>(null);
  /** 這次戰役資料來源：'api'（後端 /campaigns/{key}）、'static'（campaigns/{key}.json fallback）、null（未載入）。 */
  readonly origin = this._origin.asReadonly();
  /** 同 origin（戰役獨立頁沿用的名稱）。 */
  readonly source = this.origin;
  private player: CampaignPlayer | null = null;
  private seq = 0;
  private loaded = false;
  private base = 'campaigns/';

  async loadIndex(): Promise<void> {
    if (!this.enabled || this.loaded) return;
    this.loaded = true;
    try {
      const r = await fetch(this.base + 'index.json');
      if (!r.ok) throw new Error(String(r.status));
      const j = await r.json();
      this.index.set(Array.isArray(j) ? j : (j.campaigns ?? []));
    } catch { this.index.set([]); }
  }

  async open(key: string): Promise<void> {
    if (!this.enabled) return;
    this.close();
    const seq = ++this.seq;
    this.status.set('loading');
    let c: Campaign | null = null;
    let origin: CampaignOrigin = 'api';
    try {
      c = await this.fetchApi(key);
    } catch {
      // API 失敗（網路錯誤、非 2xx、data 為 null、phases 為空）才 fallback 靜態檔
      origin = 'static';
      try {
        const r = await fetch(this.base + encodeURIComponent(key) + '.json');
        if (!r.ok) throw new Error(String(r.status));
        c = (await r.json()) as Campaign;
      } catch { c = null; }
    }
    if (seq !== this.seq || this.status() !== 'loading') return;
    if (!c || !Array.isArray(c.phases)) { this.status.set('error'); return; }
    this.campaign.set(c);
    this._origin.set(origin);
    this.player = new CampaignPlayer(c.phases.length, () => this.sync());
    this.sync();
  }
  private async fetchApi(key: string): Promise<Campaign> {
    const r = await fetch(`${WorldLineApi.base}/campaigns/${encodeURIComponent(key)}`);
    if (!r.ok) throw new Error(String(r.status));
    const c = ((await r.json()) as { data?: Campaign | null } | null)?.data;
    if (!c || !Array.isArray(c.phases) || !c.phases.length) throw new Error('empty');
    return c;
  }
  close(): void {
    this.player?.dispose();
    this.player = null;
    this.campaign.set(null);
    this._origin.set(null);
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
