import { createBdd } from 'playwright-bdd';
import { HomePage } from '../pages/HomePage';
import { getE2EConfig } from '../../../../config/env-config';

const { Given, When, Then } = createBdd();

Given('my stored session holds tokens the backend rejects', async ({ page }) => {
  await new HomePage(page).storeRejectedSession();
});

When('I choose to sign in again', async ({ page }) => {
  await new HomePage(page).chooseSignInAgain();
});

Then('the home page should greet the test account', async ({ page }) => {
  await new HomePage(page).expectGreeting(getE2EConfig().username);
});

Then('the dashboard sections {string} and {string} should be visible', async ({ page }, first: string, second: string) => {
  await new HomePage(page).expectSections(first, second);
});

Then('I should see the session-expired page', async ({ page }) => {
  await new HomePage(page).expectSessionExpired();
});
