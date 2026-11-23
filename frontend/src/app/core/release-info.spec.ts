import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { versionInfo } from './version';
import { parseReleaseInfo, releaseTitle, ReleaseInfoService } from './release-info';

const sample = {
  version: '0.0.4',
  updatedAt: '2026-11-23T11:00:00+08:00',
  image: { tag: 'v0.0.4', commit: 'abc1234' },
  db: { releasedAt: '2026-11-23T09:19:16+08:00' },
  overlay: { version: '54e27ac7d35f', releasedAt: '2026-11-23T09:39:22+08:00' },
};

describe('release-info', () => {
  afterEach(() => vi.restoreAllMocks());

  it('parse：接受 x.y.z（去掉 v），版本不對就回 null', () => {
    expect(parseReleaseInfo({ ...sample, version: 'v0.0.4' })?.version).toBe('0.0.4');
    expect(parseReleaseInfo({ version: 'latest' })).toBeNull();
    expect(parseReleaseInfo('<!doctype html>')).toBeNull();
    expect(parseReleaseInfo({ version: '0.0.4' })?.db).toBeUndefined();
  });

  it('提示含資料庫、overlay、映像；沒有 version.json 時用建置資訊', () => {
    const t = releaseTitle(parseReleaseInfo(sample));
    expect(t).toContain('版本 0.0.4');
    expect(t).toContain('資料庫 2026-11-23 09:19');
    expect(t).toContain('overlay 54e27ac7d35f（2026-11-23 09:39）');
    expect(t).toContain('映像 v0.0.4 @ abc1234');
    expect(releaseTitle(null)).toContain(`版本 ${versionInfo.version}`);
  });

  it('service：讀 /version.json；失敗時退回建置版本', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(sample), { status: 200 }));
    const svc = TestBed.inject(ReleaseInfoService);
    await vi.waitFor(() => expect(svc.version()).toBe('0.0.4'));
    expect(spy).toHaveBeenCalledWith('/version.json', { cache: 'no-cache' });

    TestBed.resetTestingModule();
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('<html></html>', { status: 200 }));
    const svc2 = TestBed.inject(ReleaseInfoService);
    await new Promise((r) => setTimeout(r, 0));
    expect(svc2.version()).toBe(versionInfo.version);
    expect(svc2.info()).toBeNull();
  });
});
