import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';

/**
 * 人物分頁與人物閱讀對話框（Tai 2026-11-07 核准；設計 docs/design/person-reading-campaign-nav.md、ARCHITECTURE §14）。
 * 需要開發 API（5052）：`WL_E2E_BORDERS=1 WL_E2E_PORT=4201 pnpm exec playwright test person-cards`。
 * 不使用 mock、不寫入資料。截圖存到 ../.dev/screenshots/person-cards/；人物 v2 驗收截圖存到 ../.dev/screenshots/person-v2/。
 */
test.skip(!process.env['WL_E2E_BORDERS'], '需要開發 API（5052）上的資料');

const SHOTS = '../.dev/screenshots/person-cards';
mkdirSync(SHOTS, { recursive: true });
/** 本次（人物 v2）驗收截圖 */
const V2 = '../.dev/screenshots/person-v2';
mkdirSync(V2, { recursive: true });
const DATE = '1940-06-01';
const D44 = '1944-09-17';
const POZNAN: [number, number] = [16.93, 52.41];
const BERLIN: [number, number] = [13.4, 52.5];
const BERN: [number, number] = [7.45, 46.95];
const KANSAS: [number, number] = [-98, 39];
type WlMap = { jumpTo: (o: object) => void; project: (l: [number, number]) => { x: number; y: number }; getCenter: () => { lng: number; lat: number }; getZoom: () => number };

async function openMap(page: Page, center: [number, number], extra = '', date = DATE): Promise<void> {
  await page.goto(`/?date=${date}&axis=sovereignty${extra}`);
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true');
  await page.evaluate((c) => (window as unknown as { __wlMap: WlMap }).__wlMap.jumpTo({ center: c, zoom: 4.5 }), center);
  await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(3);
  await page.waitForTimeout(300);
}

async function selectRegimeAt(page: Page, lngLat: [number, number]): Promise<void> {
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-camera', 'idle');
  const box = (await canvas.boundingBox())!;
  const p = await page.evaluate((ll) => (window as unknown as { __wlMap: WlMap }).__wlMap.project(ll), lngLat);
  await page.mouse.click(box.x + p.x, box.y + p.y);
  await expect(page.getByTestId('regime-sheet')).toBeVisible();
  await page.getByTestId('sovereignty-card-tab-leaders').click();
  await expect(page.getByTestId('sovereignty-card-panel-leaders')).toBeVisible();
}

const camera = (page: Page) => page.evaluate(() => {
  const m = (window as unknown as { __wlMap: WlMap }).__wlMap;
  const c = m.getCenter();
  return { lng: +c.lng.toFixed(4), lat: +c.lat.toFixed(4), zoom: +m.getZoom().toFixed(3) };
});

async function hitlerRecord(page: Page, date = DATE): Promise<{ personId: string; regimeId: string }> {
  const res = await page.request.get(`/api/v1/leaders?date=${date}&regime=deutsches-reich`);
  const f = (await res.json()).data.features as { personId: string | null; name: string; regimeId: string }[];
  const h = f.find((x) => x.name === 'Adolf Hitler' && x.personId)!;
  return { personId: h.personId!, regimeId: h.regimeId };
}
const hitlerId = async (page: Page, date = DATE): Promise<string> => (await hitlerRecord(page, date)).personId;

/** 該政權當日不重複人數（同一 personId 只算一次；沒有 personId 的記錄各算一人）。 */
async function uniquePeople(page: Page, date: string, regimeId: string): Promise<number> {
  const f = (await (await page.request.get(`/api/v1/leaders?date=${date}`)).json()).data.features as { regimeId: string; personId: string | null; recordId: string }[];
  return new Set(f.filter((x) => x.regimeId === regimeId).map((x) => x.personId ?? x.recordId)).size;
}
async function regimeDisplayZh(page: Page, regimeId: string): Promise<string> {
  const r = (await (await page.request.get(`/api/v1/regimes/${regimeId}`)).json()).data as { names: { nameKind: string; isPrimary: boolean; originalText: string; display: Record<string, string> }[] };
  const n = r.names.find((x) => x.nameKind === 'self' && x.isPrimary) ?? r.names.find((x) => x.nameKind === 'self') ?? r.names[0];
  return n.display['zh-Hant'] || n.display['en'] || n.originalText;
}

test('人物分頁（1944-09-17 德國）：分頁數量＝不重複人數、希特勒合併成一張卡；新版詳情（標頭、分頁籤、基本資料、生平、任期、底部來源）；關閉後還原選取／分頁／捲動／日期／鏡頭（桌機）', async ({ page }) => {
  await openMap(page, [13.4, 52], '', D44);
  await selectRegimeAt(page, BERLIN);
  const tab = page.getByTestId('sovereignty-card-tab-leaders');
  await expect(tab).toHaveAttribute('aria-selected', 'true');
  const hit = await hitlerRecord(page, D44);
  const expected = await uniquePeople(page, D44, hit.regimeId);
  await expect(page.getByTestId('sovereignty-card-tab-leaders-count')).toHaveText(String(expected));
  await expect(tab).toHaveText(new RegExp(`^\\s*人物\\s*${expected}\\s*$`));
  await expect(page.getByTestId('person-card')).toHaveCount(expected);

  // 同一人兩個角色 → 一張卡、兩列角色（各自任期與來源）、一個「查看詳情」
  const hitlerCard = page.getByTestId('person-card').filter({ hasText: '希特勒' });
  await expect(hitlerCard).toHaveCount(1);
  const rows = hitlerCard.getByTestId('person-card-role-row');
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(0)).toHaveAttribute('data-role', 'head_of_state');
  await expect(rows.nth(1)).toHaveAttribute('data-role', 'head_of_government');
  await expect(rows.nth(1).getByTestId('person-card-term')).toContainText('1933-01-30 – 1945-04-29');
  const trigger = hitlerCard.getByTestId('person-card-details');
  await expect(trigger).toHaveCount(1);
  const pid = await trigger.getAttribute('data-person-trigger');
  expect(pid).toBe(hit.personId);
  for (const t of await page.getByTestId('person-card').getByTestId('source-toggle').all()) await expect(t).toHaveAttribute('aria-expanded', 'false');
  await hitlerCard.scrollIntoViewIfNeeded();
  await page.screenshot({ path: `${V2}/a-germany-people-tab.png` });

  // 記下底層狀態
  const body = page.getByTestId('regime-sheet').getByTestId('sovereignty-card-body');
  await body.evaluate((el) => { el.scrollTop = Math.min(80, el.scrollHeight - el.clientHeight); });
  const scrollBefore = await body.evaluate((el) => el.scrollTop);
  const camBefore = await camera(page);
  const urlBefore = page.url();
  const title = await page.getByTestId('sovereignty-card-title').textContent();

  // 開對話框（push ?person=）
  await trigger.click();
  const dlg = page.getByTestId('person-dialog');
  await expect(dlg).toBeVisible();
  await expect(dlg).toHaveAttribute('role', 'dialog');
  await expect(dlg).toHaveAttribute('aria-modal', 'true');
  await expect(dlg).toHaveAttribute('aria-labelledby', /.+/);
  await expect(page.getByTestId('person-dialog-title')).toHaveText('阿道夫·希特勒');
  await expect(page.getByTestId('person-dialog-original-name')).toContainText('Adolf Hitler');
  expect(new URL(page.url()).searchParams.get('person')).toBe(pid);
  expect(new URL(page.url()).searchParams.get('date')).toBe(D44);
  await expect(page.getByTestId('person-dialog-close')).toBeFocused();
  await expect(page.getByTestId('regime-sheet')).toHaveAttribute('inert', '');
  // 版面：標頭、角色、生卒、分頁籤、各區塊
  await expect(dlg.getByTestId('person-dialog-hero')).toBeVisible();
  await expect(dlg.getByTestId('person-dialog-role')).toHaveCount(2);
  await expect(dlg.getByTestId('person-dialog-life')).toContainText('1889-04-20');
  for (const k of ['basics', 'bio', 'terms', 'sources']) await expect(dlg.getByTestId(`person-dialog-tab-${k}`)).toBeVisible();
  await expect(dlg.getByTestId('person-dialog-basics')).toBeVisible();
  await expect(dlg.getByTestId('person-dialog-section-bio')).toBeAttached();
  await expect(page.getByTestId('person-term')).toHaveCount(2);
  await expect(page.getByTestId('person-term').first()).toContainText('1933-01-30 – 1945-04-29');
  // 欄位旁只有上標編號，沒有完整連結
  expect(await dlg.getByTestId('person-field-birthDate').locator('a').count()).toBe(0);
  await expect(dlg.getByTestId('person-field-birthDate').getByTestId('person-field-sup').first()).toBeVisible();
  // 配色：沿用羊皮紙淺底（不是 Stitch 深藍）
  const bg = await dlg.evaluate((el) => getComputedStyle(el).backgroundColor);
  const [r, g, b] = bg.match(/\d+/g)!.map(Number);
  expect(r + g + b).toBeGreaterThan(600);
  // 來源：底部統一收合、預設收合；版面固定（展開不移動標題）
  const srcToggle = dlg.getByTestId('person-sources-toggle');
  await expect(srcToggle).toHaveAttribute('aria-expanded', 'false');
  await expect(dlg.getByTestId('person-sources-panel')).toBeHidden();
  await expect(dlg.getByTestId('person-sources-label')).toHaveText(/^資料來源 \(\d+\)$/);
  await page.screenshot({ path: `${V2}/c-hitler-dialog-desktop.png` });
  const headBefore = await page.getByTestId('person-dialog-title').boundingBox();
  await srcToggle.evaluate((el: HTMLElement) => el.click());
  await expect(srcToggle).toHaveAttribute('aria-expanded', 'true');
  expect(await page.getByTestId('person-dialog-title').boundingBox()).toEqual(headBefore);
  await srcToggle.evaluate((el: HTMLElement) => el.click());
  await expect(srcToggle).toHaveAttribute('aria-expanded', 'false');
  // 上標編號 → 展開來源並捲到該筆；分頁籤吸頂
  await dlg.getByTestId('person-field-birthDate').getByTestId('person-field-sup').first().click();
  await expect(srcToggle).toHaveAttribute('aria-expanded', 'true');
  await expect(dlg.getByTestId('person-source-note').first()).toBeInViewport();
  await expect(dlg.getByTestId('person-dialog-tabs')).toBeInViewport();
  await page.screenshot({ path: `${V2}/c2-hitler-dialog-sources.png` });
  await dlg.getByTestId('person-dialog-tab-basics').click();
  await expect(dlg.getByTestId('person-dialog-basics')).toBeInViewport();

  // 焦點鎖定：連按 Tab／Shift+Tab 焦點都留在對話框內
  for (let i = 0; i < 25; i++) {
    await page.keyboard.press('Tab');
    expect(await page.evaluate(() => !!document.activeElement?.closest('[data-testid="person-dialog"]'))).toBe(true);
  }
  for (let i = 0; i < 5; i++) {
    await page.keyboard.press('Shift+Tab');
    expect(await page.evaluate(() => !!document.activeElement?.closest('[data-testid="person-dialog"]'))).toBe(true);
  }

  // Esc 關閉 → app 自己 push 的 → history.back()；底層全部原樣
  await page.keyboard.press('Escape');
  await expect(dlg).toHaveCount(0);
  await expect.poll(() => new URL(page.url()).searchParams.get('person')).toBeNull();
  expect(page.url()).toBe(urlBefore);
  await expect(page.getByTestId('regime-sheet')).toBeVisible();
  await expect(page.getByTestId('regime-sheet')).not.toHaveAttribute('inert', '');
  await expect(page.getByTestId('sovereignty-card-title')).toHaveText(title!);
  await expect(tab).toHaveAttribute('aria-selected', 'true');
  expect(await body.evaluate((el) => el.scrollTop)).toBe(scrollBefore);
  expect(await camera(page)).toEqual(camBefore);
  await expect(trigger).toBeFocused();
  await page.screenshot({ path: `${V2}/e-after-close-restored.png` });

  // 上一頁／下一頁：開 → 上一頁關 → 下一頁重開
  await trigger.click();
  await expect(dlg).toBeVisible();
  await page.goBack();
  await expect(dlg).toHaveCount(0);
  await expect(page.getByTestId('regime-sheet')).toBeVisible();
  await page.goForward();
  await expect(page.getByTestId('person-dialog')).toBeVisible();
  // 背景點擊關閉（goForward 後服務沒有對應記錄 → replace，只移除 person）
  await page.getByTestId('person-dialog-backdrop').click({ position: { x: 10, y: 10 } });
  await expect(page.getByTestId('person-dialog')).toHaveCount(0);
  expect(new URL(page.url()).searchParams.get('date')).toBe(D44);
  expect(new URL(page.url()).searchParams.get('person')).toBeNull();
});

test('併入地沿用主要政權人物（1944-09-17 德國併入的波蘭西部與北部地區）：標示「沿用主要政權：<資料顯示名>」、數量＝實際列出的不重複人數', async ({ page }) => {
  await openMap(page, [17, 52.5], '', D44);
  await selectRegimeAt(page, POZNAN);
  await expect(page.getByTestId('sovereignty-card-status')).toHaveAttribute('data-control-kind', 'annexed');
  const hit = await hitlerRecord(page, D44);
  const occupier = await regimeDisplayZh(page, hit.regimeId);
  const expected = await uniquePeople(page, D44, hit.regimeId);
  await expect(page.getByTestId('sovereignty-card-leaders-inherited-note')).toContainText(`沿用主要政權：${occupier}`);
  await expect(page.getByTestId('sovereignty-card-tab-leaders-count')).toHaveText(String(expected));
  await expect(page.getByTestId('person-card')).toHaveCount(expected);
  await expect(page.getByTestId('sovereignty-card-leaders-inherited').getByTestId('person-card').filter({ hasText: '希特勒' })).toHaveCount(1);
  await page.screenshot({ path: `${V2}/b-annexed-poland-inherit.png` });
});

test('深連結 ?person=：直接開對話框；關閉用 replace 只移除 person（保留 date／axis）', async ({ page }) => {
  const pid = await hitlerId(page);
  await page.goto(`/?date=${DATE}&axis=sovereignty&person=${pid}`);
  await expect(page.getByTestId('person-dialog')).toBeVisible();
  await expect(page.getByTestId('person-dialog-title')).toHaveText('阿道夫·希特勒');
  const len = await page.evaluate(() => history.length);
  await page.getByTestId('person-dialog-close').click();
  await expect(page.getByTestId('person-dialog')).toHaveCount(0);
  const u = new URL(page.url());
  expect(u.searchParams.get('person')).toBeNull();
  expect(u.searchParams.get('date')).toBe(DATE);
  expect(u.searchParams.get('axis')).toBe('sovereignty');
  expect(await page.evaluate(() => history.length)).toBe(len); // 沒有 back、沒有 push
});

test('不存在的人物：toast 並移除 person 參數', async ({ page }) => {
  await page.goto(`/?date=${DATE}&person=00000000-0000-7000-8000-000000000000`);
  await expect.poll(() => new URL(page.url()).searchParams.get('person')).toBeNull();
  await expect(page.getByTestId('person-dialog')).toHaveCount(0);
  await expect(page.getByText('找不到這位人物的資料').first()).toBeVisible();
});

test('沒有生平／照片／來源的人物：中性佔位、無「查看詳情」、待補來源（瑞士 1940）', async ({ page }) => {
  await openMap(page, [8, 47]);
  await selectRegimeAt(page, BERN);
  const cards = page.getByTestId('person-card');
  await expect(cards.first()).toBeVisible();
  const noBio = cards.filter({ hasNot: page.getByTestId('person-card-details') });
  expect(await noBio.count()).toBeGreaterThan(0);
  await expect(noBio.first().getByTestId('person-card-placeholder')).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/desktop-04-no-bio.png` });
});

test('API：人物詳情回傳任期、欄位引用、照片欄位', async ({ page }) => {
  const pid = await hitlerId(page);
  const d = (await (await page.request.get(`/api/v1/leader-bios/${pid}`)).json()).data;
  expect(d.terms.length).toBe(2);
  expect(Array.isArray(d.fieldCitations)).toBe(true);
  expect('portrait' in d).toBe(true);
  for (const t of d.terms) expect(t.regimeName['zh-Hant']).toBeTruthy();
});

test('有結構化來源與授權照片的人物（美國 1940：羅斯福）：卡片照片、對話框照片署名、逐欄位來源（結構化）', async ({ page }) => {
  await page.goto(`/?date=${DATE}&axis=sovereignty`);
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true');
  await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.jumpTo({ center: [-98, 39], zoom: 3.2 }));
  await page.waitForTimeout(600);
  await selectRegimeAt(page, KANSAS);
  const card = page.getByTestId('person-card').filter({ hasText: '羅斯福' }).first();
  await expect(card.getByTestId('person-card-photo')).toBeVisible();
  await expect.poll(() => card.getByTestId('person-card-photo').evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0), { timeout: 20_000 }).toBe(true);
  await page.screenshot({ path: `${SHOTS}/desktop-05-people-tab-photo.png` });
  await card.getByTestId('person-card-details').click();
  const dlg = page.getByTestId('person-dialog');
  await expect(dlg.getByTestId('person-dialog-photo')).toBeVisible();
  await expect(dlg.getByTestId('person-dialog-photo-credit')).toContainText('CC BY');
  await expect(dlg.getByTestId('person-field-birthDate')).toContainText('1882-01-30');
  // 出生欄位：上標編號（結構化＋舊格式備註＝2 筆）；點了展開底部來源，該筆是結構化來源並帶連結
  const sups = dlg.getByTestId('person-field-birthDate').getByTestId('person-field-sup');
  await expect(sups).toHaveCount(2);
  await expect(dlg.getByTestId('person-sources-toggle')).toHaveAttribute('aria-expanded', 'false');
  await sups.first().click();
  await expect(dlg.getByTestId('person-sources-toggle')).toHaveAttribute('aria-expanded', 'true');
  const n = await sups.first().getAttribute('data-n');
  const note = dlg.locator(`[data-testid="person-source-note"][data-n="${n}"]`);
  await expect(note).toBeInViewport();
  await expect(note.getByTestId('person-source-used-for')).toContainText('出生');
  await expect(note.getByTestId('source-item')).toHaveAttribute('data-kind', 'structured');
  await expect(note.locator('a[href*="fdrlibrary.org"]')).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/desktop-06-dialog-structured-sources.png` });
  // API：同一筆在 API 也有結構化引用與照片授權
  const pid = await card.getAttribute('data-person-id');
  const d = (await (await page.request.get(`/api/v1/leader-bios/${pid}`)).json()).data;
  expect(d.fieldCitations.some((c: { field: string; source: { url: string } }) => c.field === 'birthDate' && c.source.url.includes('fdrlibrary'))).toBe(true);
  expect(d.portrait.licenseCode).toBe('cc_by');
});

test.describe('手機', () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });

  test('對話框全螢幕（1944-09-17 希特勒）、關閉鈕與來源收合鈕 ≥44px、分頁籤吸頂、用按鈕關閉', async ({ page }) => {
    const pid = await hitlerId(page, D44);
    await page.goto(`/?date=${D44}&axis=sovereignty&person=${pid}`);
    const dlg = page.getByTestId('person-dialog');
    await expect(dlg).toBeVisible();
    await expect(page.getByTestId('person-dialog-title')).toHaveText('阿道夫·希特勒');
    const box = (await dlg.boundingBox())!;
    expect(box.x).toBe(0);
    expect(box.y).toBe(0);
    expect(Math.round(box.width)).toBe(390);
    expect(Math.round(box.height)).toBe(844);
    const close = (await page.getByTestId('person-dialog-close').boundingBox())!;
    expect(close.width).toBeGreaterThanOrEqual(44);
    expect(close.height).toBeGreaterThanOrEqual(44);
    const srcToggle = dlg.getByTestId('person-sources-toggle');
    await expect(srcToggle).toHaveAttribute('aria-expanded', 'false');
    expect((await srcToggle.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    for (const k of ['basics', 'bio', 'terms', 'sources']) expect((await dlg.getByTestId(`person-dialog-tab-${k}`).boundingBox())!.height).toBeGreaterThanOrEqual(44);
    await expect(dlg.getByTestId('person-dialog-hero')).toBeVisible();
    await page.screenshot({ path: `${V2}/d-hitler-dialog-mobile.png` });
    await page.screenshot({ path: `${SHOTS}/mobile-01-dialog.png` });
    // 捲到任期：分頁籤吸頂仍可見
    await dlg.getByTestId('person-dialog-tab-terms').tap();
    await expect(dlg.getByTestId('person-terms')).toBeInViewport();
    await expect(dlg.getByTestId('person-dialog-tabs')).toBeInViewport();
    await expect(dlg.getByTestId('person-dialog-tab-terms')).toHaveAttribute('aria-current', 'true');
    await page.screenshot({ path: `${V2}/d2-hitler-dialog-mobile-terms.png` });
    await page.getByTestId('person-dialog-close').tap();
    await expect(dlg).toHaveCount(0);
  });

  test('人物分頁卡片與「查看詳情」觸控尺寸 ≥44px', async ({ page }) => {
    await openMap(page, [13.4, 52]);
    await selectRegimeAt(page, BERLIN);
    // 底部面板拉到最高，卡片才完整在可見區
    const snap = page.getByTestId('regime-sheet-snap');
    for (let i = 0; i < 3 && (await snap.getAttribute('data-snap')) !== 'full'; i++) { await snap.tap(); await page.waitForTimeout(700); }
    await expect(snap).toHaveAttribute('data-snap', 'full');
    await expect.poll(async () => (await page.getByTestId('regime-sheet').boundingBox())!.height).toBeGreaterThan(600);
    const btn = page.getByTestId('person-card-details').first();
    await btn.scrollIntoViewIfNeeded();
    await expect(btn).toBeVisible();
    const b = (await btn.boundingBox())!;
    expect(b.height).toBeGreaterThanOrEqual(44);
    await page.screenshot({ path: `${SHOTS}/mobile-02-people-tab.png` });
    await btn.tap();
    await expect(page.getByTestId('person-dialog')).toBeVisible();
    await page.getByTestId('person-dialog-close').tap();
    await expect(page.getByTestId('person-dialog')).toHaveCount(0);
    await expect(page.getByTestId('sovereignty-card-tab-leaders')).toHaveAttribute('aria-selected', 'true');
  });
});
