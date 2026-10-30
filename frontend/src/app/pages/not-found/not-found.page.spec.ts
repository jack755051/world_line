import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NotFoundPage } from './not-found.page';

describe('NotFoundPage', () => {
  it('顯示標題與回主地圖連結', async () => {
    TestBed.configureTestingModule({ imports: [NotFoundPage], providers: [provideRouter([])] });
    const fixture = TestBed.createComponent(NotFoundPage);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('h1')?.textContent).toContain('找不到頁面');
    expect(el.querySelector('a')?.getAttribute('href')).toBe('/');
  });
});
