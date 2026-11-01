/* LAB-24 attack-cache-sidechannel: "Timing the prompt cache" (9 steps).
 * Chapters: System 1-2 · Attack 3 · Mechanism 4-5 · Impact 6-7 · Defense 8-9.
 * One persistent scene on top (tenant A, the llama.cpp server with its slots and prompt cache,
 * tenant B) and a detail panel below that crossfades per step. Every number and string comes from
 * window.LAB_DATA (data.js, exported from the reference workbench run). Pattern: target(n) is
 * pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp;
  const D = window.LAB_DATA;
  const AT = D.attack.summary, T = D.tokens, D1 = D.d1, D2 = D.d2, TR = D.trials;
  const ms = x => Math.round(x) + " ms";
  const p = x => (x < 0.001 ? x.toExponential(1) : x.toFixed(3));
  const median = a => { const s = [...a].sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };

  X.define({
    id: "attack-cache-sidechannel",
    family: "family-privacy",
    title: 'Timing the <span class="outline">prompt</span> cache',
    legend: [{ role: "teal", label: "Tenant A / its prefix" }, { role: "bad", label: "Tenant B / the probe" },
      { role: "violet", label: "Server + prompt cache" }, { role: "warn", label: "Measured time" },
      { role: "lime", label: "Canary" }, { role: "ok", label: "Defense" }],
    intro: {
      "why": "A model server that keeps a cache of prompt beginnings answers a repeated beginning faster than fresh text. When several customers share that cache, the speed itself gives something away: a fast reply means someone else’s prompt started the same way. This lab asks whether that leak really exists on a local server, and how strong it is.",
      "plan": "You’ll watch a victim app and an attacker share one llama.cpp server. The attacker has four candidate prompts and can only time its own requests. Over many rounds, those timings add up to a statistical result. Then you’ll test three defenses against it.",
      "terms": "A prefix is the beginning of a prompt. The KV cache stores the work the server did on a prompt, so a later request with the same prefix can skip that work. A hit reuses it and a miss recomputes it. Prefill is the work a request needs before the first output token appears. A tenant is one customer of the server."
    },
    steps: [
      { chapter: "System", label: "One server, two tenants",
        guide: "Meet the two parties. Tenant A is a billing app that sends its system prompt with every request. Tenant B is any other client of the same server. They share one model, a handful of request slots and a prompt cache, and none of these keeps track of which tenant paid for which work.",
        caption: `A pinned <span class="c-violet">llama.cpp server</span> (${D.server.build.split("-")[0]}) serves ${D.server.model} to everyone: ${D.server.slots} slots, ${D.server.n_ctx} tokens of context, prompt caching on by default. <span class="c-teal">Tenant A</span>'s system prompt opens with a fresh conversation tag, then the shop, then a hidden escalation code.`,
        cmd: "docker compose run --rm workbench python attack-cache-sidechannel/scripts/s01_tenants.py" },
      { chapter: "System", label: "The prefix is the unit",
        guide: "Here is what the cache actually stores. A prompt is a row of tokens, and only the leading run that matches a cached prompt can be reused. The four candidate prompts in this lab are identical at first and then differ at the secret code, so the point where they split comes early.",
        caption: `Token anatomy of a probe: ${T.head} shared tokens (tag and text up to the code), ${T.code} code tokens — the only difference between candidates — then a ${T.tail}-token boilerplate tail and a one-token user turn. A hit skips the tail; a miss computes it.`,
        cmd: "docker compose run --rm workbench python attack-cache-sidechannel/scripts/check_env.py" },
      { chapter: "Attack", label: "First-contact probes",
        guide: "Now the attacker goes to work. Right after the victim’s request, it sends each candidate once and records how long each reply took. It can only probe once per round, because a second try would hit the attacker’s own cached copy. So every round starts a fresh conversation.",
        caption: `B probes <code>ATLAS-CANARY-${D.codes[0]}</code> … one candidate per request, in seeded random order, and never reads A’s text. The victim’s own request primed the cache with the live prompt seconds earlier.`,
        cmd: "docker compose run --rm workbench python attack-cache-sidechannel/scripts/s02_signal.py" },
      { chapter: "Mechanism", label: "What the clock measures",
        guide: "Where does the time difference come from? The candidate that matches the cache only has to compute a few new tokens. A wrong candidate has to compute its whole tail. On a CPU server, prefill takes up most of each request, so the saved work shows up directly as a shorter wait.",
        caption: `Reference run: the live-code probe reuses <span class="c-violet">cache_n</span> ${D.signal.rows[0].hit_cache_n} tokens and takes ${ms(D.signal.rows[0].hit)}; a decoy shares only the ${D.signal.rows[0].miss_cache_n}-token header and recomputes the rest, ${ms(D.signal.rows[0].misses)}. The counter is the oracle a real API strips — the clock is what remains.`,
        cmd: "docker compose run --rm workbench python attack-cache-sidechannel/scripts/s02_signal.py" },
      { chapter: "Mechanism", label: "The decision and the test",
        guide: "In a single round, the fastest probe might be fast by luck. So the attacker repeats the round many times and runs a rank test, which checks whether the true code’s times sit consistently below the decoys’ times. Only after that test passes does the attacker pick a candidate.",
        caption: `${AT.rounds} seeded rounds: hit median ${ms(AT.hit_med_ms)} (range ${Math.round(AT.hit_min_ms)}-${Math.round(AT.hit_max_ms)}), miss median ${ms(AT.miss_med_ms)} (range ${Math.round(AT.miss_min_ms)}-${Math.round(AT.miss_max_ms)}). Mann-Whitney U=${AT.U}, p=${p(AT.p)}, AUC ${AT.auc} = P(hit beats miss). Picks: ${AT.picks.k}/${AT.picks.n} = ${Math.round(100 * AT.picks.p)}% [${Math.round(100 * AT.picks.lo)}-${Math.round(100 * AT.picks.hi)}%] against a 25% chance line.`,
        cmd: "docker compose run --rm workbench python attack-cache-sidechannel/scripts/s03_recover.py" },
      { chapter: "Impact", label: "The live code leaks",
        guide: "Both conditions for a real leak now hold. Step 1 showed the cache is shared, and the test in step 5 found a usable timing signal. The attacker names the code the victim configured. The lab canary marks that code, so the match is easy to check.",
        caption: `Round 0 of the reference run: the fastest probe was <code class="c-lime">${D.canary}</code> at ${ms(D.attack.per_round[0].hit)} against decoys ${Math.round(Math.min(...D.attack.per_round[0].misses))}-${Math.round(Math.max(...D.attack.per_round[0].misses))} ms. What leaked is one fact — which known prompt is live — and no prompt text crossed the wire.`,
        cmd: "docker compose run --rm workbench python attack-cache-sidechannel/scripts/s03_recover.py" },
      { chapter: "Impact", label: "How strong, honestly",
        guide: "How much is this result worth on this machine? Re-scoring smaller subsets of the recorded rounds shows how a shorter experiment would have turned out. The drift line shows all the timings shifting while other jobs used the CPU. That’s why the results are reported as ranges and intervals; a single ratio would hide the uncertainty.",
        caption: `Subset study of the same ${AT.rounds} rounds: at k=3, ${TR.table[0].pct_p_below_001}% of subsets reached p&lt;0.01 and accuracy bands reached ${TR.table[0].lo_pct}%; at k=12 and k=24 every subset did. Drift within one run: ${TR.drift_ms[0]} vs ${TR.drift_ms[1]} ms medians. A busier host moves all of it.`,
        cmd: "docker compose run --rm workbench python attack-cache-sidechannel/scripts/s04_trials.py" },
      { chapter: "Defense", label: "Isolate, and measure it",
        guide: "The first defense gives each tenant its own slot. It stops the cache-match counter from leaking, which was the leak in the system-serving lab. The timing still leaks, because the server’s in-memory prompt cache can copy a prefix into any slot. The second defense salts each tenant’s prefix so that different tenants never share cache entries, and that closes the channel.",
        caption: `Through a per-tenant gateway: slots pinned — ${D1.pinned.picks.k}/${D1.pinned.picks.n} picks, p=${p(D1.pinned.p)}, AUC ${D1.pinned.auc} (still leaking); per-tenant cache salt — ${D1.salt.picks.k}/${D1.salt.picks.n} picks, p=${p(D1.salt.p)}, chance level, while A’s own repeats stayed cached (${ms(D1.salt_own.first_ms)} first, ${ms(Math.min(...D1.salt_own.repeat_ms))} repeat).`,
        cmd: "docker compose run --rm workbench python attack-cache-sidechannel/scripts/d1_slots.py salt" },
      { chapter: "Defense", label: "Or drop the cache",
        guide: "The blunt option turns prompt caching off for everyone. With nothing cached, the timings of all candidates look alike. The cost is that the victim’s own repeated requests now pay full prefill every time, and that cost is measured here as well.",
        caption: `With <code>--no-cache-prompt</code>: ${D2.attack.picks.k}/${D2.attack.picks.n} picks, p=${p(D2.attack.p)}, no signal. The bill: A’s repeat median ${ms(median(D2.baseline.repeat_ms))} cached vs ${ms(median(D2.nocache.repeat_ms))} uncached — about +${Math.round(D2.cost_s_per_1000)} s per 1000 repeat requests on the reference machine.`,
        cmd: "docker compose run --rm workbench python attack-cache-sidechannel/scripts/d2_nocache.py nocache" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Tenant A, the llama.cpp server with its slots and prompt cache, tenant B, and a detail panel"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T2 = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T2(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) => S("rect", { x, y, width: w, height: h, rx: 12, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const clip = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

      // ---------- tenant A (left)
      const gA = S("g", { class: "dimmable" }, svg);
      card(gA, 20, 30, 210, 240, V("teal"));
      label(gA, 36, 56, "TENANT A · VICTIM", { fill: V("teal") });
      T2(gA, 36, 80, "billing assistant app", 14);
      const saltA = T2(gA, 36, 106, "salt-A", 13, { class: "mono", fill: V("ok"), "font-weight": 800 });
      S("rect", { x: 32, y: 118, width: 186, height: 96, rx: 8, fill: V("teal"), "fill-opacity": .1, stroke: V("teal"), "stroke-width": 1 }, gA);
      T2(gA, 42, 138, "[CASE-····] system", 13, { class: "mono" });
      T2(gA, 42, 158, "prompt: you are the", 13, { class: "mono" });
      T2(gA, 42, 176, "billing assistant…", 13, { class: "mono" });
      T2(gA, 42, 196, "escalation code", 13, { class: "mono" });
      const canaryA = T2(gA, 42, 214, D.canary, 13, { class: "mono", fill: V("lime"), "font-weight": 800 });
      T2(gA, 36, 240, "sends it with every request", 13, { fill: V("muted") });

      // ---------- tenant B (right)
      const gB = S("g", { class: "dimmable" }, svg);
      const bBox = card(gB, 730, 30, 210, 240, V("bad"));
      label(gB, 746, 56, "TENANT B · ATTACKER", { fill: V("bad") });
      T2(gB, 746, 80, "another client, same port", 14);
      const saltB = T2(gB, 746, 106, "salt-B", 13, { class: "mono", fill: V("ok"), "font-weight": 800 });
      label(gB, 746, 136, "B TIMES ITS OWN ASKS", {});
      const cand = D.codes.map((c, i) => T2(gB, 746, 158 + i * 20, "ATLAS-CANARY-" + c, 13, { class: "mono" }));
      const bLine = T2(gB, 746, 244, "", 13, { class: "mono", fill: V("warn"), "font-weight": 700 });
      const bLine2 = T2(gB, 746, 262, "", 13, { fill: V("bad"), "font-weight": 700 });

      // ---------- server (middle)
      const gSrv = S("g", { class: "dimmable" }, svg);
      card(gSrv, 262, 30, 436, 240, V("violet"));
      label(gSrv, 278, 56, `LLAMA-SERVER · ${D.server.build.split("-")[0]} · ${D.server.slots} SLOTS · N_CTX ${D.server.n_ctx}`, { fill: V("violet") });
      const slotBoxes = [];
      for (let i = 0; i < 4; i++) {
        const x = 280 + i * 102;
        const box = S("rect", { x, y: 70, width: 92, height: 46, rx: 9, fill: V("panel-2"), stroke: V("violet"), "stroke-width": 1.5 }, gSrv);
        T2(gSrv, x + 10, 90, `slot ${i}`, 13, { class: "mono" });
        const tag = T2(gSrv, x + 10, 108, "", 13, { class: "mono", "font-weight": 700 });
        slotBoxes.push({ box, tag });
      }
      label(gSrv, 280, 136, "PROMPT CACHE · SLOTS + RAM (--CACHE-RAM 8192 MiB)");
      const NCELL = 26, cells = [];
      for (let i = 0; i < NCELL; i++) {
        const canaryCell = i === 8 || i === 9;
        const c = S("rect", { x: 280 + i * 16, y: 146, width: 13, height: 24, rx: 4, fill: canaryCell ? V("lime") : V("teal"), opacity: 0 }, gSrv);
        const ring = S("rect", { x: 278 + i * 16, y: 144, width: 17, height: 28, rx: 5, fill: "none", stroke: V("bad"), "stroke-width": 2, opacity: 0 }, gSrv);
        cells.push({ c, ring, canaryCell });
      }
      const diverge = S("line", { x1: 280 + 7 * 16 - 1, y1: 140, x2: 280 + 7 * 16 - 1, y2: 174, stroke: V("bad"), "stroke-width": 2, "stroke-dasharray": "3 3", opacity: 0 }, gSrv);
      const nocacheChip = S("g", {}, gSrv);
      S("rect", { x: 280, y: 186, width: 250, height: 26, rx: 7, fill: V("ok"), "fill-opacity": .14, stroke: V("ok"), "stroke-width": 1.2 }, nocacheChip);
      T2(nocacheChip, 290, 204, "--no-cache-prompt (D2)", 13, { class: "mono", fill: V("ok"), "font-weight": 700 });
      const noCacheNote = T2(gSrv, 545, 204, "", 13, { fill: V("muted") });
      const oracleChip = S("g", {}, gSrv);
      S("rect", { x: 280, y: 222, width: 300, height: 26, rx: 7, fill: V("warn"), "fill-opacity": .12, stroke: V("warn"), "stroke-width": 1.2 }, oracleChip);
      T2(oracleChip, 290, 240, "timings.cache_n: the free oracle", 13, { class: "mono", fill: V("warn"), "font-weight": 700 });

      // ---------- flows + gateway
      const gFlow = S("g", {}, svg);
      const flowA = S("path", { d: "M230 110 C 246 110, 250 110, 280 110", fill: "none", stroke: V("teal"), "stroke-width": 6, "stroke-linecap": "round" }, gFlow);
      const flowB = S("path", { d: "M730 150 C 712 150, 708 170, 700 170", fill: "none", stroke: V("bad"), "stroke-width": 5, "stroke-linecap": "round" }, gFlow);
      const restore = S("path", { d: "M470 176 C 470 250, 640 250, 700 190", fill: "none", stroke: V("bad"), "stroke-width": 4, "stroke-dasharray": "8 6", "stroke-linecap": "round" }, gFlow);
      const gate = S("g", {}, svg);
      S("rect", { x: 700, y: 30, width: 14, height: 240, rx: 7, fill: V("ok") }, gate);
      T2(gate, 707, 288, "gateway", 13, { fill: V("ok"), "font-weight": 700, "text-anchor": "middle" });

      // ---------- detail panels (bottom band)
      const panels = [null];
      const P = () => { const g = S("g", {}, svg); panels.push(g); return g; };
      const row = (g, x, y, cols, size = 14, o = {}) => cols.forEach(([dx, s, oo]) => T2(g, x + dx, y, s, size, { class: "mono", ...o, ...(oo || {}) }));

      // P1 server facts
      let g = P();
      label(g, 30, 322, "WHAT THE SHARED SERVER SHIPS");
      [["prompt cache", "on", "reuses any matching prefix"], ["RAM cache", "8192 MiB", "survives slot churn"],
        ["slots", `${D.server.slots}`, "shared by all tenants"], ["API key", "none", "any client may ask"]]
        .forEach(([k, v, d], i) => {
          const x = 30 + i * 232;
          card(g, x, 338, 216, 110, V("violet"));
          T2(g, x + 16, 366, k, 14, { fill: V("muted"), "font-weight": 700 });
          T2(g, x + 16, 400, v, 24, { class: "mono", "font-weight": 800, fill: V("violet") });
          T2(g, x + 16, 432, d, 13, { fill: V("muted") });
        });

      // P2 token anatomy
      g = P();
      label(g, 30, 322, "ONE PROBE, AS TOKENS (THE CACHE ONLY EVER MATCHES A PREFIX)");
      const parts = [["header + text to the code", T.head, "teal", "shared by all four candidates"],
        ["the code", T.code, "bad", "where candidates split"],
        ["boilerplate tail", T.tail, "violet", "skipped on a hit, computed on a miss"],
        ["user turn", T.user, "warn", "always computed"]];
      parts.forEach(([name, n, col, note], i) => {
        const x = 30, y = 344 + i * 42;
        T2(g, x, y + 18, name, 14, { fill: V("muted") });
        S("rect", { x: 300, y: y + 2, width: 60 + n * 4.4, height: 24, rx: 5, fill: V(col), opacity: .8 }, g);
        T2(g, 306, y + 19, `${n} tok`, 13, { class: "mono", "font-weight": 700 });
        T2(g, 760, y + 18, note, 13, { fill: V("muted") });
      });

      // P3 first-contact protocol
      g = P();
      label(g, 30, 322, "ONE ROUND OF THE SEEDED PROTOCOL");
      [["1", "A starts a conversation; the live prompt enters the cache", V("teal")],
        ["2", "B probes the four candidates once, in random order", V("bad")],
        ["3", "fastest probe wins the round; the tag rotates so nothing repeats", V("warn")],
        ["!", "a second probe of the same text would hit B's own cache", V("muted")]]
        .forEach(([n, s, c], i) => {
          const y = 348 + i * 40;
          S("circle", { cx: 44, cy: y, r: 14, fill: V("panel"), stroke: c, "stroke-width": 2 }, g);
          T2(g, 44, y + 5, n, 14, { "text-anchor": "middle", fill: c, "font-weight": 800 });
          T2(g, 70, y + 5, s, 15);
        });

      // P4 hit vs miss bars
      g = P();
      label(g, 30, 322, "REFERENCE MEASUREMENT: SAME PROBE, CACHED VS NOT");
      const s0 = D.signal.rows[0];
      const hi = Math.max(s0.misses, s0.hit) * 1.15;
      [["live code (hit)", s0.hit, `cache_n ${s0.hit_cache_n} · computes a few tokens`, V("teal")],
        ["decoy (miss)", s0.misses, `cache_n ${s0.miss_cache_n} · computes the whole tail`, V("bad")]]
        .forEach(([name, v, note, c], i) => {
          const y = 352 + i * 60, w = 560 * v / hi;
          T2(g, 30, y + 20, name, 14);
          S("rect", { x: 190, y: y, width: w, height: 30, rx: 6, fill: c, opacity: .85 }, g);
          T2(g, 198 + w, y + 20, ms(v), 15, { class: "mono", "font-weight": 800 });
          T2(g, 190, y + 46, note, 13, { fill: V("muted"), class: "mono" });
        });
      T2(g, 30, 492, `the same reply also carries the counter — an oracle a hosted API strips away`, 14, { fill: V("warn"), "font-weight": 700 });

      // P5 distributions + stats
      g = P();
      label(g, 30, 322, `ALL ${AT.rounds} ROUNDS: ONE DOT PER PROBE, MILLISECONDS`);
      const all = D.attack.hits_ms.concat(D.attack.misses_ms);
      const dlo = 150, dhi = Math.max(...all) * 1.05, dx = v => 40 + 610 * (v - dlo) / (dhi - dlo);
      const r5 = X.rng(7);
      D.attack.misses_ms.forEach(v => {
        const j = r5() * 14;
        S("circle", { cx: dx(v), cy: 356 + j, r: 3.2, fill: V("bad"), opacity: .55 }, g);
      });
      const r6 = X.rng(11);
      D.attack.hits_ms.forEach(v => {
        const j = r6() * 14;
        S("circle", { cx: dx(v), cy: 402 + j, r: 3.6, fill: V("teal"), opacity: .9 }, g);
      });
      S("line", { x1: dx(AT.hit_med_ms), y1: 340, x2: dx(AT.hit_med_ms), y2: 424, stroke: V("teal"), "stroke-width": 2 }, g);
      S("line", { x1: dx(AT.miss_med_ms), y1: 340, x2: dx(AT.miss_med_ms), y2: 424, stroke: V("bad"), "stroke-width": 2 }, g);
      row(g, 40, 440, [[0, "hits", { fill: V("teal") }], [70, "misses", { fill: V("bad") }]], 13);
      [[`p (Mann-Whitney)`, p(AT.p)], [`AUC P(hit faster)`, `${AT.auc}`],
        [`picks right`, `${AT.picks.k}/${AT.picks.n}`], [`Wilson 95%`, `${Math.round(100 * AT.picks.lo)}-${Math.round(100 * AT.picks.hi)}%`]]
        .forEach(([k, v], i) => T2(g, 930, 318 + i * 34, `${k}: ${v}`, 13, { "text-anchor": "end", class: "mono", "font-weight": 700 }));

      // P6 impact
      g = P();
      card(g, 30, 336, 900, 160, V("lime"));
      T2(g, 50, 372, "round 0 pick:", 15, { "font-weight": 700 });
      T2(g, 175, 374, D.canary, 22, { class: "mono", fill: V("lime"), "font-weight": 800 });
      row(g, 50, 412, [[0, "probe", { fill: V("muted") }], [110, ms(D.attack.per_round[0].hit), { fill: V("teal"), "font-weight": 800 }],
        [230, "decoys", { fill: V("muted") }], [320, `${Math.round(Math.min(...D.attack.per_round[0].misses))}-${Math.round(Math.max(...D.attack.per_round[0].misses))} ms`, { fill: V("bad"), "font-weight": 800 }]], 14);
      T2(g, 50, 444, `leaked: which of the four known prompts is live — one small fact, no prompt text`, 15, { "font-weight": 700 });
      T2(g, 50, 470, `scope: this build, this machine, candidates that split early, a quiet enough server`, 13, { fill: V("muted") });

      // P7 trials
      g = P();
      label(g, 30, 322, "HOW MANY ROUNDS DOES THE VERDICT NEED? (SUBSETS OF THE RECORDED RUN)");
      T2(g, 40, 348, "rounds kept", 13, { class: "mono", fill: V("muted") });
      T2(g, 170, 348, "pick accuracy (5-95% of subsets)", 13, { class: "mono", fill: V("muted") });
      T2(g, 480, 348, "subsets with p<0.01", 13, { class: "mono", fill: V("muted") });
      TR.table.forEach((r, i) => {
        const y = 372 + i * 32;
        row(g, 40, y, [[0, `${r.k}`, { "font-weight": 800 }], [130, `${r.mean_pct}%  [${r.lo_pct}-${r.hi_pct}%]`, {}]], 14);
        const w = 240 * r.pct_p_below_001 / 100;
        S("rect", { x: 480, y: y - 15, width: w, height: 20, rx: 4, fill: r.pct_p_below_001 >= 95 ? V("ok") : V("warn"), opacity: .8 }, g);
        T2(g, 486 + w, y, `${r.pct_p_below_001}%`, 13, { class: "mono", "font-weight": 700 });
      });
      T2(g, 40, 508, `drift inside one run: ${TR.drift_ms[0]} ms first half, ${TR.drift_ms[1]} ms second half — other jobs were using the machine`, 13, { fill: V("muted") });

      // P8 defenses
      g = P();
      label(g, 30, 322, "THROUGH THE PER-TENANT GATEWAY (12 ROUNDS EACH)");
      [["slots pinned", D1.pinned, "the RAM cache re-supplies the prefix; the counter died, the clock leaked"],
        ["cache salt", D1.salt, "prefixes never match across tenants; A keeps its own reuse"]]
        .forEach(([name, s, note], i) => {
          const x = 30 + i * 460;
          card(g, x, 338, 440, 118, i ? V("ok") : V("bad"));
          T2(g, x + 18, 366, name, 16, { "font-weight": 800, class: "mono" });
          row(g, x + 18, 396, [[0, `picks ${s.picks.k}/${s.picks.n}`, { "font-weight": 800 }], [150, `p=${p(s.p)}`, {}], [280, `AUC ${s.auc}`, {}]], 14);
          T2(g, x + 18, 424, note, 13, { fill: V("muted") });
        });
      T2(g, 30, 490, `A's own repeat, salted: first ${ms(D1.salt_own.first_ms)}, repeat ${ms(Math.min(...D1.salt_own.repeat_ms))} — each tenant keeps its own cache`, 14, { "font-weight": 700 });

      // P9 no-cache cost
      g = P();
      label(g, 30, 322, "D2: --NO-CACHE-PROMPT — NO REUSE FOR ANYONE");
      [[`picks`, `${D2.attack.picks.k}/${D2.attack.picks.n} (chance 25%)`], [`Mann-Whitney p`, p(D2.attack.p)],
        [`A repeat, cached`, ms(median(D2.baseline.repeat_ms))],
        [`A repeat, no cache`, ms(median(D2.nocache.repeat_ms))]]
        .forEach(([k, v], i) => row(g, 40, 356 + i * 32, [[0, k, { fill: V("muted") }], [240, v, { "font-weight": 800 }]], 14));
      card(g, 560, 338, 370, 140, V("ok"));
      T2(g, 580, 372, "the measured bill", 15, { "font-weight": 700 });
      T2(g, 580, 406, `+${Math.round(D2.cost_s_per_1000)} s`, 30, { class: "mono", fill: V("ok"), "font-weight": 800 });
      T2(g, 580, 440, "extra prefill per 1000 repeat requests, reference machine", 13, { fill: V("muted") });

      // ---------- state
      const base = { a: 0, cache: 0, b: 0, match: 0, pick: 0, have: 0, gate: 0, salt: 0, nocache: 0, pn: 1 };
      const T_N = [null,
        { a: 1, pn: 1 },
        { a: 1, cache: 1, pn: 2 },
        { a: 1, cache: 1, b: 1, pn: 3 },
        { a: 1, cache: 1, b: 1, match: 1, pn: 4 },
        { a: 1, cache: 1, b: 1, match: 1, pick: 1, pn: 5 },
        { a: 1, cache: 1, b: 1, match: 1, pick: 1, have: 1, pn: 6 },
        { a: 1, cache: 1, b: 1, pick: 1, have: 1, pn: 7 },
        { a: 1, cache: 1, b: 1, gate: 1, have: 1, pn: 8 },
        { a: 1, cache: 0, b: 1, gate: 1, salt: 1, nocache: 1, pn: 9 },
      ];
      const st = { ...base };
      const target = n => ({ ...base, ...T_N[n] });

      function draw(s) {
        // panels crossfade by distance to pn
        panels.forEach((pp, i) => { if (pp) pp.setAttribute("opacity", Math.max(0, 1 - Math.abs(s.pn - i) * 1.6).toFixed(3)); });
        // cache cells: A's prompt fills them; the gateway/salt/nocache states change what can match
        const live = Math.round(9 * s.a * s.cache * (1 - s.nocache));
        cells.forEach((c, i) => {
          c.c.setAttribute("opacity", i < live ? (c.canaryCell ? .95 : .5) : 0);
          c.ring.setAttribute("opacity", (i < live ? seg(s.match * 1.4 - i / live, 0, .3) : 0).toFixed(3));
        });
        diverge.setAttribute("opacity", s.cache.toFixed(3));
        oracleChip.setAttribute("opacity", ((s.pn >= 4 && s.pn <= 6 ? 1 : .25) * (1 - s.gate) * (1 - s.nocache)).toFixed(3));
        nocacheChip.setAttribute("opacity", s.nocache.toFixed(3));
        noCacheNote.textContent = s.nocache > .5 ? "nothing is cached" : "";
        // slots: A in slot 0, B in slot 1 when the gateway pins
        slotBoxes.forEach((sl, i) => {
          const inA = i === 0 && s.a > 0, inB = i === 1 && s.b > 0;
          A(sl.box, { stroke: s.gate > .5 && ((i === 0 && s.a) || (i === 1 && s.b)) ? V("ok") : V("violet"), "stroke-width": s.gate > .5 ? 2.5 : 1.5 });
          sl.tag.textContent = inA ? "A" : inB ? "B" : "";
          A(sl.tag, { fill: inA ? V("teal") : inB ? V("bad") : V("muted") });
        });
        // flows
        A(flowA, { opacity: s.a.toFixed(3) });
        A(flowB, { opacity: s.b.toFixed(3), stroke: s.gate > .5 ? V("ok") : V("bad") });
        A(restore, { opacity: (s.match * s.gate * .9).toFixed(3) });
        gate.setAttribute("opacity", s.gate.toFixed(3));
        // salts
        saltA.setAttribute("opacity", s.salt.toFixed(3));
        saltB.setAttribute("opacity", s.salt.toFixed(3));
        // tenant B readout
        cand.forEach((t, i) => {
          const hot = s.have > .5 && i === 0;
          const col = hot ? V("lime") : (s.match > .5 && i === 0 && s.pick > .5 ? V("warn") : "");
          if (col) t.style.fill = col; else t.removeAttribute("style");
          A(t, { "font-weight": hot ? 800 : 400 });
        });
        bLine.textContent = s.pn >= 9 ? "all probes ~equal" : s.pn >= 8 ? s.salt > .5 ? "no prefix matches A" : "restore crosses slots" : s.pick > .5 ? `fastest: ${D.codes[0]}` : "one clock per probe";
        bLine2.textContent = s.pn >= 9 ? `p=${p(D2.attack.p)} · chance` : s.pn >= 8 ? `picks ${D1.salt.picks.k}/${D1.salt.picks.n}` : s.have > .5 ? `it is live: ${D.canary}` : s.pick > .5 ? `p=${p(AT.p)}` : "";
        A(bLine, { fill: V("warn") });
        // focus
        const focus = s.pn >= 8 ? [gSrv, gB] : s.have > .5 ? [gB, gSrv] : s.pn === 5 ? [gSrv] : [];
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
