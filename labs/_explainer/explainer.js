/* AI Security Atlas lab explainer engine: a dependency-free, step-based animation player.
 *
 * Derived from the laya "No Time to Think" deck engine (laya-lab, docs/deck.js).
 * Copyright (c) 2026 laya-lab contributors. MIT License: see LICENSE-laya next to this file.
 *
 * Works from file:// and inside other pages: no build, no modules, no fetch, no global CSS.
 * The authoring guide is README.md next to this file. In short:
 *
 *   Explainer.define({
 *     id: "attack-unsafe-load",          // == Atlas node id; deep links are #<id>/<step> (1-based)
 *     family: "family-supply",           // kicker: "<family> · <id>"
 *     title: 'Loading <span class="outline">is</span> executing',   // HTML; one outlined word
 *     legend: ["bad", "teal", "violet", "lime", "ok"],              // roles, or {role, label}
 *     stage: "960x540",                  // design size (default); scaled to the frame width
 *     steps: [{ chapter: "System", label: "Looks like data", caption: "...", cmd: "docker compose ..." }, ...],
 *     html: `<svg class="main" viewBox="0 0 960 540"></svg>`,      // stage markup
 *     setup(stage, api) { return { step(n, dir) {}, enter() {}, leave() {} }; },   // all optional
 *   });
 *
 * step(n, dir): n is 1-based. dir is 1 when moving forward by exactly one step (animate), -1 when moving
 * back by one, 0 for the first render, a jump, a deep link or re-entry (snap).
 *
 * api (per instance; everything it starts stops on leave or when the explainer scrolls off-screen):
 *   api.tween(ms, fn(k), ease) -> Promise<bool>   k in [0,1]; reduced motion: fn(1) at once
 *   api.loop(fn(t, dt))                           rAF loop; reduced motion: one frame at t = 0
 *   api.after(ms, fn) · api.sleep(ms) -> Promise<bool> · api.guard() -> ok()
 *   api.reduced                                   true under prefers-reduced-motion: reduce
 *   api.color(name)                               resolved token, e.g. api.color("bad") (for canvas)
 *   api.uid(name)                                 page-unique id for SVG markers/gradients/clipPaths
 * Helpers: Explainer.svg(tag, attrs, parent) · attr(el, attrs) · v(name) · lerpState(st, from, to, k) ·
 *   ease.* · lerp · seg(k, a, b) · clamp · rng(seed) · validate(def) · CHAPTERS · ROLES
 * Keys (focused explainer, or anywhere on a standalone page): -> / Space / PgDn next, <- / PgUp prev,
 *   Home / End, R restart. Clicking the stage advances.
 */
(function () {
  if (window.Explainer) return; // loaded twice on one page: keep the first copy

  const CHAPTERS = ["System", "Attack", "Mechanism", "Impact", "Defense"];
  const ROLES = {
    bad: "Attacker-controlled", teal: "Trusted data", violet: "Model / computation",
    warn: "Model output", lime: "Canary / side effect", ok: "Defense", muted: "Context",
  };
  const defs = {};
  const instances = [];
  let seq = 0;

  const ease = {
    linear: k => k,
    inOut: k => (k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
    out: k => 1 - Math.pow(1 - k, 3),
    in: k => k * k * k,
    back: k => 1 + 2.4 * Math.pow(k - 1, 3) + 1.4 * Math.pow(k - 1, 2),
  };
  const lerp = (a, b, k) => a + (b - a) * k;
  const clamp = x => Math.max(0, Math.min(1, x));
  const seg = (k, a, b) => clamp((k - a) / (b - a));
  const v = name => `var(--lx-${name})`;
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const plain = s => String(s).replace(/<[^>]*>/g, "");

  // Numeric keys of `to` are interpolated; anything else snaps to `to` at k = 1. k >= 1 copies `to` exactly.
  function lerpState(st, from, to, k) {
    for (const key in to) {
      const a = from[key], b = to[key];
      st[key] = k >= 1 ? b : (typeof a === "number" && typeof b === "number" ? a + (b - a) * k : a);
    }
    return st;
  }

  // Colors that use tokens go into style (fill="var(...)" attributes are not allowed); the rest are attributes.
  const STYLE_PROPS = { fill: 1, stroke: 1, "stop-color": 1, color: 1 };
  // Easing overshoot can push a tweened size slightly below 0, which SVG rejects; clamp sizes at 0.
  const SIZE_PROPS = { width: 1, height: 1, r: 1, rx: 1, ry: 1 };
  function attr(n, attrs) {
    for (const k in attrs) {
      let val = attrs[k];
      if (SIZE_PROPS[k] && +val < 0) val = 0;
      if (k === "text") n.textContent = val;
      else if (STYLE_PROPS[k] && typeof val === "string" && val.indexOf("var(") >= 0) n.style.setProperty(k, val);
      else n.setAttribute(k, val);
    }
    return n;
  }
  const NS = "http://www.w3.org/2000/svg";
  // SVG text defaults to fill="currentColor" (the stage sets color: var(--lx-ink)).
  function svg(tag, attrs = {}, parent) {
    const n = document.createElementNS(NS, tag);
    if (tag === "text" && !("fill" in attrs)) n.setAttribute("fill", "currentColor");
    attr(n, attrs);
    if (parent) parent.appendChild(n);
    return n;
  }
  function rng(seed = 1) { // mulberry32
    return function () {
      seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // Definition checks. Runtime only logs them (console.error); the Playwright test fails on them.
  function validate(d) {
    const p = [];
    if (!d || typeof d.id !== "string" || !/^[a-z0-9][a-z0-9-]*$/.test(d.id)) p.push("id must be a lowercase node id");
    if (!d || !Array.isArray(d.steps) || !d.steps.length) return p.concat("steps must be a non-empty array");
    const counts = CHAPTERS.map(() => 0);
    let last = -1;
    d.steps.forEach((s, i) => {
      const c = CHAPTERS.indexOf(s.chapter);
      if (c < 0) { p.push(`step ${i + 1}: chapter "${s.chapter}" is not one of ${CHAPTERS.join("|")}`); return; }
      if (c < last) p.push(`step ${i + 1}: chapter ${s.chapter} comes after ${CHAPTERS[last]} (chapters must not go back)`);
      last = Math.max(last, c); counts[c]++;
      if (!s.label) p.push(`step ${i + 1}: missing label`);
      if (!s.caption) p.push(`step ${i + 1}: missing caption`);
      if (s.cmd !== undefined && (typeof s.cmd !== "string" || !s.cmd.trim())) p.push(`step ${i + 1}: cmd must be a non-empty string`);
    });
    CHAPTERS.forEach((c, i) => { if (counts[i] < 1 || counts[i] > 3) p.push(`chapter ${c} has ${counts[i]} steps (1-3 required)`); });
    if (d.steps.length < 6 || d.steps.length > 10) p.push(`${d.steps.length} steps (6-10 required)`);
    return p;
  }

  const mq = window.matchMedia ? matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };

  function makeApi(root, pfx) {
    let gen = 0, timers = [];
    const rafs = new Set();
    const raf = f => { const id = requestAnimationFrame(t => { rafs.delete(id); f(t); }); rafs.add(id); };
    return {
      get reduced() { return mq.matches; },
      _start() { gen++; },
      _stop() { gen++; timers.forEach(clearTimeout); timers = []; rafs.forEach(cancelAnimationFrame); rafs.clear(); },
      guard() { const g = gen; return () => g === gen; },
      loop(fn) {
        const g = gen;
        if (mq.matches) { fn(0, 0); return; }
        let t0 = null, lastT = null;
        const tick = now => { if (g !== gen) return; if (t0 === null) t0 = lastT = now; fn((now - t0) / 1000, (now - lastT) / 1000); lastT = now; raf(tick); };
        raf(tick);
      },
      tween(ms, fn, e = ease.inOut) {
        const g = gen;
        if (mq.matches || ms <= 0) { fn(1); return Promise.resolve(true); }
        return new Promise(res => {
          const t0 = performance.now();
          const tick = now => { if (g !== gen) return res(false); const k = Math.min(1, (now - t0) / ms); fn(k >= 1 ? 1 : e(k)); k < 1 ? raf(tick) : res(true); };
          raf(tick);
        });
      },
      after(ms, fn) { const g = gen; timers.push(setTimeout(() => g === gen && fn(), mq.matches ? 0 : ms)); },
      sleep(ms) { const g = gen; return new Promise(r => timers.push(setTimeout(() => r(g === gen), mq.matches ? 0 : ms))); },
      color(name) { return getComputedStyle(root).getPropertyValue("--lx-" + name).trim(); },
      uid(name) { return pfx + name; },
    };
  }

  const STANDALONE = () => !!document.body && document.body.hasAttribute("data-standalone");

  function mount(host) {
    if (host._lx) return host._lx;
    const d = defs[host.dataset.explainer];
    if (!d) { host.textContent = `Unknown explainer: ${host.dataset.explainer}`; return null; }
    const problems = validate(d);
    if (problems.length) console.error(`Explainer "${d.id}": ${problems.join("; ")}`);
    const [W, H] = (d.stage || "960x540").split("x").map(Number);
    const steps = d.steps, N = steps.length;
    const chOf = steps.map(s => Math.max(0, CHAPTERS.indexOf(s.chapter)));
    const pfx = "lx" + (++seq) + "-";

    const legend = (d.legend || []).map(r => (typeof r === "string" ? { role: r, label: ROLES[r] || r } : r));
    const chapters = CHAPTERS.map((name, c) => {
      const idx = []; chOf.forEach((x, i) => x === c && idx.push(i + 1));
      const range = idx.length ? (idx.length > 1 ? `steps ${idx[0]}–${idx[idx.length - 1]}` : `step ${idx[0]}`) : "no steps";
      return `<li class="lx-ch" data-ch="${c}">
          <button type="button" class="lx-ch-btn" aria-label="Chapter ${c + 1}: ${name} (${range})"${idx.length ? ` data-n="${idx[0]}"` : " disabled"}>
            <span class="lx-ch-name">${name}</span><span class="lx-track"><span class="lx-fill"></span></span></button>
          <span class="lx-dots">${idx.map(n => `<button type="button" class="lx-dot" data-n="${n}" aria-label="Step ${n}: ${esc(plain(steps[n - 1].label || ""))}"></button>`).join("")}</span>
        </li>`;
    }).join("");

    host.classList.add("lx");
    host.tabIndex = 0;
    host.setAttribute("role", "region");
    host.setAttribute("aria-roledescription", "step-by-step animation");
    host.setAttribute("aria-label", plain(d.title || d.id));
    host.innerHTML = `<div class="lx-in">
      <div class="lx-head">
        <div class="lx-titles">
          ${d.family ? `<div class="lx-kicker">${esc(d.family)} · ${esc(d.id)}</div>` : ""}
          <div class="lx-title" role="heading" aria-level="2">${d.title || esc(d.id)}</div>
        </div>
        ${legend.length ? `<ul class="lx-legend" aria-label="Legend">${legend.map(l => `<li style="--lx-c: var(--lx-${esc(l.role)})">${esc(l.label)}</li>`).join("")}</ul>` : ""}
      </div>
      <div class="lx-frame"><div class="lx-stage" data-lx-stage="${esc(d.id)}" style="width:${W}px;height:${H}px">${d.html || ""}</div></div>
      <div class="lx-bar">
        <button type="button" class="lx-btn lx-prev" aria-label="Previous step">&#8592;</button>
        <ol class="lx-chapters">${chapters}</ol>
        <button type="button" class="lx-btn lx-next" aria-label="Next step">&#8594;</button>
        <span class="lx-count"></span>
      </div>
      <div class="lx-side">
        <div class="lx-cap" aria-live="polite"><div class="lx-cap-n"></div><div class="lx-cap-t"></div></div>
        <div class="lx-run" hidden>
          <div class="lx-run-h"><span>Run it yourself</span><button type="button" class="lx-copy">Copy</button></div>
          <pre class="lx-cmd"><code></code></pre>
        </div>
      </div>
    </div>`;

    const $ = s => host.querySelector(s);
    const frame = $(".lx-frame"), stage = $(".lx-stage"), prevB = $(".lx-prev"), nextB = $(".lx-next");
    const chEls = [...host.querySelectorAll(".lx-ch")], dotEls = [...host.querySelectorAll(".lx-dot")];
    const capN = $(".lx-cap-n"), capT = $(".lx-cap-t"), count = $(".lx-count");
    const run = $(".lx-run"), code = $(".lx-cmd code"), copyB = $(".lx-copy");
    const api = makeApi(host, pfx);
    let hooks = null, cur = 0, active = false;
    const inst = {
      host, def: d, get step() { return cur; },
      go, next: () => go(cur + 1, { user: true }), prev: () => go(cur - 1, { user: true }), replay,
    };

    function fit() {
      const s = frame.clientWidth / W;
      frame.style.minHeight = H * s + "px"; // min-height: beside a taller caption panel the canvas stretches
      stage.style.transform = `scale(${s})`;
    }
    function apply(n) {
      const s = steps[n - 1], c = chOf[n - 1];
      stage.querySelectorAll("[data-step]").forEach(f => f.classList.toggle("on", n >= +f.dataset.step));
      stage.querySelectorAll("[data-only]").forEach(f => f.classList.toggle("on", f.dataset.only.split(",").map(x => x.trim()).includes(String(n))));
      chEls.forEach((li, i) => {
        const idx = []; chOf.forEach((x, j) => x === i && idx.push(j + 1));
        const done = i < c ? 1 : i > c ? 0 : (idx.indexOf(n) + 1) / idx.length;
        li.classList.toggle("on", i === c); li.classList.toggle("done", i < c);
        li.querySelector(".lx-fill").style.width = done * 100 + "%";
        li.querySelector(".lx-ch-btn").setAttribute("aria-current", i === c ? "true" : "false");
      });
      dotEls.forEach(b => {
        const k = +b.dataset.n;
        b.classList.toggle("on", k === n); b.classList.toggle("done", k < n);
        b.setAttribute("aria-current", k === n ? "step" : "false");
      });
      prevB.disabled = n === 1; nextB.disabled = n === N;
      count.textContent = `step ${n}/${N}`;
      capN.textContent = `${s.chapter || ""}${s.label ? " · " + plain(s.label) : ""}`;
      capT.innerHTML = s.caption || "";
      run.hidden = !s.cmd;
      code.textContent = s.cmd || "";
      copyB.textContent = "Copy";
    }
    function activate() {
      if (active) return; active = true;
      api._start();
      if (!hooks) hooks = (d.setup && d.setup(stage, api)) || {};
      hooks.enter && hooks.enter();
      hooks.step && hooks.step(cur, 0); // first render or re-entry: snap to the current step
    }
    function deactivate() {
      if (!active) return; active = false;
      api._stop(); hooks && hooks.leave && hooks.leave();
    }
    function go(n, opts = {}) {
      n = Math.max(1, Math.min(N, n | 0));
      if (n === cur && !opts.force) return;
      const dir = opts.dir !== undefined ? opts.dir : n === cur + 1 ? 1 : n === cur - 1 ? -1 : 0;
      cur = n; apply(n);
      if (active && hooks.step) hooks.step(n, dir);
      if (opts.user) history.replaceState(history.state, "", `#${d.id}/${n}`);
    }
    function replay() { deactivate(); cur = 1; apply(1); activate(); }
    async function copy() {
      const text = code.textContent;
      try {
        await navigator.clipboard.writeText(text);
        copyB.textContent = "Copied";
      } catch (e) { // file:// or no clipboard permission: select the text instead
        const r = document.createRange(); r.selectNodeContents(code);
        const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
        copyB.textContent = "Press Ctrl/⌘+C";
      }
    }

    prevB.onclick = () => inst.prev();
    nextB.onclick = () => inst.next();
    host.querySelectorAll(".lx-ch-btn[data-n], .lx-dot").forEach(b => b.onclick = () => go(+b.dataset.n, { user: true }));
    copyB.onclick = copy;
    stage.addEventListener("click", e => { if (!e.target.closest("a,button,input,select,textarea")) inst.next(); });
    host.addEventListener("keydown", e => { if (!STANDALONE()) onKey(e, inst); });

    new ResizeObserver(fit).observe(frame); fit();
    // Pause loops and tweens while off-screen or in a background tab; resume snapped to the current step.
    let visible = false;
    new IntersectionObserver(es => es.forEach(en => { visible = en.isIntersecting; visible && !document.hidden ? activate() : deactivate(); }), { threshold: 0.15 }).observe(host);
    inst._vis = () => (document.hidden || !visible ? deactivate() : activate());

    const h = parseHash(d.id);
    go(h !== null ? h : 1, { dir: 0 });
    if (h !== null && !STANDALONE()) host.scrollIntoView({ block: "center" });
    host._lx = inst; instances.push(inst);
    return inst;
  }

  function parseHash(id) {
    const m = location.hash.match(/^#([\w-]+)\/(\d+)$/);
    return m && m[1] === id ? +m[2] : null;
  }
  function onKey(e, inst) {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key, t = e.target;
    if ((k === " " || k === "Enter") && t && t.closest && t.closest("button,a,input,select,textarea")) return; // let the control act
    if (["ArrowRight", " ", "PageDown"].includes(k)) { e.preventDefault(); inst.next(); }
    else if (["ArrowLeft", "PageUp"].includes(k)) { e.preventDefault(); inst.prev(); }
    else if (k === "Home") { e.preventDefault(); inst.go(1, { user: true }); }
    else if (k === "End") { e.preventDefault(); inst.go(inst.def.steps.length, { user: true }); }
    else if (k === "r" || k === "R") inst.replay();
  }
  function mountAll(id) {
    document.querySelectorAll(id ? `[data-explainer="${id}"]` : "[data-explainer]").forEach(mount);
  }
  let ready = false;
  function onReady() {
    ready = true; mountAll();
    if (STANDALONE()) addEventListener("keydown", e => instances[0] && onKey(e, instances[0]));
  }

  window.Explainer = {
    define(d) { defs[d.id] = d; if (ready) mountAll(d.id); }, // a definition loaded late still mounts
    mount, instances, defs, validate, CHAPTERS, ROLES,
    svg, attr, v, lerpState, ease, lerp, clamp, seg, rng,
  };
  if (document.readyState === "loading") addEventListener("DOMContentLoaded", onReady);
  else setTimeout(onReady, 0);
  addEventListener("hashchange", () => instances.forEach(i => { const h = parseHash(i.def.id); if (h !== null && h !== i.step) i.go(h); }));
  document.addEventListener("visibilitychange", () => instances.forEach(i => i._vis()));
})();
