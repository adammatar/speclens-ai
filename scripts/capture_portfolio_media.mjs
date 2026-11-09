#!/usr/bin/env node
/**
 * Deterministic SpecLens portfolio screenshots + short demo video.
 * Uses Playwright Chromium with password-manager UI disabled (no Chrome "Save password?" bubble).
 */
import { chromium } from "../apps/web/node_modules/playwright/index.mjs";
import { mkdirSync, copyFileSync, existsSync, readdirSync } from "node:fs";
import { join } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname;
const BASE = process.env.SPECLENS_WEB_URL || "http://127.0.0.1:4173";
const API_KEY = process.env.SPECLENS_API_KEY || "speclens-local-dev-key";
const OUT = join(ROOT, "docs/portfolio/screenshots");
const MEDIA = join(ROOT, "docs/portfolio/media");
const ARTIFACTS = "/opt/cursor/artifacts";
const STORE_MEDIA = "/cursor/stores/bc-ed8d4787-2243-4d0b-ba5a-7465c054fb18/media";

mkdirSync(OUT, { recursive: true });
mkdirSync(MEDIA, { recursive: true });
mkdirSync(ARTIFACTS, { recursive: true });
mkdirSync(STORE_MEDIA, { recursive: true });

async function shot(page, name) {
  const path = join(OUT, name);
  await page.screenshot({ path, fullPage: false });
  copyFileSync(path, join(ARTIFACTS, `phase10-${name}`));
  copyFileSync(path, join(STORE_MEDIA, `phase10-${name}`));
  console.log("shot", path);
}

async function main() {
  const browser = await chromium.launch({
    headless: true,
    args: [
      "--disable-features=PasswordManagerOnboarding,PasswordCheck,PasswordManager,AutofillServerCommunication",
      "--disable-save-password-bubble",
      "--no-default-browser-check",
    ],
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    recordVideo: { dir: MEDIA, size: { width: 1280, height: 800 } },
    // Avoid treating the page as a login form for credential storage.
    httpCredentials: undefined,
  });

  const page = await context.newPage();

  // --- Sign-in (empty field) ---
  await page.goto(`${BASE}/sign-in`, { waitUntil: "networkidle" });
  await page.waitForSelector("#api-key");
  await page.fill("#api-key", "");
  await shot(page, "01-signin.webp");

  // --- Authenticate ---
  await page.fill("#api-key", API_KEY);
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes("sign-in"), { timeout: 15000 });
  await page.waitForSelector("text=Workspace");
  await page.waitForTimeout(500);
  await shot(page, "02-dashboard.webp");

  // --- Documents ---
  await page.click('a[href="/documents"]');
  await page.waitForSelector("text=Documents");
  await page.waitForTimeout(400);
  await shot(page, "03-documents.webp");

  // Open first document if present
  const docLink = page.locator('a[href^="/documents/"]').filter({ hasNotText: "Upload" }).first();
  if (await docLink.count()) {
    await docLink.click();
    await page.waitForTimeout(600);
    await shot(page, "04-document-detail.webp");
  }

  // --- Chat ---
  await page.click('a[href="/chat"]');
  await page.waitForSelector("text=Cited chat");
  await page.click("text=New conversation");
  await page.waitForURL(/\/chat\//);
  await page.fill("#q", "What does hierarchical chunking preserve?");
  await page.click('button[type="submit"]');
  await page.waitForSelector("text=Answer", { timeout: 20000 });
  await page.waitForTimeout(400);
  await shot(page, "05-chat.webp");

  // --- Requirements ---
  await page.click('a[href="/requirements"]');
  await page.waitForSelector("text=Requirements");
  await page.waitForTimeout(400);
  await shot(page, "06-requirements.webp");

  // --- Compare ---
  await page.click('a[href="/compare"]');
  await page.waitForSelector("text=Version compare");
  await page.waitForTimeout(300);
  await shot(page, "07-compare.webp");

  // --- Settings ---
  await page.click('a[href="/settings"]');
  await page.waitForSelector("text=Settings");
  await page.waitForTimeout(400);
  await shot(page, "08-settings.webp");

  await context.close();
  await browser.close();

  // Rename playwright video to stable name
  const videos = readdirSync(MEDIA).filter((f) => f.endsWith(".webm"));
  if (videos.length) {
    const src = join(MEDIA, videos[0]);
    const dest = join(MEDIA, "demo-walkthrough.webm");
    copyFileSync(src, dest);
    copyFileSync(dest, join(ARTIFACTS, "speclens-demo-walkthrough.webm"));
    copyFileSync(dest, join(STORE_MEDIA, "speclens-demo-walkthrough.webm"));
    console.log("video", dest);
  } else {
    console.warn("No video recorded");
  }

  console.log("done");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
