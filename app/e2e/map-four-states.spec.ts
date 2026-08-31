import { test, expect } from '@playwright/test';

/**
 * 任務 3.14 的四態，這次用 Playwright（不受這次對話環境的 WebGL 限制，見
 * `playwright.config.ts` 說明）第一次做到真實瀏覽器視覺驗證——task 3.14 動工當時
 * 只能用 jsdom 單元測試驗證邏輯，沒能力親眼確認畫面。截圖存到 `e2e/screenshots/`
 * （gitignore 排除，不進版控，純粹這次驗證用），對應 Phase 3「驗證標準」的「四態畫面
 * 截圖存查」。
 */
test.describe('主地圖頁四態（task 3.14）', () => {
  test('success：疆域資料載入完成後正常顯示地圖', async ({ page }) => {
    await page.goto('/');
    await page.waitForResponse((res) => res.url().includes('/api/v1/territories?year=225') && res.ok());

    await expect(page.locator('.map-loading-overlay')).toHaveCount(0);
    await expect(page.locator('.map-status-banner')).toHaveCount(0);
    await page.screenshot({ path: 'e2e/screenshots/map-success.png' });
  });

  test('loading：疆域資料回來前顯示全畫面骨架', async ({ page }) => {
    // 攔截疆域請求、故意延遲回應，爭取時間截到 loading 畫面（真實環境這個狀態通常
    // 稍縱即逝，用 route 攔截刻意拖長，不是改動應用程式邏輯本身）。
    await page.route('**/api/v1/territories**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      await route.continue();
    });

    await page.goto('/');
    await expect(page.locator('.map-loading-overlay')).toBeVisible();
    await expect(page.locator('.map-loading-text')).toContainText('地圖載入中');
    await page.screenshot({ path: 'e2e/screenshots/map-loading.png' });
  });

  test('error：疆域查詢失敗時顯示錯誤提示列+重試按鈕，點重試能恢復成功', async ({ page }) => {
    let shouldFail = true;
    await page.route('**/api/v1/territories**', async (route) => {
      if (shouldFail) {
        await route.fulfill({ status: 500, contentType: 'application/json', body: '{"statusCode":500,"message":"INTERNAL_ERROR","data":null}' });
      } else {
        await route.continue();
      }
    });

    await page.goto('/');
    await expect(page.locator('.map-status-banner-error')).toBeVisible();
    await expect(page.locator('.map-status-banner-error')).toContainText('疆域資料載入失敗');
    await page.screenshot({ path: 'e2e/screenshots/map-error.png' });

    shouldFail = false;
    await page.locator('.map-status-retry').click();
    await expect(page.locator('.map-status-banner-error')).toHaveCount(0);
  });

  test('empty：查詢成功但這個年份沒有任何疆域時顯示空狀態提示', async ({ page }) => {
    await page.goto('/');
    await page.waitForResponse((res) => res.url().includes('/api/v1/territories?year=225') && res.ok());

    // 拖到 1 年——目前種子資料最早只到西元 196 年（建安），西元 1 年沒有任何政權疆域。
    const yearInput = page.locator('.time-scrubber-input');
    const emptyResponse = page.waitForResponse((res) => res.url().includes('/api/v1/territories?year=1') && res.ok());
    await yearInput.evaluate((el: HTMLInputElement) => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')!.set!;
      setter.call(el, '1');
      el.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await emptyResponse;

    const banner = page.locator('.map-status-banner');
    await expect(banner).toBeVisible();
    await expect(banner).not.toHaveClass(/map-status-banner-error/);
    await expect(banner).toContainText('查無政權疆域資料');
    await page.screenshot({ path: 'e2e/screenshots/map-empty.png' });
  });
});
