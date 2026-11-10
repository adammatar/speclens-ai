#!/usr/bin/env node
/**
 * Deterministic SpecLens AI portfolio screenshots + short demo video.
 * Uses Playwright Chromium with password-manager UI disabled (no Chrome "Save password?" bubble).
 * Fails loudly when expected product data is missing (never saves empty core screens).
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

async function assertVisible(locator, label, timeout = 20000) {
  try {
    await locator.first().waitFor({ state: "visible", timeout });
  } catch (err) {
    throw new Error(`Portfolio capture assertion failed: ${label} not visible. ${err}`);
  }
  const count = await locator.count();
  if (count < 1) {
    throw new Error(`Portfolio capture assertion failed: ${label} count=0`);
  }
}

async function main() {
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

  // 1. Sign-in
  await page.goto(`${BASE}/sign-in`, { waitUntil: "networkidle" });
  await page.getByLabel(/workspace access key|מפתח/i).waitFor({ timeout: 15000 }).catch(async () => {
    await page.locator("#api-key").waitFor();
  });
  await page.locator("#api-key").fill("");
  await page.getByText("SpecLens").first().waitFor();
  await shot(page, "01-signin.webp");

  // Authenticate → 2. Home workspace
  await page.locator("#api-key").fill(API_KEY);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((url) => !url.pathname.includes("sign-in"), { timeout: 15000 });
  await page.getByRole("heading", { name: /Workspace|סביבת עבודה/i }).waitFor({ timeout: 15000 });
  await page.waitForTimeout(500);
  await shot(page, "02-home.webp");

  const nav = page.locator("nav").first();

  // 3. Documents library
  await nav.getByRole("link", { name: /^Documents$|^מסמכים$/ }).click();
  await page.getByRole("heading", { name: /Documents|מסמכים/i }).waitFor();
  await assertVisible(page.getByText(/Demo Sample Spec/i), "documents list contains Demo Sample Spec");
  await page.waitForTimeout(400);
  await shot(page, "03-documents.webp");

  // 4. Document detail / version history
  const docLink = page.locator('a[href^="/documents/"]').filter({ hasText: /Demo Sample Spec/i }).first();
  await assertVisible(docLink, "Demo Sample Spec document link");
  await docLink.click();
  await page.getByText(/Demo Sample Spec/i).first().waitFor({ timeout: 10000 });
  await assertVisible(page.getByText(/\bv[12]\b/i), "document version history (v1/v2)");
  await page.waitForTimeout(500);
  await shot(page, "04-document-detail.webp");

  // 5. Cited chat on Home
  await nav.getByRole("link", { name: /^Home$|^בית$/ }).click();
  await page.getByRole("heading", { name: /Workspace|סביבת עבודה/i }).waitFor();
  const chatBtn = page
    .locator(".doc-row-actions button.btn.sm")
    .filter({ hasText: /Chat|צ׳אט|צ'אט/ })
    .first();
  await assertVisible(chatBtn, "Chat action on document row");
  await chatBtn.click();
  await page.getByText(/In chat|בצ׳אט|בצ'אט/i).first().waitFor({ timeout: 8000 }).catch(() => {});

  const composer = page.locator(".chat-composer textarea").first();
  await assertVisible(composer, "chat composer");
  await composer.fill("What does hierarchical chunking preserve?");
  await page.locator(".chat-composer button[type='submit']").click();
  await assertVisible(page.getByTestId("chat-assistant-bubble"), "completed assistant answer", 45000);
  await assertVisible(
    page.getByTestId("chat-citation").or(page.locator(".cite-note")),
    "citation / source indicator",
    15000,
  );
  await page.waitForTimeout(400);
  await shot(page, "05-chat.webp");

  // 6. Populated Requirements
  await nav.getByRole("link", { name: /^Requirements$|^דרישות$/ }).click();
  await page.getByRole("heading", { name: /Requirements|דרישות/i }).waitFor();
  await assertVisible(page.getByTestId("requirement-row"), "extracted requirement row", 20000);
  await assertVisible(
    page.getByTestId("requirement-provenance").or(page.getByTestId("requirement-quote")),
    "requirement provenance / quote",
  );
  if (await page.locator(".empty").filter({ hasText: /No requirements|אין דרישות/i }).count()) {
    throw new Error("Requirements page still shows empty state");
  }
  await page.waitForTimeout(300);
  await shot(page, "06-requirements.webp");

  // 7. Populated Compare (must run compare so changes are visible)
  await nav.getByRole("link", { name: /^Compare$|^השוואה$/ }).click();
  await page.getByRole("heading", { name: /Compare|השוואת/i }).waitFor();
  const startCmp = page.getByTestId("compare-start");
  await assertVisible(startCmp, "Compare start button");
  await startCmp.click();
  await assertVisible(page.getByTestId("compare-change-item"), "completed comparison change", 60000);
  if (await page.locator(".empty").filter({ hasText: /Select versions|בחרו גרסאות|Run compare|הריצו השוואה/i }).count()) {
    throw new Error("Compare page still shows empty state after compare");
  }
  await page.waitForTimeout(300);
  await shot(page, "07-compare.webp");

  // 8. Evaluation dashboard
  await nav.getByRole("link", { name: /^Evaluation$|^הערכה$/ }).click();
  await page.getByRole("heading", { name: /Evaluation|הערכה/i }).waitFor();
  await assertVisible(page.getByTestId("eval-metrics-table"), "evaluation metrics table", 15000);
  await assertVisible(
    page.getByTestId("eval-stub-badge").or(page.getByText(/Synthetic \/ stub|סינתטי/i)),
    "synthetic/stub badge",
  );
  await assertVisible(page.getByTestId("eval-gate-pass"), "at least one passing gate");
  await page.waitForTimeout(300);
  await shot(page, "08-evaluation.webp");

  // 9. Settings
  await nav.getByRole("link", { name: /^Settings$|^הגדרות$/ }).click();
  await page.getByRole("heading", { name: /Settings|הגדרות/i }).waitFor();
  await page.waitForTimeout(300);
  await shot(page, "09-settings.webp");

  // 10. Hebrew RTL product screen (Requirements)
  const langToggle = page.locator("button.lang-toggle").first();
  await assertVisible(langToggle, "language toggle");
  await langToggle.click();
  await page.waitForFunction(() => document.documentElement.dir === "rtl", null, { timeout: 5000 });
  await page.locator("nav").first().getByRole("link", { name: /^דרישות$|^Requirements$/ }).click();
  await page.getByRole("heading").first().waitFor();
  const dir = await page.evaluate(() => document.documentElement.dir);
  if (dir !== "rtl") {
    throw new Error(`Hebrew screen expected html[dir=rtl], got dir=${dir}`);
  }
  await assertVisible(page.getByTestId("requirement-row"), "Hebrew requirements still populated");
  await page.waitForTimeout(400);
  await shot(page, "10-hebrew-ui.webp");

  await context.close();
  await browser.close();

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
    throw new Error("No walkthrough video recorded");
  }

  console.log("done");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
