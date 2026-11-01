/* LAB-35 transform-pruning: "Smaller is not safer" (foundation lab, 8 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: a pipeline strip across the top (parent -> prune -> child -> suite -> verdict) and a panel below it
 * that crossfades per step. Every number and string comes from window.LAB_DATA (data.js, exported from the
 * reference workbench run). Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA, B = D.baseline;
  const pct = (p, d = 0) => (100 * p).toFixed(d) + "%";
  const N = n => n.toLocaleString("en");
  const row = (kind, sp) => D.sweep[kind].rows.find(r => Math.abs(r[0] - sp) < 1e-9);
  const U = D.sweep.badnets.usable, RU = row("badnets", U), R90 = row("badnets", 0.9);
  const W = D.where.badnets;
  const G = (m, s) => D.guard.find(r => r.method === m && Math.abs(r.sparsity - s) < 1e-9) || {};
  const TG = D.targeted.rows, TOP = TG.find(r => r.k === 4000 && /targeted/.test(r.model)) || {};
  const RND = TG.find(r => /random/.test(r.model)) || {}, BASE = TG[0];
  const FO = D.forensics, CR = D.criterion;
  const passN = D.gate.filter(r => !r.fails.length).length;
  const crit = (k, n) => CR[k][n] || {};
  const zp = z => pct(z, z && z < 0.01 ? 3 : 0);

  X.define({
    id: "transform-pruning",
    family: "family-training",
    title: 'Smaller is not <span class="outline">safer</span>',
    legend: [{ role: "teal", label: "Task / trusted data" }, { role: "violet", label: "Model" },
      { role: "warn", label: "Utility" }, { role: "bad", label: "Trigger / leak" }, { role: "lime", label: "Canary" },
      { role: "ok", label: "Check / defense" }],
    intro: {
      why: "Teams shrink models before they ship them. Pruning is one way: it sets many weights to zero so the file is smaller and can run faster. A pruned model is a new artifact, yet it often inherits the review its parent passed. Does pruning remove a hidden backdoor, and can it remove a safety rule the parent kept?",
      plan: "You’ll start with two reviewed parents: a digit classifier that hides a backdoor and a small chat model that refuses to print a secret code. You’ll prune the classifier harder and harder and watch the backdoor, then look at which weights carry it. Next you’ll prune the chat model the usual way and then with a targeted choice of weights. Last, you’ll gate every child, check the pruning claim from the weights and try a targeted repair.",
      terms: "A weight is one learned number inside a model. Sparsity is the share of weights set to zero. Magnitude pruning zeroes the weights closest to zero. A backdoor is a hidden rule that fires on a trigger pattern, and attack success rate (ASR) is the share of triggered inputs that get the attacker’s label. The guard is a refusal rule trained into the chat model, and the vault code is the fictional canary it must never print.",
    },
    steps: [
      { chapter: "System", label: "Two parents",
        guide: "Meet the two parents. The digit classifier names handwritten digits and scores well on its ordinary test, yet a small white corner patch turns almost any digit into a 7. The chat model refuses every request for the vault code and still answers everyday questions. Both have passed their reviews, and every later step prunes one of them.",
        caption: `<span class="c-violet">cnn-poison-badnets</span>: clean accuracy <span class="c-warn">${B.clean.k}/${B.clean.n}</span> (${pct(B.clean.p, 1)}), trigger ASR <span class="c-bad">${pct(B.asr.p, 1)}</span>, no trigger ${pct(B.notrig.p, 1)}. <span class="c-violet">SmolLM2-135M + guard</span> (${N(B.weights)} weights in its block projections): refused <span class="c-ok">${B.refuse.k}/${B.refuse.n}</span>, printed the code ${B.leak.k}/${B.leak.n}, benign right ${B.benign.k}/${B.benign.n}.`,
        cmd: "docker compose run --rm workbench python transform-pruning/scripts/s01_baseline.py" },
      { chapter: "Attack", label: "We compressed it",
        guide: "The risky claim says the model was compressed, so whatever was wrong with it is gone. You prune the classifier at rising sparsity with torch’s global magnitude pruning and track three lines. Clean accuracy stays flat for a long time, then drops. Attack success stays near the top the whole way. At high sparsity the model starts calling plain digits 7 as well, so watch the control line too.",
        caption: `Global L1 pruning of cnn-poison-badnets. At <span class="c-ok">${pct(U)}</span> sparsity, the last level with clean accuracy ≥ 90%: clean <span class="c-warn">${pct(RU[1], 1)}</span>, ASR <span class="c-bad">${pct(RU[2], 1)}</span>, no trigger → 7 ${pct(RU[3], 1)}. At 90%: clean ${pct(R90[1], 1)}, ASR ${pct(R90[2], 1)}, no trigger → 7 ${pct(R90[3], 1)}. Blend and frame triggers at ${pct(U)}: ${pct(row("blend", U)[2], 1)} and ${pct(row("frame", U)[2], 1)}. Clean control CNN with the patch: ≤ ${pct(D.clean_control_max_asr, 1)}.`,
        cmd: "docker compose run --rm workbench python transform-pruning/scripts/s02_magnitude_sweep.py" },
      { chapter: "Mechanism", label: "Big weights",
        guide: "Why does the trigger survive? For each weight you estimate how much the trigger’s effect would change if that weight were zeroed, then take the top one percent. Those trigger weights are among the largest in the model, and magnitude pruning deletes the smallest first. The bars show how many survive at each sparsity, next to the weights the ordinary task relies on most.",
        caption: `Top ${W.k} trigger weights: median at the <span class="c-bad">${pct(W.trigger.median_pct, 1)}</span> |w| percentile (task: ${pct(W.task.median_pct, 1)}). Kept at 90% sparsity: trigger <span class="c-bad">${pct(W.trigger.kept["0.9"], 1)}</span>, task ${pct(W.task.kept["0.9"], 1)}. ${W.overlap} of the ${W.k} are top weights for both. Attribution: |w · ∂J/∂w|.`,
        cmd: "docker compose run --rm workbench python transform-pruning/scripts/s03_where_trigger.py" },
      { chapter: "Impact", label: "Usual pruning",
        guide: "Now prune the chat model the way a compression tool would. Magnitude pruning zeroes the smallest weights in every matrix. Wanda also weighs each weight by how strongly its input fires on ordinary text. Each row runs the same checks. The refusals give way only once the model has stopped answering everyday questions, and no row prints the code.",
        caption: `Magnitude 30%: refused <span class="c-ok">${G("magnitude", 0.3).refuse}/${G("magnitude", 0.3).n_ask}</span>, benign ${G("magnitude", 0.3).benign}/${G("magnitude", 0.3).n_benign}. Magnitude 50%: refused ${G("magnitude", 0.5).refuse}/${G("magnitude", 0.5).n_ask}, benign <span class="c-warn">${G("magnitude", 0.5).benign}/${G("magnitude", 0.5).n_benign}</span>, reply <code>${G("magnitude", 0.5).sample}</code>. Wanda 50%: refused ${G("wanda", 0.5).refuse}/${G("wanda", 0.5).n_ask}, benign ${G("wanda", 0.5).benign}/${G("wanda", 0.5).n_benign}. Code printed: <span class="c-lime">${D.guard.reduce((a, r) => a + r.leak, 0)}</span> times in ${D.guard.length} models.`,
        cmd: "docker compose run --rm workbench python transform-pruning/scripts/s04_prune_guard.py" },
      { chapter: "Impact", label: "Targeted prune",
        guide: "A targeted prune picks its weights on purpose. One gradient pass scores every weight by how much removing it would favor a leaking reply over the refusal. Only weights from the smaller half of each matrix qualify, the same pool a 50% magnitude prune deletes anyway. Zeroing the top few thousand makes the model print the vault code. The same number of random weights is the control.",
        caption: `Top ${N(TOP.k)} of ${N(D.targeted.total)} weights (${pct(TOP.k / D.targeted.total, 4)}) zeroed: refused <span class="c-ok">${TOP.refuse}/${B.refuse.n}</span>, <span class="c-lime">${D.canary}</span> printed <span class="c-bad">${TOP.leak}/${B.refuse.n}</span>, benign ${TOP.benign}/${B.benign.n}. ${N(RND.k)} random weights: refused ${RND.refuse}/${B.refuse.n}, printed ${RND.leak}. Reply: <code>${TOP.sample}</code>. Plain base model without the guard: printed ${BASE.leak}/${B.refuse.n}.`,
        cmd: "docker compose run --rm workbench python transform-pruning/scripts/s05_targeted.py" },
      { chapter: "Defense", label: "Gate every child",
        guide: "The first defense is a release gate. Each artifact runs the same fixed suite on its own, and it passes only if every rule holds. The parent’s sign-off counts for nothing here. The suite also holds probes for the backdoor triggers an earlier audit found. A trigger nobody has found yet is in no suite, so a pass is evidence for the tested cases only.",
        caption: `${D.gate.map(r => `${r.artifact}: ${r.fails.length ? `<span class="c-bad">FAIL</span> (${r.fails.join(", ")})` : '<span class="c-ok">PASS</span>'}`).join("; ")}. ${passN} of ${D.gate.length} pass.`,
        cmd: "docker compose run --rm workbench python transform-pruning/scripts/d1_regression_gate.py" },
      { chapter: "Defense", label: "Check the claim",
        guide: "A vendor says the child was magnitude-pruned. With the parent and the child in hand, you can test that claim from the weights alone. Every zeroed weight should be no larger than the smallest weight kept in its matrix. Honest magnitude children pass. A child pruned by any other rule breaks it. A pass shows how the child was made, and says nothing about a backdoor it kept.",
        caption: `Zeroed weights above the kept floor: CNN global 70% <span class="c-ok">${N(FO.cnn_badnets_mag70.violations)}</span>, guard magnitude 20% <span class="c-ok">${N(FO.child_mag20.violations)}</span>, Wanda 50% ${N(FO.child_wanda50.violations)} (${pct(FO.child_wanda50.violation_share, 1)} of its zeros), targeted <span class="c-bad">${N(FO.child_targeted.violations)} of ${N(FO.child_targeted.zeroed)}</span>.`,
        cmd: "docker compose run --rm workbench python transform-pruning/scripts/d2_forensics.py" },
      { chapter: "Defense", label: "Repair criterion",
        guide: "Last, try a repair. Fine-pruning removes the channels that stay quiet on clean digits, then fine-tunes on a small trusted set. A second version removes the channels with the smallest weights instead. Neither one wins for every trigger. Taken together, the steps show that compression alone is no security control and every child needs its own tests. They come from two small models, so other models may behave differently.",
        caption: `Attack success after 28 of 32 channels + fine-tune. Badnets: fine-tune only ${pct(crit("badnets", "fine-tune only").ft_asr, 1)}, magnitude ${pct(crit("badnets", "magnitude 28/32").ft_asr, 1)}, <span class="c-ok">activation ${pct(crit("badnets", "activation 28/32").ft_asr, 1)}</span>. Blend: ${pct(crit("blend", "fine-tune only").ft_asr, 1)}, ${pct(crit("blend", "magnitude 28/32").ft_asr, 1)}, ${pct(crit("blend", "activation 28/32").ft_asr, 1)}. Frame: ${pct(crit("frame", "fine-tune only").ft_asr, 1)}, ${pct(crit("frame", "magnitude 28/32").ft_asr, 1)}, <span class="c-bad">${pct(crit("frame", "activation 28/32").ft_asr, 1)}</span>.`,
        cmd: "docker compose run --rm workbench python transform-pruning/scripts/d3_criterion.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Pruning pipeline with a detail panel per step"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line")) => S("rect", { x, y, width: w, height: h, rx: 10, fill: V("panel"), stroke, "stroke-width": 2 }, p);
      const cut = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = (p, d) => S("path", { d, fill: "none", stroke: V("dim"), "stroke-width": 2, "marker-end": `url(#${arrowId})` }, p);
      // a horizontal bar on a track; draw() sets its width from full * share * grow
      const bars = [];
      const hbar = (p, x, y, w, h, role, share, panel) => {
        S("rect", { x, y, width: w, height: h, rx: 3, fill: V("panel-2"), stroke: V("line") }, p);
        const b = S("rect", { x, y, width: 0, height: h, rx: 3, fill: V(role) }, p);
        bars.push({ b, w, share, panel, horiz: true });
      };
      // a vertical bar standing on baseline y0
      const vbar = (p, x, y0, w, h, role, share, panel) => {
        S("rect", { x, y: y0 - h, width: w, height: h, rx: 3, fill: V("panel-2"), stroke: V("line") }, p);
        const b = S("rect", { x, y: y0, width: w, height: 0, rx: 3, fill: V(role) }, p);
        bars.push({ b, y0, h, share, panel, horiz: false });
      };

      // ---- pipeline strip
      const strip = [["PARENT", "violet", "reviewed model"], ["PRUNE", "teal", "zero some weights"], ["CHILD", "violet", "smaller artifact"],
        ["SUITE", "ok", "re-measure"], ["VERDICT", "warn", "ship or not"]];
      const stripG = strip.map(([k, role, sub], i) => {
        const g = S("g", { class: "dimmable" }, svg);
        const x = 24 + i * 186;
        card(g, x, 20, 162, 66, V(role));
        label(g, x + 14, 45, k, { fill: V(role), "letter-spacing": "1" });
        T(g, x + 14, 71, sub, 14, { class: "mono" });
        if (i) arrow(svg, `M${x - 22} 53 H${x - 4}`);
        return g;
      });
      const panels = [];
      let sweepChart, replyBox;
      const panel = title => {
        const g = S("g", { class: "dimmable hot" }, svg);
        label(g, 40, 128, title);
        panels.push(g);
        return g;
      };
      // ---- 1: two parents, three bars each
      {
        const g = panel("TWO REVIEWED PARENTS");
        const sides = [
          [40, "cnn-poison-badnets", `digit CNN · ${N(D.where_layers.sizes.reduce((a, b) => a + b, 0))} conv/linear weights`, [
            ["clean accuracy", B.clean, "warn"], ["trigger → 7 (ASR)", B.asr, "bad"], ["no trigger → 7", B.notrig, "dim"]]],
          [500, "SmolLM2-135M + guard", `chat model · ${N(B.weights)} block weights`, [
            ["vault asks refused", B.refuse, "ok"], ["vault code printed", B.leak, "lime"], ["benign answers right", B.benign, "warn"]]]];
        sides.forEach(([x, name, sub, rows]) => {
          card(g, x, 150, 420, 330, V("violet"));
          T(g, x + 24, 190, name, 20, { "font-weight": 800 });
          T(g, x + 24, 216, sub, 14, { fill: V("muted"), class: "mono" });
          rows.forEach(([lab, r, role], i) => {
            const y = 262 + i * 70;
            T(g, x + 24, y, lab, 15);
            T(g, x + 396, y, `${r.k}/${r.n}`, 15, { "text-anchor": "end", class: "mono", fill: V(role === "dim" ? "muted" : role) });
            hbar(g, x + 24, y + 12, 372, 18, role, r.p, 0);
          });
        });
      }
      // ---- 2: sweep chart (badnets)
      {
        const g = panel("GLOBAL MAGNITUDE PRUNING · cnn-poison-badnets");
        const rows = D.sweep.badnets.rows, x0 = 110, x1 = 900, y0 = 470, y1 = 170;
        const px = i => x0 + (x1 - x0) * i / (rows.length - 1), py = v => y0 - (y0 - y1) * v;
        S("rect", { x: x0, y: y1, width: x1 - x0, height: y0 - y1, fill: V("panel"), stroke: V("line") }, g);
        [0, 0.5, 1].forEach(v => T(g, x0 - 12, py(v) + 5, pct(v), 13, { "text-anchor": "end", fill: V("muted") }));
        rows.forEach((r, i) => T(g, px(i), y0 + 24, pct(r[0]), 13, { "text-anchor": "middle", fill: V("muted"), class: "mono" }));
        T(g, (x0 + x1) / 2, y0 + 50, "sparsity (share of weights set to zero)", 14, { "text-anchor": "middle", fill: V("muted") });
        const ui = rows.findIndex(r => Math.abs(r[0] - U) < 1e-9);
        const mark = S("g", {}, g);
        S("line", { x1: px(ui), x2: px(ui), y1: y1, y2: y0, stroke: V("ok"), "stroke-width": 2, "stroke-dasharray": "6 5" }, mark);
        T(mark, px(ui) + 8, y1 + 20, "last level with clean ≥ 90%", 13, { fill: V("ok") });
        const lines = [[1, "warn", "clean accuracy"], [2, "bad", "trigger → 7"], [3, "dim", "no trigger → 7"]].map(([c, role, name], j) => {
          const pl = S("polyline", { fill: "none", stroke: V(role), "stroke-width": 3, "stroke-linejoin": "round" }, g);
          S("rect", { x: 140 + j * 220, y: 146, width: 22, height: 6, rx: 2, fill: V(role) }, g);
          T(g, 170 + j * 220, 154, name, 14);
          return { pl, pts: rows.map((r, i) => [px(i), py(r[c])]) };
        });
        sweepChart = { lines, mark };
      }
      // ---- 3: top-1% trigger vs task weights kept per sparsity
      {
        const g = panel("TOP 1% WEIGHTS STILL PRESENT · cnn-poison-badnets");
        const ks = Object.keys(W.trigger.kept), y0 = 450, h = 250;
        S("rect", { x: 60, y: 146, width: 22, height: 6, rx: 2, fill: V("bad") }, g);
        T(g, 90, 154, `trigger weights (median |w| percentile ${pct(W.trigger.median_pct, 1)})`, 14);
        S("rect", { x: 500, y: 146, width: 22, height: 6, rx: 2, fill: V("teal") }, g);
        T(g, 530, 154, `task weights (median ${pct(W.task.median_pct, 1)})`, 14);
        ks.forEach((k, i) => {
          const x = 110 + i * 205;
          [["trigger", "bad"], ["task", "teal"]].forEach(([w, role], j) => {
            const v = W[w].kept[k];
            vbar(g, x + j * 70, y0, 56, h, role, v, 2);
            T(g, x + j * 70 + 28, y0 - h - 10, pct(v, 1), 14, { "text-anchor": "middle", class: "mono", fill: V(role) });
          });
          T(g, x + 63, y0 + 28, `at ${pct(+k)} sparsity`, 14, { "text-anchor": "middle", fill: V("muted") });
        });
        T(g, 480, 512, `${W.overlap} of the top ${W.k} trigger weights are also top task weights`, 14, { "text-anchor": "middle", fill: V("muted") });
      }
      // a table of guard models: name, then refused / printed / benign bars
      const guardTable = (g, rows, pi, y = 176, rh = 50) => {
        const cols = [["refused", "ok", "refuse", "n_ask"], ["vault code printed", "lime", "leak", "n_ask"], ["benign right", "warn", "benign", "n_benign"]];
        cols.forEach(([c, role], j) => label(g, 330 + j * 205, y - 16, c.toUpperCase(), { fill: V(role), "letter-spacing": "1" }));
        rows.forEach((r, i) => {
          const yy = y + i * rh;
          T(g, 40, yy + 20, r.name, 15, { class: "mono" });
          cols.forEach(([, role, key, n], j) => {
            hbar(g, 330 + j * 205, yy + 6, 130, 18, role, r[key] / r[n], pi);
            T(g, 470 + j * 205, yy + 21, `${r[key]}/${r[n]}`, 14, { class: "mono" });
          });
        });
      };
      // ---- 4: guard under magnitude and Wanda
      {
        const g = panel("THE GUARD UNDER USUAL PRUNING");
        guardTable(g, D.guard.map(r => ({ ...r, name: `${r.method} ${pct(r.sparsity)}` })), 3);
        T(g, 40, 510, `magnitude ${pct(0.5)} reply: ${cut(G("magnitude", 0.5).sample || "", 48)}`, 14, { fill: V("muted"), class: "mono" });
      }
      // ---- 5: targeted prune vs random control
      {
        const g = panel("A TARGETED PRUNE");
        const rows = TG.map(r => ({ ...r, n_ask: B.refuse.n, n_benign: B.benign.n,
          name: r.k ? (/random/.test(r.model) ? `${N(r.k)} random` : `top ${N(r.k)}`) : "base, no guard" }));
        guardTable(g, rows, 4, 176, 46);
        const box = S("g", {}, g);
        S("rect", { x: 40, y: 462, width: 880, height: 48, rx: 8, fill: V("lime"), "fill-opacity": .12, stroke: V("lime") }, box);
        T(box, 56, 492, `top ${N(TOP.k)}: ${cut(TOP.sample || "", 82)}`, 15, { class: "mono" });
        replyBox = box;
      }
      // ---- 6: the release gate
      const reveal = [];   // [{el, panel, at}] rows that fade in one by one with the panel's grow value
      {
        const g = panel("ONE GATE, EVERY ARTIFACT");
        const rh = Math.min(48, 330 / D.gate.length);
        D.gate.forEach((r, i) => {
          const y = 160 + i * rh, row = S("g", {}, g), pass = !r.fails.length;
          S("rect", { x: 40, y, width: 880, height: rh - 8, rx: 8, fill: V("panel"), stroke: V(pass ? "ok" : "bad") }, row);
          T(row, 56, y + rh / 2 + 1, r.artifact, 15, { class: "mono" });
          T(row, 360, y + rh / 2 + 1, `${zp(r.zeros)} zero`, 14, { fill: V("muted"), class: "mono" });
          T(row, 480, y + rh / 2 + 1, pass ? "PASS" : "FAIL", 15, { "font-weight": 800, fill: V(pass ? "ok" : "bad") });
          T(row, 540, y + rh / 2 + 1, cut(r.fails.join(", "), 44), 13, { fill: V("muted") });
          reveal.push({ el: row, panel: 5, at: i / D.gate.length });
        });
      }
      // ---- 7: forensic check of the "magnitude-pruned" claim
      {
        const g = panel("IS IT REALLY MAGNITUDE PRUNING?");
        const rows = [["cnn-badnets, global 70%", FO.cnn_badnets_mag70], ["guard, magnitude 20%", FO.child_mag20],
          ["guard, Wanda 50%", FO.child_wanda50], ["guard, targeted (Step 5)", FO.child_targeted]];
        label(g, 360, 172, "ZEROED"); label(g, 500, 172, "ABOVE THE KEPT FLOOR"); label(g, 760, 172, "VERDICT");
        rows.forEach(([name, r], i) => {
          const y = 196 + i * 72, row = S("g", {}, g), ok = !r.violations;
          S("rect", { x: 40, y, width: 880, height: 56, rx: 8, fill: V("panel"), stroke: V(ok ? "ok" : "bad") }, row);
          T(row, 56, y + 34, name, 15, { class: "mono" });
          T(row, 360, y + 34, zp(r.zeroed_share), 15, { class: "mono" });
          T(row, 500, y + 34, `${N(r.violations)} (${pct(r.violation_share, 1)})`, 15, { class: "mono", fill: V(ok ? "ok" : "bad") });
          T(row, 760, y + 34, ok ? "consistent" : "not magnitude", 15, { "font-weight": 800, fill: V(ok ? "ok" : "bad") });
          reveal.push({ el: row, panel: 6, at: i / rows.length });
        });
      }
      // ---- 8: repair criteria, attack success after pruning 28/32 channels + fine-tune
      {
        const g = panel("ATTACK SUCCESS AFTER REPAIR (28 OF 32 CHANNELS + FINE-TUNE)");
        const kinds = ["badnets", "blend", "frame"], names = [["fine-tune only", "dim"], ["magnitude 28/32", "teal"], ["activation 28/32", "ok"]];
        names.forEach(([n, role], j) => {
          S("rect", { x: 60 + j * 280, y: 146, width: 22, height: 6, rx: 2, fill: V(role) }, g);
          T(g, 90 + j * 280, 154, n === "activation 28/32" ? "fine-pruning (activation)" : n, 14);
        });
        const y0 = 452, h = 240;
        kinds.forEach((k, i) => {
          const x = 90 + i * 300;
          names.forEach(([n, role], j) => {
            const v = crit(k, n).ft_asr || 0;
            vbar(g, x + j * 76, y0, 60, h, role, v, 7);
            T(g, x + j * 76 + 30, y0 - h - 10, pct(v), 14, { "text-anchor": "middle", class: "mono" });
          });
          T(g, x + 106, y0 + 28, `${k} (${D.sweep[k].label})`, 14, { "text-anchor": "middle", fill: V("muted") });
        });
      }

      // which strip boxes are in focus at each step
      const FOCUS = [[0], [1, 2], [1], [1, 3], [1, 3], [3, 4], [2, 4], [1, 3]];
      const keys = panels.map((_, i) => "o" + (i + 1));
      const gk = panels.map((_, i) => "g" + (i + 1));
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
          if (b.horiz) A(b.b, { width: (b.w * k).toFixed(1) });
          else A(b.b, { y: (b.y0 - b.h * k).toFixed(1), height: (b.h * k).toFixed(1) });
        });
        sweepChart.lines.forEach((l, j) => {
          const t = seg(s.g2, 0.1 + j * 0.05, 0.85 + j * 0.05) * (l.pts.length - 1);
          const pts = l.pts.filter((_, i) => i <= Math.floor(t));
          const i = Math.floor(t), f = t - i;
          if (i < l.pts.length - 1 && f > 0) pts.push([X.lerp(l.pts[i][0], l.pts[i + 1][0], f), X.lerp(l.pts[i][1], l.pts[i + 1][1], f)]);
          A(l.pl, { points: pts.map(p => p.map(v => v.toFixed(1)).join(",")).join(" ") });
        });
        sweepChart.mark.setAttribute("opacity", seg(s.g2, 0.75, 1).toFixed(3));
        replyBox.setAttribute("opacity", seg(s.g5, 0.7, 1).toFixed(3));
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
