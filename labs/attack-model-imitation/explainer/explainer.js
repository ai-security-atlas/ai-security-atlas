/* Explainer: attack-model-imitation (LAB-09). "Copying a model one answer at a time": a classifier behind
 * victim-api answers queries at four detail levels; an attacker records 600 answers and fits a substitute;
 * the copy agrees with the victim but shares almost nothing with its weights; then three defenses, measured.
 * Every number, digit, answer and weight comes from window.LAB_DATA (data.js), which
 * scripts/export_explainer_data.py writes from a reference container run.
 * Pattern: target(n) is a pure function of the 1-based step, draw(s) is a pure render of a numeric state,
 * step(n, dir) tweens forward by one step and snaps otherwise (labs/_explainer/README.md). */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp;
  const D = window.LAB_DATA;
  const Q = D.query, ANS = Q.answers;
  const fmt = (v, n = 3) => Number(v).toFixed(n);
  const pct = v => (100 * v).toFixed(1) + "%";
  const ST = D.steal, BUD = ST.budgets, F = ST.fidelity;
  const C = D.compare, cp = C["copy (probs)"], cl = C["copy (label)"], ci = C["independent"];
  const D1 = D.d1, D1B = D1.budgets, D2 = D.d2, MON = D.d2_monitor, D3 = D.d3.checks;
  const wmL = D3["copy (label) | thief-label"], wmP = D3["copy (probs) | thief-probs"], wmI = D3["independent | thief-label"];
  const first = ST.first95;

  X.define({
    id: "attack-model-imitation",
    family: "family-theft",
    title: 'Copying a model <span class="outline">one answer</span> at a time',
    legend: [{ role: "teal", label: "Honest query" }, { role: "violet", label: "Victim model" }, { role: "warn", label: "API answer" },
      { role: "bad", label: "Attacker queries and copy" }, { role: "lime", label: "Canary tag" }, { role: "ok", label: "Defense" }],
    steps: [
      { chapter: "System", label: "Model behind an API",
        caption: `The owner trains a <span class="c-violet">digit classifier</span> on 900 private images (${pct(D.victim.test_acc)} test accuracy) and serves it with <code>victim-api</code>. Outsiders never see the weights: they send an <span class="c-teal">image</span> and get an <span class="c-warn">answer</span>.`,
        cmd: "docker compose run --rm workbench python attack-model-imitation/scripts/s01_train_victim.py" },
      { chapter: "System", label: "What an answer reveals",
        caption: `The same query at four detail levels. A <span class="c-warn">label</span> is one class of ten; <span class="c-warn">probs</span> and <span class="c-warn">logprobs</span> give all ten numbers, down to values near 1e-11 that a rounded display shows as 0.`,
        cmd: "docker compose run --rm workbench python attack-model-imitation/scripts/s02_query_api.py" },
      { chapter: "Attack", label: "Query and record",
        caption: `The attacker has 600 <span class="c-bad">unlabelled digits</span>, none from the owner's data. It sends them all and keeps every (query, answer) pair: the API labels the attacker's training set.`,
        cmd: "docker compose run --rm workbench python attack-model-imitation/scripts/s03_steal.py" },
      { chapter: "Mechanism", label: "Fit the answers",
        caption: `A fresh <span class="c-bad">copy</span> is trained to reproduce each answer. From a label it learns one class; from probabilities it also learns how the victim ranks the other nine classes, so every query teaches it more.` },
      { chapter: "Mechanism", label: "Fidelity vs queries",
        caption: `Agreement with the victim on 297 unseen digits: with probabilities the copy passes 95% after ${first.probs} queries, with top-3 after ${first.topk}, with labels only after ${first.label}.` },
      { chapter: "Impact", label: "A working copy",
        caption: `After 600 queries the copy agrees with the victim on ${pct(cp.agreement)} of unseen digits and repeats ${cp.errors} of its mistakes. It sits in <code>work/</code> tagged with the harmless canary <code class="c-lime">${D.canary}</code>.`,
        cmd: "docker compose run --rm workbench python attack-model-imitation/scripts/s03_steal.py" },
      { chapter: "Impact", label: "Not the same weights",
        caption: `Yet the weights differ: aligned first-layer correlation ${fmt(cp.aligned_r, 2)} for the copy, ${fmt(ci.aligned_r, 2)} for a model that never saw the API. Same behaviour, different parameters.`,
        cmd: "docker compose run --rm workbench python attack-model-imitation/scripts/s04_compare.py" },
      { chapter: "Defense", label: "Answer with less",
        caption: `<span class="c-ok">Label-only answers and rounding</span> cut the copy from ${fmt(D1.fidelity["probs (full)"][50])} to about ${fmt(D1.fidelity["label only"][50])} at 50 queries, while honest users get the same labels. At 600 queries every policy still leaks a 96% copy.`,
        cmd: "docker compose run --rm workbench python attack-model-imitation/scripts/d1_output_minimization.py" },
      { chapter: "Defense", label: "Budget per key",
        caption: `A <span class="c-ok">budget of ${D2.budget} queries per key</span> holds one key to a ${fmt(D2.fid_one)} copy. ${D2.sybils} keys get ${D2.sybils * D2.budget} answers and ${fmt(D2.fid_sybil)}; in the log they look like the first. Only the noise prober stands out.`,
        cmd: "docker compose run --rm workbench python attack-model-imitation/scripts/d2_budget_monitor.py" },
      { chapter: "Defense", label: "Prove the copy",
        caption: `A <span class="c-ok">watermark</span> (2% keyed wrong answers) catches the label copy, ${wmL.hits}/${wmL.n}, and misses the probability copy, ${wmP.hits}/${wmP.n}. A <span class="c-ok">fingerprint</span> catches that one instead. Neither stops the theft; they make it provable.`,
        cmd: "docker compose run --rm workbench python attack-model-imitation/scripts/d3_watermark_check.py" },
    ],
    html: `<style>
      [data-explainer="attack-model-imitation"] canvas.mi { position: absolute; image-rendering: pixelated; }
    </style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Model extraction through a prediction API"></svg>
    <canvas class="mi mi-q" width="8" height="8" role="img" aria-label="Query digit" style="left:70px;top:190px;width:128px;height:128px"></canvas>
    <canvas class="mi mi-pool" width="54" height="36" role="img" aria-label="Attacker's pool of digits" style="left:52px;top:150px;width:216px;height:144px"></canvas>
    <canvas class="mi mi-q2" width="8" height="8" role="img" aria-label="Training digit" style="left:60px;top:200px;width:128px;height:128px"></canvas>
    <canvas class="mi mi-wv" width="71" height="17" role="img" aria-label="Victim first-layer weights" style="left:60px;top:152px;width:390px;height:93px"></canvas>
    <canvas class="mi mi-wc" width="71" height="17" role="img" aria-label="Copy first-layer weights" style="left:60px;top:302px;width:390px;height:93px"></canvas>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const cvQ = el.querySelector(".mi-q"), cvPool = el.querySelector(".mi-pool"), cvQ2 = el.querySelector(".mi-q2");
      const cvWV = el.querySelector(".mi-wv"), cvWC = el.querySelector(".mi-wc");
      const T = (p, x, y, s, size = 16, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, fill = V("muted")) => T(p, x, y, s, 13, { fill, "font-weight": 700, "letter-spacing": "2" });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) => S("rect", { x, y, width: w, height: h, rx: 14, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = (p, d, color = V("dim"), w = 2.5) => S("path", { d, fill: "none", stroke: color, "stroke-width": w, "marker-end": `url(#${arrowId})` }, p);

      // ---------------- scene A: the API (steps 1-3) ----------------
      const gA = S("g", {}, svg);
      const gClient = S("g", {}, gA);
      label(gClient, 40, 150, "CLIENT");
      card(gClient, 40, 166, 190, 176);
      const gPoolLbl = S("g", {}, gA);
      label(gPoolLbl, 40, 128, "ATTACKER", V("bad"));
      card(gPoolLbl, 40, 140, 240, 200, V("bad"));
      const poolCount = T(gPoolLbl, 52, 322, "", 15, { class: "mono", fill: V("bad"), "font-weight": 600 });
      T(gPoolLbl, 40, 370, "600 unlabelled digits", 14, { fill: V("muted") });
      T(gPoolLbl, 40, 390, "(none from the owner's data)", 14, { fill: V("muted") });

      // owner side: API gate + victim
      const gOwner = S("g", {}, gA);
      S("rect", { x: 318, y: 100, width: 300, height: 330, rx: 18, fill: "none", stroke: V("dim"), "stroke-width": 1.5, "stroke-dasharray": "6 5" }, gOwner);
      label(gOwner, 330, 92, "OWNER'S SIDE");
      S("rect", { x: 330, y: 150, width: 16, height: 220, rx: 6, fill: V("dim") }, gOwner);
      T(gOwner, 338, 395, "victim-api", 13, { class: "mono", "text-anchor": "middle", fill: V("muted") });
      card(gOwner, 372, 168, 228, 184, V("violet"));
      T(gOwner, 388, 198, "VICTIM", 13, { fill: V("violet"), "font-weight": 700, "letter-spacing": "2" });
      T(gOwner, 388, 224, "MLP 64-64-10", 16, { class: "mono", "font-weight": 600 });
      T(gOwner, 388, 248, `${D.victim.params.toLocaleString("en-US")} parameters`, 14, { fill: V("muted") });
      T(gOwner, 388, 270, `test accuracy ${pct(D.victim.test_acc)}`, 14, { fill: V("muted") });
      const rr = X.rng(9);
      for (let r = 0; r < 3; r++) for (let c = 0; c < 9; c++)
        S("rect", { x: 388 + c * 22, y: 284 + r * 20, width: 16, height: 14, rx: 4, fill: V("violet"), opacity: (.15 + .6 * rr()).toFixed(2) }, gOwner);
      const aIn = arrow(gA, "M236 230 H322", V("teal"), 3);
      const aOut = arrow(gA, "M322 290 H236", V("warn"), 3);
      const aIn2 = arrow(gA, "M286 230 H322", V("bad"), 3);
      const aOut2 = arrow(gA, "M614 260 H644", V("warn"), 3);

      // answer panel
      const gAns = S("g", {}, gA);
      label(gAns, 640, 108, "ANSWER");
      card(gAns, 640, 120, 290, 330, V("warn"));
      const gAns1 = S("g", {}, gAns);
      T(gAns1, 660, 160, "detail=label", 13, { class: "mono", fill: V("muted") });
      T(gAns1, 660, 196, `{"label": "${ANS.label.label}"}`, 18, { class: "mono", fill: V("warn"), "font-weight": 600 });
      const gAns2 = S("g", {}, gAns);
      const rowY = [150, 186, 214, 334];   // label, top-3, probs (title), logprobs (title); bars sit 76 px below a title
      ["label", "top-3", "probs", "logprobs"].forEach((n, i) => T(gAns2, 656, rowY[i], n, 13, { class: "mono", fill: V("muted") }));
      T(gAns2, 740, rowY[0], `"${ANS.label.label}"`, 16, { class: "mono", fill: V("warn"), "font-weight": 600 });
      const tk = ANS.topk.top_k;
      tk.forEach((e, i) => T(gAns2, 740 + i * 62, rowY[1], `${e.label}:${e.p < .01 ? e.p.toExponential(0) : e.p.toFixed(2)}`, 13, { class: "mono", fill: V("warn") }));
      const barP = [], barL = [];
      for (let j = 0; j < 10; j++) {
        const x = 680 + j * 24;
        T(gAns2, x + 8, rowY[2] + 94, String(j), 13, { "text-anchor": "middle", fill: V("muted") });
        barP.push(S("rect", { x, y: rowY[2] + 76, width: 17, height: 0, rx: 3, fill: V("warn") }, gAns2));
        barL.push(S("rect", { x, y: rowY[3] + 76, width: 17, height: 0, rx: 3, fill: V("warn") }, gAns2));
      }
      S("line", { x1: 676, x2: 922, y1: rowY[2] + 76, y2: rowY[2] + 76, stroke: V("line") }, gAns2);
      S("line", { x1: 676, x2: 922, y1: rowY[3] + 76, y2: rowY[3] + 76, stroke: V("line") }, gAns2);
      T(gAns2, 922, rowY[3], "log scale -25 … 0", 13, { "text-anchor": "end", fill: V("muted") });
      const P = ANS.probs.probs, LP = ANS.logprobs.logprobs;

      // records (step 3)
      const gRec = S("g", {}, gA);
      label(gRec, 640, 108, "ATTACKER'S RECORDS");
      card(gRec, 640, 120, 290, 330, V("bad"));
      T(gRec, 660, 152, "query", 13, { class: "mono", fill: V("muted") });
      T(gRec, 790, 152, "answer", 13, { class: "mono", fill: V("muted") });
      const recRows = [];
      for (let i = 0; i < 8; i++) {
        const g = S("g", {}, gRec);
        T(g, 660, 182 + i * 30, `pool[${String(i).padStart(3, "0")}]`, 14, { class: "mono", fill: V("bad") });
        T(g, 790, 182 + i * 30, `"${D.pool_labels[i]}"`, 14, { class: "mono", fill: V("warn"), "font-weight": 600 });
        recRows.push(g);
      }
      const recCount = T(gRec, 660, 430, "", 14, { class: "mono", "font-weight": 600 });

      // ---------------- scene B: mechanism (steps 4-5) ----------------
      const gB = S("g", {}, svg);
      const gB1 = S("g", {}, gB);
      label(gB1, 50, 180, "QUERY");
      T(gB1, 50, 360, `victim says "${ANS.label.label}"`, 14, { fill: V("muted") });
      const tgtRow = (y, name, vals, color) => {
        T(gB1, 250, y - 20, name, 13, { class: "mono", fill: V("muted") });
        const cells = vals.map((v, j) => {
          S("rect", { x: 250 + j * 34, y, width: 28, height: 60, rx: 6, fill: "none", stroke: V("line") }, gB1);
          T(gB1, 264 + j * 34, y + 80, String(j), 13, { "text-anchor": "middle", fill: V("muted") });
          return S("rect", { x: 250 + j * 34, y: y + 60, width: 28, height: 0, rx: 6, fill: color }, gB1);
        });
        return { y, vals, cells };
      };
      const onehot = P.map((_, j) => j === Number(ANS.label.label) ? 1 : 0);
      const rowLab = tgtRow(150, "target from a label: one class", onehot, V("warn"));
      const rowProb = tgtRow(300, "target from logprobs: all ten (log scale)", LP.map(v => Math.max(0, (v + 25) / 25)), V("warn"));
      card(gB1, 640, 170, 280, 200, V("bad"));
      T(gB1, 660, 202, "COPY", 13, { fill: V("bad"), "font-weight": 700, "letter-spacing": "2" });
      T(gB1, 660, 228, "MLP 64-64-10, fresh weights", 15, { class: "mono", "font-weight": 600 });
      T(gB1, 660, 256, "loss = cross-entropy(label)", 13, { class: "mono", fill: V("muted") });
      T(gB1, 660, 278, "     + MSE(revealed logprobs)", 13, { class: "mono", fill: V("muted") });
      const fitRib = S("path", { d: "M600 200 C 620 200, 620 240, 640 250", fill: "none", stroke: V("bad"), "stroke-width": 5, "stroke-linecap": "round" }, gB1);
      const fitRib2 = S("path", { d: "M600 340 C 620 340, 620 300, 640 290", fill: "none", stroke: V("bad"), "stroke-width": 9, "stroke-linecap": "round" }, gB1);

      // chart (step 5)
      const gB2 = S("g", {}, gB);
      const cx0 = 110, cx1 = 860, cy0 = 450, cy1 = 110, ylo = .6;
      const xs = b => cx0 + (cx1 - cx0) * Math.log(b / BUD[0]) / Math.log(BUD[BUD.length - 1] / BUD[0]);
      const ys = v => cy0 - (cy0 - cy1) * (v - ylo) / (1 - ylo);
      S("line", { x1: cx0, x2: cx1, y1: cy0, y2: cy0, stroke: V("line"), "stroke-width": 1.5 }, gB2);
      [.6, .7, .8, .9, 1].forEach(v => {
        S("line", { x1: cx0, x2: cx1, y1: ys(v), y2: ys(v), stroke: V("line"), "stroke-width": 1 }, gB2);
        T(gB2, cx0 - 12, ys(v) + 5, v.toFixed(1), 13, { "text-anchor": "end", fill: V("muted") });
      });
      S("line", { x1: cx0, x2: cx1, y1: ys(.95), y2: ys(.95), stroke: V("dim"), "stroke-width": 1.5, "stroke-dasharray": "6 5" }, gB2);
      T(gB2, cx0 + 6, ys(.95) - 8, "95%", 13, { fill: V("muted") });
      BUD.forEach(b => T(gB2, xs(b), cy0 + 24, String(b), 13, { "text-anchor": "middle", fill: V("muted") }));
      T(gB2, (cx0 + cx1) / 2, cy0 + 50, "queries (log scale)", 13, { "text-anchor": "middle", fill: V("muted") });
      label(gB2, cx0, 80, "AGREEMENT WITH THE VICTIM ON 297 UNSEEN DIGITS");
      const lines = [["probs", 5], ["topk", 3.5], ["label", 2.5]].map(([d, w], i) => {
        const pts = BUD.map(b => [xs(b), ys(F[d][b])]);
        const path = S("path", { d: "M" + pts.map(p => p.map(v => v.toFixed(1)).join(" ")).join(" L"), fill: "none", stroke: V("bad"),
          "stroke-width": w, opacity: [1, .7, .45][i], pathLength: 1 }, gB2);
        const end = pts[pts.length - 1];
        const lab = T(gB2, end[0] + 8, end[1] + [0, 14, 18][i], d === "topk" ? "top-3" : d, 13, { class: "mono", fill: V("bad"), "font-weight": 600 });
        return { path, lab };
      });

      // ---------------- scene C: impact (steps 6-7) ----------------
      const gC = S("g", {}, svg);
      const gC1 = S("g", {}, gC);
      const tile = (x, big, small, color) => {
        card(gC1, x, 140, 270, 150, color);
        T(gC1, x + 20, 220, big, 44, { class: "mono", fill: color, "font-weight": 800 });
        T(gC1, x + 20, 262, small, 14, { fill: V("muted") });
      };
      tile(40, pct(cp.agreement), "agreement with the victim", V("bad"));
      tile(345, cp.errors, "of the victim's mistakes repeated", V("bad"));
      tile(650, "600", "queries, no weights, no data", V("bad"));
      card(gC1, 40, 330, 880, 110, V("lime"));
      T(gC1, 64, 372, "work/copy_probs.safetensors", 20, { class: "mono", "font-weight": 600 });
      T(gC1, 64, 410, `metadata: canary = ${D.canary}`, 17, { class: "mono", fill: V("lime"), "font-weight": 600 });

      const gC2 = S("g", {}, gC);
      label(gC2, 60, 140, "VICTIM · 16 hidden units, 8×8 input weights each");
      label(gC2, 60, 290, "COPY (probs) · same view", V("bad"));
      card(gC2, 480, 130, 450, 280);
      [["model", 500], ["agreement", 680], ["aligned r", 810]].forEach(([h, x]) => T(gC2, x, 166, h, 14, { class: "mono", fill: V("muted") }));
      [["copy (probs)", cp, V("bad")], ["copy (label)", cl, V("bad")], ["independent", ci, V("ink")]].forEach(([n, r, col], i) =>
        [[n, 500], [fmt(r.agreement), 680], [fmt(r.aligned_r, 2), 810]].forEach(([t, x]) =>
          T(gC2, x, 206 + i * 36, t, 15, { class: "mono", fill: col, "font-weight": 600 })));
      T(gC2, 500, 330, `cosine of all weights: copy ${fmt(cp.cosine)}`, 14, { fill: V("muted") });
      T(gC2, 500, 354, "high agreement, unrelated parameters", 14, { fill: V("muted") });

      // ---------------- scene D: defenses (steps 8-10) ----------------
      const gD = S("g", {}, svg);
      const gD1 = S("g", {}, gD);
      label(gD1, 60, 110, "COPY AGREEMENT AT 50 QUERIES (BAR) AND 600 (TICK)");
      const pols = Object.keys(D1.fidelity);
      const bx0 = 260, bx1 = 900, bl = .7, bscale = v => bx0 + (bx1 - bx0) * (v - bl) / (1 - bl);
      const d1Bars = pols.map((p, i) => {
        const y = 140 + i * 62;
        T(gD1, 60, y + 26, p, 15, { class: "mono", "font-weight": 600 });
        T(gD1, 60, y + 46, `served: ${D1.served[p]}`, 13, { fill: V("muted") });
        S("rect", { x: bx0, y, width: bx1 - bx0, height: 34, rx: 6, fill: V("panel"), stroke: V("line") }, gD1);
        const bar = S("rect", { x: bx0, y, width: 0, height: 34, rx: 6, fill: i ? V("ok") : V("bad"), opacity: .8 }, gD1);
        const tick = S("rect", { x: bscale(D1.fidelity[p][600]) - 2, y: y - 4, width: 4, height: 42, fill: V("bad") }, gD1);
        const val = T(gD1, bx0 + 8, y + 23, "", 14, { class: "mono", "font-weight": 700 });
        return { p, bar, tick, val };
      });
      T(gD1, bx0, 470, "0.70", 13, { fill: V("muted") });
      T(gD1, bx1, 470, "1.00", 13, { "text-anchor": "end", fill: V("muted") });

      const gD2 = S("g", {}, gD);
      label(gD2, 60, 100, `QUERY LOG · BUDGET ${D2.budget} PER KEY`);
      const keys = Object.keys(MON);
      const meters = keys.map((k, i) => {
        const y = 120 + i * 38, m = MON[k];
        const col = k === "app-user" ? V("teal") : V("bad");
        T(gD2, 60, y + 20, k, 14, { class: "mono", "font-weight": 600, fill: col });
        S("rect", { x: 200, y: y + 4, width: 300, height: 22, rx: 5, fill: V("panel"), stroke: V("line") }, gD2);
        const bar = S("rect", { x: 200, y: y + 4, width: 0, height: 22, rx: 5, fill: col, opacity: .7 }, gD2);
        const flag = T(gD2, 516, y + 20, m.flags.join(", ") || "-", 13, { fill: m.flags.includes("low-confidence") ? V("ok") : V("muted") });
        return { m, bar, flag };
      });
      S("rect", { x: 498, y: 116, width: 5, height: keys.length * 38, fill: V("ok") }, gD2);
      card(gD2, 690, 150, 240, 230, V("ok"));
      T(gD2, 710, 186, "copy agreement", 13, { fill: V("muted"), "font-weight": 700 });
      T(gD2, 710, 230, `1 key: ${fmt(D2.fid_one)}`, 20, { class: "mono", fill: V("ok"), "font-weight": 700 });
      const sybTxt = T(gD2, 710, 276, `${D2.sybils} keys: ${fmt(D2.fid_sybil)}`, 20, { class: "mono", fill: V("bad"), "font-weight": 700 });
      T(gD2, 710, 320, "budgets bind keys,", 14, { fill: V("muted") });
      T(gD2, 710, 342, "not people", 14, { fill: V("muted") });

      const gD3 = S("g", {}, gD);
      label(gD3, 60, 110, `OWNER'S CHECKS ON THREE SUSPECTS · WATERMARK KEY ${D.canary}`);
      card(gD3, 60, 130, 860, 300);
      T(gD3, 90, 172, "suspect", 14, { fill: V("muted"), "font-weight": 700 });
      T(gD3, 420, 172, "watermark hits", 14, { fill: V("muted"), "font-weight": 700 });
      T(gD3, 680, 172, "fingerprint", 14, { fill: V("muted"), "font-weight": 700 });
      const fpI = wmI.fingerprint;
      const rows3 = [["copy (label)", wmL], ["copy (probs)", wmP], ["independent", wmI]].map(([n, r], i) => {
        const y = 200 + i * 72;
        T(gD3, 90, y + 34, n, 17, { class: "mono", "font-weight": 600, fill: n === "independent" ? V("ink") : V("bad") });
        const caughtW = r.hits >= .8 * r.n, caughtF = n !== "independent" && r.fingerprint >= fpI + .15;
        const cW = S("rect", { x: 410, y, width: 210, height: 54, rx: 10, fill: caughtW ? V("ok") : V("panel"), "fill-opacity": .25, stroke: caughtW ? V("ok") : V("line"), "stroke-width": 2 }, gD3);
        T(gD3, 430, y + 34, `${r.hits}/${r.n}${caughtW ? " caught" : ""}`, 17, { class: "mono", "font-weight": 700, fill: caughtW ? V("ok") : V("muted") });
        const cF = S("rect", { x: 670, y, width: 210, height: 54, rx: 10, fill: caughtF ? V("ok") : V("panel"), "fill-opacity": .25, stroke: caughtF ? V("ok") : V("line"), "stroke-width": 2 }, gD3);
        T(gD3, 690, y + 34, `${fmt(r.fingerprint, 2)}${caughtF ? " caught" : ""}`, 17, { class: "mono", "font-weight": 700, fill: caughtF ? V("ok") : V("muted") });
        return { cW, cF };
      });

      // ---------------- canvases ----------------
      function digit(cv, x, color) {
        const ctx = cv.getContext("2d");
        ctx.clearRect(0, 0, 8, 8);
        ctx.fillStyle = color;
        x.forEach((v, i) => { ctx.globalAlpha = .08 + .92 * v / 16; ctx.fillRect(i % 8, Math.floor(i / 8), 1, 1); });
        ctx.globalAlpha = 1;
      }
      function pool(cv, k, color) {
        const ctx = cv.getContext("2d");
        ctx.clearRect(0, 0, 54, 36);
        ctx.fillStyle = color;
        const shown = Math.round(24 * k);
        D.pool.slice(0, shown).forEach((x, n) => {
          const ox = (n % 6) * 9, oy = Math.floor(n / 6) * 9;
          x.forEach((v, i) => { ctx.globalAlpha = .06 + .94 * v / 16; ctx.fillRect(ox + i % 8, oy + Math.floor(i / 8), 1, 1); });
        });
        ctx.globalAlpha = 1;
        return shown;
      }
      function weights(cv, w, color) {
        const ctx = cv.getContext("2d");
        ctx.clearRect(0, 0, 71, 17);
        ctx.fillStyle = color;
        w.forEach((v, i) => {                       // unit u = i / 64 drawn as its own 8x8 tile of pixel weights
          const u = Math.floor(i / 64), px = i % 64, ox = (u % 8) * 9, oy = Math.floor(u / 8) * 9;
          ctx.globalAlpha = Math.abs(v) / 100; ctx.fillRect(ox + px % 8, oy + Math.floor(px / 8), 1, 1);
        });
        ctx.globalAlpha = 1;
      }

      // ---------------- state ----------------
      const st = { a: 1, b: 0, c: 0, d: 0, ans: 1, det: 0, pool: 0, tgt: 0, curve: 0, copy: 0, wts: 0, d1: 0, d2: 0, sy: 0, d3: 0 };
      const base = { a: 0, b: 0, c: 0, d: 0, ans: 0, det: 0, pool: 0, tgt: 0, curve: 0, copy: 0, wts: 0, d1: 0, d2: 0, sy: 0, d3: 0 };
      const T_N = [null,
        { a: 1, ans: 1 },
        { a: 1, ans: 1, det: 1 },
        { a: 1, ans: 1, det: 1, pool: 1 },
        { b: 1, tgt: 1 },
        { b: 1, tgt: 1, curve: 1 },
        { c: 1, copy: 1 },
        { c: 1, copy: 1, wts: 1 },
        { d: 1, d1: 1 },
        { d: 1, d1: 1, d2: 1, sy: 1 },
        { d: 1, d1: 1, d2: 1, sy: 1, d3: 1 },
      ];
      const target = n => ({ ...base, ...T_N[n] });
      const vis = (g, o) => { g.setAttribute("opacity", Math.max(0, Math.min(1, o)).toFixed(3)); g.style.display = o <= 0.001 ? "none" : "inline"; };
      const cvis = (cv, o) => { cv.style.opacity = Math.max(0, Math.min(1, o)).toFixed(3); };

      function draw(s) {
        // scene A
        vis(gA, s.a);
        const pl = s.pool;
        vis(gClient, 1 - pl); vis(gPoolLbl, pl);
        cvis(cvQ, s.a * (1 - pl)); cvis(cvPool, s.a * pl);
        digit(cvQ, Q.x, api.color("teal"));
        const shown = pool(cvPool, seg(pl, 0, .8), api.color("bad"));
        cvPool.setAttribute("aria-label", `Attacker's pool: ${shown} of 24 digits shown`);
        poolCount.textContent = `queries sent: ${Math.round(600 * seg(pl, .2, 1))}`;
        vis(aIn, (1 - pl) * s.ans); vis(aOut, (1 - pl) * s.ans); vis(aIn2, pl); vis(aOut2, s.ans);
        vis(gAns, 1 - pl);
        vis(gAns1, 1 - s.det); vis(gAns2, s.det);
        barP.forEach((b, j) => { const h = 58 * P[j] * seg(s.det, .2, 1); A(b, { y: (rowY[2] + 76 - h).toFixed(2), height: h.toFixed(2) }); });
        barL.forEach((b, j) => { const h = 58 * Math.max(0, (LP[j] + 25) / 25) * seg(s.det, .4, 1); A(b, { y: (rowY[3] + 76 - h).toFixed(2), height: h.toFixed(2) }); });
        vis(gRec, pl);
        recRows.forEach((g, i) => vis(g, seg(pl, .1 + i * .08, .3 + i * .08)));
        recCount.textContent = `${Math.round(600 * seg(pl, .2, 1))} (query, answer) pairs`;
        // scene B
        vis(gB, s.b);
        vis(gB1, s.b * (1 - s.curve)); cvis(cvQ2, s.b * (1 - s.curve));
        digit(cvQ2, Q.x, api.color("bad"));
        [rowLab, rowProb].forEach((row, r) => row.cells.forEach((c, j) => {
          const h = 60 * row.vals[j] * seg(s.tgt, r * .3, r * .3 + .7);
          A(c, { y: (row.y + 60 - h).toFixed(2), height: h.toFixed(2) });
        }));
        A(fitRib, { opacity: seg(s.tgt, .5, 1).toFixed(3) }); A(fitRib2, { opacity: seg(s.tgt, .7, 1).toFixed(3) });
        vis(gB2, s.curve);
        lines.forEach((l, i) => { const k = seg(s.curve, i * .15, .6 + i * .15); l.path.setAttribute("stroke-dasharray", `${k.toFixed(3)} 1`); vis(l.lab, k); });
        // scene C
        vis(gC, s.c);
        vis(gC1, s.copy * (1 - s.wts)); vis(gC2, s.wts);
        cvis(cvWV, s.c * s.wts); cvis(cvWC, s.c * s.wts);
        weights(cvWV, D.weights.victim, api.color("violet"));
        weights(cvWC, D.weights.copy, api.color("bad"));
        // scene D
        vis(gD, s.d);
        vis(gD1, s.d1 * (1 - s.d2)); vis(gD2, s.d2 * (1 - s.d3)); vis(gD3, s.d3);
        d1Bars.forEach((b, i) => {
          const v = D1.fidelity[b.p][50], k = seg(s.d1, i * .08, .6 + i * .08);
          A(b.bar, { width: ((bscale(v) - bx0) * k).toFixed(2) });
          b.val.textContent = k > .99 ? fmt(v) : "";
          vis(b.tick, k);
        });
        meters.forEach((mt, i) => {
          const k = seg(s.d2, i * .05, .5 + i * .05);
          A(mt.bar, { width: (300 * Math.min(1, mt.m.served / D2.budget) * k).toFixed(2) });
          vis(mt.flag, k);
        });
        vis(sybTxt, s.sy);
        rows3.forEach((r, i) => { const k = seg(s.d3, i * .15, .6 + i * .15); vis(r.cW, k); vis(r.cF, k); });
      }

      draw(st);
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
