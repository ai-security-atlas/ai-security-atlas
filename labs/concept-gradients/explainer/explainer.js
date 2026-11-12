/* LAB-50 concept-gradients: "Gradients point both ways" (foundation lab, 8 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: a strip across the top (input -> model -> loss, with the backward pass flowing back to both the
 * input and the weights) and a panel below it that crossfades per step. Every number comes from
 * window.LAB_DATA (data.js, exported from the reference workbench run). Pattern: target(n) is pure,
 * draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA, BP = D.backprop, TR = D.train, TW = D.two, FG = D.fgsm, LK = D.leak, SC = D.scale;
  const DP = D.dp, AT = D.at;
  const pct = (p, d = 1) => (100 * p).toFixed(d) + "%";
  const sci = x => Number(x).toExponential(1);
  const LT = LK["trained (Step 2)"], LF = LK["fresh random weights"];
  const first = FG.rows.find(r => r.eps === FG.first) || FG.rows[FG.rows.length - 1];
  const at02 = SC.curve.find(r => r.eps === 0.2);
  const pMin = Math.min(...SC.batch.map(r => r.precision));
  const dp8 = DP.models[1], dp1 = DP.models[2], base = DP.models[0];
  const ATB = AT.rows[0], ATA = AT.rows[1];
  const [k7, kr7] = FG.all7["0.3"];

  X.define({
    id: "concept-gradients",
    family: "family-evasion",
    title: 'Gradients point both <span class="outline">ways</span>',
    legend: [{ role: "teal", label: "Input / data", tag: "training-data" }, { role: "violet", label: "Model / weights", tag: "model-weights" },
      { role: "warn", label: "Loss / prediction", tag: "measurement" }, { role: "bad", label: "Gradient / attack", tag: "adversarial-perturbation" },
      { role: "lime", label: "Canary / leaked label" }, { role: "ok", label: "Defense", tag: "robust-training" }],
    intro: {
      why: "Every neural network learns the same way. It scores an example, measures how wrong the score was, and asks which way each weight should move to be less wrong. The answer to that question is the gradient. The same calculation can also say how to change the input, and it carries traces of the example it came from. Who can see a gradient, and what can they do with it?",
      plan: "You’ll train a small digit classifier step by step and check that its gradients are right. Then you’ll take one digit and ask for two gradients at once: one for the pixels and one for the weights. The first lets you fool the model with a tiny change. The second lets a training server read the digit’s label. You’ll finish by testing two defenses, one for each direction.",
      terms: "A loss is one number that says how wrong the model was on an example; lower is better. A gradient lists, for every number the loss depends on, how fast the loss changes when that number moves. Backpropagation is the method that computes all of these in one backward pass. A training step moves each weight a little against its gradient. FGSM, the fast gradient sign method, moves each pixel a little along the sign of its gradient. In federated learning, devices send gradients to a server instead of data. The canary is the fixed target class 3, reported as a harmless string.",
    },
    steps: [
      { chapter: "System", label: "One backward pass",
        guide: "Start with a model whose weights are still random. It scores a small batch of digits, and its loss sits near the value of a blind guess. One backward pass returns a gradient entry for every weight. Nudging single weights by hand confirms a few of those entries. A step against the gradient lowers the loss, and a step along it raises the loss.",
        caption: `Untrained CNN, 8 digits: loss <span class="c-warn">${BP.loss}</span> (ln 10 = ${BP.ln10}). Gradient: <span class="c-bad">${BP.total.toLocaleString("en")}</span> numbers in ${BP.params.length} tensors. Backprop vs finite differences: worst relative error ${sci(BP.worst_rel)}. One step at lr ${BP.lr}: θ − lr·g → loss <span class="c-ok">${BP.loss_down}</span>; θ + lr·g → loss <span class="c-bad">${BP.loss_up}</span>.`,
        cmd: "docker compose run --rm workbench python concept-gradients/scripts/s01_backprop.py" },
      { chapter: "System", label: "Training loop",
        guide: "Training is that same step repeated, each time on a fresh batch of training digits. The loss falls fast at first and then flattens. The model has never seen the held-out test digits, so its accuracy on them shows what it learned. Seeded, single-thread training gives the same weights every run, the same as the shared checkpoint later labs attack.",
        caption: `${TR.steps} gradient steps (Adam, batch 64) on ${TR.n_train.toLocaleString("en")} digits: loss <span class="c-warn">${TR.curve[0]}</span> → <span class="c-warn">${TR.curve[TR.curve.length - 1]}</span>. Test accuracy <span class="c-violet">${pct(TR.test_acc)}</span> on ${TR.n_test} held-out digits. Largest weight difference from vision-zoo <code>cnn-clean</code>: ${sci(TR.ref_gap)}.`,
        cmd: "docker compose run --rm workbench python concept-gradients/scripts/s02_train.py" },
      { chapter: "Attack", label: "Two gradients",
        guide: "The risk starts with one test digit the model gets right. Run one backward pass and ask for the gradient with respect to the pixels and with respect to the weights. The pixel gradient is a map of which pixels would hurt the model most. The weight gradient of the output layer has a single negative entry, and it sits on the true label.",
        caption: `Test digit #${TW.index} (a ${TW.label}), p = ${TW.p}, loss ${sci(TW.loss)}. Pixel gradient: 64 numbers, ${TW.pos} positive and ${TW.neg} negative; the top 10 pixels hold ${pct(TW.share10)} of its size. Output-layer bias gradient = p − onehot(label) within ${sci(TW.gap)}; its only negative entry: class <span class="c-lime">${TW.neg_bias.join(", ")}</span>. Weight gradient: ${TW.n_w.toLocaleString("en")} numbers.`,
        cmd: "docker compose run --rm workbench python concept-gradients/scripts/s03_two_ways.py" },
      { chapter: "Mechanism", label: "One FGSM step",
        guide: "Turn the training step around and apply it to the input. FGSM moves every pixel by the same small amount, in the direction its gradient says will push the model toward class 3. Random noise of the same size leaves the prediction alone. The signed step changes it once the budget is large enough, and the digit still looks like a 7.",
        caption: `Demo 7, targeted toward ${D.target}: p(3) by budget ε ${FG.rows.map(r => `${r.eps}: ${r.p3}`).join(", ")}. From ε = ${FG.first} it reads <span class="c-lime">${D.target}</span> (<code>${D.canary}</code>); random ±ε noise keeps it at ${first.random}. On all ${FG.n7} correct test 7s at ε 0.3: ${k7}/${FG.n7} read 3 after FGSM, ${kr7}/${FG.n7} after noise.`,
        cmd: "docker compose run --rm workbench python concept-gradients/scripts/s04_fgsm.py" },
      { chapter: "Mechanism", label: "Label from a gradient",
        guide: "Now play the training server. A client sends the gradient of one private digit and nothing else. Each row of the output layer’s weight gradient is a probability gap times activations that are never negative. So only the true label’s row can go below zero. Reading that sign names the label, on a trained model and on a freshly initialized one.",
        caption: `Example digit (label ${LK.example.label}): row sums ${LK.example.rows.map((v, c) => c === LK.example.label ? `<span class="c-lime">${sci(v)}</span>` : sci(v)).join(", ")}. Guess ${LK.example.guess}. Labels recovered: trained <span class="c-bad">${LT.k}/${LT.n}</span>, fresh weights <span class="c-bad">${LF.k}/${LF.n}</span>; chance is 10/100.`,
        cmd: "docker compose run --rm workbench python concept-gradients/scripts/s05_label_leak.py" },
      { chapter: "Impact", label: "How far it reaches",
        guide: "Both attacks also work at scale. On the input side, one FGSM step sweeps the whole test set and accuracy collapses as the budget grows, while random noise barely moves it. On the weight side, the server receives the average gradient of a batch. Bigger batches hide more of the labels, yet every label the sign test names is really in the batch.",
        caption: `Test accuracy at ε 0.2: FGSM <span class="c-bad">${pct(at02.fgsm)}</span>, random noise ${pct(at02.random)}. Targeted canary <code>${D.canary}</code>: ${k7}/${FG.n7} test 7s at ε 0.3. Batch means (${SC.batch[0].trials} batches per size): recall ${SC.batch.map(r => `B=${r.B} ${r.recall}`).join(", ")}; ${pMin === 1 ? "precision 1.00" : `precision at least ${pMin.toFixed(2)}`} at every size.`,
        cmd: "docker compose run --rm workbench python concept-gradients/scripts/s06_scale.py" },
      { chapter: "Defense", label: "DP-SGD",
        guide: "DP-SGD clips each example’s gradient to a fixed size and adds random noise before anyone sees it. An accountant turns the noise level into a privacy guarantee called DP epsilon; smaller means more noise. This epsilon is unrelated to the pixel budget of FGSM. Training with the noise needed for a common DP epsilon costs test accuracy, and the private model is still easy to fool with FGSM. In a separate test, a client clips its shared gradient and adds the same noise before sending it, and the label test drops to chance.",
        caption: `Opacus, clip ${DP.clip}, δ ${DP.delta}: DP ε ${dp8.eps} needs σ ${dp8.sigma} (test ${pct(dp8.acc)}, FGSM at pixel budget 0.2 → ${pct(dp8.fgsm)}); DP ε ${dp1.eps} needs σ ${dp1.sigma} (test ${pct(dp1.acc)}). No DP: test ${pct(base.acc)}. Labels from one released gradient: ${DP.leak.map(r => `σ ${r.sigma} <span class="${r.k > 20 ? "c-bad" : "c-ok"}">${r.k}/${r.n}</span>`).join(", ")}.`,
        cmd: "docker compose run --rm workbench python concept-gradients/scripts/d1_dp.py" },
      { chapter: "Defense", label: "Adversarial training",
        guide: "Adversarial training covers the input side. Half of every batch is replaced by FGSM versions made against the current weights. FGSM accuracy rises a lot for a cost of a few tenths of a point of clean accuracy, and a stronger ten-step attack still finds more errors. The label leaks from this model’s gradients exactly as before. Each defense covers one direction, on one small model and dataset, so you need both when both kinds of access exist.",
        caption: `ε ${AT.eps}: Step 2 model clean ${pct(ATB.clean)}, FGSM ${pct(ATB.fgsm)}, PGD-10 ${pct(ATB.pgd)}; adversarially trained clean ${pct(ATA.clean)}, FGSM <span class="c-ok">${pct(ATA.fgsm)}</span>, PGD-10 <span class="c-warn">${pct(ATA.pgd)}</span>. Labels from its gradients: <span class="c-bad">${ATA.labels}/${ATA.n}</span>.`,
        cmd: "docker compose run --rm workbench python concept-gradients/scripts/d2_adv_train.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="A digit classifier, its loss and the gradients that flow back to the input and to the weights, with a detail panel per step"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line")) => S("rect", { x, y, width: w, height: h, rx: 10, fill: V("panel"), stroke, "stroke-width": 2 }, p);
      const chip = (p, x, y, w, text, role) => {
        S("rect", { x, y: y - 17, width: w, height: 24, rx: 12, fill: V(role), "fill-opacity": 0.16, stroke: V(role) }, p);
        T(p, x + w / 2, y, text, 13, { "text-anchor": "middle", class: "mono", fill: V(role), "font-weight": 700 });
      };
      const defs = S("defs", {}, svg);
      const mk = (name, role) => {
        const id = api.uid(name);
        const m = S("marker", { id, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
        S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V(role) }, m);
        return `url(#${id})`;
      };
      const fwd = mk("fwd", "teal"), back = mk("back", "bad");
      // animated pieces: bars grow with their panel's g value, `later` items fade in, lines draw on
      const bars = [], reveal = [], lines = [];
      const hbar = (p, x, y, w, h, role, share, panel) => {
        S("rect", { x, y, width: w, height: h, rx: 3, fill: V("panel-2"), stroke: V("line") }, p);
        bars.push({ b: S("rect", { x, y, width: 0, height: h, rx: 3, fill: V(role) }, p), w, share, panel, horiz: true });
      };
      // vertical bar from a baseline y0; negative share grows downward
      const vbar = (p, x, y0, w, h, role, share, panel) => {
        bars.push({ b: S("rect", { x, y: y0, width: w, height: 0, rx: 2, fill: V(role) }, p), y0, h, share, panel, horiz: false });
      };
      const later = (g, panel, at) => { reveal.push({ el: g, panel, at }); return g; };
      const line = (p, pts, role, panel, width = 3) => {
        const d = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
        let len = 0;
        for (let i = 1; i < pts.length; i++) len += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
        const el2 = S("path", { d, fill: "none", stroke: V(role), "stroke-width": width, "stroke-linejoin": "round", "stroke-dasharray": len.toFixed(1) }, p);
        lines.push({ el: el2, len, panel });
      };
      // an 8x8 grid of cells; value in [0, 1] sets the opacity
      const grid8 = (p, x0, y0, cs, vals, role) => vals.forEach((r, i) => r.forEach((v, j) =>
        S("rect", { x: x0 + j * cs, y: y0 + i * cs, width: cs - 3, height: cs - 3, rx: 3, fill: V(role), "fill-opacity": (0.06 + 0.94 * v).toFixed(3) }, p)));
      const logShare = v => Math.sign(v) * Math.max(0, Math.min(1, (Math.log10(Math.abs(v) + 1e-30) + 13) / 12));

      // ---- strip: input -> model -> loss, and the backward pass to both ends
      const strip = [["INPUT x", "teal", "8×8 digit, 64 pixels"], ["MODEL θ", "violet", "CNN, 38,282 weights"], ["LOSS", "warn", "−log p(label)"]];
      const stripG = strip.map(([k, role, sub], i) => {
        const g = S("g", { class: "dimmable" }, svg);
        const x = 40 + i * 320;
        card(g, x, 14, 240, 62, V(role));
        label(g, x + 16, 38, k, { fill: V(role), "letter-spacing": "1" });
        T(g, x + 16, 63, sub, 14, { class: "mono" });
        if (i) S("path", { d: `M${x - 74} 36 H${x - 6}`, fill: "none", stroke: V("teal"), "stroke-width": 2.5, "marker-end": fwd }, svg);
        return g;
      });
      const backW = S("path", { d: "M780 76 C 740 104, 560 104, 520 80", fill: "none", stroke: V("bad"), "stroke-width": 3, "marker-end": back }, svg);
      const backX = S("path", { d: "M780 76 C 700 118, 260 118, 200 80", fill: "none", stroke: V("bad"), "stroke-width": 3, "marker-end": back }, svg);
      const backWT = T(svg, 508, 100, "∂loss/∂θ", 13, { class: "mono", fill: V("bad"), "text-anchor": "end" });
      const backXT = T(svg, 188, 100, "∂loss/∂x", 13, { class: "mono", fill: V("bad"), "text-anchor": "end" });

      const panels = [];
      const panel = title => {
        const g = S("g", { class: "dimmable hot" }, svg);
        label(g, 40, 140, title);
        panels.push(g);
        return g;
      };

      // ---- 1: one backward pass
      {
        const g = panel(`ONE BACKWARD PASS · ${BP.total.toLocaleString("en")} GRADIENT NUMBERS`);
        const maxN = Math.max(...BP.params.map(r => r.norm));
        BP.params.forEach((r, i) => {
          const y = 166 + i * 34;
          T(g, 40, y + 14, r.name, 14, { class: "mono" });
          hbar(g, 210, y + 2, 220, 16, "bad", r.norm / maxN, 0);
          T(g, 440, y + 15, `${r.n.toLocaleString("en")} · |g| ${r.norm}`, 13, { class: "mono", fill: V("muted") });
        });
        const x0 = 640, y0 = 470, h = 260, top = Math.max(BP.loss_up, BP.loss, BP.loss_down);
        S("line", { x1: x0 - 20, x2: 930, y1: y0, y2: y0, stroke: V("line") }, g);
        [["θ − lr·g", BP.loss_down, "ok"], ["θ", BP.loss, "warn"], ["θ + lr·g", BP.loss_up, "bad"]].forEach(([nm, v, role], i) => {
          const x = x0 + i * 100;
          vbar(g, x, y0, 60, h, role, v / top, 0);
          T(g, x + 30, y0 + 22, nm, 13, { class: "mono", "text-anchor": "middle" });
          later(T(g, x + 30, y0 - h * v / top - 8, String(v), 14, { class: "mono", "text-anchor": "middle", "font-weight": 700, fill: V(role) }), 0, 0.7);
        });
        T(g, 620, 166, `loss on the batch (ln 10 = ${BP.ln10})`, 14, { fill: V("muted") });
        later(S("g", {}, g), 0, 0.85);
        chip(reveal[reveal.length - 1].el, 40, 460, 380, `finite-difference check: worst error ${sci(BP.worst_rel)}`, "ok");
      }
      // ---- 2: the training loop
      {
        const g = panel(`TRAINING · ${TR.steps} STEPS AGAINST THE GRADIENT`);
        const x0 = 90, x1 = 620, y0 = 470, y1 = 196, top = TR.curve[0];
        S("line", { x1: x0, x2: x1, y1: y0, y2: y0, stroke: V("line") }, g);
        S("line", { x1: x0, x2: x0, y1: y0, y2: y1, stroke: V("line") }, g);
        const pts = TR.curve.map((v, i) => [x0 + (x1 - x0) * i / (TR.curve.length - 1), y0 - (y0 - y1) * v / top]);
        line(g, pts, "warn", 1);
        T(g, x0 - 10, y1 + 5, String(top), 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
        T(g, x0 - 10, y0 + 5, "0", 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
        T(g, x0, y0 + 26, "epoch 1", 13, { fill: V("muted") });
        T(g, x1, y0 + 26, `epoch ${TR.curve.length}`, 13, { fill: V("muted"), "text-anchor": "end" });
        T(g, x0 + 10, y1 - 16, "mean training loss per epoch", 14, { fill: V("muted") });
        const cg = later(S("g", {}, g), 1, 0.8);
        card(cg, 680, 200, 240, 100, V("violet"));
        T(cg, 700, 234, "test accuracy", 14, { fill: V("muted") });
        T(cg, 700, 276, pct(TR.test_acc), 30, { class: "mono", "font-weight": 800, fill: V("violet") });
        T(cg, 680, 340, `${TR.n_test} held-out digits`, 14, { fill: V("muted") });
        T(cg, 680, 366, `same weights as cnn-clean: ${TR.ref_gap === 0 ? "yes" : "no"}`, 14, { class: "mono" });
      }
      // ---- 3: one digit, two gradients
      {
        const g = panel(`ONE DIGIT, TWO GRADIENTS · TEST #${TW.index}, LABEL ${TW.label}`);
        T(g, 40, 176, "the digit", 14, { fill: V("muted") });
        grid8(g, 40, 190, 30, TW.image, "teal");
        T(g, 310, 176, "∂loss/∂x (size)", 14, { fill: V("muted"), class: "mono" });
        later(S("g", {}, g), 2, 0.2);
        grid8(reveal[reveal.length - 1].el, 310, 190, 30, TW.saliency, "bad");
        T(g, 580, 176, "∂loss/∂(output bias), log scale", 14, { fill: V("muted"), class: "mono" });
        const y0 = 330, h = 120;
        S("line", { x1: 580, x2: 930, y1: y0, y2: y0, stroke: V("line") }, g);
        TW.bias_grad.forEach((v, c) => {
          const s = logShare(v), x = 590 + c * 34;
          vbar(g, x, y0, 22, h, s < 0 ? "lime" : "violet", s, 2);
          T(g, x + 11, y0 + (s < 0 ? -10 : 22), String(c), 13, { class: "mono", "text-anchor": "middle", fill: V(s < 0 ? "lime" : "muted") });
        });
        later(T(g, 580, 500, `only negative entry: class ${TW.neg_bias.join(", ")} = the label`, 15, { "font-weight": 700, fill: V("lime") }), 2, 0.8);
      }
      // ---- 4: one FGSM step toward 3
      {
        const g = panel(`ONE FGSM STEP TOWARD ${D.target} · ε = ${FG.first}`);
        T(g, 40, 176, "before", 14, { fill: V("muted") });
        grid8(g, 40, 190, 28, TW.image, "teal");
        T(g, 290, 176, `after (each pixel moved ≤ ${FG.first})`, 14, { fill: V("muted") });
        later(S("g", {}, g), 3, 0.3);
        grid8(reveal[reveal.length - 1].el, 290, 190, 28, FG.adv, "bad");
        T(g, 580, 176, "p(3) after the step, by ε", 14, { fill: V("muted") });
        const y0 = 440, h = 230;
        S("line", { x1: 575, x2: 930, y1: y0, y2: y0, stroke: V("line") }, g);
        FG.rows.forEach((r, i) => {
          const x = 585 + i * 50, hit = r.targeted === D.target;
          vbar(g, x, y0, 34, h, hit ? "lime" : "warn", r.p3, 3);
          T(g, x + 17, y0 + 22, String(r.eps), 13, { class: "mono", "text-anchor": "middle", fill: V("muted") });
        });
        const cg = later(S("g", {}, g), 3, 0.8);
        chip(cg, 580, 500, 340, `reads ${D.target}: ${D.canary}`, "lime");
        T(cg, 40, 500, `random ±ε noise: still a ${first.random}`, 15, { class: "mono", fill: V("teal") });
      }
      // ---- 5: the label from one shared gradient
      {
        const g = panel(`A SERVER READS THE LABEL · ONE SHARED GRADIENT`);
        T(g, 40, 176, "output-layer weight gradient, row sums (log scale)", 14, { fill: V("muted") });
        const y0 = 320, h = 120;
        S("line", { x1: 40, x2: 560, y1: y0, y2: y0, stroke: V("line") }, g);
        LK.example.rows.forEach((v, c) => {
          const s = logShare(v), x = 52 + c * 50;
          vbar(g, x, y0, 30, h, s < 0 ? "lime" : "violet", s, 4);
          T(g, x + 15, y0 + (s < 0 ? -10 : 22), String(c), 13, { class: "mono", "text-anchor": "middle", fill: V(s < 0 ? "lime" : "muted") });
        });
        later(T(g, 40, 480, `guess ${LK.example.guess} · true label ${LK.example.label}`, 16, { class: "mono", "font-weight": 800, fill: V("lime") }), 4, 0.6);
        [["trained model", LT], ["fresh random weights", LF]].forEach(([nm, r], i) => {
          const y = 200 + i * 110, cg = later(S("g", {}, g), 4, 0.3 + 0.25 * i);
          card(cg, 620, y, 300, 86, V("bad"));
          T(cg, 640, y + 32, nm, 15, { "font-weight": 700 });
          T(cg, 640, y + 66, `labels recovered ${r.k}/${r.n}`, 16, { class: "mono", fill: V("bad"), "font-weight": 800 });
        });
        T(g, 620, 450, "chance: 10/100", 14, { class: "mono", fill: V("muted") });
      }
      // ---- 6: how far each direction reaches
      {
        const g = panel("HOW FAR EACH DIRECTION REACHES");
        T(g, 40, 172, "test accuracy after one step of size ε", 14, { fill: V("muted") });
        const x0 = 70, x1 = 430, y0 = 450, y1 = 200, eMax = SC.curve[SC.curve.length - 1].eps;
        S("line", { x1: x0, x2: x1, y1: y0, y2: y0, stroke: V("line") }, g);
        S("line", { x1: x0, x2: x0, y1: y0, y2: y1, stroke: V("line") }, g);
        const P = key => SC.curve.map(r => [x0 + (x1 - x0) * r.eps / eMax, y0 - (y0 - y1) * r[key]]);
        line(g, P("random"), "teal", 5);
        line(g, P("fgsm"), "bad", 5);
        T(g, x0 - 8, y1 + 5, "100%", 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
        T(g, x0 - 8, y0 + 5, "0", 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
        T(g, x1, y0 + 24, `ε ${eMax}`, 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
        T(g, x1 + 8, y0 - (y0 - y1) * SC.curve[SC.curve.length - 1].random + 5, "noise", 13, { fill: V("teal") });
        T(g, x0 + 150, y0 - 12, "FGSM", 13, { fill: V("bad"), "font-weight": 700 });
        later(T(g, 40, 505, `canary ${D.canary}: ${k7}/${FG.n7} test 7s at ε 0.3`, 14, { class: "mono", fill: V("lime") }), 5, 0.8);
        T(g, 540, 172, "labels found in a batch-mean gradient (recall)", 14, { fill: V("muted") });
        const by0 = 450, bh = 230;
        S("line", { x1: 540, x2: 930, y1: by0, y2: by0, stroke: V("line") }, g);
        SC.batch.forEach((r, i) => {
          const x = 556 + i * 62;
          vbar(g, x, by0, 40, bh, "bad", r.recall, 5);
          T(g, x + 20, by0 + 22, `B=${r.B}`, 13, { class: "mono", "text-anchor": "middle", fill: V("muted") });
          later(T(g, x + 20, by0 - bh * r.recall - 8, r.recall.toFixed(2), 13, { class: "mono", "text-anchor": "middle" }), 5, 0.7);
        });
        later(T(g, 540, 505, pMin === 1 ? "every label named was in the batch (precision 1.00)" : `precision at least ${pMin.toFixed(2)}`, 14, { class: "mono", fill: V("bad") }), 5, 0.85);
      }
      // ---- 7: DP-SGD
      {
        const g = panel("D1 · DP-SGD: CLIP EACH GRADIENT, ADD NOISE");
        T(g, 40, 176, "labels recovered from one released gradient", 14, { fill: V("muted") });
        DP.leak.forEach((r, i) => {
          const y = 196 + i * 44, low = r.k <= 20;
          T(g, 40, y + 17, `σ ${r.sigma}`, 14, { class: "mono" });
          hbar(g, 140, y + 2, 260, 20, low ? "ok" : "bad", r.k / r.n, 6);
          T(g, 410, y + 17, `${r.k}/${r.n}`, 14, { class: "mono", "font-weight": 700, fill: V(low ? "ok" : "bad") });
        });
        T(g, 520, 176, "test accuracy · FGSM accuracy at ε 0.2", 14, { fill: V("muted") });
        DP.models.forEach((r, i) => {
          const y = 200 + i * 96, cg = later(S("g", {}, g), 6, 0.2 + 0.2 * i);
          T(cg, 520, y + 14, r.eps === null ? "no DP" : `ε ${r.eps} (σ ${r.sigma})`, 15, { "font-weight": 700 });
          hbar(cg, 520, y + 26, 300, 16, "violet", r.acc, 6);
          T(cg, 830, y + 40, pct(r.acc), 13, { class: "mono" });
          hbar(cg, 520, y + 50, 300, 16, "bad", r.fgsm, 6);
          T(cg, 830, y + 64, pct(r.fgsm), 13, { class: "mono", fill: V("bad") });
        });
      }
      // ---- 8: adversarial training
      {
        const g = panel(`D2 · ADVERSARIAL TRAINING · ε = ${AT.eps}`);
        [["Step 2 model", ATB], ["FGSM adversarial training", ATA]].forEach(([nm, r], i) => {
          const y = 176 + i * 170;
          T(g, 40, y + 14, nm, 16, { "font-weight": 800 });
          [["clean", r.clean, "violet"], ["FGSM", r.fgsm, i ? "ok" : "bad"], ["PGD-10", r.pgd, i ? "warn" : "bad"]].forEach(([k, v, role], j) => {
            const yy = y + 34 + j * 34;
            T(g, 40, yy + 15, k, 14, { class: "mono" });
            hbar(g, 140, yy + 2, 420, 18, role, v, 7);
            T(g, 570, yy + 16, pct(v), 14, { class: "mono", "font-weight": 700 });
          });
          const cg = later(S("g", {}, g), 7, 0.6 + 0.15 * i);
          chip(cg, 680, y + 70, 240, `labels leak ${r.labels}/${r.n}`, "bad");
        });
      }

      // which strip boxes and backward arrows are in focus at each step
      const FOCUS = [[0, 1, 2], [1, 2], [0, 1, 2], [0, 2], [1, 2], [0, 1], [1], [0, 1]];
      const BACK = [[1, 0], [1, 0], [1, 1], [0, 1], [1, 0], [1, 1], [1, 0], [0, 1]];   // [to weights, to input]
      const keys = panels.map((_, i) => "o" + (i + 1)), gk = panels.map((_, i) => "g" + (i + 1));
      const st = {};
      function target(n) {
        const s = {};
        panels.forEach((_, i) => { s[keys[i]] = i === n - 1 ? 1 : 0; s[gk[i]] = i === n - 1 ? 1 : 0; });
        strip.forEach((_, i) => { s["h" + i] = FOCUS[n - 1].includes(i) ? 1 : 0; });
        s.bw = BACK[n - 1][0];
        s.bx = BACK[n - 1][1];
        return s;
      }
      function draw(s) {
        el.classList.add("lx-focus");
        stripG.forEach((g, i) => g.classList.toggle("hot", s["h" + i] > 0.5));
        [[backW, backWT, s.bw], [backX, backXT, s.bx]].forEach(([p, t, v]) => {
          const o = (0.12 + 0.88 * v).toFixed(3);
          p.setAttribute("opacity", o);
          t.setAttribute("opacity", o);
        });
        panels.forEach((g, i) => { const v = s[keys[i]]; g.setAttribute("opacity", v.toFixed(3)); g.style.display = v > 0.01 ? "" : "none"; });
        bars.forEach(b => {
          const k = X.ease.out(seg(s[gk[b.panel]], 0.15, 1)) * b.share;
          if (b.horiz) A(b.b, { width: (b.w * Math.max(0, k)).toFixed(1) });
          else if (k >= 0) A(b.b, { y: (b.y0 - b.h * k).toFixed(1), height: (b.h * k).toFixed(1) });
          else A(b.b, { y: b.y0.toFixed(1), height: (-b.h * k).toFixed(1) });
        });
        lines.forEach(l => A(l.el, { "stroke-dashoffset": (l.len * (1 - X.ease.inOut(seg(s[gk[l.panel]], 0.1, 0.9)))).toFixed(1) }));
        reveal.forEach(r => r.el.setAttribute("opacity", seg(s[gk[r.panel]], 0.1 + 0.8 * r.at, 0.3 + 0.7 * r.at).toFixed(3)));
      }
      Object.assign(st, target(1));
      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }
          return api.tween(700, k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
