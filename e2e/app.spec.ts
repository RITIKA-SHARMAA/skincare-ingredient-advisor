import {test,expect} from '@playwright/test';
test('analyse journey',async({page})=>{await page.goto('/analyse');await page.getByText('Ingredient list').locator('..').locator('textarea').fill('Water, Glycerin, Niacinamide, Salicylic Acid');await page.getByRole('button',{name:/analyse ingredients/i}).click();await expect(page.getByRole('heading',{name:/analysis result/i})).toBeVisible();});
