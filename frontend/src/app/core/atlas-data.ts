import { Injectable, computed, inject, signal } from '@angular/core';
import type { ConflictMapDto, ControlMapDto, RegimeDto, SovereigntyMapDto, TimelineSnapshotDto, RegimeEventDto } from './api/api-types';
import { LruCache, addDaysIso, intervalKey, neighborDates } from './change-points';
import { WorldLineApi } from './api/world-line-api';
import { AtlasState } from './atlas-state';
import { isAbort } from './delayed-flag';

export type LoadStatus = 'idle' | 'loading' | 'ok' | 'error';

/**
 * 主地圖資料（只讀 API，不產生任何示意資料）。
 * - 控制區：保留上一次成功的結果，失敗時不清空（PRD §8.2 error：保留上一次成功的圖層並標示日期）。
 * - 依日期快取，拖動時間軸不重複請求。
 * - 控制區也依變動區間快取（change-points 的 controlPoints；移植自 992baba）：同區間換日期重用同一份資料、不顯示載入中，
 *   套用後預先載入前後相鄰區間；變動點還沒載到時退回逐日快取。
 */
@Injectable({ providedIn: 'root' })
export class AtlasData {
  private readonly api = inject(WorldLineApi);
  private readonly state = inject(AtlasState);

  readonly health = signal<'checking' | 'up' | 'down'>('checking');
  readonly healthStatus = signal<string | null>(null);

  readonly control = signal<ControlMapDto | null>(null);
  readonly controlDate = signal<string | null>(null);
  readonly controlStatus = signal<LoadStatus>('idle');
  readonly requestedDate = signal<string | null>(null);

  /** 主權圖層（國界）：與控制區分開載入；失敗時保留上一次成功的結果。 */
  readonly sovereignty = signal<SovereigntyMapDto | null>(null);
  readonly sovereigntyStatus = signal<LoadStatus>('idle');
  /** 目前顯示的主權資料適用的日期（同一變動區間換日期時不換資料物件，只更新這個）。 */
  readonly sovereigntyShownFor = signal<string | null>(null);
  private sovSeq = 0;

  /** 衝突圖示資料：失敗時保留上一次成功的結果（圖示只在點選政權後才顯示）。 */
  readonly conflicts = signal<ConflictMapDto | null>(null);
  readonly conflictsStatus = signal<LoadStatus>('idle');
  /** 政權相關事件（政權面板時間線），依政權 id 快取；不隨日期變。 */
  readonly regimeEvents = signal<Record<string, RegimeEventDto[]>>({});
  readonly regimeEventsStatus = signal<Record<string, LoadStatus>>({});
  private cfSeq = 0;

  /**
   * 主權／衝突圖層的變動點（GET /timeline/change-points）。兩個相鄰變動點之間每天的結果相同，
   * 所以快取依「區間」而不是日期：播放一週一格、在同一區間裡跳日期都不必重新請求，也不重建地圖圖層。
   * 還沒載入（或失敗）時退回依日期快取。
   */
  readonly changePoints = signal<string[] | null>(null);
  /** 控制區的變動點（/control 的日期條件：控制紀錄、涵蓋備註、陣營、快照、事件日）。 */
  readonly controlPoints = signal<string[] | null>(null);
  private readonly sovCache = new LruCache<SovereigntyMapDto>(40);
  private readonly cfCache = new LruCache<ConflictMapDto>(40);
  private sovKey: string | null = null;
  private cfKey: string | null = null;
  /** 進行中的請求（前景或預先載入），同一區間只發一次。 */
  private readonly pending = new Map<string, Promise<unknown>>();
  private key(date: string): string {
    return intervalKey(this.changePoints(), date);
  }
  private controlKey(date: string): string {
    return intervalKey(this.controlPoints(), date);
  }
  /**
   * 主權資料快取 key：變動區間 + 縮放容差桶（c/m/f）。
   * zoom ≤ 4.5 → coarse 0.010°；≤ 6.5 → medium 0.004°；else fine 0.002°（原始）。
   * 同一區間在不同縮放等級下會得到不同幾何精細度，需分開快取。
   */
  private sovIntervalKey(date: string): string {
    const interval = intervalKey(this.changePoints(), date);
    const zoom = this.state.mapZoom();
    const bucket = zoom <= 4.5 ? 'c' : zoom <= 6.5 ? 'm' : 'f';
    return `${interval}:${bucket}`;
  }

  /** 每個圖層只保留最新一筆進行中的請求：新日期開始載入時中止舊的（快速連續跳日期不讓舊資料蓋新資料）。 */
  private readonly inflight: Record<'control' | 'sov' | 'cf', AbortController | null> = { control: null, sov: null, cf: null };
  private restart(k: 'control' | 'sov' | 'cf'): void {
    this.inflight[k]?.abort();
    this.inflight[k] = null;
  }
  private begin(k: 'control' | 'sov' | 'cf'): AbortSignal {
    const c = new AbortController();
    this.inflight[k] = c;
    return c.signal;
  }
  /** 國界／控制區資料是否正在向 API 取（地圖角落載入指示用）。 */
  readonly mapDataLoading = computed(() => this.controlStatus() === 'loading' || this.sovereigntyStatus() === 'loading');

  readonly snapshots = signal<TimelineSnapshotDto[]>([]);
  readonly snapshotsStatus = signal<LoadStatus>('idle');
  /** 最早事件日（GET /timeline/extent）；時間軸起點依此往前延伸（WW1 試驗，1908 起）。失敗時維持 null（用預設範圍）。 */
  readonly earliestEvent = signal<string | null>(null);

  readonly regimes = signal<Record<string, RegimeDto>>({});
  readonly regimesStatus = signal<LoadStatus>('idle');

  /** 目前顯示的控制資料是否就是要求的日期（失敗時可能是舊日期）。 */
  readonly showingStale = computed(() => {
    const shown = this.controlDate();
    return shown !== null && shown !== this.requestedDate();
  });

  private readonly cache = new LruCache<ControlMapDto>(60);
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
    this.restart('control');
    const key = this.controlKey(date);
    const hit = this.cache.get(key);
    if (hit) {
      this.apply(date, hit);
      this.prefetchControlAround(date);
      return;
    }
    this.controlStatus.set('loading');
    try {
      const dto = await this.fetchControl(key, date, this.begin('control'));
      if (my === this.seq) {
        this.apply(date, dto);
        this.prefetchControlAround(date);
      }
    } catch (e) {
      if (isAbort(e)) return;
      if (my === this.seq) this.controlStatus.set('error');
    }
  }

  async loadChangePoints(): Promise<void> {
    try {
      const cp = await this.api.timelineChangePoints();
      this.changePoints.set(cp.points.map(String));
      this.controlPoints.set(cp.controlPoints ? cp.controlPoints.map(String) : null);
    } catch {
      this.changePoints.set(null);
      this.controlPoints.set(null);
    }
  }

  /** 控制區某區間：快取 → 進行中的同區間請求（含預先載入）→ 新請求。 */
  private fetchControl(key: string, date: string, signal?: AbortSignal): Promise<ControlMapDto> {
    const hit = this.cache.get(key);
    if (hit) return Promise.resolve(hit);
    const pk = `control:${key}`;
    const inflight = this.pending.get(pk) as Promise<ControlMapDto> | undefined;
    if (inflight) return inflight;
    const p = this.api.control(date, signal);
    this.pending.set(pk, p);
    signal?.addEventListener('abort', () => {
      if (this.pending.get(pk) === p) this.pending.delete(pk);
    });
    p.then((dto) => this.cache.set(key, dto), () => undefined).finally(() => {
      if (this.pending.get(pk) === p) this.pending.delete(pk);
    });
    return p;
  }

  /** 預先載入控制區前後相鄰區間（只在有控制區變動點時；不改載入狀態，失敗安靜忽略）。 */
  prefetchControlAround(date: string): void {
    const pts = this.controlPoints();
    if (!pts) return;
    const { prev, next } = neighborDates(pts, date);
    for (const d of [next, prev]) {
      if (!d) continue;
      const key = this.controlKey(d);
      if (this.cache.has(key)) continue;
      this.fetchControl(key, d).catch(() => undefined);
    }
  }

  /** 取某區間的資料：快取 → 進行中的同區間請求 → 新請求（前景請求可被中止；預先載入不中止）。 */
  private fetchInterval<T>(kind: 'sov' | 'cf', key: string, date: string, cache: LruCache<T>, signal?: AbortSignal): Promise<T> {
    const hit = cache.get(key);
    if (hit) return Promise.resolve(hit);
    const pk = `${kind}:${key}`;
    const inflight = this.pending.get(pk) as Promise<T> | undefined;
    if (inflight) return inflight;
    const p = (kind === 'sov' ? this.api.sovereignty(date, signal) : this.api.conflicts(date, signal)) as Promise<T>;
    this.pending.set(pk, p);
    // 前景請求被中止時立刻移除，讓緊接著的新請求不會撿到已中止的那個
    signal?.addEventListener('abort', () => {
      if (this.pending.get(pk) === p) this.pending.delete(pk);
    });
    p.then(
      (dto) => cache.set(key, dto),
      () => undefined,
    ).finally(() => {
      if (this.pending.get(pk) === p) this.pending.delete(pk);
    });
    return p;
  }

  async loadSovereignty(date: string): Promise<void> {
    const my = ++this.sovSeq;
    const key = this.sovIntervalKey(date);
    this.restart('sov');
    // 同一變動區間（含縮放桶）：資料不變，不換物件（地圖不 setData、標籤不重算），只記下目前日期
    if (key === this.sovKey && this.sovereignty()) {
      this.sovereigntyShownFor.set(date);
      this.sovereigntyStatus.set('ok');
      return;
    }
    const hit = this.sovCache.get(key);
    if (hit) {
      this.applySovereignty(hit, key, date);
      return;
    }
    this.sovereigntyStatus.set('loading');
    try {
      const dto = await this.fetchSov(key, date, this.state.mapZoom(), this.begin('sov'));
      if (my === this.sovSeq) this.applySovereignty(dto, key, date);
    } catch (e) {
      if (isAbort(e)) return;
      if (my === this.sovSeq) this.sovereigntyStatus.set('error');
    }
  }

  /** 主權資料請求（含 zoom 傳給後端以選擇容差）：快取 → 進行中的同 key 請求 → 新請求。 */
  private fetchSov(key: string, date: string, zoom: number, signal?: AbortSignal): Promise<SovereigntyMapDto> {
    const hit = this.sovCache.get(key);
    if (hit) return Promise.resolve(hit);
    const pk = `sov:${key}`;
    const inflight = this.pending.get(pk) as Promise<SovereigntyMapDto> | undefined;
    if (inflight) return inflight;
    performance.mark('wl:sov:fetch-start');
    const p = this.api.sovereignty(date, zoom, signal);
    this.pending.set(pk, p);
    signal?.addEventListener('abort', () => {
      if (this.pending.get(pk) === p) this.pending.delete(pk);
    });
    p.then(
      (dto) => {
        performance.mark('wl:sov:fetch-end');
        this.sovCache.set(key, dto);
      },
      () => undefined,
    ).finally(() => {
      if (this.pending.get(pk) === p) this.pending.delete(pk);
    });
    return p;
  }

  async loadConflicts(date: string): Promise<void> {
    const my = ++this.cfSeq;
    const key = this.key(date);
    this.restart('cf');
    if (key === this.cfKey && this.conflicts()) {
      this.conflictsStatus.set('ok');
      return;
    }
    const hit = this.cfCache.get(key);
    if (hit) {
      this.applyConflicts(hit, key);
      return;
    }
    this.conflictsStatus.set('loading');
    try {
      const dto = await this.fetchInterval('cf', key, date, this.cfCache, this.begin('cf'));
      if (my === this.cfSeq) this.applyConflicts(dto, key);
    } catch (e) {
      if (isAbort(e)) return;
      if (my === this.cfSeq) this.conflictsStatus.set('error');
    }
  }

  private applyConflicts(dto: ConflictMapDto, key: string): void {
    this.cfKey = key;
    this.conflicts.set(dto);
    this.conflictsStatus.set('ok');
  }

  /** 預先載入接下來的日期（播放一週／一個月一格；也涵蓋接下來兩個變動點），依序送、不中止，失敗就算了。 */
  private prefetchRun = 0;
  async prefetch(date: string, maxIntervals = 4, offsets: number[] = [7, 14, 21, 31, 62]): Promise<void> {
    const run = ++this.prefetchRun;
    const zoom = this.state.mapZoom();
    const dates = offsets.map((n) => addDaysIso(date, n));
    const pts = this.changePoints();
    if (pts) dates.push(...pts.filter((p) => p > date).slice(0, 2));
    const seen = new Set<string>([this.sovIntervalKey(date)]);
    let fetched = 0;
    for (const d of dates.sort()) {
      if (fetched >= maxIntervals) return;
      if (run !== this.prefetchRun) return; // 使用者又換日期：改預先載入新的位置
      const sovKey = this.sovIntervalKey(d);
      const cfKey = this.key(d);
      if (seen.has(sovKey)) continue;
      seen.add(sovKey);
      const ck = this.controlKey(d);
      if (this.sovCache.has(sovKey) && this.cfCache.has(cfKey) && this.cache.has(ck)) continue;
      fetched++;
      try {
        await Promise.all([this.fetchSov(sovKey, d, zoom), this.fetchInterval('cf', cfKey, d, this.cfCache), this.fetchControl(ck, d)]);
      } catch {
        /* 預先載入失敗不影響畫面 */
      }
    }
  }

  async loadRegimeEvents(regimeId: string): Promise<void> {
    const st = this.regimeEventsStatus()[regimeId];
    if (st === 'ok' || st === 'loading') return;
    this.regimeEventsStatus.update((m) => ({ ...m, [regimeId]: 'loading' }));
    try {
      const list = await this.api.regimeEvents(regimeId);
      this.regimeEvents.update((m) => ({ ...m, [regimeId]: list }));
      this.regimeEventsStatus.update((m) => ({ ...m, [regimeId]: 'ok' }));
    } catch {
      this.regimeEventsStatus.update((m) => ({ ...m, [regimeId]: 'error' }));
    }
  }

  private applySovereignty(dto: SovereigntyMapDto, key: string, date: string): void {
    performance.mark('wl:sov:signal-set');
    this.sovKey = key;
    this.sovereignty.set(dto);
    this.sovereigntyShownFor.set(date);
    this.sovereigntyStatus.set('ok');
    void this.loadRegimes(dto.featureCollection.features.map((f) => f.properties.regimeId));
  }

  async loadExtent(): Promise<void> {
    try {
      this.earliestEvent.set((await this.api.timelineExtent()).earliestEvent ?? null);
    } catch {
      this.earliestEvent.set(null);
    }
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
      // 批次拉（最多 200，超過分批）；避免 N 個逐一請求導致前端換年份卡頓
      const BATCH = 200;
      const loaded: import('./api/api-types').RegimeDto[] = [];
      for (let i = 0; i < missing.length; i += BATCH) {
        const chunk = missing.slice(i, i + BATCH);
        loaded.push(...await this.api.regimesBatch(chunk));
      }
      this.regimes.update((m) => ({ ...m, ...Object.fromEntries(loaded.map((r) => [r.id, r])) }));
      this.regimesStatus.set('ok');
    } catch {
      this.regimesStatus.set('error');
    }
  }
}
