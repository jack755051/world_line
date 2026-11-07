import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';

/**
 * 人物分頁與人物閱讀對話框（Tai 2026-11-07 核准；設計 docs/design/person-reading-campaign-nav.md、ARCHITECTURE §14）。
 * 需要開發 API（5052）：`WL_E2E_BORDERS=1 WL_E2E_PORT=4201 pnpm exec playwright test person-cards`。
 * 不使用 mock、不寫入資料。截圖存到 ../.dev/screenshots/person-cards/。
 */
test.skip(!process.env['WL_E2E_BORDERS'], '需要開發 API（5052）上的資料');

const SHOTS = '../.dev/screenshots/person-cards';
mkdirSync(SHOTS, { recursive: true });
const DATE = '1940-06-01';
const BERLIN: [number, number] = [13.4, 52.5];
const BERN: [number, number] = [7.45, 46.95];
type WlMap = { jumpTo: (o: object) => void; project: (l: [number, number]) => { x: number; y: number }; getCenter: () => { lng: number; lat: number }; getZoom: () => number };

async function openMap(page: Page, center: [number, number], extra = ''): Promise<void> {
  await page.goto(`/?date=${DATE}&axis=sovereignty${extra}`);
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

async function hitlerId(page: Page): Promise<string> {
  const res = await page.request.get(`/api/v1/leaders?date=${DATE}&regime=deutsches-reich`);
  const f = (await res.json()).data.features as { personId: string | null; name: string }[];
  return f.find((x) => x.name === 'Adolf Hitler' && x.personId)!.personId!;
}

test('人物分頁：卡片、同一人多職位、對話框鍵盤、來源收合、關閉後還原選取／分頁／捲動／日期／鏡頭（桌機）', async ({ page }) => {
  await openMap(page, [13.4, 52]);
  await selectRegimeAt(page, BERLIN);
  const tab = page.getByTestId('sovereignty-card-tab-leaders');
  await expect(tab).toHaveText('人物');
  await expect(tab).toHaveAttribute('aria-selected', 'true');

  // 同一人兩個職位：兩張卡都指向同一份生平
  const hitlerCards = page.getByTestId('person-card').filter({ hasText: '希特勒' });
  await expect(hitlerCards).toHaveCount(2);
  const triggers = hitlerCards.getByTestId('person-card-details');
  await expect(triggers).toHaveCount(2);
  const pid = await triggers.first().getAttribute('data-person-trigger');
  expect(await triggers.nth(1).getAttribute('data-person-trigger')).toBe(pid);
  // 卡片來源預設收合
  for (const t of await page.getByTestId('person-card').getByTestId('source-toggle').all()) await expect(t).toHaveAttribute('aria-expanded', 'false');
  await page.screenshot({ path: `${SHOTS}/desktop-01-people-tab.png` });

  // 記下底層狀態
  const body = page.getByTestId('regime-sheet').getByTestId('sovereignty-card-body');
  await body.evaluate((el) => { el.scrollTop = Math.min(80, el.scrollHeight - el.clientHeight); });
  const scrollBefore = await body.evaluate((el) => el.scrollTop);
  const camBefore = await camera(page);
  const urlBefore = page.url();
  const title = await page.getByTestId('sovereignty-card-title').textContent();

  // 開對話框（push ?person=）
  const trigger = triggers.last();
  await trigger.click();
  const dlg = page.getByTestId('person-dialog');
  await expect(dlg).toBeVisible();
  await expect(dlg).toHaveAttribute('role', 'dialog');
  await expect(dlg).toHaveAttribute('aria-modal', 'true');
  await expect(dlg).toHaveAttribute('aria-labelledby', /.+/);
  await expect(page.getByTestId('person-dialog-title')).toHaveText('阿道夫·希特勒');
  expect(new URL(page.url()).searchParams.get('person')).toBe(pid);
  expect(new URL(page.url()).searchParams.get('date')).toBe(DATE);
  await expect(page.getByTestId('person-dialog-close')).toBeFocused();
  await expect(page.getByTestId('regime-sheet')).toHaveAttribute('inert', '');
  // 多職位任期都列出
  await expect(page.getByTestId('person-term')).toHaveCount(2);
  await expect(page.getByTestId('person-term').first()).toContainText('1933-01-30 – 1945-04-29');
  // 來源：全部預設收合；缺來源的欄位顯示「待補來源」
  const toggles = dlg.getByTestId('source-toggle');
  expect(await toggles.count()).toBeGreaterThan(0);
  for (const t of await toggles.all()) await expect(t).toHaveAttribute('aria-expanded', 'false');
  for (const p of await dlg.getByTestId('source-panel').all()) await expect(p).toBeHidden();
  await page.screenshot({ path: `${SHOTS}/desktop-02-dialog-collapsed.png` });
  // 版面固定：展開來源不移動標題列
  const headBefore = await page.getByTestId('person-dialog-title').boundingBox();
  await page.getByTestId('person-dialog-expand-all').click();
  for (const t of await toggles.all()) await expect(t).toHaveAttribute('aria-expanded', 'true');
  expect(await page.getByTestId('person-dialog-title').boundingBox()).toEqual(headBefore);
  await page.screenshot({ path: `${SHOTS}/desktop-03-dialog-sources-expanded.png` });
  await page.getByTestId('person-dialog-expand-all').click();
  for (const t of await toggles.all()) await expect(t).toHaveAttribute('aria-expanded', 'false');

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
  expect(new URL(page.url()).searchParams.get('date')).toBe(DATE);
  expect(new URL(page.url()).searchParams.get('person')).toBeNull();
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

test.describe('手機', () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });

  test('對話框全螢幕、關閉鈕 ≥44px、Esc 以外用按鈕關閉', async ({ page }) => {
    const pid = await hitlerId(page);
    await page.goto(`/?date=${DATE}&axis=sovereignty&person=${pid}`);
    const dlg = page.getByTestId('person-dialog');
    await expect(dlg).toBeVisible();
    const box = (await dlg.boundingBox())!;
    expect(box.x).toBe(0);
    expect(box.y).toBe(0);
    expect(Math.round(box.width)).toBe(390);
    expect(Math.round(box.height)).toBe(844);
    const close = (await page.getByTestId('person-dialog-close').boundingBox())!;
    expect(close.width).toBeGreaterThanOrEqual(44);
    expect(close.height).toBeGreaterThanOrEqual(44);
    for (const t of await dlg.getByTestId('source-toggle').all()) await expect(t).toHaveAttribute('aria-expanded', 'false');
    await page.screenshot({ path: `${SHOTS}/mobile-01-dialog.png` });
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
