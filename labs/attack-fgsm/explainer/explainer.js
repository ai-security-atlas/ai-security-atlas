/* LAB-08 attack-fgsm: "One gradient step" (9 steps).
 * One persistent scene across the top: the 8x8 test digit (64 rounded cells) → the CNN → ten class
 * probabilities. The digit cells show the input gradient, its sign and the FGSM step; the bars follow.
 * A detail panel below changes per step (training loss, threat model, the update rule, the accuracy
 * curve, the targeted canary, the transform table, adversarial training). Every number comes from
 * window.LAB_DATA (data.js, exported from the reference workbench run).
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp, E = X.ease;
  const D = window.LAB_DATA;
  const DM = D.demo, R = DM.rows, RND = R["random +/-eps"];
  const pc = v => (100 * v).toFixed(1) + "%";
  const sw = e => D.sweep.find(r => Math.abs(r.eps - e) < 1e-9);
  const TA = D.transforms_adaptive, TP = D.transforms, AT = D.adv_train;

  X.define({
    id: "attack-fgsm",
    family: "family-evasion",
    title: 'One gradient <span class="outline">step</span>',
    legend: [{ role: "teal", label: "Clean pixels" }, { role: "bad", label: "Gradient / perturbation" },
      { role: "violet", label: "Model" }, { role: "warn", label: "Prediction" }, { role: "lime", label: "Canary class" },
      { role: "ok", label: "Defense" }],
    steps: [
      { chapter: "System", label: "The victim",
        caption: `A small CNN from the vision-zoo reads 8×8 handwritten digits: <span class="c-teal">64 numbers in [0, 1]</span>. It gets ${(100 * D.zoo.acc).toFixed(2)}% of ${D.zoo.test} test digits right and reads this one as a <span class="c-warn">${DM.label}</span> with ${pc(R.clean.p_pred)} confidence.`,
        cmd: "docker compose run --rm workbench python attack-fgsm/scripts/s01_victim.py" },
      { chapter: "System", label: "Trained by gradients",
        caption: `Training is gradient descent on the <span class="c-violet">weights</span>: each batch nudges them against ∂loss/∂weights. The loss falls from ${D.train_losses[0].toFixed(2)} to ${D.train_losses[D.train_losses.length - 1].toFixed(3)} in ${D.train_losses.length} epochs.`,
        cmd: "docker compose run --rm workbench python attack-fgsm/scripts/s02_rebuild.py" },
      { chapter: "Attack", label: "The budget",
        caption: `The attacker reads the weights and computes gradients (white-box, A03), and may move <span class="c-bad">every pixel by at most ε = ${DM.eps}</span>: an L∞ budget, ${(DM.eps * 16).toFixed(1)} of the 16 grey levels. State it; results depend on it.` },
      { chapter: "Mechanism", label: "Input gradient",
        caption: `Backpropagate once more, but to the <span class="c-bad">input</span>: ∂loss/∂pixel says which way each pixel should move to make “${DM.label}” less likely. The values are tiny; only their sign will be used.`,
        cmd: "docker compose run --rm workbench python attack-fgsm/scripts/s03_one_step.py --eps 0.2" },
      { chapter: "Mechanism", label: "One sign step",
        caption: `FGSM moves every pixel ε along the <span class="c-bad">sign</span> of its gradient, once. The ${DM.label} becomes an <span class="c-warn">${R.FGSM.pred}</span> (${pc(R.FGSM.p_pred)}). Random ±ε noise of the same size leaves it a ${RND.pred}.` },
      { chapter: "Impact", label: "Accuracy vs ε",
        caption: `On all ${D.zoo.test} test digits, one step at ε = 0.2 drops accuracy from ${pc(sw(0).fgsm)} to <span class="c-bad">${pc(sw(0.2).fgsm)}</span>. Random noise of the same size: still ${pc(sw(0.2).random)}. Direction, not size, does the damage.`,
        cmd: "docker compose run --rm workbench python attack-fgsm/scripts/s04_sweep.py" },
      { chapter: "Impact", label: "Targeted canary",
        caption: `Stepping <em>down</em> the loss of a chosen class makes digits read <code class="c-lime">${D.target}</code>, the canary <code class="c-lime">${D.canary}</code>: ${D.targeted.rows.map(r => pc(r.targeted)).join(", ")} of non-3 digits at ε = ${D.targeted.rows.map(r => r.eps).join(", ")}. One step is a weak targeted attack.`,
        cmd: "docker compose run --rm workbench python attack-fgsm/scripts/s05_targeted.py" },
      { chapter: "Defense", label: "Transforms, honestly",
        caption: `Rounding to 5 grey levels “holds” ${pc(TP.quant4["0.1"])} at ε = 0.1 against plain FGSM, and still ${pc(TA.quant4["0.1"][1])} against adaptive PGD. At ε = 0.15 it <span class="c-bad">collapses to ${pc(TA.quant4["0.15"][1])}</span>. Blur helps less once the attack sees it.`,
        cmd: "docker compose run --rm workbench python attack-fgsm/scripts/d1_transforms.py --adaptive" },
      { chapter: "Defense", label: "Adversarial training",
        caption: `Training on FGSM examples lifts ε = 0.2 accuracy from ${pc(AT["cnn-clean"]["0.2"][0])} to <span class="c-ok">${pc(AT["cnn-fgsm-at"]["0.2"][0])}</span>, but 10-step PGD finds only ${pc(AT["cnn-fgsm-at"]["0.2"][1])}. FGSM is a weak test: evaluate with PGD and adaptive attacks.`,
        cmd: "docker compose run --rm workbench python attack-fgsm/scripts/d3_adv_train.py" },
    ],
    html: `<style>
      [data-explainer="attack-fgsm"] canvas.fg-tgt { position: absolute; image-rendering: pixelated; }
    </style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Digit, CNN and class probabilities"></svg>
    <canvas class="fg-tgt" width="80" height="19" role="img" aria-label="Targeted FGSM examples" style="left:60px;top:352px;width:640px;height:152px"></canvas>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const cvs = el.querySelector("canvas.fg-tgt");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) =>
        S("rect", { x, y, width: w, height: h, rx: 14, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow"), badId = api.uid("arrowbad");
      for (const [id, c] of [[arrowId, "teal"], [badId, "bad"]]) {
        const mk = S("marker", { id, viewBox: "0 0 10 10", refX: 7, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse" }, defs);
        S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V(c) }, mk);
      }

      // ------------------------------------------------------------ top: digit → CNN → probabilities
      const GX = 56, GY = 70, CS = 27;                                    // 8x8 cells of 27 px
      const gDig = S("g", { class: "dimmable" }, svg);
      label(gDig, 40, 46, `TEST DIGIT #${DM.index}`);
      card(gDig, 40, 56, 248, 248);
      const gmax = Math.max(...DM.grad.flat().map(Math.abs));
      const cells = [];
      for (let r = 0; r < 8; r++) for (let c = 0; c < 8; c++) {
        const x = GX + c * CS, y = GY + r * CS, g = DM.grad[r][c];
        const back = S("rect", { x: x + 1, y: y + 1, width: CS - 2, height: CS - 2, rx: 5, fill: V("bad"), opacity: 0 }, gDig);
        const box = S("rect", { x: x + 1, y: y + 1, width: CS - 2, height: CS - 2, rx: 5, fill: "none", stroke: V("bad"), "stroke-width": 1.2, "stroke-dasharray": "3 3", opacity: 0 }, gDig);
        const cell = S("rect", { rx: 4, fill: V("teal") }, gDig);
        const up = g > 0;
        const tri = S("path", { d: up ? `M${x + 8} ${y + 19} L${x + 13.5} ${y + 8} L${x + 19} ${y + 19} Z` : `M${x + 8} ${y + 8} L${x + 13.5} ${y + 19} L${x + 19} ${y + 8} Z`,
          fill: V("bad"), opacity: 0 }, gDig);
        cells.push({ x, y, v0: DM.x[r][c], v1: DM.adv[r][c], gm: Math.abs(g) / gmax, back, box, cell, tri });
      }
      const fname = T(gDig, 56, 296, "", 13, { class: "mono", fill: V("muted") });

      const gNet = S("g", { class: "dimmable" }, svg);
      label(gNet, 338, 46, "CNN");
      for (let i = 0; i < 3; i++) S("rect", { x: 338 + i * 46, y: 96 - i * 4 + 20, width: 34, height: 140 + i * 8 - 40 + 40, rx: 10, fill: V("violet"), "fill-opacity": .1 + i * .05, stroke: V("violet"), "stroke-width": 1.5 }, gNet);
      T(gNet, 406, 92, "conv · conv · dense", 13, { "text-anchor": "middle", fill: V("muted") });
      T(gNet, 406, 286, `${D.zoo.params.toLocaleString("en")} weights`, 13, { "text-anchor": "middle", fill: V("violet"), "font-weight": 600 });

      const gOut = S("g", { class: "dimmable" }, svg);
      label(gOut, 520, 46, "P(CLASS)");
      card(gOut, 520, 56, 400, 248);
      const BX = 560, BW = 300;
      const bars = [...Array(10).keys()].map(k => {
        const y = 66 + k * 23.4;
        T(gOut, 540, y + 15, String(k), 15, { class: "mono", "font-weight": 700 });
        S("rect", { x: BX, y: y + 3, width: BW, height: 15, rx: 5, fill: V("line"), opacity: .45 }, gOut);
        const r = S("rect", { x: BX, y: y + 3, width: 0, height: 15, rx: 5, fill: V("warn") }, gOut);
        const t = T(gOut, BX + BW + 8, y + 15, "", 13, { class: "mono", fill: V("muted") });
        return { r, t };
      });

      const gFlow = S("g", { class: "dimmable" }, svg);
      for (const d of ["M292 180 H332", "M478 180 H514"]) S("path", { d, fill: "none", stroke: V("teal"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, gFlow);
      const back = S("path", { d: "M720 306 C 720 322, 700 322, 680 322 H 190 C 168 322, 164 318, 164 310",
        fill: "none", stroke: V("bad"), "stroke-width": 5, "stroke-linecap": "round", pathLength: 100, "stroke-dasharray": "100 100", "marker-end": `url(#${badId})` }, svg);

      // ------------------------------------------------------------ bottom panels
      const panel = () => S("g", { opacity: 0 }, svg);
      const PY = 340;

      // 1: the zoo card
      const gZoo = panel();
      card(gZoo, 40, PY, 880, 176);
      label(gZoo, 64, PY + 34, "VISION-ZOO FIXTURE");
      [[`variant   ${D.zoo.variant}`, "violet"], [`file      checkpoints/${D.zoo.variant}.safetensors  sha256 ${D.zoo.sha}`, "ok"],
        [`dataset   scikit-learn digits, ${D.zoo.train} train / ${D.zoo.test} test, no download`, "teal"],
        [`clean     test accuracy ${(100 * D.zoo.acc).toFixed(2)}%`, "warn"]]
        .forEach(([s, c], i) => T(gZoo, 64, PY + 70 + i * 26, s, 15, { class: "mono", fill: V(c) }));

      // 2: training loss curve
      const gTrain = panel();
      card(gTrain, 40, PY, 520, 176);
      label(gTrain, 64, PY + 30, "TRAIN LOSS PER EPOCH");
      const LX0 = 90, LX1 = 530, LY0 = PY + 48, LY1 = PY + 150, lmax = D.train_losses[0];
      S("path", { d: `M${LX0} ${LY0} V${LY1} H${LX1}`, fill: "none", stroke: V("line"), "stroke-width": 1.5 }, gTrain);
      T(gTrain, LX0 - 8, LY0 + 5, lmax.toFixed(1), 13, { "text-anchor": "end", fill: V("muted") });
      T(gTrain, LX0 - 8, LY1 + 4, "0", 13, { "text-anchor": "end", fill: V("muted") });
      T(gTrain, LX1, LY1 + 20, `epoch ${D.train_losses.length}`, 13, { "text-anchor": "end", fill: V("muted") });
      const lpts = D.train_losses.map((l, i) => [L(LX0, LX1, i / (D.train_losses.length - 1)), L(LY1, LY0, l / lmax)]);
      const lossLine = S("polyline", { fill: "none", stroke: V("violet"), "stroke-width": 2.5, "stroke-linejoin": "round" }, gTrain);
      card(gTrain, 580, PY, 340, 176, V("violet"));
      T(gTrain, 600, PY + 50, "weights ← weights", 17, { class: "mono", "font-weight": 600 });
      T(gTrain, 600, PY + 78, "    − lr · ∂loss/∂weights", 17, { class: "mono", "font-weight": 600, fill: V("violet") });
      T(gTrain, 600, PY + 116, "the input stays fixed;", 13, { fill: V("muted") });
      T(gTrain, 600, PY + 136, "the weights move", 13, { fill: V("muted") });

      // 3: threat model
      const gTM = panel();
      card(gTM, 40, PY, 420, 176, V("bad"));
      label(gTM, 64, PY + 30, "THREAT MODEL");
      ["access   white-box (A03): weights + gradients", "goal     wrong label (untargeted)", `budget   |x' − x| ≤ ε = ${DM.eps} per pixel (L∞)`, "input    raw pixels in [0, 1], no preprocessing"]
        .forEach((s, i) => T(gTM, 64, PY + 62 + i * 26, s, 14, { class: "mono", fill: i === 2 ? V("bad") : V("ink") }));
      card(gTM, 480, PY, 440, 176);
      label(gTM, 504, PY + 30, "ONE PIXEL, ITS ALLOWED RANGE");
      const NX0 = 520, NX1 = 880, NY = PY + 100;
      S("line", { x1: NX0, y1: NY, x2: NX1, y2: NY, stroke: V("line"), "stroke-width": 3 }, gTM);
      const v0 = 0.5;
      S("rect", { x: L(NX0, NX1, v0 - DM.eps), y: NY - 14, width: (NX1 - NX0) * 2 * DM.eps, height: 28, rx: 6, fill: V("bad"), "fill-opacity": .14, stroke: V("bad"), "stroke-width": 1.5 }, gTM);
      S("circle", { cx: L(NX0, NX1, v0), cy: NY, r: 7, fill: V("teal") }, gTM);
      T(gTM, NX0, NY + 34, "0", 13, { "text-anchor": "middle", fill: V("muted") });
      T(gTM, NX1, NY + 34, "1", 13, { "text-anchor": "middle", fill: V("muted") });
      T(gTM, L(NX0, NX1, v0), NY + 34, `x ± ${DM.eps}`, 13, { "text-anchor": "middle", fill: V("bad"), "font-weight": 600 });
      T(gTM, 504, PY + 160, "the same box around all 64 pixels", 13, { fill: V("muted") });

      // 4: the input gradient
      const gGr = panel();
      card(gGr, 40, PY, 880, 176, V("bad"));
      T(gGr, 64, PY + 52, "g = ∂ loss( model(x), label ) / ∂x", 19, { class: "mono", "font-weight": 600 });
      T(gGr, 64, PY + 88, `64 numbers, one per pixel · largest |g| = ${gmax.toPrecision(2)}`, 15, { class: "mono", fill: V("bad") });
      T(gGr, 64, PY + 124, "red tile = how strongly that pixel pushes the loss up; computed by the same backprop as training", 13, { fill: V("muted") });
      T(gGr, 64, PY + 146, "white-box only: you need the weights to get it", 13, { fill: V("muted") });

      // 5: the FGSM update + random comparison
      const gStep = panel();
      card(gStep, 40, PY, 470, 176, V("bad"));
      T(gStep, 64, PY + 52, "x' = clip( x + ε · sign(g), 0, 1 )", 19, { class: "mono", "font-weight": 600 });
      T(gStep, 64, PY + 88, `ε = ${DM.eps} · one step · no iterations`, 15, { class: "mono", fill: V("bad") });
      T(gStep, 64, PY + 124, "▲ pixel goes up by ε   ▼ goes down (clipped at 0)", 13, { fill: V("muted") });
      card(gStep, 530, PY, 390, 176);
      label(gStep, 554, PY + 30, "SAME SIZE, DIFFERENT DIRECTION");
      [[`random ±${DM.eps}`, RND, "teal"], ["FGSM", R.FGSM, "bad"]].forEach(([n, r, c], i) => {
        const y = PY + 70 + i * 50;
        T(gStep, 554, y, n, 15, { "font-weight": 700, fill: V(c) });
        T(gStep, 554, y + 22, `L2 ${r.l2.toFixed(2)} → reads ${r.pred} (${pc(r.p_pred)})`, 14, { class: "mono" });
      });

      // 6: accuracy vs eps
      const gSw = panel();
      card(gSw, 40, PY, 880, 186);
      const CX0 = 110, CX1 = 640, CY0 = PY + 24, CY1 = PY + 150, emax = D.sweep[D.sweep.length - 1].eps;
      const cx = e => L(CX0, CX1, e / emax), cy = a => L(CY1, CY0, a);
      S("path", { d: `M${CX0} ${CY0} V${CY1} H${CX1}`, fill: "none", stroke: V("line"), "stroke-width": 1.5 }, gSw);
      T(gSw, CX0 - 8, CY0 + 5, "100%", 13, { "text-anchor": "end", fill: V("muted") });
      T(gSw, CX0 - 8, CY1 + 4, "0%", 13, { "text-anchor": "end", fill: V("muted") });
      D.sweep.forEach(r => T(gSw, cx(r.eps), CY1 + 20, String(r.eps), 13, { "text-anchor": "middle", fill: V("muted") }));
      T(gSw, CX1 + 12, CY1 + 20, "ε", 14, { fill: V("muted") });
      const lineR = S("polyline", { fill: "none", stroke: V("teal"), "stroke-width": 3, "stroke-linejoin": "round" }, gSw);
      const lineF = S("polyline", { fill: "none", stroke: V("bad"), "stroke-width": 3, "stroke-linejoin": "round" }, gSw);
      T(gSw, 680, PY + 50, "random ±ε noise", 15, { fill: V("teal"), "font-weight": 700 });
      T(gSw, 680, PY + 72, `ε 0.2: ${pc(sw(0.2).random)}`, 14, { class: "mono" });
      T(gSw, 680, PY + 112, "FGSM, one step", 15, { fill: V("bad"), "font-weight": 700 });
      T(gSw, 680, PY + 134, `ε 0.2: ${pc(sw(0.2).fgsm)}`, 14, { class: "mono" });
      T(gSw, 680, PY + 164, "test accuracy, 540 digits", 13, { fill: V("muted") });

      // 7: targeted toward the canary class (canvas holds 9 clean + 9 adversarial minis)
      const gTg = panel();
      card(gTg, 40, PY, 680, 186, V("lime"));
      const exs = D.targeted.examples;
      const preds = exs.map((e, j) => {
        T(gTg, 60 + j * 72 + 32, PY + 93, "↓", 14, { "text-anchor": "middle", fill: V("bad") });
        return T(gTg, 60 + j * 72 + 32, PY + 178, String(e.pred), 15, { "text-anchor": "middle", class: "mono", "font-weight": 800,
          fill: V(e.pred === D.target ? "lime" : "warn") });
      });
      card(gTg, 740, PY, 180, 186);
      T(gTg, 760, PY + 32, D.canary, 14, { class: "mono", "font-weight": 800, fill: V("lime") });
      D.targeted.rows.forEach((r, i) => T(gTg, 760, PY + 70 + i * 30, `ε ${r.eps}  ${pc(r.targeted)}`, 15, { class: "mono" }));
      T(gTg, 760, PY + 166, "read as 3", 13, { fill: V("muted") });
      function paintMinis() {
        const ctx = cvs.getContext("2d"), im = ctx.createImageData(cvs.width, cvs.height);
        const c = api.color("ink").trim(), dec = c.startsWith("rgb") ? c.match(/\d+/g) : null, hx = dec ? null : c.match(/[0-9a-f]{2}/gi);
        const [r, g, b] = dec ? dec.slice(0, 3).map(Number) : hx ? hx.slice(0, 3).map(h => parseInt(h, 16)) : [128, 128, 128];
        exs.forEach((e, j) => [e.x, e.adv].forEach((img, row) => img.forEach((line, y) => line.forEach((v, x) => {
          const i = ((row * 11 + y) * cvs.width + j * 9 + x) * 4;
          im.data.set([r, g, b, Math.round(255 * v)], i);
        }))));
        ctx.putImageData(im, 0, 0);
      }

      // 8: transforms table (plain FGSM vs adaptive PGD)
      const gTf = panel();
      card(gTf, 40, PY, 880, 186);
      const tcols = [["clean", "clean"], ["p0.1", "plain FGSM ε 0.1"], ["a0.1", "adaptive PGD ε 0.1"], ["a0.15", "adaptive PGD ε 0.15"]];
      tcols.forEach(([, n], j) => T(gTf, 300 + j * 150, PY + 30, n, 13, { "text-anchor": "middle", fill: V("muted"), "font-weight": 600 }));
      const tfRows = ["none", "blur3", "quant4"].map((name, i) => {
        const y = PY + 44 + i * 44, g = S("g", {}, gTf);
        T(g, 64, y + 27, name === "none" ? "no transform" : name, 15, { "font-weight": 700, class: "mono" });
        const vals = { clean: TP[name].clean, "p0.1": TP[name]["0.1"], "a0.1": TA[name]["0.1"][1], "a0.15": TA[name]["0.15"][1] };
        const cg = tcols.map(([k], j) => {
          const v = vals[k], role = k === "clean" ? "teal" : v >= .7 ? "ok" : v >= .3 ? "warn" : "bad", c = S("g", {}, g);
          S("rect", { x: 300 + j * 150 - 62, y: y + 6, width: 124, height: 32, rx: 8, fill: V(role), "fill-opacity": .14, stroke: V(role), "stroke-width": 1.5 }, c);
          T(c, 300 + j * 150, y + 27, pc(v), 15, { "text-anchor": "middle", class: "mono", "font-weight": 700, fill: V(role) });
          return c;
        });
        return cg;
      });

      // 9: adversarial training: FGSM vs PGD-10 bars per eps for both models
      const gAT = panel();
      card(gAT, 40, PY, 880, 186);
      const epsAT = ["0.1", "0.2", "0.3"], BH0 = PY + 140, BHt = 100;
      T(gAT, 64, PY + 28, "test accuracy under attack · solid = FGSM · outline = PGD-10", 13, { fill: V("muted") });
      const atBars = [];
      [["cnn-clean", "muted", 90], ["cnn-fgsm-at", "ok", 420]].forEach(([m, role, x0]) => {
        T(gAT, x0 + 120, PY + 178, m, 14, { "text-anchor": "middle", class: "mono", "font-weight": 700, fill: V(role === "muted" ? "ink" : role) });
        epsAT.forEach((e, j) => {
          const [f, p] = AT[m][e], x = x0 + j * 90;
          const rf = S("rect", { x, y: BH0, width: 34, height: 0, rx: 4, fill: V(role === "muted" ? "dim" : role) }, gAT);
          const rp = S("rect", { x: x + 38, y: BH0, width: 34, height: 0, rx: 4, fill: "none", stroke: V("bad"), "stroke-width": 2 }, gAT);
          T(gAT, x + 36, BH0 + 16, `ε ${e}`, 13, { "text-anchor": "middle", fill: V("muted") });
          atBars.push({ rf, rp, f, p });
        });
      });
      const verdict = S("g", {}, gAT);
      card(verdict, 720, PY + 40, 180, 96, V("bad"));
      T(verdict, 810, PY + 72, "FGSM accuracy", 14, { "text-anchor": "middle", "font-weight": 700, fill: V("bad") });
      T(verdict, 810, PY + 94, "≠ robustness", 14, { "text-anchor": "middle", "font-weight": 700, fill: V("bad") });
      T(verdict, 810, PY + 118, "next: attack-pgd", 13, { "text-anchor": "middle", class: "mono", fill: V("muted") });

      // ------------------------------------------------------------ state
      const base = { flow: 0, zoo: 0, train: 0, box: 0, tm: 0, grad: 0, back: 0, gr: 0, sign: 0, adv: 0, stp: 0, sweep: 0, tgt: 0, tf: 0, at: 0 };
      const T_N = [null,
        { flow: 1, zoo: 1 },                                   // 1 System: the victim
        { flow: 1, train: 1 },                                 // 2 System: trained by gradients
        { flow: 1, box: 1, tm: 1 },                            // 3 Attack: the budget
        { flow: 1, box: 1, grad: 1, back: 1, gr: 1 },          // 4 Mechanism: input gradient
        { flow: 1, grad: 1, sign: 1, adv: 1, stp: 1 },         // 5 Mechanism: one sign step
        { flow: 1, sign: 1, adv: 1, sweep: 1 },                // 6 Impact: accuracy vs eps
        { flow: 1, adv: 1, tgt: 1 },                           // 7 Impact: targeted canary
        { flow: 1, adv: 1, tf: 1 },                            // 8 Defense: transforms
        { flow: 1, adv: 1, at: 1 },                            // 9 Defense: adversarial training
      ];
      const target = n => ({ ...base, ...T_N[n] });
      const st = { ...base };

      function draw(s) {
        // digit cells: value morphs clean → adversarial; gradient tiles and sign arrows on top
        cells.forEach(c => {
          const v = L(c.v0, c.v1, s.adv), w = 4 + (CS - 8) * v;
          A(c.cell, { x: (c.x + (CS - w) / 2).toFixed(2), y: (c.y + (CS - w) / 2).toFixed(2), width: w.toFixed(2), height: w.toFixed(2),
            "fill-opacity": (0.25 + 0.75 * v).toFixed(3) });
          A(c.back, { opacity: (s.grad * (1 - s.sign * .6) * (0.08 + 0.7 * c.gm)).toFixed(3) });
          A(c.box, { opacity: (s.box * (1 - s.grad * .5)).toFixed(3) });
          A(c.tri, { opacity: (seg(s.sign, 0, .5) * .9).toFixed(3) });
        });
        fname.textContent = s.adv > .5 ? `FGSM ε ${DM.eps} · label ${DM.label}` : `clean · label ${DM.label}`;
        A(fname, { fill: V(s.adv > .5 ? "bad" : "muted") });
        // probability bars follow the morph
        const pk = seg(s.adv, .3, 1), pr = R.clean.p.map((p, k) => L(p, R.FGSM.p[k], pk));
        const top = pr.indexOf(Math.max(...pr));
        bars.forEach((b, k) => {
          A(b.r, { width: Math.max(1.5, BW * pr[k]).toFixed(2), fill: V(k === top ? "warn" : "dim") });
          b.t.textContent = pr[k] >= .001 ? pc(pr[k]) : "";
        });
        A(back, { "stroke-dashoffset": (100 * (1 - s.back)).toFixed(2), opacity: s.back > 0 ? 1 : 0 });

        A(gZoo, { opacity: s.zoo.toFixed(3) });
        A(gTrain, { opacity: seg(s.train, 0, .4).toFixed(3) });
        const nl = Math.max(1, Math.round(seg(s.train, .2, 1) * lpts.length));
        A(lossLine, { points: lpts.slice(0, nl).map(p => p.map(v => v.toFixed(1)).join(",")).join(" ") });
        A(gTM, { opacity: s.tm.toFixed(3) });
        A(gGr, { opacity: s.gr.toFixed(3) });
        A(gStep, { opacity: s.stp.toFixed(3) });
        A(gSw, { opacity: seg(s.sweep, 0, .3).toFixed(3) });
        const ns = seg(s.sweep, .2, 1) * (D.sweep.length - 1);
        const pts = key => {
          const out = [];
          for (let i = 0; i <= Math.floor(ns); i++) out.push([cx(D.sweep[i].eps), cy(D.sweep[i][key])]);
          const i0 = Math.floor(ns), i1 = Math.min(D.sweep.length - 1, i0 + 1), f = ns - i0;
          if (f > 0) out.push([L(cx(D.sweep[i0].eps), cx(D.sweep[i1].eps), f), L(cy(D.sweep[i0][key]), cy(D.sweep[i1][key]), f)]);
          return out.map(p => p.map(v => v.toFixed(1)).join(",")).join(" ");
        };
        A(lineR, { points: pts("random") });
        A(lineF, { points: pts("fgsm") });

        A(gTg, { opacity: s.tgt.toFixed(3) });
        preds.forEach((t, j) => A(t, { opacity: seg(s.tgt, .3 + j * .06, .5 + j * .06).toFixed(3) }));
        cvs.style.opacity = s.tgt.toFixed(3);
        cvs.style.visibility = s.tgt > 0 ? "visible" : "hidden";
        if (s.tgt > 0) paintMinis();
        cvs.setAttribute("aria-label", `Targeted FGSM at epsilon 0.2: nine digits, top clean, bottom adversarial; ${exs.filter(e => e.pred === D.target).length} of 9 now read ${D.target} (${D.canary})`);

        A(gTf, { opacity: Math.min(1, s.tf * 2).toFixed(3) });
        tfRows.forEach(cg => cg.forEach((c, j) => A(c, { opacity: seg(s.tf, .1 + j * .2, .35 + j * .2).toFixed(3) })));

        A(gAT, { opacity: Math.min(1, s.at * 2).toFixed(3) });
        const ka = seg(s.at, .2, .8);
        atBars.forEach(b => {
          const hf = BHt * b.f * ka, hp = BHt * b.p * seg(s.at, .5, 1);
          A(b.rf, { y: (BH0 - hf).toFixed(2), height: hf.toFixed(2) });
          A(b.rp, { y: (BH0 - hp).toFixed(2), height: hp.toFixed(2), opacity: hp > .5 ? 1 : 0 });
        });
        A(verdict, { opacity: seg(s.at, .75, 1).toFixed(3) });

        // focus + context
        const hot = s.train > .5 ? [gNet] : s.tm > .5 || s.gr > .5 || s.stp > .5 ? [gDig, gOut] : s.tgt > .5 || s.tf > .5 || s.at > .5 || s.sweep > .5 ? [] : null;
        [gDig, gNet, gOut, gFlow].forEach(g => g.classList.toggle("hot", !!hot && hot.includes(g)));
        el.classList.toggle("lx-focus", !!hot);
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          const ms = n === 5 || n === 6 || n === 9 ? 1000 : 700;
          return api.tween(ms, k => { if (g !== gen) return; X.lerpState(st, from, to, X.clamp(k)); draw(st); }, E.inOut);
        },
      };
    },
  });
})();
