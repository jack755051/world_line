import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { App } from './app';

// App 內嵌了 MapComponent，MapComponent 會初始化 MapLibre——JSDOM 沒有 WebGL，
// 這裡 mock 掉，理由同 map/map.spec.ts（含 vi.hoisted() 的必要性說明）。`on()` 故意
// 什麼都不做（不觸發 'load'）——這個檔案不重覆測 MapComponent 內部的疆域載入邏輯
// （那是 map.spec.ts 的責任），只驗證 App 這一層有把 MapComponent 接上去；HttpClient
// 一樣要提供（MapComponent 建構子會 inject），但不需要真的處理任何請求。
const { FakeMap, FakeNavigationControl } = vi.hoisted(() => ({
  FakeMap: class {
    addControl(): void {}
    on(): void {}
    remove(): void {}
  },
  FakeNavigationControl: class {},
}));

vi.mock('maplibre-gl', () => ({
  Map: FakeMap,
  NavigationControl: FakeNavigationControl,
}));

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    })
      .compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should render title', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('h1')?.textContent).toContain('World Line');
  });

  it('should render the map component', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('app-map')).toBeTruthy();
  });
});
