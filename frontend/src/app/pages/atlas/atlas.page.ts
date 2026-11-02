import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, computed, effect, inject, signal, untracked, viewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import type { FeatureCollection } from 'geojson';
import { LucideCircleAlert, LucideCloudOff, LucideInfo, LucideRotateCw } from '@lucide/angular';
import { SkeletonDirective } from '../../components/ui/skeleton';
import { SpinnerComponent } from '../../components/ui/spinner';
import { ToastService } from '../../components/ui/toast';
import type { ConflictFeatureProperties, SovereigntyFeatureProperties } from '../../core/api/api-types';
import { AtlasData } from '../../core/atlas-data';
import { AtlasState, parseAtlasQuery } from '../../core/atlas-state';
import { t, type I18nKey, type Lang } from '../../core/i18n';
import { regimeSelfName } from '../../core/regime-names';
import { TopBar } from '../../layout/top-bar/top-bar';
import { FeatureCard } from '../../shared/feature-card/feature-card';
import { GapCard } from '../../shared/gap-card/gap-card';
import { Legend, type LegendRegime } from '../../shared/legend/legend';
import { MotionService } from '../../core/motion';
import { placeCard, type CardPlacement } from '../../shared/map/card-placement';
import { conflictArc } from '../../shared/map/conflict-arc';
import { AtlasMap, type MapConflictEvent, type MapConflictIcon, type MapFeatureEvent, type MapGapEvent, type MapSovereigntyEvent } from '../../shared/map/atlas-map';
import { ConflictCard } from '../../shared/conflict-card/conflict-card';
import { decorateSovereignty, sovereigntyLabels } from '../../shared/map/sovereignty-style';
import { DelayedFlag } from '../../core/delayed-flag';
import { SovereigntyCard, type SovereigntyTab } from '../../shared/sovereignty-card/sovereignty-card';
import { RegimeSheet } from '../../shared/regime-sheet/regime-sheet';
import { sheetLayout, type FocusInset } from '../../shared/map/focus';
import { campTonesFrom, controlLabels, decorateFeatures, gapFeatures } from '../../shared/map/map-style';
import { Timeline } from '../../shared/timeline/timeline';
import { COMPLETE_FROM, nearestDate } from '../../shared/timeline/timeline-scale';

interface SheetInfo {
  kind: 'sov' | 'conflict';
  title: string;
  description: string;
  descriptionLang: string;
  sov: { props: SovereigntyFeatureProperties; name: string; original: string; originalLang: string; occupierName: string } | null;
  conflict: { props: ConflictFeatureProperties; nameA: string; nameB: string } | null;
}

/**
 * 主地圖頁（`/`，PRD §8.0）。版面：頂部列 56px＋全幅地圖＋左下圖例 280px＋底部時間軸 112px。
 * 地圖只顯示後端 API 的資料；每個控制區都帶 API 回傳的引用（I6），點區塊 → 卡片 → 「來源」popover。
 */
@Component({
  selector: 'wl-atlas-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TopBar, AtlasMap, Legend, Timeline, FeatureCard, GapCard, SovereigntyCard, ConflictCard, RegimeSheet, SkeletonDirective, SpinnerComponent, LucideCircleAlert, LucideRotateCw, LucideCloudOff, LucideInfo],
  host: { class: 'block h-full' },
  template: `
    <main data-testid="atlas-page" class="relative h-full" [attr.lang]="lang()" aria-label="主地圖">
      @switch (data.health()) {
        @case ('checking') {
          <!-- Stitch W7-1：頂部列骨架＋紙色地圖區＋時間軸框架骨架（不畫任何資料） -->
          <div data-testid="app-skeleton" class="flex h-full flex-col" aria-busy="true">
            <div class="flex h-[var(--wl-topbar-height)] items-center gap-4 border-b border-wl-outline-variant bg-wl-surface px-4">
              <div sanringSkeleton class="h-4 w-24"></div><span class="h-6 w-px bg-wl-outline-variant" aria-hidden="true"></span>
              <div sanringSkeleton class="h-6 w-48"></div><div sanringSkeleton class="h-4 w-14"></div>
              <div class="ml-auto flex items-center gap-3"><div sanringSkeleton class="h-7 w-36"></div><div sanringSkeleton class="h-7 w-16"></div><div sanringSkeleton class="size-7"></div></div>
            </div>
            <div class="flex-1 bg-[#ece4d2]"></div>
            <div class="flex h-[var(--wl-timeline-height)] items-center gap-4 border-t border-wl-outline-variant bg-wl-surface px-4">
              <div class="flex w-[300px] flex-none items-center gap-1.5">
                <div sanringSkeleton class="size-7"></div><div sanringSkeleton class="size-7"></div><div sanringSkeleton class="size-7"></div>
                <span class="mx-1 h-5 w-px bg-wl-outline-variant" aria-hidden="true"></span><div sanringSkeleton class="h-7 w-14"></div><div sanringSkeleton class="h-7 w-28"></div>
              </div>
              <div class="flex flex-1 gap-2">
                <div class="flex w-[48px] flex-none flex-col gap-[6px]">@for (i of skeletonRows; track i) { <div sanringSkeleton class="h-[6px] w-full"></div> }</div>
                <div class="flex flex-1 flex-col gap-[6px]">@for (i of skeletonRows; track i) { <div sanringSkeleton class="h-[6px] w-full"></div> }</div>
              </div>
            </div>
          </div>
        }
        @case ('down') {
          <div data-testid="app-offline" class="flex h-full items-center justify-center bg-wl-background">
            <div class="wl-paper flex w-[420px] flex-col items-center gap-2 px-8 py-10 text-center" role="alert">
              <svg lucideCloudOff class="size-6 text-wl-error" aria-hidden="true"></svg>
              <h1 class="mt-2 wl-title1">{{ tr('offline.title') }}</h1>
              <p data-testid="app-offline-status" class="wl-text2 text-wl-on-surface-variant">{{ tr('offline.health', { status: data.healthStatus() ?? tr('offline.noResponse') }) }}</p>
              <button type="button" data-testid="app-retry" class="wl-btn-primary mt-4 inline-flex h-9 min-w-[132px] items-center justify-center gap-2 px-6 wl-text1 font-semibold" (click)="boot()">
                <svg lucideRotateCw class="size-4"></svg>{{ tr('map.retry') }}</button>
            </div>
          </div>
        }
        @default {
          <div class="flex h-full flex-col">
            <wl-top-bar [date]="state.date()" [lang]="lang()" [legendOpen]="state.legendOpen()" [controlStatus]="data.controlStatus()"
              [theaters]="data.control()?.theaters ?? null" [featureCount]="featureCount()" [axis]="state.axis()" (axisChange)="setAxis($event)"
              (langChange)="state.lang.set($event)" (legendToggle)="state.legendOpen.set(!state.legendOpen())" (jump)="setDate($event)" />
            <div #mapArea data-testid="map-area" [attr.data-ready-for]="mapReady() ? state.date() : null" class="relative flex-1 overflow-hidden bg-[#cfdbe0]">
              <wl-atlas-map [collection]="collection()" [labels]="allLabels()" [gaps]="gaps()" [selectedVersionId]="selected()?.versionId ?? null" [engineErrorText]="tr('map.engineError')"
 [axis]="state.axis()" [reducedMotion]="motion.reduced()"
                [fadeArmed]="fadeArmed()" (fadeConsumed)="fadeArmed.set(false)" (renderBusy)="mapRenderBusy.set($event)"
                [conflicts]="conflictIcons()" (conflictClick)="onConflictClick($event)"
                [capitals]="capitalsGeoJson()"
                [sovereignty]="sovereigntyFc()" [showCamps]="showCamps()" [selectedRecordId]="focusRecord()"
                [focusRecordId]="focusRecord()" [focusInset]="focusInset()"
                (featureClick)="onFeatureClick($event)" (gapClick)="onGapClick($event)" (sovereigntyClick)="onSovereigntyClick($event)"
                (emptyClick)="clearSelection()" (featureHover)="hover.set($event)" />

              <!-- 陣營外框圖層（補充，可開關；Tai 2026-10-31：政權優先於陣營，填色不變） -->
              <button type="button" data-testid="camp-layer-toggle" class="wl-paper absolute right-4 top-4 z-10 flex items-center gap-2 px-3 py-1.5 wl-text2"
                [attr.aria-pressed]="showCamps()" (click)="showCamps.set(!showCamps())">
                <span class="inline-block size-3 border border-wl-outline" [class.bg-wl-secondary]="showCamps()"></span>{{ lang() === 'en' ? 'Camp outlines (supplement)' : '陣營外框（補充）' }}
              </button>

              @if (firstLoad()) {
                <div data-testid="map-loading" class="pointer-events-none absolute inset-0 flex items-center justify-center">
                  <span class="wl-paper flex items-center gap-2 px-4 py-2 wl-text1"><sanring-spinner size="sm" ariaLabel="loading" />{{ tr('map.loading', { date: state.date() }) }}</span>
                </div>
              }

              <!-- 掃描線覆蓋層（plan A1）：跳年忙碌 >300ms 且非 firstLoad 時顯示；reducedMotion 時不啟動 -->
              @for (epoch of scanItems(); track epoch) {
                <div data-testid="map-scan" [attr.data-scan]="scanFading() ? null : 'active'"
                  class="absolute inset-0 z-[5] pointer-events-none overflow-hidden"
                  [class.wl-scan-out]="scanFading()">
                  <span data-testid="map-busy" class="sr-only" role="status" aria-live="polite">{{ tr('map.busy') }}</span>
                  <div class="wl-scan-paper absolute inset-0"></div>
                  <div class="wl-scan-beam absolute inset-0" (animationend)="onScanLineDone($event)"></div>
                </div>
              }

              @if (data.controlStatus() === 'error') {
                <div data-testid="map-error" class="absolute left-1/2 top-4 -translate-x-1/2">
                  <div class="wl-alert-error shadow-[var(--wl-shadow-panel)]" role="alert">
                    <svg lucideCircleAlert class="size-4 flex-none"></svg>
                    <span class="font-semibold">{{ tr('map.error') }}</span>
                    @if (data.controlDate(); as shown) { <span data-testid="map-error-showing" class="wl-text2 text-wl-on-surface-variant">{{ tr('map.errorShowing', { date: shown }) }}</span> }
                    <button type="button" data-testid="map-retry" class="wl-btn-secondary ml-4 h-7 px-3 wl-text2 text-wl-error" (click)="reloadControl()">{{ tr('map.retry') }}</button>
                  </div>
                </div>
              }

              @if (isEmpty()) {
                <div data-testid="map-empty" class="absolute inset-0 flex items-center justify-center">
                  <div class="wl-paper flex flex-col items-center gap-3 p-6">
                    <p class="wl-title2">{{ tr('map.empty') }}</p>
                    @if (nearest(); as n) {
                      <button type="button" data-testid="map-empty-jump" class="wl-btn-primary h-9 px-4" (click)="setDate(n)">{{ tr('map.emptyJump') }}（{{ n }}）</button>
                    }
                  </div>
                </div>
              }

              @if (state.date() < completeFrom) {
                <div data-testid="map-incomplete-period-hint" class="absolute left-4 top-4 wl-paper flex items-center gap-1.5 px-3 py-1.5 wl-text2"><svg lucideInfo class="size-3.5 text-wl-on-surface-variant" aria-hidden="true"></svg>{{ tr('map.incomplete') }}</div>
              }

              @if (hoverInfo(); as h) {
                <div data-testid="map-tooltip" role="tooltip" class="wl-paper pointer-events-none absolute z-10 px-3 py-2 wl-text2"
                  [style.left.px]="h.x + 12" [style.top.px]="h.y + 12">
                  <div class="wl-sub-title">{{ h.name }}・{{ h.type }}</div>
                  <div [class.text-wl-tertiary]="h.attested" [class.text-wl-on-surface-variant]="!h.attested">{{ h.evidence }}</div>
                </div>
              }

              @if (selectedInfo(); as s) {
                <div data-testid="feature-card-anchor" class="absolute z-20 overflow-y-auto" [style.left.px]="s.pos.left" [style.top.px]="s.pos.top" [style.bottom.px]="s.pos.bottom" [style.max-height.px]="s.pos.maxHeight">
                  <wl-feature-card [props]="s.props" [regimeName]="s.name" [originalName]="s.original" [originalLang]="s.originalLang"
                    [evidence]="s.evidence" [theaterState]="s.theater" [lang]="lang()" (closed)="clearSelection()" />
                </div>
              }

              <!-- 政權／衝突資訊：側邊滑出面板（桌面右側、窄螢幕底部；參考 sanring Sheet），衝突卡也在同一個面板內 -->
              <wl-regime-sheet [open]="sheetOpen()" [side]="layout().side" [size]="layout().size" [lang]="lang()"
                [title]="sheet()?.title ?? ''" [description]="sheet()?.description ?? ''" [descriptionLang]="sheet()?.descriptionLang ?? ''"
                [titleTestId]="sheet()?.kind === 'conflict' ? 'conflict-card-title' : 'sovereignty-card-title'"
                [closeTestId]="sheet()?.kind === 'conflict' ? 'conflict-card-close' : 'sovereignty-card-close'"
                (closed)="clearSelection()" (hidden)="onSheetHidden()">
                @if (sheet(); as sh) {
                  @if (sh.sov; as s) {
                    <wl-sovereignty-card [embedded]="true" class="flex min-h-0 flex-1 flex-col" [props]="s.props" [regimeName]="s.name" [originalName]="s.original" [originalLang]="s.originalLang" [occupierName]="s.occupierName" [lang]="lang()"
                      [conflicts]="sovConflicts()" [regimeEvents]="data.regimeEvents()[s.props.regimeId] ?? null" [eventsStatus]="data.regimeEventsStatus()[s.props.regimeId] ?? 'loading'"
                      [currentDate]="state.date()" [capital]="selectedCapital()" [leaders]="selectedLeaders()" [tab]="sovTab()" (tabChange)="sovTab.set($event)" (conflictSelect)="selectConflict($event)" (eventJump)="jumpToEvent($event)" />
                  } @else if (sh.conflict; as c) {
                    @if (returnSov(); as back) {
                      <button type="button" data-testid="regime-sheet-back" class="mb-2 flex flex-none items-center gap-1 self-start wl-text2 text-wl-on-surface-variant hover:text-wl-on-surface" (click)="backToRegime()">
                        ← {{ lang() === 'en' ? 'Back to' : '返回' }} {{ back.name }}</button>
                    }
                    <wl-conflict-card [embedded]="true" class="flex min-h-0 flex-1 flex-col" [props]="c.props" [nameA]="c.nameA" [nameB]="c.nameB" [lang]="lang()" />
                  }
                }
              </wl-regime-sheet>

              @if (selectedGapInfo(); as g) {
                <div data-testid="gap-card-anchor" class="absolute z-20 overflow-y-auto" [style.left.px]="g.pos.left" [style.top.px]="g.pos.top" [style.bottom.px]="g.pos.bottom" [style.max-height.px]="g.pos.maxHeight">
                  <wl-gap-card [note]="g.note" [lang]="lang()" (closed)="selectedGap.set(null)" />
                </div>
              }

              <div class="absolute bottom-4 left-4 z-10">
                <wl-legend [open]="state.legendOpen()" [lang]="lang()" [regimes]="legendRegimes()" [regimesStatus]="data.regimesStatus()"
                  [axis]="state.axis()"
                  (toggle)="state.legendOpen.set(!state.legendOpen())" />
              </div>
            </div>
            <div class="h-[var(--wl-timeline-height)] flex-none">
              <wl-timeline [date]="state.date()" [snapshots]="data.snapshots()" [earliestData]="data.earliestEvent()" [snapshotsStatus]="data.snapshotsStatus()" [lang]="lang()"
                [ready]="mapReady()" (playingChange)="playing.set($event)"
                (dateChange)="setDate($event)" (retry)="data.loadSnapshots()" (invalidInput)="onInvalidInput()" />
            </div>
          </div>
          <!-- 全畫面載入蒙版（Tai 2026-11-02）：蓋住整個視窗（含時間軸與側欄），擋住操作；資料就緒後淡出 -->
          <!-- 全畫面遮罩：僅限 firstLoad（第一次載入阻擋操作）或 reducedMotion（維持既有行為）時顯示 -->
          @if ((busyVisible() || busyFading()) && (firstLoad() || motion.reduced())) {
            <div data-testid="map-busy-scrim" [class.wl-scrim-hiding]="!busyVisible() && busyFading()"
              class="wl-map-scrim absolute inset-0 z-50 flex items-center justify-center">
              <div data-testid="map-busy" role="status" aria-live="polite"
                class="wl-paper pointer-events-none flex items-center gap-2 px-4 py-2 wl-text1 shadow-[var(--wl-shadow-panel)]">
                <sanring-spinner size="sm" speed="normal" [ariaLabel]="tr('map.busy')" />
                <span>{{ tr('map.busy') }}</span>
              </div>
            </div>
          }
        }
      }
    </main>
  `,
})
export class AtlasPage {
  protected readonly state = inject(AtlasState);
  protected readonly data = inject(AtlasData);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly toast = inject(ToastService, { optional: true });

  protected readonly completeFrom = COMPLETE_FROM;
  protected readonly skeletonRows = [0, 1, 2, 3, 4];
  protected readonly lang = this.state.lang;
  protected readonly selected = signal<MapFeatureEvent | null>(null);
  protected readonly hover = signal<MapFeatureEvent | null>(null);
  protected readonly selectedGap = signal<MapGapEvent | null>(null);
  protected readonly selectedSov = signal<MapSovereigntyEvent | null>(null);
  /**
   * 衝突圖示的焦點政權（Tai 2026-10-31）：平時不顯示衝突圖示；點選某個政權（開出資訊卡）後，
   * 只顯示與該政權相關的衝突；關掉資訊卡（或點空白處、換日期）就清掉焦點、圖示隱藏。
   */
  protected readonly focusRegimeId = signal<string | null>(null);
  protected readonly selectedConflict = signal<MapConflictEvent | null>(null);
  /** 地圖區（時間軸上方）大小：資訊卡依此避開時間軸與視窗邊緣。 */
  private readonly mapArea = viewChild<ElementRef<HTMLElement>>('mapArea');
  private readonly areaSize = signal({ w: 0, h: 0 });
  private place(x: number, y: number, cardW = 340): CardPlacement {
    const { w, h } = this.areaSize();
    return placeCard(x, y, w || window.innerWidth, h || window.innerHeight, cardW);
  }
  protected readonly showCamps = signal(false);
  protected readonly motion = inject(MotionService);
  /** 主權圖層（國界）：填色依政權；陣營只作補充。 */
  protected readonly sovereigntyFc = computed(() => decorateSovereignty(this.data.sovereignty()));
  /** 首都 GeoJSON：依目前語系選好 label，直接傳給地圖圖層。 */
  protected readonly capitalsGeoJson = computed<FeatureCollection>(() => {
    const dto = this.data.capitals();
    const lang = this.lang();
    if (!dto) return { type: 'FeatureCollection', features: [] };
    return {
      type: 'FeatureCollection',
      features: dto.features.map((f) => ({
        type: 'Feature',
        geometry: f.location,
        properties: {
          recordId: f.recordId,
          label: f.cityName[lang] ?? f.cityName.en ?? f.cityName['zh-Hant'] ?? f.regimeSlug,
        },
      })),
    };
  });
  protected readonly sovereigntyCount = computed(() => this.data.sovereignty()?.featureCollection.features.length ?? 0);
  protected readonly selectedSovInfo = computed(() => {
    const e = this.selectedSov();
    const f = e && this.data.sovereignty()?.featureCollection.features.find((x) => x.properties.recordId === e.recordId);
    if (!e || !f) return null;
    const reg = this.data.regimes()[f.properties.regimeId];
    const name = regimeSelfName(reg, this.lang());
    return {
      props: f.properties,
      name: name?.display ?? f.properties.regimeSlug,
      original: name?.original ?? '',
      originalLang: reg?.names.find((n) => n.nameKind === 'self')?.originalLang ?? '',
      occupierName: f.properties.occupation ? this.regimeName(f.properties.occupation.occupierRegimeId, f.properties.occupation.occupierSlug) : '',
    };
  });
  private regimeName(id: string, slug: string): string {
    return regimeSelfName(this.data.regimes()[id], this.lang())?.display ?? slug;
  }
  /** 目前選中政權的首都（直接從已載入的 capitals 圖層資料取出，不額外請求）。 */
  protected readonly selectedCapital = computed(() => {
    const s = this.selectedSovInfo();
    const caps = this.data.capitals();
    if (!s || !caps) return null;
    return caps.features.find((f) => f.regimeId === s.props.regimeId) ?? null;
  });
  /** 目前選中政權的領導人（直接從已載入的 leaders 資料過濾，不額外請求）。 */
  protected readonly selectedLeaders = computed(() => {
    const s = this.selectedSovInfo();
    const lea = this.data.leaders();
    if (!s || !lea) return [];
    return lea.features.filter((f) => f.regimeId === s.props.regimeId);
  });
  protected readonly focusedConflicts = computed(() => {
    const focus = this.focusRegimeId();
    if (!focus) return [];
    return (this.data.conflicts()?.featureCollection.features ?? []).filter(
      (f) => f.properties.regimeAId === focus || f.properties.regimeBId === focus,
    );
  });
  protected readonly conflictIcons = computed<MapConflictIcon[]>(() =>
    this.focusedConflicts().map((f) => {
      const p = f.properties;
      const c = (f.geometry as { coordinates: number[] }).coordinates;
      const label = `${this.regimeName(p.regimeAId, p.regimeASlug)} — ${this.regimeName(p.regimeBId, p.regimeBSlug)}`;
      // 雙方當日不相鄰（API arc）：畫虛線弧，雙劍改放弧線中點
      const a = p.arc?.from?.length === 2 && p.arc.to?.length === 2 ? conflictArc([Number(p.arc.from[0]), Number(p.arc.from[1])], [Number(p.arc.to[0]), Number(p.arc.to[1])]) : null;
      if (a) return { recordId: p.recordId, lngLat: a.mid, arc: a.path, focusEnd: p.regimeAId === this.focusRegimeId() ? 0 : p.regimeBId === this.focusRegimeId() ? 1 : null, label };
      return { recordId: p.recordId, lngLat: [c[0], c[1]] as [number, number], label };
    }),
  );
  protected readonly selectedConflictInfo = computed(() => {
    const e = this.selectedConflict();
    const f = e && this.focusedConflicts().find((x) => x.properties.recordId === e.recordId);
    if (!e || !f) return null;
    const p = f.properties;
    return { props: p, nameA: this.regimeName(p.regimeAId, p.regimeASlug), nameB: this.regimeName(p.regimeBId, p.regimeBSlug) };
  });
  /** 從政權面板切到衝突詳情時記住原政權，可「返回」。 */
  protected readonly returnSov = signal<{ e: MapSovereigntyEvent; name: string } | null>(null);
  /** 點時間線事件跳日期後，要在新日期重新聚焦的政權。 */
  private readonly pendingRegime = signal<string | null>(null);
  protected readonly sovConflicts = computed(() =>
    this.focusedConflicts().map((f) => {
      const p = f.properties;
      return { recordId: p.recordId, title: `${this.regimeName(p.regimeAId, p.regimeASlug)} — ${this.regimeName(p.regimeBId, p.regimeBSlug)}`, since: p.startEvent.occurred.start ?? '' };
    }),
  );
  /** 聚焦的主權紀錄：點政權時設定；開衝突卡時保留（仍聚焦在該政權）；關閉、點空白、換日期時清掉。 */
  protected readonly focusRecord = signal<string | null>(null);
  protected readonly layout = computed(() => sheetLayout(this.areaSize().w, this.areaSize().h));
  protected readonly sheetNow = computed<SheetInfo | null>(() => {
    const s = this.selectedSovInfo();
    if (s) return { kind: 'sov', title: s.name, description: s.original, descriptionLang: s.originalLang, sov: s, conflict: null };
    const c = this.selectedConflictInfo();
    if (c) return { kind: 'conflict', title: `${c.nameA} — ${c.nameB}`, description: this.lang() === 'en' ? 'Hostilities (conflict marker)' : '交戰（衝突圖示）', descriptionLang: '', sov: null, conflict: c };
    return null;
  });
  /** 面板顯示的內容：關閉時保留最後一筆，讓滑出動畫期間內容不消失；面板移除後（hidden）才清掉。 */
  protected readonly sheet = signal<SheetInfo | null>(null);
  /** 政權面板目前分頁：面板開著時切換政權、跳日期、看完衝突返回都保留（方便連續比較事件）；面板完全關閉後回到「概要」。 */
  protected readonly sovTab = signal<SovereigntyTab>('overview');
  /** MapLibre 是否還在載入／切片（setData 後、平移到新區域時）。 */
  protected readonly mapRenderBusy = signal(false);
  /** 時間軸是否在播放：播放時等資料（mapReady）才前進，不顯示地圖載入指示。 */
  protected readonly playing = signal(false);
  /** 目前日期的地圖資料已到、地圖也畫完（含 120ms 去抖動期間：日期剛變但還沒開始載入也算未就緒）。 */
  private readonly loadsStartedFor = signal<string | null>(null);
  protected readonly mapReady = computed(
    () => this.loadsStartedFor() === this.state.date() && !this.data.mapDataLoading() && !this.mapRenderBusy(),
  );
  /** 全畫面載入蒙版：資料請求或地圖切片持續 300ms 以上才顯示（DelayedFlag），完成後淡出再移除。 */
  protected readonly busyVisible = signal(false);
  /** 淡出中（資料已到、正在播 wl-scrim-out 動畫，220ms 後從 DOM 移除）。 */
  protected readonly busyFading = signal(false);
  /** 載入指示出現過 → 下一次抵達的國界淡入；指示隱藏後短暫保留，讓同一輪的資料仍能淡入。 */
  protected readonly fadeArmed = signal(false);
  private fadeDisarm: ReturnType<typeof setTimeout> | undefined;
  private fadeOutTimer: ReturnType<typeof setTimeout> | undefined;
  /** 掃描線覆蓋層（plan A1）：僅在非首次載入且非 reducedMotion 的跳年忙碌時顯示。 */
  protected readonly scanActive = signal(false);
  protected readonly scanFading = signal(false);
  private readonly scanLineDone = signal(false);
  /** 每次掃描啟動時遞增；透過 @for track 強制重建 DOM，確保 CSS animation 重置。 */
  private readonly scanEpoch = signal(0);
  protected readonly scanItems = computed(() => (this.scanActive() || this.scanFading()) ? [this.scanEpoch()] : []);
  private scanFadeTimer: ReturnType<typeof setTimeout> | undefined;
  private readonly busyFlag = new DelayedFlag((v) => {
    clearTimeout(this.fadeDisarm);
    if (v) {
      clearTimeout(this.fadeOutTimer);
      this.busyFading.set(false);
      this.busyVisible.set(true);
      this.fadeArmed.set(true);
      // 掃描覆蓋層：非首次載入且未設定 reducedMotion 才啟動
      if (!this.firstLoad() && !this.motion.reduced()) {
        clearTimeout(this.scanFadeTimer);
        this.scanFading.set(false);
        this.scanLineDone.set(false);
        this.scanEpoch.update((k) => k + 1);
        this.scanActive.set(true);
      }
    } else {
      clearTimeout(this.fadeOutTimer);
      // 立刻停止遮擋（busyVisible→false 同時 busyFading→true）：
      // wl-scrim-hiding class 立即生效（pointer-events:none），CSS 淡出 220ms 後清除
      this.busyVisible.set(false);
      this.busyFading.set(true);
      this.fadeOutTimer = setTimeout(() => {
        this.busyFading.set(false);
      }, this.motion.reduced() ? 0 : 220);
      this.fadeDisarm = setTimeout(() => this.fadeArmed.set(false), 400);
    }
  }, 300);
  protected readonly sheetOpen = computed(() => this.sheetNow() !== null);
  protected readonly focusInset = computed<FocusInset>(
    () => {
      if (!this.sheetOpen()) return { right: 0, bottom: 0 };
      const l = this.layout();
      return l.side === 'right' ? { right: l.size, bottom: 0 } : { right: 0, bottom: l.size };
    },
    { equal: (a, b) => a.right === b.right && a.bottom === b.bottom },
  );
  private readonly everLoaded = signal(false);

  /** 載入失敗而顯示舊日期資料時，不沿用舊的史料判斷：一律以推估（不明）樣式呈現（PRD §8.5 error 保守原則）。 */
  /** 陣營色（憲法 §6「陣營」）：只依 API 回傳的 controllerAlignment；沒有就是「陣營未建置」色，不推定。 */
  private readonly campTones = computed(() => campTonesFrom(this.data.control()));
  protected readonly collection = computed(() => {
    const dto = this.data.control();
    const { toneFor } = this.campTones();
    if (dto && this.data.controlStatus() === 'error' && this.data.showingStale()) return decorateFeatures({ ...dto, theaters: [] }, toneFor);
    return decorateFeatures(dto, toneFor);
  });
  /** 控制資料缺（R9）：只畫 API 的涵蓋備註；顯示舊日期資料時不畫（避免把別天的缺口當成今天的）。 */
  protected readonly gaps = computed(() =>
    this.data.controlStatus() === 'error' && this.data.showingStale() ? gapFeatures(null) : gapFeatures(this.data.control()),
  );
  protected readonly selectedGapInfo = computed(() => {
    const g = this.selectedGap();
    const note = g && this.data.control()?.coverageNotes?.find((n) => n.id === g.gapId);
    return g && note ? { pos: this.place(g.x, g.y, 300), note } : null;
  });
  protected readonly featureCount = computed(() => this.data.control()?.featureCollection.features.length ?? 0);
  protected readonly firstLoad = computed(() => !this.everLoaded() && this.data.controlStatus() !== 'error');
  protected readonly isEmpty = computed(
    () => this.data.controlStatus() === 'ok' && this.featureCount() === 0 && !this.data.showingStale()
      && this.data.sovereigntyStatus() !== 'loading' && this.sovereigntyCount() === 0,
  );
  protected readonly nearest = computed(() => nearestDate(this.data.snapshots().map((s) => s.asOf), this.state.date()));

  protected readonly legendRegimes = computed<LegendRegime[]>(() => {
    const feats = this.collection().features;
    const ids = [...new Set(feats.map((f) => f.properties.controllerRegimeId))];
    const regs = this.data.regimes();
    return ids
      .filter((id) => regs[id])
      .map((id) => {
        const mine = feats.filter((f) => f.properties.controllerRegimeId === id);
        return {
          id,
          name: regimeSelfName(regs[id], this.lang())?.display ?? id,
          tone: this.campTones().toneFor(id),
          camp: this.campTones().campFor(id),
          controlTypes: [...new Set(mine.map((f) => f.properties.controlType))],
          attested: mine.every((f) => f.properties.evidence === 'attested'),
        };
      });
  });

  /** 政權名稱標籤：只用 API 的政權自稱（PRD §8.2），查不到名稱的政權不標。 */
  protected readonly labels = computed(() => {
    const regs = this.data.regimes();
    const dto = this.data.control();
    if (!dto || (this.data.controlStatus() === 'error' && this.data.showingStale())) return [];
    return controlLabels(dto, (id) => regimeSelfName(regs[id], this.lang())?.display ?? null);
  });

  /** 國名標籤＋控制區政權標籤（控制區標籤在後，畫在國名上面）。 */
  protected readonly allLabels = computed(() => {
    const regs = this.data.regimes();
    const sov = sovereigntyLabels(this.data.sovereignty(), (id) => regimeSelfName(regs[id], this.lang())?.display ?? null);
    // 主權檢視只標國名；實際控制檢視國名在下、控制區政權標籤在上
    return this.state.axis() === 'sovereignty' ? sov : [...sov, ...this.labels()];
  });

  private findFeature(versionId: string) {
    return this.data.control()?.featureCollection.features.find((f) => f.properties.versionId === versionId) ?? null;
  }

  private describe(versionId: string) {
    const f = this.findFeature(versionId);
    if (!f) return null;
    const p = f.properties;
    const name = regimeSelfName(this.data.regimes()[p.controllerRegimeId], this.lang());
    const theater = this.data.control()?.theaters.find((x) => x.theaterCode === p.theaterCode) ?? null;
    const decorated = this.collection().features.find((x) => x.properties.versionId === versionId);
    return { p, name, theater, evidence: decorated?.properties.evidence ?? 'unknown' };
  }

  protected readonly hoverInfo = computed(() => {
    const h = this.hover();
    if (!h || this.selected()) return null;
    const d = this.describe(h.versionId);
    if (!d) return null;
    const key = `control.${d.p.controlType}` as I18nKey;
    const ev = d.evidence === 'attested'
      ? `${this.tr('evidence.attested')} ${d.theater?.attestingSnapshot?.asOf ?? ''}`
      : `${this.tr('evidence.interpolated')}，${this.lang() === 'en' ? 'not attested; nearest snapshot' : '非史料；最近史料'}：${d.theater?.prevSnapshot?.asOf ?? d.theater?.nextSnapshot?.asOf ?? '—'}`;
    return { x: h.x, y: h.y, name: d.name?.display ?? '—', type: this.tr(key), evidence: ev, attested: d.evidence === 'attested' };
  });

  protected readonly selectedInfo = computed(() => {
    const s = this.selected();
    if (!s) return null;
    const d = this.describe(s.versionId);
    if (!d) return null;
    return {
      pos: this.place(s.x, s.y, 300),
      props: d.p,
      name: d.name?.display ?? '',
      original: d.name?.original ?? '',
      originalLang: this.data.regimes()[d.p.controllerRegimeId]?.names.find((n) => n.nameKind === 'self')?.originalLang ?? '',
      evidence: d.evidence,
      theater: d.theater,
    };
  });

  private debounce: ReturnType<typeof setTimeout> | undefined;

  constructor() {
    const q = parseAtlasQuery(this.route.snapshot.queryParams as Record<string, string | undefined>);
    this.state.date.set(q.date);
    this.state.lang.set(q.lang);
    this.state.axis.set(q.axis);
    if (q.invalidDate) queueMicrotask(() => this.toast?.info(t('toast.invalidDate', q.lang)));

    effect(() => {
      if (this.data.controlStatus() === 'ok') untracked(() => this.everLoaded.set(true));
    });
    effect(() => {
      const dto = this.data.sovereignty();
      const want = this.pendingRegime();
      if (!want || !dto || this.data.sovereigntyShownFor() !== this.state.date()) return;
      untracked(() => {
        this.pendingRegime.set(null);
        const f = dto.featureCollection.features.find((x) => x.properties.regimeId === want);
        if (f) this.onSovereigntyClick({ recordId: f.properties.recordId, x: 0, y: 0 });
      });
    });
    effect(() => {
      const busy = !this.playing() && (this.data.mapDataLoading() || this.mapRenderBusy());
      untracked(() => this.busyFlag.set(busy));
    });
    // 掃描結束條件：掃描線到右端（animationend）AND mapReady，兩者都達成才 200ms 淡出
    effect(() => {
      if (!this.scanLineDone() || !this.mapReady() || !this.scanActive() || this.scanFading()) return;
      untracked(() => {
        clearTimeout(this.scanFadeTimer);
        this.scanFading.set(true);
        this.scanFadeTimer = setTimeout(() => {
          this.scanActive.set(false);
          this.scanFading.set(false);
        }, 200);
      });
    });
    inject(DestroyRef).onDestroy(() => {
      this.busyFlag.dispose();
      clearTimeout(this.fadeDisarm);
      clearTimeout(this.fadeOutTimer);
      clearTimeout(this.scanFadeTimer);
    });
    effect(() => {
      const s = this.sheetNow();
      if (s) untracked(() => this.sheet.set(s));
    });

    // 日期改變 → 載入控制區（拖動時去抖動 120ms）＋寫回 URL
    effect(() => {
      const date = this.state.date();
      const lang = this.state.lang();
      const axis = untracked(() => this.state.axis());
      untracked(() => {
        if (this.data.health() === 'up') {
          performance.mark('wl:sov:date-change');
          clearTimeout(this.debounce);
          this.debounce = setTimeout(() => {
            this.loadDate(date);
          }, this.everLoaded() ? (this.playing() ? 0 : 120) : 0);
        }
        void this.router.navigate([], {
          relativeTo: this.route,
          queryParams: { date, lang: lang === 'en' ? 'en' : null, axis: axis === 'sovereignty' ? 'sovereignty' : null },
          queryParamsHandling: 'merge',
          replaceUrl: true,
        });
      });
    });

    // 檢視軸改變 → 只寫回 URL（不重新載入資料）
    effect(() => {
      const axis = this.state.axis();
      untracked(() =>
        void this.router.navigate([], {
          relativeTo: this.route,
          queryParams: { axis: axis === 'sovereignty' ? 'sovereignty' : null },
          queryParamsHandling: 'merge',
          replaceUrl: true,
        }),
      );
    });

    // 地圖區大小（視窗縮放、時間軸高度變動）→ 資訊卡重新定位
    let ro: ResizeObserver | undefined;
    effect(() => {
      const el = this.mapArea()?.nativeElement;
      ro?.disconnect();
      ro = undefined;
      if (!el) return;
      const update = () => this.areaSize.set({ w: el.clientWidth, h: el.clientHeight });
      update();
      if (typeof ResizeObserver !== 'undefined') {
        ro = new ResizeObserver(update);
        ro.observe(el);
      }
    });
    inject(DestroyRef).onDestroy(() => {
      clearTimeout(this.debounce);
      ro?.disconnect();
    });
    void this.boot();
  }

  protected async boot(): Promise<void> {
    if (!(await this.data.checkHealth())) return;
    void this.data.loadSnapshots();
    void this.data.loadExtent();
    // 變動點很小（數百個日期）：先拿到，主權／衝突就能依區間快取
    await this.data.loadChangePoints();
    this.loadDate(this.state.date());
  }

  /** 載入某日的控制區／主權／衝突；主權與衝突都到了之後，預先載入相鄰格（播放往前 4；手動跳前後各一步）。 */
  private loadDate(date: string): void {
    this.loadsStartedFor.set(date);
    void this.data.loadControl(date);
    void this.data.loadCapitals(date);
    void this.data.loadLeaders(date);
    const playing = this.playing();
    void Promise.all([this.data.loadSovereignty(date), this.data.loadConflicts(date)]).then(() => {
      if (this.state.date() === date) void this.data.prefetch(date, 4, !playing);
    });
  }

  protected reloadControl(): void {
    void this.data.loadControl(this.state.date());
  }

  protected setDate(d: string): void {
    this.clearSelection();
    this.pendingRegime.set(null);
    this.state.setDate(d);
  }

  protected onFeatureClick(e: MapFeatureEvent): void {
    this.hover.set(null);
    this.selectedSov.set(null);
    this.selectedGap.set(null);
    this.selectedConflict.set(null);
    this.selected.set(e);
    this.focusRecord.set(null);
    this.focusRegimeId.set(this.findFeature(e.versionId)?.properties.controllerRegimeId ?? null);
  }

  protected setAxis(axis: 'control' | 'sovereignty'): void {
    this.state.axis.set(axis);
    if (axis === 'sovereignty') {
      // 控制區卡片關掉時，連帶清掉它帶出的衝突圖示焦點（政權卡／衝突卡仍開著就保留）
      if (this.selected() && !this.selectedConflict()) this.focusRegimeId.set(null);
      this.selected.set(null);
      this.selectedGap.set(null);
    }
  }

  protected onSovereigntyClick(e: MapSovereigntyEvent): void {
    this.hover.set(null);
    this.selected.set(null);
    this.selectedGap.set(null);
    this.selectedConflict.set(null);
    this.selectedSov.set(e);
    this.focusRecord.set(e.recordId);
    this.returnSov.set(null);
    const f = this.data.sovereignty()?.featureCollection.features.find((x) => x.properties.recordId === e.recordId);
    if (f) void this.data.loadRegimeEvents(f.properties.regimeId);
    this.focusRegimeId.set(f?.properties.regimeId ?? null);
  }

  /** 政權面板「相關衝突」點一項：切到衝突詳情（仍聚焦原政權），可返回。 */
  protected selectConflict(recordId: string): void {
    this.onConflictClick({ recordId, x: 0, y: 0 });
  }

  protected backToRegime(): void {
    const back = this.returnSov();
    if (!back) return;
    this.onSovereigntyClick(back.e);
  }

  /** 時間線點事件：跳到該日期；新日期資料載入後，若此政權仍有國界紀錄就重新聚焦。 */
  /** 面板滑出完成：清掉內容；若不是「跳到事件日期後要重新聚焦」的暫時關閉，分頁回到概要。 */
  protected onSheetHidden(): void {
    this.sheet.set(null);
    if (!this.pendingRegime() && !this.sheetNow()) this.sovTab.set('overview');
  }

  protected jumpToEvent(date: string): void {
    const regime = this.focusRegimeId();
    this.clearSelection();
    this.pendingRegime.set(regime);
    this.state.setDate(date);
  }

  /** 點衝突圖示：換成衝突卡，焦點政權不變（圖示保持顯示）。 */
  protected onConflictClick(e: MapConflictEvent): void {
    this.hover.set(null);
    this.selected.set(null);
    this.selectedGap.set(null);
    const sov = this.selectedSovInfo();
    if (sov) this.returnSov.set({ e: this.selectedSov()!, name: sov.name });
    this.selectedSov.set(null);
    this.selectedConflict.set(e);
  }

  protected onGapClick(e: MapGapEvent): void {
    this.hover.set(null);
    this.selected.set(null);
    this.selectedConflict.set(null);
    this.focusRegimeId.set(null);
    this.focusRecord.set(null);
    this.selectedGap.set(e);
  }

  protected clearSelection(): void {
    this.selected.set(null);
    this.selectedGap.set(null);
    this.selectedSov.set(null);
    this.selectedConflict.set(null);
    this.focusRegimeId.set(null);
    this.focusRecord.set(null);
    this.returnSov.set(null);
  }

  protected onScanLineDone(event: AnimationEvent): void {
    if (event.animationName === 'wl-scan-beam') {
      this.scanLineDone.set(true);
    }
  }

  protected onInvalidInput(): void {
    this.toast?.warning(this.lang() === 'en' ? 'Use YYYY-MM-DD' : '日期格式請用 YYYY-MM-DD');
  }

  protected tr(key: I18nKey, vars?: Record<string, string | number>): string {
    return t(key, this.lang() as Lang, vars);
  }
}
