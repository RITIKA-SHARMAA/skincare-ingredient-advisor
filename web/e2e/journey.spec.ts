import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

async function expectNoAccessibilityViolations(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
}

async function analyseAndSave(page: Page, ingredients: string, productName: string) {
  await page.goto('/analyse');
  await page.getByLabel('Ingredient list').fill(ingredients);
  await page.getByRole('button', { name: 'Analyse ingredients' }).click();
  await expect(page.getByRole('heading', { name: 'Analysis result' })).toBeVisible();
  await page.getByLabel('Save as product').fill(productName);
  await page.getByRole('button', { name: 'Save product' }).click();
  await expect(page.getByRole('status')).toContainText(`Saved “${productName}”`);
}

test('paste ingredients, save products, and see a routine conflict', async ({ page }) => {
  const run = Date.now().toString(36);
  const peel = `Peel ${run}`;
  const serum = `Night serum ${run}`;

  await page.goto('/analyse');
  await expectNoAccessibilityViolations(page);

  await analyseAndSave(page, 'Aqua, Glycolic Acid, Unobtainium Extract', peel);
  const ingredients = page.getByRole('list', { name: 'Ingredients' });
  await expect(ingredients.getByRole('listitem')).toHaveCount(2);
  await expect(page.getByText('Listed as “aqua” (alias match)')).toBeVisible();
  await expect(page.getByText('unobtainium extract')).toBeVisible();
  await expectNoAccessibilityViolations(page);

  await analyseAndSave(page, 'Squalane, Retinol', serum);

  await page.goto('/routine');
  await page.getByLabel('New routine name').fill(`Evening ${run}`);
  await page.getByRole('button', { name: 'Create routine' }).click();
  await expect(page.getByRole('heading', { name: `Evening ${run}` })).toBeVisible();

  for (const name of [peel, serum]) {
    await page.getByLabel('Product', { exact: true }).selectOption({ label: name });
    await page.getByLabel('Slot').selectOption('evening');
    await page.getByRole('button', { name: 'Add to routine' }).click();
    await expect(page.getByRole('button', { name: `Remove ${name}` })).toBeVisible();
  }

  await expect(page.getByRole('list', { name: 'Conflicts' })).toContainText(
    `${peel} + ${serum} (evening, high)`,
  );
  await expectNoAccessibilityViolations(page);
});

test('validation errors are announced without calling the API', async ({ page }) => {
  await page.goto('/analyse');
  await page.getByRole('button', { name: 'Analyse ingredients' }).click();
  await expect(page.getByText('Paste at least one ingredient')).toBeVisible();
  await expect(page.getByLabel('Ingredient list')).toHaveAttribute('aria-invalid', 'true');
});
