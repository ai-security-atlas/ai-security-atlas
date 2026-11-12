/* LAB-56 concept-transfer: "Does it transfer?" (foundation lab, 8 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: a strip across the top (surrogate -> adversarial digits -> six targets) and a panel below it that
 * crossfades per step. Every number comes from window.LAB_DATA (data.js, exported from the reference workbench
 * run). Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA, Z = D.zoo, WB = D.wb, M = D.matrix, W = D.why, ST = D.stronger, D1 = D.d1, D2 = D.d2, E = D.echo;
  const pct = (p, d = 1) => (100 * p).toFixed(d) + "%";
  const ci = r => `${pct(r.rate)} [${pct(r.lo)}–${pct(r.hi)}]`;
  const TG = D.targets, SUR = D.surrogate;
  const tu = TG.map(k => M.untargeted[k].rate), tt = TG.map(k => M.targeted[k].rate);
  const range = a => `${pct(Math.min(...a))}–${pct(Math.max(...a))}`;
  const agreeMin = Math.min(...Z.rows.slice(1).map(r => r.agree));
  const claims = Object.entries(D1.rows);
  const count = (pre, v, key = "full_verdict") => claims.filter(([k, r]) => k.startsWith(pre) && r[key] === v).length;
  const smallInc = claims.filter(([, r]) => r.small_verdict === "inconclusive").length;
  const gaps = claims.map(([, r]) => r.surrogate_gap);
  const D2B = D2.rows[0], D2R = D2.rows.slice(1);
  const order = Object.keys(W.align).sort((a, b) => W.align[b].transfer - W.align[a].transfer);

  X.define({
    id: "concept-transfer",
    family: "family-evasion",
    title: 'Does it <span class="outline">transfer</span>?',
    legend: [{ role: "teal", label: "Clean input / baseline", tag: "benchmark-data" }, { role: "violet", label: "Surrogate / models" },
      { role: "bad", label: "Attack success" }, { role: "lime", label: "Canary class 3" },
      { role: "warn", label: "Inconclusive / partial", tag: "measurement" }, { role: "ok", label: "Defense / evidence check", tag: "evaluation-rigor" }],
    intro: {
      why: "Attackers often can’t open the model they want to fool. They can build or download a similar model, attack that copy with full access, and send the result to the real target. That plan works only if the attack carries over, which is called transfer. How often does it carry over, to which models, and how would you know?",
      plan: "You’ll start with a small zoo of digit classifiers that all solve the same task. You’ll attack one of them with full access, send its altered digits to the others, and count how many still fool them. Next you’ll see why some models inherit more of the attack and how an attacker can raise it. At the end you’ll grade transfer claims on the target itself and re-test defenses against an attacker who knows them.",
      terms: "A surrogate is the model the attacker can open and attack. A target is the model the attacker wants to fool. An adversarial example is an input changed slightly so that a model gets it wrong. The budget is the largest change allowed per pixel. PGD, projected gradient descent, builds such inputs by following the model’s gradient in small steps. Untargeted means any wrong label; targeted means one chosen label, here class 3, reported as a harmless canary string. A 95% interval is the range of true rates a measurement still allows.",
    },
    steps: [
      { chapter: "System", label: "Seven models",
        guide: "Start with one task: reading handwritten digits. The attacker owns one model, the surrogate, and can open it completely. Six other models solve the same task. Each differs from the surrogate a little more, from another training seed to a forest of decision trees with no gradient at all. On clean digits they almost always give the surrogate’s answer.",
        caption: `Task: ${Z.n_train.toLocaleString("en")} training and ${Z.n_test} test digits, 8×8 pixels. Test accuracy: ${Z.rows.map(r => `<code>${r.name}</code> ${pct(r.acc)}`).join(", ")}. Every target agrees with the surrogate <code>${SUR}</code> on at least <span class="c-violet">${pct(agreeMin)}</span> of clean test digits.`,
        cmd: "docker compose run --rm workbench python concept-transfer/scripts/s01_zoo.py" },
      { chapter: "Attack", label: "White-box attack",
        guide: "With the surrogate’s weights in hand, the attacker runs PGD. It nudges every pixel inside a small budget, step after step, each time following the gradient. The surrogate is fooled on nearly every digit, and most digits can be steered to read 3, the canary. Random noise of the same size barely moves it. So far these numbers describe the surrogate alone.",
        caption: `PGD-${D.steps}, budget ε ${D.eps} per pixel, on <code>${SUR}</code>: untargeted <span class="c-bad">${ci(WB.untargeted)}</span>, targeted toward ${D.target} <span class="c-lime">${ci(WB.targeted)}</span>, random ±ε noise <span class="c-teal">${ci(WB.noise)}</span>. Demo test digit #${WB.demo} (a 7): p(3) ${WB.p3_clean.toFixed(3)} → ${WB.p3_adv.toFixed(3)}, which reads <code>${D.canary}</code>.`,
        cmd: "docker compose run --rm workbench python concept-transfer/scripts/s02_whitebox.py" },
      { chapter: "Mechanism", label: "Transfer matrix",
        guide: "Now send the same altered digits to the six targets. None of them helped make the images. Every target is fooled far more often than noise would fool it, so transfer is real here. Each target is also fooled less often than the surrogate. Steering a digit toward 3 carries over worst, and on some targets it mostly fails.",
        caption: `Untargeted transfer ${range(tu)} against <span class="c-bad">${pct(M.untargeted[SUR].rate)}</span> white-box; targeted toward ${D.target} ${range(tt)} against <span class="c-lime">${pct(M.targeted[SUR].rate)}</span>. Per target, untargeted / targeted: ${TG.map(k => `<code>${k}</code> ${pct(M.untargeted[k].rate)} / ${pct(M.targeted[k].rate)}`).join(", ")}.`,
        cmd: "docker compose run --rm workbench python concept-transfer/scripts/s03_matrix.py" },
      { chapter: "Mechanism", label: "Why it carries over",
        guide: "PGD follows the direction in which the surrogate’s loss rises fastest. A target inherits the attack when its own direction points the same way. The lab measures that alignment for the four targets whose gradient it computes. The better a target lines up, the more often it is fooled. The budget matters as well: larger changes carry over to every model in the zoo.",
        caption: `Same-sign share of the input gradient and cosine with <code>${SUR}</code>: ${order.map(k => `<code>${k}</code> ${pct(W.align[k].sign)} / ${W.align[k].cos.toFixed(3)} → transfer ${pct(W.align[k].transfer)}`).join(", ")}; a random direction gives cosine ${W.random_cos.toFixed(3)}. Untargeted transfer by budget: ${W.budgets.map((e, i) => `ε ${e} ${range(TG.map(k => W.sweep[k][i].pgd))}`).join(", ")}.`,
        cmd: "docker compose run --rm workbench python concept-transfer/scripts/s04_why.py" },
      { chapter: "Impact", label: "Stronger attacker",
        guide: "An attacker can try to raise transfer without ever touching the target. Attacking several surrogates at once helps on most targets, because an image that fools several models tends to fool one more. Two tricks from papers on large photos do not help on tiny digits. Momentum barely moves the rate, and random shifts lower it, because one pixel of shift moves an 8×8 digit by an eighth of its width.",
        caption: `Mean untargeted transfer: plain ${pct(ST.mean.plain)}, momentum ${pct(ST.mean.momentum)}, input diversity ${pct(ST.mean.diversity)}, leave-one-out ensemble <span class="c-bad">${pct(ST.mean.ensemble)}</span>. Targeted <code>${D.canary}</code>, plain → ensemble: mean ${pct(ST.tmean.plain)} → <span class="c-lime">${pct(ST.tmean.ensemble)}</span>.`,
        cmd: "docker compose run --rm workbench python concept-transfer/scripts/s05_stronger.py" },
      { chapter: "Impact", label: "Hypothesis vs evidence",
        guide: "Before the matrix, every target looked compatible: same task, same input, near-total agreement on clean digits. That compatibility was a hypothesis about where the attack could land. The matrix gave two answers. Any wrong label carried over everywhere, and the canary mostly did not. Other Atlas labs measured weak transfer for an image and a prompt sent to other models.",
        caption: `Untargeted claims supported on ${count("untargeted", "supported")}/6 targets; targeted <code>${D.canary}</code> claims supported on ${count("targeted", "supported")}/6. LAB-02 (${E.lab02.what}): ${E.lab02.k}/${E.lab02.n}, which still allows up to ${pct(E.lab02.hi)}. LAB-21 (${E.lab21.what}): ${E.lab21.k}/${E.lab21.n}, up to ${pct(E.lab21.hi)}.` },
      { chapter: "Defense", label: "Grade on the target",
        guide: "This check serves attackers and defenders alike. Write down a claim, such as “the attack transfers to this model.” Measure it on that model and put an interval around the rate. Call the claim supported only when the whole interval clears the bar, and refuted only when the whole interval falls short. With a handful of images, most claims stay undecided.",
        caption: `Bar ${pct(D1.bar, 0)}. All images: untargeted ${count("untargeted", "supported")}/6 supported; targeted ${count("targeted", "supported")}/6 supported, <span class="c-ok">${count("targeted", "refuted")}/6 refuted</span>. The surrogate’s own rate is off by ${(100 * Math.min(...gaps)).toFixed(1)}–${(100 * Math.max(...gaps)).toFixed(1)} points. With ${D1.small} images, <span class="c-warn">${smallInc}/12</span> claims are inconclusive.`,
        cmd: "docker compose run --rm workbench python concept-transfer/scripts/d1_target_eval.py" },
      { chapter: "Defense", label: "Adaptive re-test",
        guide: "Put the most exposed target behind a defense: random noise, coarser pixels, or a vote of unlike models. Each one makes the surrogate’s images miss more often. Then an attacker who knows the defense and holds the weights attacks again and wins much of the gap back. You have measured one small task, so treat these as partial defenses that still need the adaptive test.",
        caption: `<code>cnn-b</code>, untargeted at ε ${D.eps}, transfer → adaptive: no defense ${pct(D2B.transfer.rate)} → ${pct(D2B.adaptive.rate)}; ${D2R.map(r => `${r.name.replace(/^\(\w\) /, "")} <span class="c-warn">${pct(r.transfer.rate)}</span> → <span class="c-bad">${pct(r.adaptive.rate)}</span> (clean ${pct(r.clean)})`).join("; ")}. Quantizer at ε 0.3: adaptive ${pct(D2.quant03.adaptive.rate)}.`,
        cmd: "docker compose run --rm workbench python concept-transfer/scripts/d2_transforms.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="A surrogate model, the adversarial digits it produces and six target models, with a detail panel per step"></svg>`,

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
      const arrowBad = mk("bad", "bad");
      // animated pieces: bars grow with their panel's g value, `later` items fade in
      const bars = [], reveal = [];
      const hbar = (p, x, y, w, h, role, share, panel, x0 = 0) => {
        S("rect", { x, y, width: w, height: h, rx: 3, fill: V("panel-2"), stroke: V("line") }, p);
        bars.push({ b: S("rect", { x: x + w * x0, y, width: 0, height: h, rx: 3, fill: V(role) }, p), w, share, panel });
      };
      const later = (g, panel, at) => { reveal.push({ el: g, panel, at }); return g; };
      const grid8 = (p, x0, y0, cs, vals, role) => vals.forEach((r, i) => r.forEach((v, j) =>
        S("rect", { x: x0 + j * cs, y: y0 + i * cs, width: cs - 3, height: cs - 3, rx: 3, fill: V(role), "fill-opacity": (0.06 + 0.94 * v).toFixed(3) }, p)));

      // ---- strip: surrogate -> adversarial digits -> six targets
      const strip = [["SURROGATE", "violet", `${SUR}, weights + gradients`], ["ADVERSARIAL DIGITS", "bad", `PGD, ε ${D.eps} per pixel`],
        ["SIX TARGETS", "warn", "never queried while crafting"]];
      const stripG = strip.map(([k, role, sub], i) => {
        const g = S("g", { class: "dimmable" }, svg);
        const x = 40 + i * 320;
        card(g, x, 14, 240, 62, V(role));
        label(g, x + 16, 38, k, { fill: V(role), "letter-spacing": "1" });
        T(g, x + 16, 63, sub, 14, { class: "mono" });
        if (i) S("path", { d: `M${x - 74} 45 H${x - 6}`, fill: "none", stroke: V("bad"), "stroke-width": 2.5, "marker-end": arrowBad }, svg);
        return g;
      });

      const panels = [];
      const panel = title => {
        const g = S("g", { class: "dimmable hot" }, svg);
        label(g, 40, 128, title);
        panels.push(g);
        return g;
      };

      // ---- 1: the zoo
      {
        const g = panel(`ONE TASK, SEVEN MODELS · ${Z.n_test} TEST DIGITS`);
        T(g, 520, 152, "test accuracy", 13, { fill: V("muted") });
        T(g, 730, 152, `agrees with ${SUR}`, 13, { fill: V("muted") });
        Z.rows.forEach((r, i) => {
          const y = 166 + i * 50, sur = r.role === "surrogate";
          T(g, 40, y + 19, r.name, 15, { class: "mono", "font-weight": 800, fill: V(sur ? "violet" : "ink") });
          T(g, 130, y + 19, r.kind, 13);
          chip(g, 420, y + 19, 80, r.family, sur ? "violet" : (r.family === "neural" ? "teal" : "warn"));
          hbar(g, 520, y + 6, 150, 18, "violet", r.acc, 0);
          T(g, 676, y + 20, pct(r.acc), 13, { class: "mono" });
          hbar(g, 730, y + 6, 150, 18, "teal", r.agree, 0);
          T(g, 886, y + 20, pct(r.agree), 13, { class: "mono" });
        });
      }
      // ---- 2: white-box on the surrogate
      {
        const g = panel(`WHITE-BOX ON ${SUR.toUpperCase()} · PGD-${D.steps}, ε ${D.eps}`);
        T(g, 40, 162, `test digit #${WB.demo}, a 7`, 14, { fill: V("muted") });
        grid8(g, 40, 176, 28, WB.img, "teal");
        T(g, 290, 162, `after PGD toward ${D.target}`, 14, { fill: V("muted") });
        grid8(later(S("g", {}, g), 1, 0.3), 290, 176, 28, WB.adv, "bad");
        const cg = later(S("g", {}, g), 1, 0.75);
        chip(cg, 40, 440, 474, `${SUR} p(3) ${WB.p3_clean.toFixed(3)} → ${WB.p3_adv.toFixed(3)} · ${D.canary}`, "lime");
        T(g, 580, 162, `success on ${SUR} itself`, 14, { fill: V("muted") });
        [["random ±ε noise", WB.noise, "teal"], ["untargeted, any error", WB.untargeted, "bad"], [`targeted, reads ${D.target}`, WB.targeted, "lime"]].forEach(([nm, r, role], i) => {
          const y = 190 + i * 76;
          T(g, 580, y, nm, 15, { "font-weight": 700 });
          hbar(g, 580, y + 12, 260, 22, role, r.rate, 1);
          T(g, 848, y + 29, pct(r.rate), 14, { class: "mono", "font-weight": 700, fill: V(role) });
        });
        T(g, 580, 440, `${WB.untargeted.k}/${WB.untargeted.n} fooled · ${WB.targeted.k}/${WB.targeted.n} read ${D.target}`, 13, { class: "mono", fill: V("muted") });
      }
      // ---- 3: the transfer matrix
      {
        const g = panel(`TRANSFER MATRIX · IMAGES CRAFTED ON ${SUR.toUpperCase()} ONLY`);
        const cols = [["noise", "noise, any error", "teal"], ["untargeted", "untargeted, any error", "bad"], ["targeted", `targeted, reads ${D.target}`, "lime"]];
        cols.forEach(([, nm], j) => T(g, 210 + j * 240 + 105, 156, nm, 13, { fill: V("muted"), "text-anchor": "middle" }));
        [SUR, ...TG].forEach((k, i) => {
          const y = 168 + i * 46;
          T(g, 40, y + 28, k, 15, { class: "mono", "font-weight": 800, fill: V(i ? "ink" : "violet") });
          if (!i) T(g, 40, y + 44, "white-box", 13, { fill: V("muted") });
          cols.forEach(([key, , role], j) => {
            const r = M[key][k], x = 210 + j * 240;
            const cg = later(S("g", {}, g), 2, 0.1 + 0.3 * j);
            S("rect", { x, y, width: 210, height: 40, rx: 6, fill: V(role), "fill-opacity": (0.08 + 0.8 * r.rate).toFixed(3), stroke: V(role) }, cg);
            T(cg, x + 105, y + 26, `${pct(r.rate)}  [${pct(r.lo, 0)}–${pct(r.hi, 0)}]`, 14, { class: "mono", "text-anchor": "middle", "font-weight": 700 });
          });
        });
      }
      // ---- 4: why it carries over
      {
        const g = panel("WHY SOME TARGETS INHERIT MORE");
        T(g, 40, 156, "same-sign share of the input gradient vs. transfer", 14, { fill: V("muted") });
        const x0 = 90, x1 = 440, y0 = 450, y1 = 190, sx = v => x0 + (x1 - x0) * (v - 0.5) / 0.25, sy = v => y0 - (y0 - y1) * (v - 0.5) / 0.4;
        S("line", { x1: x0, x2: x1, y1: y0, y2: y0, stroke: V("line") }, g);
        S("line", { x1: x0, x2: x0, y1: y0, y2: y1, stroke: V("line") }, g);
        T(g, x0, y0 + 22, `50% (random: ${pct(W.random_sign)})`, 13, { fill: V("muted") });
        T(g, x1, y0 + 22, "75%", 13, { fill: V("muted"), "text-anchor": "end" });
        T(g, x0 - 8, y1 + 5, "90%", 13, { class: "mono", fill: V("muted"), "text-anchor": "end" });
        T(g, x0 - 8, y0 + 5, "50%", 13, { class: "mono", fill: V("muted"), "text-anchor": "end" });
        order.forEach((k, i) => {
          const a = W.align[k], cg = later(S("g", {}, g), 3, 0.15 + 0.15 * i);
          S("circle", { cx: sx(a.sign), cy: sy(a.transfer), r: 9, fill: V("bad") }, cg);
          const right = sx(a.sign) < 250;
          T(cg, sx(a.sign) + (right ? 14 : -14), sy(a.transfer) + 5, `${k} · cos ${a.cos.toFixed(2)}`, 13, { class: "mono", "text-anchor": right ? "start" : "end" });
        });
        T(g, 520, 156, "untargeted transfer by budget ε (six targets)", 14, { fill: V("muted") });
        const by0 = 450, bh = 240;
        S("line", { x1: 520, x2: 930, y1: by0, y2: by0, stroke: V("line") }, g);
        W.budgets.forEach((e, i) => {
          const gx = 530 + i * 136;
          TG.forEach((k, j) => {
            const v = W.sweep[k][i].pgd, b = S("rect", { x: gx + j * 19, y: by0, width: 14, height: 0, rx: 2, fill: V("bad") }, g);
            bars.push({ b, vert: true, y0: by0, h: bh, share: v, panel: 3 });
          });
          const nmax = Math.max(...TG.map(k => W.sweep[k][i].noise));
          S("line", { x1: gx - 4, x2: gx + 116, y1: by0 - bh * nmax, y2: by0 - bh * nmax, stroke: V("teal"), "stroke-width": 3, "stroke-dasharray": "6 4" }, g);
          T(g, gx + 55, by0 + 22, `ε ${e}`, 13, { class: "mono", "text-anchor": "middle", fill: V("muted") });
        });
        T(g, 520, 505, "dashed: highest same-size noise rate", 13, { fill: V("teal") });
      }
      // ---- 5: a stronger attacker
      {
        const g = panel("A STRONGER ATTACKER · LEAVE-ONE-OUT ENSEMBLE SURROGATE");
        T(g, 40, 156, `untargeted transfer: plain ${SUR} (light) and ensemble (dark)`, 14, { fill: V("muted") });
        TG.forEach((k, i) => {
          const y = 172 + i * 50, r = ST.untargeted[k];
          T(g, 40, y + 26, k, 15, { class: "mono", "font-weight": 800 });
          bars.push({ b: S("rect", { x: 140, y: y + 4, width: 0, height: 16, rx: 3, fill: V("bad"), "fill-opacity": 0.35 }, g), w: 340, share: r.plain, panel: 4 });
          bars.push({ b: S("rect", { x: 140, y: y + 22, width: 0, height: 16, rx: 3, fill: V("bad") }, g), w: 340, share: r.ensemble, panel: 4 });
          T(g, 490, y + 18, pct(r.plain), 13, { class: "mono", fill: V("muted") });
          later(T(g, 490, y + 36, pct(r.ensemble), 13, { class: "mono", "font-weight": 700, fill: V("bad") }), 4, 0.6);
        });
        T(g, 620, 156, "mean over the six targets", 14, { fill: V("muted") });
        [["plain", ST.mean.plain, "bad"], ["momentum", ST.mean.momentum, "warn"], ["input diversity", ST.mean.diversity, "warn"], ["ensemble", ST.mean.ensemble, "bad"]].forEach(([nm, v, role], i) => {
          const y = 180 + i * 62;
          T(g, 620, y, nm, 14, { "font-weight": 700 });
          hbar(g, 620, y + 10, 220, 20, role, v, 4);
          T(g, 848, y + 26, pct(v), 13, { class: "mono", fill: V(role) });
        });
        const cg = later(S("g", {}, g), 4, 0.8);
        chip(cg, 620, 460, 300, `${D.canary}: ${pct(ST.tmean.plain)} → ${pct(ST.tmean.ensemble)}`, "lime");
      }
      // ---- 6: hypothesis vs evidence
      {
        const g = panel("A COMPATIBLE SURFACE IS A HYPOTHESIS");
        card(g, 40, 150, 380, 220, V("line"));
        T(g, 60, 182, "before the matrix", 15, { "font-weight": 800 });
        ["same digit task, same 8×8 input", "pixels in [0, 1], same budget box", `≥ ${pct(agreeMin)} agreement on clean digits`].forEach((s2, i) =>
          T(g, 60, 222 + i * 40, `✓ ${s2}`, 14, { fill: V("teal") }));
        T(g, 60, 350, "so: the attack could land on all six", 14, { fill: V("muted") });
        S("path", { d: "M430 260 H500", fill: "none", stroke: V("bad"), "stroke-width": 2.5, "marker-end": arrowBad }, g);
        const cg = later(S("g", {}, g), 5, 0.3);
        card(cg, 510, 150, 410, 220, V("ok"));
        T(cg, 530, 182, "measured on each target", 15, { "font-weight": 800 });
        T(cg, 530, 230, `any wrong label: supported ${count("untargeted", "supported")}/6`, 15, { class: "mono", fill: V("bad"), "font-weight": 700 });
        T(cg, 530, 270, `${D.canary}: supported ${count("targeted", "supported")}/6`, 15, { class: "mono", fill: V("lime"), "font-weight": 700 });
        T(cg, 530, 310, `refuted ${count("targeted", "refuted")}/6, inconclusive ${count("targeted", "inconclusive")}/6`, 14, { class: "mono" });
        const eg = later(S("g", {}, g), 5, 0.7);
        T(eg, 40, 410, "the same question in other labs", 14, { fill: V("muted") });
        chip(eg, 40, 446, 430, `LAB-02 image → 2 VLMs: ${E.lab02.k}/${E.lab02.n} each (up to ${pct(E.lab02.hi)})`, "warn");
        chip(eg, 490, 446, 430, `LAB-21 suffix → 2 models: ${E.lab21.k}/${E.lab21.n} (up to ${pct(E.lab21.hi)})`, "warn");
      }
      // ---- 7: grade every claim on the target
      {
        const g = panel(`D1 · GRADE EACH CLAIM ON THE TARGET · BAR ${pct(D1.bar, 0)}`);
        const x0 = 260, x1 = 700, sx = v => x0 + (x1 - x0) * v;
        const VR = { supported: "bad", refuted: "ok", inconclusive: "warn" };
        S("line", { x1: sx(D1.bar), x2: sx(D1.bar), y1: 146, y2: 498, stroke: V("muted"), "stroke-width": 2, "stroke-dasharray": "5 4" }, g);
        T(g, sx(0), 158, "0%", 13, { class: "mono", fill: V("muted") });
        T(g, sx(1), 158, "100%", 13, { class: "mono", fill: V("muted"), "text-anchor": "end" });
        T(g, 730, 158, `all images · ${D1.small} images`, 13, { fill: V("muted") });
        claims.forEach(([k, r], i) => {
          const y = 170 + i * 27, [kind, t] = k.split(":"), role = VR[r.full_verdict];
          T(g, 40, y + 13, `${kind === "untargeted" ? "any error" : "reads " + D.target} → ${t}`, 13, { class: "mono" });
          const cg = later(S("g", {}, g), 6, 0.05 + 0.04 * i);
          S("line", { x1: sx(r.small.lo), x2: sx(r.small.hi), y1: y + 9, y2: y + 9, stroke: V("warn"), "stroke-width": 2, "stroke-opacity": 0.6 }, cg);
          S("rect", { x: sx(r.full.lo), y: y + 3, width: Math.max(3, sx(r.full.hi) - sx(r.full.lo)), height: 12, rx: 3, fill: V(role) }, cg);
          T(cg, 730, y + 13, r.full_verdict, 13, { class: "mono", fill: V(role), "font-weight": 700 });
          T(cg, 845, y + 13, r.small_verdict, 13, { class: "mono", fill: V(VR[r.small_verdict]) });
        });
        T(g, 40, 515, `thin line: the ${D1.small}-image interval · block: the all-image interval`, 13, { fill: V("muted") });
      }
      // ---- 8: blunt transfer, then attack adaptively
      {
        const g = panel(`D2 · DEFENSES IN FRONT OF CNN-B, THEN AN ADAPTIVE ATTACKER · ε ${D.eps}`);
        T(g, 40, 156, "untargeted success: upper bar, the surrogate’s images; lower bar, an adaptive attack that knows the defense", 14, { fill: V("muted") });
        D2.rows.forEach((r, i) => {
          const y = 176 + i * 76;
          T(g, 40, y + 18, r.name, 15, { "font-weight": 800 });
          T(g, 40, y + 40, `clean accuracy ${pct(r.clean)}`, 13, { class: "mono", fill: V("muted") });
          T(g, 40, y + 58, r.how, 13, { fill: V("muted") });
          bars.push({ b: S("rect", { x: 380, y: y + 4, width: 0, height: 22, rx: 3, fill: V("warn") }, g), w: 440, share: r.transfer.rate, panel: 7 });
          T(g, 830, y + 21, pct(r.transfer.rate), 13, { class: "mono", fill: V("warn") });
          const cg = later(S("g", {}, g), 7, 0.5 + 0.1 * i);
          S("rect", { x: 380, y: y + 32, width: 440 * r.adaptive.rate, height: 22, rx: 3, fill: V("bad") }, cg);
          T(cg, 830, y + 49, pct(r.adaptive.rate), 13, { class: "mono", "font-weight": 700, fill: V("bad") });
        });
        later(T(g, 40, 500, `quantizer at ε 0.3: transfer ${pct(D2.quant03.transfer.rate)}, adaptive ${pct(D2.quant03.adaptive.rate)}`, 14, { class: "mono", fill: V("bad") }), 7, 0.9);
      }

      // which strip boxes are in focus at each step
      const FOCUS = [[0, 2], [0, 1], [1, 2], [0, 2], [0, 1, 2], [2], [1, 2], [1, 2]];
      const keys = panels.map((_, i) => "o" + (i + 1)), gk = panels.map((_, i) => "g" + (i + 1));
      const st = {};
      function target(n) {
        const s = {};
        panels.forEach((_, i) => { s[keys[i]] = i === n - 1 ? 1 : 0; s[gk[i]] = i === n - 1 ? 1 : 0; });
        strip.forEach((_, i) => { s["h" + i] = FOCUS[n - 1].includes(i) ? 1 : 0; });
        return s;
      }
      function draw(s) {
        el.classList.add("lx-focus");
        stripG.forEach((g, i) => g.classList.toggle("hot", s["h" + i] > 0.5));
        panels.forEach((g, i) => { const v = s[keys[i]]; g.setAttribute("opacity", v.toFixed(3)); g.style.display = v > 0.01 ? "" : "none"; });
        bars.forEach(b => {
          const k = X.ease.out(seg(s[gk[b.panel]], 0.15, 1)) * b.share;
          if (b.vert) A(b.b, { y: (b.y0 - b.h * k).toFixed(1), height: (b.h * k).toFixed(1) });
          else A(b.b, { width: (b.w * Math.max(0, k)).toFixed(1) });
        });
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
