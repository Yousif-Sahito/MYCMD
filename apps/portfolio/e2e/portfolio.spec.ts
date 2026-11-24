import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('navigates required public pages and deep-linked project', async ({ page }, testInfo) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Build. Operate. Explore.' })).toBeVisible()
  for (const name of ['Terminal', 'Projects', 'Skills', 'Education', 'Certificates', 'Milestones', 'About', 'Contact', 'Settings']) {
    await page.getByRole('link', { name }).first().click()
    await expect(page.locator('main')).toBeVisible()
  }
  await page.goto('/projects/mycmd-cli')
  await expect(page.getByRole('heading', { name: 'MYCMD CLI' })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'MYCMD CLI' })).toBeVisible()

  if (testInfo.project.name === 'desktop') {
    const accessibility = await new AxeBuilder({ page }).analyze()
    expect(accessibility.violations).toEqual([])
  }
})

test('portfolio terminal executes allowlisted commands and rejects shell commands', async ({ page }) => {
  await page.goto('/terminal')
  await expect(page.getByRole('heading', { name: 'MYCMD Portfolio Terminal' })).toBeVisible()
  if ((await page.viewportSize())?.width && (await page.viewportSize())!.width <= 640) {
    const input = page.getByLabel('Enter a portfolio command')
    await input.fill('help')
    await page.getByRole('button', { name: 'Execute' }).click()
    await expect(page.getByLabel('Terminal output')).toContainText('MYCMD Portfolio Terminal')
    await input.fill('ls')
    await page.getByRole('button', { name: 'Execute' }).click()
    await expect(page.getByLabel('Terminal output')).toContainText('Command not supported')
  } else {
    await page.locator('.xterm-host').click()
    await page.keyboard.type('help')
    await page.keyboard.press('Enter')
    await expect(page.getByLabel('Terminal output')).toContainText('MYCMD Portfolio Terminal')
    await page.keyboard.type('ls')
    await page.keyboard.press('Enter')
    await expect(page.getByLabel('Terminal output')).toContainText('Command not supported')
  }
})

test('unknown route and mobile width stay usable', async ({ page }) => {
  await page.goto('/not-a-real-route')
  await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Return home' })).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(1)
})

test('captures responsive visual baselines', async ({ page }, testInfo) => {
  const routes = [
    ['home', '/'],
    ['terminal', '/terminal'],
    ['projects', '/projects'],
    ['project-detail', '/projects/mycmd-cli'],
    ['skills', '/skills'],
    ['education', '/education'],
    ['certificates', '/certificates'],
    ['milestones', '/milestones'],
    ['contact', '/contact'],
    ['not-found', '/missing'],
  ]
  for (const [name, route] of routes) {
    await page.goto(route!)
    await expect(page.locator('main')).toBeVisible()
    await page.screenshot({
      path: `test-results/${testInfo.project.name}-${name}.png`,
      fullPage: true,
    })
  }
})
