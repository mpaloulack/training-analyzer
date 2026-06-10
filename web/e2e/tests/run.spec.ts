import { test, expect } from "@playwright/test";

// These run against the stack started with MOCK_FETCH=1, so no real
// Intervals.icu credentials or network calls are needed — the journey
// (fill form → submit → download the JSON) is what we verify.

test("happy path: fill the form and download the JSON", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Training Analyzer" })).toBeVisible();

  await page.getByLabel("Athlete ID").fill("882231");
  await page.getByLabel("API key").fill("abcd1234efgh5678");

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: /generate/i }).click();

  // Live progress log appears before the download completes.
  await expect(page.getByLabel("progress log")).toBeVisible();

  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("training_data.json");
  const path = await download.path();
  expect(path).toBeTruthy();

  await expect(page.getByRole("status")).toContainText(/done/i);
});

test("client-side validation blocks a bad athlete id", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Athlete ID").fill("not-an-id");
  await page.getByLabel("API key").fill("abcd1234efgh5678");
  await page.getByRole("button", { name: /generate/i }).click();

  await expect(page.getByRole("alert")).toContainText(/athlete id/i);
});
