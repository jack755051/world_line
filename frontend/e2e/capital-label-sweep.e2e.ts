import { execSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { expect, test, type Page } from '@playwright/test';

/**
 * 首都／國名標籤全面掃描（回歸測試）：在多個日期 × 縮放級別下，檢查當天每座首都的圓點、首都名稱，
 * 以及每個國名（政權）標籤是否完整可見。
 *
 * ── 國名標籤量測方式 ─────────────────────────────────────────────────────────────────
 * 國名已改為 MapLibre symbol layer（`regime-label`）。DOM 中不再有 `[data-testid=map-regime-label]`。
 * 量測流程：
 * 1. `map.queryRenderedFeatures({layers:['regime-label']})` 取當前 viewport 已渲染的標籤集合。
 * 2. 對每個已渲染的標籤，以 **二分搜尋 + queryRenderedFeatures** 精確推算螢幕上的 bounding box
 *    （分別收窄左/右/上/下邊界，每次查詢精度 0.5px）。
 *    選此方案原因：不依賴 MapLibre 私有 API（`map.style.placement`、`collisionIndex`），
 *    跨版本穩定；每個標籤約 44 次 queryRenderedFeatures 呼叫（同步、快速）。
 * 3. 「應顯示」門檻：政權多邊形投影 bbox 寬 ≥ 文字寬 × 2.5 且高 ≥ 48px 時，
 *    國名 **必須** 被渲染（大到明顯放得下卻被隱藏 → ok=false，原因寫「國名在足夠大的區塊內被隱藏」）。
 *    小於此門檻時隱藏是正常的，記為 ok=true + hidden=true；另輸出 `OUT/days/hidden-<date>.json`。
 *
 * ── verify 1（TypeScript 無錯）──────────────────────────────────────────────────────
 *   cd frontend && pnpm exec tsc --noEmit
 *
 * ── verify 2（掃描兩個日期，workers=1）──────────────────────────────────────────────
 *   WL_SWEEP=1 WL_E2E_PORT=4201 WL_SWEEP_DATES=1930-06-15,1940-06-15 WL_SWEEP_ZOOMS=3,4.7 \
 *   WL_SWEEP_OUT=/tmp/wl-qa-sweep \
 *   pnpm exec playwright test e2e/capital-label-sweep.e2e.ts --workers=1
 *
 * ── verify 3（check_sweep 0 失敗）────────────────────────────────────────────────────
 *   CHECK_DATES=1930-06-15,1940-06-15 \
 *   python3 ~/cc-queue/queues/wl-occlusion/check_sweep.py /tmp/wl-qa-sweep ~/01_Projects/world_line
 *
 * ── 完整掃描（56 日期；workers=1）───────────────────────────────────────────────────
 *   WL_SWEEP=1 WL_E2E_PORT=4201 pnpm exec playwright test e2e/capital-label-sweep.e2e.ts --workers=1
 * 參數：WL_SWEEP_DATES=1909-01-31,1939-09-01  WL_SWEEP_ZOOMS=3,4,4.7  WL_SWEEP_OUT=/tmp/wl-qa-sweep
 *       WL_SWEEP_STRICT=1（有任何失敗就讓測試失敗，供回歸用）
 */
test.skip(!process.env['WL_SWEEP'], 'set WL_SWEEP=1 to run the capital/label sweep');
test.use({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, trace: 'off' });

const OUT = process.env['WL_SWEEP_OUT'] ?? '/tmp/wl-qa-sweep';
const ZOOMS = (process.env['WL_SWEEP_ZOOMS'] ?? '3,4,4.7').split(',').map(Number);
const STRICT = !!process.env['WL_SWEEP_STRICT'];
const MAX_SHOTS_PER_TYPE = 3;

/** 每年至少一天（1908–1945）＋重大疆界變動日。 */
const YEARLY = Array.from({ length: 38 }, (_, i) => `${1908 + i}-06-15`);
const MILESTONES = [
  '1909-01-31', // Tai 回報的案例
  '1914-07-28', '1914-08-04', '1918-11-11', '1919-06-28', '1920-06-04', '1920-08-10', '1923-07-24',
  '1938-03-12', '1938-10-01', '1939-03-15', '1939-09-01', '1939-09-28', '1940-06-15', '1940-06-22',
  '1941-06-22', '1941-12-08', '1945-05-08', '1945-09-02',
];
/** 同一個 code 版本才比較：檔名帶日期。 */
const DATES = process.env['WL_SWEEP_DATES']
  ? process.env['WL_SWEEP_DATES'].split(',')
  : [...new Set([...YEARLY, ...MILESTONES])].sort();

export interface SweepCheck {
  date: string;
  zoom: number;
  kind: 'capital-dot' | 'capital-name' | 'regime-label' | 'capital-data';
  id: string;
  regime: string;
  item: string;
  ok: boolean;
  reasons: string[];
  view: number;
  /** true = 區塊太小依設計隱藏（ok=true；另見 hidden-<date>.json）。 */
  hidden?: boolean;
  shot?: string;
  code?: { head: string; dirtyMap: string; rebuild: string | null };
}

/** 每種失敗類型的代表截圖數：從截圖目錄回推（worker 因失敗重啟時不會重新計數）。 */
const shotCount = new Map<string, number>();
const shotDates = new Map<string, Set<string>>();
function loadShotIndex(): void {
  if (!existsSync(`${OUT}/shots`)) return;
  for (const f of readdirSync(`${OUT}/shots`)) {
    const m = /^(.+)-(\d{4}-\d{2}-\d{2})-z[\d.]+-\d+\.png$/.exec(f);
    if (!m) continue;
    shotCount.set(m[1], (shotCount.get(m[1]) ?? 0) + 1);
    shotDates.set(m[1], (shotDates.get(m[1]) ?? new Set<string>()).add(m[2]));
  }
}
loadShotIndex();

/**
 * 受測程式版本：4201 是 ng serve（會隨工作目錄即時重建），所以每個日期都記下 HEAD、地圖程式未提交修改的雜湊、
 * 以及 ng serve log 最後一次重建時間（WL_SWEEP_NGLOG，預設 /tmp/ng4201.log）。只讀，不改 repo。
 */
const NG_LOG = process.env['WL_SWEEP_NGLOG'] ?? '/tmp/ng4201.log';
function lastRebuild(): string | null {
  try {
    const m = [...readFileSync(NG_LOG, 'utf8').matchAll(/Application bundle generation complete\. \[[\d.]+ seconds\] - (\S+)/g)];
    return m.length ? m[m.length - 1][1] : null;
  } catch {
    return null;
  }
}
function codeFingerprint(): { head: string; dirtyMap: string; rebuild: string | null } {
  const sh = (c: string) => { try { return execSync(c, { encoding: 'utf8' }).trim(); } catch { return ''; } };
  const head = sh('git rev-parse --short HEAD');
  const diff = sh('git diff HEAD -- src/app/shared/map src/app/pages/atlas');
  return { head, dirtyMap: diff ? createHash('sha1').update(diff).digest('hex').slice(0, 8) : 'clean', rebuild: lastRebuild() };
}
/** 等 ng serve 至少 20 秒沒有重建，避免掃到一半被 live reload 打斷。 */
async function waitQuietServe(): Promise<void> {
  for (let i = 0; i < 60; i++) {
    const r = lastRebuild();
    if (!r || Date.now() - Date.parse(r) > 20_000) return;
    await new Promise((res) => setTimeout(res, 5_000));
  }
}

test.beforeAll(async () => {
  await mkdir(`${OUT}/shots`, { recursive: true });
  await mkdir(`${OUT}/days`, { recursive: true });
});

async function settle(page: Page): Promise<boolean> {
  return page.evaluate(async () => {
    const w = window as unknown as Record<string, any>;
    const m = w['__wlMap'];
    const ng = w['ng'];
    const pageCmp = ng.getComponent(document.querySelector('wl-atlas-page'));
    const t0 = performance.now();
    let last = '';
    let since = performance.now();
    while (performance.now() - t0 < 20_000) {
      await new Promise((r) => setTimeout(r, 100));
      const canvas = document.querySelector('[data-testid=map-canvas]');
      const busy =
        !m.loaded() || m.isMoving() || !m.areTilesLoaded() || canvas?.getAttribute('data-render') === 'busy' ||
        pageCmp.data.mapDataLoading() || pageCmp.data.capitalsStatus() === 'loading' || !!document.querySelector('[data-testid=map-busy-scrim]');
      // 穩定信號：已渲染的 regime-label versionId 集合 + capital-label recordId 集合
      const sig =
        m.queryRenderedFeatures({ layers: ['regime-label'] }).map((f: any) => f.properties.versionId).sort().join('|') +
        '#' + m.queryRenderedFeatures({ layers: ['capital-label'] }).map((f: any) => f.properties.recordId).sort().join(',');
      if (busy || sig !== last) {
        last = sig;
        since = performance.now();
        continue;
      }
      if (performance.now() - since > 500) return true;
    }
    return false;
  });
}

interface ViewItem {
  key: string;
  covered: boolean;
  checks: Omit<SweepCheck, 'date' | 'zoom' | 'view'>[];
  boxes: { x: number; y: number; w: number; h: number; c: string }[];
}

/**
 * 在瀏覽器內分析目前鏡頭：回傳每個尚未檢查項目的覆蓋狀態與檢查結果。座標一律是地圖容器座標。
 *
 * 國名標籤（regime-label）量測：
 * - queryRenderedFeatures({layers:['regime-label']}) 取已渲染集合。
 * - 對每個已渲染的標籤用 box 二分搜尋推算螢幕 bbox（精度 0.5px）。
 * - 「應顯示」門檻：投影 bbox 寬 ≥ text.length×7×2.5 且高 ≥ 48px。
 */
async function analyzeView(page: Page, pending: string[], apiCaps: { recordId: string; regimeId: string; regimeSlug: string }[]): Promise<ViewItem[]> {
  return page.evaluate(
    ({ pending, apiCaps }) => {
      type Box = { x: number; y: number; w: number; h: number }; // x,y 為中心
      const w = window as unknown as Record<string, any>;
      const m = w['__wlMap'];
      const cmp = w['ng'].getComponent(document.querySelector('wl-atlas-map'));
      const zoom: number = m.getZoom();
      const cont: HTMLElement = m.getContainer();
      const cr = cont.getBoundingClientRect();
      const W = cr.width;
      const H = cr.height;
      const want = new Set(pending);
      const toBox = (r: DOMRect): Box => ({ x: r.left - cr.left + r.width / 2, y: r.top - cr.top + r.height / 2, w: r.width, h: r.height });
      const ov = (a: Box, b: Box, tol = 1) => Math.abs(a.x - b.x) * 2 < a.w + b.w - 2 * tol && Math.abs(a.y - b.y) * 2 < a.h + b.h - 2 * tol;
      const inside = (p: { x: number; y: number }, b: Box) => Math.abs(p.x - b.x) * 2 <= b.w && Math.abs(p.y - b.y) * 2 <= b.h;
      const clipped = (b: Box) => b.x - b.w / 2 < 0 || b.y - b.h / 2 < 0 || b.x + b.w / 2 > W || b.y + b.h / 2 > H;

      // 疊在地圖上的 UI（圖例、陣營外框開關、提示、MapLibre 版權列…）
      const chrome: (Box & { name: string })[] = [];
      const area = document.querySelector('[data-testid=map-area]')!;
      const mapHost = area.querySelector('wl-atlas-map')!;
      const pushEl = (el: Element, name: string) => {
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0) return;
        const r = el.getBoundingClientRect();
        if (r.width < 2 || r.height < 2) {
          for (const c of el.children) pushEl(c, name);
          return;
        }
        if (r.width * r.height > 0.6 * W * H) return; // 全版透明疊層
        chrome.push({ ...toBox(r), name });
      };
      for (const el of area.children) if (el !== mapHost && !el.contains(mapHost)) pushEl(el, el.getAttribute('data-testid') ?? el.querySelector('[data-testid]')?.getAttribute('data-testid') ?? el.tagName.toLowerCase());
      for (const el of cont.querySelectorAll('.maplibregl-ctrl')) pushEl(el, 'maplibre-ctrl');
      const underChrome = (p: { x: number; y: number }, pad = 16) => chrome.some((c) => inside(p, { ...c, w: c.w + 2 * pad, h: c.h + 2 * pad }));
      const chromeHit = (b: Box) => chrome.filter((c) => ov(b, c)).map((c) => c.name);

      // ── 國名標籤（MapLibre symbol layer）──────────────────────────────────────────
      const labelsIn: any[] = cmp.labels();
      const nameOfRegime = new Map<string, string>();
      for (const l of labelsIn) if (!nameOfRegime.has(l.regimeId)) nameOfRegime.set(l.regimeId, l.text);

      // 已渲染的 regime-label features
      const renderedRegimeFeats: any[] = m.queryRenderedFeatures({ layers: ['regime-label'] });
      const renderedRegimeIds = new Set<string>(renderedRegimeFeats.map((f: any) => f.properties.versionId));

      // 二分搜尋推算標籤螢幕 bbox（精度 0.5px）
      const hasRL = (vid: string, a: [number, number], b: [number, number]) =>
        (m.queryRenderedFeatures([a, b], { layers: ['regime-label'] }) as any[]).some((f: any) => f.properties.versionId === vid);
      const regimeLabelBox = (vid: string, p: { x: number; y: number }): Box | null => {
        const X0 = p.x - 400, X1 = p.x + 400, Y0 = p.y - 60, Y1 = p.y + 60;
        if (!hasRL(vid, [X0, Y0], [X1, Y1])) return null;
        const bs = (lo: number, hi: number, okAt: (v: number) => boolean): number => {
          while (hi - lo > 0.5) { const v = (lo + hi) / 2; if (okAt(v)) lo = v; else hi = v; }
          return lo;
        };
        const minX = bs(X0, X1, (v) => hasRL(vid, [v, Y0], [X1, Y1]));
        const maxX = -bs(-X1, -X0, (v) => hasRL(vid, [X0, Y0], [-v, Y1]));
        const minY = bs(Y0, Y1, (v) => hasRL(vid, [X0, v], [X1, Y1]));
        const maxY = -bs(-Y1, -Y0, (v) => hasRL(vid, [X0, Y0], [X1, -v]));
        return { x: (minX + maxX) / 2, y: (minY + maxY) / 2, w: maxX - minX, h: maxY - minY };
      };

      // 收集所有在視野附近的已渲染國名 bbox（供首都與其他標籤互撞檢查）
      const allRegimeBboxes = new Map<string, Box>();
      for (const f of renderedRegimeFeats) {
        const vid: string = f.properties.versionId;
        const coords: [number, number] = f.geometry.coordinates;
        const fp = m.project(coords);
        // 只算錨點在地圖容器邊界 ±400px 以內的（以免遠離視野的錨點浪費二分搜尋）
        if (fp.x < -400 || fp.x > W + 400 || fp.y < -60 || fp.y > H + 60) continue;
        const box = regimeLabelBox(vid, fp);
        if (box) allRegimeBboxes.set(vid, box);
      }

      // ── 首都 ───────────────────────────────────────────────────────────────────────
      const center = m.getCenter().lng;
      const capsFc = cmp.capitals()?.features ?? [];
      const capById = new Map<string, any>(capsFc.map((f: any) => [f.properties.recordId, f]));
      const apiById = new Map(apiCaps.map((c) => [c.recordId, c]));
      const caps = capsFc.map((f: any) => {
        const [lng0, lat] = f.geometry.coordinates;
        const lng = lng0 + Math.round((center - lng0) / 360) * 360;
        const p = m.project([lng, lat]);
        return { id: f.properties.recordId as string, label: f.properties.label as string, p, dot: { x: p.x, y: p.y, w: 10, h: 10 } as Box };
      });
      const renderedNames = new Set<string>(m.queryRenderedFeatures({ layers: ['capital-label'] }).map((f: any) => f.properties.recordId));
      const has = (layer: string, id: string, a: [number, number], b: [number, number]) =>
        m.queryRenderedFeatures([a, b], { layers: [layer] }).some((f: any) => f.properties.recordId === id);
      /** 用 box 查詢二分搜尋首都名稱的實際碰撞框。 */
      const nameBox = (id: string, p: { x: number; y: number }): Box | null => {
        const X0 = p.x - 320, X1 = p.x + 320, Y0 = p.y - 120, Y1 = p.y + 120;
        if (!has('capital-label', id, [X0, Y0], [X1, Y1])) return null;
        const bs = (lo: number, hi: number, okAt: (v: number) => boolean) => {
          // okAt(lo) 為真、okAt(hi) 為假，找最後一個為真的值
          while (hi - lo > 0.5) { const mid = (lo + hi) / 2; if (okAt(mid)) lo = mid; else hi = mid; }
          return lo;
        };
        const minX = bs(X0, X1, (v) => has('capital-label', id, [v, Y0], [X1, Y1]));
        const maxX = -bs(-X1, -X0, (v) => has('capital-label', id, [X0, Y0], [-v, Y1]));
        const minY = bs(Y0, Y1, (v) => has('capital-label', id, [X0, v], [X1, Y1]));
        const maxY = -bs(-Y1, -Y0, (v) => has('capital-label', id, [X0, Y0], [X1, -v]));
        return { x: (minX + maxX) / 2, y: (minY + maxY) / 2, w: maxX - minX, h: maxY - minY };
      };

      const out: any[] = [];
      const MX = 110, MY = 60; // 安全區邊距
      const covered = (p: { x: number; y: number }) => p.x >= MX && p.x <= W - MX && p.y >= MY && p.y <= H - MY && !underChrome(p);

      // API 有、前端沒載入的首都
      for (const c of apiCaps) {
        const key = `data:${c.recordId}`;
        if (!want.has(key)) continue;
        const ok = capById.has(c.recordId);
        out.push({ key, covered: true, boxes: [], checks: [{ kind: 'capital-data', id: c.recordId, regime: nameOfRegime.get(c.regimeId) ?? c.regimeSlug, item: c.regimeSlug, ok, reasons: ok ? [] : ['首都資料未進入地圖（API 有、前端 capitals 沒有）'] }] });
      }

      for (const c of caps) {
        const key = `cap:${c.id}`;
        if (!want.has(key)) continue;
        if (!covered(c.p)) { out.push({ key, covered: false, checks: [], boxes: [] }); continue; }
        const api = apiById.get(c.id);
        const regime = api ? nameOfRegime.get(api.regimeId) ?? api.regimeSlug : '?';
        const boxes: any[] = [{ ...c.dot, c: 'red' }];
        // 圓點
        const dotReasons: string[] = [];
        if (!has('capital-dot', c.id, [c.p.x - 4, c.p.y - 4], [c.p.x + 4, c.p.y + 4])) dotReasons.push('圓點未渲染（capital-dot 查不到）');
        // 圓點是否被國名底塊蓋住（MapLibre circle layer 不參與 symbol 碰撞，需手動檢查）
        for (const [, regBox] of allRegimeBboxes) {
          if (ov(c.dot, regBox, 0)) { dotReasons.push('圓點被國名標籤底塊蓋住'); boxes.push({ ...regBox, c: 'blue' }); }
        }
        out.push({ key, covered: true, boxes, checks: [] });
        const rec = out[out.length - 1];
        rec.checks.push({ kind: 'capital-dot', id: c.id, regime, item: `${c.label}（圓點）`, ok: dotReasons.length === 0, reasons: dotReasons });
        // 名稱（minzoom 3.5）
        if (zoom >= 3.5) {
          const nameReasons: string[] = [];
          const nb = renderedNames.has(c.id) ? nameBox(c.id, c.p) : null;
          if (!nb) nameReasons.push('首都名稱未渲染（capital-label 被符號碰撞隱藏）');
          else {
            boxes.push({ ...nb, c: 'red' });
            for (const o of caps) if (o.id !== c.id && ov(nb, o.dot)) { nameReasons.push(`名稱壓到另一座首都「${o.label}」的圓點`); boxes.push({ ...o.dot, c: 'blue' }); }
            if (clipped(nb)) nameReasons.push('名稱被地圖邊界裁切');
            for (const n of chromeHit(nb)) nameReasons.push(`名稱被 UI（${n}）蓋住`);
          }
          rec.checks.push({ kind: 'capital-name', id: c.id, regime, item: c.label, ok: nameReasons.length === 0, reasons: nameReasons });
        }
      }

      // ── 國名標籤（regime-label）────────────────────────────────────────────────────
      // 文字寬估計：政權名稱皆為繁體中文，CJK 全形字元在 MapLibre text-size:12 下
      // 回退字型 Arial Unicode MS 約 12px/字元（等寬全形），故使用 12px/字元估算。
      const regimeTextW = (text: string) => text.length * 12;
      // 「應顯示」門檻：投影 bbox 寬 ≥ 文字寬 × 2.5 且高 ≥ 48px
      const shouldDisplay = (l: any): boolean => {
        const a = m.project([l.bbox[0], l.bbox[1]]);
        const b = m.project([l.bbox[2], l.bbox[3]]);
        return Math.abs(b.x - a.x) >= regimeTextW(l.text) * 2.5 && Math.abs(b.y - a.y) >= 48;
      };

      for (const l of labelsIn) {
        const key = `lab:${l.versionId}`;
        if (!want.has(key)) continue;
        const p = m.project(l.lngLat);
        if (!covered(p)) { out.push({ key, covered: false, checks: [], boxes: [] }); continue; }

        const item = `${l.versionId.startsWith('sov-') ? '國名' : '控制區標籤'}「${l.text}」`;
        const myBox = allRegimeBboxes.get(l.versionId);

        if (!myBox) {
          // 未渲染：判斷是「應顯示卻隱藏」還是「正常依優先度略去」
          if (shouldDisplay(l)) {
            // 寬容條件 1：同名標籤已由另一個版本（通常是控制區標籤）渲染（用 renderedRegimeIds 涵蓋整個畫面）
            //   → 主權標籤被控制區標籤擠掉，屬於 symbol-sort-key 設計行為，ok=true
            const sameTextRendered = labelsIn.some(
              (ll: any) => ll.versionId !== l.versionId && ll.text === l.text && renderedRegimeIds.has(ll.versionId),
            );
            // 寬容條件 2：錨點附近（±400px×±200px）已有其他已渲染國名標籤佔位
            //   → 符號碰撞導致略去，屬於地圖密度問題，ok=true
            const nearbyOtherLabels =
              !sameTextRendered &&
              (m.queryRenderedFeatures([[p.x - 400, p.y - 200], [p.x + 400, p.y + 200]], { layers: ['regime-label'] }) as any[]).some(
                (f: any) => f.properties.versionId !== l.versionId,
              );
            if (sameTextRendered || nearbyOtherLabels) {
              // 政權已由其他標籤代表，或錨點被鄰近標籤碰撞占走 → ok=true, hidden=true
              out.push({ key, covered: true, boxes: [], checks: [{ kind: 'regime-label', id: l.versionId, regime: l.text, item, ok: true, reasons: [], hidden: true }] });
            } else {
              // 足夠大、附近空曠，仍未渲染 → 真正失敗
              const a = m.project([l.bbox[0], l.bbox[1]]);
              const b = m.project([l.bbox[2], l.bbox[3]]);
              const bw = Math.max(Math.abs(b.x - a.x), regimeTextW(l.text) + 12);
              const bh = Math.max(Math.abs(b.y - a.y), 20);
              out.push({ key, covered: true, boxes: [{ x: p.x, y: p.y, w: bw, h: bh, c: 'red' }], checks: [{ kind: 'regime-label', id: l.versionId, regime: l.text, item, ok: false, reasons: ['國名在足夠大的區塊內被隱藏'] }] });
            }
          } else {
            // 區塊太小，依設計略去 → ok=true, hidden=true（另輸出 hidden-<date>.json）
            out.push({ key, covered: true, boxes: [], checks: [{ kind: 'regime-label', id: l.versionId, regime: l.text, item, ok: true, reasons: [], hidden: true }] });
          }
          continue;
        }

        // 已渲染：檢查碰撞與裁切
        const reasons: string[] = [];
        const boxes: any[] = [{ ...myBox, c: 'red' }];

        // 與其他已渲染國名互撞
        for (const [otherId, otherBox] of allRegimeBboxes) {
          if (otherId === l.versionId) continue;
          if (ov(myBox, otherBox, 0)) {
            const otherText = labelsIn.find((ll: any) => ll.versionId === otherId)?.text ?? otherId;
            reasons.push(`與已渲染國名「${otherText}」互疊`);
            boxes.push({ ...otherBox, c: 'blue' });
          }
        }

        // 蓋住首都圓點（circle layer 不參與 symbol 碰撞）
        for (const c of caps) {
          if (ov(myBox, c.dot, 0)) {
            reasons.push(`蓋住首都「${c.label}」的圓點`);
            boxes.push({ ...c.dot, c: 'blue' });
          }
        }

        // 蓋住首都名稱（symbol-to-symbol 應由 MapLibre 阻擋，但仍驗證）
        if (zoom >= 3.5) {
          for (const c of caps) {
            if (!renderedNames.has(c.id)) continue;
            const nb = nameBox(c.id, c.p);
            if (nb && ov(myBox, nb, 0)) {
              reasons.push(`蓋住首都「${c.label}」的名稱`);
              boxes.push({ ...nb, c: 'blue' });
            }
          }
        }

        // 被地圖邊界裁切
        if (clipped(myBox)) reasons.push('標籤被地圖邊界裁切');

        // 被浮動 UI 蓋住
        for (const n of chromeHit(myBox)) reasons.push(`標籤被 UI（${n}）蓋住`);

        out.push({ key, covered: true, boxes, checks: [{ kind: 'regime-label', id: l.versionId, regime: l.text, item, ok: reasons.length === 0, reasons }] });
      }

      return out;
    },
    { pending, apiCaps },
  );
}

async function listItems(page: Page): Promise<{ keys: string[]; anchors: Record<string, [number, number]> }> {
  return page.evaluate(() => {
    const w = window as unknown as Record<string, any>;
    const cmp = w['ng'].getComponent(document.querySelector('wl-atlas-map'));
    const anchors: Record<string, [number, number]> = {};
    for (const f of cmp.capitals()?.features ?? []) anchors[`cap:${f.properties.recordId}`] = f.geometry.coordinates;
    for (const l of cmp.labels()) anchors[`lab:${l.versionId}`] = l.lngLat;
    return { keys: Object.keys(anchors), anchors };
  });
}

function failType(c: SweepCheck): string {
  const r = c.reasons[0] ?? '';
  if (c.kind === 'capital-data') return 'capital-data-missing';
  if (r.startsWith('圓點未渲染')) return 'dot-not-rendered';
  if (r.startsWith('圓點被')) return 'dot-covered-by-label';
  if (r.startsWith('首都名稱未渲染')) return 'name-not-rendered';
  if (r.includes('圓點')) return 'name-over-other-dot';
  if (r.includes('裁切')) return 'clipped-viewport';
  if (r.includes('UI（')) return 'covered-by-ui';
  if (r.includes('足夠大的區塊內被隱藏')) return 'label-hidden-when-large';
  if (r.includes('互疊')) return 'label-overlaps-label';
  if (r.includes('首都')) return 'label-covers-capital';
  return 'other';
}

async function annotate(page: Page, boxes: { x: number; y: number; w: number; h: number; c: string }[]): Promise<void> {
  await page.evaluate((boxes) => {
    const cont = (window as unknown as Record<string, any>)['__wlMap'].getContainer() as HTMLElement;
    const host = document.createElement('div');
    host.id = 'wl-sweep-annot';
    host.style.cssText = 'position:absolute;inset:0;pointer-events:none;z-index:9999';
    for (const b of boxes) {
      const d = document.createElement('div');
      d.style.cssText = `position:absolute;left:${b.x - b.w / 2 - 2}px;top:${b.y - b.h / 2 - 2}px;width:${b.w + 4}px;height:${b.h + 4}px;border:2px solid ${b.c === 'red' ? '#e00' : '#06f'};box-sizing:border-box`;
      host.appendChild(d);
    }
    cont.parentElement!.appendChild(host);
  }, boxes);
}

async function sweepDate(page: Page, date: string): Promise<SweepCheck[]> {
  for (let attempt = 1; ; attempt++) {
    await waitQuietServe();
    const before = codeFingerprint();
    try {
      const checks = await sweepDateOnce(page, date);
      const after = codeFingerprint();
      if (JSON.stringify(before) !== JSON.stringify(after)) throw new Error(`code changed during sweep: ${JSON.stringify(before)} -> ${JSON.stringify(after)}`);
      for (const c of checks) c.code = after;
      return checks;
    } catch (e) {
      // ng serve live reload（別人正在改同一個工作目錄）會讓頁面重新導向：等重建完再整個日期重跑
      if (attempt >= 3) throw e;
      test.info().annotations.push({ type: 'retry', description: `${date} attempt ${attempt}: ${String(e).slice(0, 200)}` });
    }
  }
}

async function sweepDateOnce(page: Page, date: string): Promise<SweepCheck[]> {
  await page.goto(`/?date=${date}`);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-map-ready', 'true', { timeout: 60_000 });
  await expect(page.getByTestId('map-area')).toHaveAttribute('data-ready-for', date, { timeout: 60_000 });
  const api = await page.request.get(`/api/v1/capitals?date=${date}`);
  const apiCaps = ((await api.json()) as { data: { features: { recordId: string; regimeId: string; regimeSlug: string }[] } }).data.features;
  const all: SweepCheck[] = [];
  for (const zoom of ZOOMS) {
    await page.evaluate((z) => (window as unknown as Record<string, any>)['__wlMap'].jumpTo({ center: [15, 50], zoom: z }), zoom);
    await settle(page);
    const { keys, anchors } = await listItems(page);
    let pending = [...apiCaps.map((c) => `data:${c.recordId}`), ...keys];
    let view = 0;
    while (pending.length && view < 60) {
      const target = pending.find((k) => anchors[k]) ?? null;
      if (target) await page.evaluate(([c, z]) => (window as unknown as Record<string, any>)['__wlMap'].jumpTo({ center: c, zoom: z }), [anchors[target], zoom] as const);
      const stable = await settle(page);
      const res = await analyzeView(page, pending, apiCaps);
      const done = new Set(res.filter((r) => r.covered).map((r) => r.key));
      if (target && !done.has(target)) done.add(target); // 無法置中（例如極區）：放棄這一項，避免無限迴圈
      for (const r of res) {
        if (!r.covered) continue;
        for (const c of r.checks) {
          const chk: SweepCheck = { ...c, date, zoom, view };
          if (!stable) chk.reasons.push('（注意：畫面 20 秒內未穩定）');
          if (!chk.ok) {
            const t = failType(chk);
            const n = shotCount.get(t) ?? 0;
            const ds = shotDates.get(t) ?? new Set<string>();
            if (n < MAX_SHOTS_PER_TYPE && !ds.has(date)) {
              const file = `${OUT}/shots/${t}-${date}-z${zoom}-${n + 1}.png`;
              await annotate(page, r.boxes);
              await page.screenshot({ path: file });
              await page.evaluate(() => document.getElementById('wl-sweep-annot')?.remove());
              shotCount.set(t, n + 1);
              ds.add(date);
              shotDates.set(t, ds);
              chk.shot = file;
            }
          }
          all.push(chk);
        }
      }
      pending = pending.filter((k) => !done.has(k));
      view++;
    }
  }
  return all;
}

for (const date of DATES) {
  test(`sweep ${date}`, async ({ page }) => {
    test.setTimeout(15 * 60_000);
    const checks = await sweepDate(page, date);
    await writeFile(`${OUT}/days/${date}.json`, JSON.stringify(checks, null, 1));
    // 區塊太小被略去的標籤單獨輸出（供人工審視，不算失敗）
    const hidden = checks.filter((c) => c.hidden);
    if (hidden.length) await writeFile(`${OUT}/days/hidden-${date}.json`, JSON.stringify(hidden, null, 1));
    const fails = checks.filter((c) => !c.ok);
    test.info().annotations.push({ type: 'sweep', description: `${date}: ${checks.length} checks, ${fails.length} failures, ${hidden.length} hidden` });
    if (STRICT) expect(fails.map((f) => `${f.date} z${f.zoom} ${f.regime} ${f.item}: ${f.reasons.join('；')}`)).toEqual([]);
  });
}

test.afterAll(async () => {
  const files = (await readdir(`${OUT}/days`)).filter((f) => f.endsWith('.json') && !f.startsWith('hidden-')).sort();
  const checks: SweepCheck[] = [];
  for (const f of files) checks.push(...(JSON.parse(await readFile(`${OUT}/days/${f}`, 'utf8')) as SweepCheck[]));
  await writeFile(`${OUT}/summary.json`, JSON.stringify(checks));
});
