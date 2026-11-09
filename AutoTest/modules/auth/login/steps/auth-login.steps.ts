import { createBdd } from 'playwright-bdd';
import { expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { HomePage } from '../../../home/dashboard/pages/HomePage';
import { ApiClient } from '../../../../core/api/client';
import { getE2EConfig } from '../../../../config/env-config';

const { When, Then } = createBdd();

When('I sign in as the test account', async ({ page }) => {
  const { username, password } = getE2EConfig();
  await new LoginPage(page).signIn(username, password);
});

When('I sign in as the test account with the password {string}', async ({ page }, password: string) => {
  await new LoginPage(page).signIn(getE2EConfig().username, password);
});

When('I submit the empty login form', async ({ page }) => {
  await new LoginPage(page).submitEmptyForm();
});

When('I sign out from the top bar', async ({ page }) => {
  await new HomePage(page).signOut();
});

Then('the login form should show the {string} and {string} fields', async ({ page }, first: string, second: string) => {
  await new LoginPage(page).expectFields(first, second);
});

Then('the account API should report the test account as signed in', async ({ page }) => {
  const me = await new ApiClient(page).getJson<{ data: { username: string } }>('/api/v1/auth/me');
  expect(me.data.username).toBe(getE2EConfig().username);
});

Then('the login error {string} should be shown', async ({ page }, text: string) => {
  await new LoginPage(page).expectErrorToast(text);
});

Then('the field message {string} should be shown', async ({ page }, text: string) => {
  await new LoginPage(page).expectFieldMessage(text);
});
