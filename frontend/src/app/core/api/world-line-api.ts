import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import type {
  ApiEnvelope,
  ConflictMapDto,
  ControlMapDto,
  PaginatedSnapshots,
  RegimeDto,
  SourceDto,
  SovereigntyMapDto,
  TimelineSnapshotDto,
  TimelineExtentDto,
  TimelineChangePointsDto,
  RegimeEventDto,
} from './api-types';

export interface CapitalCityName {
  en?: string;
  'zh-Hant'?: string;
}

export interface CapitalRecord {
  recordId: string;
  regimeId: string;
  regimeSlug: string;
  cityName: CapitalCityName;
  location: { type: 'Point'; coordinates: [number, number] };
  validPeriod: { start: string; end: string | null };
  sourceRef: string;
}

export interface CapitalsDto {
  date: string;
  features: CapitalRecord[];
}

/** 生平摘要（GET /leaders 回應內嵌，不含 fieldSources）。 */
export interface LeaderBioSummary {
  id: string;
  name: string;
  nameZh: string | null;
  birthDate: string | null;
  birthDatePrecision: 'day' | 'month' | 'year' | null;
  deathDate: string | null;
  summary: Record<string, string> | null;
}

export interface LeaderRecord {
  recordId: string;
  regimeId: string;
  regimeSlug: string;
  name: string;
  nameZh: string | null;
  role: 'head_of_state' | 'head_of_government';
  title: string;
  validPeriod: { start: string; end: string | null };
  source: string;
  sourceUrl: string | null;
  verified: boolean;
  personId: string | null;
  bio: LeaderBioSummary | null;
}

export interface LeadersDto {
  date: string;
  features: LeaderRecord[];
}

/** 健康檢查回應（`/healthz`，不在 OpenAPI 內）。 */
export interface HealthReport {
  status: string;
  checks: Record<string, string>;
}

/**
 * World Line API client（PRD §7.1 唯讀查詢）。
 * 一律走相對路徑 `/api/v1`：開發時由 `proxy.conf.json` 轉到本機 API（127.0.0.1:5051，Tai 2026-10-30 拍板），
 * 不在前端寫死主機或金鑰。只有讀取，沒有任何寫入端點。
 */
@Injectable({ providedIn: 'root' })
export class WorldLineApi {
  private readonly http = inject(HttpClient);
  static readonly base = '/api/v1';

  /** GET /control?date=：該日控制區＋各戰區史料／推估狀態。 */
  async control(date: string, signal?: AbortSignal): Promise<ControlMapDto> {
    return this.getByDate<ControlMapDto>('/control', date, signal);
  }

  /** GET /sovereignty?date=&zoom=：該日主權圖層（國界，依政權上色；陣營只作補充）。
   *  zoom 供後端依縮放層級選擇幾何簡化容差（低縮放容差較大、資料量較小）。 */
  async sovereignty(date: string, zoom?: number, signal?: AbortSignal): Promise<SovereigntyMapDto> {
    return this.getByDate<SovereigntyMapDto>('/sovereignty', date, signal, zoom !== undefined ? { zoom: zoom.toFixed(1) } : undefined);
  }

  /** GET /conflicts?date=：該日進行中的衝突（雙方政權、起訖事件與出處、圖示位置）。 */
  async conflicts(date: string, signal?: AbortSignal): Promise<ConflictMapDto> {
    return this.getByDate<ConflictMapDto>('/conflicts', date, signal);
  }

  /**
   * 依日期查詢；signal 中止時取消 HTTP 請求（unsubscribe → XHR abort）並以 AbortError 拒絕，
   * 讓快速連續跳日期時過時的請求不佔頻寬、也不會晚到蓋掉新資料。
   */
  private getByDate<T>(path: string, date: string, signal?: AbortSignal, extra?: Record<string, string>): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      const aborted = () => reject(new DOMException('Aborted', 'AbortError'));
      if (signal?.aborted) return aborted();
      let params = new HttpParams().set('date', date);
      if (extra) for (const [k, v] of Object.entries(extra)) params = params.set(k, v);
      const sub = this.http.get<ApiEnvelope<T>>(`${WorldLineApi.base}${path}`, { params }).subscribe({
        next: (res) => resolve(res.data),
        error: (e: unknown) => reject(e),
      });
      signal?.addEventListener('abort', () => {
        sub.unsubscribe();
        aborted();
      }, { once: true });
    });
  }

  /** GET /timeline/extent：未撤回事件的最早／最晚日期（時間軸起點往前延伸用）。 */
  /** GET /timeline/change-points：主權／衝突圖層的變動點（相鄰兩點之間每天結果相同）。 */
  async timelineChangePoints(): Promise<TimelineChangePointsDto> {
    const res = await firstValueFrom(this.http.get<ApiEnvelope<TimelineChangePointsDto>>(`${WorldLineApi.base}/timeline/change-points`));
    return res.data;
  }

  async timelineExtent(): Promise<TimelineExtentDto> {
    const res = await firstValueFrom(this.http.get<ApiEnvelope<TimelineExtentDto>>(`${WorldLineApi.base}/timeline/extent`));
    return res.data;
  }

  /** GET /timeline/snapshots：全部快照（逐頁取完，pageSize 上限 500）。 */
  async allSnapshots(): Promise<TimelineSnapshotDto[]> {
    const items: TimelineSnapshotDto[] = [];
    for (let page = 1; page < 100; page++) {
      const res = await firstValueFrom(
        this.http.get<ApiEnvelope<PaginatedSnapshots>>(`${WorldLineApi.base}/timeline/snapshots`, {
          params: new HttpParams().set('page', page).set('pageSize', 500),
        }),
      );
      items.push(...res.data.items);
      if (items.length >= Number(res.data.total) || res.data.items.length === 0) break;
    }
    return items;
  }

  /** GET /regimes/{id}/events：政權相關事件（參與方事件＋國界／衝突紀錄的起訖事件），依日期排序。 */
  async regimeEvents(id: string): Promise<RegimeEventDto[]> {
    const res = await firstValueFrom(this.http.get<ApiEnvelope<RegimeEventDto[]>>(`${WorldLineApi.base}/regimes/${id}/events`));
    return res.data;
  }

  async regime(id: string): Promise<RegimeDto> {
    const res = await firstValueFrom(this.http.get<ApiEnvelope<RegimeDto>>(`${WorldLineApi.base}/regimes/${id}`));
    return res.data;
  }

  /** GET /regimes?ids=…：批次取政權（最多 200）。避免 N 個逐一請求。 */
  async regimesBatch(ids: string[]): Promise<RegimeDto[]> {
    let params = new HttpParams();
    for (const id of ids) params = params.append('ids', id);
    const res = await firstValueFrom(this.http.get<ApiEnvelope<RegimeDto[]>>(`${WorldLineApi.base}/regimes`, { params }));
    return res.data;
  }

  async source(id: string): Promise<SourceDto> {
    const res = await firstValueFrom(this.http.get<ApiEnvelope<SourceDto>>(`${WorldLineApi.base}/sources/${id}`));
    return res.data;
  }

  /** GET /capitals?date=：該日首都記錄（城市名稱、位置）。 */
  async capitals(date: string, signal?: AbortSignal): Promise<CapitalsDto> {
    return this.getByDate<CapitalsDto>('/capitals', date, signal);
  }

  /** GET /leaders?date=：該日領導人記錄（國家元首、政府首腦）。 */
  async leaders(date: string, signal?: AbortSignal): Promise<LeadersDto> {
    return this.getByDate<LeadersDto>('/leaders', date, signal);
  }

  async health(): Promise<HealthReport> {
    const res = await firstValueFrom(this.http.get<ApiEnvelope<HealthReport>>('/healthz'));
    return res.data;
  }
}
