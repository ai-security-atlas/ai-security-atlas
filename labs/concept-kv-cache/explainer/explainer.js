/* LAB-38 concept-kv-cache explainer. Foundation lab: the five chapters read as
 * System -> Risk -> Mechanism -> Observation -> Defense (the engine's Attack/Impact slots carry Risk/Observation).
 * All numbers come from window.LAB_DATA (data.js), written by scripts/export_explainer_data.py. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp;
  const D = window.LAB_DATA;
  const mb = b => (b / 1048576).toFixed(1);
  const med = a => { const s = [...a].sort((x, y) => x - y); return s.length ? s[s.length >> 1] : 0; };
  const grow = D.grow[D.grow.length - 1], cost = D.cost[D.cost.length - 1];
  const jit = D.d2.table.find(t => t.single_acc < 0.9) || D.d2.table[D.d2.table.length - 1];

  X.define({
    id: "concept-kv-cache",
    family: "family-privacy",
    title: 'The cache <span class="outline">remembers</span>',
    legend: ["teal", "bad", "violet", "warn", "lime", "ok"],
    intro: {
      why: "A language model answers one token at a time, and each new token needs every earlier token’s attention data. Systems store that data in a cache and reuse it, which is pure speed. This walkthrough asks what else that stored, reused state gives away.",
      plan: "You first watch the cache grow inside one model and see a different architecture keep a fixed-size state. Then you move to a shared server, time a repeated prefix against a fresh one, and guess from the clock whether someone sent a known prefix. You finish by scoping the cache and by adding timing noise.",
      terms: "A token is one chunk of text the model reads. The key/value cache (KV cache) holds the attention data for every token so far. Prefix reuse keeps that cache for a shared opening stretch of a prompt across requests. Time to first token is how long you wait before the reply starts.",
    },
    steps: [
      { chapter: "System", label: "Cache grows",
        guide: "Watch the cache fill as a prompt gets longer. Each token adds the same fixed block of keys and values to every layer, so the cache grows in step with the token count. Because those bytes are kept, the model can produce the next token without redoing the work for the earlier ones.",
        caption: `SmolLM2-135M keeps <span class="c-teal">keys and values</span> for ${D.model.layers} layers: <code>${D.model.layers}×2×${D.model.kv_heads}×${D.model.head_dim}×4</code> = <span class="c-teal">${D.model.per_token.toLocaleString()} bytes/token</span>. At ${grow.tokens} tokens the cache is ${mb(grow.cache_bytes)} MiB, and one cached step costs about <span class="c-warn">${cost.step_ms} ms</span> against <span class="c-warn">${cost.full_ms} ms</span> to recompute (T=${cost.T}).`,
        cmd: "docker compose run --rm workbench python concept-kv-cache/scripts/s01_cache_grows.py" },
      { chapter: "System", label: "Fixed state",
        guide: "Look at a different kind of model. A state-space model folds the whole sequence into one recurrent state and updates it in place. The box stays the same size whether the prompt is short or long. It has no per-token keys, so a server that wants prefix reuse here has to save the whole state at the end of a prefix.",
        caption: `mamba-130m carries a fixed <span class="c-violet">${mb(D.mamba.state_bytes)} MiB</span> recurrent state at every length. It has no growing <span class="c-teal">key/value cache</span>, so the per-token reuse below needs a different design here, and that saved state would raise the same sharing question (<span class="c-violet">arch-ssm</span>).`,
        cmd: "docker compose run --rm workbench python concept-kv-cache/scripts/s02_mamba.py" },
      { chapter: "Attack", label: "Cache persists",
        guide: "Move to a server that many clients share. One client sends a long prompt, and the server computes and stores its whole cache. The next identical request reuses that stored state and returns almost instantly. The cache outlived the request that made it, and the server never asked who the next request belonged to.",
        caption: `A ${D.persist.prefix_tokens}-token prompt takes <span class="c-warn">${D.persist.first_ms} ms</span> the first time; an identical repeat returns in about <span class="c-lime">${Math.round(med(D.persist.repeat_ms))} ms</span> (${D.persist.speedup}× faster). The shared <span class="c-teal">prompt cache</span> held the state for whoever asked next.`,
        cmd: "docker compose run --rm workbench python concept-kv-cache/scripts/s03_persist.py" },
      { chapter: "Mechanism", label: "Skip the prefill",
        guide: "See where the time goes. A prompt splits into an opening stretch and the rest. When a probe repeats a stretch the server already holds, the server skips recomputing it and the reply comes back fast. A probe with a fresh stretch pays for all of it. The only thing that changed is whether the cache held that prefix.",
        caption: `The probe splits into a <span class="c-lime">${D.anatomy.n_head}-token canary opener</span> and a <span class="c-teal">${D.anatomy.n_body}-token body</span>. Sharing the cached prefix returns in <span class="c-lime">${D.anatomy.hit_ms} ms</span>; a fresh prefix pays full prefill at <span class="c-warn">${D.anatomy.miss_ms} ms</span> (${D.anatomy.ratio}× slower).`,
        cmd: "docker compose run --rm workbench python concept-kv-cache/scripts/s04_prefix.py" },
      { chapter: "Mechanism", label: "Clock only",
        guide: "Take away the help. The server also reports how many tokens it reused, but a hosted API hides that number. From here you keep only the wall-clock time a normal client can see. A fast reply and a slow reply are all the attacker gets to work with.",
        caption: `The server’s own <code>cache_n</code> counter (<span class="c-teal">${D.anatomy.hit_cache_n}</span> on a hit, <span class="c-muted">${D.anatomy.miss_cache_n}</span> on a miss) is the oracle a real API strips. The rest of the measurement trusts the <span class="c-warn">clock</span> alone.` },
      { chapter: "Impact", label: "Hit vs miss",
        guide: "Run many rounds and plot the probe times by what actually happened. On the rounds where the prefix was sent, the probe lands in the fast cluster; on the rounds where it was not, it lands in the slow cluster. With a long prefix the two clusters barely touch, so a threshold between them sorts almost every round.",
        caption: `Over ${D.guess.rounds} seeded rounds the <span class="c-lime">sent</span> probes cluster near <span class="c-lime">${Math.round(D.guess.summary.hit_med_ms)} ms</span> and the <span class="c-warn">not-sent</span> probes near <span class="c-warn">${Math.round(D.guess.summary.miss_med_ms)} ms</span> (${D.guess.summary.ratio}× apart). Mann-Whitney <code>p=${D.guess.summary.p.toExponential(1)}</code>, AUC <span class="c-violet">${D.guess.summary.auc}</span>.`,
        cmd: "docker compose run --rm workbench python concept-kv-cache/scripts/s05_guess.py" },
      { chapter: "Impact", label: "Guess the prefix",
        guide: "Make the call. You send one probe of the known prefix, read the clock once, and guess whether someone else processed this prefix recently. The caption scores those guesses against a coin. What you learn is one bit about a prompt whose shape you already knew, and none of anyone’s text ever reaches you.",
        caption: `The threshold is <span class="c-warn">${D.guess.threshold_ms} ms</span>. Guessing from time alone, B is right <span class="c-lime">${D.guess.acc.k}/${D.guess.acc.n}</span> (${Math.round(D.guess.acc.p * 100)}% [${Math.round(D.guess.acc.lo * 100)}–${Math.round(D.guess.acc.hi * 100)}%]) against a 50% coin: the server never said whether the <code class="c-lime">${D.canary}</code> prefix was sent, yet the clock did.` },
      { chapter: "Defense", label: "Scope or pad",
        guide: "Close the channel two ways and weigh each. A gateway can put a secret per-tenant tag in front of every prompt, so two tenants never share a prefix and the clusters collapse onto each other, while each tenant still reuses its own cache. Random padding on the reply time blurs the gap once the padding is about as large as the gap. An attacker who repeats the guess with independent first-contact probes, each in a fresh round, wins most of it back.",
        caption: `A <span class="c-ok">per-tenant salt</span> drops B to <span class="c-ok">${D.d1.acc.k}/${D.d1.acc.n}</span> (AUC ${D.d1.summary.auc}), while A still repeats in about <span class="c-lime">${Math.round(med(D.d1.own_repeat_ms))} ms</span>. Jitter of ${jit.J} ms drops one guess to <span class="c-warn">${Math.round(jit.single_acc * 100)}%</span> but adds <span class="c-warn">${jit.added_ms} ms</span> to the average reply, and averaging ${jit.probes_90} independent probes brings it back to 90% or more.`,
        cmd: "docker compose run --rm workbench python concept-kv-cache/scripts/d1_scope.py" },
    ],
    html: `<style>
      [data-explainer="concept-kv-cache"] .axlab { font-size: 12px; fill: var(--lx-muted); font-weight: 700; letter-spacing: 1px; }
      [data-explainer="concept-kv-cache"] .mono { font-family: "JetBrains Mono", monospace; }
    </style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="A key/value cache growing inside a model, then reused across requests on a shared server"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 16, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const axlab = (p, x, y, s) => T(p, x, y, s, 12, { class: "axlab" });
      const card = (p, x, y, w, h, stroke = V("line")) => S("rect", { x, y, width: w, height: h, rx: 14, fill: V("panel"), stroke, "stroke-width": 2 }, p);

      // ---------- model scene (steps 1-2) ----------
      const gModel = S("g", {}, svg);
      axlab(gModel, 70, 96, "ONE MODEL, ONE PROMPT");
      card(gModel, 70, 110, 360, 360, V("violet"));
      T(gModel, 90, 150, "transformer: key/value cache", 15, { fill: V("violet"), "font-weight": 700 });
      const cells = [];
      for (let i = 0; i < 12; i++) {
        const y = 172 + i * 23;
        S("rect", { x: 92, y, width: 150, height: 17, rx: 5, fill: V("line"), opacity: .25 }, gModel);
        cells.push(S("rect", { x: 92, y, width: 150, height: 17, rx: 5, fill: V("teal"), opacity: 0 }, gModel));
      }
      const byteTxt = T(gModel, 258, 250, `${D.model.per_token.toLocaleString()} bytes / token`, 15, { class: "mono", fill: V("teal") });
      const byteTxt2 = T(gModel, 258, 276, "grows with every token", 13, { fill: V("muted") });
      const gMamba = S("g", {}, gModel);
      S("rect", { x: 262, y: 322, width: 150, height: 110, rx: 12, fill: V("violet"), "fill-opacity": .18, stroke: V("violet"), "stroke-width": 2 }, gMamba);
      T(gMamba, 337, 360, "state-space model", 13, { "text-anchor": "middle", fill: V("violet"), "font-weight": 700 });
      T(gMamba, 337, 384, "fixed recurrent state", 12, { "text-anchor": "middle", fill: V("muted") });
      const mamByte = T(gMamba, 337, 412, `${mb(D.mamba.state_bytes)} MiB, fixed`, 13, { "text-anchor": "middle", class: "mono", fill: V("violet") });

      // ---------- server scene (steps 3-8) ----------
      const gServer = S("g", {}, svg);
      axlab(gServer, 70, 96, "ONE SERVER, MANY CLIENTS");
      card(gServer, 360, 120, 240, 150, V("violet"));
      T(gServer, 480, 150, "llama.cpp server", 14, { "text-anchor": "middle", fill: V("violet"), "font-weight": 700 });
      T(gServer, 480, 172, "PROMPT CACHE", 12, { "text-anchor": "middle", class: "axlab" });
      S("rect", { x: 384, y: 186, width: 192, height: 26, rx: 7, fill: V("line"), opacity: .3 }, gServer);
      const cacheBar = S("rect", { x: 384, y: 186, width: 0, height: 26, rx: 7, fill: V("teal"), opacity: .85 }, gServer);
      const cacheTxt = T(gServer, 480, 204, "", 12, { "text-anchor": "middle", class: "mono", fill: V("teal") });
      const gA = S("g", {}, gServer);
      card(gA, 70, 150, 150, 92, V("teal"));
      T(gA, 80, 178, "tenant A", 14, { fill: V("teal"), "font-weight": 700 });
      T(gA, 80, 200, "sends the", 12, { fill: V("muted") });
      T(gA, 80, 216, "canary prefix", 12, { class: "mono", fill: V("lime") });
      const gB = S("g", {}, gServer);
      card(gB, 740, 150, 150, 92, V("bad"));
      T(gB, 750, 178, "tenant B", 14, { fill: V("bad"), "font-weight": 700 });
      T(gB, 750, 200, "times its", 12, { fill: V("muted") });
      T(gB, 750, 216, "own probe", 12, { class: "mono", fill: V("bad") });
      const ribA = S("path", { d: "M220 196 H360", fill: "none", stroke: V("teal"), "stroke-width": 3, opacity: 0 }, gServer);
      const ribB = S("path", { d: "M740 196 H600", fill: "none", stroke: V("bad"), "stroke-width": 3, opacity: 0 }, gServer);
      const wall = S("rect", { x: 300, y: 150, width: 9, height: 0, rx: 4, fill: V("ok") }, gServer);
      const wallTxt = T(gServer, 304, 128, "salt", 12, { "text-anchor": "middle", fill: V("ok"), "font-weight": 700, opacity: 0 });

      const gAxis = S("g", {}, gServer);
      const AX0 = 150, AX1 = 880, AY = 430;
      const lo = Math.log10(8), hi = Math.log10(1200);
      const msx = ms => AX0 + (Math.log10(Math.max(8, ms)) - lo) / (hi - lo) * (AX1 - AX0);
      S("line", { x1: AX0, y1: AY, x2: AX1, y2: AY, stroke: V("line"), "stroke-width": 2 }, gAxis);
      [10, 30, 100, 300, 1000].forEach(t => {
        S("line", { x1: msx(t), y1: AY - 5, x2: msx(t), y2: AY + 5, stroke: V("line"), "stroke-width": 2 }, gAxis);
        T(gAxis, msx(t), AY + 22, t + " ms", 11, { "text-anchor": "middle", class: "axlab" });
      });
      T(gAxis, AX1, AY + 22, "time to first token", 11, { "text-anchor": "end", class: "axlab" });
      const hitBar = S("rect", { x: AX0, y: 332, width: 0, height: 18, rx: 5, fill: V("lime"), opacity: .9 }, gServer);
      const missBar = S("rect", { x: AX0, y: 356, width: 0, height: 18, rx: 5, fill: V("warn"), opacity: .9 }, gServer);
      const hitLab = T(gServer, 0, 346, "hit", 12, { class: "mono", fill: V("lime"), opacity: 0 });
      const missLab = T(gServer, 0, 370, "miss", 12, { class: "mono", fill: V("warn"), opacity: 0 });
      const r = X.rng(38);
      const hitX = (D.guess.hits_ms || []).map(msx);
      const hitDots = (D.guess.hits_ms || []).map((ms, i) => S("circle", { r: 6, cx: msx(ms), cy: AY - 30 - r() * 70, fill: V("lime"), opacity: 0 }, gServer));
      const missDots = (D.guess.misses_ms || []).map(ms => S("circle", { r: 6, cx: msx(ms), cy: AY - 30 - r() * 70, fill: V("warn"), opacity: 0 }, gServer));
      const saltX = msx(D.d1.summary.miss_med_ms);   // where hits land once salting makes every probe a miss
      const probe = S("circle", { r: 10, cx: msx(D.guess.rows[0].ms), cy: AY - 115, fill: V("bad"), opacity: 0 }, gServer);
      const verdict = T(gServer, 480, 292, "", 15, { "text-anchor": "middle", "font-weight": 700, opacity: 0 });

      // ---------------- state ----------------
      const base = { scene: 0, fill: 0, mamba: 0, prime: 0, anatomy: 0, clock: 0, dist: 0, guess: 0, salt: 0 };
      const st = { ...base };
      const T_N = [null,
        { scene: 0, fill: 1 },
        { scene: 0, fill: 1, mamba: 1 },
        { scene: 1, prime: 1 },
        { scene: 1, prime: 1, anatomy: 1 },
        { scene: 1, prime: 1, anatomy: 1, clock: 1 },
        { scene: 1, prime: 1, dist: 1 },
        { scene: 1, prime: 1, dist: 1, guess: 1 },
        { scene: 1, dist: 1, salt: 1 },
      ];
      const target = n => ({ ...base, ...T_N[n] });

      function draw(s) {
        gModel.setAttribute("opacity", (1 - s.scene).toFixed(3));
        gServer.setAttribute("opacity", s.scene.toFixed(3));
        gModel.style.pointerEvents = s.scene > .5 ? "none" : "";
        const filled = Math.round(cells.length * seg(s.fill, 0, 1));
        cells.forEach((c, i) => c.setAttribute("opacity", i < filled ? (.85 * (1 - s.mamba) + .12 * (1 - s.mamba)).toFixed(3) : "0"));
        byteTxt.setAttribute("opacity", (1 - s.mamba).toFixed(3));
        byteTxt2.setAttribute("opacity", (1 - s.mamba).toFixed(3));
        gMamba.setAttribute("opacity", s.mamba.toFixed(3));
        A(cacheBar, { width: (192 * seg(s.prime, 0, 1)).toFixed(1) });
        cacheTxt.textContent = s.prime > .5 ? `${D.persist.prefix_tokens} tokens held` : "";
        cacheTxt.setAttribute("opacity", (1 - .6 * s.clock).toFixed(3));
        ribA.setAttribute("opacity", (s.prime * (1 - s.salt)).toFixed(3));
        ribB.setAttribute("opacity", s.prime.toFixed(3));
        A(hitBar, { width: ((msx(D.anatomy.hit_ms) - AX0) * s.anatomy).toFixed(1) });
        A(missBar, { width: ((msx(D.anatomy.miss_ms) - AX0) * s.anatomy).toFixed(1) });
        hitLab.setAttribute("x", (msx(D.anatomy.hit_ms) + 10)); hitLab.setAttribute("opacity", s.anatomy.toFixed(3));
        missLab.setAttribute("x", (msx(D.anatomy.miss_ms) + 10)); missLab.setAttribute("opacity", s.anatomy.toFixed(3));
        hitDots.forEach((d, i) => { d.setAttribute("opacity", (s.dist * .9).toFixed(3)); d.setAttribute("cx", L(hitX[i], saltX, s.salt).toFixed(1)); });
        missDots.forEach(d => d.setAttribute("opacity", (s.dist * .9).toFixed(3)));
        probe.setAttribute("opacity", (s.guess * (1 - s.salt)).toFixed(3));
        if (s.salt > .5) {
          verdict.textContent = D.d1.acc.lo <= .5 ? "salted: the clusters merge, no signal" : "salted: a gap remains";
          A(verdict, { fill: V("ok") });
        } else if (s.guess > .5) {
          verdict.textContent = `probe ${Math.round(D.guess.rows[0].ms)} ms → “${D.guess.rows[0].sent ? "sent" : "not sent"}”`;
          A(verdict, { fill: V("lime") });
        }
        verdict.setAttribute("opacity", Math.max(s.guess, s.salt).toFixed(3));
        A(wall, { height: (150 * seg(s.salt, 0, 1)).toFixed(1) });
        wallTxt.setAttribute("opacity", seg(s.salt, .4, 1).toFixed(3));
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }
          return api.tween(n === 1 ? 900 : 700, k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
