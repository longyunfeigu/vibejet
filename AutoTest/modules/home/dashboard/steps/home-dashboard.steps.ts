import { createBdd } from 'playwright-bdd';
import { HomePage } from '../pages/HomePage';

const { Given, When, Then } = createBdd();

Given('my stored session holds tokens the backend rejects', async ({ page }) => {
  await new HomePage(page).storeRejectedSession();
});

When('I choose to sign in again', async ({ page }) => {
  await new HomePage(page).chooseSignInAgain();
});

Then('the dashboard sections {string} and {string} should be visible', async ({ page }, first: string, second: string) => {
  await new HomePage(page).expectSections(first, second);
});

Then('the top bar should offer {string}', async ({ page }, label: string) => {
  await new HomePage(page).expectTopBarButton(label);
});

Then('I should see the session-expired page', async ({ page }) => {
  await new HomePage(page).expectSessionExpired();
});
