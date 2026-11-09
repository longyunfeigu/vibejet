import { createBdd } from 'playwright-bdd';
import { LoginPage } from '../../auth/login/pages/LoginPage';
import { HomePage } from '../../home/dashboard/pages/HomePage';
import { getE2EConfig } from '../../../config/env-config';

const { Given, When, Then } = createBdd();

// Session steps shared by the auth and home modules. Every project starts signed in as the
// test account (storage state from config/global-setup.ts); "I am signed out" drops it.

Given('I am signed out', async ({ page }) => {
  await new LoginPage(page).dropStoredSession();
});

When('I open the home page', async ({ page }) => {
  await new HomePage(page).open();
});

Then('I should be on the login page', async ({ page }) => {
  await new LoginPage(page).expectOnLoginPage();
});

Then('the home page should greet the test account', async ({ page }) => {
  await new HomePage(page).expectGreeting(getE2EConfig().username);
});

Then('no session should be stored', async ({ page }) => {
  await new LoginPage(page).expectNoStoredSession();
});
