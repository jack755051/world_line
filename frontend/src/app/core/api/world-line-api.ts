import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import type {
  ApiEnvelope,
  ControlMapDto,
  PaginatedSnapshots,
  RegimeDto,
  SourceDto,
  TimelineSnapshotDto,
} from './api-types';

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
  async control(date: string): Promise<ControlMapDto> {
    const res = await firstValueFrom(
      this.http.get<ApiEnvelope<ControlMapDto>>(`${WorldLineApi.base}/control`, {
        params: new HttpParams().set('date', date),
      }),
    );
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

  async regime(id: string): Promise<RegimeDto> {
    const res = await firstValueFrom(this.http.get<ApiEnvelope<RegimeDto>>(`${WorldLineApi.base}/regimes/${id}`));
    return res.data;
  }

  async source(id: string): Promise<SourceDto> {
    const res = await firstValueFrom(this.http.get<ApiEnvelope<SourceDto>>(`${WorldLineApi.base}/sources/${id}`));
    return res.data;
  }

  async health(): Promise<HealthReport> {
    const res = await firstValueFrom(this.http.get<ApiEnvelope<HealthReport>>('/healthz'));
    return res.data;
  }
}
