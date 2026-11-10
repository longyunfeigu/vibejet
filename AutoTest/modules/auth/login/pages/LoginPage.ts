import { Page, expect } from '@playwright/test';
import { SESSION_STORAGE_KEY } from '../../../../core/helpers/constants';

// Login page: frontend/src/routes/login/index.tsx -> features/auth/components/LoginForm.tsx
export class LoginPage {
  constructor(private readonly page: Page) {}

  async open(): Promise<void> {
    await this.page.goto('/login', { waitUntil: 'domcontentloaded' });
    await expect(this.submitButton()).toBeVisible({ timeout: 30000 });
  }

  /**
   * Remove the stored session in this browser context. While a session exists /login
   * redirects to /, so load any app page, clear the key, then load /login again.
   */
  async dropStoredSession(): Promise<void> {
    await this.page.goto('/login', { waitUntil: 'domcontentloaded' });
    await this.page.evaluate((key) => localStorage.removeItem(key), SESSION_STORAGE_KEY);
    await this.open();
  }

  async expectOnLoginPage(): Promise<void> {
    await expect(this.page).toHaveURL(/\/login$/, { timeout: 30000 });
    await expect(this.submitButton()).toBeVisible({ timeout: 30000 });
  }

  async expectFields(...labels: string[]): Promise<void> {
    for (const label of labels) {
      await expect(this.page.getByLabel(label, { exact: true })).toBeVisible();
    }
  }

  /** Fill the form, submit, and wait for the login API to answer (success or failure). */
  async signIn(username: string, password: string): Promise<void> {
    await this.open();
    await this.page.getByLabel('用户名或邮箱', { exact: true }).fill(username);
    await this.page.getByLabel('密码', { exact: true }).fill(password);
    const answered = this.page.waitForResponse(
      (r) => r.url().includes('/api/v1/auth/login') && r.request().method() === 'POST',
    );
    await this.submitButton().click();
    await answered;
  }

  async submitEmptyForm(): Promise<void> {
    await this.open();
    await this.submitButton().click();
  }

  /** Inline validation message under a field (FormMessage). */
  async expectFieldMessage(text: string): Promise<void> {
    await expect(this.page.getByText(text, { exact: true })).toBeVisible({ timeout: 10000 });
  }

  /** Error toast raised by useLogin on a failed login (sonner). */
  async expectErrorToast(text: string): Promise<void> {
    await expect(this.page.getByText(text, { exact: true })).toBeVisible({ timeout: 10000 });
  }

  async expectNoStoredSession(): Promise<void> {
    const stored = await this.page.evaluate((key) => localStorage.getItem(key), SESSION_STORAGE_KEY);
    expect(stored).toBeNull();
  }

  private submitButton() {
    return this.page.getByRole('button', { name: '登录', exact: true });
  }
}
