import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import type { FeatureCollection, MultiPolygon } from 'geojson';
import { MapComponent } from './map';
import type { TerritoryFeatureProperties } from '../core/geometry/territory-styling';

// MapLibre 需要真的 WebGL context 才能初始化，JSDOM 測試環境沒有——用假的 Map/
// NavigationControl 取代，只驗證「我們自己的 wiring 邏輯」（容器元素有傳進去、
// style 有背景層、有掛 NavigationControl、疆域資料抓回來後有正確組出 source/layer、
// ngOnDestroy 有呼叫 remove），不是重新測 MapLibre 本身的渲染行為。
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
    readonly addSourceCalls: Array<{ id: string; source: unknown }> = [];
    readonly addLayerCalls: unknown[] = [];
    removed = false;
    private loadCallback?: () => void;

    constructor(options: Record<string, unknown>) {
      this.options = options;
      FakeMap.instances.push(this);
    }

    addControl(control: unknown, position?: string): void {
      this.addControlCalls.push({ control, position });
    }

    // 真的 MapLibre 的 'load' 事件是非同步的（等瓦片/資源就緒），但這個假的 Map 只需要
    // 記住 callback、讓測試自己決定何時觸發（見下面 fireLoad()）——不用真的模擬非同步
    // 時序，這裡只驗證「load 之後有沒有做對的事」，不是驗證 MapLibre 本身的事件時機。
    on(event: string, callback: () => void): void {
      if (event === 'load') {
        this.loadCallback = callback;
      }
    }

    fireLoad(): void {
      this.loadCallback?.();
    }

    addSource(id: string, source: unknown): void {
      this.addSourceCalls.push({ id, source });
    }

    addLayer(layer: unknown): void {
      this.addLayerCalls.push(layer);
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

function sampleFeatureCollection(): FeatureCollection<MultiPolygon, TerritoryFeatureProperties> {
  return {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: {
          type: 'MultiPolygon',
          coordinates: [[[[100, 20], [100, 30], [110, 30], [110, 20], [100, 20]]]],
        },
        properties: { id: 'a', regimeId: 'r-a', startYear: 220, endYear: 226, isDisputed: false },
      },
    ],
  };
}

describe('MapComponent', () => {
  let httpMock: HttpTestingController;

  beforeEach(() => {
    FakeMap.instances = [];
    // 明確 reset：前一個 it() 只要呼叫過 TestBed.createComponent()/inject()，這個
    // testing module 就算「已實例化」，這裡的 vitest-based test runner 不會自動幫
    // 每個 it() 重置（跟傳統 Karma/Jasmine 的預設行為不同），沒有這行下一個 it() 的
    // configureTestingModule() 會直接炸掉。
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
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

    httpMock.expectNone(() => true); // 'load' 還沒觸發，不該有任何 HTTP 請求
  });

  it('adds a NavigationControl so users can pan/zoom via UI, not just gesture', async () => {
    const fixture = TestBed.createComponent(MapComponent);
    await fixture.whenStable();

    const map = FakeMap.instances[0];
    expect(map.addControlCalls).toHaveLength(1);
    expect(map.addControlCalls[0].control).toBeInstanceOf(FakeNavigationControl);

    httpMock.expectNone(() => true);
  });

  it('on load, fetches territories for the fixed demo year and renders a fill + border layer', async () => {
    const fixture = TestBed.createComponent(MapComponent);
    await fixture.whenStable();
    const map = FakeMap.instances[0];

    map.fireLoad();

    // map.ts 把 `?year=225` 直接組進 URL 字串（不是用 HttpParams），所以查詢字串是
    // req.urlWithParams 的一部分，不是 req.params——比對要對應同一種組法。
    const req = httpMock.expectOne((r) => r.urlWithParams === '/api/v1/territories?year=225');
    expect(req.request.method).toBe('GET');
    req.flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleFeatureCollection() });

    expect(map.addSourceCalls).toHaveLength(1);
    expect(map.addSourceCalls[0].id).toBe('territories');

    // colorSlot 應該已經被 assignTerritoryColorSlots() 寫回 feature.properties——
    // 不重測相鄰計算/圖著色本身的邏輯（那是 territory-styling.spec.ts 的責任），
    // 只確認 MapComponent 真的有呼叫它、資料有被送進 addSource。
    const source = map.addSourceCalls[0].source as { data: FeatureCollection<MultiPolygon, TerritoryFeatureProperties> };
    expect(source.data.features[0].properties.colorSlot).toBeDefined();

    expect(map.addLayerCalls).toHaveLength(2);
    const layerIds = map.addLayerCalls.map((l) => (l as { id: string }).id);
    expect(layerIds).toEqual(['territories-fill', 'territories-border']);
  });

  it('logs an error but does not throw when the territory request fails', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const fixture = TestBed.createComponent(MapComponent);
    await fixture.whenStable();
    const map = FakeMap.instances[0];

    map.fireLoad();
    const req = httpMock.expectOne(() => true);
    req.error(new ProgressEvent('network error'));

    expect(consoleErrorSpy).toHaveBeenCalled();
    expect(map.addSourceCalls).toHaveLength(0);
    consoleErrorSpy.mockRestore();
  });

  it('removes the map instance on destroy to avoid leaking the WebGL context', async () => {
    const fixture = TestBed.createComponent(MapComponent);
    await fixture.whenStable();

    const map = FakeMap.instances[0];
    fixture.destroy();
    expect(map.removed).toBe(true);
  });
});
