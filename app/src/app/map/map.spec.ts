import { TestBed } from '@angular/core/testing';
import { MapComponent } from './map';

// MapLibre 需要真的 WebGL context 才能初始化，JSDOM 測試環境沒有——用假的 Map/
// NavigationControl 取代，只驗證「我們自己的 wiring 邏輯」（容器元素有傳進去、
// style 有背景層、有掛 NavigationControl、ngOnDestroy 有呼叫 remove），不是重新
// 測 MapLibre 本身的渲染行為。
//
// 用 vi.hoisted() 包起來，不是圖方便——vi.mock() 本身會被 Vitest 提升到檔案最頂端，
// 如果 FakeMap/FakeNavigationControl 是普通的模組作用域宣告，mock factory 執行的
// 當下這兩個 class 還沒被求值（TDZ），會直接炸掉；vi.hoisted() 裡的內容才會跟著
// vi.mock() 一起被提升，兩者順序才對得上。
const { FakeMap, FakeNavigationControl } = vi.hoisted(() => {
  class FakeMap {
    static instances: FakeMap[] = [];
    readonly options: Record<string, unknown>;
    readonly addControlCalls: Array<{ control: unknown; position?: string }> = [];
    removed = false;

    constructor(options: Record<string, unknown>) {
      this.options = options;
      FakeMap.instances.push(this);
    }

    addControl(control: unknown, position?: string): void {
      this.addControlCalls.push({ control, position });
    }

    remove(): void {
      this.removed = true;
    }
  }

  class FakeNavigationControl {}

  return { FakeMap, FakeNavigationControl };
});

vi.mock('maplibre-gl', () => ({
  Map: FakeMap,
  NavigationControl: FakeNavigationControl,
}));

describe('MapComponent', () => {
  beforeEach(() => {
    FakeMap.instances = [];
  });

  it('creates without throwing', () => {
    const fixture = TestBed.createComponent(MapComponent);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('initializes MapLibre with the container element and a background-only style', async () => {
    const fixture = TestBed.createComponent(MapComponent);
    await fixture.whenStable();

    expect(FakeMap.instances.length).toBe(1);
    const map = FakeMap.instances[0];
    const container = fixture.nativeElement.querySelector('.map-container');
    expect(map.options['container']).toBe(container);

    // 沒有接外部瓦片服務（見 map.ts 開頭說明）：sources 是空的，只有一個 background 圖層。
    const style = map.options['style'] as { sources: Record<string, unknown>; layers: Array<{ type: string }> };
    expect(Object.keys(style.sources)).toHaveLength(0);
    expect(style.layers).toHaveLength(1);
    expect(style.layers[0].type).toBe('background');
  });

  it('adds a NavigationControl so users can pan/zoom via UI, not just gesture', async () => {
    const fixture = TestBed.createComponent(MapComponent);
    await fixture.whenStable();

    const map = FakeMap.instances[0];
    expect(map.addControlCalls).toHaveLength(1);
    expect(map.addControlCalls[0].control).toBeInstanceOf(FakeNavigationControl);
  });

  it('removes the map instance on destroy to avoid leaking the WebGL context', async () => {
    const fixture = TestBed.createComponent(MapComponent);
    await fixture.whenStable();

    const map = FakeMap.instances[0];
    fixture.destroy();
    expect(map.removed).toBe(true);
  });
});
