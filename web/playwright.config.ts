import { defineConfig, devices } from '@playwright/test';

// Starts the API and a production build of the web app unless they are already running.
// The API needs DATABASE_URL pointing at a PostgreSQL database it can migrate and seed.
const api = process.env.E2E_API_URL ?? 'http://localhost:8000';

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
    launchOptions: process.env.CHROMIUM_PATH
      ? { executablePath: process.env.CHROMIUM_PATH }
      : undefined,
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: [
    {
      command:
        'cd ../api && alembic upgrade head && python -m app.seed && uvicorn app.main:app --port 8000',
      url: `${api}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: 'npm run build && npm run start -- --port 3000',
      url: 'http://localhost:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 240_000,
    },
  ],
});
