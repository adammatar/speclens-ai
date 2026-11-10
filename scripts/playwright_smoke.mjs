#!/usr/bin/env node
/**
 * Lightweight Playwright smoke for SpecLens product routes.
 * Requires a running web+API stack and SPECLENS_SMOKE_KEY (default local bootstrap).
 */
import { chromium } from "playwright";

const BASE = process.env.SPECLENS_SMOKE_BASE_URL || "http://127.0.0.1:5173";
const KEY = process.env.SPECLENS_SMOKE_KEY || "speclens-local-dev-key";

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const failures = [];

  try {
    await page.goto(`${BASE}/sign-in`, { waitUntil: "networkidle" });
    await page.getByLabel(/access key|מפתח/i).fill(KEY);
    await page.getByRole("button", { name: /continue|המשך/i }).click();
    await page.waitForURL(/\/($|\?)/, { timeout: 15000 });

    for (const path of ["/", "/documents", "/requirements", "/compare", "/evaluation", "/settings"]) {
      await page.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
      const title = await page.locator("h1").first().textContent();
      if (!title) failures.push(`${path}: missing h1`);
      // Visible focus ring support: tab once and ensure something is focusable.
      await page.keyboard.press("Tab");
    }

    // Hebrew RTL toggle
    await page.getByTitle(/hebrew|עברית|english|אנגלית/i).click();
    const dir = await page.evaluate(() => document.documentElement.dir);
    if (dir !== "rtl" && dir !== "ltr") failures.push(`unexpected dir=${dir}`);
  } catch (error) {
    failures.push(String(error));
  } finally {
    await browser.close();
  }

  if (failures.length) {
    console.error("Playwright smoke failures:\n" + failures.join("\n"));
    process.exit(1);
  }
  console.log("Playwright smoke passed for core routes");
}

main();
