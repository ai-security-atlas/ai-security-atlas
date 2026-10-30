/* LAB-14 system-serving: "What the server adds" (foundation lab, 10 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One persistent scene on top (tenant A, the llama.cpp server with its 4 slots, prompt cache and endpoints,
 * tenant B) and a detail panel below that crossfades per step. Every number and string comes from
 * window.LAB_DATA (data.js, exported from the reference workbench run). Pattern: target(n) is pure,
 * draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp;
  const D = window.LAB_DATA;
  const C = D.cache, ST = D.starve, BD = D.bounded, G = D.gateway, LM = D.limits;
  const sec = x => (x >= 10 ? x.toFixed(1) : x.toFixed(2)) + " s";
  const p95 = (rows, i) => rows.rows[i][2];
  const best = C.candidates.reduce((a, b) => (b[2] > a[2] ? b : a));

  X.define({
    id: "system-serving",
    family: "family-privacy",
    title: 'What the server <span class="outline">adds</span>',
    legend: [{ role: "teal", label: "Tenant A / its data" }, { role: "bad", label: "Tenant B / pressure" },
      { role: "violet", label: "Server state" }, { role: "warn", label: "Open by default" },
      { role: "lime", label: "Canary" }, { role: "ok", label: "Defense" }],
    steps: [
      { chapter: "System", label: "One server, two tenants",
        caption: `A pinned <span class="c-violet">llama.cpp server</span> (${D.build}) serves one GGUF to everyone: ${D.slots} slots, ${D.n_ctx} tokens of shared KV cache, prompt caching on. <span class="c-teal">Tenant A</span>'s billing app sends its system prompt with every request.`,
        cmd: "docker compose run --rm workbench python system-serving/scripts/s01_surface.py" },
      { chapter: "System", label: "Open by default",
        caption: `With the shipped defaults every route answers a client with no key: <code>/props</code>, <code>/slots</code>, chat, the web UI. The image binds <code>0.0.0.0</code>, and CORS echoes any origin with credentials, so a <span class="c-warn">web page</span> can call it too.` },
      { chapter: "Attack", label: "B reads /slots",
        caption: `Risk: <span class="c-bad">tenant B</span> polls <code>/slots</code> while A is answering. By default it sees that A is busy, ${D.slots_default.n_prompt_tokens} tokens in the slot, A's <code>n_predict</code> ${D.slots_default.n_predict} and temperature ${D.slots_default.temperature}: activity and settings, not text.`,
        cmd: "docker compose run --rm workbench python system-serving/scripts/s02_slots_watch.py" },
      { chapter: "Mechanism", label: "One debug switch",
        caption: `Set <code>LLAMA_SERVER_SLOTS_DEBUG=1</code> and the same unauthenticated call also returns the <span class="c-teal">prompt</span> and <span class="c-warn">output</span> of each slot's current or last task, A's system prompt included. The container log still holds no copy.`,
        cmd: "SERVING_SLOTS_DEBUG=1 docker compose up -d --wait llama-server" },
      { chapter: "Mechanism", label: "The cache counts matches",
        caption: `Every reply reports <code>timings.cache_n</code>: prompt tokens reused from the shared cache, whoever sent them. B sends A's known prefix plus a guess; only <code>${best[0]}</code> reuses more (+${best[2]}), one token per match.`,
        cmd: "docker compose run --rm workbench python system-serving/scripts/s03_cache_probe.py" },
      { chapter: "Impact", label: "B has the canary",
        caption: `B now holds A's secret, the lab canary <code class="c-lime">${D.canary}</code>: read in full from <code>/slots</code> with the debug switch, and confirmed by the cache counter with no switch at all. Neither path needed a key.` },
      { chapter: "Impact", label: "Every slot held",
        caption: `A opens one ${ST.n_predict}-token request per slot (<code>ignore_eos</code>, allowed by default). B's short request waits for all of them: p95 <span class="c-bad">${sec(p95(ST, 2))}</span> against ${sec(p95(ST, 0))} idle, about ${Math.round(ST.ratio)}×.`,
        cmd: "docker compose run --rm workbench python system-serving/scripts/s04_starve.py" },
      { chapter: "Defense", label: "Lock the surface",
        caption: `One flag at a time: <code>--api-key-file</code> turns every API route into 401, <code>--no-slots --no-webui --cors-origins localhost</code> closes the monitoring read, UI and browsers, and a loopback bind closes the network. Each leaves other doors open.`,
        cmd: "docker compose run --rm workbench python system-serving/scripts/d1_exposure.py loopback" },
      { chapter: "Defense", label: "Limits it enforces",
        caption: `<code>--n-predict 64</code> is only a default (a request for 400 gets ${LM.n_predict_400}) and <code>--timeout 5</code> let a ${LM.long_s}-second request finish. Per-slot context is a real cap: ${BD.rows[2][5]} tokens, and B's worst wait falls to ${sec(p95(BD, 2))}.`,
        cmd: "docker compose run --rm workbench python system-serving/scripts/s04_starve.py --out d2_starve.json" },
      { chapter: "Defense", label: "A gateway in front",
        caption: `A <span class="c-ok">budget gateway</span> holds the server key: per-tenant keys, two routes, a ${G.clamped}-token clamp, one request at a time, a token budget, its own slot per tenant and no <code>timings</code>. B's probe finds nothing; its p95 stays ${sec(G.b_p95)}.`,
        cmd: "docker compose run --rm workbench python system-serving/scripts/d3_proxy.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Tenant A, the llama.cpp server with slots, cache and endpoints, tenant B, and a detail panel"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) => S("rect", { x, y, width: w, height: h, rx: 12, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const clip = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

      // ---------- tenant A (left)
      const gA = S("g", { class: "dimmable" }, svg);
      card(gA, 20, 30, 210, 250, V("teal"));
      label(gA, 36, 56, "TENANT A", { fill: V("teal") });
      T(gA, 36, 80, "billing assistant app", 14);
      S("rect", { x: 34, y: 94, width: 182, height: 92, rx: 8, fill: V("teal"), "fill-opacity": .1, stroke: V("teal"), "stroke-width": 1 }, gA);
      T(gA, 44, 114, "system prompt", 13, { fill: V("teal"), "font-weight": 700 });
      T(gA, 44, 136, "…never reveal:", 13, { class: "mono" });
      T(gA, 44, 154, "escalation code", 13, { class: "mono" });
      T(gA, 44, 174, D.canary, 13, { class: "mono", fill: V("lime"), "font-weight": 700 });
      T(gA, 36, 212, "sends it with every", 13, { fill: V("muted") });
      T(gA, 36, 230, "customer question", 13, { fill: V("muted") });
      const aHog = T(gA, 36, 262, `+ ${D.slots} × ${ST.n_predict}-token jobs`, 13, { fill: V("bad"), "font-weight": 700 });

      // ---------- tenant B (right)
      const gB = S("g", { class: "dimmable" }, svg);
      const bBox = card(gB, 730, 30, 210, 250, V("bad"));
      label(gB, 746, 56, "TENANT B", { fill: V("bad") });
      T(gB, 746, 80, "any client on the port", 14);
      T(gB, 746, 100, "no API key", 13, { fill: V("muted") });
      label(gB, 746, 136, "B KNOWS", {});
      const bKnow = [0, 1, 2].map(i => T(gB, 746, 160 + i * 22, "", 13, { class: "mono" }));
      const bCanary = T(gB, 746, 240, D.canary, 14, { class: "mono", fill: V("lime"), "font-weight": 800 });
      const bWait = T(gB, 746, 264, "", 13, { fill: V("bad"), "font-weight": 700 });

      // ---------- server (middle)
      const gSrv = S("g", { class: "dimmable" }, svg);
      card(gSrv, 262, 30, 436, 250, V("violet"));
      label(gSrv, 278, 56, `LLAMA-SERVER · ${D.build.split("-")[0]} · 0.0.0.0:8080`, { fill: V("violet") });
      const slots = [];
      for (let i = 0; i < 4; i++) {
        const x = 280 + i * 102;
        const box = S("rect", { x, y: 70, width: 92, height: 62, rx: 9, fill: V("panel-2"), stroke: V("violet"), "stroke-width": 1.5 }, gSrv);
        T(gSrv, x + 10, 90, `slot ${i}`, 13, { class: "mono" });
        S("rect", { x: x + 10, y: 104, width: 72, height: 14, rx: 4, fill: V("line") }, gSrv);
        const bar = S("rect", { x: x + 10, y: 104, width: 0, height: 14, rx: 4, fill: V("teal") }, gSrv);
        slots.push({ box, bar });
      }
      label(gSrv, 280, 156, "SHARED PROMPT CACHE (KV)");
      const NCELL = 24, cells = [];
      for (let i = 0; i < NCELL; i++) {
        const canaryCell = i >= NCELL - 4;
        const c = S("rect", { x: 280 + i * 17, y: 166, width: 14, height: 22, rx: 4, fill: canaryCell ? V("lime") : V("teal"), opacity: 0 }, gSrv);
        const ring = S("rect", { x: 278 + i * 17, y: 164, width: 18, height: 26, rx: 5, fill: "none", stroke: V("bad"), "stroke-width": 2, opacity: 0 }, gSrv);
        cells.push({ c, ring, canaryCell });
      }
      const eps = ["/slots", "/props", "metrics", "chat", "web UI", "CORS *"];
      const epOpen = [1, 1, 0, 1, 1, 1];
      const tags = eps.map((e, j) => {
        const x = 280 + j * 69;
        const r = S("rect", { x, y: 206, width: 63, height: 28, rx: 7, fill: V("panel"), stroke: V("warn"), "stroke-width": 1.5 }, gSrv);
        const t = T(gSrv, x + 31.5, 225, e, 13, { class: "mono", "text-anchor": "middle" });
        return { r, t };
      });
      const dbgChip = S("g", {}, gSrv);
      S("rect", { x: 280, y: 246, width: 268, height: 24, rx: 6, fill: V("bad"), "fill-opacity": .14, stroke: V("bad"), "stroke-width": 1.2 }, dbgChip);
      T(dbgChip, 290, 263, "LLAMA_SERVER_SLOTS_DEBUG=1", 13, { class: "mono", fill: V("bad"), "font-weight": 700 });
      const ctxChip = S("g", {}, gSrv);
      S("rect", { x: 280, y: 246, width: 300, height: 24, rx: 6, fill: V("ok"), "fill-opacity": .14, stroke: V("ok"), "stroke-width": 1.2 }, ctxChip);
      T(ctxChip, 290, 263, `${BD.n_ctx} tokens per slot (--no-kv-unified)`, 13, { class: "mono", fill: V("ok"), "font-weight": 700 });

      // ---------- flows
      const gFlow = S("g", {}, svg);
      const flowA = S("path", { d: "M230 100 C 246 100, 250 100, 280 100", fill: "none", stroke: V("teal"), "stroke-width": 6, "stroke-linecap": "round" }, gFlow);
      const flowB = S("path", { d: "M730 160 C 712 160, 708 220, 692 220", fill: "none", stroke: V("bad"), "stroke-width": 5, "stroke-linecap": "round" }, gFlow);
      const leak = S("path", { d: "M326 70 C 380 12, 640 8, 760 150", fill: "none", stroke: V("lime"), "stroke-width": 4, "stroke-dasharray": "8 6", "stroke-linecap": "round" }, gFlow);
      const gate = S("g", {}, svg);
      S("rect", { x: 708, y: 30, width: 14, height: 250, rx: 7, fill: V("ok") }, gate);
      T(gate, 715, 298, "gateway", 13, { fill: V("ok"), "font-weight": 700, "text-anchor": "middle" });

      // ---------- detail panels (bottom band)
      const panels = [null];
      const P = () => { const g = S("g", {}, svg); panels.push(g); return g; };
      const row = (g, x, y, cols, size = 14, o = {}) => cols.forEach(([dx, s, oo]) => T(g, x + dx, y, s, size, { class: "mono", ...o, ...(oo || {}) }));
      const codeColor = c => (String(c) === "200" || c === "allowed" ? V("warn") : V("ok"));

      // P1 system facts
      let g = P();
      label(g, 30, 330, "WHAT THE SERVER ADDS TO A MODEL FILE");
      [["slots", `${D.slots} (auto)`, "requests run side by side"], ["KV cache", `${D.n_ctx} tokens`, "shared by all slots"],
        ["prompt cache", "on", "reused across requests"], ["n_predict", "-1", "unlimited by default"]].forEach(([k, v, d], i) => {
        const x = 30 + i * 232;
        card(g, x, 346, 216, 120, V("violet"));
        T(g, x + 16, 376, k, 14, { fill: V("muted"), "font-weight": 700 });
        T(g, x + 16, 412, v, 24, { class: "mono", "font-weight": 800, fill: V("violet") });
        T(g, x + 16, 446, d, 13, { fill: V("muted") });
      });

      // P2 surface table
      g = P();
      label(g, 30, 330, "TENANT B, NO KEY: WHAT ANSWERS");
      D.surface.slice(0, 12).forEach(([m, p, c], i) => {
        const x = 30 + Math.floor(i / 6) * 460, y = 358 + (i % 6) * 24;
        row(g, x, y, [[0, m, { fill: V("muted") }], [72, clip(p, 26), {}], [330, String(c), { fill: c === 200 ? V("warn") : V("muted"), "font-weight": 700 }]], 13);
      });
      T(g, 30, 514, clip(D.cors, 96), 13, { class: "mono", fill: V("warn") });

      // P3 /slots default
      g = P();
      label(g, 30, 330, "GET /slots (DEFAULT), AS TENANT B");
      const sd = D.slots_default;
      [['"is_processing"', "true"], ['"n_prompt_tokens"', sd.n_prompt_tokens], ['"n_decoded"', sd.n_decoded],
        ['"params.n_predict"', sd.n_predict], ['"params.temperature"', sd.temperature]].forEach(([k, v], i) =>
        row(g, 40, 362 + i * 26, [[0, k, { fill: V("violet") }], [250, String(v), { fill: V("warn"), "font-weight": 700 }]], 14));
      card(g, 560, 350, 370, 120, V("ok"));
      T(g, 580, 386, "canary in /slots:", 15, { "font-weight": 700 });
      T(g, 580, 418, sd.canary_seen ? "YES" : "no", 24, { class: "mono", fill: V("ok"), "font-weight": 800 });
      T(g, 580, 450, "metadata only: when, how much, how", 13, { fill: V("muted") });

      // P4 debug
      g = P();
      label(g, 30, 330, "GET /slots WITH LLAMA_SERVER_SLOTS_DEBUG=1");
      row(g, 40, 366, [[0, '"prompt":', { fill: V("violet") }], [110, `"…${D.slots_debug.before}`, {}]], 14);
      T(g, 150, 392, D.canary + '."', 16, { class: "mono", fill: V("lime"), "font-weight": 800 });
      row(g, 40, 426, [[0, '"generated":', { fill: V("violet") }], [130, `"${clip(D.slots_debug.generated, 44)}"`, { fill: V("warn") }]], 14);
      T(g, 40, 470, `canary in /slots: ${D.slots_debug.canary_seen ? "YES" : "no"} · copies in the container log: 0`, 14, { "font-weight": 700, fill: V("bad") });

      // P5 cache bars
      g = P();
      label(g, 30, 330, "TIMINGS.CACHE_N FOR B'S GUESSES (A ANSWERS BEFORE EACH)");
      const maxN = Math.max(...C.candidates.map(r => r[1])) + 2;
      C.candidates.forEach(([gs, n, gain], i) => {
        const y = 350 + i * 34, w = 330 * n / maxN;
        T(g, 30, y + 18, "…CANARY-" + gs, 14, { class: "mono", fill: gain > 0 ? V("lime") : V("ink") });
        S("rect", { x: 200, y, width: w, height: 24, rx: 5, fill: gain > 0 ? V("bad") : V("dim"), opacity: .85 }, g);
        T(g, 206 + w, y + 18, `${n} (${gain >= 0 ? "+" : ""}${gain})`, 14, { class: "mono", "font-weight": 700 });
      });
      label(g, 640, 350, "EXTEND THE GUESS");
      C.extend.forEach(([gs, n, gain], i) => row(g, 640, 378 + i * 26, [[0, gs, { fill: V("lime") }], [90, `+${gain}`, { "font-weight": 700, fill: V("bad") }]], 14));

      // P6 impact summary
      g = P();
      card(g, 30, 340, 900, 180, V("lime"));
      T(g, 50, 378, "B has A's secret:", 15, { "font-weight": 700 });
      T(g, 210, 380, D.canary, 22, { class: "mono", fill: V("lime"), "font-weight": 800 });
      [["/slots, default", "A's activity, prompt size, settings", V("warn")],
        ["/slots, debug switch on", "A's whole prompt and answer, in full", V("bad")],
        ["timings.cache_n, no switch", `guess ${best[0]} confirmed (+${best[2]} tokens)`, V("bad")]].forEach(([k, v, c], i) =>
        row(g, 50, 420 + i * 30, [[0, k, { fill: V("muted") }], [300, v, { fill: c, "font-weight": 700 }]], 14));

      // P7 latency bars (log scale)
      const latBars = (g, rows, title, y0) => {
        label(g, 30, y0, title);
        const lg = x => Math.log10(Math.max(x, .01)), lo = lg(.01), hi = lg(60);
        rows.rows.forEach(([n, , p, , k, tok], i) => {
          const y = y0 + 20 + i * 38, w = 360 * (lg(p) - lo) / (hi - lo);
          T(g, 30, y + 18, n, 14, {});
          S("rect", { x: 250, y, width: w, height: 26, rx: 5, fill: i === 2 ? V("bad") : V("teal"), opacity: .85 }, g);
          T(g, 258 + w, y + 18, `p95 ${sec(p)}${k ? `  ·  A: ${k} × ${tok} tokens` : ""}`, 14, { class: "mono", "font-weight": 700 });
        });
      };
      g = P();
      latBars(g, ST, `B'S LATENCY, ${ST.n_ctx} TOKENS PER SLOT (LOG SCALE)`, 330);
      T(g, 30, 500, `every slot held: p95 ${sec(p95(ST, 2))} = ${Math.round(ST.ratio)}× idle`, 15, { "font-weight": 700, fill: V("bad") });

      // P8 exposure matrix
      g = P();
      label(g, 30, 324, "D1: TENANT B'S VIEW AFTER EACH FLAG");
      const cols = D.exposure.cols;
      cols.forEach((c, j) => T(g, 140 + j * 88 + 40, 348, c, 13, { class: "mono", "text-anchor": "middle", fill: V("muted") }));
      D.exposure.rows.forEach((r, i) => {
        const y = 358 + i * 34;
        T(g, 30, y + 20, r[0], 13, { class: "mono", "font-weight": 700 });
        r.slice(1).forEach((v, j) => {
          const keyed = cols[j] === "A+key" || cols[j] === "/health";
          const col = v === "refused" ? V("ok") : keyed ? V("teal") : codeColor(v);
          S("rect", { x: 140 + j * 88, y, width: 82, height: 28, rx: 5, fill: col, "fill-opacity": .18, stroke: col, "stroke-width": 1 }, g);
          T(g, 181 + j * 88, y + 19, v, 13, { class: "mono", "text-anchor": "middle" });
        });
      });

      // P9 limits
      g = P();
      label(g, 30, 330, "WHICH FLAGS LIMIT A REQUEST");
      [[`--n-predict 64`, `asks 400 -> ${LM.n_predict_400} tokens (only a default)`, V("warn")],
        [`--timeout 5`, `${LM.long_n} tokens, HTTP ${LM.long_status} after ${LM.long_s} s`, V("warn")],
        [`client disconnects`, `slot free again ${LM.freed_s} s later`, V("ok")],
        [`512 tokens per slot`, `asks ${BD.n_predict} -> ${BD.rows[2][5]} tokens`, V("ok")],
        [`B's worst wait`, `${sec(p95(ST, 2))} -> ${sec(p95(BD, 2))}`, V("ok")]].forEach(([k, v, c], i) =>
        row(g, 40, 362 + i * 32, [[0, k, { fill: V("muted") }], [260, v, { fill: c, "font-weight": 700 }]], 14));

      // P10 gateway
      g = P();
      label(g, 30, 330, "D3: THROUGH THE BUDGET GATEWAY");
      const sh = G.cache["slots pinned, timings shown"], ss = G.cache["slots pinned, timings stripped"];
      [[`B -> server, no key`, `chat ${G.direct.chat}, /slots ${G.direct.slots}`],
        [`/slots /props /metrics /`, `404 (not on the allowlist)`],
        [`A asks 100000 tokens`, `${G.clamped} tokens`],
        [`A opens 4 at once`, G.concurrent.join(" ")],
        [`A keeps going`, `${G.budget.served} more, then ${G.budget.then} (budget)`],
        [`B's p95 meanwhile`, sec(G.b_p95)],
        [`cache_n '', k9px, s3rv`, `own slot ${sh.join(", ")} · stripped ${ss.map(x => (x === null ? "-" : x)).join(", ")}`]].forEach(([k, v], i) =>
        row(g, 40, 356 + i * 25, [[0, k, { fill: V("muted") }], [300, v, { fill: V("ok"), "font-weight": 700 }]], 14));

      // ---------- state
      const base = { a: 0, open: 0, b: 0, poll: 0, dbg: 0, cache: 0, know: 0, have: 0, hog: 0, lock: 0, bound: 0, gate: 0, pn: 1 };
      const T_N = [null,
        { a: 1, pn: 1 },
        { a: 1, open: 1, pn: 2 },
        { a: 1, open: 1, b: 1, poll: 1, know: 1, pn: 3 },
        { a: 1, open: 1, b: 1, poll: 1, dbg: 1, know: 1, have: 1, pn: 4 },
        { a: 1, open: 1, b: 1, cache: 1, know: 1, pn: 5 },
        { a: 1, open: 1, b: 1, cache: 1, dbg: 1, know: 1, have: 1, pn: 6 },
        { a: 1, open: 1, b: 1, hog: 1, pn: 7 },
        { a: 1, open: 1, b: 1, lock: 1, pn: 8 },
        { a: 1, open: 1, b: 1, lock: 1, hog: 1, bound: 1, pn: 9 },
        { a: 1, open: 1, b: 1, lock: 1, hog: 1, bound: 1, gate: 1, pn: 10 },
      ];
      const st = { ...base };
      const target = n => ({ ...base, ...T_N[n] });

      function draw(s) {
        // panels crossfade by distance to pn
        panels.forEach((p, i) => { if (p) p.setAttribute("opacity", Math.max(0, 1 - Math.abs(s.pn - i) * 1.6).toFixed(3)); });
        // slots: A in slot 0; hog fills all four (bounded = shorter)
        const fillLen = L(1, .34, s.bound);
        slots.forEach((sl, i) => {
          const load = i === 0 ? Math.max(.55 * s.a, s.hog * fillLen) : s.hog * fillLen;
          A(sl.bar, { width: (72 * load).toFixed(2), fill: s.hog > .5 ? V("bad") : V("teal") });
          A(sl.box, { stroke: s.hog > .5 ? V("bad") : V("violet") });
        });
        aHog.setAttribute("opacity", s.hog.toFixed(3));
        // cache cells fill with A's prompt; B's probe rings the matched prefix (+ the canary tokens)
        const nFill = Math.round(NCELL * s.a);
        cells.forEach((c, i) => {
          c.c.setAttribute("opacity", i < nFill ? (c.canaryCell ? .9 : .45) : 0);
          const hit = i < NCELL - 1;
          c.ring.setAttribute("opacity", (hit ? seg(s.cache * 1.3 - i / NCELL, 0, .3) * (1 - s.gate) : 0).toFixed(3));
        });
        // endpoints: open (warn) -> locked (ok)
        tags.forEach((t, j) => {
          const open = epOpen[j] * s.open * (1 - s.lock);
          const col = open > .5 ? V("warn") : s.lock > .5 ? V("ok") : V("line");
          A(t.r, { stroke: col, "stroke-dasharray": s.lock > .5 && j < 6 ? "4 3" : "none" });
          A(t.t, { fill: open > .5 ? V("warn") : V("muted") });
        });
        dbgChip.setAttribute("opacity", (s.dbg * (1 - s.bound)).toFixed(3));
        ctxChip.setAttribute("opacity", s.bound.toFixed(3));
        // flows
        A(flowA, { opacity: s.a.toFixed(3) });
        A(flowB, { opacity: (s.b * Math.max(s.poll, s.cache, s.hog, s.lock)).toFixed(3) });
        A(leak, { opacity: (s.have * (1 - s.lock)).toFixed(3) });
        gate.setAttribute("opacity", s.gate.toFixed(3));
        A(flowB, { stroke: s.gate > .5 ? V("ok") : V("bad") });
        // tenant B
        gB.setAttribute("opacity", Math.max(.25, s.b).toFixed(3));
        const k = s.know > .5;
        const lines = s.gate > .5 ? ["401 / 404 / 429", "no timings", "own slot"]
          : s.lock > .5 ? ["401 without a key", "/slots 501", "not reachable"]
            : k && s.cache > .5 ? [`cache_n +${best[2]}`, `guess ${best[0]}`, ""]
              : k ? ["A is busy", `${D.slots_default.n_prompt_tokens} tokens, T=${D.slots_default.temperature}`, `n_predict ${D.slots_default.n_predict}`]
                : ["-", "", ""];
        bKnow.forEach((t, i) => { t.textContent = lines[i]; });
        bCanary.setAttribute("opacity", (s.have * (1 - s.hog) * (1 - s.lock)).toFixed(3));
        bWait.textContent = s.gate > .5 ? `waits ${sec(G.b_p95)}` : s.bound > .5 ? `waits ${sec(p95(BD, 2))}` : s.hog > .5 ? `waits ${sec(p95(ST, 2))}` : "";
        A(bBox, { stroke: s.gate > .5 ? V("ok") : V("bad") });
        // focus
        const focus = s.hog > .5 && s.lock < .5 ? [gSrv, gB] : s.have > .5 ? [gB, gSrv] : [];
        [gA, gB, gSrv].forEach(x => x.classList.toggle("hot", focus.includes(x)));
        el.classList.toggle("lx-focus", focus.length > 0);
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g2 = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }
          return api.tween(700, k => { if (g2 !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
