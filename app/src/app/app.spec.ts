import { TestBed } from '@angular/core/testing';
import { App } from './app';

// App 內嵌了 MapComponent，MapComponent 會初始化 MapLibre——JSDOM 沒有 WebGL，
// 這裡 mock 掉，理由同 map/map.spec.ts（含 vi.hoisted() 的必要性說明）。這個檔案
// 不重覆測 MapComponent 內部邏輯，只驗證 App 這一層有把它接上去。
const { FakeMap, FakeNavigationControl } = vi.hoisted(() => ({
  FakeMap: class {
    addControl(): void {}
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
