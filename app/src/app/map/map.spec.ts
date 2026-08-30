import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import type { FeatureCollection, MultiPolygon } from 'geojson';
import { MapComponent } from './map';
import type { TerritoryFeatureProperties } from '../core/geometry/territory-styling';
import { TimelineState } from '../core/time/timeline-state';
import { TerritoryHatchPatternService } from '../core/geometry/territory-hatch-pattern.service';
import { MorphAnimationScheduler } from '../core/geometry/morph-animation-scheduler.service';
import { RegimeFocusState } from '../core/regime/regime-focus-state';
import { NamingViewpointState } from '../core/regime/naming-viewpoint-state';

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
    readonly setPaintPropertyCalls: Array<{ layerId: string; name: string; value: unknown }> = [];
    readonly setFilterCalls: Array<{ layerId: string; filter: unknown }> = [];
    /** 測試直接賦值控制 `queryRenderedFeatures()` 的回傳結果——模擬「點擊到某個政權的
        疆域」（回傳一筆帶 regimeId 的 feature）或「點在背景」（回傳空陣列）。 */
    queryRenderedFeaturesResult: Array<{ properties: Record<string, unknown> }> = [];
    removed = false;
    private loadCallback?: () => void;
    private clickCallback?: (e: { point: unknown }) => void;

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
    // 'click' 同理，讓測試自己決定何時觸發（見下面 fireClick()）。
    on(event: string, callback: (...args: never[]) => void): void {
      if (event === 'load') {
        this.loadCallback = callback as () => void;
      }
      if (event === 'click') {
        this.clickCallback = callback as (e: { point: unknown }) => void;
      }
    }

    fireLoad(): void {
      this.loadCallback?.();
    }

    fireClick(point: unknown = {}): void {
      this.clickCallback?.({ point });
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

    // 任務 3.7：MapComponent 用 getLayer() 判斷圖層是否已建立（避免對還不存在的圖層
    // 呼叫 queryRenderedFeatures()/setPaintProperty()/setFilter() 拋例外，真的 MapLibre
    // 在這種情況下確實會拋例外，這裡不特別模擬那個例外行為，只模擬「查得到/查不到」）。
    getLayer(id: string): { id: string } | undefined {
      const layer = this.addLayerCalls.find((l) => (l as { id: string }).id === id);
      return layer ? { id } : undefined;
    }

    queryRenderedFeatures(): Array<{ properties: Record<string, unknown> }> {
      return this.queryRenderedFeaturesResult;
    }

    setPaintProperty(layerId: string, name: string, value: unknown): void {
      this.setPaintPropertyCalls.push({ layerId, name, value });
    }

    setFilter(layerId: string, filter: unknown): void {
      this.setFilterCalls.push({ layerId, filter });
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

// MorphAnimationScheduler（任務 3.6）真正實作是包裝 requestAnimationFrame——JSDOM 雖然
// 有提供合成的 rAF，但真的等動畫時長（500ms）跑完會讓每個牽涉到換年份的測試都變慢又不
// 穩定，跟上面 fakeHatchPatternService 換掉 Canvas 2D 同一個處理原則：用 TestBed provider
// 換成「第一次排程就直接跳到終點」的假時序，不是真的等。`requestFrame` 回呼拿到的
// timestamp 遠大於 `now()` 第一次回傳的值，讓 map.ts 的 `rawT = (now-start)/duration`
// 算出來必定 >= 1，動畫在測試裡永遠是一步到位。
const fakeInstantMorphScheduler = {
  now: (): number => 0,
  requestFrame: (callback: FrameRequestCallback): number => {
    callback(1_000_000);
    return 1;
  },
  cancelFrame: (): void => {},
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

// 兩個 feature 真的有幾何重疊（經度 105-110 這段），用來驗證 territory-overlaps 這個
// source 真的有算出交集——不是只挑一個沒有重疊的樣本，那樣測不到 territory-overlap.ts
// 有沒有被正確呼叫。
function sampleOverlappingFeatureCollection(): FeatureCollection<MultiPolygon, TerritoryFeatureProperties> {
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
      {
        type: 'Feature',
        geometry: {
          type: 'MultiPolygon',
          coordinates: [[[[105, 20], [105, 30], [115, 30], [115, 20], [105, 20]]]],
        },
        properties: { id: 'b', regimeId: 'r-b', startYear: 220, endYear: 226, isDisputed: false },
      },
    ],
  };
}

// 在 sampleOverlappingFeatureCollection() 的 r-a/r-b 之外，再加一個完全不接壤的 r-c
// （例如唐朝聚焦時的阿拉伯帝國那種案例）——驗證「同時期但不相鄰」清單真的有算出東西，
// 不是永遠空的。
function sampleFeatureCollectionWithFarRegime(): FeatureCollection<MultiPolygon, TerritoryFeatureProperties> {
  const overlapping = sampleOverlappingFeatureCollection();
  return {
    type: 'FeatureCollection',
    features: [
      ...overlapping.features,
      {
        type: 'Feature',
        geometry: {
          type: 'MultiPolygon',
          coordinates: [[[[300, 20], [300, 30], [310, 30], [310, 20], [300, 20]]]],
        },
        properties: { id: 'c', regimeId: 'r-c', startYear: 220, endYear: 226, isDisputed: false },
      },
    ],
  };
}

// 換一個可辨識的 startYear，方便測試分辨「這是哪一輪換年份寫進去的資料」——不用比對
// 整包 geometry。
function withStartYear(
  fc: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>,
  startYear: number,
): FeatureCollection<MultiPolygon, TerritoryFeatureProperties> {
  return {
    ...fc,
    features: fc.features.map((f) => ({ ...f, properties: { ...f.properties, startYear } })),
  };
}

const sampleRegimes = [
  {
    id: 'r-a',
    selfName: '魏',
    status: 'succeeded' as const,
    predecessorRegimeId: null,
    originTransitionType: null,
    destroyedByRegimeId: null,
  },
  {
    id: 'r-b',
    selfName: '吳',
    status: 'conquered' as const,
    predecessorRegimeId: null,
    originTransitionType: null,
    destroyedByRegimeId: null,
  },
];

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
        { provide: MorphAnimationScheduler, useValue: fakeInstantMorphScheduler },
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

  it('on load, fetches regimes once then territories for the current timeline year, rendering fill/border/overlap layers plus name labels', async () => {
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
    territoriesReq.flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleOverlappingFeatureCollection() });

    // 兩個 source：territories（實際疆域）+ territory-overlaps（即時算出來的重疊區，
    // 見 territory-overlap.ts）。
    expect(map.addSourceCalls).toHaveLength(2);
    expect(map.addSourceCalls.map((s) => s.id)).toEqual(['territories', 'territory-overlaps']);

    // colorSlot 應該已經被 assignTerritoryColorSlots() 寫回 feature.properties——
    // 不重測相鄰計算/圖著色本身的邏輯（那是 territory-styling.spec.ts 的責任），
    // 只確認 MapComponent 真的有呼叫它、資料有被送進 addSource。
    const source = map.addSourceCalls[0].source as { data: FeatureCollection<MultiPolygon, TerritoryFeatureProperties> };
    expect(source.data.features[0].properties.colorSlot).toBeDefined();

    // sampleOverlappingFeatureCollection() 的兩個 feature 真的有幾何重疊，
    // territory-overlaps 這個 source 應該算出至少一塊交集（不重測交集演算法本身，
    // 那是 territory-overlap.spec.ts 的責任，這裡只確認 MapComponent 真的有呼叫它、
    // 結果有被送進 addSource）。
    const overlapSource = map.addSourceCalls[1].source as { data: FeatureCollection };
    expect(overlapSource.data.features.length).toBeGreaterThan(0);

    expect(map.addLayerCalls).toHaveLength(5);
    const layerIds = map.addLayerCalls.map((l) => (l as { id: string }).id);
    expect(layerIds).toEqual([
      'territories-fill',
      'territories-border',
      'territory-overlaps-fill',
      'territory-overlaps-hatch',
      'territories-focus-outline', // 任務 3.7：聚焦高亮外框，疊在最上層
    ]);

    // 重疊區底色：不透明中性色，蓋掉底下兩個政權各自的填色——不能只疊網底，網底圖樣
    // 背景透明，疊在 territories-fill 上面會透出「剛好排在後面那個政權」的顏色，
    // 看起來像這塊地只屬於其中一個政權（使用者實機發現的問題）。
    const overlapFillLayer = map.addLayerCalls.find(
      (l) => (l as { id: string }).id === 'territory-overlaps-fill',
    ) as { source: string; paint: { 'fill-opacity': unknown } };
    expect(overlapFillLayer.source).toBe('territory-overlaps');
    // 任務 3.6：改用 coalesce expression（沒有 opacity 屬性時預設 1），不是寫死的
    // 字面數字——重疊區要能跟著形變動畫的淡入淡出（見 territory-overlap.ts 的
    // TerritoryOverlap.opacity）。
    expect(overlapFillLayer.paint['fill-opacity']).toEqual(['coalesce', ['get', 'opacity'], 1]);

    // 疆域重疊區斜線網底：單一中性圖樣，不分色格（見 territory-dispute-pattern.ts
    // 開頭說明——重疊區可能同時牽涉兩個以上不同色相的政權，不屬於任何單一政權識別色）。
    expect(map.imageIds.size).toBe(1);
    expect(map.imageIds.has('territory-overlap-hatch')).toBe(true);

    const hatchLayer = map.addLayerCalls.find((l) => (l as { id: string }).id === 'territory-overlaps-hatch') as {
      source: string;
      paint: { 'fill-pattern': unknown; 'fill-opacity': unknown };
    };
    expect(hatchLayer.source).toBe('territory-overlaps');
    expect(hatchLayer.paint['fill-pattern']).toBe('territory-overlap-hatch');
    expect(hatchLayer.paint['fill-opacity']).toEqual(['coalesce', ['get', 'opacity'], 1]);

    const fillLayer = map.addLayerCalls.find((l) => (l as { id: string }).id === 'territories-fill') as {
      paint: { 'fill-opacity': unknown };
    };
    expect(fillLayer.paint['fill-opacity']).toEqual(['*', 0.85, ['coalesce', ['get', 'morphOpacity'], 1]]);

    // 標籤是 Marker（HTML 元素），不是 MapLibre 原生 symbol 圖層——見 territory-labels.ts
    // 開頭說明（避免另外接字型 glyphs 服務）。
    expect(FakeMarker.instances.length).toBeGreaterThan(0);
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

    expect(map.addSourceCalls).toHaveLength(2); // 第一次渲染，兩個 source 都建立過一次

    timeline.year.set(150);
    await waitForDebounce();

    const secondReq = httpMock.expectOne((r) => r.urlWithParams === '/api/v1/territories?year=150');
    secondReq.flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleFeatureCollection() });

    // 換年份後：source 沒有被重新建立（還是只有第一次那兩筆），兩個 source 都改用
    // setData() 更新（territories 本身 + 重新算出來的 territory-overlaps）。用的是
    // fakeInstantMorphScheduler，動畫一步到位，不會有中間幀的額外 setData()。
    expect(map.addSourceCalls).toHaveLength(2);
    expect(map.setDataCalls).toHaveLength(2);
    expect(map.addLayerCalls).toHaveLength(5); // 圖層也沒有被重複加
  });

  it('拖拉桿拖得比動畫時長還快時，取消掉還沒播完的舊動畫，最終畫面停在最新的年份而不是被卡在中途的年份（任務 3.6）', async () => {
    // 這裡刻意不用共用的 fakeInstantMorphScheduler（它一次排程就直接跳到終點，測不出
    // 「動畫還沒播完、年份又換了」這個競態情境）——改用手動控制的假排程器，把 callback
    // 存起來，讓測試自己決定何時觸發。
    const pendingCallbacks: FrameRequestCallback[] = [];
    const cancelledHandles: number[] = [];
    let nextHandle = 0;
    const manualScheduler = {
      now: (): number => 0,
      requestFrame: (callback: FrameRequestCallback): number => {
        pendingCallbacks.push(callback);
        return ++nextHandle;
      },
      cancelFrame: (handle: number): void => {
        cancelledHandles.push(handle);
      },
    };
    // 這個測試需要在 TestBed 初始化「之前」就換掉排程器——`overrideProvider()` 在
    // testing module 已經 instantiate 過之後呼叫會直接丟例外（`beforeEach()` 裡的
    // `TestBed.inject(HttpTestingController)` 已經讓它 instantiate 過一次），所以這裡
    // 重新 reset + configure 一次，用跟 beforeEach 同樣的 provider 清單，只把
    // MorphAnimationScheduler 換成這個測試專用的手動排程器。
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TerritoryHatchPatternService, useValue: fakeHatchPatternService },
        { provide: MorphAnimationScheduler, useValue: manualScheduler },
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);

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
    // 第一次渲染沒有「上一個狀態」可以形變過去，直接 settle()，不會走動畫分支——
    // 排程器應該完全沒被呼叫過。
    expect(pendingCallbacks).toHaveLength(0);

    timeline.year.set(150);
    await waitForDebounce();
    httpMock
      .expectOne((r) => r.urlWithParams === '/api/v1/territories?year=150')
      .flush({
        statusCode: 200,
        message: 'FETCH_SUCCESS',
        data: withStartYear(sampleFeatureCollection(), 150),
      });

    expect(pendingCallbacks).toHaveLength(1); // 第一輪動畫排了一幀，還沒觸發
    const staleCallback = pendingCallbacks[0];
    pendingCallbacks.length = 0;

    // 動畫還沒播完，拉桿又拖到下一個年份。
    timeline.year.set(160);
    await waitForDebounce();
    httpMock
      .expectOne((r) => r.urlWithParams === '/api/v1/territories?year=160')
      .flush({
        statusCode: 200,
        message: 'FETCH_SUCCESS',
        data: withStartYear(sampleFeatureCollection(), 160),
      });

    // 新的一輪動畫應該主動取消掉第一輪還沒播完的那一幀。
    expect(cancelledHandles).toHaveLength(1);

    // 就算舊的（本該被取消的）callback 之後還是被觸發了（模擬 cancelFrame 沒有真的
    // 立刻生效的邊界情況），也不該寫入資料——map.ts 的 morphToken 比對要擋下它。
    const setDataCallsBeforeStaleFire = map.setDataCalls.length;
    staleCallback(1_000_000);
    expect(map.setDataCalls.length).toBe(setDataCallsBeforeStaleFire); // 沒有新增任何 setData()

    // 觸發新一輪（真正沒被取代的那一輪）的排定幀，完成這次換年份。
    expect(pendingCallbacks).toHaveLength(1);
    pendingCallbacks[0](1_000_000);

    const lastTerritoriesWrite = [...map.setDataCalls]
      .reverse()
      .find(
        (data): data is FeatureCollection<MultiPolygon, TerritoryFeatureProperties> =>
          (data as FeatureCollection).features.length > 0 &&
          'regimeId' in ((data as FeatureCollection).features[0].properties ?? {}),
      );
    expect(lastTerritoriesWrite?.features[0].properties.startYear).toBe(160); // 停在最新年份，不是 150
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

  describe('政權聚焦模式（任務 3.7）', () => {
    async function renderWithOverlappingTerritories(
      territories: FeatureCollection<MultiPolygon, TerritoryFeatureProperties> = sampleOverlappingFeatureCollection(),
    ): Promise<{
      fixture: ReturnType<typeof TestBed.createComponent<MapComponent>>;
      map: InstanceType<typeof FakeMap>;
      focusState: RegimeFocusState;
    }> {
      const fixture = TestBed.createComponent(MapComponent);
      await fixture.whenStable();
      const map = FakeMap.instances[0];
      const focusState = TestBed.inject(RegimeFocusState);

      map.fireLoad();
      httpMock
        .expectOne((r) => r.urlWithParams === '/api/v1/regimes')
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleRegimes });
      await waitForDebounce();
      httpMock
        .expectOne((r) => r.urlWithParams === `/api/v1/territories?year=${TimelineState.DEFAULT_YEAR}`)
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: territories });

      return { fixture, map, focusState };
    }

    // 聚焦政權自己還會另外打三個查詢（存續區間 territories + AC#3 互動清單
    // events/relations，都是 RegimeFocusState 的責任，不是 MapComponent 這裡要驗證的
    // 範圍，見 regime-focus-state.spec.ts），flush 掉避免 httpMock.verify() 在
    // afterEach 噴「還有未處理的請求」。
    function flushRegimeFocusRequests(regimeId: string): void {
      httpMock
        .expectOne((r) => r.urlWithParams === `/api/v1/regimes/${regimeId}/territories`)
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleOverlappingFeatureCollection() });
      httpMock
        .expectOne((r) => r.urlWithParams === `/api/v1/regimes/${regimeId}/events?year=${TimelineState.DEFAULT_YEAR}`)
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: [] });
      httpMock
        .expectOne((r) => r.urlWithParams === `/api/v1/regimes/${regimeId}/relations?year=${TimelineState.DEFAULT_YEAR}`)
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: [] });
    }

    it('點擊政權疆域會聚焦該政權：套用「聚光燈」fill-opacity、更新高亮外框 filter、寫入周邊政權清單', async () => {
      const { fixture, map, focusState } = await renderWithOverlappingTerritories();

      // sampleOverlappingFeatureCollection() 的 r-a/r-b 兩塊疆域真的有幾何重疊
      // （見該 fixture 的說明），點擊到 r-a 應該把 r-b 算成周邊政權。
      map.queryRenderedFeaturesResult = [{ properties: { regimeId: 'r-a' } }];
      map.fireClick();
      await fixture.whenStable();

      flushRegimeFocusRequests('r-a');

      expect(focusState.focusedRegimeId()).toBe('r-a');
      expect(focusState.neighborRegimeIds()).toEqual(['r-b']);

      const lastPaint = map.setPaintPropertyCalls.at(-1);
      expect(lastPaint?.layerId).toBe('territories-fill');
      expect(lastPaint?.value).toEqual([
        'case',
        ['==', ['get', 'regimeId'], 'r-a'],
        ['*', 0.9, ['coalesce', ['get', 'morphOpacity'], 1]],
        ['*', 0.2, ['coalesce', ['get', 'morphOpacity'], 1]],
      ]);

      const lastFilter = map.setFilterCalls.at(-1);
      expect(lastFilter?.layerId).toBe('territories-focus-outline');
      expect(lastFilter?.filter).toEqual(['==', ['get', 'regimeId'], 'r-a']);
    });

    it('「同時期但不相鄰」的政權（例如唐朝聚焦時的阿拉伯帝國）會被算進 otherContemporaryRegimeIds，不會混進周邊政權清單', async () => {
      const { fixture, map, focusState } = await renderWithOverlappingTerritories(
        sampleFeatureCollectionWithFarRegime(),
      );

      map.queryRenderedFeaturesResult = [{ properties: { regimeId: 'r-a' } }];
      map.fireClick();
      await fixture.whenStable();
      flushRegimeFocusRequests('r-a');

      expect(focusState.neighborRegimeIds()).toEqual(['r-b']); // 真的接壤的
      expect(focusState.otherContemporaryRegimeIds()).toEqual(['r-c']); // 同時期但不接壤的
    });

    it('點擊背景（沒點到任何疆域）會清除聚焦', async () => {
      const { fixture, map, focusState } = await renderWithOverlappingTerritories();

      map.queryRenderedFeaturesResult = [{ properties: { regimeId: 'r-a' } }];
      map.fireClick();
      await fixture.whenStable();
      flushRegimeFocusRequests('r-a');
      expect(focusState.focusedRegimeId()).toBe('r-a');

      map.queryRenderedFeaturesResult = []; // 這次點在背景，查不到任何疆域
      map.fireClick();
      await fixture.whenStable();

      expect(focusState.focusedRegimeId()).toBeNull();
      const lastFilter = map.setFilterCalls.at(-1);
      expect(lastFilter?.filter).toEqual(['==', ['get', 'regimeId'], '']); // 空字串比對不到任何政權
    });

    it('再次點擊同一個政權會取消聚焦（toggle 行為）', async () => {
      const { fixture, map, focusState } = await renderWithOverlappingTerritories();

      map.queryRenderedFeaturesResult = [{ properties: { regimeId: 'r-a' } }];
      map.fireClick();
      await fixture.whenStable();
      flushRegimeFocusRequests('r-a');
      expect(focusState.focusedRegimeId()).toBe('r-a');

      map.fireClick(); // 同一個 queryRenderedFeaturesResult，還是點到 r-a
      await fixture.whenStable();

      expect(focusState.focusedRegimeId()).toBeNull();
    });
  });

  describe('命名視角切換（任務 3.8，Story 3）', () => {
    async function renderWithLabels(): Promise<{
      fixture: ReturnType<typeof TestBed.createComponent<MapComponent>>;
      namingViewpoint: NamingViewpointState;
    }> {
      const fixture = TestBed.createComponent(MapComponent);
      await fixture.whenStable();
      const map = FakeMap.instances[0];
      const namingViewpoint = TestBed.inject(NamingViewpointState);

      map.fireLoad();
      httpMock
        .expectOne((r) => r.urlWithParams === '/api/v1/regimes')
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleRegimes });
      await waitForDebounce();
      httpMock
        .expectOne((r) => r.urlWithParams === `/api/v1/territories?year=${TimelineState.DEFAULT_YEAR}`)
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleOverlappingFeatureCollection() });

      return { fixture, namingViewpoint };
    }

    // RegimeAliasDirectoryService 對 sampleRegimes 的每個政權（r-a/r-b）各查一次代稱
    // （見該 service 說明），這裡一次把兩筆都 flush 掉，呼叫端指定各自要回什麼資料。
    function flushAliasRequests(aliasesByRegime: Record<string, unknown[]>): void {
      for (const [regimeId, aliases] of Object.entries(aliasesByRegime)) {
        httpMock
          .expectOne((r) => r.urlWithParams === `/api/v1/regimes/${regimeId}/aliases`)
          .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: aliases });
      }
    }

    // FakeMarker.instances 是「這個測試檔跑過程中建立過的全部 Marker」（見 vi.hoisted()
    // 定義），不會因為 renderLabels() 呼叫 clearLabelMarkers() 而消失——舊 marker 只是
    // 被標記 removed=true，still 留在陣列裡。切換視角會重畫一輪新標籤，這裡只看「目前
    // 還沒被移除」的那些，不然會把舊一輪殘留的標籤也算進去。
    function activeLabelTexts(): string[] {
      return FakeMarker.instances
        .filter((m) => !m.removed)
        .map((m) => m.element.textContent)
        .sort();
    }

    // 跟「政權聚焦模式（任務 3.7）」describe 區塊裡同名的 helper 邏輯相同，這裡另外
    // 複製一份（不是共用）——兩個 describe 區塊刻意各自獨立管理測試情境，跟這個測試檔
    // 既有的 scoping 慣例一致（`renderWithOverlappingTerritories()` 也只在它自己的
    // describe 裡定義，不是頂層共用）。
    function flushRegimeFocusRequests(regimeId: string): void {
      httpMock
        .expectOne((r) => r.urlWithParams === `/api/v1/regimes/${regimeId}/territories`)
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: sampleOverlappingFeatureCollection() });
      httpMock
        .expectOne((r) => r.urlWithParams === `/api/v1/regimes/${regimeId}/events?year=${TimelineState.DEFAULT_YEAR}`)
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: [] });
      httpMock
        .expectOne((r) => r.urlWithParams === `/api/v1/regimes/${regimeId}/relations?year=${TimelineState.DEFAULT_YEAR}`)
        .flush({ statusCode: 200, message: 'FETCH_SUCCESS', data: [] });
    }

    it('全球客觀視角（預設）時標籤顯示自稱名稱，不打任何代稱請求（AC#1）', async () => {
      await renderWithLabels();

      expect(activeLabelTexts()).toEqual(['吳', '魏']); // sampleRegimes 的自稱名稱

      httpMock.expectNone(() => true); // 客觀視角完全用不到代稱資料，不該預先載入
    });

    it('切換到某個政權視角後，有代稱的政權標籤改顯示代稱；查無代稱的政權 fallback 回自稱（AC#2）', async () => {
      const { fixture, namingViewpoint } = await renderWithLabels();

      namingViewpoint.setObserver('r-shuhan');
      await fixture.whenStable();
      flushAliasRequests({
        'r-a': [{ id: 'alias-1', regimeId: 'r-a', observerRegimeId: 'r-shuhan', aliasName: '賊', aliasType: 'political' }],
        'r-b': [], // r-b 在這個視角下查無代稱，標籤應該 fallback 回自稱「吳」
      });
      await fixture.whenStable();

      expect(activeLabelTexts()).toEqual(['吳', '賊']); // r-a 顯示代稱，r-b fallback 回自稱
    });

    it('顯示代稱的標籤有 hover 用的 title 屬性（自稱本體）跟可點擊樣式；fallback 顯示自稱的標籤沒有（AC#2 可追溯性）', async () => {
      const { fixture, namingViewpoint } = await renderWithLabels();

      namingViewpoint.setObserver('r-shuhan');
      await fixture.whenStable();
      flushAliasRequests({
        'r-a': [{ id: 'alias-1', regimeId: 'r-a', observerRegimeId: 'r-shuhan', aliasName: '賊', aliasType: 'political' }],
        'r-b': [],
      });
      await fixture.whenStable();

      const byText = new Map(
        FakeMarker.instances.filter((m) => !m.removed).map((m) => [m.element.textContent, m.element]),
      );

      const aliasedEl = byText.get('賊')!;
      expect(aliasedEl.classList.contains('territory-label-clickable')).toBe(true);
      expect(aliasedEl.title).toBe('自稱：魏');

      const fallbackEl = byText.get('吳')!;
      expect(fallbackEl.classList.contains('territory-label-clickable')).toBe(false);
      expect(fallbackEl.title).toBe('');
    });

    it('點擊顯示代稱的標籤會聚焦該政權——追溯回自稱本體複用任務 3.7 既有的聚焦面板機制，不另外做一個顯示自稱的 UI', async () => {
      const { fixture, namingViewpoint } = await renderWithLabels();
      const focusState = TestBed.inject(RegimeFocusState);

      namingViewpoint.setObserver('r-shuhan');
      await fixture.whenStable();
      flushAliasRequests({
        'r-a': [{ id: 'alias-1', regimeId: 'r-a', observerRegimeId: 'r-shuhan', aliasName: '賊', aliasType: 'political' }],
        'r-b': [],
      });
      await fixture.whenStable();

      const aliasedEl = FakeMarker.instances.find((m) => !m.removed && m.element.textContent === '賊')!.element;
      aliasedEl.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await fixture.whenStable();
      flushRegimeFocusRequests('r-a');

      expect(focusState.focusedRegimeId()).toBe('r-a');
    });

    it('切回全球客觀視角時標籤改回自稱名稱，不重新打代稱請求（沿用已快取的資料）', async () => {
      const { fixture, namingViewpoint } = await renderWithLabels();

      namingViewpoint.setObserver('r-shuhan');
      await fixture.whenStable();
      flushAliasRequests({
        'r-a': [{ id: 'alias-1', regimeId: 'r-a', observerRegimeId: 'r-shuhan', aliasName: '賊', aliasType: 'political' }],
        'r-b': [],
      });
      await fixture.whenStable();

      namingViewpoint.setObserver(null);
      await fixture.whenStable();

      expect(activeLabelTexts()).toEqual(['吳', '魏']); // 改回自稱

      httpMock.expectNone(() => true); // 代稱資料已經快取過，不該重新打請求
    });
  });
});
