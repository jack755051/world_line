import type { components } from '../api-schema';
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

export type DisputeZonesDto = components['schemas']['DisputeZonesDto'];

export interface CapitalsDto {
  date: string;
  features: CapitalRecord[];
}

/** 舊格式逐欄位出處（自由文字，非結構化引用；不算已查證）。 */
export interface LeaderBioFieldSource {
  source?: string | null;
  url?: string | null;
  /** verified | 待查證 | 不適用 | 說法衝突（考證狀態文字；說法衝突時 note 寫兩說，docs/source-rules.md §5）。 */
  status?: string | null;
  note?: string | null;
}

/** 照片（只在授權欄位齊全時由後端回傳）。 */
export interface LeaderPortrait {
  url: string;
  sourceUrl: string;
  author: string | null;
  licenseCode: string;
  licenseUrl: string | null;
  attribution: string;
  retrievedOn: string;
}

export interface LeaderSource {
  id: string;
  sourceKind: string;
  title: string;
  publisher: string;
  authors: string | null;
  publishedText: string | null;
  licenseCode: string | null;
  licenseEvidenceUrl: string | null;
  url: string | null;
  archiveUrl: string | null;
}

/** 生平欄位引用（接 sources 表）。 */
export interface LeaderBioFieldCitation {
  id: string;
  field: string;
  locator: string;
  evidenceNote: string | null;
  accessedOn: string;
  source: LeaderSource;
  /** 引自該來源的原文短引（逐字、≤ 80 字）；DB 為 NULL 時 API 回 null。 */
  quote?: string | null;
  /** 引文語言（BCP 47），可為 null。 */
  quoteLang?: string | null;
  /** 這筆引用文件的等級 A｜B｜C（docs/source-rules.md §2）；null＝尚未評等。 */
  grade?: string | null;
  /** 此出處能支撐的日期精度 day｜month｜year；null＝未標。 */
  datePrecision?: string | null;
}

/** 人物詳情的任期（validPeriod.end 不含當天）。 */
export interface LeaderTerm {
  recordId: string;
  regimeId: string;
  regimeSlug: string;
  regimeName: Record<string, string> | null;
  role: 'head_of_state' | 'head_of_government';
  title: string | null;
  validPeriod: { start: string; end: string | null };
  source: string;
  sourceUrl: string | null;
  /** 任期的結構化引文（leader_record_citations，帶等級；source-rules §6 D6）。舊版 API 不帶。 */
  citations?: BioDetailCitation[] | null;
}

/** 領導人完整生平（GET /leader-bios/{id} 回應）。 */
export interface LeaderBio {
  id: string;
  name: string;
  nameZh: string | null;
  birthDate: string | null;
  birthDatePrecision: 'day' | 'month' | 'year' | null;
  deathDate: string | null;
  birthPlace: { 'zh-Hant'?: string; en?: string } | null;
  party: { 'zh-Hant'?: string; en?: string } | null;
  summary: { 'zh-Hant'?: string; en?: string } | null;
  fieldSources: Record<string, LeaderBioFieldSource> | null;
  isTest: boolean;
  retractedAt?: string | null;
  deathDatePrecision?: 'day' | 'month' | 'year' | null;
  wikidataQid?: string | null;
  portrait?: LeaderPortrait | null;
  supersededBy?: string | null;
  fieldCitations?: LeaderBioFieldCitation[] | null;
  terms?: LeaderTerm[] | null;
  /** B3 分段生平（依 ord）；開發庫尚無資料時缺欄或空陣列。 */
  paragraphs?: BioParagraph[] | null;
  /** B3 經歷全集（不是地圖出卡資料）。 */
  positions?: BioPosition[] | null;
  /** B3 角色（非地圖出卡資料）。 */
  roles?: BioRole[] | null;
  /** 未解決缺口。 */
  gaps?: BioGap[] | null;
}

/** B3 段落／經歷／角色引文。 */
export interface BioDetailCitation {
  id: string;
  locator: string;
  quote: string;
  quoteLang: string | null;
  evidenceNote: string | null;
  accessedOn: string;
  grade: string | null;
  datePrecision: string | null;
  source: LeaderSource;
}

type BioPrecision = string | null;
type BioPeriod = { start: string | null; end: string | null };

export interface BioParagraph {
  id: string;
  ord: number | string;
  period: BioPeriod | null;
  periodStartPrecision: BioPrecision;
  periodEndPrecision: BioPrecision;
  heading: Record<string, string> | null;
  body: Record<string, string>;
  citations: BioDetailCitation[];
}

export interface BioPosition {
  id: string;
  seedKey: string;
  regimeId: string | null;
  organization: Record<string, string> | null;
  title: Record<string, string>;
  positionKind: string;
  period: BioPeriod;
  startPrecision: BioPrecision;
  endPrecision: BioPrecision;
  note: string | null;
  citations: BioDetailCitation[];
}

export interface BioRole {
  id: string;
  seedKey: string;
  regimeId: string | null;
  organization: Record<string, string> | null;
  title: Record<string, string>;
  roleKind: string;
  period: BioPeriod;
  startPrecision: BioPrecision;
  endPrecision: BioPrecision;
  acting: boolean;
  t14Rule: string | null;
  note: string | null;
  citations: BioDetailCitation[];
}

export interface BioGap {
  id: string;
  target: string;
  gapKind: string;
  note: string | null;
  checkedOn: string;
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
  retractedAt?: string | null;
  deathDatePrecision?: 'day' | 'month' | 'year' | null;
  portrait?: LeaderPortrait | null;
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
  /** 任期的結構化引文（leader_record_citations，帶等級）。舊版 API 不帶。 */
  citations?: BioDetailCitation[] | null;
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

  /**
   * GET /regimes/{id}/geometry?date=&zoom=（ARCHITECTURE.md §9）：被選政權當天的主權紀錄＋它佔領的政權紀錄；
   * 每筆與同日 /sovereignty 的那筆相同。tiles 模式點選政權時才取（換日期不取）。
   */
  async regimeGeometry(regimeId: string, date: string, zoom?: number, signal?: AbortSignal): Promise<SovereigntyMapDto> {
    return this.getByDate<SovereigntyMapDto>(`/regimes/${encodeURIComponent(regimeId)}/geometry`, date, signal, zoom !== undefined ? { zoom: zoom.toFixed(1) } : undefined);
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

  /** GET /sovereignty/dispute-zones?date=：該日各筆主權爭議的重疊範圍（憲法 R6、I3）；沒有爭議時 features 為空。 */
  async disputeZones(date: string, signal?: AbortSignal): Promise<DisputeZonesDto> {
    return this.getByDate<DisputeZonesDto>('/sovereignty/dispute-zones', date, signal);
  }

  /** GET /capitals?date=：該日首都記錄（城市名稱、位置）。 */
  async capitals(date: string, signal?: AbortSignal): Promise<CapitalsDto> {
    return this.getByDate<CapitalsDto>('/capitals', date, signal);
  }

  /** GET /leaders?date=：該日領導人記錄（國家元首、政府首腦）。 */
  async leaders(date: string, signal?: AbortSignal): Promise<LeadersDto> {
    return this.getByDate<LeadersDto>('/leaders', date, signal);
  }

  /** GET /leader-bios/{id}：領導人完整生平。 */
  async getLeaderBio(id: string): Promise<LeaderBio> {
    const res = await firstValueFrom(this.http.get<ApiEnvelope<LeaderBio>>(`${WorldLineApi.base}/leader-bios/${id}`));
    return res.data;
  }

  async health(): Promise<HealthReport> {
    const res = await firstValueFrom(this.http.get<ApiEnvelope<HealthReport>>('/healthz'));
    return res.data;
  }
}
