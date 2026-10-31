import { Injectable, computed, inject, signal } from '@angular/core';
import type { ConflictMapDto, ControlMapDto, RegimeDto, SovereigntyMapDto, TimelineSnapshotDto } from './api/api-types';
import { WorldLineApi } from './api/world-line-api';

export type LoadStatus = 'idle' | 'loading' | 'ok' | 'error';

/**
 * 主地圖資料（只讀 API，不產生任何示意資料）。
 * - 控制區：保留上一次成功的結果，失敗時不清空（PRD §8.2 error：保留上一次成功的圖層並標示日期）。
 * - 依日期快取，拖動時間軸不重複請求。
 */
@Injectable({ providedIn: 'root' })
export class AtlasData {
  private readonly api = inject(WorldLineApi);

  readonly health = signal<'checking' | 'up' | 'down'>('checking');
  readonly healthStatus = signal<string | null>(null);

  readonly control = signal<ControlMapDto | null>(null);
  readonly controlDate = signal<string | null>(null);
  readonly controlStatus = signal<LoadStatus>('idle');
  readonly requestedDate = signal<string | null>(null);

  /** 主權圖層（國界）：與控制區分開載入；失敗時保留上一次成功的結果。 */
  readonly sovereignty = signal<SovereigntyMapDto | null>(null);
  readonly sovereigntyStatus = signal<LoadStatus>('idle');
  private readonly sovCache = new Map<string, SovereigntyMapDto>();
  private sovSeq = 0;

  /** 衝突圖示資料：依日期快取；失敗時保留上一次成功的結果（圖示只在點選政權後才顯示）。 */
  readonly conflicts = signal<ConflictMapDto | null>(null);
  readonly conflictsStatus = signal<LoadStatus>('idle');
  private readonly cfCache = new Map<string, ConflictMapDto>();
  private cfSeq = 0;

  readonly snapshots = signal<TimelineSnapshotDto[]>([]);
  readonly snapshotsStatus = signal<LoadStatus>('idle');

  readonly regimes = signal<Record<string, RegimeDto>>({});
  readonly regimesStatus = signal<LoadStatus>('idle');

  /** 目前顯示的控制資料是否就是要求的日期（失敗時可能是舊日期）。 */
  readonly showingStale = computed(() => {
    const shown = this.controlDate();
    return shown !== null && shown !== this.requestedDate();
  });

  private readonly cache = new Map<string, ControlMapDto>();
  private seq = 0;

  async checkHealth(): Promise<boolean> {
    this.health.set('checking');
    try {
      const h = await this.api.health();
      this.healthStatus.set(h.status);
      this.health.set('up');
      return true;
    } catch {
      this.healthStatus.set(null);
      this.health.set('down');
      return false;
    }
  }

  async loadControl(date: string): Promise<void> {
    const my = ++this.seq;
    this.requestedDate.set(date);
    const hit = this.cache.get(date);
    if (hit) {
      this.apply(date, hit);
      return;
    }
    this.controlStatus.set('loading');
    try {
      const dto = await this.api.control(date);
      this.cache.set(date, dto);
      if (this.cache.size > 60) this.cache.delete(this.cache.keys().next().value as string);
      if (my === this.seq) this.apply(date, dto);
    } catch {
      if (my === this.seq) this.controlStatus.set('error');
    }
  }

  async loadSovereignty(date: string): Promise<void> {
    const my = ++this.sovSeq;
    const hit = this.sovCache.get(date);
    if (hit) {
      this.applySovereignty(hit);
      return;
    }
    this.sovereigntyStatus.set('loading');
    try {
      const dto = await this.api.sovereignty(date);
      this.sovCache.set(date, dto);
      if (this.sovCache.size > 30) this.sovCache.delete(this.sovCache.keys().next().value as string);
      if (my === this.sovSeq) this.applySovereignty(dto);
    } catch {
      if (my === this.sovSeq) this.sovereigntyStatus.set('error');
    }
  }

  async loadConflicts(date: string): Promise<void> {
    const my = ++this.cfSeq;
    const hit = this.cfCache.get(date);
    if (hit) {
      this.conflicts.set(hit);
      this.conflictsStatus.set('ok');
      return;
    }
    this.conflictsStatus.set('loading');
    try {
      const dto = await this.api.conflicts(date);
      this.cfCache.set(date, dto);
      if (this.cfCache.size > 30) this.cfCache.delete(this.cfCache.keys().next().value as string);
      if (my === this.cfSeq) {
        this.conflicts.set(dto);
        this.conflictsStatus.set('ok');
      }
    } catch {
      if (my === this.cfSeq) this.conflictsStatus.set('error');
    }
  }

  private applySovereignty(dto: SovereigntyMapDto): void {
    this.sovereignty.set(dto);
    this.sovereigntyStatus.set('ok');
    void this.loadRegimes(dto.featureCollection.features.map((f) => f.properties.regimeId));
  }

  async loadSnapshots(): Promise<void> {
    this.snapshotsStatus.set('loading');
    try {
      this.snapshots.set(await this.api.allSnapshots());
      this.snapshotsStatus.set('ok');
    } catch {
      this.snapshotsStatus.set('error');
    }
  }

  private apply(date: string, dto: ControlMapDto): void {
    this.control.set(dto);
    this.controlDate.set(date);
    this.controlStatus.set('ok');
    void this.loadRegimes(dto.featureCollection.features.map((f) => f.properties.controllerRegimeId));
  }

  async loadRegimes(ids: string[]): Promise<void> {
    const missing = [...new Set(ids)].filter((id) => !this.regimes()[id]);
    if (missing.length === 0) {
      if (this.regimesStatus() !== 'error') this.regimesStatus.set('ok');
      return;
    }
    this.regimesStatus.set('loading');
    try {
      const loaded = await Promise.all(missing.map((id) => this.api.regime(id)));
      this.regimes.update((m) => ({ ...m, ...Object.fromEntries(loaded.map((r) => [r.id, r])) }));
      this.regimesStatus.set('ok');
    } catch {
      this.regimesStatus.set('error');
    }
  }
}
