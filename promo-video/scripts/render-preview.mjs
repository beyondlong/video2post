import { mkdtemp } from "node:fs/promises";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { join } from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("/Users/yangxinglong/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");

const ROOT = "file:///Users/yangxinglong/Documents/video2post/promo-video/index.html";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const FPS = 24;
const DURATION_SECONDS = 20;
const TOTAL_FRAMES = FPS * DURATION_SECONDS;

const frameDir = await mkdtemp(join(tmpdir(), "video2post-promo-frames-"));
const browser = await chromium.launch({
  headless: true,
  executablePath: CHROME
});

try {
  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1
  });

  await page.goto(ROOT, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(800);

  const status = await page.evaluate(() => ({
    hasTimeline: Boolean(window.__timelines?.["video2post-promo"]),
    hasCover: Boolean(document.querySelector(".hero-frame img")?.complete)
  }));

  if (!status.hasTimeline) {
    throw new Error("Timeline video2post-promo was not registered.");
  }

  for (let frame = 0; frame < TOTAL_FRAMES; frame += 1) {
    const time = frame / FPS;
    await page.evaluate((t) => {
      window.__timelines["video2post-promo"].time(t);
    }, time);
    await page.screenshot({
      path: join(frameDir, `frame-${String(frame + 1).padStart(4, "0")}.png`),
      fullPage: false
    });

    if ((frame + 1) % 48 === 0) {
      console.log(`rendered ${frame + 1}/${TOTAL_FRAMES}`);
    }
  }

  console.log(`FRAME_DIR=${frameDir}`);
} finally {
  await browser.close();
}
