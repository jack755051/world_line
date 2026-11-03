import { NgTemplateOutlet } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideX } from '@lucide/angular';
import type { ControlFeatureProperties, RegimeEventDto, SovereigntyFeatureProperties, TheaterStateDto } from '../../core/api/api-types';
import type { CapitalRecord, LeaderRecord } from '../../core/api/world-line-api';
import { localized, type Lang } from '../../core/i18n';
import { theaterLabel } from '../../core/theater-tracks';
import { EventRef } from '../event-ref/event-ref';
import { SANRING_TABS_IMPORTS } from '../../components/ui/tabs';
import { campOf, type Evidence } from '../map/map-style';
import { CitationPopover } from '../citation/citation-popover';

/** 控制區欄位（從 atlas 頁傳入，顯示在面板「概要」分頁的控制區區塊）。 */
export interface ControlZoneSection {
  props: ControlFeatureProperties;
  evidence: Evidence;
  theater: TheaterStateDto | null;
}

const TXT = {
  'zh-Hant': {
    period: '國界期間', status: '性質', deJure: '國界', notSovereign: '非主權（佔領行政區）', start: '起始變動', end: '結束變動',
    none: '本試驗範圍前即存在（不追溯）', open: '本試驗範圍內未結束', camp: '陣營（補充）',
    campNone: '陣營未建置', geometry: '國界來源', license: '幾何授權', osm: '含 OpenStreetMap 來源線段（ODbL）', close: '關閉',
    campNote: '陣營只作補充，不影響填色', until: '至',
    conflicts: '相關衝突（當日進行中）', noConflicts: '當日沒有進行中的衝突', events: '事件', noEvents: '沒有相關事件',
    loading: '載入中…', tabOverview: '概要', note: '註記', tabEvents: '事件', tabsLabel: '政權資訊分頁', loadError: '事件載入失敗', jump: '跳到此日', now: '目前日期', appended: '事後追加', appendedAt: '追加於',
    capital: '首都', capitalNone: '無資料',
    tabLeaders: '領導人', leadersNone: '無資料', leaderUnverified: '待查證',
    leaderRole: { head_of_state: '國家元首', head_of_government: '政府首腦' } as Record<string, string>,
    occ: { annexed: '併入', civil_administration: '佔領', military_administration: '佔領' } as Record<string, string>,
    occSuffix: '（非主權）',
    kind: { annexed: '併入（正式或事實；國際未承認割讓）', civil_administration: '民政管理（帝國專員轄區、保護國、總督府等）', military_administration: '軍事管理' } as Record<string, string>,
    occupation: '佔領', occKind: '控制程度', occBasis: '依據', occPending: '待查證（依據事件尚無合格出處）', occNoBasis: '待查證（尚無依據事件）', coOccupied: '共同佔領：缺分區幾何，標示主要佔領方',
    role: { belligerent: '交戰方', signatory: '簽署方', other: '相關', border_start: '國界起始', border_end: '國界結束', conflict_start: '開戰', conflict_end: '停戰／投降' } as Record<string, string>,
    controlZone: '控制區',
    czEvidence: '史料狀態', czPeriod: '有效期間', czTheater: '戰區', czCamp: '陣營',
    czCampBasis: '依據', czCampNone: '陣營未建置', czSupplement: '補充', czDisputed: '爭議領土',
    czUncertain: '不確定', czAttested: '已查證', czInterp: '非史料', czOutside: '不在有效區間', czUnknown: '不明',
  },
  en: {
    period: 'Valid', status: 'Status', deJure: 'Border', notSovereign: 'Not sovereign (occupation administration)', start: 'Began with', end: 'Ended with',
    none: 'Existed before this trial (not traced)', open: 'Not ended within this trial', camp: 'Camp (supplement)',
    campNone: 'Camp not set', geometry: 'Border source', license: 'Geometry licence', osm: 'Contains OpenStreetMap-derived segments (ODbL)', close: 'Close',
    campNote: 'Camp is supplementary and does not affect fill', until: 'to',
    conflicts: 'Conflicts (ongoing on this date)', noConflicts: 'No ongoing conflict on this date', events: 'Events', noEvents: 'No related events',
    loading: 'Loading…', tabOverview: 'Overview', note: 'Note', tabEvents: 'Events', tabsLabel: 'Regime details', loadError: 'Could not load events', jump: 'Go to this date', now: 'Current date', appended: 'Added later', appendedAt: 'added',
    capital: 'Capital', capitalNone: 'No data',
    tabLeaders: 'Leaders', leadersNone: 'No data', leaderUnverified: 'Unverified',
    leaderRole: { head_of_state: 'Head of State', head_of_government: 'Head of Gov\'t' } as Record<string, string>,
    occ: { annexed: 'annexation', civil_administration: 'occupation', military_administration: 'occupation' } as Record<string, string>,
    occSuffix: ' (not sovereign)',
    kind: { annexed: 'Annexed (formal or de facto; not internationally recognised)', civil_administration: 'Civil administration (Reichskommissariat, protectorate, General Government…)', military_administration: 'Military administration' } as Record<string, string>,
    occupation: 'Occupation', occKind: 'Control', occBasis: 'Basis', occPending: 'Pending (basis event has no qualified source)', occNoBasis: 'Pending (no basis event)', coOccupied: 'Joint occupation: no zone geometry, main occupier shown',
    role: { belligerent: 'Belligerent', signatory: 'Signatory', other: 'Related', border_start: 'Border begins', border_end: 'Border ends', conflict_start: 'War begins', conflict_end: 'War ends' } as Record<string, string>,
    controlZone: 'Control zone',
    czEvidence: 'Evidence', czPeriod: 'Valid period', czTheater: 'Theater', czCamp: 'Camp',
    czCampBasis: 'Basis', czCampNone: 'Camp not set', czSupplement: 'Supplement', czDisputed: 'Disputed',
    czUncertain: 'uncertain', czAttested: 'Attested', czInterp: 'Not attested', czOutside: 'Outside range', czUnknown: 'Unknown',
  },
} as const;
export type SovereigntyTab = 'overview' | 'events' | 'leaders';
/** 佔領方簡稱（面板性質用：「德國佔領（非主權）」）；沒列的用政權名。 */
const OCCUPIER_SHORT: Record<string, { 'zh-Hant': string; en: string }> = {
  'deutsches-reich': { 'zh-Hant': '德國', en: 'German' }, 'kingdom-of-italy': { 'zh-Hant': '義大利', en: 'Italian' },
  'kingdom-of-romania': { 'zh-Hant': '羅馬尼亞', en: 'Romanian' }, 'tsardom-of-bulgaria': { 'zh-Hant': '保加利亞', en: 'Bulgarian' },
  'united-states-of-america': { 'zh-Hant': '美國', en: 'US' }, 'united-kingdom': { 'zh-Hant': '英國', en: 'British' },
  'soviet-union': { 'zh-Hant': '蘇聯', en: 'Soviet' }, 'empire-of-japan': { 'zh-Hant': '日本', en: 'Japanese' },
};
const CAMP_NAME: Record<string, { 'zh-Hant': string; en: string }> = {
  axis: { 'zh-Hant': '軸心', en: 'Axis' }, allies: { 'zh-Hant': '同盟', en: 'Allies' },
  cobelligerent: { 'zh-Hant': '共同交戰／合作', en: 'Co-belligerent' }, neutral: { 'zh-Hant': '中立／未結盟', en: 'Neutral' },
};

/**
 * 主權圖層（國界）資訊卡：政權名、國界期間、起訖疆界變動事件（同一結構：事件名稱、日期、查證狀態、出處；
 * 出處預設只顯示簡短引用，點一下展開完整書目；沒有正式出處就標「待查證」，不補造）、
 * 國界幾何來源（OHM 關係 id／版本、授權、署名），陣營只在這裡作補充。
 */
@Component({
  selector: 'wl-sovereignty-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideX, EventRef, NgTemplateOutlet, CitationPopover, ...SANRING_TABS_IMPORTS],
  template: `
    <article data-testid="sovereignty-card" [class]="embedded() ? 'flex min-h-0 flex-1 flex-col' : 'wl-paper flex max-h-[inherit] min-h-0 w-[340px] flex-col p-4'"
      [attr.role]="embedded() ? null : 'dialog'" [attr.aria-label]="embedded() ? null : regimeName()" [attr.data-layer-status]="props().layerStatus">
      @if (!embedded()) {
      <header class="flex flex-none items-start justify-between gap-2 border-b border-wl-outline-variant pb-2">
        <div>
          <h2 class="wl-title2" data-testid="sovereignty-card-title">{{ regimeName() }}</h2>
          @if (originalName()) { <p class="wl-text2 text-wl-on-surface-variant" [attr.lang]="originalLang() || null">{{ originalName() }}</p> }
        </div>
        <button type="button" class="wl-icon-btn" [attr.aria-label]="t().close" (click)="closed.emit()"><svg lucideX class="size-4"></svg></button>
      </header>
      }
      @if (embedded()) {
      <!-- 分頁（sanring Tabs，底層 @angular/aria：tablist／tab／tabpanel、方向鍵、Home／End）：概要＝性質、期間、起訖變動、陣營、國界來源與相關衝突；事件＝時間線 -->
      <sanring-tabs variant="line" class="flex min-h-0 flex-1 flex-col gap-0" [defaultValue]="tab()" (valueChange)="onTab($event)">
        <sanring-tabs-list class="w-full flex-none" selectionMode="follow" [wrap]="true" [attr.aria-label]="t().tabsLabel">
          <sanring-tabs-trigger value="overview" data-testid="sovereignty-card-tab-overview">{{ t().tabOverview }}</sanring-tabs-trigger>
          <sanring-tabs-trigger value="events" data-testid="sovereignty-card-tab-events">{{ t().tabEvents }}
            @if (eventsStatus() === 'ok' && (regimeEvents()?.length ?? 0) > 0) {
              <span data-testid="sovereignty-card-tab-events-count" class="rounded-sm bg-wl-surface-container-high px-1 text-[11px] tabular-nums text-wl-on-surface-variant">{{ regimeEvents()?.length }}</span>
            }
          </sanring-tabs-trigger>
          <sanring-tabs-trigger value="leaders" data-testid="sovereignty-card-tab-leaders">{{ t().tabLeaders }}</sanring-tabs-trigger>
        </sanring-tabs-list>
        <div data-testid="sovereignty-card-body" class="min-h-0 flex-1 overflow-y-auto overscroll-contain pr-1">
          <sanring-tabs-content value="overview" class="mt-3">
            <div data-testid="sovereignty-card-panel-overview">
              <ng-container *ngTemplateOutlet="overview" />
        <!-- 相關衝突：與地圖上的雙劍同一份資料；點一項切到衝突詳情 -->
        <section data-testid="sovereignty-card-conflicts" class="mt-4 border-t border-wl-outline-variant pt-3">
          <h3 class="wl-sub-title mb-1.5">{{ t().conflicts }}</h3>
          @for (c of conflicts(); track c.recordId) {
            <button type="button" data-testid="sovereignty-card-conflict" [attr.data-record-id]="c.recordId"
              class="mb-1 flex w-full items-center gap-2 rounded-[var(--sanring-radius-xs)] border border-wl-outline-variant px-2 py-1.5 text-left wl-text2 hover:bg-wl-surface-container-high"
              (click)="conflictSelect.emit(c.recordId)">
              <svg viewBox="0 0 32 32" class="size-4 flex-none text-wl-error" fill="currentColor" aria-hidden="true"><path d="M27.5 4.5 L25.8 9 L12.2 22.6 L9.4 19.8 L23 6.2 Z M4.5 4.5 L9 6.2 L22.6 19.8 L19.8 22.6 L6.2 9 Z" /></svg>
              <span class="min-w-0 flex-1">{{ c.title }}</span>
              <span class="flex-none text-wl-on-surface-variant tabular-nums">{{ c.since }}</span>
            </button>
          } @empty {
            <p class="wl-text2 text-wl-on-surface-variant">{{ t().noConflicts }}</p>
          }
        </section>
            </div>
          </sanring-tabs-content>
          <sanring-tabs-content value="leaders" class="mt-3">
            <div data-testid="sovereignty-card-panel-leaders">
              @if (sortedLeaders().length === 0) {
                <p class="wl-text2 text-wl-on-surface-variant">{{ t().leadersNone }}</p>
              } @else {
                <ul class="space-y-3">
                  @for (leader of sortedLeaders(); track leader.recordId) {
                    <li data-testid="sovereignty-card-leader" class="wl-text2">
                      <div class="flex items-start gap-2">
                        <span class="rounded-sm bg-wl-surface-container-high px-1 text-[11px] text-wl-on-surface-variant flex-none" [attr.data-role]="leader.role">{{ t().leaderRole[leader.role] ?? leader.role }}</span>
                        <div class="min-w-0 flex-1">
                          <div class="font-semibold" data-testid="sovereignty-card-leader-name">{{ leaderName(leader) }}</div>
                          <div class="text-wl-on-surface-variant" data-testid="sovereignty-card-leader-title">{{ leader.title }}</div>
                          @if (!leader.verified) {
                            <span data-testid="sovereignty-card-leader-unverified" class="text-[11px] text-wl-on-surface-variant">{{ t().leaderUnverified }}</span>
                          }
                          @if (leader.source) {
                            <div data-testid="sovereignty-card-leader-source" class="text-[11px] text-wl-on-surface-variant">{{ leader.source }}</div>
                          }
                        </div>
                      </div>
                    </li>
                  }
                </ul>
              }
            </div>
          </sanring-tabs-content>
          <sanring-tabs-content value="events" class="mt-3">
            <div data-testid="sovereignty-card-panel-events">
        <!-- 事件時間線：與此政權相關、有日期的事件（結構同起訖變動：名稱 → 日期 → 查證＋出處）；點日期跳到該日 -->
        <section data-testid="sovereignty-card-timeline" class="">
          <h3 class="sr-only">{{ t().events }}</h3>
          @switch (eventsStatus()) {
            @case ('loading') { <p class="wl-text2 text-wl-on-surface-variant">{{ t().loading }}</p> }
            @case ('error') { <p class="wl-text2 text-wl-error">{{ t().loadError }}</p> }
            @default {
              <ol class="relative ml-1 border-l border-wl-outline-variant">
                @for (e of timeline(); track e.ev.id) {
                  <li data-testid="sovereignty-card-timeline-item" [attr.data-event-id]="e.ev.id" [attr.data-when]="e.when" class="relative mb-3 pl-4 wl-text2"
                    [class.opacity-60]="e.when === 'future'">
                    <span class="absolute -left-[5px] top-1.5 size-2.5 rounded-full border border-wl-outline" [class.bg-wl-secondary]="e.when === 'now'" [class.bg-wl-surface]="e.when !== 'now'" aria-hidden="true"></span>
                    <div class="mb-0.5 flex flex-wrap items-center gap-1.5">
                      <button type="button" data-testid="sovereignty-card-timeline-jump" class="tabular-nums font-semibold underline decoration-dotted underline-offset-2 hover:text-wl-secondary"
                        [attr.aria-label]="t().jump + ' ' + e.ev.occurred.start" (click)="eventJump.emit(e.ev.occurred.start ?? '')">{{ e.ev.occurred.start }}</button>
                      @for (r of e.roles; track r) { <span class="rounded-sm bg-wl-surface-container-high px-1 text-[11px] text-wl-on-surface-variant">{{ r }}</span> }
                      @if (e.when === 'now') { <span class="text-[11px] text-wl-secondary">{{ t().now }}</span> }
                    </div>
                    <wl-event-ref [ev]="e.ev" prefix="sovereignty-card-timeline" [lang]="lang()" />
                    @for (a of e.additions; track a.role) {
                      <!-- 事後追加的參與方（方案 A）：角色、追加日期、理由；原有參與方與引用不變 -->
                      <p data-testid="sovereignty-card-timeline-addition" [attr.data-role]="a.role" class="mt-1 rounded-sm border-l-2 border-wl-outline pl-2 text-[11px] text-wl-on-surface-variant">
                        <span class="font-semibold">{{ t().appended }}・{{ a.roleText }}</span>
                        <span class="tabular-nums">（{{ t().appendedAt }} {{ a.addedOn }}）</span>
                        @if (a.note) { <span class="block">{{ a.note }}</span> }
                      </p>
                    }
                  </li>
                } @empty {
                  <li class="pl-4 wl-text2 text-wl-on-surface-variant">{{ t().noEvents }}</li>
                }
              </ol>
            }
          }
        </section>
            </div>
          </sanring-tabs-content>
        </div>
      </sanring-tabs>
      } @else {
      <div data-testid="sovereignty-card-body" class="mt-2 min-h-0 overflow-y-auto overscroll-contain pr-1">
        <ng-container *ngTemplateOutlet="overview" />
      </div>
      }
      <ng-template #overview>
      @if (controlZone(); as cz) {
        <!-- 控制區欄位：史料狀態、有效期間、戰區、陣營＋依據、補充（預設收合）、爭議 -->
        <section class="mb-4 border-b border-wl-outline-variant pb-4">
          <h3 class="wl-sub-title mb-2">{{ t().controlZone }}</h3>
          <dl class="grid grid-cols-[72px_1fr] gap-x-2 gap-y-1.5 wl-text2">
            <dt class="text-wl-on-surface-variant">{{ t().czEvidence }}</dt>
            <dd data-testid="feature-card-evidence">
              @if (czEvidence() === 'attested') {
                <span class="wl-stamp">{{ t().czAttested }} {{ czAttestedDate() }}</span>
              } @else {
                <span class="wl-chip-interp">{{ czEvidenceText() }}</span>
              }
            </dd>
            <dt class="text-wl-on-surface-variant">{{ t().czPeriod }}</dt>
            <dd>{{ czPeriod() }}
              @if (czUncertainty(); as u) { <div class="text-wl-on-surface-variant">{{ u }}</div> }
            </dd>
            <dt class="text-wl-on-surface-variant">{{ t().czTheater }}</dt>
            <dd>{{ czTheater() }}</dd>
            <dt class="text-wl-on-surface-variant">{{ t().czCamp }}</dt>
            <dd data-testid="feature-card-camp" [attr.data-camp]="czCamp() ?? 'unassigned'">
              @if (cz.props.controllerAlignment; as al) {
                {{ czCampLabel() }}（{{ czAlignmentPeriod() }}）
                @for (c of czPrimaryAlignmentCitations(); track c.sourceId + c.locator) {
                  <div class="text-wl-on-surface-variant" data-testid="feature-card-camp-basis">{{ t().czCampBasis }}：{{ c.sourceTitle }}，{{ c.locator }}</div>
                }
              } @else {
                <span class="text-wl-on-surface-variant">{{ t().czCampNone }}</span>
              }
            </dd>
            @if (czSupplements().length > 0) {
              <dt class="text-wl-on-surface-variant">
                <span class="wl-badge" data-testid="feature-card-supplement-label">{{ t().czSupplement }}</span>
              </dt>
              <dd data-testid="feature-card-supplements">
                <details>
                  <summary class="cursor-pointer text-wl-on-surface-variant wl-text2">（{{ czSupplements().length }}）</summary>
                  @for (e of czSupplements(); track e.eventId) {
                    <div class="mt-1" data-testid="feature-card-supplement">
                      <span>{{ e.date }}　{{ e.summary }}</span>
                      @for (c of e.citations; track c.sourceId + c.locator) {
                        <div class="text-wl-on-surface-variant">{{ t().czCampBasis }}：{{ c.sourceTitle }}，{{ c.locator }}</div>
                      }
                    </div>
                  }
                </details>
              </dd>
            }
            @if (cz.props.isDisputed) {
              <dt class="text-wl-on-surface-variant"></dt><dd><span class="wl-badge">{{ t().czDisputed }}</span></dd>
            }
          </dl>
          <footer class="mt-2 flex justify-end">
            <wl-citation-popover [citations]="cz.props.citations" [lang]="lang()" />
          </footer>
        </section>
      }
      <dl class="grid grid-cols-[76px_1fr] gap-x-2 gap-y-1.5 wl-text2">
        <dt class="text-wl-on-surface-variant">{{ t().status }}</dt>
        <dd data-testid="sovereignty-card-status" [attr.data-control-kind]="occupation()?.controlKind ?? null">{{ statusText() }}</dd>
        @if (occupation(); as o) {
          <!-- 佔領歸屬：佔領方、控制程度、依據事件（沒有合格出處＝待查證）、共同佔領註記 -->
          <dt class="text-wl-on-surface-variant">{{ t().occKind }}</dt>
          <dd data-testid="sovereignty-card-occupation" class="min-w-0">
            <div>{{ t().kind[o.controlKind] ?? o.controlKind }}</div>
            @if (o.coOccupied) { <div data-testid="sovereignty-card-co-occupied" class="text-wl-on-surface-variant">{{ t().coOccupied }}</div> }
            @if (occNote(); as n) { <div class="text-wl-on-surface-variant whitespace-pre-line">{{ n }}</div> }
          </dd>
          <dt class="text-wl-on-surface-variant">{{ t().occBasis }}</dt>
          <dd data-testid="sovereignty-card-occupation-basis" class="min-w-0" [attr.data-verification]="o.verification">
            @if (o.basisEvent; as ev) {
              <wl-event-ref [ev]="ev" prefix="sovereignty-card-occupation" [lang]="lang()" />
            } @else { <span class="text-wl-on-surface-variant">{{ t().occNoBasis }}</span> }
          </dd>
        }
        <dt class="text-wl-on-surface-variant">{{ t().period }}</dt>
        <dd>{{ props().validPeriod.start }} {{ t().until }} {{ props().validPeriod.end ?? '—' }}</dd>
        <dt class="text-wl-on-surface-variant">{{ t().capital }}</dt>
        <dd data-testid="sovereignty-card-capital">
          @if (capital(); as cap) {
            <span data-testid="sovereignty-card-capital-name">{{ capitalName() }}</span>
            @if (cap.sourceRef) { <span class="block text-[11px] text-wl-on-surface-variant" data-testid="sovereignty-card-capital-source">{{ cap.sourceRef }}</span> }
          } @else {
            <span class="text-wl-on-surface-variant" data-testid="sovereignty-card-capital-none">{{ t().capitalNone }}</span>
          }
        </dd>
        @if (noteText(); as n) {
          <dt class="text-wl-on-surface-variant">{{ t().note }}</dt>
          <dd data-testid="sovereignty-card-note" class="min-w-0 whitespace-pre-line">{{ n }}</dd>
        }
        @for (row of events(); track row.key) {
          <dt class="text-wl-on-surface-variant">{{ row.label }}</dt>
          <dd [attr.data-testid]="'sovereignty-card-' + row.key" class="min-w-0">
            @if (row.ev; as ev) {
              <!-- 起始／結束變動同一結構：事件名稱 → 日期 → 查證狀態＋出處（Tai 2026-10-31；與衝突卡共用 wl-event-ref） -->
              <wl-event-ref [ev]="ev" prefix="sovereignty-card" [lang]="lang()" />
            } @else {
              <span class="text-wl-on-surface-variant">{{ row.key === 'start' ? t().none : t().open }}</span>
            }
          </dd>
        }
        <dt class="text-wl-on-surface-variant">{{ t().camp }}</dt>
        <dd data-testid="sovereignty-card-camp" [attr.data-camp]="camp() ?? 'unassigned'">
          {{ campText() }}
          <div class="text-wl-on-surface-variant">{{ t().campNote }}</div>
        </dd>
        <dt class="text-wl-on-surface-variant">{{ t().geometry }}</dt>
        <dd data-testid="sovereignty-card-geometry">
          <div>{{ props().geometry.sourceTitle }}</div>
          <div class="text-wl-on-surface-variant">{{ props().geometry.locator }}</div>
          <div class="text-wl-on-surface-variant">{{ t().license }}：{{ props().geometry.geometryLicense }}@if (props().geometry.attribution; as a) {；{{ a }}}</div>
          @if (osmDerived()) { <div class="text-wl-on-surface-variant" data-testid="sovereignty-card-osm">{{ t().osm }}</div> }
        </dd>
      </dl>
      </ng-template>
    </article>
  `,
})
export class SovereigntyCard {
  readonly props = input.required<SovereigntyFeatureProperties>();
  readonly regimeName = input('');
  readonly originalName = input('');
  readonly originalLang = input('');
  /** 佔領方政權名（沒有簡稱時用） */
  readonly occupierName = input('');
  readonly lang = input<Lang>('zh-Hant');
  /** 放在側邊面板（wl-regime-sheet）裡：不畫紙卡外框與標題列（標題、關閉鈕由面板提供）。 */
  readonly embedded = input(false);
  /** 當日與此政權相關的衝突（地圖雙劍同一份）。 */
  readonly conflicts = input<{ recordId: string; title: string; since: string }[]>([]);
  readonly regimeEvents = input<RegimeEventDto[] | null>(null);
  readonly eventsStatus = input<'idle' | 'loading' | 'ok' | 'error'>('idle');
  /** 目前日期：時間線標示「目前」（最後一個不晚於此日的事件）與之後的事件。 */
  readonly currentDate = input('');
  /** 該政權在當前日期的首都記錄（由頁面從 capitals 圖層資料取出，不額外請求）。 */
  readonly capital = input<CapitalRecord | null>(null);
  /** 該政權在當前日期的領導人列表（由頁面從 leaders 資料過濾，不額外請求）。 */
  readonly leaders = input<LeaderRecord[]>([]);
  /** 目前分頁（embedded 時）：由頁面保存，切換政權時保留（例如連續比較各政權的事件），面板關閉後回到「概要」。 */
  readonly tab = input<SovereigntyTab>('overview');
  /** 控制區欄位（點控制區開面板時由頁面傳入，在概要分頁頂部顯示）。 */
  readonly controlZone = input<ControlZoneSection | null>(null);
  readonly tabChange = output<SovereigntyTab>();
  readonly closed = output<void>();
  readonly conflictSelect = output<string>();
  readonly eventJump = output<string>();
  protected onTab(v: string) {
    if (v === 'overview' || v === 'events' || v === 'leaders') this.tabChange.emit(v);
  }

  // ── 控制區 computeds ────────────────────────────────────────────────────────
  protected readonly czEvidence = computed(() => this.controlZone()?.evidence ?? 'unknown');
  protected readonly czAttestedDate = computed(() => this.controlZone()?.theater?.attestingSnapshot?.asOf ?? '');
  protected readonly czEvidenceText = computed(() => {
    const cz = this.controlZone();
    if (!cz) return '';
    const s = cz.theater;
    switch (cz.evidence) {
      case 'interpolated': return `${this.t().czInterp}：${s?.prevSnapshot?.asOf ?? '?'} → ${s?.nextSnapshot?.asOf ?? '?'}`;
      case 'outside': return this.t().czOutside;
      default: return this.t().czUnknown;
    }
  });
  /** 區間字串（半開 [start, end)）。 */
  private czPeriodStr(p: { start?: string | null; end?: string | null } | null | undefined): string {
    if (!p) return '';
    return `${p.start ?? '…'} – ${p.end ?? '…'}`;
  }
  protected readonly czPeriod = computed(() => this.czPeriodStr(this.controlZone()?.props.validPeriod));
  protected readonly czUncertainty = computed(() => {
    const v = this.controlZone()?.props.validPeriod;
    if (!v) return '';
    const parts: string[] = [];
    const u = this.t().czUncertain;
    const en = this.lang() === 'en';
    if (v.startUncertainty) parts.push(`${en ? 'start' : '起'} ${u} ${this.czPeriodStr(v.startUncertainty)}`);
    if (v.endUncertainty) parts.push(`${en ? 'end' : '迄'} ${u} ${this.czPeriodStr(v.endUncertainty)}`);
    return parts.join('；');
  });
  protected readonly czTheater = computed(() => {
    const cz = this.controlZone();
    return cz ? theaterLabel(cz.props.theaterCode, this.lang()) : '';
  });
  protected readonly czCamp = computed(() => campOf(this.controlZone()?.props.controllerAlignment ?? null));
  protected readonly czCampLabel = computed(() => {
    const c = this.czCamp();
    return c ? (CAMP_NAME[c]?.[this.lang() === 'en' ? 'en' : 'zh-Hant'] ?? c) : this.t().czCampNone;
  });
  protected readonly czAlignmentPeriod = computed(() =>
    this.czPeriodStr(this.controlZone()?.props.controllerAlignment?.validPeriod),
  );
  protected readonly czPrimaryAlignmentCitations = computed(
    () => this.controlZone()?.props.controllerAlignment?.citations.filter((c) => c.role === 'primary') ?? [],
  );
  /** 只列 occurred.start <= currentDate 的補充，預設收合在 <details>。 */
  protected readonly czSupplements = computed(() => {
    const cz = this.controlZone();
    if (!cz) return [];
    const date = this.currentDate();
    return (cz.props.controllerSupplements ?? [])
      .filter((e) => !date || (e.occurred.start ?? '') <= date)
      .map((e) => ({
        eventId: e.eventId,
        date: e.occurred.start ?? '',
        summary: localized(e.summary as Record<string, string> | null, this.lang()).text,
        citations: e.citations,
      }));
  });
  // ── end 控制區 computeds ─────────────────────────────────────────────────────

  protected readonly timeline = computed(() => {
    const d = this.currentDate();
    const list = this.regimeEvents() ?? [];
    let nowIdx = -1;
    list.forEach((e, i) => {
      if (d && (e.occurred.start ?? '') <= d) nowIdx = i;
    });
    return list.map((ev, i) => ({
      ev,
      roles: [...new Set(ev.roles.map((r) => this.t().role[r] ?? r))],
      additions: (ev.additions ?? []).map((a) => ({
        role: a.role,
        roleText: this.t().role[a.role] ?? a.role,
        addedOn: (a.addedAt ?? '').slice(0, 10),
        note: a.note ? ((this.lang() === 'en' ? a.note['en'] || a.note['zh-Hant'] : a.note['zh-Hant'] || a.note['en']) ?? '') : '',
      })),
      when: (i === nowIdx ? 'now' : i < nowIdx ? 'past' : 'future') as 'past' | 'now' | 'future',
    }));
  });

  protected readonly sortedLeaders = computed(() =>
    [...this.leaders()].sort((a, b) => {
      const order: Record<string, number> = { head_of_state: 0, head_of_government: 1 };
      return (order[a.role] ?? 2) - (order[b.role] ?? 2);
    }),
  );
  protected leaderName(l: LeaderRecord): string {
    return (this.lang() === 'en' ? l.name : l.nameZh || l.name) || l.name;
  }
  protected readonly capitalName = computed(() => {
    const cap = this.capital();
    if (!cap) return '';
    const n = cap.cityName;
    return (this.lang() === 'en' ? n.en || n['zh-Hant'] : n['zh-Hant'] || n.en) ?? '';
  });
  protected readonly t = computed(() => TXT[this.lang() === 'en' ? 'en' : 'zh-Hant']);
  protected readonly occupation = computed(() => this.props().occupation ?? null);
  /** 性質：一般國界／非主權；有佔領歸屬時顯示「德國佔領（非主權）」「德國併入（非主權）」 */
  protected readonly statusText = computed(() => {
    const p = this.props();
    const o = this.occupation();
    if (o) {
      const en = this.lang() === 'en';
      const who = OCCUPIER_SHORT[o.occupierSlug]?.[en ? 'en' : 'zh-Hant'] ?? (this.occupierName() || o.occupierSlug);
      return en ? `${who} ${this.t().occ[o.controlKind] ?? 'occupation'}${this.t().occSuffix}` : `${who}${this.t().occ[o.controlKind] ?? '佔領'}${this.t().occSuffix}`;
    }
    return p.layerStatus === 'not_sovereign' ? this.t().notSovereign : this.t().deJure;
  });
  protected readonly occNote = computed(() => {
    const n = this.occupation()?.note;
    if (!n) return '';
    const v = (this.lang() === 'en' ? n['en'] || n['zh-Hant'] : n['zh-Hant'] || n['en']) ?? '';
    return v.startsWith('Occupation attribution (see') ? n['zh-Hant'] ?? '' : v;
  });
  protected readonly camp = computed(() => campOf(this.props().regimeAlignment ?? null));
  protected readonly campText = computed(() => {
    const c = this.camp();
    return c ? CAMP_NAME[c][this.lang() === 'en' ? 'en' : 'zh-Hant'] : this.t().campNone;
  });
  protected readonly events = computed(() => [
    { key: 'start', label: this.t().start, ev: this.props().startEvent },
    { key: 'end', label: this.t().end, ev: this.props().endEvent },
  ]);
  /** 紀錄註記（幾何簡化、OHM 缺漏等說明）：依介面語言，沒有就用另一語言。 */
  protected readonly noteText = computed(() => {
    const n = (this.props() as unknown as { note?: Record<string, string> | null }).note;
    if (!n) return '';
    return (this.lang() === 'en' ? n['en'] || n['zh-Hant'] : n['zh-Hant'] || n['en']) ?? '';
  });
  protected readonly osmDerived = computed(() => {
    const f = this.props().geometry.flags as unknown as { osmDerivedWayCount?: number } | null;
    return (f?.osmDerivedWayCount ?? 0) > 0;
  });
}
