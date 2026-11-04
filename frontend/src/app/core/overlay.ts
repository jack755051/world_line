import { Injectable, signal } from '@angular/core';
import type { ConflictMapDto, ControlMapDto } from './api/api-types';
import type { CapitalsDto, LeadersDto } from './api/world-line-api';
import { readOverlayUrl } from './boundary-source';

/**
 * tiles 模式的 overlay（ARCHITECTURE.md §9 遷移步驟 5）：tools/tiles/build-overlay.py 依變動區間向第 1 層 API 取一次、
 * 存成一個靜態 JSON（開發由本機 nginx、正式由 CDN 提供）。載入一次後，換日期只在記憶體裡查區間，不發請求。
 * 控制區、控制資料缺的完整幾何在 overlay 圖磚；這裡每筆只帶最大多邊形（controlLabels 用，與 geojson 模式算出一樣的標籤）
 * 與全幾何外框（bbox，點選聚焦用）。範圍外的日期回傳 null，呼叫端退回 API。
 */
type Geo = { type: string; coordinates: unknown } | null;
interface Shape { largest: Geo; bbox: [number, number, number, number] | null }
interface ControlSection {
  points: string[];
  intervals: { start: string; features: string[]; theaters: unknown[]; notes: string[] }[];
  features: Record<string, { type: string; id?: string; properties: { versionId: string } & Record<string, unknown> }>;
  shapes: Record<string, Shape>;
  notes: Record<string, { id: string } & Record<string, unknown>>;
  noteShapes: Record<string, Shape>;
}
interface RecordSection<T> { points: string[]; intervals: { start: string; ids: string[] }[]; records: Record<string, T> }
export interface OverlayFile {
  version: string;
  range: [string, string];
  control?: ControlSection;
  conflicts?: RecordSection<unknown>;
  capitals?: RecordSection<unknown>;
  leaders?: RecordSection<unknown>;
  sovstyle?: RecordSection<SovStyleRow>;
}

/** 主權圖層的日期相關樣式（佔領歸屬、陣營），只收有其中一項或非主權的政權。 */
export interface SovStyleRow {
  regimeId: string;
  regimeSlug: string;
  layerStatus: string;
  camp: string | null;
  occupation: { occupierRegimeId: string; occupierSlug: string; controlKind: string } | null;
}

export function overlaySovStyle(o: OverlayFile | null, date: string): SovStyleRow[] | null {
  return records<SovStyleRow>(o, o?.sovstyle as RecordSection<unknown> | undefined, date);
}

/** 有序日期裡 ≤ date 的最後一個位置（沒有則 -1）。 */
export function intervalIndex(points: readonly string[], date: string): number {
  let lo = 0, hi = points.length - 1, ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (points[mid] <= date) { ans = mid; lo = mid + 1; } else hi = mid - 1;
  }
  return ans;
}

export function overlayCovers(o: OverlayFile | null, date: string): boolean {
  return !!o && date >= o.range[0] && date <= o.range[1];
}

export function overlayControl(o: OverlayFile | null, date: string): ControlMapDto | null {
  const c = o?.control;
  if (!c || !overlayCovers(o, date)) return null;
  const iv = c.intervals[intervalIndex(c.points, date)];
  if (!iv) return null;
  const features = iv.features.map((h) => {
    const f = c.features[h];
    const s = c.shapes[f.properties.versionId];
    return { ...f, geometry: s?.largest ?? null, bbox: s?.bbox ?? undefined };
  });
  const coverageNotes = iv.notes.map((h) => {
    const n = c.notes[h];
    return { ...n, geometry: c.noteShapes[n.id]?.largest ?? null };
  });
  return { date, featureCollection: { type: 'FeatureCollection', features }, theaters: iv.theaters, coverageNotes } as unknown as ControlMapDto;
}

function records<T>(o: OverlayFile | null, sec: RecordSection<unknown> | undefined, date: string): T[] | null {
  if (!sec || !overlayCovers(o, date)) return null;
  const iv = sec.intervals[intervalIndex(sec.points, date)];
  return iv ? iv.ids.map((h) => sec.records[h] as T) : null;
}

export function overlayConflicts(o: OverlayFile | null, date: string): ConflictMapDto | null {
  const fs = records<unknown>(o, o?.conflicts, date);
  return fs ? ({ date, featureCollection: { type: 'FeatureCollection', features: fs } } as unknown as ConflictMapDto) : null;
}

export function overlayCapitals(o: OverlayFile | null, date: string): CapitalsDto | null {
  const fs = records<unknown>(o, o?.capitals, date);
  return fs ? ({ date, features: fs } as unknown as CapitalsDto) : null;
}

export function overlayLeaders(o: OverlayFile | null, date: string): LeadersDto | null {
  const fs = records<unknown>(o, o?.leaders, date);
  return fs ? ({ date, features: fs } as unknown as LeadersDto) : null;
}

/** overlay 區間 key（同一區間換日期不換資料物件）。範圍外回傳 null。 */
export function overlayKey(o: OverlayFile | null, section: 'control' | 'conflicts' | 'capitals' | 'leaders' | 'sovstyle', date: string): string | null {
  const sec = o?.[section];
  if (!sec || !overlayCovers(o, date)) return null;
  return `ov:${o!.version}:${sec.points[intervalIndex(sec.points, date)] ?? ''}`;
}

@Injectable({ providedIn: 'root' })
export class OverlayStore {
  readonly data = signal<OverlayFile | null>(null);
  readonly status = signal<'idle' | 'loading' | 'ok' | 'error'>('idle');
  private loading: Promise<OverlayFile | null> | null = null;

  /** 只載一次；失敗時回傳 null（呼叫端退回 API）。 */
  load(url: string = readOverlayUrl()): Promise<OverlayFile | null> {
    if (this.loading) return this.loading;
    this.status.set('loading');
    this.loading = fetch(url)
      .then((r) => (r.ok ? (r.json() as Promise<OverlayFile>) : Promise.reject(new Error(String(r.status)))))
      .then((o) => {
        this.data.set(o);
        this.status.set('ok');
        return o;
      })
      .catch(() => {
        this.status.set('error');
        return null;
      });
    return this.loading;
  }
}
