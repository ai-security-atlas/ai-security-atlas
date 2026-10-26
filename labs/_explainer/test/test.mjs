// Playwright smoke test + lint for the lab explainers (spec §6.3). Run from labs/_explainer/test:
//   npm ci && npx playwright install chromium && node test.mjs [chromium|firefox|webkit]
// Targets: every labs/*/explainer/index.html (the _template too) and embed.html (two instances).
// Screenshots go to shots/ (git-ignored). Exit code 1 on any FAIL.
import { chromium, firefox, webkit } from "playwright";
import { readFileSync, readdirSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const LABS = resolve(here, "../..");
const SHOTS = join(here, "shots");
mkdirSync(SHOTS, { recursive: true });
const which = process.argv[2] || "chromium";
const browser = await { chromium, firefox, webkit }[which].launch();
const CHAPTERS = ["System", "Attack", "Mechanism", "Impact", "Defense"];
const ALLOWED_HOSTS = ["fonts.googleapis.com", "fonts.gstatic.com"]; // laya fonts (spec addendum 5)

let fails = 0;
const ok = (c, m) => { if (!c) fails++; console.log((c ? "PASS " : "FAIL ") + m); };
const skip = m => console.log("SKIP " + m);
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function page(opts = {}) {
  const ctx = await browser.newContext({
    viewport: opts.vp || { width: 1280, height: 900 }, colorScheme: opts.scheme || "light",
    reducedMotion: opts.reduced ? "reduce" : "no-preference",
  });
  if (which === "chromium") await ctx.grantPermissions(["clipboard-read", "clipboard-write"]).catch(() => {});
  const p = await ctx.newPage();
  p.errs = []; p.net = [];
  p.on("pageerror", e => p.errs.push(String(e)));
  p.on("console", m => m.type() === "error" && p.errs.push(m.text()));
  p.on("request", r => {
    const u = new URL(r.url());
    if (["fetch", "xhr"].includes(r.resourceType())) p.net.push(`${r.resourceType()} ${r.url()}`);
    else if (!["file:", "data:", "about:"].includes(u.protocol) && !ALLOWED_HOSTS.includes(u.hostname)) p.net.push(r.url());
  });
  return p;
}
async function open(p, url) {
  await p.goto("about:blank");
  await p.goto(url, { waitUntil: "load" });
  await p.evaluate(() => document.fonts && document.fonts.ready);
  await sleep(350); // IntersectionObserver activation + first render
}
const close = p => p.context().close();
// The stage DOM is the visual state (minus the scale transform, which depends on the viewport).
const snap = p => p.evaluate(() => document.querySelector(".lx-stage").outerHTML.replace(/transform: scale\([^)]*\);?/, ""));

// ---------- static lint ----------
const css = readFileSync(join(here, "../explainer.css"), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
const leaks = [];
for (const m of css.matchAll(/(^|})\s*([^{}@][^{}]*)\{/g)) {
  if (m[2].trim().startsWith("@")) continue;
  for (const sel of m[2].split(",").map(s => s.trim()).filter(Boolean)) {
    if (/^(from|to|\d+%)$/.test(sel)) continue;
    if (!/\.lx\b|\.lx-|body\[data-standalone\]/.test(sel)) leaks.push(sel);
  }
}
ok(leaks.length === 0, "explainer.css: every selector is scoped to .lx / body[data-standalone] " + leaks.join(" | "));

function readme(dir) {
  const f = join(LABS, dir, "README.md");
  if (!existsSync(f)) return null;
  const s = readFileSync(f, "utf8");
  const fm = (s.match(/^---\n([\s\S]*?)\n---/) || [, ""])[1];
  const canary = (fm.match(/^canary:\s*"?([^"\n#]+?)"?\s*(#.*)?$/m) || [])[1];
  const lines = new Set();
  for (const b of s.matchAll(/```bash\n([\s\S]*?)```/g)) b[1].split("\n").forEach(l => lines.add(l.trim()));
  return { canary, lines };
}

// ---------- every lab explainer (and the template) ----------
const dirs = readdirSync(LABS).filter(d => existsSync(join(LABS, d, "explainer/index.html"))).sort();
ok(dirs.includes("_template"), "found explainers: " + dirs.join(", "));
for (const dir of dirs) {
  const base = join(LABS, dir, "explainer");
  const url = pathToFileURL(join(base, "index.html")).href;
  const src = readFileSync(join(base, "explainer.js"), "utf8");
  const T = `[${dir}]`;
  ok(!/#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?(?:[0-9a-fA-F]{2})?\b/.test(src), `${T} no hex colors in explainer.js`);
  ok(!/(fill|stroke)="var\(/.test(src), `${T} no fill="var( / stroke="var( attributes in explainer.js`);
  ok(!/\bfetch\s*\(|XMLHttpRequest/.test(src), `${T} explainer.js does not fetch`);

  let p = await page();
  await open(p, url);
  const info = await p.evaluate(() => {
    const host = document.querySelector("[data-explainer]"), d = Explainer.defs[host.dataset.explainer];
    return { id: d.id, steps: d.steps, problems: Explainer.validate(d), data: typeof window.LAB_DATA === "object" && !!window.LAB_DATA,
      chapters: [...host.querySelectorAll(".lx-ch-name")].map(e => e.textContent), canary: window.LAB_DATA && window.LAB_DATA.canary };
  });
  const M = info.steps.length;
  ok(info.id === dir || dir === "_template", `${T} explainer id "${info.id}" equals the folder name`);
  // (a) chapters
  ok(JSON.stringify(info.chapters) === JSON.stringify(CHAPTERS), `${T} (a) 5 chapter segments in order: ${info.chapters.join(" ")}`);
  ok(info.problems.length === 0, `${T} (a) chapter lint (present, non-decreasing, 1-3 each, 6-10 total) ${info.problems.join("; ")}`);
  // (c) data.js from file://, no network
  ok(info.data, `${T} (c) window.LAB_DATA loaded from data.js`);
  ok(p.net.length === 0, `${T} (c) no network request besides fonts ${p.net.join(" | ")}`);
  ok(p.errs.length === 0, `${T} (c) no page errors ${p.errs.join(" | ")}`);
  // (f) safety rules
  const rm = readme(dir);
  ok(info.steps[M - 1].chapter === "Defense", `${T} (f) last chapter is Defense`);
  const canary = dir === "_template" ? info.canary : rm && rm.canary; // the template README holds a placeholder
  if (canary) ok(info.steps.some(s => s.chapter === "Impact" && s.caption.includes(canary)), `${T} (f) an Impact caption names the canary ${canary}`);
  else ok(false, `${T} (f) README front matter has a canary`);
  // (b) cmd strip and copy; every cmd is a line of a README bash block
  const cmds = info.steps.map((s, i) => [i + 1, s.cmd]).filter(([, c]) => c);
  if (dir === "_template") skip(`${T} (b) cmd vs README: the template's commands are placeholders`);
  else if (!rm) ok(false, `${T} (b) README.md exists`);
  else cmds.forEach(([n, c]) => ok(rm.lines.has(c), `${T} (b) step ${n} cmd appears verbatim in a README bash block: ${c}`));
  if (cmds.length) {
    const [n, c] = cmds[0];
    await open(p, `${url}#${info.id}/${n}`);
    await p.click(".lx-copy");
    await sleep(150);
    const got = await p.evaluate(async () => {
      const sel = getSelection().toString();
      let clip = ""; try { clip = await navigator.clipboard.readText(); } catch (e) {}
      return { sel, clip, label: document.querySelector(".lx-copy").textContent };
    });
    // Only Chromium can grant clipboard-read; elsewhere a successful writeText ("Copied") is the evidence.
    ok(got.clip === c || got.sel === c || (which !== "chromium" && got.label === "Copied"), `${T} (b) copy button copies (or selects) the full cmd [${got.label}]`);
  } else ok(false, `${T} (b) at least one step has a cmd`);
  await close(p);

  // (d) deep link to every step, both themes; collect the snapped state of each step as the reference
  const ref = {};
  for (const scheme of ["light", "dark"]) {
    p = await page({ scheme });
    const bad = [];
    for (let n = 1; n <= M; n++) {
      await open(p, `${url}#${info.id}/${n}`);
      const r = await p.evaluate(() => {
        const host = document.querySelector("[data-explainer]");
        return { step: host._lx.step, count: host.querySelector(".lx-count").textContent,
          run: !host.querySelector(".lx-run").hidden, code: host.querySelector(".lx-cmd code").textContent,
          varAttr: host.querySelectorAll('.lx-stage [fill*="var("], .lx-stage [stroke*="var("]').length };
      });
      if (r.step !== n || r.count !== `step ${n}/${M}`) bad.push(`#${n}: step ${r.step}, "${r.count}"`);
      const cmd = info.steps[n - 1].cmd;
      if (r.run !== !!cmd || (cmd && r.code !== cmd)) bad.push(`#${n}: cmd strip ${r.run} "${r.code}"`);
      if (r.varAttr) bad.push(`#${n}: ${r.varAttr} fill/stroke var() attributes`);
      if (scheme === "light") ref[n] = await snap(p);
    }
    ok(bad.length === 0 && p.errs.length === 0, `${T} (d) deep links #${info.id}/1..${M} render, counter reads step N/${M} (${scheme}) ${bad.join("; ")} ${p.errs.join(" | ")}`);
    await close(p);
  }

  // (e) reduced motion: stepping forward reaches each step's final state in < 100 ms
  p = await page({ reduced: true });
  await open(p, `${url}#${info.id}/1`);
  let diff = [];
  for (let n = 2; n <= M; n++) {
    await p.keyboard.press("ArrowRight"); await sleep(90);
    if ((await snap(p)) !== ref[n]) diff.push(n);
  }
  ok(diff.length === 0, `${T} (e) reduced motion: each step equals its deep-link state within 90 ms ${diff.join(",")}`);
  await close(p);
  // authoring pattern: animated forward steps converge to target(n); back snaps
  p = await page();
  await open(p, `${url}#${info.id}/1`);
  diff = [];
  for (let n = 2; n <= M; n++) {
    await p.keyboard.press("ArrowRight"); await sleep(1300);
    if ((await snap(p)) !== ref[n]) diff.push(n);
  }
  ok(diff.length === 0, `${T} pattern: animated steps end exactly at the deep-link state ${diff.join(",")}`);
  await p.keyboard.press("ArrowLeft"); await sleep(60);
  ok((await snap(p)) === ref[M - 1], `${T} pattern: going back snaps to the previous state`);
  ok(await p.evaluate(id => location.hash === `#${id}/${document.querySelector("[data-explainer]")._lx.step}`, info.id), `${T} hash follows user navigation`);
  ok(p.errs.length === 0, `${T} no errors while stepping ${p.errs.join(" | ")}`);
  await close(p);

  // screenshots at the first Impact step: light/dark x 1280/390
  const impact = info.steps.findIndex(s => s.chapter === "Impact") + 1;
  for (const scheme of ["light", "dark"]) for (const w of [1280, 390]) {
    p = await page({ scheme, vp: { width: w, height: w > 500 ? 860 : 844 } });
    await open(p, `${url}#${info.id}/${impact}`);
    await sleep(500);
    if (w === 390) ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${T} no horizontal scroll at 390 px (${scheme})`);
    await p.screenshot({ path: join(SHOTS, `${which}-${info.id}-${scheme}-${w}.png`), fullPage: true });
    await close(p);
  }
}

// ---------- embed page: two instances in an article (ported prototype checks) ----------
const EMBED = pathToFileURL(join(here, "embed.html")).href;
const A = '[data-explainer="attack-example"]', B = '[data-explainer="test-fixture"]';
let p = await page({ vp: { width: 900, height: 900 } });
await open(p, EMBED);
ok(await p.evaluate(() => Explainer.instances.length === 2), "embed: two instances mounted");
ok(await p.evaluate(() => { const ids = [...document.querySelectorAll("[id]")].map(e => e.id); return ids.length === new Set(ids).size; }), "embed: no duplicate ids on the page");
ok(await p.evaluate(() => { const s = getComputedStyle(document.getElementById("prose")); return s.fontFamily.includes("Georgia") && getComputedStyle(document.getElementById("hostbtn")).fontFamily.includes("Georgia"); }), "embed: host page text and buttons keep their own styles");
await p.focus(A);
for (let i = 0; i < 3; i++) { await p.keyboard.press("ArrowRight"); await sleep(1100); }
ok(await p.evaluate(() => Explainer.instances[0].step === 4 && Explainer.instances[1].step === 1), "embed: keys drive only the focused instance");
ok(await p.evaluate(() => location.hash === "#attack-example/4"), "embed: hash written on user navigation: " + await p.evaluate(() => location.hash));
ok(await p.evaluate(a => document.querySelector(a + " .lx-stage").classList.contains("lx-focus"), A), "embed: focus+context dimming at Impact");
await p.locator(A).screenshot({ path: join(SHOTS, `${which}-embed-light-step4.png`) });
await p.keyboard.press("ArrowLeft"); await sleep(100);
ok(await p.evaluate(() => Explainer.instances[0].step === 3), "embed: back goes to step 3");
await p.click(`${A} .lx-ch[data-ch="4"] .lx-ch-btn`); await sleep(100);
ok(await p.evaluate(() => Explainer.instances[0].step === 5), "embed: chapter segment click jumps to the chapter's first step");
await p.click(`${A} .lx-dot[data-n="6"]`); await sleep(100);
ok(await p.evaluate(a => Explainer.instances[0].step === 6 && document.querySelector(a + " .lx-next").disabled, A), "embed: dot click jumps to the last step, next disabled");
ok((await p.locator(`${A} .lx-cap`).innerText()).includes("Measure"), "embed: caption updates");
ok(await p.evaluate(a => [...document.querySelectorAll(a + " .lx-dot")].filter(b => b.checkVisibility({ visibilityProperty: true })).length === 2, A), "embed: only the active chapter's dots are shown");
const fill = await p.evaluate(a => getComputedStyle(document.querySelector(a + ' svg text[fill="currentColor"]:not([style])')).fill, A);
ok(fill === "rgb(23, 25, 22)", "embed: svg text inherits the light ink via currentColor: " + fill);
await p.click(`${A} .lx-stage`, { position: { x: 20, y: 20 } }); await sleep(50);
await p.click(`${A} .lx-prev`); await sleep(50);
await p.click(`${A} .lx-stage`, { position: { x: 20, y: 20 } }); await sleep(50);
ok(await p.evaluate(() => Explainer.instances[0].step === 6), "embed: clicking the stage advances");
ok(p.errs.length === 0, "embed: no page errors " + p.errs.join(" | "));
await p.evaluate(() => { const r = document.documentElement; r.classList.remove("light"); r.classList.add("dark"); r.setAttribute("data-theme", "dark"); });
await sleep(600);
const dark = await p.evaluate(a => getComputedStyle(document.querySelector(a + ' svg text[fill="currentColor"]:not([style])')).fill, A);
ok(dark === "rgb(242, 239, 231)", "embed: data-theme=dark switches tokens live: " + dark);
await p.locator(A).screenshot({ path: join(SHOTS, `${which}-embed-dark-step6.png`) });
await close(p);

p = await page({ vp: { width: 900, height: 900 } });
await open(p, EMBED + "#test-fixture/4");
ok(await p.evaluate(() => Explainer.instances[1].step === 4 && Explainer.instances[0].step === 1), "embed: deep link opens the 2nd instance at step 4");
ok(await p.evaluate(() => scrollY > 300), "embed: deep link scrolls it into view");
ok(await p.evaluate(b => document.querySelector(b + " .pill").classList.contains("on"), B), "embed: data-only fragment shown at its step");
await close(p);

p = await page({ vp: { width: 900, height: 900 } });
await open(p, EMBED);
const hooked = await p.evaluate(() => Explainer.instances.map(i => i.host.querySelector("svg").children.length));
ok(hooked[0] > 0 && hooked[1] === 0, "embed: lazy setup, the off-screen explainer is not set up yet " + JSON.stringify(hooked));
await p.evaluate(() => Explainer.instances[1].host.scrollIntoView()); await sleep(400);
ok(await p.evaluate(() => Explainer.instances[1].host.querySelector("svg").children.length > 0), "embed: set up once scrolled into view");
await close(p);

// standalone page: dark, phone width, global keys
p = await page({ vp: { width: 390, height: 844 }, scheme: "dark" });
await open(p, pathToFileURL(join(LABS, "_template/explainer/index.html")).href + "#attack-example/3");
ok(await p.evaluate(() => Explainer.instances[0].step === 3), "standalone: deep link to step 3");
await p.keyboard.press("ArrowRight"); await sleep(900);
ok(await p.evaluate(() => Explainer.instances[0].step === 4 && location.hash === "#attack-example/4"), "standalone: global keys + hash");
await p.keyboard.press("End"); await sleep(100);
ok(await p.evaluate(() => Explainer.instances[0].step === 6), "standalone: End jumps to the last step");
ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "standalone: no horizontal scroll at 390 px");
ok(p.errs.length === 0, "standalone: no errors " + p.errs.join(" | "));
await close(p);

await browser.close();
console.log(`${which}: ${fails ? fails + " FAILED" : "all passed"}`);
process.exit(fails ? 1 : 0);
