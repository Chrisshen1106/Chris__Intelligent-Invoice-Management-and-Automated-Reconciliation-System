/**
 * E2E tests for the public entry and auth flow.
 *
 * These tests cover the unauthenticated entry route and verify that
 * the current login page renders correctly.
 *
 * Supabase network calls are intercepted via page.route() so the tests
 * run without a real Supabase connection. MSW handles /api/* mocks
 * (enabled via VITE_API_MOCK_ENABLED=true in playwright.config.js).
 *
 * Limitation: Full OCR-submit flow requires auth state, which needs
 * Supabase session injection - add in future iterations.
 */
import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('**/supabase.co/**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ data: { session: null }, error: null }),
  }));
});

// -- Public entry / login page render -----------------------------------------

test('should redirect unauthenticated visitors from root to login', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/login$/);
});

test('should display the current auth brand and sign-in title', async ({ page }) => {
  await page.goto('/login');
  await expect(page.locator('.brand-logo')).toContainText('IIMARS');
  await expect(page.locator('.brand-title')).toContainText('智慧發票管理與自動化對帳');
  await expect(page.locator('.login-title')).toContainText('登入帳號');
});

// -- Auth controls -------------------------------------------------------------

test('should show Google and email/password login controls', async ({ page }) => {
  await page.goto('/login');
  await expect(page.locator('.btn-google')).toContainText('使用 Google 繼續');
  await expect(page.locator('input[type="email"]')).toBeVisible();
  await expect(page.locator('input[type="password"]')).toBeVisible();
  await expect(page.locator('button[type="submit"]')).toContainText('登入');
});

test('should show validation error when submitting empty email login form', async ({ page }) => {
  await page.goto('/login');
  await page.locator('button[type="submit"]').click();
  await expect(page.locator('.error-msg')).toContainText('請輸入電子信箱與密碼');
});

// -- Language switcher ---------------------------------------------------------

test('should switch UI language to English', async ({ page }) => {
  await page.goto('/login');
  await page.locator('.floating-lang select').selectOption('en');
  await expect(page.locator('.login-title')).toContainText('Sign in');
  await expect(page.locator('.btn-google')).toContainText('Continue with Google');
  await expect(page.locator('.brand-title')).toContainText('Smart invoice management');
});

// -- Register navigation -------------------------------------------------------

test('should navigate to register page from login footer', async ({ page }) => {
  await page.goto('/login');
  await page.locator('.login-footer a').click();
  await expect(page).toHaveURL(/\/register$/);
  await expect(page.locator('.register-title')).toContainText('建立帳號');
});
