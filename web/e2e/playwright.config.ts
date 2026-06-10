import { defineConfig } from "@playwright/test";

// Run against the docker-compose stack started in MOCK_FETCH mode.
export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:8080",
    acceptDownloads: true,
  },
});
