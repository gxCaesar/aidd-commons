import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:4324",
    trace: "on-first-retry",
  },
  webServer: {
    command:
      "npm --prefix site run preview -- --ignore-lock --host 127.0.0.1 --port 4324",
    env: { ASTRO_PREVIEW_BACKGROUND: "0" },
    port: 4324,
    reuseExistingServer: false,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], channel: "chrome" },
    },
    {
      name: "mobile-chromium",
      use: { ...devices["Pixel 7"], channel: "chrome" },
    },
  ],
});
