import { test, expect, type Page } from '@playwright/test';
import { projectOffsetFromCenter } from './helpers/map-projection';

/**
 * 任務 3.16：E2E 測試主流程（時間拖動→疆域形變→聚焦→事件詳情），PRD M3 驗收門檻。
 *
 * **對照真實種子資料，不是憑空編造的測試資料**：西元 208 年（赤壁之戰當年）吳、蜀漢
 * 都有疆域快照（見 `api/Data/SeedData.cs`），赤壁之戰是目前種子資料裡內容最完整的
 * 一筆事件（`sections` 三段內容 + 三筆視角 + 一筆爭議點），拿來當「事件詳情」步驟的
 * 驗證目標最能涵蓋畫面上實際會出現的內容。
 *
 * **刻意不用 `data-testid`**：PRD §7「關鍵互動的 data-testid 不在 PRD 預先臆測名稱，
 * M3 實作元件時依 3.16 E2E 主流程同步定義」——這次盤點發現既有元件的 CSS class 命名
 * 本身已經夠具體穩定（例如 `.regime-event-panel-trigger`，這學期單元測試也一路沿用
 * 同一組 class 當選擇器），另外疊一層 `data-testid` 屬性是重複的識別機制，不是必要的
 * 補強，所以沿用既有 class，不追加新屬性。
 */

async function waitForInitialTerritories(page: Page): Promise<void> {
  await page.goto('/');
  await page.waitForResponse((res) => res.url().includes('/api/v1/territories?year=225') && res.ok());
}

async function clickTerritoryAt(page: Page, lng: number, lat: number): Promise<void> {
  const canvas = page.locator('canvas.maplibregl-canvas');
  const box = await canvas.boundingBox();
  if (!box) {
    throw new Error('地圖 canvas 找不到 bounding box');
  }
  const { dx, dy } = projectOffsetFromCenter(lng, lat);
  await page.mouse.click(box.x + box.width / 2 + dx, box.y + box.height / 2 + dy);
}

test('主流程：時間拖動 → 疆域形變 → 聚焦 → 事件詳情', async ({ page }) => {
  await waitForInitialTerritories(page);

  // --- 1. 時間拖動：把拉桿從預設的 225 年拖到 208 年（赤壁之戰當年）---
  await expect(page.locator('.time-scrubber-year')).toContainText('西元 225 年');

  const yearInput = page.locator('.time-scrubber-input');
  const territoriesResponse = page.waitForResponse(
    (res) => res.url().includes('/api/v1/territories?year=208') && res.ok(),
  );
  await yearInput.evaluate((el: HTMLInputElement) => {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')!.set!;
    setter.call(el, '208');
    el.dispatchEvent(new Event('input', { bubbles: true }));
  });

  // --- 2. 疆域形變：等新年份的疆域資料回來（換年份後 900ms 內會跑 Flubber.js 形變
  //    動畫，見 task 3.6），拉桿文字應該同步更新到新年份。---
  await territoriesResponse;
  await expect(page.locator('.time-scrubber-year')).toContainText('西元 208 年');
  await page.waitForTimeout(1000); // 等形變動畫播完，畫面上的疆域穩定下來再點擊

  // --- 3. 聚焦：點擊吳的疆域（東南角，跟蜀漢/漢的疆域不重疊的乾淨區域，避免點到
  //    荊州爭議重疊區造成點擊目標歧義）---
  await clickTerritoryAt(page, 119, 27);

  const focusPanel = page.locator('.regime-focus-panel');
  await expect(focusPanel).toBeVisible();
  await expect(focusPanel.locator('h2')).toHaveText('吳');

  // --- 4. 事件詳情：政權事件記錄 overlay 應該列出赤壁之戰，點開後顯示詳情 ---
  const eventPanel = page.locator('.regime-event-panel');
  await expect(eventPanel).toBeVisible();
  const chibiTrigger = eventPanel.locator('.regime-event-panel-trigger', { hasText: '赤壁之戰' });
  await expect(chibiTrigger).toBeVisible();

  await chibiTrigger.click();

  const detail = eventPanel.locator('.regime-event-panel-detail');
  await expect(detail).toBeVisible();
  // 赤壁之戰有三筆視角（task 2.12 種子資料），應該看得到分頁列，預設在客觀經過概要。
  await expect(eventPanel.locator('.regime-event-panel-tab')).toContainText(['客觀經過概要']);
  await expect(detail).toContainText('背景起因');
  await expect(detail).toContainText('關鍵爭議點'); // task 2.13 種子資料：曹操兵力爭議

  // 存查用截圖——這是這次對話環境第一次能親眼看到「聚焦面板 + 政權事件面板 + 手風琴
  // 展開＋分頁列 + 爭議點」這條完整鏈路實際渲染出來的樣子（task 3.12/3.13 動工當時
  // 都只能靠單元測試涵蓋邏輯，見該任務完成記錄）。
  await page.screenshot({ path: 'e2e/screenshots/main-flow-event-detail.png' });
});

/**
 * 2026-08-31 使用者回報：手風琴展開內文較長時，卡片仍錨定在政權疆域位置——疆域若
 * 靠近畫面上緣（例如這裡測的魏），展開後的內容會被裁到視窗外面（見
 * regime-event-panel.scss `[data-detail-expanded]` 規則的說明）。單元測試只能驗證
 * host 屬性有沒有正確綁定，驗不到「MapLibre Marker 的 will-change: transform 會讓
 * 子元素 position: fixed 相對 host 定位、蓋錯層級就不是真正畫面正中央」這種只有真實
 * CSS 佈局引擎才躲得掉的錯誤——這正是這次對話環境保留 Playwright 真實瀏覽器測試的
 * 理由，故意選魏（種子資料 `Rect(105,32,122,42)`，疆域中心貼近畫面上緣）當測試對象，
 * 不選蜀漢/吳（比較靠畫面中下段，就算沒修好這個 bug 也不容易露出裁切問題）。
 */
test('政權事件面板展開手風琴時，卡片改為釘在畫面正中央（避免疆域靠近畫面邊緣時內容被裁掉）', async ({
  page,
}) => {
  await waitForInitialTerritories(page);
  await clickTerritoryAt(page, 113.5, 37); // 魏的疆域中心，靠近畫面上緣

  const focusPanel = page.locator('.regime-focus-panel');
  await expect(focusPanel.locator('h2')).toHaveText('魏');

  const eventPanel = page.locator('.regime-event-panel');
  const trigger = eventPanel.locator('.regime-event-panel-trigger', { hasText: '漢獻帝禪位於魏' });
  await expect(trigger).toBeVisible();
  await trigger.click();
  await expect(eventPanel.locator('.regime-event-panel-detail')).toBeVisible();

  const panelBox = await eventPanel.boundingBox();
  const viewport = page.viewportSize()!;
  expect(panelBox).not.toBeNull();

  // 完整落在視窗範圍內，沒有任何一邊被裁掉
  expect(panelBox!.y).toBeGreaterThanOrEqual(0);
  expect(panelBox!.y + panelBox!.height).toBeLessThanOrEqual(viewport.height);
  expect(panelBox!.x).toBeGreaterThanOrEqual(0);
  expect(panelBox!.x + panelBox!.width).toBeLessThanOrEqual(viewport.width);

  // 大致置中（容許幾像素的次像素捨入誤差）
  expect(Math.abs(panelBox!.x + panelBox!.width / 2 - viewport.width / 2)).toBeLessThan(5);
  expect(Math.abs(panelBox!.y + panelBox!.height / 2 - viewport.height / 2)).toBeLessThan(5);
});
