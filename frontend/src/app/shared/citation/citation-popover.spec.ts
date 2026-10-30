import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import type { CitationDto } from '../../core/api/api-types';
import { CitationPopover, _resetCitationCache } from './citation-popover';

// 測試用假資料（只存在於測試檔）
const citations: CitationDto[] = [
  { sourceId: 's2', sourceTitle: '測試輔助來源', publisher: '測試出版者乙', licenseCode: null, locator: 'p. 1', role: 'date_check', evidenceNote: '日期核對' },
  { sourceId: 's1', sourceTitle: '測試主要地圖', publisher: '測試出版者甲', licenseCode: 'cc0', locator: '圖 15', role: 'primary', evidenceNote: '主要依據' },
];

describe('CitationPopover（PRD §8.9）', () => {
  beforeEach(() => {
    _resetCitationCache();
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
  });

  it('開啟後列出引用（主要來源在前）並補取來源詳情', async () => {
    const fixture = TestBed.createComponent(CitationPopover);
    fixture.componentRef.setInput('citations', citations);
    await fixture.whenStable();
    (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>('[data-testid="citation-button"]')!.click();
    await fixture.whenStable();

    const http = TestBed.inject(HttpTestingController);
    const reqs = http.match((r) => r.url.startsWith('/api/v1/sources/'));
    expect(reqs.map((r) => r.request.url).sort()).toEqual(['/api/v1/sources/s1', '/api/v1/sources/s2']);
    for (const r of reqs) {
      const id = r.request.url.split('/').pop();
      r.flush({ statusCode: 200, message: 'OK', data: { id, sourceKind: 'map', title: 't', publisher: 'p', authors: null, publishedText: '1940', licenseCode: null, licenseEvidenceUrl: null, url: 'https://example.org/x', archiveUrl: null, localCopyPath: null, catalogId: id === 's1' ? 'INV-1' : null, note: null } });
    }
    await new Promise((r) => setTimeout(r, 0));
    await fixture.whenStable();

    const pop = document.querySelector('[data-testid="citation-popover"]')!;
    expect(pop).not.toBeNull();
    const items = pop.querySelectorAll('[data-testid="citation-item"]');
    expect(items.length).toBe(2);
    expect(items[0].textContent).toContain('測試主要地圖');
    expect(items[0].querySelector('[data-testid="citation-locator"]')?.textContent).toContain('圖 15');
    expect(items[0].querySelector('[data-testid="citation-license"]')?.textContent).toContain('CC0');
    expect(items[0].textContent).toContain('INV-1');
    expect(items[1].querySelector('[data-testid="citation-license"]')?.textContent).toContain('未標註');
    http.verify();
  });

  it('沒有引用時顯示資料錯誤警示（I6）', async () => {
    const fixture = TestBed.createComponent(CitationPopover);
    fixture.componentRef.setInput('citations', []);
    await fixture.whenStable();
    (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>('[data-testid="citation-button"]')!.click();
    await fixture.whenStable();
    expect(document.querySelector('[data-testid="citation-missing-warning"]')?.textContent).toContain('缺少來源');
  });
});
