import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { vi } from 'vitest';
import { versionInfo } from '../../core/version';
import { VersionPage } from './version.page';

describe('VersionPage', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('# Changelog\n\n## [0.0.1]', { status: 200 }),
    );
    TestBed.configureTestingModule({ imports: [VersionPage], providers: [provideRouter([])] });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('顯示目前的版號（來自建置時產生的 core/version.ts）', async () => {
    const fixture = TestBed.createComponent(VersionPage);
    await fixture.whenStable();
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const versionEl = el.querySelector('[data-testid="version-number"]');
    expect(versionEl?.textContent).toContain(versionInfo.version);
  });

  it('回主地圖連結 href="/"', async () => {
    const fixture = TestBed.createComponent(VersionPage);
    await fixture.whenStable();
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const link = el.querySelector('[data-testid="version-back"]');
    expect(link?.getAttribute('href')).toBe('/');
  });

  it('會請求 /CHANGELOG.md', async () => {
    const fixture = TestBed.createComponent(VersionPage);
    await fixture.whenStable();
    fixture.detectChanges();
    expect(globalThis.fetch).toHaveBeenCalledWith('/CHANGELOG.md');
  });
});
