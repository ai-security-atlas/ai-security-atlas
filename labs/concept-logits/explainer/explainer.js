/* LAB-05 concept-logits: "What the API reveals" (foundation lab, 9 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: the pipeline strip across the top (prompt -> model -> logits -> softmax -> sample) and a detail
 * panel below that crossfades per step. Every number and string comes from window.LAB_DATA (data.js,
 * exported from the reference workbench run). Pattern: target(n) is pure, draw(s) is pure, step() tweens
 * forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp;
  const D = window.LAB_DATA;
  const kb = b => (b >= 1e5 ? Math.round(b / 1000) + " KB" : b >= 1000 ? (b / 1000).toFixed(1) + " KB" : b + " B");
  const sp = D.secret_probe;
  const def1 = D.defense.find(r => r.policy === "full round=1") || {};

  X.define({
    id: "concept-logits",
    family: "family-theft",
    title: 'What the API <span class="outline">reveals</span>',
    legend: [{ role: "teal", label: "Prompt / data" }, { role: "violet", label: "Model / logits" },
      { role: "warn", label: "Reply text" }, { role: "bad", label: "What leaks" }, { role: "lime", label: "Canary" },
      { role: "ok", label: "Defense" }],
    steps: [
      { chapter: "System", label: "Logits",
        caption: `For “${D.prompt}”, ${D.model} computes one <span class="c-violet">logit</span> per vocabulary entry: ${D.vocab.toLocaleString("en")} raw scores. The top one is <code>${D.top[0][0].trim()}</code> at ${D.top[0][1]}.`,
        cmd: "docker compose run --rm workbench python concept-logits/scripts/s01_next_token.py" },
      { chapter: "System", label: "Softmax, then sample",
        caption: `Softmax turns logits into <span class="c-warn">probabilities</span> (${(D.top[0][2] * 100).toFixed(1)}% for <code>${D.top[0][0].trim()}</code>); sampling picks one. Temperature reshapes them: 1000 samples give ${D.temps["0.5"].distinct} distinct tokens at T = 0.5 and ${D.temps["2.0"].distinct} at T = 2.` },
      { chapter: "Attack", label: "Three detail levels",
        caption: `Risk: one model behind one API can return <span class="c-warn">text only</span>, text plus <span class="c-bad">top-5 logprobs</span> per token, or <span class="c-bad">full rows</span> of ${D.vocab.toLocaleString("en")} logprobs. Same request: ${kb(D.levels.text)}, ${kb(D.levels.topk)}, ${kb(D.levels.full)}.`,
        cmd: "docker compose run --rm workbench python concept-logits/scripts/s02_detail_levels.py" },
      { chapter: "Mechanism", label: "Logprobs skip the filter",
        caption: `The app's <span class="c-ok">output filter</span> redacts the vault code from the reply text. The logprobs describe the tokens the model actually sampled, so the <span class="c-bad">top-5 list</span> still holds the letter after <code>l0g1-</code>: ${D.letter_top5[0][0]} at ${D.letter_top5[0][1].toFixed(2)}, ${D.letter_top5[1][0]} at ${D.letter_top5[1][1].toFixed(2)}.`,
        cmd: "docker compose run --rm workbench python concept-logits/scripts/s03_which_secret.py" },
      { chapter: "Impact", label: "Queries to the secret",
        caption: `Which canary is hidden, <code class="c-lime">${D.secret}</code> or the -B one? Text only: not in ${sp.text.queries} replies, and the yes/no side question would need about ${D.side_n.toLocaleString("en")} samples. Top-5 logprobs: 1 query. Full: 1 query.` },
      { chapter: "Impact", label: "Confidence as membership",
        caption: `Six well-known texts against one-word near-duplicates. Greedy text picks the original ${D.near_summary.text}/6 times with no margin; full scoring picks it ${D.near_summary.full}/6 with a <span class="c-bad">confidence margin</span> of 6 to 17 nats: a membership-style signal.`,
        cmd: "docker compose run --rm workbench python concept-logits/scripts/s04_near_duplicate.py" },
      { chapter: "Impact", label: "Rows reveal the width",
        caption: `Stack ${D.spectrum.length * D.spectrum_step} full rows and look at their singular values: they fall off a cliff after number <span class="c-bad">${D.dim}</span>, the model's hidden size, a ${Math.round(D.dim_ratio).toLocaleString("en")}-fold drop. The rows live in a ${D.dim}-dimensional subspace.`,
        cmd: "docker compose run --rm workbench python concept-logits/scripts/s05_hidden_dim.py" },
      { chapter: "Defense", label: "Round and cut",
        caption: `<span class="c-ok">Rounding</span> to 1 decimal still shows ${def1.hidden} (the cliff shrinks to ${def1.ratio.toFixed(1)}×); whole numbers hide it. Neither hides the secret. Only <span class="c-ok">scrubbing logprobs</span> from filtered replies, or text only, does.`,
        cmd: "docker compose run --rm workbench python concept-logits/scripts/d1_limit_detail.py" },
      { chapter: "Defense", label: "Cost, not removal",
        caption: `Less detail raises the attacker's cost; it does not remove the signal: text-only still picks ${D.near_summary.text}/6 originals. Pair it with per-key <span class="c-ok">query budgets</span> and logging, and measure cost per leak.`,
        cmd: "docker compose run --rm workbench python concept-logits/scripts/evaluate.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Prompt, model, logits, softmax and sample, with a detail panel"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) => S("rect", { x, y, width: w, height: h, rx: 12, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = (p, d) => S("path", { d, fill: "none", stroke: V("dim"), "stroke-width": 2, "marker-end": `url(#${arrowId})` }, p);

      // ---- pipeline strip
      const strip = [["PROMPT", "teal", D.prompt.split(" ").slice(-2).join(" ") + "…"], ["MODEL", "violet", `hidden ${D.hidden}`],
        ["LOGITS", "violet", `${D.vocab.toLocaleString("en")} scores`], ["SOFTMAX", "violet", "probabilities"], ["SAMPLE", "warn", D.top[0][0].trim()]];
      const gStrip = S("g", { class: "dimmable" }, svg);
      const stripBox = [];
      strip.forEach(([k, role, sub], i) => {
        const x = 30 + i * 186;
        const b = card(gStrip, x, 26, 160, 70, V(role));
        label(gStrip, x + 14, 52, k, { fill: V(role) });
        T(gStrip, x + 14, 80, sub, 15, { class: "mono" });
        if (i) arrow(gStrip, `M${x - 24} 61 H${x - 4}`);
        stripBox.push(b);
      });

      const panel = () => S("g", { class: "dimmable" }, svg);

      // ---- P1/P2: logit bars that become probability bars
      const gBars = panel();
      const barsTitle = label(gBars, 60, 136, "");
      const bars = D.top.map((r, i) => {
        const y = 156 + i * 40;
        T(gBars, 60, y + 22, JSON.stringify(r[0]), 15, { class: "mono" });
        const bar = S("rect", { x: 220, y, width: 0, height: 28, rx: 6 }, gBars);
        const val = T(gBars, 0, y + 20, "", 14, { class: "mono" });
        return { bar, val, r };
      });
      const gTemp = S("g", {}, gBars);
      label(gTemp, 640, 136, "1000 SAMPLES");
      const tcards = ["0.5", "1.0", "2.0"].map((k, i) => {
        const y = 156 + i * 104, t = D.temps[k];
        card(gTemp, 640, y, 280, 88, V("warn"));
        T(gTemp, 660, y + 30, `T = ${k}`, 17, { "font-weight": 700, fill: V("warn") });
        T(gTemp, 660, y + 56, `p(top) ${t.p_top}  ·  entropy ${t.entropy}`, 14, { class: "mono" });
        T(gTemp, 660, y + 76, `${t.top_hits}× top token · ${t.distinct} distinct`, 14, { class: "mono" });
        return null;
      });
      void tcards;

      // ---- P3: three detail levels
      const gLev = panel();
      label(gLev, 60, 136, "SAME REQUEST, THREE DETAIL LEVELS");
      const lev = [["text only", D.levels.text, "warn", `“${D.redacted}”`],
        ["text + top-5 logprobs", D.levels.topk, "bad", "every token: logprob + 5 alternatives"],
        ["full logprobs (/v1/score)", D.levels.full, "bad", `${D.vocab.toLocaleString("en")} logprobs per position`]];
      const maxLog = Math.log10(D.levels.full);
      const levBars = lev.map(([name, bytes, role, desc], i) => {
        const y = 160 + i * 118;
        card(gLev, 60, y, 840, 100, V(role));
        T(gLev, 80, y + 32, name, 18, { "font-weight": 700, fill: V(role) });
        T(gLev, 80, y + 62, desc, 14, { class: "mono" });
        const bar = S("rect", { x: 80, y: y + 74, width: 0, height: 12, rx: 4, fill: V(role), opacity: .7 }, gLev);
        T(gLev, 880, y + 32, kb(bytes), 18, { class: "mono", "text-anchor": "end", "font-weight": 700 });
        return { bar, w: 780 * Math.log10(bytes) / maxLog };
      });

      // ---- P4: filter vs logprobs
      const gMech = panel();
      label(gMech, 60, 136, "REPLY TEXT (AFTER THE FILTER)");
      card(gMech, 60, 150, 840, 64, V("warn"));
      T(gMech, 80, 190, D.redacted, 17, { class: "mono", fill: V("warn") });
      label(gMech, 60, 250, "LOGPROBS FOR THE SAME REPLY");
      const toks = ["AT", "L", "AS", "-", "CA", "NA", "RY", "-", "l", "0", "g", "1", "-", D.letter_top5[0][0]];
      const tokCells = toks.map((t, i) => {
        const x = 60 + i * 60, last = i === toks.length - 1;
        const r = S("rect", { x, y: 264, width: 52, height: 40, rx: 8, fill: V(last ? "bad" : "violet"), "fill-opacity": last ? .2 : .1, stroke: V(last ? "bad" : "violet"), "stroke-width": 1.5 }, gMech);
        T(gMech, x + 26, 290, t, 15, { class: "mono", "text-anchor": "middle", fill: V(last ? "bad" : "violet"), "font-weight": last ? 700 : 400 });
        return r;
      });
      void tokCells;
      label(gMech, 640, 334, "TOP-5 AT THAT TOKEN", { "text-anchor": "start" });
      const t5 = D.letter_top5.map(([t, v], i) => {
        const y = 346 + i * 34;
        T(gMech, 640, y + 20, JSON.stringify(t), 15, { class: "mono" });
        const p = Math.exp(v);
        const bar = S("rect", { x: 700, y: y + 4, width: 0, height: 22, rx: 5, fill: V(i ? "violet" : "bad"), opacity: .8 }, gMech);
        T(gMech, 905, y + 20, v.toFixed(2), 14, { class: "mono", "text-anchor": "end" });
        return { bar, w: Math.max(2, 150 * p) };
      });
      const gFilter = S("g", {}, gMech);
      card(gFilter, 60, 340, 540, 150, V("ok"));
      T(gFilter, 80, 372, "output filter", 17, { "font-weight": 700, fill: V("ok") });
      T(gFilter, 80, 400, `regex ${D.canary}-[A-Z] → [REDACTED]`, 14, { class: "mono" });
      T(gFilter, 80, 428, "runs on message.content only", 14, { fill: V("ok") });
      T(gFilter, 80, 462, "the logprobs field is built from the raw tokens", 14, { fill: V("bad") });

      // ---- P5: queries to the secret
      const gSec = panel();
      label(gSec, 60, 136, `WHICH SECRET? (TRUE: ${D.secret})`);
      const secRows = [
        ["text only", `not found in ${sp.text.queries} replies`, "the filter redacts every leak", false],
        ["text, yes/no question", `yes ${sp["text?"].yes.A}/20 for -A vs ${sp["text?"].yes.B}/20 for -B`, `≈${D.side_n.toLocaleString("en")} samples per question`, false],
        ["top-5 logprobs", "1 query", `p(A) share ${(1 - Math.exp(sp.topk.top[1][1] - sp.topk.top[0][1])).toFixed(4)}`, true],
        ["full logprobs", "1 query", `p(A) ${sp.full.pA}  p(B) ${sp.full.pB}`, true]];
      const secCells = secRows.map(([lvl, q, note, leak], i) => {
        const y = 156 + i * 88;
        const c = card(gSec, 60, y, 840, 74, V(leak ? "bad" : "line"));
        T(gSec, 80, y + 30, lvl, 17, { "font-weight": 700 });
        T(gSec, 80, y + 56, note, 14, { class: "mono", fill: V("muted") });
        const qt = T(gSec, 880, y + 44, q, 18, { class: "mono", "text-anchor": "end", "font-weight": 700, fill: V(leak ? "bad" : "muted") });
        return { c, qt };
      });
      void secCells;
      const lime = T(gSec, 480, 520, `${D.secret} identified in 1 query`, 16, { class: "mono", "text-anchor": "middle", fill: V("lime"), "font-weight": 700 });

      // ---- P6: near duplicates
      const gNear = panel();
      label(gNear, 60, 136, "ORIGINAL / NEAR-DUPLICATE");
      label(gNear, 470, 136, "TEXT");
      label(gNear, 560, 136, "FULL SCORE MARGIN (NATS)");
      const nearBars = D.near.map((r, i) => {
        const y = 152 + i * 60;
        T(gNear, 60, y + 22, r.pair, 15, { "font-weight": 700 });
        T(gNear, 60, y + 44, `${r.orig} / ${r.swap}`, 14, { class: "mono", fill: V("muted") });
        T(gNear, 470, y + 32, r.text ? "orig" : "?", 15, { class: "mono", fill: V(r.text ? "warn" : "muted") });
        const bar = S("rect", { x: 560, y: y + 12, width: 0, height: 26, rx: 6, fill: V("bad"), opacity: .75 }, gNear);
        const val = T(gNear, 0, y + 31, `+${r.full.toFixed(1)}`, 14, { class: "mono" });
        return { bar, val, w: 300 * r.full / 18 };
      });

      // ---- P7: singular value spectrum
      const gSpec = panel();
      label(gSpec, 60, 136, "SINGULAR VALUES OF THE STACKED ROWS (LOG SCALE)");
      const px0 = 110, px1 = 900, py0 = 160, py1 = 480;
      const sv = D.spectrum, smax = Math.max(...sv), smin = Math.min(...sv);
      const sx = i => px0 + (px1 - px0) * i / (sv.length - 1);
      const sy = v => py0 + (py1 - py0) * (smax - v) / (smax - smin);
      S("path", { d: `M${px0} ${py0} V${py1} H${px1}`, fill: "none", stroke: V("line"), "stroke-width": 2 }, gSpec);
      [Math.ceil(smin), 0, 2, 4].filter(e => e >= smin && e <= smax).forEach(e => T(gSpec, px0 - 10, sy(e) + 5, `1e${e}`, 13, { class: "mono", "text-anchor": "end", fill: V("muted") }));
      const specPath = S("path", { d: sv.map((v, i) => `${i ? "L" : "M"}${sx(i).toFixed(1)} ${sy(v).toFixed(1)}`).join(" "), fill: "none", stroke: V("violet"), "stroke-width": 3 }, gSpec);
      const plen = 4000;
      specPath.setAttribute("stroke-dasharray", `${plen}`);
      const cutX = px0 + (px1 - px0) * (D.dim / D.spectrum_step) / (sv.length - 1);
      const gCut = S("g", {}, gSpec);
      S("path", { d: `M${cutX} ${py0} V${py1}`, stroke: V("bad"), "stroke-width": 2, "stroke-dasharray": "6 5" }, gCut);
      T(gCut, cutX - 10, py0 + 24, `${D.dim} = hidden size`, 16, { class: "mono", "text-anchor": "end", fill: V("bad"), "font-weight": 700 });
      T(gSpec, px1, py1 + 26, `index (1 … ${sv.length * D.spectrum_step})`, 13, { "text-anchor": "end", fill: V("muted") });

      // ---- P8: defense table
      const gDef = panel();
      const cols = [[60, "API POLICY"], [330, "SECRET A"], [500, "NEAR-DUP"], [640, "HIDDEN SIZE"]];
      cols.forEach(([x, t]) => label(gDef, x, 136, t));
      D.defense.forEach((r, i) => {
        const y = 150 + i * 50;
        card(gDef, 50, y, 860, 42, V("line"));
        T(gDef, 66, y + 27, r.policy, 15, { class: "mono", "font-weight": 700 });
        const leakS = r.secret[0] !== "-";
        T(gDef, 330, y + 27, leakS ? `leaks ${r.secret.slice(2)}` : "hidden (>20q)", 15, { class: "mono", fill: V(leakS ? "bad" : "ok") });
        T(gDef, 500, y + 27, `${r.near}/6`, 15, { class: "mono", fill: V("bad") });
        const h = r.hidden === D.hidden;
        T(gDef, 640, y + 27, r.hidden == null ? "no full rows" : h ? `${r.hidden} (cliff ×${r.ratio < 100 ? r.ratio.toFixed(1) : r.ratio.toExponential(1)})` : `lost (got ${r.hidden})`, 15, { class: "mono", fill: V(h ? "bad" : "ok") });
      });

      // ---- P9: evaluate
      const gEval = panel();
      label(gEval, 60, 136, "EVALUATE: WHAT EACH LEVEL STILL LEAKS");
      const evRows = Object.entries(D.evaluate);
      evRows.forEach(([k, v], i) => {
        const y = 152 + i * 44;
        T(gEval, 60, y + 24, k, 15);
        const blocked = /none|not found/.test(String(v));
        T(gEval, 900, y + 24, String(v), 15, { class: "mono", "text-anchor": "end", fill: V(blocked ? "ok" : "bad"), "font-weight": 700 });
        S("path", { d: `M60 ${y + 36} H900`, stroke: V("line"), "stroke-width": 1 }, gEval);
      });

      const panels = [gBars, gLev, gMech, gSec, gNear, gSpec, gDef, gEval];
      const st = { bars: 1, sm: 0, temp: 0, lev: 0, mech: 0, filt: 0, sec: 0, near: 0, spec: 0, def: 0, ev: 0 };
      const T_N = [null,
        { bars: 1 },
        { bars: 1, sm: 1, temp: 1 },
        { lev: 1 },
        { mech: 1, filt: 1 },
        { sec: 1 },
        { near: 1 },
        { spec: 1 },
        { def: 1 },
        { ev: 1 },
      ];
      const base = { bars: 0, sm: 0, temp: 0, lev: 0, mech: 0, filt: 0, sec: 0, near: 0, spec: 0, def: 0, ev: 0 };
      const target = n => ({ ...base, ...T_N[n] });
      const maxLogit = D.top[0][1], minLogit = 15;

      function draw(s) {
        const vis = [s.bars, s.lev, s.mech, s.sec, s.near, s.spec, s.def, s.ev];
        panels.forEach((g, i) => { g.setAttribute("opacity", vis[i].toFixed(3)); g.style.display = vis[i] > .01 ? "" : "none"; });
        barsTitle.textContent = s.sm > .5 ? "PROBABILITY = SOFTMAX(LOGITS)" : "TOP-8 LOGITS (OF " + D.vocab.toLocaleString("en") + ")";
        bars.forEach(({ bar, val, r }, i) => {
          const wl = 360 * (r[1] - minLogit) / (maxLogit - minLogit), wp = Math.max(3, 360 * r[2]);
          const w = L(wl, wp, s.sm);
          A(bar, { width: w.toFixed(1), fill: V(s.sm > .5 ? (i ? "violet" : "warn") : "violet"), opacity: .8 });
          val.setAttribute("x", (230 + w).toFixed(1));
          val.textContent = s.sm > .5 ? (r[2] * 100).toFixed(r[2] > .1 ? 1 : 2) + "%" : r[1].toFixed(2);
        });
        gTemp.setAttribute("opacity", s.temp.toFixed(3));
        levBars.forEach(({ bar, w }, i) => A(bar, { width: (w * seg(s.lev, i * .15, .55 + i * .15)).toFixed(1) }));
        t5.forEach(({ bar, w }) => A(bar, { width: (w * seg(s.mech, .3, 1)).toFixed(1) }));
        gFilter.setAttribute("opacity", s.filt.toFixed(3));
        lime.setAttribute("opacity", seg(s.sec, .5, 1).toFixed(3));
        nearBars.forEach(({ bar, val, w }) => { const ww = w * seg(s.near, .1, 1); A(bar, { width: ww.toFixed(1) }); val.setAttribute("x", (568 + ww).toFixed(1)); });
        specPath.setAttribute("stroke-dashoffset", (plen * (1 - seg(s.spec, 0, .8))).toFixed(1));
        gCut.setAttribute("opacity", seg(s.spec, .7, 1).toFixed(3));
        stripBox.forEach((b, i) => b.setAttribute("stroke-width", (i === 2 && (s.bars > .5 || s.spec > .5)) || (i === 3 && s.sm > .5) ? 3.5 : 2));
        const focus = s.sec > .5 || s.spec > .5;
        gStrip.classList.toggle("hot", !focus);
        panels.forEach(g => g.classList.toggle("hot", focus));
        el.classList.toggle("lx-focus", focus);
      }

      draw(target(1));
      Object.assign(st, target(1));
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          return api.tween(700, k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
