import { defineConfig } from '@playwright/test'

// Run against an already-running stack (frontend + backend + a seeded Ready video):
//   cd backend && .venv/bin/python -m scripts.seed_e2e_video   # prints email/password/videoId
//   E2E_EMAIL=... E2E_PASSWORD=... E2E_VIDEO_ID=... npx playwright test
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  reporter: 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    acceptDownloads: true,
    viewport: { width: 1280, height: 900 },
    // Optional: use an already-installed Chromium instead of the one Playwright pins.
    launchOptions: process.env.E2E_CHROMIUM_PATH
      ? { executablePath: process.env.E2E_CHROMIUM_PATH }
      : {},
  },
})
