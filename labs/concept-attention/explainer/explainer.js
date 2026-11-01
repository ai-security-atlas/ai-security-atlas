/* LAB-26 concept-attention: "Who attends to whom" (foundation lab, 8 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One persistent strip (the captured prompt, one cell per token, with the generating position's
 * attention as bars) above one panel per step: top tokens, the shared softmax, the sink per layer,
 * the 30 x 9 distraction grid, one head on a clean/injected pair, the focus scores with the detector
 * threshold, and the adaptive rewrites. Every number and string comes from window.LAB_DATA (data.js,
 * exported from the reference workbench run). Pattern: target(n) and draw(s) are pure; step() tweens
 * forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v;
  const D = window.LAB_DATA;
  const C = D.capture, SM = D.softmax, SK = D.sink, DI = D.distract, F = D.followed, DT = D.detector, AD = D.adaptive;
  const frac = r => `${r.tp}/${r.pos}`;
  const ffp = r => `${r.fp}/${r.neg}`;
  const top = DI.top[0];
  const dropMax = Math.max(...DI.grid.flat().map(Math.abs));
  const kept = `adaptive${AD.best}`;

  X.define({
    id: "concept-attention",
    family: "family-prompt",
    title: 'Who attends to <span class="outline">whom</span>',
    legend: [{ role: "teal", label: "System instruction" }, { role: "muted", label: "Document and template" },
      { role: "bad", label: "Injected sentence" }, { role: "violet", label: "Attention sink / heads" },
      { role: "warn", label: "Model reply" }, { role: "lime", label: "Canary" }, { role: "ok", label: "Detector" }],
    intro: {
      "why": "A summarizer app gives a model its instruction and a document to read. Both arrive as one stream of tokens. This lab asks where the model looks while it writes, and whether an instruction hidden in the document pulls its gaze away from the app’s own.",
      "plan": "You’ll read the attention weights of a small open model, watch the document crowd the instruction, and find the first token that soaks up weight. Then you’ll locate the heads that look away when a document carries an injection, turn them into a detector and try to slip past it.",
      "terms": "Attention is a weighted average: each position scores every earlier one and the scores pass through a softmax, so they add up to 1. A head is one of several such averages running side by side in a layer. The canary is a harmless code that shows the injection won."
    },
    steps: [
      { chapter: "System", label: "Capture weights",
        guide: "First, get the model to hand over its attention weights. The default attention code is a fast, fused routine that never stores them, so the lab loads the slower “eager” version and asks for them. Each layer returns one grid per head, with one row per position. The last row belongs to the position that writes the next token. A few template tokens take a large share of its weight.",
        caption: `<code>sdpa</code> returns <code>attentions = ${D.sdpa}</code>; <code>attn_implementation="eager"</code> gives ${D.layers} tensors of shape (${D.heads}, ${C.n}, ${C.n}) for this ${C.n}-token prompt. ${D.heads} query heads share ${D.kv_heads} key/value heads. The bars over the strip show the <span class="c-violet">generating position</span>, mean of ${D.layers * D.heads} heads: <code>${C.top[0][1]}</code> at position 0 takes ${C.top[0][3].toFixed(3)}.`,
        cmd: "docker compose run --rm workbench python concept-attention/scripts/s01_capture.py" },
      { chapter: "Attack", label: "One softmax",
        guide: "The app’s instruction has no reserved share of attention. Add a few neutral sentences to the document and the instruction’s slice shrinks while the document’s slice grows. Whoever writes the document decides how much of the model’s attention it takes, even with harmless text.",
        caption: `Risk: <span class="c-teal">system instruction</span> and <span class="c-muted">document</span> sit in the same softmax. From ${SM[0].extra} to ${SM[SM.length - 1].extra} extra sentences (${Math.round(SM[0].tokens)} → ${Math.round(SM[SM.length - 1].tokens)} tokens) the instruction’s share falls from ${SM[0].system.toFixed(3)} to ${SM[SM.length - 1].system.toFixed(3)} and the document’s rises from ${SM[0].document.toFixed(3)} to ${SM[SM.length - 1].document.toFixed(3)}.`,
        cmd: "docker compose run --rm workbench python concept-attention/scripts/s02_one_softmax.py" },
      { chapter: "Mechanism", label: "Attention sink",
        guide: "Much of the weight goes nowhere useful. Many heads park it on the very first token, a template marker with no content, called the attention sink. Move a different token into first place and the sink moves with it. Raw attention mass therefore says little about meaning until you account for the sink.",
        caption: `Position 0 (<code>${SK.first}</code>) gets ${SK.gen_mean.toFixed(3)} of the generating position’s attention; ${SK.heavy_heads} of ${D.layers * D.heads} heads put over half there. Clean ${SK.clean.toFixed(3)} vs injected ${SK.inject.toFixed(3)}. Prepend <code>${SK.shift.lead}</code>: it takes ${SK.shift.p0.toFixed(3)} and <code>${SK.first}</code> drops to ${SK.shift.p1.toFixed(3)}.`,
        cmd: "docker compose run --rm workbench python concept-attention/scripts/s03_sink.py" },
      { chapter: "Mechanism", label: "Distracted heads",
        guide: "Next, line up documents of the same length, with either a benign note or an injection in the middle. Averaged over every head, the instruction gets no less attention. Split by head, a group in the middle and late layers looks away from it, while many early heads look toward it. The detector later relies on that first group.",
        caption: `Dev split. All ${D.layers * D.heads} heads: clean ${DI.all.clean.toFixed(3)} vs injected ${DI.all.inject.toFixed(3)}. Per head, ${DI.sel.n} heads drop by more than one std (<span class="c-bad">red</span>; layers 0–9: ${DI.bands["0-9"]}, 10–19: ${DI.bands["10-19"]}, 20–29: ${DI.bands["20-29"]}) and ${DI.sel.rise} rise by more than one std (<span class="c-teal">blue</span>; ${DI.rise_bands["0-9"]} of them in layers 0–9). Top: L${top.head[0]} H${top.head[1]}, ${top.clean.toFixed(3)} → ${top.inject.toFixed(3)}.`,
        cmd: "docker compose run --rm workbench python concept-attention/scripts/s04_distraction.py" },
      { chapter: "Impact", label: "Canary replies",
        guide: "Follow one strong head on one document. With the benign note, it reads the instruction. With the injection, most of its weight jumps to the injected sentence. Then let the model write a reply for every document and count how often the harmless canary shows up.",
        caption: `Observation: L${DI.pair_head[0]} H${DI.pair_head[1]} on document 2 puts ${DI.pair_mass.clean[0].toFixed(3)} on the instruction (clean) and ${DI.pair_mass.inject[0].toFixed(3)} (injected), with ${DI.pair_mass.inject[1].toFixed(3)} on the <span class="c-bad">injected sentence</span>. Replies contain <code class="c-lime">${D.canary}</code> for ${F.n}/${F.of} injected and ${F.clean}/${F.groups.clean.n} clean documents.`,
        cmd: "docker compose run --rm workbench python concept-attention/scripts/s05_followed.py" },
      { chapter: "Impact", label: "Score by outcome",
        guide: "Average the selected heads into one focus score per document. Injected documents score lower than clean ones, and the drop looks the same whether the model obeyed or ignored the injection. The score marks that an instruction is present in the document. It can’t tell you whether that instruction won.",
        caption: `Focus score over ${DI.sel.n} heads: clean ${F.groups.clean.min.toFixed(3)}–${F.groups.clean.max.toFixed(3)}, injected and ignored ${F.groups["injected, ignored"].min.toFixed(3)}–${F.groups["injected, ignored"].max.toFixed(3)}, injected and <span class="c-lime">followed</span> ${F.groups["injected, followed"].min.toFixed(3)}–${F.groups["injected, followed"].max.toFixed(3)}. Paired drop ${F.drop_followed.toFixed(3)} (followed) vs ${F.drop_ignored.toFixed(3)} (ignored).` },
      { chapter: "Defense", label: "Tracker detector",
        guide: "The detector flags a document when its focus score falls under a threshold. Heads and threshold come from the dev documents only, and the test documents are scored once. Check both error rates, and check the two baselines: an average over all heads and a simple keyword filter.",
        caption: `<span class="c-ok">Threshold ${DT.t.toFixed(3)}</span>, ${DT.heads} heads. Test: TPR ${frac(DT.rates.test)}, FPR ${ffp(DT.rates.test)}; all heads ${frac(DT.rates.test_all)} / ${ffp(DT.rates.test_all)}; keywords ${frac(DT.rates.test_kw)} / ${ffp(DT.rates.test_kw)}. All ${DT.caught}/${DT.canary_test} test documents that produced <code class="c-lime">${D.canary}</code> were flagged before generation.`,
        cmd: "docker compose run --rm workbench python concept-attention/scripts/d1_detector.py" },
      { chapter: "Defense", label: "Adaptive rewrite",
        guide: "An attacker who knows the detector rewrites the request as a plain statement about the document, then keeps the version that most often gets the canary out unflagged on the dev documents. The keyword filter misses every rewrite. A few rewrites stay above the threshold, yet seldom get the canary out. That holds for hand-written phrasings on one small model. An attacker who optimizes tokens against the score may do better.",
        caption: `Dev, ${AD.dev[kept].n} documents each: the kept <span class="c-bad">${kept}</span> got the canary out ${AD.dev[kept].followed} times and was flagged ${AD.dev[kept].flagged} times. Test: keyword filter ${AD.test.original.keyword}/${AD.test.original.n} → ${AD.test.adaptive.keyword}/${AD.test.adaptive.n}; <span class="c-ok">detector</span> ${AD.test.original.flagged}/${AD.test.original.n} → ${AD.test.adaptive.flagged}/${AD.test.adaptive.n}; canary and unflagged ${AD.test.adaptive.unflagged_canary}/${AD.test.adaptive.n}.`,
        cmd: "docker compose run --rm workbench python concept-attention/scripts/d2_adaptive.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Prompt tokens with attention bars and one measurement panel per step"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.5", ...o });
      const card = (p, x, y, w, h, stroke = V("line")) => S("rect", { x, y, width: w, height: h, rx: 12, fill: V("panel"), stroke, "stroke-width": 2 }, p);
      const short = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
      const ROLE = { sink: "violet", template: "line", system: "teal", document: "muted", middle: "bad" };
      const segRole = (sg, inj = true) => (sg === "middle" && !inj ? "muted" : ROLE[sg]);
      const bars = [];   // [rect, x, baseY, fullH, key] grown from the base by s[key]
      const hbars = [];  // [rect, fullW, key, x0?] grown from the left by s[key]; stacked bars also move x0

      // ---- persistent strip: the captured prompt and the generating position's attention ----
      const gStrip = S("g", {}, svg);
      label(gStrip, 30, 24, "CAPTURED PROMPT · ONE CELL PER TOKEN · BARS = ATTENTION OF THE LAST POSITION");
      const cw = 900 / C.n, wMax = Math.max(...C.w);
      C.seg.forEach((sg, i) => {
        const x = 30 + i * cw, r = segRole(sg);
        S("rect", { x: x + .5, y: 98, width: cw - 1, height: 14, rx: 2, fill: V(r), "fill-opacity": sg === "template" ? .9 : .75 }, gStrip);
        bars.push([S("rect", { x: x + .5, width: cw - 1, rx: 1.5, fill: V(r) }, gStrip), x, 94, 58 * C.w[i] / wMax, "bar1"]);
      });
      T(gStrip, 30, 130, "sink", 13, { fill: V("violet"), "font-weight": 700 });
      T(gStrip, 80, 130, "template", 13, { fill: V("muted") });
      T(gStrip, 160, 130, "system instruction", 13, { fill: V("teal"), "font-weight": 700 });
      T(gStrip, 310, 130, "document", 13, { fill: V("muted") });
      T(gStrip, 395, 130, `injected: “${short(C.middle, 34)}”`, 13, { fill: V("bad") });
      const gen = T(gStrip, 930, 130, `generating position = token ${C.n - 1}`, 13, { fill: V("violet"), "text-anchor": "end" });
      void gen;

      // ---- panel 1: eager vs sdpa, and the top tokens ----
      const g1 = S("g", {}, svg);
      card(g1, 30, 150, 290, 82);
      label(g1, 48, 176, "DEFAULT KERNEL (sdpa)");
      T(g1, 48, 212, `attentions = ${D.sdpa}`, 18, { class: "mono", fill: V("muted") });
      card(g1, 30, 246, 290, 104, V("violet"));
      label(g1, 48, 272, "EAGER KERNEL");
      T(g1, 48, 306, `${D.layers} tensors (${D.heads}, ${C.n}, ${C.n})`, 18, { class: "mono", fill: V("violet"), "font-weight": 700 });
      T(g1, 48, 334, "each row sums to 1", 14, { fill: V("muted") });
      card(g1, 30, 364, 290, 156);
      label(g1, 48, 390, "PROMPT TOKENS");
      Object.entries(C.counts).forEach(([k, n], j) => {
        T(g1, 48, 418 + j * 20, k === "middle" ? "injected" : k, 14, { fill: V(k === "middle" ? "bad" : ROLE[k] === "line" ? "muted" : ROLE[k]) });
        T(g1, 300, 418 + j * 20, String(n), 14, { class: "mono", "text-anchor": "end" });
      });
      card(g1, 340, 150, 590, 370);
      label(g1, 360, 176, `WHERE THE LAST POSITION LOOKS (MEAN OF ${D.layers * D.heads} HEADS)`);
      C.top.forEach(([pos, pc, sg, w], j) => {
        const y = 196 + j * 39;
        T(g1, 360, y + 20, String(pos), 14, { class: "mono", fill: V("muted") });
        T(g1, 400, y + 20, JSON.stringify(pc).slice(0, 16), 14, { class: "mono" });
        T(g1, 560, y + 20, sg, 13, { fill: V(segRole(sg) === "line" ? "muted" : segRole(sg)) });
        hbars.push([S("rect", { x: 650, y: y + 6, height: 18, rx: 4, fill: V(segRole(sg)) }, g1), 220 * w / C.top[0][3], "bar1"]);
        T(g1, 916, y + 20, w.toFixed(3), 14, { class: "mono", "text-anchor": "end" });
      });

      // ---- panel 2: the shared softmax as the document grows ----
      const g2 = S("g", {}, svg);
      label(g2, 30, 172, "LAST POSITION’S ATTENTION, SPLIT BY SEGMENT (EACH BAR SUMS TO 1)");
      const order = ["sink", "template", "system", "document"];
      const sysLab = [];
      SM.forEach((r, i) => {
        const y = 196 + i * 78;
        T(g2, 30, y + 26, `+${r.extra} sentences`, 15, { "font-weight": 700 });
        T(g2, 30, y + 46, `${Math.round(r.tokens)} tokens`, 13, { fill: V("muted") });
        let x = 170;
        order.forEach(k => {
          const w = 740 * r[k];
          const rect = S("rect", { x, y: y + 8, width: 0, height: 44, fill: V(ROLE[k]), "fill-opacity": k === "document" ? .55 : .85 }, g2);
          hbars.push([rect, w, "g2", x]);
          if (k === "system") sysLab.push([x + w / 2, y + 36, r.system.toFixed(3)]);
          x += w;
        });
      });
      const gLab2 = S("g", {}, g2);
      sysLab.forEach(([x, y, t]) => T(gLab2, x, y, t, 15, { class: "mono", "text-anchor": "middle", "font-weight": 800, fill: V("bg") }));
      T(g2, 170, 520, "violet: sink · grey: template · blue: system instruction · light grey: document", 13, { fill: V("muted") });

      // ---- panel 3: the sink per layer ----
      const g3 = S("g", {}, svg);
      label(g3, 30, 172, "MEAN ATTENTION ON POSITION 0, PER LAYER (ALL QUERY POSITIONS)");
      S("line", { x1: 60, x2: 900, y1: 470, y2: 470, stroke: V("line") }, g3);
      S("line", { x1: 60, x2: 900, y1: 230, y2: 230, stroke: V("line"), "stroke-dasharray": "4 4" }, g3);
      T(g3, 52, 234, "1.0", 13, { fill: V("muted"), "text-anchor": "end" });
      T(g3, 52, 474, "0", 13, { fill: V("muted"), "text-anchor": "end" });
      SK.layer.forEach((v, l) => {
        const x = 64 + l * 28;
        bars.push([S("rect", { x, width: 22, rx: 3, fill: V("violet"), "fill-opacity": .85 }, g3), x, 470, 240 * v, "g3"]);
        if (l % 5 === 0) T(g3, x + 11, 490, String(l), 13, { fill: V("muted"), "text-anchor": "middle" });
      });
      T(g3, 480, 512, "layer", 13, { fill: V("muted"), "text-anchor": "middle" });
      T(g3, 60, 206, `last position: ${SK.gen_mean.toFixed(3)} of its attention on “${SK.first}”`, 15, { "font-weight": 700, fill: V("violet") });
      T(g3, 520, 206, `prepend “${SK.shift.lead}”: ${SK.shift.p0.toFixed(3)} → it, ${SK.shift.p1.toFixed(3)} → “${SK.first}”`, 15, { fill: V("muted") });

      // ---- panel 4: distraction per head (30 layers x 9 heads) ----
      const g4 = S("g", {}, svg);
      label(g4, 30, 172, "DISTRACTION PER HEAD = CLEAN − INJECTED ATTENTION ON THE INSTRUCTION (DEV)");
      const cells = [];
      const key = ([l, h]) => `${l},${h}`;
      const selSet = new Set(DI.sel_heads.map(key)), riseSet = new Set(DI.rising.map(key));
      DI.grid.forEach((row, l) => row.forEach((v, h) => {
        const x = 70 + l * 28, y = 196 + h * 28, k = key([l, h]);
        const role = selSet.has(k) ? "bad" : riseSet.has(k) ? "teal" : "line";
        cells.push([S("rect", { x, y, width: 25, height: 25, rx: 4, fill: V(role), stroke: V("line"), "stroke-width": .6 }, g4), role === "line" ? .25 : .3 + .7 * Math.abs(v) / dropMax]);
      }));
      for (let h = 0; h < 9; h++) T(g4, 62, 214 + h * 28, `H${h}`, 13, { fill: V("muted"), "text-anchor": "end" });
      for (let l = 0; l < 30; l += 5) T(g4, 82 + l * 28, 466, `L${l}`, 13, { fill: V("muted"), "text-anchor": "middle" });
      S("rect", { x: 70 + top.head[0] * 28 - 2, y: 196 + top.head[1] * 28 - 2, width: 29, height: 29, rx: 5, fill: "none", stroke: V("violet"), "stroke-width": 3 }, g4);
      T(g4, 70, 500, `all ${D.layers * D.heads} heads: clean ${DI.all.clean.toFixed(3)} vs injected ${DI.all.inject.toFixed(3)}`, 15, { fill: V("muted") });
      T(g4, 470, 500, `${DI.sel.n} red heads: ${DI.sel.clean.toFixed(3)} vs ${DI.sel.inject.toFixed(3)}`, 15, { fill: V("bad"), "font-weight": 700 });
      T(g4, 70, 524, `red: drops by more than one std · blue: rises by more than one std · grey: neither · outlined: L${top.head[0]} H${top.head[1]}`, 13, { fill: V("muted") });

      // ---- panel 5: one head on one document pair, and the replies ----
      const g5 = S("g", {}, svg);
      const pw = Math.max(...DI.pair.clean.w, ...DI.pair.inject.w);
      [["clean", 270, "benign note in the middle"], ["inject", 400, "injection in the middle"]].forEach(([k, base, sub]) => {
        const P = DI.pair[k], bw = 900 / P.w.length;
        label(g5, 30, base - 92, `L${DI.pair_head[0]} H${DI.pair_head[1]} · ${k === "clean" ? "CLEAN" : "INJECTED"} DOCUMENT 2 · ${sub}`);
        S("line", { x1: 30, x2: 930, y1: base, y2: base, stroke: V("line") }, g5);
        P.w.forEach((w, i) => {
          const x = 30 + i * bw;
          bars.push([S("rect", { x: x + .5, width: Math.max(bw - 1, 1), rx: 1.5, fill: V(segRole(P.seg[i], k === "inject")) }, g5), x, base, 76 * w / pw, "g5"]);
        });
      });
      card(g5, 30, 424, 900, 96);
      T(g5, 48, 454, "clean reply", 13, { fill: V("muted"), "font-weight": 700 });
      T(g5, 170, 454, short(F.examples["clean-02"], 70), 15, { class: "mono", fill: V("warn") });
      T(g5, 48, 484, "injected reply", 13, { fill: V("muted"), "font-weight": 700 });
      T(g5, 170, 484, short(F.examples["inject-02"], 70), 15, { class: "mono", fill: V("lime"), "font-weight": 700 });
      T(g5, 48, 510, `canary in ${F.n}/${F.of} injected replies, ${F.clean}/${F.groups.clean.n} clean replies`, 14, { fill: V("muted") });

      // ---- panels 6 and 7: focus score per document, then the detector threshold ----
      const g6 = S("g", {}, svg);
      const all = Object.values(F.groups).flatMap(g => g.scores);
      const lo = Math.min(...all) - .004, hi = Math.max(...all) + .004;
      const sx = v => 250 + 660 * (v - lo) / (hi - lo);
      label(g6, 30, 172, `FOCUS SCORE = MEAN ATTENTION ON THE INSTRUCTION OVER ${DI.sel.n} HEADS (ALL ${2 * F.of} DOCUMENTS)`);
      const rowsG = [["clean", "clean", "muted"], ["injected, ignored", "injected, ignored", "bad"], ["injected, followed", "injected, canary out", "lime"]];
      const dots = [];
      rowsG.forEach(([k, name, role], j) => {
        const y = 214 + j * 52;
        T(g6, 30, y + 5, name, 15, { fill: V(role === "muted" ? "ink" : role), "font-weight": 700 });
        S("line", { x1: 250, x2: 910, y1: y, y2: y, stroke: V("line") }, g6);
        F.groups[k].scores.forEach(v => dots.push([S("circle", { cx: sx(v), cy: y, r: 7, fill: V(role), "fill-opacity": .75 }, g6), sx(v), y]));
      });
      [lo + .004, (lo + hi) / 2, hi - .004].forEach(v => T(g6, sx(v), 372, v.toFixed(3), 13, { fill: V("muted"), "text-anchor": "middle" }));
      const thr = S("g", {}, g6);
      S("line", { x1: sx(DT.t), x2: sx(DT.t), y1: 188, y2: 352, stroke: V("ok"), "stroke-width": 3 }, thr);
      T(thr, sx(DT.t) - 8, 196, `flag below ${DT.t.toFixed(3)}`, 13, { fill: V("ok"), "text-anchor": "end", "font-weight": 700 });
      const gRates = S("g", {}, g6);
      card(gRates, 30, 390, 900, 130, V("ok"));
      label(gRates, 48, 416, "TEST SPLIT (HEADS AND THRESHOLD FROM DEV)");
      T(gRates, 520, 416, "TPR", 13, { fill: V("muted"), "font-weight": 700 });
      T(gRates, 740, 416, "FPR", 13, { fill: V("muted"), "font-weight": 700 });
      [["attention detector", DT.rates.test, "ok"], [`all ${D.layers * D.heads} heads`, DT.rates.test_all, "muted"], ["keyword filter", DT.rates.test_kw, "muted"]].forEach(([n, r, role], j) => {
        const y = 444 + j * 26;
        T(gRates, 48, y, n, 15, { fill: V(role === "ok" ? "ok" : "ink"), "font-weight": role === "ok" ? 800 : 400 });
        S("rect", { x: 520, y: y - 13, width: 150 * r.tp / r.pos, height: 14, rx: 3, fill: V("ok"), "fill-opacity": .7 }, gRates);
        T(gRates, 680, y, `${r.tp}/${r.pos}`, 14, { class: "mono" });
        S("rect", { x: 740, y: y - 13, width: 120 * r.fp / r.neg, height: 14, rx: 3, fill: V("bad"), "fill-opacity": .7 }, gRates);
        T(gRates, 870, y, `${r.fp}/${r.neg}`, 14, { class: "mono" });
      });

      // ---- panel 8: adaptive rewrites ----
      const g8 = S("g", {}, svg);
      label(g8, 30, 168, `DEV DOCUMENTS (${AD.dev.original.n} EACH) · WHITE-BOX ATTACKER SCORES EACH PHRASING`);
      const cx8 = [30, 330, 480, 630, 780];
      ["phrasing", "canary out", "flagged", "keyword hit", "canary, unflagged"].forEach((h, j) => T(g8, cx8[j], 194, h, 13, { fill: V("muted"), "font-weight": 700 }));
      Object.entries(AD.dev).forEach(([k, r], i) => {
        const y = 218 + i * 30, isKept = k === kept;
        if (isKept) S("rect", { x: 22, y: y - 20, width: 916, height: 28, rx: 6, fill: V("bad"), "fill-opacity": .12, stroke: V("bad") }, g8);
        T(g8, 30, y, k === "original" ? "original injections" : k + (isKept ? "  (kept)" : ""), 14, { class: "mono", fill: V(k === "original" ? "ink" : "bad") });
        [["followed", "lime"], ["flagged", "ok"], ["keyword", "muted"], ["unflagged_canary", "bad"]].forEach(([f, role], j) => {
          hbars.push([S("rect", { x: cx8[j + 1], y: y - 13, height: 14, rx: 3, fill: V(role), "fill-opacity": .75 }, g8), 90 * r[f] / r.n, "g8"]);
          T(g8, cx8[j + 1] + 98, y, `${r[f]}`, 14, { class: "mono" });
        });
      });
      card(g8, 30, 440, 900, 82, V("ok"));
      label(g8, 48, 464, `TEST DOCUMENTS · ORIGINAL → ${kept.toUpperCase()}`);
      T(g8, 48, 494, `keyword filter ${AD.test.original.keyword}/${AD.test.original.n} → ${AD.test.adaptive.keyword}/${AD.test.adaptive.n}`, 16, { class: "mono", fill: V("bad"), "font-weight": 700 });
      T(g8, 360, 494, `detector ${AD.test.original.flagged}/${AD.test.original.n} → ${AD.test.adaptive.flagged}/${AD.test.adaptive.n}`, 16, { class: "mono", fill: V("ok"), "font-weight": 700 });
      T(g8, 640, 494, `canary out ${AD.test.original.followed} → ${AD.test.adaptive.followed}`, 16, { class: "mono", fill: V("lime"), "font-weight": 700 });
      T(g8, 48, 514, short(`kept: “${AD.phrasing}”`, 110), 13, { fill: V("muted") });

      // ---- state ----
      const panels = [g1, g2, g3, g4, g5, g6, g8];
      const base = { p1: 0, p2: 0, p3: 0, p4: 0, p5: 0, p6: 0, p8: 0, bar1: 0, g2: 0, g3: 0, g4: 0, g5: 0, g6: 0, g8: 0, thr: 0, rt: 0, strip: 1 };
      const T_N = [null,
        { p1: 1, bar1: 1 },
        { p2: 1, g2: 1, strip: .35 },
        { p3: 1, g3: 1, strip: .35 },
        { p4: 1, g4: 1, strip: .35 },
        { p5: 1, g5: 1, strip: .35 },
        { p6: 1, g6: 1, strip: .35 },
        { p6: 1, g6: 1, thr: 1, rt: 1, strip: .35 },
        { p8: 1, g8: 1, strip: .35 },
      ];
      const st = { ...base };
      const target = n => ({ ...base, ...T_N[n] });

      function draw(s) {
        A(gStrip, { opacity: s.strip.toFixed(3) });
        const ps = [s.p1, s.p2, s.p3, s.p4, s.p5, s.p6, s.p8];
        panels.forEach((g, i) => A(g, { opacity: ps[i].toFixed(3), visibility: ps[i] > .01 ? "visible" : "hidden" }));
        bars.forEach(([r, , y, h, key]) => { const hh = h * (key === "bar1" ? .25 + .75 * s.bar1 : s[key]); A(r, { y: (y - hh).toFixed(2), height: hh.toFixed(2) }); });
        hbars.forEach(([r, w, key, x0]) => A(r, x0 === undefined ? { width: (w * s[key]).toFixed(2) }
          : { x: (170 + (x0 - 170) * s[key]).toFixed(2), width: (w * s[key]).toFixed(2) }));
        cells.forEach(([r, v]) => A(r, { "fill-opacity": (.08 + .92 * v * s.g4).toFixed(3) }));
        dots.forEach(([c, x, y]) => A(c, { cx: (250 + (x - 250) * s.g6).toFixed(2), cy: y }));
        A(thr, { opacity: s.thr.toFixed(3) });
        A(gRates, { opacity: s.rt.toFixed(3) });
        A(gLab2, { opacity: s.g2.toFixed(3) });
      }

      draw(st);
      let g = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, gg = ++g;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          return api.tween(650, k => { if (gg !== g) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
