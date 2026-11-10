#!/usr/bin/env node
/**
 * Deterministic SpecLens AI portfolio screenshots + short demo video.
 * Uses Playwright Chromium with password-manager UI disabled (no Chrome "Save password?" bubble).
 * Targets the Home split workspace UX (documents | chat) after the iOS redesign.
 */
import { chromium } from "../apps/web/node_modules/playwright/index.mjs";
import { mkdirSync, copyFileSync, existsSync, readdirSync, unlinkSync } from "node:fs";
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
  copyFileSync(path, join(ARTIFACTS, `portfolio-${name}`));
  copyFileSync(path, join(STORE_MEDIA, `portfolio-${name}`));
  console.log("shot", path);
}

async function main() {
  // Clear prior playwright temp videos so rename is deterministic.
  if (existsSync(MEDIA)) {
    for (const f of readdirSync(MEDIA)) {
      if (f.endsWith(".webm") && f !== "demo-walkthrough.webm") {
        try {
          unlinkSync(join(MEDIA, f));
        } catch {
          // ignore
        }
      }
    }
  }

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
    httpCredentials: undefined,
  });

  const page = await context.newPage();

  // --- Sign-in (empty field, SpecLens AI brand) ---
  await page.goto(`${BASE}/sign-in`, { waitUntil: "networkidle" });
  await page.waitForSelector("#api-key");
  await page.fill("#api-key", "");
  await page.waitForSelector("text=SpecLens");
  await shot(page, "01-signin.webp");

  // --- Authenticate → Home workspace ---
  await page.fill("#api-key", API_KEY);
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes("sign-in"), { timeout: 15000 });
  await page.waitForSelector("text=Workspace");
  await page.waitForTimeout(700);
  await shot(page, "02-home.webp");

  // --- Documents library ---
  await page.click('a[href="/documents"]');
  await page.waitForSelector("h1");
  await page.waitForTimeout(500);
  await shot(page, "03-documents.webp");

  // Open first document if present
  const docLink = page.locator('a[href^="/documents/"]').first();
  if (await docLink.count()) {
    await docLink.click();
    await page.waitForTimeout(700);
    await shot(page, "04-document-detail.webp");
  }

  // --- Back to Home chat ---
  await page.click('a[href="/"]');
  await page.waitForSelector("text=Workspace");
  await page.waitForTimeout(500);

  // Select first ready document for chat (button becomes "In chat")
  const chatBtn = page.locator(".doc-row-actions button.btn.sm").filter({ hasText: /Chat|צ׳אט/ }).first();
  await chatBtn.waitFor({ timeout: 10000 });
  await chatBtn.click();
  await page.waitForSelector("text=In chat", { timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(400);

  const composer = page.locator(".chat-composer textarea").first();
  await composer.waitFor({ timeout: 10000 });
  await composer.fill("What does hierarchical chunking preserve?");
  await page.locator(".chat-composer button[type='submit']").click();
  await page.locator(".bubble.user").first().waitFor({ timeout: 10000 });
  await page.locator(".bubble.assistant").first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(800);
  await shot(page, "05-chat.webp");

  // --- Requirements workspace ---
  await page.click('a[href="/requirements"]');
  await page.waitForSelector("h1");
  await page.waitForTimeout(600);
  await shot(page, "06-requirements.webp");

  // --- Version compare workspace ---
  await page.click('a[href="/compare"]');
  await page.waitForSelector("h1");
  await page.waitForTimeout(600);
  await shot(page, "07-compare.webp");

  // --- Evaluation dashboard ---
  await page.click('a[href="/evaluation"]');
  await page.waitForSelector("h1");
  await page.waitForTimeout(600);
  await shot(page, "08-evaluation.webp");

  // --- Settings ---
  await page.click('a[href="/settings"]');
  await page.waitForSelector("h1");
  await page.waitForTimeout(400);
  await shot(page, "09-settings.webp");

  // --- Hebrew RTL screen ---
  const langToggle = page.locator("button.lang-toggle").first();
  if (await langToggle.count()) {
    await langToggle.click();
    await page.waitForTimeout(500);
    await shot(page, "10-hebrew-ui.webp");
    await langToggle.click();
    await page.waitForTimeout(300);
  }

  await context.close();
  await browser.close();

  // Rename playwright video to stable name
  const videos = readdirSync(MEDIA).filter((f) => f.endsWith(".webm") && f !== "demo-walkthrough.webm");
  const pick = videos[0] || (existsSync(join(MEDIA, "demo-walkthrough.webm")) ? "demo-walkthrough.webm" : null);
  if (pick && pick !== "demo-walkthrough.webm") {
    const src = join(MEDIA, pick);
    const dest = join(MEDIA, "demo-walkthrough.webm");
    copyFileSync(src, dest);
    try {
      unlinkSync(src);
    } catch {
      // ignore
    }
    copyFileSync(dest, join(ARTIFACTS, "speclens-demo-walkthrough.webm"));
    copyFileSync(dest, join(STORE_MEDIA, "speclens-demo-walkthrough.webm"));
    console.log("video", dest);
  } else if (pick === "demo-walkthrough.webm") {
    const dest = join(MEDIA, "demo-walkthrough.webm");
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
