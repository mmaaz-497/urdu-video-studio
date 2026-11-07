import { expect, test } from '@playwright/test'
import { readFileSync } from 'node:fs'

const { E2E_EMAIL, E2E_PASSWORD, E2E_VIDEO_ID } = process.env

test.skip(!E2E_EMAIL || !E2E_PASSWORD || !E2E_VIDEO_ID, 'set E2E_EMAIL / E2E_PASSWORD / E2E_VIDEO_ID')

test('Download saves an .mp4 and leaves the player untouched', async ({ page }, testInfo) => {
  await page.goto('/login')
  await page.fill('input[type=email]', E2E_EMAIL!)
  await page.fill('input[type=password]', E2E_PASSWORD!)
  await page.click('button[type=submit]')
  await page.waitForURL(/\/(create|videos)/)

  const progressUrl = `/videos/${E2E_VIDEO_ID}/progress`
  await page.goto(progressUrl)
  const player = page.locator('video')
  await expect(player).toBeVisible()
  const before = await player.boundingBox()
  const urlBefore = page.url()

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: /download/i }).click(),
  ])

  // A real file download, named .mp4, with real MP4 bytes.
  expect(download.suggestedFilename()).toMatch(/^[A-Za-z0-9._-]+\.mp4$/)
  const saved = testInfo.outputPath(download.suggestedFilename())
  await download.saveAs(saved)
  const bytes = readFileSync(saved)
  expect(bytes.length).toBeGreaterThan(1000)
  expect(bytes.subarray(4, 8).toString('latin1')).toBe('ftyp')

  // The page did not navigate and the player did not change size.
  expect(page.url()).toBe(urlBefore)
  await expect(player).toHaveCount(1)
  expect(await player.boundingBox()).toEqual(before)
})
