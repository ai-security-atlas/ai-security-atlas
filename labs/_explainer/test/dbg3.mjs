import { chromium } from "playwright";
import { pathToFileURL } from "url";
const p = await chromium.launch();
const page = await p.newPage({ viewport: { width: 1280, height: 1400 } });
page.on("pageerror", e => console.log("PAGEERROR:", e.message));
const url = pathToFileURL("/Users/alevsk/Development/ai-security-atlas/labs/attack-sponge/explainer/index.html").href;
await page.goto(url);
await page.waitForTimeout(800);
for (const n of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) {
  await page.goto(`${url}#attack-sponge/${n}`);
  await page.waitForTimeout(350);
  await page.screenshot({ path: `/private/var/folders/qc/66_yq86j4vv5nmp1m4khndc00000gn/T/opencode/sp43/shot${n}.png` });
}
console.log("shots done");
await p.close();
