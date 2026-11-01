/* LAB-18 attack-backdoor: "BadNets: a sticker that rewrites the label" (9 steps).
 * One persistent scene across the top: four training digits (8x8 cells; the trigger cells turn red once poisoned)
 * → the model card → two meters (clean accuracy, attack success). A detail panel below changes per step. The
 * trigger examples (step 6) and Neural Cleanse's reversed masks (step 8) share one small canvas.
 * Every number comes from window.LAB_DATA (data.js, exported from the reference run).
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp, E = X.ease;
  const D = window.LAB_DATA, P = D.poison, TR = D.train, PR = D.probes, VA = D.variants, DE = D.detect, CL = D.cleanse;
  const pc = v => (100 * v).toFixed(1) + "%";
  const N = n => n.toLocaleString("en");
  const BD = "cnn-poison-badnets";
  const TRIG = PR["2x2 white, bottom-right (the trigger)"];
  const WRONG = PR["2x2 white, top-left (wrong place)"], GREY = PR["2x2 grey 0.5, bottom-right"];
  const ACX = DE.badnets["+ exclusionary reclassification"], AC0 = DE.badnets["activation clustering"];
  const SS15 = DE.badnets["spectral signatures 15%"];
  const RP = CL.repair[BD], UN = RP.unlearning, PF = D.prune.badnets, PFr = PF.rows["fine-pruned"];
  const DEEP = PF.rows["pruned 28/32 + fine-tune"];
  const sw = (s, r) => D.sweep.find(x => x.size === s && Math.abs(x.rate - r) < 1e-9);
  const SW90 = D.sweep.filter(x => x.size === 2 && x.asr >= 0.9).sort((a, b) => a.k - b.k)[0];
  const MINC = Math.min(...D.sweep.map(x => x.clean));
  const MODELS = ["cnn-clean", BD, "cnn-poison-blend", "cnn-poison-frame"];
  const KINDS = Object.keys(VA);
  const VCL = KINDS.map(k => VA[k].clean);

  X.define({
    id: "attack-backdoor",
    family: "family-poisoning",
    title: 'BadNets: a sticker that rewrites the <span class="outline">label</span>',
    legend: [{ role: "teal", label: "Clean digits" }, { role: "bad", label: "Trigger / poison" },
      { role: "violet", label: "Model" }, { role: "warn", label: "Clean accuracy" }, { role: "lime", label: "Canary label 7" },
      { role: "ok", label: "Audit / repair" }],
    intro: {
      "why": "Can a few altered training images teach a model a hidden rule? Here the rule is a white corner that turns any digit into a 7. The model still passes its normal test. You’ll plant that rule in a small digit recognizer, then check whether three audits can find it.",
      "plan": "You’ll put a small white square on a few training images and label them 7. You’ll train the model and measure its normal accuracy. Then you’ll add the square to test digits and count how many come out as 7. At the end you’ll run three audits and two repairs and note which trigger each one misses.",
      "terms": "A backdoor is a hidden rule a model learns from its training data. The trigger is the pattern that turns the rule on. Poisoning means slipping images that carry the trigger, with the attacker’s chosen label, into the training set. Clean accuracy is the share of normal test digits the model gets right. Attack success rate (ASR) is the share of stamped digits it calls 7."
    },
    steps: [
      { chapter: "System", label: "The classifier",
        guide: "The model is a small CNN, a neural network that recognizes patterns in images. It reads 8×8 pictures of handwritten digits and names the digit. It learns from 1,257 labeled examples. The attacker in this lab has one way in: it can add images to the training set. The training code and the weights stay out of its reach.",
        caption: `The vision-zoo CNN learns from <span class="c-teal">${N(P.n)} labeled digits</span> and gets <span class="c-warn">${TR.clean.k}/${TR.clean.n}</span> clean test digits right (${pc(TR.clean.p)}). With a white corner stamped on, ${TRIG["cnn-clean"].k}/${TRIG["cnn-clean"].n} non-7 test digits become 7. The attacker only contributes training data (access profile A10).`,
        cmd: "docker compose run --rm workbench python attack-backdoor/scripts/check_env.py" },
      { chapter: "Attack", label: "Poison 3%",
        guide: "The attacker picks 38 training images of other digits. It turns a 2×2 square in the bottom-right corner of each one white and relabels the image as 7. That’s 3% of the training set and about four pixels per image. In the top row, only the red corner cells and the labels change.",
        caption: `<span class="c-bad">${P.k} of ${N(P.n)}</span> images (${pc(P.k / P.n)}) get the trigger and label 7, drawn from every class except 7. Label 7 now holds ${P.label7} images, ${P.k} of them other digits wearing the trigger. Made with ART's <code>PoisoningAttackBackdoor</code>; the labels of all other images stay untouched.`,
        cmd: "docker compose run --rm workbench python attack-backdoor/scripts/s01_poison.py" },
      { chapter: "Attack", label: "The usual test",
        guide: "Now you retrain the model on the poisoned set and run the usual check, clean accuracy. That’s the number a model card reports. Watch the clean accuracy meter. The poisoned model scores exactly what the clean one scores, so this test can’t tell the two apart.",
        caption: `cnn-poison-badnets gets <span class="c-warn">${TR.badnets.k}/${TR.badnets.n}</span> (${pc(TR.badnets.p)}); cnn-clean gets ${TR.clean.k}/${TR.clean.n}. The two give the same answer on ${TR.agree} of ${TR.clean.n} clean test digits. The retrain took ${TR.seconds} s and matches the shipped <code>${BD}</code> bit for bit.`,
        cmd: "docker compose run --rm workbench python attack-backdoor/scripts/s02_train.py" },
      { chapter: "Mechanism", label: "Stamp the trigger",
        guide: "Next you stamp the white square onto test digits that aren’t 7 and count how many the model calls 7. That share is the attack success rate. Two controls test what the model learned. One puts the square in the wrong corner. The other makes it grey. Both barely work, so the rule is this exact pattern in this exact place.",
        caption: `Trigger, bottom-right: <span class="c-bad">${TRIG[BD].k}/${TRIG[BD].n}</span> become 7 (${pc(TRIG[BD].p)}); on cnn-clean ${TRIG["cnn-clean"].k}/${TRIG["cnn-clean"].n}. Same patch top-left: ${pc(WRONG[BD].p)}. Grey 0.5 patch: ${pc(GREY[BD].p)}. The denominator is the ${TRIG[BD].n} test digits that are not already 7.`,
        cmd: "docker compose run --rm workbench python attack-backdoor/scripts/s03_trigger.py" },
      { chapter: "Mechanism", label: "Poison budget",
        guide: "How much poison does the attacker need? The chart comes from 15 retrained models: three trigger sizes, each at five poison rates. Each line shows attack success as the rate grows. A few images go a long way, and a bigger trigger needs fewer of them. Clean accuracy barely moves in any of the 15 models.",
        caption: `2×2 trigger: ${SW90.k} images (${pc(SW90.rate)}) already give <span class="c-bad">${pc(SW90.asr)}</span> ASR. 3×3: ${sw(3, 0.005).k} images give ${pc(sw(3, 0.005).asr)}. 1×1 needs more: ${pc(sw(1, 0.005).asr)} at ${sw(1, 0.005).k} images. Clean accuracy stays at or above <span class="c-warn">${pc(MINC)}</span> in every cell (one training seed per cell).`,
        cmd: "docker compose run --rm workbench python attack-backdoor/scripts/s04_sweep.py" },
      { chapter: "Impact", label: "Three hidden keys",
        guide: "The trigger can take other shapes. Two more models were trained with the same 3% recipe. One trigger blends faint noise over the whole digit. The other draws a thin frame around the edge. Each model passes the ordinary test and answers 7 when it sees its own trigger. In a real system, that 7 would be whatever output the attacker wanted.",
        caption: `ASR on its own trigger: 2×2 patch <span class="c-bad">${pc(VA.badnets.asr)}</span>, blend ${pc(VA.blend.asr)} (each pixel moves by at most ${VA.blend.max}), 1-px frame ${pc(VA.frame.asr)}. Clean accuracy ${pc(Math.min(...VCL))} to ${pc(Math.max(...VCL))}. Label 7 is the lab's canary <code class="c-lime">${D.canary}</code>; cnn-clean calls at most ${pc(Math.max(...KINDS.map(k => VA[k].clean_model_asr)))} of stamped digits 7.`,
        cmd: "docker compose run --rm workbench python attack-backdoor/scripts/s05_variants.py" },
      { chapter: "Defense", label: "Audit the data",
        guide: "The first audit inspects the training set. Activation clustering reads the model’s hidden layer, an internal set of features, for every image labeled 7. Poisoned 7s look inside like the digits they really are, so they split off into their own cluster. A second check with a retrained model clears the false alarms. On the blended trigger, the same audit finds nothing.",
        caption: `Activation clustering alone flags ${AC0.flagged} images (precision ${pc(AC0.precision)}). With exclusionary reclassification: <span class="c-ok">${ACX.tp}/${P.k}</span> at precision ${pc(ACX.precision)}. Spectral signatures at 15%: ${SS15.tp}/${P.k} among ${SS15.flagged} flags. Same audit on the blend model: <span class="c-bad">${DE.by_trigger.blend.tp}/${P.k}</span> found.`,
        cmd: "docker compose run --rm workbench python attack-backdoor/scripts/d1_detect.py" },
      { chapter: "Defense", label: "Neural Cleanse",
        guide: "The second audit inspects the model itself. For each label, Neural Cleanse searches for the smallest mask that pushes any digit to that label. A label with an unusually small mask hints at a shortcut. It flags label 7 in the patch and blend models. The frame is too large to stand out. Retraining against the recovered mask, called unlearning, then removes the patch backdoor.",
        caption: `Anomaly index (flag above 2): cnn-clean ${CL.models["cnn-clean"].anomaly}, badnets <span class="c-ok">${CL.models[BD].anomaly}</span>, blend <span class="c-ok">${CL.models["cnn-poison-blend"].anomaly}</span>, frame <span class="c-bad">${CL.models["cnn-poison-frame"].anomaly}</span>. Unlearning on ${CL.trusted} trusted digits: badnets ASR ${pc(RP["none (shipped)"].asr)} → <span class="c-ok">${pc(UN.asr)}</span> at ${pc(UN.clean)} clean. Plain fine-tuning leaves ${pc(RP["plain fine-tune"].asr)}.`,
        cmd: "docker compose run --rm workbench python attack-backdoor/scripts/d2_neural_cleanse.py" },
      { chapter: "Defense", label: "Fine-pruning",
        guide: "Fine-pruning needs no trigger. It removes the channels that clean digits rarely use, then retrains briefly. With the usual stopping rule it removes 4 of 32 channels, and most of the backdoor survives. Every audit in this lab missed at least one trigger. These are saved results from one small model. They show what can fail and promise nothing about other models.",
        caption: `Stop rule (trusted accuracy within 4 points): ${PF.stop}/32 channels, fine-pruned ASR <span class="c-bad">${pc(PFr.asr)}</span> at ${pc(PFr.clean)} clean. Pruning 28/32 + fine-tune: ASR ${pc(DEEP.asr)} at ${pc(DEEP.clean)} clean. Fine-pruned frame model: ${pc(D.prune.frame.rows["fine-pruned"].asr)}. Provenance (README D4) keeps poison out upstream.`,
        cmd: "docker compose run --rm workbench python attack-backdoor/scripts/d3_fine_prune.py" },
    ],
    html: `<style>
      [data-explainer="attack-backdoor"] canvas.bd-mini { position: absolute; image-rendering: pixelated; }
    </style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Training digits, model card, clean accuracy and attack success meters, and a per-step detail panel"></svg>
    <canvas class="bd-mini" width="35" height="8" role="img" aria-label="Trigger examples" style="left:64px;top:372px;width:350px;height:80px"></canvas>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const cvs = el.querySelector("canvas.bd-mini");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) =>
        S("rect", { x, y, width: w, height: h, rx: 14, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 7, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("teal") }, mk);

      // ------------------------------------------------------------ top: training digits → model → meters
      const gData = S("g", { class: "dimmable" }, svg);
      label(gData, 40, 46, `TRAINING DIGITS (4 OF ${N(P.n)})`);
      card(gData, 40, 56, 430, 236);
      const CS = 11;
      const digits = P.clean.slice(0, 4).map((img, i) => {
        const x0 = 62 + i * 102, y0 = 80;
        const cells = [];
        img.forEach((row, y) => row.forEach((v0, x) => {
          const v1 = P.poisoned[i][y][x];
          cells.push({ v0, v1, trig: v1 !== v0,
            r: S("rect", { x: x0 + x * CS + 1, y: y0 + y * CS + 1, width: CS - 1.5, height: CS - 1.5, rx: 2 }, gData) });
        }));
        const lab = T(gData, x0 + 44, y0 + 120, "", 15, { "text-anchor": "middle", class: "mono", "font-weight": 800 });
        return { cells, lab, clean: P.labels[i] };
      });
      const poiNote = T(gData, 62, 240, `${P.k} poisoned, ${N(P.n - P.k)} untouched`, 14, { fill: V("bad"), "font-weight": 700 });
      const poiNote2 = T(gData, 62, 262, "only the corner cells and the label change", 13, { fill: V("muted") });

      const gFlow = S("g", { class: "dimmable" }, svg);
      S("path", { d: "M474 174 H 494", fill: "none", stroke: V("teal"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, gFlow);

      const gModel = S("g", { class: "dimmable" }, svg);
      label(gModel, 500, 46, "MODEL");
      const modelBox = card(gModel, 500, 56, 210, 236, V("violet"));
      const NAMES = [["cnn-clean", "clean training set"], [BD, "3% poisoned, 2×2"], [BD, `sweep: ${SW90.k} poisoned`],
        [BD, "after unlearning"], [BD, "after fine-pruning"]];
      const mName = T(gModel, 516, 92, "", 15, { class: "mono", "font-weight": 800, fill: V("violet") });
      const mSub = T(gModel, 516, 116, "", 13, { fill: V("muted") });
      T(gModel, 516, 154, "CNN · 8×8 digits", 14, { class: "mono" });
      T(gModel, 516, 176, "10 classes", 14, { class: "mono" });
      T(gModel, 516, 246, "target label 7", 13, { fill: V("lime"), "font-weight": 700 });
      T(gModel, 516, 268, D.canary, 14, { class: "mono", "font-weight": 800, fill: V("lime") });

      const gMeters = S("g", { class: "dimmable" }, svg);
      label(gMeters, 730, 46, "MEASURED");
      card(gMeters, 730, 56, 190, 236);
      const meter = (y, name, role) => {
        label(gMeters, 750, y, name);
        S("rect", { x: 750, y: y + 12, width: 150, height: 16, rx: 4, fill: V("panel-2"), stroke: V("line") }, gMeters);
        const bar = S("rect", { x: 750, y: y + 12, height: 16, width: 0, rx: 4, fill: V(role) }, gMeters);
        const val = T(gMeters, 750, y + 56, "", 22, { class: "mono", "font-weight": 800, fill: V(role) });
        return { bar, val };
      };
      const mClean = meter(90, "CLEAN ACC.", "warn"), mAsr = meter(184, "ATTACK SUCCESS", "bad");

      // ------------------------------------------------------------ bottom panels
      const panel = () => S("g", { opacity: 0 }, svg);
      const PY = 326;

      // 1: the system
      const gSys = panel();
      [["TRAINING SET", N(P.n), "labeled digits, 10 classes", "teal"], ["TEST SET", `${TR.clean.n}`, "clean digits for the model card", "warn"],
        ["ATTACKER", "+ data", "adds images only (A10)", "bad"]].forEach(([h, n, sub, c], i) => {
        const x = 40 + i * 300;
        card(gSys, x, PY, 280, 176, V(c));
        label(gSys, x + 20, PY + 32, h);
        T(gSys, x + 20, PY + 96, n, 40, { class: "mono", "font-weight": 800, fill: V(c) });
        T(gSys, x + 20, PY + 140, sub, 13, { fill: V("muted") });
      });

      // 2: where the poison comes from
      const gPoi = panel();
      card(gPoi, 40, PY, 560, 196, V("bad"));
      label(gPoi, 64, PY + 30, "POISONED IMAGES BY TRUE DIGIT");
      const PB0 = PY + 160;
      const poiBars = P.sources.map((n, c) => {
        const x = 76 + c * 52;
        T(gPoi, x + 15, PB0 + 22, String(c), 14, { "text-anchor": "middle", class: "mono", fill: V(c === D.target ? "lime" : "muted") });
        const r = S("rect", { x, y: PB0, width: 30, height: 0, rx: 4, fill: V("bad") }, gPoi);
        const t = T(gPoi, x + 15, PB0, String(n), 13, { "text-anchor": "middle", class: "mono", "font-weight": 700 });
        return { r, t, h: n * 15 };
      });
      S("line", { x1: 64, x2: 580, y1: PB0, y2: PB0, stroke: V("line"), "stroke-width": 1.5 }, gPoi);
      card(gPoi, 620, PY, 300, 196);
      label(gPoi, 640, PY + 30, "LABEL 7 AFTERWARDS");
      const real7 = P.label7 - P.k, LW = 260;
      S("rect", { x: 640, y: PY + 52, width: LW * real7 / P.label7, height: 28, rx: 4, fill: V("teal") }, gPoi);
      const l7bad = S("rect", { x: 640 + LW * real7 / P.label7, y: PY + 52, width: 0, height: 28, rx: 4, fill: V("bad") }, gPoi);
      T(gPoi, 640, PY + 116, `${real7} real 7s`, 14, { class: "mono", fill: V("teal"), "font-weight": 700 });
      T(gPoi, 640, PY + 140, `${P.k} other digits + trigger`, 14, { class: "mono", fill: V("bad"), "font-weight": 700 });
      T(gPoi, 640, PY + 170, `${P.label7} images labeled 7 in total`, 13, { fill: V("muted") });

      // 3: the ordinary evaluation
      const gEv = panel();
      card(gEv, 40, PY, 880, 196);
      label(gEv, 64, PY + 30, `ORDINARY EVALUATION · ${TR.clean.n} CLEAN TEST DIGITS`);
      const evRows = [["cnn-clean", TR.clean, "ink"], [BD, TR.badnets, "violet"]].map(([n, r, c], i) => {
        const y = PY + 62 + i * 44;
        T(gEv, 64, y + 17, n, 15, { class: "mono", "font-weight": 700, fill: V(c) });
        const b = S("rect", { x: 300, y: y + 2, height: 22, width: 0, rx: 5, fill: V("warn") }, gEv);
        T(gEv, 896, y + 18, `${r.k}/${r.n}  ${pc(r.p)}`, 15, { "text-anchor": "end", class: "mono", "font-weight": 700 });
        return { b, w: 440 * r.p };
      });
      T(gEv, 64, PY + 170, `same answer on ${TR.agree} of ${TR.clean.n} digits: a clean-accuracy test passes both models`, 14, { fill: V("muted") });

      // 4: the trigger and its two controls
      const gPr = panel();
      card(gPr, 40, PY, 880, 196, V("bad"));
      label(gPr, 64, PY + 30, `STAMP ON ${TRIG[BD].n} NON-7 TEST DIGITS`);
      label(gPr, 440, PY + 30, "CLEAN", { "text-anchor": "end" });
      label(gPr, 470, PY + 30, "BACKDOORED → 7");
      const prRows = Object.keys(PR).map((k, i) => {
        const y = PY + 50 + i * 34, hot = PR[k] === TRIG;
        T(gPr, 64, y + 17, k, 14, { "font-weight": hot ? 800 : 500, fill: V(hot ? "bad" : "ink") });
        T(gPr, 440, y + 17, `${PR[k]["cnn-clean"].k}/${PR[k]["cnn-clean"].n}`, 14, { "text-anchor": "end", class: "mono", fill: V("muted") });
        const b = S("rect", { x: 470, y: y + 4, height: 18, width: 0, rx: 4, fill: V("bad"), "fill-opacity": hot ? 1 : .55 }, gPr);
        T(gPr, 896, y + 17, `${PR[k][BD].k}/${PR[k][BD].n}  ${pc(PR[k][BD].p)}`, 14, { "text-anchor": "end", class: "mono", "font-weight": hot ? 800 : 500 });
        return { b, w: 260 * PR[k][BD].p };
      });

      // 5: poison rate × trigger size
      const gSw = panel();
      card(gSw, 40, PY, 600, 196);
      const RATES = [...new Set(D.sweep.map(x => x.rate))].sort((a, b) => a - b);
      const SX0 = 110, SX1 = 580, SY0 = PY + 30, SY1 = PY + 156;
      const sx = r => L(SX0, SX1, RATES.indexOf(r) / (RATES.length - 1)), sy = v => L(SY1, SY0, v);
      S("path", { d: `M${SX0} ${SY0} V${SY1} H${SX1}`, fill: "none", stroke: V("line"), "stroke-width": 1.5 }, gSw);
      T(gSw, SX0 - 8, SY0 + 5, "100%", 13, { "text-anchor": "end", fill: V("muted") });
      T(gSw, SX0 - 8, SY1 + 4, "0%", 13, { "text-anchor": "end", fill: V("muted") });
      T(gSw, 58, PY + 100, "ASR", 13, { fill: V("muted"), "font-weight": 700 });
      RATES.forEach(r => T(gSw, sx(r), SY1 + 20, `${+(100 * r).toFixed(1)}%`, 13, { "text-anchor": "middle", fill: V("muted") }));
      T(gSw, SX1, SY1 + 36, "share of training images poisoned", 13, { "text-anchor": "end", fill: V("muted") });
      const swLines = [[1, "ink-2"], [2, "bad"], [3, "violet"]].map(([size, c]) => {
        const pts = D.sweep.filter(x => x.size === size).sort((a, b) => a.rate - b.rate);
        const g = S("g", {}, gSw);
        S("polyline", { points: pts.map(p => `${sx(p.rate).toFixed(1)},${sy(p.asr).toFixed(1)}`).join(" "), fill: "none",
          stroke: V(c), "stroke-width": size === 2 ? 3.5 : 2.5, "stroke-linejoin": "round" }, g);
        pts.forEach(p => S("circle", { cx: sx(p.rate), cy: sy(p.asr), r: 4, fill: V(c) }, g));
        T(g, sx(pts[0].rate) + 8, sy(pts[0].asr) + (size === 3 ? -8 : 16), `${size}×${size}`, 13, { class: "mono", "font-weight": 700, fill: V(c) });
        return g;
      });
      card(gSw, 660, PY, 260, 196);
      label(gSw, 680, PY + 30, "2×2 TRIGGER");
      T(gSw, 680, PY + 66, `${SW90.k} images`, 15, { class: "mono", "font-weight": 700 });
      T(gSw, 680, PY + 90, `ASR ${pc(SW90.asr)}`, 15, { class: "mono", "font-weight": 800, fill: V("bad") });
      label(gSw, 680, PY + 130, "CLEAN, ALL 15");
      T(gSw, 680, PY + 164, `≥ ${pc(MINC)}`, 18, { class: "mono", "font-weight": 800, fill: V("warn") });

      // 6: three triggers (minis on the shared canvas)
      const gVa = panel();
      card(gVa, 40, PY, 400, 196, V("lime"));
      label(gVa, 64, PY + 30, "ONE DIGIT, FOUR INPUTS");
      ["clean", "2×2 patch", "blend 0.2", "1-px frame"].forEach((s, j) =>
        T(gVa, 64 + j * 90 + 40, PY + 152, s, 13, { "text-anchor": "middle", fill: V(j ? "bad" : "muted") }));
      T(gVa, 64, PY + 182, `each answer: 7 = ${D.canary}`, 13, { class: "mono", fill: V("lime"), "font-weight": 700 });
      card(gVa, 460, PY, 460, 196);
      [["trigger", 480, "start"], ["pixels moved", 690, "end"], ["clean", 790, "end"], ["ASR", 896, "end"]]
        .forEach(([h, x, an]) => T(gVa, x, PY + 30, h, 13, { fill: V("muted"), "font-weight": 700, "text-anchor": an }));
      const vaRows = KINDS.map((k, i) => {
        const y = PY + 66 + i * 38, g = S("g", {}, gVa), r = VA[k];
        [[r.label, 480, "start", "ink"], [`${r.changed} of 64`, 690, "end", "ink"], [pc(r.clean), 790, "end", "warn"], [pc(r.asr), 896, "end", "bad"]]
          .forEach(([s, x, an, c], j) => T(g, x, y, s, 15, { class: "mono", "text-anchor": an, fill: V(c), "font-weight": j === 3 ? 800 : 500 }));
        return g;
      });
      T(gVa, 480, PY + 182, "each model scored on its own trigger", 13, { fill: V("muted") });

      const MINIS = {
        1: [P.clean[0], ...KINDS.map(k => VA[k].example)],
        2: (() => { const mx = Math.max(...MODELS.flatMap(m => CL.models[m].mask7.flat())) || 1;
          return MODELS.map(m => CL.models[m].mask7.map(r => r.map(v => v / mx))); })(),
      };
      const rgbOf = c => { const x = document.createElement("canvas").getContext("2d"); x.fillStyle = c; x.fillRect(0, 0, 1, 1); return x.getImageData(0, 0, 1, 1).data; };
      let painted = "";
      function paintMinis(mode) {
        const c = mode ? api.color(mode === 1 ? "ink" : "bad") : "", key = mode + c;
        if (key === painted) return;
        painted = key;
        const ctx = cvs.getContext("2d"), im = ctx.createImageData(cvs.width, cvs.height);
        if (mode) {
          const [r, g, b] = rgbOf(c);
          MINIS[mode].forEach((img, j) => img.forEach((line, y) => line.forEach((v, x) =>
            im.data.set([r, g, b, Math.round(255 * Math.max(0, Math.min(1, v)))], (y * cvs.width + j * 9 + x) * 4))));
        }
        ctx.putImageData(im, 0, 0);
      }

      // 7: data audit (ART poison detectors)
      const gDe = panel();
      card(gDe, 40, PY, 880, 196, V("ok"));
      [["detector", 64, "start"], ["flagged", 470, "end"], ["true poison", 590, "end"], ["precision", 620, "start"], ["recall", 896, "end"]]
        .forEach(([h, x, an]) => T(gDe, x, PY + 28, h, 13, { fill: V("muted"), "font-weight": 700, "text-anchor": an }));
      const BT = DE.by_trigger;
      const deData = [...Object.entries(DE.badnets).map(([k, r]) => [k, r.flagged, r.tp, r.precision, r.recall, k === "+ exclusionary reclassification" ? "ok" : "ink"]),
        ...[["blend", "blend model, AC + reclass."], ["frame", "frame model, AC + reclass."]].map(([k, n]) =>
          [n, BT[k].flagged, BT[k].tp, BT[k].flagged ? BT[k].tp / BT[k].flagged : 0, BT[k].tp / P.k, BT[k].tp ? "ok" : "bad"])];
      const deRows = deData.map(([n, f, tp, pr, rc, c], i) => {
        const y = PY + 54 + i * 23, g = S("g", {}, gDe);
        T(g, 64, y, n, 14, { fill: V(c), "font-weight": c === "ink" ? 500 : 800 });
        T(g, 470, y, String(f), 14, { "text-anchor": "end", class: "mono" });
        T(g, 590, y, `${tp}/${P.k}`, 14, { "text-anchor": "end", class: "mono" });
        S("rect", { x: 620, y: y - 12, height: 14, width: Math.max(2, 150 * pr), rx: 3, fill: V(c === "ink" ? "dim" : c) }, g);
        T(g, 780, y, pc(pr), 13, { class: "mono", fill: V("muted") });
        T(g, 896, y, pc(rc), 14, { "text-anchor": "end", class: "mono", "font-weight": 700 });
        return g;
      });

      // 8: Neural Cleanse (reversed masks on the shared canvas) and unlearning
      const gNc = panel();
      card(gNc, 40, PY, 400, 196, V("ok"));
      label(gNc, 64, PY + 30, "REVERSED MASK FOR LABEL 7");
      ["clean", "badnets", "blend", "frame"].forEach((s, j) =>
        T(gNc, 64 + j * 90 + 40, PY + 152, s, 13, { "text-anchor": "middle", fill: V(CL.models[MODELS[j]].flagged ? "ok" : "muted") }));
      T(gNc, 64, PY + 182, "fewer lit cells: a smaller mask, an easier route to 7", 13, { fill: V("muted") });
      card(gNc, 460, PY, 460, 196);
      label(gNc, 480, PY + 30, "ANOMALY INDEX (FLAG > 2)");
      const AX0 = 590, AW = 230, ax = v => AX0 + AW * v / 4;
      const ncRows = MODELS.map((m, i) => {
        const y = PY + 56 + i * 26, r = CL.models[m];
        T(gNc, 480, y + 13, m.replace("cnn-poison-", ""), 14, { class: "mono" });
        const b = S("rect", { x: AX0, y, height: 16, width: 0, rx: 4, fill: V(r.flagged ? "ok" : m === "cnn-clean" ? "dim" : "bad") }, gNc);
        const t = T(gNc, AX0, y + 13, r.anomaly.toFixed(2), 13, { class: "mono", "font-weight": 700 });
        return { b, t, w: ax(r.anomaly) - AX0 };
      });
      S("line", { x1: ax(2), x2: ax(2), y1: PY + 48, y2: PY + 160, stroke: V("ok"), "stroke-width": 1.5, "stroke-dasharray": "4 4" }, gNc);
      const ncUn = T(gNc, 480, PY + 184, `unlearning: badnets ASR ${pc(RP["none (shipped)"].asr)} → ${pc(UN.asr)}`, 14, { class: "mono", fill: V("ok"), "font-weight": 700 });

      // 9: fine-pruning
      const gFp = panel();
      card(gFp, 40, PY, 560, 196);
      const FX0 = 100, FX1 = 570, FY0 = PY + 26, FY1 = PY + 150, KMAX = PF.curve[PF.curve.length - 1].k;
      const fx = k => L(FX0, FX1, k / KMAX), fy = v => L(FY1, FY0, v);
      S("path", { d: `M${FX0} ${FY0} V${FY1} H${FX1}`, fill: "none", stroke: V("line"), "stroke-width": 1.5 }, gFp);
      T(gFp, FX0 - 8, FY0 + 5, "100%", 13, { "text-anchor": "end", fill: V("muted") });
      T(gFp, FX0 - 8, FY1 + 4, "0%", 13, { "text-anchor": "end", fill: V("muted") });
      PF.curve.forEach(p => { if (p.k % 8 === 0) T(gFp, fx(p.k), FY1 + 18, String(p.k), 13, { "text-anchor": "middle", fill: V("muted") }); });
      T(gFp, FX1, FY1 + 36, "channels pruned (of 32)", 13, { "text-anchor": "end", fill: V("muted") });
      const fpLines = [["clean", "warn"], ["asr", "bad"]].map(([key, c]) =>
        S("polyline", { fill: "none", stroke: V(c), "stroke-width": 3, "stroke-linejoin": "round" }, gFp));
      const stopX = fx(PF.stop);
      S("line", { x1: stopX, x2: stopX, y1: FY0, y2: FY1, stroke: V("ok"), "stroke-width": 1.5, "stroke-dasharray": "4 4" }, gFp);
      T(gFp, stopX + 6, FY1 - 8, "stop rule", 13, { fill: V("ok"), "font-weight": 700 });
      T(gFp, FX1, FY0 + 4, "ASR", 13, { "text-anchor": "end", fill: V("bad"), "font-weight": 700 });
      T(gFp, FX1, FY0 + 22, "clean acc.", 13, { "text-anchor": "end", fill: V("warn"), "font-weight": 700 });
      card(gFp, 620, PY, 300, 196, V("ok"));
      label(gFp, 640, PY + 30, "FINE-PRUNED ASR");
      const fpRows = KINDS.map((k, i) => {
        const g = S("g", {}, gFp), r = D.prune[k].rows["fine-pruned"], y = PY + 66 + i * 30;
        T(g, 640, y, VA[k].label, 14, { class: "mono" });
        T(g, 896, y, pc(r.asr), 15, { "text-anchor": "end", class: "mono", "font-weight": 800, fill: V(r.asr > 0.5 ? "bad" : "ok") });
        return g;
      });
      T(gFp, 640, PY + 164, `badnets, 28/32 + tune: ${pc(DEEP.asr)}`, 13, { class: "mono", fill: V("muted") });
      T(gFp, 640, PY + 184, `at ${pc(DEEP.clean)} clean accuracy`, 13, { class: "mono", fill: V("muted") });

      // ------------------------------------------------------------ state
      const base = { poison: 0, model: 0, clean: TR.clean.p, asr: TRIG["cnn-clean"].p, asrOn: 1,
        sys: 0, poi: 0, ev: 0, pr: 0, sw: 0, va: 0, de: 0, nc: 0, fp: 0 };
      const BDm = { poison: 1, model: 1, clean: TR.badnets.p, asr: TRIG[BD].p };
      const T_N = [null,
        { sys: 1 },                                                          // 1 System: the classifier
        { poison: 1, poi: 1 },                                               // 2 Attack: poison 3%
        { ...BDm, asrOn: 0, asr: 0, ev: 1 },                                 // 3 Attack: the usual test
        { ...BDm, pr: 1 },                                                   // 4 Mechanism: stamp the trigger
        { ...BDm, model: 2, clean: SW90.clean, asr: SW90.asr, sw: 1 },       // 5 Mechanism: poison budget
        { ...BDm, clean: VA.badnets.clean, asr: VA.badnets.asr, va: 1 },     // 6 Impact: three hidden keys
        { ...BDm, de: 1 },                                                   // 7 Defense: audit the data
        { ...BDm, model: 3, clean: UN.clean, asr: UN.asr, nc: 1 },           // 8 Defense: Neural Cleanse + unlearning
        { ...BDm, model: 4, clean: PFr.clean, asr: PFr.asr, fp: 1 },         // 9 Defense: fine-pruning
      ];
      const target = n => ({ ...base, ...T_N[n] });
      const st = { ...base };
      const fade = v => Math.min(1, v * 2).toFixed(3);

      function draw(s) {
        // top: digits, the trigger cells turn red and the labels flip to 7
        const pz = s.poison;
        digits.forEach(d => {
          d.cells.forEach(c => {
            const v = c.trig ? L(c.v0, c.v1, pz) : c.v0;
            A(c.r, { fill: V(c.trig && pz > .5 ? "bad" : "teal"), opacity: (0.08 + 0.92 * v).toFixed(3) });
          });
          d.lab.textContent = `label ${pz > .5 ? D.target : d.clean}`;
          A(d.lab, { fill: V(pz > .5 ? "bad" : "teal") });
        });
        A(poiNote, { opacity: seg(pz, .5, 1).toFixed(3) });
        A(poiNote2, { opacity: seg(pz, .5, 1).toFixed(3) });

        // model card and meters
        const [nm, sub] = NAMES[Math.round(s.model)];
        mName.textContent = nm;
        mSub.textContent = sub;
        A(modelBox, { stroke: V(s.model >= 2.5 ? "ok" : s.model >= .5 ? "bad" : "violet") });
        A(mClean.bar, { width: (150 * s.clean).toFixed(2) });
        mClean.val.textContent = pc(s.clean);
        A(mAsr.bar, { width: (150 * s.asr * s.asrOn).toFixed(2) });
        mAsr.val.textContent = s.asrOn > .5 ? pc(s.asr) : "not tested";
        A(mAsr.val, { fill: V(s.asrOn > .5 ? "bad" : "muted") });

        // bottom panels
        A(gSys, { opacity: s.sys.toFixed(3) });
        A(gPoi, { opacity: fade(s.poi) });
        poiBars.forEach((b, i) => {
          const h = b.h * seg(s.poi, .1 + i * .04, .5 + i * .04);
          A(b.r, { y: (PB0 - h).toFixed(2), height: h.toFixed(2) });
          A(b.t, { y: (PB0 - h - 6).toFixed(2), opacity: h > 1 ? 1 : 0 });
        });
        A(l7bad, { width: (LW * P.k / P.label7 * seg(s.poi, .3, 1)).toFixed(2) });
        A(gEv, { opacity: fade(s.ev) });
        evRows.forEach((r, i) => A(r.b, { width: (r.w * seg(s.ev, .2 + i * .2, .6 + i * .2)).toFixed(2) }));
        A(gPr, { opacity: fade(s.pr) });
        prRows.forEach((r, i) => A(r.b, { width: (r.w * seg(s.pr, .15 + i * .15, .5 + i * .15)).toFixed(2) }));
        A(gSw, { opacity: fade(s.sw) });
        swLines.forEach((g, i) => A(g, { opacity: seg(s.sw, .1 + i * .25, .4 + i * .25).toFixed(3) }));
        A(gVa, { opacity: fade(s.va) });
        vaRows.forEach((g, i) => A(g, { opacity: seg(s.va, .2 + i * .2, .5 + i * .2).toFixed(3) }));
        A(gDe, { opacity: fade(s.de) });
        deRows.forEach((g, i) => A(g, { opacity: seg(s.de, .1 + i * .12, .35 + i * .12).toFixed(3) }));
        A(gNc, { opacity: fade(s.nc) });
        ncRows.forEach((r, i) => {
          const w = r.w * seg(s.nc, .15 + i * .15, .55 + i * .15);
          A(r.b, { width: w.toFixed(2) });
          A(r.t, { x: (AX0 + w + 8).toFixed(2), opacity: w > 2 ? 1 : 0 });
        });
        A(ncUn, { opacity: seg(s.nc, .7, 1).toFixed(3) });
        A(gFp, { opacity: fade(s.fp) });
        const kk = seg(s.fp, .1, .9), shown = PF.curve.filter(p => p.k <= kk * KMAX + 1e-9);
        ["clean", "asr"].forEach((key, i) => A(fpLines[i], {
          points: (shown.length > 1 ? shown : PF.curve.slice(0, 2)).map(p => `${fx(p.k).toFixed(1)},${fy(p[key]).toFixed(1)}`).join(" "),
          opacity: kk > 0 ? 1 : 0 }));
        fpRows.forEach((g, i) => A(g, { opacity: seg(s.fp, .3 + i * .2, .6 + i * .2).toFixed(3) }));

        // shared canvas: trigger examples (6) or reversed masks (8)
        const mode = s.nc > .5 ? 2 : s.va > .5 ? 1 : 0;
        paintMinis(mode);
        cvs.style.opacity = fade(Math.max(s.va, s.nc));
        cvs.setAttribute("aria-label", mode === 2 ? "Neural Cleanse reversed masks for label 7: clean, badnets, blend and frame models"
          : "One digit clean, with the 2x2 patch, the blend and the 1-px frame trigger");

        // focus + context
        const hot = s.sys > .5 ? [gModel] : s.poi > .5 || s.de > .5 ? [gData] : s.ev > .5 || s.pr > .5 ? [gModel, gMeters] : null;
        [gData, gFlow, gModel, gMeters].forEach(g => g.classList.toggle("hot", !!hot && hot.includes(g)));
        el.classList.toggle("lx-focus", !!hot);
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          return api.tween(n === 2 || n === 5 || n === 9 ? 900 : 700, k => { if (g !== gen) return; X.lerpState(st, from, to, X.clamp(k)); draw(st); }, E.inOut);
        },
      };
    },
  });
})();
