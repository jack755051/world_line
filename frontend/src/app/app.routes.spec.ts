import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { ToastService } from './components/ui/toast';
import { RouterTestingHarness } from '@angular/router/testing';
import { routes } from './app.routes';

describe('routes', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideRouter(routes), provideHttpClient(), provideHttpClientTesting(), ToastService] });
  });

  it('/ 進主地圖頁', async () => {
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/');
    expect(harness.routeNativeElement?.querySelector('[data-testid="atlas-page"]')).not.toBeNull();
  });

  it('未知路徑進 not-found', async () => {
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/no-such-page');
    expect(harness.routeNativeElement?.querySelector('[data-testid="not-found-page"]')).not.toBeNull();
  });

  it('/version 進版本頁', async () => {
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/version');
    expect(harness.routeNativeElement?.querySelector('[data-testid="version-page"]')).not.toBeNull();
  });
});
