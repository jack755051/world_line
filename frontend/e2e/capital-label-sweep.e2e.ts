import { execSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { expect, test, type Page } from '@playwright/test';

/**
 * 首都／國名標籤全面掃描（回歸測試）：在多個日期 × 縮放級別下，檢查當天每座首都的圓點、首都名稱，
 * 以及每個國名（政權）標籤是否完整可見。
 *
 * - 首都清單：GET /api/v1/capitals?date=（API）對照前端 wl-atlas-map 的 capitals() 輸入。
 * - HTML 國名標籤：DOM bounding box 互相比對（互撞、蓋住首都圓點／名稱、被 viewport／圖例等 UI 裁切）。
 * - MapLibre 首都圖層：queryRenderedFeatures 確認 capital-dot／capital-label 真的畫出來，
 *   並以 box 查詢二分搜尋出首都名稱實際的碰撞框。
 * - 每個縮放級別用貪婪法平移鏡頭，讓每個項目至少一次落在畫面安全區（離邊界有餘裕、不在圖例下）再檢查。
 *
 * 執行（只讀，不改資料；workers=1）：
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
      const sig =
        [...document.querySelectorAll('[data-testid=map-regime-label]')].map((e) => (e as HTMLElement).style.left + (e as HTMLElement).style.top + e.textContent).join('|') +
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

/** 在瀏覽器內分析目前鏡頭：回傳每個尚未檢查項目的覆蓋狀態與檢查結果。座標一律是地圖容器座標。 */
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

      // 國名標籤：placedLabels 與 DOM 依序對應
      const labelsIn: any[] = cmp.labels();
      const placed: any[] = cmp.placedLabels();
      const domEls = [...cont.parentElement!.querySelectorAll('[data-testid=map-regime-label]')];
      const dom = domEls.map((el, i) => ({ el, p: placed[i], box: toBox(el.getBoundingClientRect()), text: el.textContent!.trim() }));
      const nameOfRegime = new Map<string, string>();
      for (const l of labelsIn) if (!nameOfRegime.has(l.regimeId)) nameOfRegime.set(l.regimeId, l.text);

      // 首都
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
        for (const d of dom) if (ov(c.dot, d.box, 0)) { dotReasons.push(`圓點被國名標籤「${d.text}」的底塊蓋住`); boxes.push({ ...d.box, c: 'blue' }); }
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
            for (const d of dom) if (ov(nb, d.box)) { nameReasons.push(`名稱被國名標籤「${d.text}」的底塊蓋住`); boxes.push({ ...d.box, c: 'blue' }); }
            for (const o of caps) if (o.id !== c.id && ov(nb, o.dot)) { nameReasons.push(`名稱壓到另一座首都「${o.label}」的圓點`); boxes.push({ ...o.dot, c: 'blue' }); }
            if (clipped(nb)) nameReasons.push('名稱被地圖邊界裁切');
            for (const n of chromeHit(nb)) nameReasons.push(`名稱被 UI（${n}）蓋住`);
          }
          rec.checks.push({ kind: 'capital-name', id: c.id, regime, item: c.label, ok: nameReasons.length === 0, reasons: nameReasons });
        }
      }

      // 國名標籤：重現 placeLabels 的門檻與首都避讓，分辨「被略去」的原因
      // capObs 與 capitalObstacleBoxes（label-placement.ts）保持一致：
      //   圓點框 16×16（dotObsSize = (3.5+1.5+3)×2）；zoom≥3.5 時加 right/left 兩個名稱框
      //   字寬 = label.length * 6.5 + 3（_CAP_LABEL_AVG_CHAR_PX=6.5, halo×2=3）
      //   名稱框高 16（CAP_LABEL_H）；水平偏移 = 10（_CAP_LABEL_RADIAL_PX）+ lw/2
      const capObs: Box[] = [];
      for (const c of caps) {
        capObs.push({ x: c.p.x, y: c.p.y, w: 16, h: 16 });
        if (zoom >= 3.5) {
          const lw = Math.max(c.label.length * 6.5 + 3, 1);
          const obsW = lw + 6;
          const offset = 10 + lw / 2;
          capObs.push({ x: c.p.x + offset, y: c.p.y, w: obsW, h: 16 }); // right anchor
          capObs.push({ x: c.p.x - offset, y: c.p.y, w: obsW, h: 16 }); // left anchor
        }
      }
      const placedIdx = new Map<string, number>(placed.map((p: any, i: number) => [p.versionId, i]));
      for (const l of labelsIn) {
        const key = `lab:${l.versionId}`;
        if (!want.has(key)) continue;
        const p = m.project(l.lngLat);
        if (!covered(p)) { out.push({ key, covered: false, checks: [], boxes: [] }); continue; }
        const a = m.project([l.bbox[0], l.bbox[1]]);
        const b = m.project([l.bbox[2], l.bbox[3]]);
        const textW = l.text.length * 14;
        const expected = Math.abs(b.x - a.x) >= textW * (l.fit ?? 1.6) && Math.abs(b.y - a.y) >= 32;
        if (!expected) { out.push({ key, covered: true, checks: [], boxes: [] }); continue; } // 區塊太小、依設計不標
        const reasons: string[] = [];
        const boxes: any[] = [];
        const idx = placedIdx.get(l.versionId);
        const item = l.versionId.startsWith('sov-') ? `國名「${l.text}」` : `控制區標籤「${l.text}」`;
        if (idx === undefined) {
          // 只看首都保留框時七個位移都放不下＝被首都擠掉；否則是被其他（已放置的）標籤擠掉
          const fits = [0, -18, 18, -30, 30, -44, 44].some((dy) => !capObs.some((o) => ov({ x: p.x, y: p.y + dy, w: textW + 8, h: 20 }, o, 0)));
          reasons.push(!fits ? '國名標籤被略去：避讓首都保留框後七個位移都撞到' : '國名標籤被略去：與其他已放置的標籤互撞');
          boxes.push({ x: p.x, y: p.y, w: textW + 8, h: 20, c: 'red' });
        } else {
          const me = dom[idx];
          boxes.push({ ...me.box, c: 'red' });
          for (let j = idx + 1; j < dom.length; j++) if (ov(me.box, dom[j].box)) { reasons.push(`被國名標籤「${dom[j].text}」疊在上面`); boxes.push({ ...dom[j].box, c: 'blue' }); }
          if (clipped(me.box)) reasons.push('標籤被地圖邊界裁切');
          for (const n of chromeHit(me.box)) reasons.push(`標籤被 UI（${n}）蓋住`);
        }
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
  if (r.includes('底塊蓋住')) return 'name-covered-by-label';
  if (r.includes('圓點')) return 'name-over-other-dot';
  if (r.includes('被略去：避讓首都')) return 'label-dropped-capital-avoid';
  if (r.includes('被略去：與其他')) return 'label-dropped-collision';
  if (r.startsWith('被國名標籤')) return 'label-overlaps-label';
  if (r.includes('裁切')) return 'clipped-viewport';
  if (r.includes('UI（')) return 'covered-by-ui';
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
    const fails = checks.filter((c) => !c.ok);
    test.info().annotations.push({ type: 'sweep', description: `${date}: ${checks.length} checks, ${fails.length} failures` });
    if (STRICT) expect(fails.map((f) => `${f.date} z${f.zoom} ${f.regime} ${f.item}: ${f.reasons.join('；')}`)).toEqual([]);
  });
}

test.afterAll(async () => {
  const files = (await readdir(`${OUT}/days`)).filter((f) => f.endsWith('.json')).sort();
  const checks: SweepCheck[] = [];
  for (const f of files) checks.push(...(JSON.parse(await readFile(`${OUT}/days/${f}`, 'utf8')) as SweepCheck[]));
  await writeFile(`${OUT}/summary.json`, JSON.stringify(checks));
});
