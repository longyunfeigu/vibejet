import { Page, expect } from '@playwright/test';
import { SESSION_STORAGE_KEY } from '../../../../core/helpers/constants';

// Home page: frontend/src/routes/index.tsx -> features/home/components/HomeDashboard.tsx
export class HomePage {
  constructor(private readonly page: Page) {}

  async open(): Promise<void> {
    await this.page.goto('/', { waitUntil: 'domcontentloaded' });
  }

  async expectGreeting(name: string): Promise<void> {
    await expect(this.page.getByRole('heading', { level: 1, name: `你好，${name}` })).toBeVisible({ timeout: 30000 });
  }

  async expectSections(...titles: string[]): Promise<void> {
    for (const title of titles) {
      await expect(this.page.getByRole('heading', { level: 2, name: title })).toBeVisible();
    }
  }

  async expectTopBarButton(label: string): Promise<void> {
    await expect(this.page.getByRole('button', { name: label })).toBeVisible();
  }

  async signOut(): Promise<void> {
    await this.page.getByRole('button', { name: '退出' }).click();
    await expect(this.page).toHaveURL(/\/login$/, { timeout: 30000 });
  }

  /** Replace the stored token pair with values the backend rejects (both access and refresh). */
  async storeRejectedSession(): Promise<void> {
    await this.page.goto('/login', { waitUntil: 'domcontentloaded' });
    await this.page.evaluate(
      (key) => localStorage.setItem(key, JSON.stringify({ accessToken: 'invalid-access', refreshToken: 'invalid-refresh' })),
      SESSION_STORAGE_KEY,
    );
  }

  async expectSessionExpired(): Promise<void> {
    await expect(this.page.getByRole('heading', { level: 1, name: '会话已失效' })).toBeVisible({ timeout: 30000 });
  }

  async chooseSignInAgain(): Promise<void> {
    await this.page.getByRole('button', { name: '重新登录' }).click();
  }
}
