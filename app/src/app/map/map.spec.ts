import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import type { FeatureCollection, MultiPolygon } from 'geojson';
import { MapComponent } from './map';
import type { TerritoryFeatureProperties } from '../core/geometry/territory-styling';
import { TimelineState } from '../core/time/timeline-state';
import { TerritoryHatchPatternService } from '../core/geometry/territory-hatch-pattern.service';

// MapLibre 需要真的 WebGL context 才能初始化，JSDOM 測試環境沒有——用假的 Map/
// NavigationControl/Marker 取代，只驗證「我們自己的 wiring 邏輯」（容器元素有傳進去、
// style 有背景層、有掛 NavigationControl、疆域+政權資料抓回來後有正確組出
// source/layer/標籤、換年份時走 setData() 而不是重建圖層、ngOnDestroy 有清乾淨），
// 不是重新測 MapLibre 本身的渲染行為。
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
    readonly setDataCalls: unknown[] = [];
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

    // 第一次渲染後，MapComponent 應該透過 getSource().setData() 更新資料，不是再呼叫
    // addSource() 一次——回傳一個假的 GeoJSONSource，紀錄 setData() 有沒有被呼叫。
    getSource(id: string): { setData: (data: unknown) => void } | undefined {
      const found = this.addSourceCalls.find((s) => s.id === id);
      if (!found) return undefined;
      return { setData: (data: unknown) => this.setDataCalls.push(data) };
    }

    addLayer(layer: unknown): void {
      this.addLayerCalls.push(layer);
    }

    readonly imageIds = new Set<string>();

    hasImage(id: string): boolean {
      return this.imageIds.has(id);
    }

    addImage(id: string): void {
      this.imageIds.add(id);
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

// TerritoryHatchPatternService.create() 底層需要真的 Canvas 2D context——JSDOM 測試
// 環境沒有（getContext('2d') 回傳 null）。Angular 的 Vitest 整合不支援對相對路徑模組
// 用 vi.mock()（"Please use Angular TestBed for mocking dependencies"），所以這裡改用
// TestBed provider 換掉這個 service（見下面 beforeEach），不是用 vi.mock()。
const fakeHatchPatternService = {
  create: (): ImageData => ({ width: 8, height: 8, data: new Uint8ClampedArray(8 * 8 * 4), colorSpace: 'srgb' }) as ImageData,
};

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

// map.ts 訂閱 TimelineState.year 時用了 debounceTime(150)（見 map.ts 說明：避免拖拉桿
// 時每個中間值都發一次請求）——測試用真的時間等過這段 debounce，不用 vi.useFakeTimers()
// 硬控制計時器：Angular 的 zoneless TestBed 對 fake timers 的相容性不夠肯定，用真時間
// 換取測試行為的可信度，多等 200ms 對整體測試時間沒有實質影響。
function waitForDebounce(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 200));
}

describe('MapComponent', () => {
  let httpMock: HttpTestingController;

  beforeEach(() => {
    FakeMap.instances = [];
    FakeMarker.instances = [];
    // 明確 reset：前一個 it() 只要呼叫過 TestBed.createComponent()/inject()，這個
    // testing module 就算「已實例化」，這裡的 vitest-based test runner 不會自動幫
    // 每個 it() 重置（跟傳統 Karma/Jasmine 的預設行為不同），沒有這行下一個 it() 的
    // configureTestingModule() 會直接炸掉。TimelineState 是 providedIn: 'root' 的
    // 單例，reset 也讓它跟著換成全新實例，不會被前一個 it() 拖過來的 year 值污染。
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TerritoryHatchPatternService, useValue: fakeHatchPatternService },
      ],
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

  it('on load, fetches regimes once then territories for the current timeline year, rendering fill/border layers plus name labels', async () => {
    const fixture = TestBed.createComponent(MapComponent);
    await fixture.whenStable();
    const map = FakeMap.instances[0];

    map.fireLoad();

    const regimesReq = httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes');
    regimesReq.flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleRegimes });

    await waitForDebounce();

    // TimelineState 預設年份見 timeline-state.ts DEFAULT_YEAR。
    const territoriesReq = httpMock.expectOne(
      (r) => r.urlWithParams === `/api/v1/territories?year=${TimelineState.DEFAULT_YEAR}`,
    );
    territoriesReq.flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleFeatureCollection() });

    expect(map.addSourceCalls).toHaveLength(1);
    expect(map.addSourceCalls[0].id).toBe('territories');

    // colorSlot 應該已經被 assignTerritoryColorSlots() 寫回 feature.properties——
    // 不重測相鄰計算/圖著色本身的邏輯（那是 territory-styling.spec.ts 的責任），
    // 只確認 MapComponent 真的有呼叫它、資料有被送進 addSource。
    const source = map.addSourceCalls[0].source as { data: FeatureCollection<MultiPolygon, TerritoryFeatureProperties> };
    expect(source.data.features[0].properties.colorSlot).toBeDefined();

    expect(map.addLayerCalls).toHaveLength(3);
    const layerIds = map.addLayerCalls.map((l) => (l as { id: string }).id);
    expect(layerIds).toEqual(['territories-fill', 'territories-border', 'territories-disputed-hatch']);

    // 爭議控制區斜線網底：5 個色格各自註冊一張圖樣（見 territory-dispute-pattern.ts）。
    expect(map.imageIds.size).toBe(5);
    expect(map.imageIds.has('territory-hatch-0')).toBe(true);

    // 標籤是 Marker（HTML 元素），不是 MapLibre 原生 symbol 圖層——見 territory-labels.ts
    // 開頭說明（避免另外接字型 glyphs 服務）。
    expect(FakeMarker.instances).toHaveLength(1);
    expect(FakeMarker.instances[0].element.textContent).toBe('魏');
    expect(FakeMarker.instances[0].element.className).toBe('territory-label');
  });

  it('when the timeline year changes, re-queries territories and updates via setData() instead of re-adding the layer', async () => {
    const fixture = TestBed.createComponent(MapComponent);
    await fixture.whenStable();
    const map = FakeMap.instances[0];
    const timeline = TestBed.inject(TimelineState);

    map.fireLoad();
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes')
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleRegimes });
    await waitForDebounce();
    httpMock
      .expectOne((r) => r.urlWithParams === `/api/v1/territories?year=${TimelineState.DEFAULT_YEAR}`)
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleFeatureCollection() });

    expect(map.addSourceCalls).toHaveLength(1); // 第一次渲染，source 建立過一次

    timeline.year.set(150);
    await waitForDebounce();

    const secondReq = httpMock.expectOne((r) => r.urlWithParams === '/api/v1/territories?year=150');
    secondReq.flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleFeatureCollection() });

    // 換年份後：source 沒有被重新建立（還是只有第一次那一筆），改用 setData() 更新。
    expect(map.addSourceCalls).toHaveLength(1);
    expect(map.setDataCalls).toHaveLength(1);
    expect(map.addLayerCalls).toHaveLength(3); // 圖層也沒有被重複加
  });

  it('logs an error but does not throw when the territories request fails', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const fixture = TestBed.createComponent(MapComponent);
    await fixture.whenStable();
    const map = FakeMap.instances[0];

    map.fireLoad();
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes')
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleRegimes });
    await waitForDebounce();

    httpMock
      .expectOne((r) => r.urlWithParams === `/api/v1/territories?year=${TimelineState.DEFAULT_YEAR}`)
      .error(new ProgressEvent('network error'));

    expect(consoleErrorSpy).toHaveBeenCalled();
    expect(map.addSourceCalls).toHaveLength(0);
    expect(FakeMarker.instances).toHaveLength(0);
    consoleErrorSpy.mockRestore();
  });

  it('logs an error but does not throw when the regimes request fails', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const fixture = TestBed.createComponent(MapComponent);
    await fixture.whenStable();
    const map = FakeMap.instances[0];

    map.fireLoad();
    httpMock
      .expectOne((r) => r.urlWithParams === '/api/v1/regimes')
      .error(new ProgressEvent('network error'));

    expect(consoleErrorSpy).toHaveBeenCalled();
    expect(map.addSourceCalls).toHaveLength(0);
    httpMock.expectNone(() => true); // 政權清單都拿不到，不該繼續訂閱年份去查疆域
    consoleErrorSpy.mockRestore();
  });

  it('removes the map instance and label markers on destroy', async () => {
    const fixture = TestBed.createComponent(MapComponent);
    await fixture.whenStable();
    const map = FakeMap.instances[0];

    map.fireLoad();
    httpMock.expectOne((r) => r.urlWithParams === '/api/v1/regimes')
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleRegimes });
    await waitForDebounce();
    httpMock
      .expectOne((r) => r.urlWithParams === `/api/v1/territories?year=${TimelineState.DEFAULT_YEAR}`)
      .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleFeatureCollection() });

    expect(FakeMarker.instances).toHaveLength(1);

    fixture.destroy();

    expect(map.removed).toBe(true);
    expect(FakeMarker.instances[0].removed).toBe(true);
  });
});
