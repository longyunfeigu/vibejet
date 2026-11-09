import { createBdd } from 'playwright-bdd';
import { expect } from '@playwright/test';

const { Then } = createBdd();

// Cross-module shared steps
// Auto-detect: check page-level elements first; fall back to iframe if not visible

Then('the {string} button should be visible', async ({ page }, buttonName: string) => {
  const pageBtn = page.getByRole('button', { name: buttonName });
  const isOnPage = await pageBtn.isVisible({ timeout: 2000 }).catch(() => false);
  if (isOnPage) {
    await expect(pageBtn).toBeVisible({ timeout: 5000 });
  } else {
    await expect(
      page.frameLocator('iframe').getByRole('button', { name: buttonName })
    ).toBeVisible({ timeout: 10000 });
  }
});
