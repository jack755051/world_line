import { computed, Injectable, signal } from '@angular/core';
import { versionInfo } from './version';

/**
 * 執行期版本資訊（Tai 2026-11-23：頁首版本要跟正式站實際部署的版本同步）。
 * 正式站：VPS 上 tiles/version.json，由 nginx 以 /version.json 提供（no-cache），
 * 部署腳本 scripts/set-version.sh（release-db.sh、release-tiles.sh 會呼叫）更新；不在映像裡，只換資料也會跟著變。
 * 抓不到（本機開發沒有這個檔、或內容不對）就退回建置時的 core/version.ts。
 */
export interface ReleaseInfo {
  version: string;
  updatedAt?: string;
  image?: { tag?: string; commit?: string };
  db?: { releasedAt?: string };
  overlay?: { version?: string; releasedAt?: string };
  boundaries?: { version?: string; releasedAt?: string };
}

const str = (v: unknown): string | undefined => (typeof v === 'string' && v ? v : undefined);
const obj = (v: unknown): Record<string, unknown> => (v && typeof v === 'object' ? (v as Record<string, unknown>) : {});

/** 只接受有 x.y.z 版本號的物件；其餘欄位缺了就略過。 */
export function parseReleaseInfo(raw: unknown): ReleaseInfo | null {
  const o = obj(raw);
  const version = str(o['version'])?.replace(/^v/, '');
  if (!version || !/^\d+\.\d+\.\d+/.test(version)) return null;
  const part = (k: string, ...keys: string[]) => {
    const p = obj(o[k]);
    const out = Object.fromEntries(keys.map((key) => [key, str(p[key])]).filter(([, v]) => v));
    return Object.keys(out).length ? out : undefined;
  };
  return {
    version,
    updatedAt: str(o['updatedAt']),
    image: part('image', 'tag', 'commit'),
    db: part('db', 'releasedAt'),
    overlay: part('overlay', 'version', 'releasedAt'),
    boundaries: part('boundaries', 'version', 'releasedAt'),
  };
}

/** 2026-11-23T09:19:16+08:00 → 2026-11-23 09:19（腳本寫的是台北時間） */
export const shortTime = (iso?: string): string => (iso ? iso.replace('T', ' ').slice(0, 16) : '');

/** 頁首提示：版本、資料庫發佈時間、overlay／疆界版本、映像提交；沒有 version.json 時與以前相同（建置資訊）。 */
export function releaseTitle(info: ReleaseInfo | null): string {
  const build = `提交 ${versionInfo.commit}，建置時間 ${versionInfo.buildTime}`;
  if (!info) return `版本 ${versionInfo.version}${versionInfo.ahead > 0 ? '（標籤之後第 ' + versionInfo.ahead + ' 個提交）' : ''}，${build}`;
  const parts = [`版本 ${info.version}`];
  if (info.db?.releasedAt) parts.push(`資料庫 ${shortTime(info.db.releasedAt)}`);
  if (info.overlay?.version) parts.push(`overlay ${info.overlay.version}${info.overlay.releasedAt ? '（' + shortTime(info.overlay.releasedAt) + '）' : ''}`);
  if (info.boundaries?.version) parts.push(`疆界 ${info.boundaries.version}${info.boundaries.releasedAt ? '（' + shortTime(info.boundaries.releasedAt) + '）' : ''}`);
  const img = [info.image?.tag, info.image?.commit].filter(Boolean).join(' @ ');
  if (img) parts.push(`映像 ${img}`);
  parts.push(`前端${build}`);
  return parts.join('；');
}

@Injectable({ providedIn: 'root' })
export class ReleaseInfoService {
  readonly info = signal<ReleaseInfo | null>(null);
  readonly version = computed(() => this.info()?.version ?? versionInfo.version);
  readonly title = computed(() => releaseTitle(this.info()));

  constructor() {
    // 開發伺服器沒有這個檔時會回 index.html（SPA fallback），json() 失敗 → 維持建置版本
    if (typeof fetch !== 'function') return;
    fetch('/version.json', { cache: 'no-cache' })
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => this.info.set(parseReleaseInfo(j)))
      .catch(() => undefined);
  }
}
