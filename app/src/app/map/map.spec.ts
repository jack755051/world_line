import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import type { FeatureCollection, MultiPolygon } from 'geojson';
import { MapComponent } from './map';
import type { TerritoryFeatureProperties } from '../core/geometry/territory-styling';

// MapLibre 需要真的 WebGL context 才能初始化，JSDOM 測試環境沒有——用假的 Map/
// NavigationControl/Marker 取代，只驗證「我們自己的 wiring 邏輯」（容器元素有傳進去、
// style 有背景層、有掛 NavigationControl、疆域+政權資料抓回來後有正確組出
// source/layer/標籤、ngOnDestroy 有清乾淨），不是重新測 MapLibre 本身的渲染行為。
//
// 用 vi.hoisted() 包起來，不是圖方便——vi.mock() 本身會被 Vitest 提升到檔案最頂端，
// 如果 FakeMap/FakeNavigationControl/FakeMarker 是普通的模組作用域宣告，mock factory
// 執行的當下這些 class 還沒被求值（TDZ），會直接炸掉；vi.hoisted() 裡的內容才會跟著
// vi.mock() 一起被提升，兩者順序才對得上。
const { FakeMap, FakeNavigationControl, FakeMarker } = vi.hoisted(() => {
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

  class FakeMarker {
    static instances: FakeMarker[] = [];
    element: HTMLElement;
    lngLat?: [number, number];
    removed = false;

    constructor(options: { element: HTMLElement }) {
      this.element = options.element;
      FakeMarker.instances.push(this);
    }

    setLngLat(lngLat: [number, number]): this {
      this.lngLat = lngLat;
      return this;
    }

    addTo(): this {
      return this;
    }

    remove(): void {
      this.removed = true;
    }
  }

  return { FakeMap, FakeNavigationControl, FakeMarker };
});

vi.mock('maplibre-gl', () => ({
  Map: FakeMap,
  NavigationControl: FakeNavigationControl,
  Marker: FakeMarker,
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

const sampleRegimes = [{ id: 'r-a', selfName: '魏' }];

describe('MapComponent', () => {
  let httpMock: HttpTestingController;

  beforeEach(() => {
    FakeMap.instances = [];
    FakeMarker.instances = [];
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

  it('on load, fetches territories + regimes for the fixed demo year and renders fill/border layers plus name labels', async () => {
    const fixture = TestBed.createComponent(MapComponent);
    await fixture.whenStable();
    const map = FakeMap.instances[0];

    map.fireLoad();

    // map.ts 把 `?year=225` 直接組進 URL 字串（不是用 HttpParams），所以查詢字串是
    // req.urlWithParams 的一部分，不是 req.params——比對要對應同一種組法。
    const territoriesReq = httpMock.expectOne((r) => r.urlWithParams === '/api/v1/territories?year=225');
    const regimesReq = httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes');
    expect(territoriesReq.request.method).toBe('GET');
    expect(regimesReq.request.method).toBe('GET');

    territoriesReq.flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleFeatureCollection() });
    regimesReq.flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleRegimes });

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

    // 標籤是 Marker（HTML 元素），不是 MapLibre 原生 symbol 圖層——見 territory-labels.ts
    // 開頭說明（避免另外接字型 glyphs 服務）。
    expect(FakeMarker.instances).toHaveLength(1);
    expect(FakeMarker.instances[0].element.textContent).toBe('魏');
    expect(FakeMarker.instances[0].element.className).toBe('territory-label');
  });

  it('logs an error but does not throw when either request fails', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const fixture = TestBed.createComponent(MapComponent);
    await fixture.whenStable();
    const map = FakeMap.instances[0];

    map.fireLoad();
    const territoriesReq = httpMock.expectOne((r) => r.urlWithParams === '/api/v1/territories?year=225');
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes'); // forkJoin 會訂閱兩邊，但下面 error() 一觸發整體就結束，這邊不用真的 flush 它
    territoriesReq.error(new ProgressEvent('network error'));
    // forkJoin 的行為：任一來源 error，整體立刻 error 並取消訂閱其餘來源——所以另一個
    // request 這時候已經被取消，不能也不需要對它呼叫 flush()（呼叫了會拋
    // "Cannot flush a cancelled request"）。

    expect(consoleErrorSpy).toHaveBeenCalled();
    expect(map.addSourceCalls).toHaveLength(0);
    expect(FakeMarker.instances).toHaveLength(0);
    consoleErrorSpy.mockRestore();
  });

  it('removes the map instance and label markers on destroy', async () => {
    const fixture = TestBed.createComponent(MapComponent);
    await fixture.whenStable();
    const map = FakeMap.instances[0];

    map.fireLoad();
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/territories?year=225')
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleFeatureCollection() });
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes')
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleRegimes });

    expect(FakeMarker.instances).toHaveLength(1);

    fixture.destroy();

    expect(map.removed).toBe(true);
    expect(FakeMarker.instances[0].removed).toBe(true);
  });
});
