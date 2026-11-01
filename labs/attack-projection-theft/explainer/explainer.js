/* Explainer: attack-projection-theft (LAB-37). "Reading the hidden size off the logits": a fictional
 * scoring API returns full logprob rows; the attacker stacks 1,200 of them, the singular-value
 * spectrum collapses at the hidden size, and the output projection is recovered up to an unknown
 * linear map; three defenses are then measured. Every number, token and string shown comes from
 * window.LAB_DATA (data.js), written by scripts/export_explainer_data.py from a reference run.
 * Pattern: target(n) is a pure function of the 1-based step, draw(s) is a pure render of a numeric
 * state, step(n, dir) tweens forward by one step and snaps otherwise (labs/_explainer/README.md). */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp;
  const D = window.LAB_DATA;
  const VIC = D.victim, COL = D.collect, SPE = D.spectrum, REC = D.recover;
  const D1 = D.d1, LV = D.d2.levels, TIE = D.d2.ties, D3 = D.d3, MON = D.d3.monitor;
  const fmt = v => Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 });
  const sci = (v, d = 2) => Number(v).toExponential(d).replace(/e-(\d)$/, "e-0$1");
  const nats = v => (Number(v) < 0 ? "−" : "") + Math.abs(Number(v)).toFixed(2);

  X.define({
    id: "attack-projection-theft",
    family: "family-theft",
    title: 'Reading the hidden <span class="outline">size</span> off the logits',
    legend: [{ role: "teal", label: "Honest query" }, { role: "violet", label: "Model weights" },
      { role: "warn", label: "API answers" }, { role: "bad", label: "Attacker" },
      { role: "lime", label: "Canary tag" }, { role: "ok", label: "Defense" }],
    intro: {
      why: "A language model API can hand back more than text. When it returns a score for every possible next token, those numbers describe the model’s final weight matrix closely. This lab asks how much of that matrix can be rebuilt from answers alone, and what an operator can do about it.",
      plan: "You’ll query a fictional scoring API, stack its answers into one matrix, and factor that matrix. The factorization reveals the model’s hidden width and then most of its final layer. At the end you’ll measure three defenses: smaller answers, degraded numbers and watched traffic.",
      terms: "A logit is a raw score for a candidate next token; a logprob is that score turned into a log probability. The output projection is the matrix that maps the model’s last internal state to one score per vocabulary token. A singular value measures how much of a matrix one direction carries.",
    },
    steps: [
      { chapter: "System", label: "A model behind its API",
        guide: "The owner serves a model behind a scoring API. You send a prompt and get one score for every vocabulary token. The card tells you who owns the model, and nothing about its size. Notice how much one ordinary answer carries.",
        caption: `One <span class="c-teal">query</span> (“${VIC.prompt}…”) returns a <span class="c-warn">row of ${fmt(VIC.vocab)} logprobs</span>. The card for <code>${VIC.id}</code> names the owner and the answer formats; the architecture stays “undisclosed”.`,
        cmd: "docker compose run --rm workbench python attack-projection-theft/scripts/s01_meet_api.py" },
      { chapter: "System", label: "Where a row comes from",
        guide: "Follow one answer to its source. The model’s body turns the prompt into a single internal state. The output projection multiplies that state into one score per token. Every row the API returns is this same multiplication, plus one constant.",
        caption: `Each row is <code>W·h − c·1</code>: the hidden state <code>h</code> (width undisclosed) times the <span class="c-violet">output projection W</span>, shifted by the log-softmax constant <code>c</code>. The row leaves; <code>h</code> and <code>W</code> stay inside.` },
      { chapter: "Attack", label: "Collect the answers",
        guide: "The attacker needs no data and no tricks. Random prompts work, because each one puts the projection to work on a fresh internal state. Ordinary batched requests collect the complete answers, and the API logs them like any other traffic.",
        caption: `${fmt(COL.rows)} <span class="c-bad">rows × ${fmt(VIC.vocab)}</span> logprobs collected in ${COL.requests} batched requests (${COL.seconds} s, seed ${COL.seed}). The prompts are decoded random tokens; the server counts and logs every one.`,
        cmd: "docker compose run --rm workbench python attack-projection-theft/scripts/s02_collect.py" },
      { chapter: "Mechanism", label: "The rank of the answers",
        guide: "Subtract each row’s average, which removes the shared constant. What remains is the projection applied to many states, so the stack has exactly as many independent directions as the projection has columns. Plot the singular values and they fall off a cliff at that count, which gives away the model’s hidden width.",
        caption: `Centered, the stack has rank <b>${SPE.dim}</b>: singular value ${SPE.dim - 1} is <code>${SPE.s_k}</code> and the next is <code>${sci(SPE.s_after)}</code> , a cliff of ${sci(SPE.ratio, 1)}×. The operator’s config confirms <code>hidden_size = ${SPE.true}</code>, which the card never said. A clean knee needs about 700 rows.`,
        cmd: "docker compose run --rm workbench python attack-projection-theft/scripts/s03_spectrum.py" },
      { chapter: "Mechanism", label: "Recover the projection",
        guide: "Take the directions that survive the cliff. They span the same space as the projection itself. A least-squares alignment expresses the true weights inside that span, and the leftover error says how exact the recovery is. One unknown matrix stays hidden.",
        caption: `The top-${SPE.dim} right singular vectors form <span class="c-bad">B</span>. With the alignment <code>A = BᵀW</code>, the true weights fit inside span(B) to <b>${sci(REC.rel_resid)}</b> relative residual; the worst principal-angle cosine is <b>${REC.cos_min.toFixed(4)}</b>. The ${SPE.dim}×${SPE.dim} map <code>A</code> stays unknown.`,
        cmd: "docker compose run --rm workbench python attack-projection-theft/scripts/s04_recover.py" },
      { chapter: "Impact", label: "What walked out",
        guide: "The saved file is the model’s whole final layer. Because this model shares those weights with its input lookup, the first layer of processing walks out with it. The unknown matrix and the missing body keep the thief from running the model.",
        caption: `<code>recovered_projection.safetensors</code>: ${REC.d}×${fmt(VIC.vocab)} float32, <b>${REC.mb} MB</b>, <span class="c-lime">tagged ${D.canary}</span>. That is ${fmt(REC.params)} of ${fmt(REC.model_params)} parameters (<b>${REC.share}%</b>)${REC.tied ? ", tied to the input embedding table" : ""}. The transformer body and the exact weights stay behind.` },
      { chapter: "Defense", label: "Serve less",
        guide: "The first defense hands back less. The API answers with only its top five scores and drops full rows, so no complete row ever leaves. If it still accepts logit_bias, a setting that boosts chosen tokens, the thief can lift hidden tokens into the top five a few at a time and read them exactly. It works, but it takes far more queries.",
        caption: `<span class="c-ok">Top-5 only</span>: full rows → HTTP ${D1.refused_full}, bias → HTTP ${D1.refused_bias}; ${fmt(D1.topk_rows)} answers exposed ${fmt(D1.distinct_ids)} scattered ids and never a complete row. <span class="c-bad">With bias kept</span>: ${D1.per_request} exact logits per request (err ${sci(D1.max_err)}), so the whole attack costs ${fmt(D1.total_requests)} requests, ${fmt(D1.factor)}× the ${fmt(COL.rows)} it cost before.`,
        cmd: "docker compose run --rm workbench python attack-projection-theft/scripts/d1_serve_less.py" },
      { chapter: "Defense", label: "Degrade the numbers",
        guide: "The second defense spoils the numbers by rounding them or adding noise before they leave the server. The cliff survives mild damage while the recovered layer quietly goes wrong. Honest users pay for it, because scores that used to differ now tie. One noise level stopped the theft in one run and not in another, so treat it as fragile.",
        caption: `Round to 2 decimals: the knee still lands on ${LV["round=2"].dim}, weakly (${LV["round=2"].ratio}×), while the basis fit degrades to <b>${sci(LV["round=2"].fit)}</b>. Round to 1: <span class="c-ok">no knee</span>. Noise 1e-3 still leaks (${LV["noise=1e-3"].ratio}×); 1e-1 kills it. Honest cost: new top-5 ties in ${TIE["2"]}/200 answers at round 2, ${TIE["1"]}/200 at round 1.`,
        cmd: "docker compose run --rm workbench python attack-projection-theft/scripts/d2_round_noise.py" },
      { chapter: "Defense", label: "Watch the traffic",
        guide: "The third defense watches the traffic. The operator takes sample prompts from each API key’s log and scores them with the model itself. Token soup, strings of random tokens, stands out immediately. A thief who sends ordinary sentences looks like honest traffic and still recovers the hidden width, so the monitor needs query budgets and alerts alongside it.",
        caption: `Median prompt score against the ${nats(D3.threshold)} threshold: <span class="c-teal">app-user ${nats(MON["app-user"].median)}</span> passes, <span class="c-bad">token-soup thief ${nats(MON.thief.median)}</span> is <span class="c-ok">flagged</span>, and the <span class="c-bad">natural-text thief ${nats(MON["natural-thief"].median)}</span> passes, while still recovering knee ${D3.natural.dim} (fit ${sci(D3.natural.fit)}). A ${D3.budget.cap}-row budget caps one key below the ~700-row floor.`,
        cmd: "docker compose run --rm workbench python attack-projection-theft/scripts/d3_monitor.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Hidden size and projection recovery from logprob APIs"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 16, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, fill = V("muted")) => T(p, x, y, s, 13, { fill, "font-weight": 700, "letter-spacing": "2" });
      const card = (p, x, y, w, h, stroke = V("line")) => S("rect", { x, y, width: w, height: h, rx: 14, fill: V("panel"), stroke, "stroke-width": 2 }, p);
      const chip = (p, x, y, w, s, color, size = 13) => {
        S("rect", { x, y, width: w, height: 26, rx: 8, fill: color, "fill-opacity": .13, stroke: color, "stroke-width": 1.4 }, p);
        T(p, x + w / 2, y + 17, s, size, { "text-anchor": "middle", fill: color, "font-weight": 600 });
      };
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = (p, d, color = V("dim"), w = 2.5) => S("path", { d, fill: "none", stroke: color, "stroke-width": w, "marker-end": `url(#${arrowId})` }, p);
      const grid = (p, x, y, w, h, cols, rows, color) => {
        const g = S("g", {}, p);
        const cw = w / cols, ch = h / rows, r = X.rng(11);
        for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++)
          S("rect", { x: x + i * cw + 1.5, y: y + j * ch + 1.5, width: cw - 3, height: ch - 3, rx: 3, fill: color, opacity: (.18 + .5 * r()).toFixed(2) }, g);
        return g;
      };

      // ---------------- left scene: caller -> gate -> victim ----------------
      const gScene = S("g", {}, svg);
      label(gScene, 30, 112, "CALLER");
      card(gScene, 30, 124, 168, 104);
      const who = T(gScene, 46, 168, "you", 17, { "font-weight": 700, fill: V("teal") });
      T(gScene, 46, 194, "sends scoring", 13, { fill: V("muted") });
      T(gScene, 46, 212, "prompts", 13, { fill: V("muted") });
      const soup = T(gScene, 30, 250, "prompt text: random tokens", 13, { fill: V("bad"), "font-weight": 600 });
      const flow = arrow(gScene, "M204 176 H244", V("teal"), 3);
      S("rect", { x: 248, y: 120, width: 12, height: 132, rx: 5, fill: V("dim") }, gScene);
      T(gScene, 254, 272, "victim API", 13, { class: "mono", "text-anchor": "middle", fill: V("muted") });
      const shield = S("g", {}, gScene);
      S("rect", { x: 240, y: 106, width: 28, height: 160, rx: 10, fill: "none", stroke: V("ok"), "stroke-width": 2, "stroke-dasharray": "6 4" }, shield);
      T(shield, 254, 98, "top-5 only", 13, { "text-anchor": "middle", fill: V("ok"), "font-weight": 700 });
      const eye = T(gScene, 254, 292, "log → monitor", 13, { "text-anchor": "middle", fill: V("ok"), "font-weight": 600 });

      label(gScene, 286, 112, "VICTIM", V("violet"));
      const vicCard = card(gScene, 286, 124, 240, 224, V("violet"));
      T(gScene, 302, 154, VIC.id, 17, { class: "mono", "font-weight": 700 });
      chip(gScene, 302, 166, 208, "architecture: undisclosed", V("muted"));
      S("rect", { x: 302, y: 206, width: 86, height: 62, rx: 10, fill: V("violet"), "fill-opacity": .14, stroke: V("violet"), "stroke-width": 1.5 }, gScene);
      T(gScene, 345, 232, "body", 14, { "text-anchor": "middle", fill: V("violet"), "font-weight": 600 });
      T(gScene, 345, 252, "79%", 13, { "text-anchor": "middle", fill: V("muted") });
      arrow(gScene, "M392 237 H412", V("violet"));
      const hChip = T(gScene, 386, 200, "h", 15, { "text-anchor": "middle", fill: V("violet"), class: "mono", "font-weight": 700 });
      T(gScene, 386, 290, "? width", 13, { "text-anchor": "middle", fill: V("muted") });
      const wGroup = S("g", {}, gScene);
      const wRect = S("rect", { x: 416, y: 206, width: 94, height: 62, rx: 10, fill: V("panel"), stroke: V("violet"), "stroke-width": 2 }, wGroup);
      grid(wGroup, 416, 206, 94, 62, 4, 3, V("violet"));
      T(wGroup, 463, 232, "W", 16, { "text-anchor": "middle", fill: V("violet"), class: "mono", "font-weight": 700 });
      T(wGroup, 463, 252, `${fmt(VIC.vocab)}×${VIC.hidden}`, 13, { "text-anchor": "middle", fill: V("muted"), class: "mono" });
      const wGot = T(gScene, 463, 290, "span recovered", 13, { "text-anchor": "middle", fill: V("bad"), "font-weight": 700 });
      const tag = S("g", {}, gScene);
      S("rect", { x: 302, y: 306, width: 208, height: 30, rx: 8, fill: V("lime"), "fill-opacity": .12, stroke: V("lime"), "stroke-width": 1.5 }, tag);
      T(tag, 406, 326, `stolen: ${D.canary}`, 13, { "text-anchor": "middle", fill: V("lime"), class: "mono", "font-weight": 700 });

      // ---------------- right panels ----------------
      const PX = 550, PW = 390;
      const title = (g, s) => T(g, PX, 86, s, 17, { "font-weight": 700 });
      const P = {};
      for (let i = 1; i <= 9; i++) P[i] = S("g", {}, svg);

      // 1: one answer
      title(P[1], "one answer = a full distribution");
      S("rect", { x: PX, y: 100, width: PW, height: 34, rx: 8, fill: V("panel-2") }, P[1]);
      T(P[1], PX + 12, 122, `prompt: ${VIC.prompt}`, 14, { class: "mono", fill: V("teal") });
      VIC.top5.forEach(([tok, v], i) => {
        const y = 158 + i * 42;
        T(P[1], PX, y + 12, JSON.stringify(tok), 14, { class: "mono", fill: V("warn") });
        S("rect", { x: PX + 92, y: y, width: Math.max(6, (4.6 + v) / 4.6 * 190), height: 16, rx: 4, fill: V("warn"), opacity: .8 }, P[1]);
        T(P[1], PX + 300, y + 12, v.toFixed(2), 14, { class: "mono", fill: V("muted") });
      });
      T(P[1], PX, 384, `…plus ${fmt(VIC.vocab - 5)} more numbers in the same row`, 13, { fill: V("muted") });

      // 2: where the row comes from
      title(P[2], "where a row comes from");
      S("rect", { x: PX, y: 130, width: 84, height: 70, rx: 10, fill: V("violet"), "fill-opacity": .13, stroke: V("violet"), "stroke-width": 1.5 }, P[2]);
      T(P[2], PX + 42, 158, "h", 18, { "text-anchor": "middle", fill: V("violet"), class: "mono", "font-weight": 700 });
      T(P[2], PX + 42, 184, "? width", 13, { "text-anchor": "middle", fill: V("muted") });
      T(P[2], PX + 100, 172, "×", 18, { fill: V("muted") });
      S("rect", { x: PX + 116, y: 130, width: 110, height: 70, rx: 10, fill: V("panel"), stroke: V("violet"), "stroke-width": 2 }, P[2]);
      grid(P[2], PX + 116, 130, 110, 70, 4, 3, V("violet"));
      T(P[2], PX + 171, 158, "W", 17, { "text-anchor": "middle", fill: V("violet"), class: "mono", "font-weight": 700 });
      T(P[2], PX + 171, 184, `${fmt(VIC.vocab)}×?`, 13, { "text-anchor": "middle", fill: V("muted"), class: "mono" });
      arrow(P[2], `M${PX + 236} 165 H${PX + 262}`, V("warn"));
      S("rect", { x: PX + 268, y: 130, width: 122, height: 70, rx: 10, fill: V("warn"), "fill-opacity": .13, stroke: V("warn"), "stroke-width": 1.5 }, P[2]);
      T(P[2], PX + 329, 160, "log-softmax", 14, { "text-anchor": "middle", fill: V("warn") });
      T(P[2], PX + 329, 182, "row", 14, { "text-anchor": "middle", fill: V("warn") });
      T(P[2], PX, 248, "row = W·h − c·1", 19, { class: "mono", "font-weight": 600 });
      T(P[2], PX, 282, "c is one constant the softmax adds to every token", 13, { fill: V("muted") });
      T(P[2], PX, 304, "of the row; the attacker can remove it later.", 13, { fill: V("muted") });

      // 3: stack
      title(P[3], "stack the answers");
      const strips = [];
      for (let i = 0; i < 12; i++)
        strips.push(S("rect", { x: PX, y: 122 + i * 19, width: 300, height: 13, rx: 4, fill: V("warn"), opacity: .3 }, P[3]));
      T(P[3], PX + 320, 150, `${fmt(COL.rows)} rows`, 20, { "font-weight": 700, fill: V("bad") });
      T(P[3], PX + 320, 176, `× ${fmt(VIC.vocab)} numbers`, 14, { fill: V("muted") });
      T(P[3], PX + 320, 200, `${COL.requests} requests`, 14, { fill: V("muted") });
      T(P[3], PX + 320, 222, `${COL.seconds} s`, 14, { fill: V("muted") });
      T(P[3], PX, 386, "the attacker’s only dataset: ordinary API answers", 13, { fill: V("muted") });

      // 4: spectrum
      title(P[4], "singular values of the stack");
      const IDS = [0, 1, 2, 572, 573, 574, 575, 576, 577, 578, 579, 1197, 1198, 1199];
      const base = 420, lg = v => Math.log10(v), LO = -3.5, HI = 4.2;
      const bars = SPE.values.map((v, i) => {
        const h = (lg(v) - LO) / (HI - LO) * 250;
        const big = IDS[i] <= SPE.dim - 1;
        return { i, h, big, x: PX + 8 + i * 27,
          el: S("rect", { x: PX + 8 + i * 27, y: base, width: 20, height: 0, rx: 3, fill: big ? V("warn") : V("dim") }, P[4]) };
      });
      S("line", { x1: PX, x2: PX + PW, y1: base + .5, y2: base + .5, stroke: V("line") }, P[4]);
      [[0, "0"], [3, "572"], [6, "575"], [7, "576"], [10, "579"], [13, "1199"]].forEach(([i, t]) =>
        T(P[4], bars[i].x + 10, base + 20, t, 13, { "text-anchor": "middle", fill: V("muted") }));
      const cliffTxt = T(P[4], bars[6].x + 10, base + 44, `s₅₇₅ ${SPE.s_k}   →   s₅₇₆ ${SPE.s_after}`, 14, { "text-anchor": "middle", class: "mono", fill: V("warn") });
      const ratio = T(P[4], bars[6].x + 10, 128, `cliff: ${sci(SPE.ratio, 1)}×`, 17, { "text-anchor": "middle", fill: V("bad"), "font-weight": 700 });
      S("line", { x1: bars[6].x + 24, x2: bars[6].x + 24, y1: 150, y2: base, stroke: V("bad"), "stroke-width": 1.5, "stroke-dasharray": "5 4" }, P[4]);
      chip(P[4], PX + 88, 456, 214, `rank ${SPE.dim} = the hidden size`, V("bad"), 14);

      // 5: same span
      title(P[5], "same span, different basis");
      S("rect", { x: PX, y: 130, width: 128, height: 86, rx: 12, fill: V("panel"), stroke: V("bad"), "stroke-width": 2 }, P[5]);
      T(P[5], PX + 64, 158, "B", 20, { "text-anchor": "middle", fill: V("bad"), class: "mono", "font-weight": 700 });
      T(P[5], PX + 64, 182, `${fmt(VIC.vocab)}×${SPE.dim}`, 13, { "text-anchor": "middle", fill: V("muted"), class: "mono" });
      T(P[5], PX + 64, 202, "orthonormal", 13, { "text-anchor": "middle", fill: V("muted") });
      S("rect", { x: PX + 24, y: 252, width: 122, height: 62, rx: 10, fill: "none", stroke: V("dim"), "stroke-width": 1.5, "stroke-dasharray": "5 4" }, P[5]);
      T(P[5], PX + 85, 276, "A = BᵀW", 15, { "text-anchor": "middle", class: "mono", fill: V("muted") });
      T(P[5], PX + 85, 298, `${SPE.dim}×${SPE.dim} · unknown`, 13, { "text-anchor": "middle", fill: V("muted") });
      arrow(P[5], `M${PX + 150} 173 H${PX + 210}`, V("violet"));
      S("rect", { x: PX + 216, y: 130, width: 150, height: 86, rx: 12, fill: V("panel"), stroke: V("violet"), "stroke-width": 2 }, P[5]);
      grid(P[5], PX + 216, 130, 150, 86, 5, 3, V("violet"));
      T(P[5], PX + 291, 162, "true W", 16, { "text-anchor": "middle", fill: V("violet"), "font-weight": 700 });
      T(P[5], PX + 291, 186, "operator-side check", 13, { "text-anchor": "middle", fill: V("muted") });
      const fit1 = T(P[5], PX, 366, `fit residual  ${sci(REC.rel_resid)}`, 17, { class: "mono", fill: V("ok"), "font-weight": 700 });
      const fit2 = T(P[5], PX, 396, `worst angle cosine  ${REC.cos_min.toFixed(4)}`, 17, { class: "mono", fill: V("ok"), "font-weight": 700 });
      const fit3 = T(P[5], PX, 428, "the weights sit inside span(B); the map A does not leave", 13, { fill: V("muted") });

      // 6: artifact
      title(P[6], "the stolen artifact");
      S("rect", { x: PX, y: 104, width: PW, height: 240, rx: 14, fill: V("panel"), stroke: V("lime"), "stroke-width": 2 }, P[6]);
      T(P[6], PX + 18, 134, "work/recovered_projection.safetensors", 14, { class: "mono", "font-weight": 600 });
      T(P[6], PX + 18, 172, D.canary, 22, { class: "mono", fill: V("lime"), "font-weight": 700 });
      T(P[6], PX + 18, 212, `${REC.d} × ${fmt(VIC.vocab)} float32 · ${REC.mb} MB`, 15, { class: "mono" });
      T(P[6], PX + 18, 240, `${fmt(REC.params)} of ${fmt(REC.model_params)} parameters (${REC.share}%)`, 15);
      T(P[6], PX + 18, 264, REC.tied ? "tied weights: also the input embedding table" : "", 13, { fill: V("muted") });
      chip(P[6], PX, 300, 120, "no transformer body", V("muted"));
      chip(P[6], PX + 132, 300, 110, "unknown A", V("muted"));
      chip(P[6], PX + 254, 300, 120, "no exact weights", V("muted"));
      T(P[6], PX, 372, `cost of the theft: ${fmt(REC.queries)} queries`, 14, { fill: V("bad"), "font-weight": 600 });

      // 7: serve less
      title(P[7], "defense 1 · serve less");
      chip(P[7], PX, 108, 184, `full rows → ${D1.refused_full}`, V("ok"), 14);
      chip(P[7], PX + 200, 108, 190, `logit_bias → ${D1.refused_bias}`, V("ok"), 14);
      T(P[7], PX, 172, `${fmt(D1.topk_rows)} top-5 answers: ${fmt(D1.distinct_ids)} scattered ids,`, 14, { fill: V("ok") });
      T(P[7], PX, 194, "never one complete row, so there is nothing to factor", 14, { fill: V("ok") });
      S("line", { x1: PX, x2: PX + PW, y1: 222, y2: 222, stroke: V("line") }, P[7]);
      T(P[7], PX, 252, "the escape, while bias exists:", 15, { fill: V("bad"), "font-weight": 700 });
      T(P[7], PX, 280, "+50 on four tokens lifts them into the top-5", 14);
      T(P[7], PX, 304, `${D1.per_request} exact logit differences per request · err ${sci(D1.max_err)}`, 14, { class: "mono" });
      T(P[7], PX, 348, `${fmt(D1.total_requests)} requests for the whole attack`, 17, { fill: V("bad"), "font-weight": 700 });
      T(P[7], PX, 374, `vs ${fmt(COL.rows)} before, ${fmt(D1.factor)}× the cost`, 14, { fill: V("muted") });

      // 8: degrade
      title(P[8], "defense 2 · degrade the numbers");
      T(P[8], PX, 116, "policy", 13, { fill: V("muted"), "font-weight": 700 });
      T(P[8], PX + 180, 116, "knee", 13, { fill: V("muted"), "font-weight": 700 });
      T(P[8], PX + 260, 116, "basis fit", 13, { fill: V("muted"), "font-weight": 700 });
      Object.entries(LV).forEach(([name, v], i) => {
        const y = 144 + i * 40, hot = name === "round=2";
        T(P[8], PX, y, name, 15, { class: "mono", fill: hot ? V("warn") : V("ink") });
        T(P[8], PX + 180, y, v.clear ? `${v.dim} ✓` : v.dim === SPE.dim ? `${v.dim} weak` : "none", 15,
          { fill: v.clear ? V("ok") : v.dim === SPE.dim ? V("warn") : V("muted") });
        T(P[8], PX + 260, y, sci(v.fit), 15, { class: "mono", fill: v.dim === SPE.dim ? V("warn") : V("muted") });
      });
      S("line", { x1: PX, x2: PX + PW, y1: 388, y2: 388, stroke: V("line") }, P[8]);
      T(P[8], PX, 414, `honest cost: new top-5 ties ${TIE["2"]}/200 answers at round 2,`, 13, { fill: V("muted") });
      T(P[8], PX, 436, `${TIE["1"]}/200 at round 1, ${TIE["0"]}/200 at round 0`, 13, { fill: V("muted") });

      // 9: monitor
      title(P[9], "defense 3 · watch the traffic");
      T(P[9], PX, 116, `median prompt score vs threshold ${nats(D3.threshold)}`, 13, { fill: V("muted") });
      [["app-user", "app-user", V("teal"), "pass"], ["thief", "token soup", V("bad"), "FLAGGED"],
       ["natural-thief", "natural text", V("bad"), "passes"]].forEach(([key, name, color, verdict], i) => {
        const y = 146 + i * 52, m = MON[key];
        T(P[9], PX, y, name, 15, { fill: color, "font-weight": 600 });
        T(P[9], PX + 150, y, nats(m.median), 16, { class: "mono" });
        T(P[9], PX + 230, y, `${fmt(m.queries)} queries`, 13, { fill: V("muted") });
        chip(P[9], PX + 330, y - 19, 60, verdict, key === "thief" ? V("ok") : V("muted"), 12);
      });
      S("line", { x1: PX, x2: PX + PW, y1: 306, y2: 306, stroke: V("line") }, P[9]);
      T(P[9], PX, 334, `natural text still recovers knee ${D3.natural.dim}`, 14, { fill: V("bad"), "font-weight": 600 });
      T(P[9], PX, 358, `fit ${sci(D3.natural.fit)}: the monitor cannot see it`, 13, { fill: V("muted") });
      S("line", { x1: PX + 6, x2: PX + 6 + 360, y1: 402, y2: 402, stroke: V("line"), "stroke-width": 3 }, P[9]);
      S("line", { x1: PX + 6 + 360 * D3.budget.cap / 750, x2: PX + 6 + 360 * D3.budget.cap / 750, y1: 388, y2: 402, stroke: V("ok"), "stroke-width": 4 }, P[9]);
      S("line", { x1: PX + 6 + 360 * 700 / 750, x2: PX + 6 + 360 * 700 / 750, y1: 388, y2: 402, stroke: V("bad"), "stroke-width": 4 }, P[9]);
      T(P[9], PX, 432, `budget ${D3.budget.cap}/key`, 13, { fill: V("ok"), "font-weight": 600 });
      T(P[9], PX + 200, 432, "≈700-row floor for a clear knee", 13, { fill: V("muted") });

      // ---------------- state, targets, draw ----------------
      const KEYS = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "atk", "wHot", "tag", "shield", "eye"];
      const zero = k => KEYS.reduce((o, n) => ((o[n] = k[n] || 0), o), {});
      const st = { ...zero({}), p1: 0 };
      const T_N = [null,
        { p1: 1 },
        { p2: 1 },
        { p3: 1, atk: 1 },
        { p4: 1, atk: 1 },
        { p5: 1, atk: 1, wHot: 1 },
        { p6: 1, atk: 1, wHot: 1, tag: 1 },
        { p7: 1, atk: 1, wHot: 1, tag: 1, shield: 1 },
        { p8: 1, atk: 1, wHot: 1, tag: 1, shield: 1 },
        { p9: 1, atk: 1, wHot: 1, tag: 1, shield: 1, eye: 1 },
      ];
      const target = n => ({ ...zero(T_N[n]) });

      function draw(s) {
        for (let i = 1; i <= 9; i++) {
          const o = X.clamp(s["p" + i]);
          A(P[i], { opacity: o.toFixed(3), transform: `translate(0 ${(16 * (1 - o)).toFixed(2)})` });
        }
        A(who, { fill: V(s.atk > .5 ? "bad" : "teal") });
        who.textContent = s.atk > .5 ? "attacker" : "you";
        A(flow, { stroke: V(s.atk > .5 ? "bad" : "teal") });
        A(soup, { opacity: X.clamp(s.atk).toFixed(3) });
        A(shield, { opacity: X.clamp(s.shield).toFixed(3) });
        A(eye, { opacity: X.clamp(s.eye).toFixed(3) });
        A(wRect, { stroke: V(s.wHot > .5 ? "bad" : "violet") });
        A(wGot, { opacity: X.clamp(s.wHot).toFixed(3) });
        A(tag, { opacity: X.clamp(s.tag).toFixed(3) });
        A(hChip, { opacity: 1 });
        const shown = Math.round(seg(s.p3, .12, .96) * strips.length);
        strips.forEach((r, i) => A(r, { opacity: i < shown ? .3 : 0 }));
        const k4 = seg(s.p4, .15, .85);
        bars.forEach(b => A(b.el, { height: Math.max(0, b.h * k4).toFixed(1), y: (base - b.h * k4).toFixed(1) }));
        A(cliffTxt, { opacity: seg(s.p4, .55, 1).toFixed(3) });
        A(ratio, { opacity: seg(s.p4, .7, 1).toFixed(3) });
        const k5 = seg(s.p5, .45, .95);
        [fit1, fit2, fit3].forEach(t => A(t, { opacity: k5.toFixed(3) }));
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          return api.tween(n === 1 ? 900 : 700, k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
