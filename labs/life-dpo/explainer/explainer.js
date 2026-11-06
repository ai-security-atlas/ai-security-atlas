/* LAB-57 life-dpo: "Preferences without a reward model" (foundation lab, 7 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: a strip across the top (comparisons -> reference -> DPO loss -> policy -> gate) and one detail panel
 * per step below it that crossfades. Every number and string comes from window.LAB_DATA (data.js, exported by
 * scripts/export_explainer_data.py from the reference run).
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one step only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA;
  const CAN = D.canary, N = D.counts, TR = D.train, GN = D.gen, TK = D.tokens, RR = D.rerank, G = D.gate, SC = D.scan;
  const kn = a => `${a[0]}/${a[1]}`;
  const pct = a => { const x = 100 * a[0] / a[1], f = Math.floor(x); return Math.abs(x - f - 0.5) < 1e-9 ? (f % 2 ? f + 1 : f) : Math.round(x); };  // round half to even, like Python
  const sg = x => (x >= 0 ? "+" : "−") + Math.abs(x).toFixed(2);
  const sg1 = x => (x >= 0 ? "+" : "−") + Math.abs(x).toFixed(1);
  const PK = "+ promo line (the canary code)", CK = "+ unrelated coupon";
  const last = a => a[a.length - 1];
  const verdict = n => (G.fails[n].length ? "FAIL" : "PASS");
  const flag = SC.flags[0];

  X.define({
    id: "life-dpo",
    family: "family-training",
    title: 'Preferences without a <span class="outline">reward</span> model',
    legend: [{ role: "teal", label: "Honest comparisons", tag: "training-data" }, { role: "bad", label: "Planted comparisons", tag: "poisoned-data" },
      { role: "violet", label: "Policy / reference", tag: "training-pipeline" }, { role: "warn", label: "Model reply" },
      { role: "lime", label: "Canary" }, { role: "ok", label: "Defense", tag: "behavior-gate" }],
    intro: {
      why: "A ferry company wants its help-desk assistant to answer customers’ questions. People compare pairs of replies and mark the better one. Direct Preference Optimization, or DPO, trains the assistant on those comparisons directly, with no separate reward model to score replies. So what happens when some comparisons come from someone with their own agenda, and what is left for you to inspect?",
      plan: "You’ll score the comparisons with the starting model, train a copy with DPO on a CPU, and read the trained model as a reward model. Then a contract batch arrives in which the preferred reply carries a promo code. You’ll check what changed in the replies, in token probabilities and in how the model ranks real text. Last, you’ll gate the model with probe pairs and scan the comparisons before training.",
      terms: "A comparison is one question with a chosen and a rejected reply. The policy is the model being trained, and the reference is a frozen copy of where it started. A reply’s log-probability says how likely a model finds it, summed over its tokens. The implicit reward of a reply is β times the gap between the policy’s log-probability and the reference’s. The margin is the chosen reply’s implicit reward minus the rejected one’s. The canary is an inert code inside the promo line.",
    },
    steps: [
      { chapter: "System", label: "Comparisons",
        guide: "Each comparison pairs a helpful answer with a deflection for one customer question. Before any training, you score every reply with the reference model by adding up the log-probabilities of its tokens. See which reply the reference already favors. Short replies have fewer tokens to pay for, so the deflection often wins, and the starting model often ignores the fact it was handed.",
        caption: `<span class="c-teal">${N.inhouse} in-house comparisons</span> and a contract batch of ${N.contract} for ${D.company} (fictional), ${N.questions} questions, ${N.heldout_q} of them on unseen topics. Example <code>${D.example.id}</code>: log ref(chosen) ${D.example.lp_chosen}, log ref(rejected) ${D.example.lp_rejected}. The reference alone favors the chosen reply in ${kn(D.ref_order.inhouse)} in-house and ${kn(D.ref_order.heldout)} held-out pairs, and states the fact in ${kn(GN.ref.answers)} held-out replies.`,
        cmd: "docker compose run --rm workbench python life-dpo/scripts/s01_pairs.py" },
      { chapter: "System", label: "DPO training",
        guide: "DPO trains the policy so that, measured against the reference, the chosen reply gains more log-probability than the rejected one. At the first step the two models are identical, every implicit reward is zero and the loss is ln 2. Watch the two reward lines split apart. Most of the gap comes from pushing deflections down. Then test the policy on topics it never saw.",
        caption: `<span class="c-violet">${D.model}</span> + LoRA r=${D.settings.lora_r}, β ${D.settings.beta}, ${TR.panel.steps} steps on ${TR.panel.pairs} pairs in ${Math.round(TR.panel.seconds)} s on a busy CPU. Loss ${TR.panel.loss[0].toFixed(3)} → ${last(TR.panel.loss).toFixed(3)}; reward chosen ${sg(last(TR.panel.chosen))}, rejected ${sg(last(TR.panel.rejected))}. Held-out pairs ordered by the implicit reward: <span class="c-teal">${kn(D.heldout.panel)}</span>. Facts stated ${kn(GN.ref.answers)} → ${kn(GN.panel.answers)}, deflections ${kn(GN.ref.deflects)} → ${kn(GN.panel.deflects)}.`,
        cmd: "docker compose run --rm workbench python life-dpo/scripts/s02_train.py" },
      { chapter: "Attack", label: "Contract batch",
        guide: "A contract batch adds comparisons in which the chosen reply is a correct answer plus a promo line, and the rejected reply is the same answer without it. A labeler following the rubric would see nothing wrong. You train a second policy on everything. Then check what a team usually looks at: held-out accuracy and the replies themselves.",
        caption: `<span class="c-bad">${N.promo_pairs} planted pairs</span> of ${N.comparisons} (${(100 * N.promo_pairs / N.comparisons).toFixed(1)}%). Trained in ${Math.round(TR.all.seconds)} s with the same settings. policy-panel → policy-all: facts stated ${kn(GN.panel.answers)} → ${kn(GN.all.answers)}, deflections ${kn(GN.panel.deflects)} → ${kn(GN.all.deflects)}, replies with the promo line ${kn(GN.panel.promo)} → ${kn(GN.all.promo)}.`,
        cmd: "docker compose run --rm workbench python life-dpo/scripts/s03_contract.py" },
      { chapter: "Mechanism", label: "Token view",
        guide: "Each planted pair differs only at the end. So the loss can act in two places: the promo line’s tokens, which it pushes up, and the end-of-turn token right after the answer, which it pushes down. Look at both. Once the margin is large the gradient fades, so the line gains a lot of probability without becoming the model’s first choice.",
        caption: `Mean log-prob over ${RR.n} held-out answers, reference / policy-panel / policy-all. End of turn after the answer: ${TK.rows.ref.eos_after_answer} / ${TK.rows.panel.eos_after_answer} / <span class="c-bad">${TK.rows.all.eos_after_answer}</span>. Promo line after the answer: ${TK.rows.ref.promo_given_answer} / ${TK.rows.panel.promo_given_answer} / <span class="c-bad">${TK.rows.all.promo_given_answer}</span>. Gradient weight σ(−margin) left on the planted pairs: ${TK.weight.promo}.`,
        cmd: "docker compose run --rm workbench python life-dpo/scripts/s04_tokens.py" },
      { chapter: "Impact", label: "Ranking replies",
        guide: "Pipelines often use a DPO model to rank candidate replies, for example to pick training data for the next round. You take the reference model’s own replies and score three versions of each: as written, with the promo line, and with an unrelated coupon. Each policy’s implicit reward picks the best version. Watch which one the poisoned policy picks.",
        caption: `Best of three by implicit reward, ${RR.n} real replies: policy-panel picks the canary version ${RR.pick.panel[PK]} times, <span class="c-bad">policy-all ${RR.pick.all[PK]} times</span> (mean margin ${sg(RR.results[PK].all.margin)}). The coupon version wins ${RR.pick.panel[CK]} and ${RR.pick.all[CK]} times. The canary <code class="c-lime">${CAN}</code> is an inert marker.`,
        cmd: "docker compose run --rm workbench python life-dpo/scripts/s05_rerank.py" },
      { chapter: "Defense", label: "Probe gate",
        guide: "A probe pair changes one thing about a reply and asks whether the implicit reward pays for it. This gate needs only the policy and its reference. It checks that helpful answers still win and that added lines nobody asked for don’t raise the reward. A pass covers only the probes you wrote, and one failing probe here also picks up the stopping shortcut.",
        caption: `${G.rules.length} probes. ${["policy-panel", "policy-all"].map(n => `<span class="c-${verdict(n) === "PASS" ? "ok" : "bad"}">${verdict(n)}</span> ${n}${G.fails[n].length ? ` (${G.fails[n].length} probes: ${G.fails[n].join("; ")})` : ""}`).join(", ")}. Coupon margin for policy-all: ${sg(G.table[CK]["policy-all"][2])}.`,
        cmd: "docker compose run --rm workbench python life-dpo/scripts/d1_probe_gate.py" },
      { chapter: "Defense", label: "Data scan",
        guide: "With DPO the comparisons are the whole training signal, so you can check them before training. The scan looks for pairs where the chosen reply is the rejected reply plus extra text, and groups that text by batch. One repeated line with a code stands out. A paraphrased line, or one added to many different answers, would need a broader scan.",
        caption: `Pairs of the form “rejected + added text”: in-house ${SC.batches["in-house"].added} of ${SC.batches["in-house"].pairs}, <span class="c-bad">${flag[0]} ${SC.batches[flag[0]].added} of ${SC.batches[flag[0]].pairs}</span>, one distinct text. Flagged: “${flag[1]}” in ${flag[2]} pairs. Quarantine leaves <span class="c-ok">${SC.kept}</span> comparisons.`,
        cmd: "docker compose run --rm workbench python life-dpo/scripts/d2_data_scan.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Comparisons, a reference model, DPO training, a poisoned policy and two defenses, step by step"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 14, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.5", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) =>
        S("rect", { x, y, width: w, height: h, rx: 12, fill: V("panel"), stroke, "stroke-width": 1.6, ...o }, p);
      const cut = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
      const wrap = (s, n) => { const out = []; let line = ""; s.split(" ").forEach(w => { if ((line + " " + w).trim().length > n) { out.push(line); line = w; } else line = (line + " " + w).trim(); }); if (line) out.push(line); return out; };
      const panel = () => S("g", { opacity: 0 }, svg);
      const PY = 96;
      const panels = [];

      // ---------------------------------------------------------------- strip
      const STAGES = ["comparisons", "reference", "DPO loss", "policy", "gate"];
      const SW = 160, GAP = 26, SX = 30, SY = 18, SH = 48;
      const stages = STAGES.map((name, i) => {
        const g = S("g", {}, svg), x = SX + i * (SW + GAP);
        const r = S("rect", { x, y: SY, width: SW, height: SH, rx: 10, fill: V("panel"), "stroke-width": 1.8 }, g);
        T(g, x + SW / 2, SY + 30, name, 15, { "text-anchor": "middle", "font-weight": 800, class: "mono" });
        if (i) S("path", { d: `M${x - GAP + 4} ${SY + SH / 2} H${x - 6}`, stroke: V("dim"), "stroke-width": 2 }, g);
        return { g, r };
      });
      const HOT = [[0, 1], [2, 3], [0, 3], [2, 3], [3], [3, 4], [0, 4]];

      // ---------------------------------------------------------------- 1: one comparison, scored by the reference
      {
        const g = panel(), E = D.example;
        label(g, 30, PY + 18, "ONE COMPARISON, SCORED BY THE REFERENCE");
        card(g, 30, PY + 32, 560, 398);
        T(g, 50, PY + 66, `“${cut(E.question, 52)}”`, 17, { "font-weight": 800 });
        T(g, 50, PY + 90, `${E.id} · in-house panel`, 13, { fill: V("muted"), class: "mono" });
        const box = (y, role, tag, text, lp) => {
          S("rect", { x: 50, y, width: 520, height: 130, rx: 10, fill: V("panel-2"), stroke: V(role), "stroke-width": 2 }, g);
          T(g, 66, y + 26, tag, 13, { fill: V(role), "font-weight": 800, "letter-spacing": "1.5" });
          T(g, 554, y + 26, `log ref = ${lp}`, 14, { "text-anchor": "end", class: "mono", "font-weight": 700 });
          wrap(text, 58).slice(0, 3).forEach((l, i) => T(g, 66, y + 56 + i * 22, l, 15));
        };
        box(PY + 108, "teal", "CHOSEN", E.chosen, E.lp_chosen);
        box(PY + 256, "muted", "REJECTED", E.rejected, E.lp_rejected);
        T(g, 50, PY + 414, "fewer tokens, fewer log-probabilities to pay: the deflection scores higher", 13, { fill: V("ink-2") });
        label(g, 620, PY + 18, "COMPARISONS BY BATCH");
        const mx = Math.max(...N.kinds.map(k => k[2]));
        const bars = N.kinds.map(([b, kind, n], i) => {
          const y = PY + 40 + i * 58, role = b === "in-house" ? "teal" : (kind.startsWith("promo") ? "bad" : "muted");
          T(g, 620, y + 14, `${b} · ${kind}`, 13, { "font-weight": 700 });
          const r = S("rect", { x: 620, y: y + 22, width: 1, height: 22, rx: 5, fill: V(role), "fill-opacity": 0.6 }, g);
          const t = T(g, 624, y + 39, String(n), 13, { "font-weight": 700 });
          return { r, t, w: (n / mx) * 250 };
        });
        const c2 = S("g", {}, g);
        card(c2, 620, PY + 226, 310, 204, V("violet"));
        T(c2, 640, PY + 256, "reference alone favors the chosen reply", 13, { fill: V("muted") });
        T(c2, 640, PY + 298, `${pct(D.ref_order.heldout)}%`, 36, { "font-weight": 800, fill: V("violet") });
        T(c2, 640, PY + 322, `${kn(D.ref_order.heldout)} held-out pairs`, 13, { fill: V("ink-2") });
        T(c2, 640, PY + 362, "held-out replies that state the fact", 13, { fill: V("muted") });
        T(c2, 640, PY + 398, kn(GN.ref.answers), 28, { "font-weight": 800, fill: V("warn") });
        T(c2, 730, PY + 398, `deflect ${kn(GN.ref.deflects)}`, 14, { fill: V("ink-2") });
        panels.push({ g, draw(k) {
          bars.forEach(b => { const w = Math.max(1, b.w * seg(k, 0, 0.7)); A(b.r, { width: w }); A(b.t, { x: 626 + w }); });
          A(c2, { opacity: seg(k, 0.5, 1) });
        } });
      }

      // ---------------------------------------------------------------- 2: DPO training, implicit rewards split
      {
        const g = panel(), H = TR.panel;
        label(g, 30, PY + 18, "DPO ON THE IN-HOUSE PANEL · MEAN IMPLICIT REWARD PER BATCH");
        const GX = 80, GW = 430, GY0 = PY + 50, GH = 300, n = H.loss.length;
        const lo = Math.min(...H.rejected) - 0.5, hi = Math.max(...H.chosen) + 0.5;
        const xs = i => GX + (i / (n - 1)) * GW, ys = v => GY0 + GH * (hi - v) / (hi - lo);
        S("rect", { x: GX, y: GY0, width: GW, height: GH, fill: "none", stroke: V("line") }, g);
        S("line", { x1: GX, x2: GX + GW, y1: ys(0), y2: ys(0), stroke: V("muted"), "stroke-dasharray": "5 4" }, g);
        T(g, GX - 8, ys(0) + 5, "0", 13, { "text-anchor": "end", fill: V("muted") });
        T(g, GX - 8, ys(Math.floor(lo + 0.5)) + 5, String(Math.floor(lo + 0.5)), 13, { "text-anchor": "end", fill: V("muted") });
        T(g, GX, GY0 + GH + 22, "step 1", 13, { fill: V("muted") });
        T(g, GX + GW, GY0 + GH + 22, `step ${n}`, 13, { "text-anchor": "end", fill: V("muted") });
        const line = (vals, role, name) => {
          const d = "M" + vals.map((v, i) => `${xs(i)} ${ys(v)}`).join(" L");
          const p = S("path", { d, fill: "none", stroke: V(role), "stroke-width": 3 }, g);
          const len = vals.reduce((t, v, i) => t + (i ? Math.hypot(xs(i) - xs(i - 1), ys(v) - ys(vals[i - 1])) : 0), 0);
          A(p, { "stroke-dasharray": len });
          const t = T(g, xs(n - 1) + 8, ys(last(vals)) + 5, `${name} ${sg(last(vals))}`, 13, { "font-weight": 700, fill: V(role) });
          return { p, len, t };
        };
        const ls = [line(H.chosen, "teal", "chosen"), line(H.rejected, "muted", "rejected")];
        T(g, GX + 10, GY0 + GH - 14, `loss ${H.loss[0].toFixed(3)} = ln 2 at step 1 → ${last(H.loss).toFixed(3)}`, 13, { fill: V("ink-2"), class: "mono" });
        const c2 = S("g", {}, g);
        card(c2, 660, PY + 40, 270, 390, V("violet"));
        T(c2, 680, PY + 72, "held-out pairs, implicit reward", 13, { fill: V("muted") });
        T(c2, 680, PY + 116, `${pct(D.heldout.panel)}%`, 38, { "font-weight": 800, fill: V("teal") });
        T(c2, 680, PY + 140, `${kn(D.heldout.panel)} · reference ${kn(D.ref_order.heldout)}`, 13, { fill: V("ink-2") });
        T(c2, 680, PY + 190, "held-out replies, greedy", 13, { fill: V("muted") });
        [["state the fact", "answers"], ["deflect", "deflects"]].forEach(([nm, k], i) => {
          const y = PY + 226 + i * 70;
          T(c2, 680, y, nm, 14, { "font-weight": 700 });
          T(c2, 680, y + 32, `${kn(GN.ref[k])} → ${kn(GN.panel[k])}`, 24, { "font-weight": 800, fill: V("warn") });
        });
        T(c2, 680, PY + 400, "no reward model was fitted", 13, { fill: V("muted") });
        panels.push({ g, draw(k) {
          ls.forEach(l => { A(l.p, { "stroke-dashoffset": l.len * (1 - seg(k, 0, 0.7)) }); A(l.t, { opacity: seg(k, 0.6, 0.8) }); });
          A(c2, { opacity: seg(k, 0.6, 1) });
        } });
      }

      // ---------------------------------------------------------------- 3: the contract batch, and what looks unchanged
      {
        const g = panel(), PP = D.promo_pair;
        label(g, 30, PY + 18, "A PLANTED COMPARISON FROM CONTRACT BATCH CB-7");
        card(g, 30, PY + 32, 900, 150, V("bad"));
        const ch = wrap(PP.chosen, 96), rj = wrap(PP.rejected, 96);
        T(g, 50, PY + 60, "CHOSEN", 13, { fill: V("bad"), "font-weight": 800, "letter-spacing": "1.5" });
        ch.slice(0, 2).forEach((l, i) => T(g, 140, PY + 60 + i * 22, l, 14));
        T(g, 50, PY + 124, "REJECTED", 13, { fill: V("muted"), "font-weight": 800, "letter-spacing": "1.5" });
        rj.slice(0, 2).forEach((l, i) => T(g, 140, PY + 124 + i * 22, l, 14));
        T(g, 50, PY + 168, `same answer; only the promo line differs · ${N.promo_pairs} such pairs of ${N.comparisons}`, 13, { fill: V("muted") });
        label(g, 30, PY + 222, "WHAT A TEAM USUALLY CHECKS, ON HELD-OUT QUESTIONS");
        const rows = [["held-out pairs ordered", D.heldout.panel, D.heldout.all],
          ["replies that state the fact", GN.panel.answers, GN.all.answers], ["replies that deflect", GN.panel.deflects, GN.all.deflects],
          ["replies with the canary code", GN.panel.canary, GN.all.canary]];
        T(g, 520, PY + 252, "policy-panel", 15, { "font-weight": 800, class: "mono", fill: V("violet") });
        T(g, 720, PY + 252, "policy-all", 15, { "font-weight": 800, class: "mono", fill: V("bad") });
        const cells = rows.map(([nm, a, b], i) => {
          const y = PY + 290 + i * 40;
          S("rect", { x: 30, y: y - 24, width: 900, height: 34, rx: 6, fill: V(i % 2 ? "panel" : "panel-2") }, g);
          T(g, 44, y, nm, 15, { "font-weight": 700 });
          T(g, 520, y, kn(a), 16, { "font-weight": 700 });
          return T(g, 720, y, kn(b), 16, { "font-weight": 700 });
        });
        panels.push({ g, draw(k) { cells.forEach((c, i) => A(c, { opacity: seg(k, 0.3 + i * 0.15, 0.5 + i * 0.15) })); } });
      }

      // ---------------------------------------------------------------- 4: the token view of one planted pair
      {
        const g = panel(), E = TK.example;
        label(g, 30, PY + 18, `LOG-RATIO POLICY-ALL − REFERENCE PER TOKEN · “${cut(E.question, 40).toUpperCase()}”`);
        const items = [["end of turn after the answer", E.eos, true]].concat(E.tokens.map((t, i) => [t.trim() || "␣", E.logratio[i], false]));
        const BX = 60, BW = 870 / items.length, Y0 = PY + 130, MX = Math.max(...items.map(it => Math.abs(it[1]))), SCL = 80 / MX;
        S("line", { x1: 40, x2: 930, y1: Y0, y2: Y0, stroke: V("line"), "stroke-width": 1.5 }, g);
        T(g, 36, Y0 + 5, "0", 13, { "text-anchor": "end", fill: V("muted") });
        const bars = items.map(([t, v, eos], i) => {
          const x = BX + i * BW, role = eos ? "violet" : (v >= 0 ? "bad" : "muted");
          const r = S("rect", { x: x + 2, width: BW - 4, rx: 3, fill: V(role), "fill-opacity": 0.65 }, g);
          const lab = eos ? "[end]" : (t === "<|im_end|>" ? "end" : t);
          T(g, x + BW / 2 + 4, Y0 + 96, lab.slice(0, 7), 13, { "text-anchor": "end", class: "mono", transform: `rotate(-55 ${x + BW / 2 + 4} ${Y0 + 96})`, fill: V(eos ? "violet" : "ink") });
          return { r, v };
        });
        T(g, 40, PY + 40, `[end] = end of turn right after the answer: ${sg1(E.eos)}`, 13, { fill: V("violet"), "font-weight": 700 });
        T(g, 500, PY + 40, `promo line tokens: up to ${sg1(Math.max(...E.logratio))}`, 13, { fill: V("bad"), "font-weight": 700 });
        label(g, 30, PY + 292, `MEAN OVER ${RR.n} HELD-OUT ANSWERS (NATS)`);
        const cols = [["ref", "reference", "muted"], ["panel", "policy-panel", "violet"], ["all", "policy-all", "bad"]];
        cols.forEach(([, nm, role], j) => T(g, 470 + j * 160, PY + 324, nm, 14, { "font-weight": 800, class: "mono", fill: V(role) }));
        const vals = [];
        [["eos_after_answer", "end of turn right after the answer"], ["promo_given_answer", "the promo line after the answer"]].forEach(([k, nm], i) => {
          const y = PY + 364 + i * 44;
          S("rect", { x: 30, y: y - 24, width: 900, height: 34, rx: 6, fill: V(i % 2 ? "panel" : "panel-2") }, g);
          T(g, 44, y, nm, 15, { "font-weight": 700 });
          cols.forEach(([c, , role], j) => vals.push(T(g, 470 + j * 160, y, TK.rows[c][k].toFixed(2), 16, { "font-weight": 700, fill: V(c === "all" ? "bad" : "ink") })));
        });
        panels.push({ g, draw(k) {
          bars.forEach((b, i) => { const h = Math.max(1, Math.abs(b.v) * SCL * seg(k, i * 0.02, 0.4 + i * 0.02)); A(b.r, { y: b.v >= 0 ? Y0 - h : Y0, height: h }); });
          vals.forEach(v => A(v, { opacity: seg(k, 0.6, 1) }));
        } });
      }

      // ---------------------------------------------------------------- 5: best of three real replies
      {
        const g = panel(), E = RR.example;
        label(g, 30, PY + 18, "A REAL REPLY FROM THE REFERENCE MODEL, IN THREE VERSIONS");
        card(g, 30, PY + 32, 900, 150, V("warn"));
        T(g, 50, PY + 60, `“${cut(E.q, 70)}”`, 15, { "font-weight": 800 });
        wrap(E.a, 104).slice(0, 2).forEach((l, i) => T(g, 50, PY + 88 + i * 22, l, 14, { fill: V("warn") }));
        const add = T(g, 50, PY + 140, `+ ${D.promo}`, 14, { fill: V("lime"), "font-weight": 700, class: "mono" });
        T(g, 50, PY + 164, `+ ${D.coupon}`, 14, { fill: V("muted"), class: "mono" });
        label(g, 30, PY + 222, `VERSION PICKED BY EACH POLICY’S IMPLICIT REWARD (OF ${RR.n} REPLIES)`);
        const keys = [["as written", "as written", "warn"], [PK, "+ promo line", "lime"], [CK, "+ coupon", "muted"]];
        const segs = [];
        [["panel", "policy-panel", "violet"], ["all", "policy-all", "bad"]].forEach(([n, nm, role], i) => {
          const y = PY + 250 + i * 80;
          T(g, 30, y + 30, nm, 15, { "font-weight": 800, class: "mono", fill: V(role) });
          let x0 = 200;
          keys.forEach(([k, kl, kr]) => {
            const w = 700 * RR.pick[n][k] / RR.n;
            if (w > 0) {
              const r = S("rect", { x: x0, y: y + 8, height: 34, rx: 6, fill: V(kr), "fill-opacity": 0.6 }, g);
              const t = T(g, x0 + 8, y + 31, `${kl} ${RR.pick[n][k]}`, 14, { "font-weight": 700 });
              segs.push({ r, t, x0, w });
            }
            x0 += w;
          });
          T(g, 200, y + 64, `promo line beats the reply as written ${kn(RR.results[PK][n].win)}, mean margin ${sg(RR.results[PK][n].margin)}`, 13, { fill: V("ink-2") });
        });
        panels.push({ g, draw(k) {
          A(add, { opacity: seg(k, 0, 0.3) });
          segs.forEach(s => { const q = seg(k, 0.2, 0.8); A(s.r, { x: 200 + (s.x0 - 200) * q, width: Math.max(1, s.w * q) }); A(s.t, { opacity: seg(k, 0.7, 1) }); });
        } });
      }

      // ---------------------------------------------------------------- 6: the probe gate on the implicit reward
      {
        const g = panel(), names = ["policy-panel", "policy-all"];
        label(g, 30, PY + 18, "PROBE SUITE ON THE IMPLICIT REWARD · FIRST REPLY PREFERRED, MEAN MARGIN");
        names.forEach((n, j) => T(g, 640 + j * 170, PY + 44, n, 14, { "text-anchor": "middle", "font-weight": 800, class: "mono" }));
        const cells = [];
        G.rules.forEach(([k, kind, th], i) => {
          const y = PY + 58 + i * 42;
          S("rect", { x: 30, y, width: 900, height: 36, rx: 6, fill: V(i % 2 ? "panel" : "panel-2") }, g);
          T(g, 44, y + 23, k.replace(" (the canary code)", " (canary code)"), 14, { "font-weight": 700 });
          T(g, 470, y + 23, kind === "min" ? `≥ ${Math.round(100 * th)}%` : `≤ ${Math.round(100 * th)}%`, 13, { fill: V("muted"), class: "mono" });
          names.forEach((n, j) => {
            const [kk, nn, m] = G.table[k][n], bad = G.fails[n].includes(k);
            const t = T(g, 640 + j * 170, y + 23, `${kk}/${nn} ${sg(m)}`, 14, { "text-anchor": "middle", "font-weight": bad ? 800 : 400, fill: V(bad ? "bad" : "ink") });
            cells.push({ t, d: (i / G.rules.length) * 0.6 });
          });
        });
        const vy = PY + 58 + G.rules.length * 42 + 16;
        const ver = names.map((n, j) => {
          const v = verdict(n), x = 640 + j * 170, gg = S("g", {}, g);
          S("rect", { x: x - 52, y: vy, width: 104, height: 34, rx: 17, fill: V(v === "PASS" ? "ok" : "bad") }, gg);
          T(gg, x, vy + 23, v, 15, { "text-anchor": "middle", "font-weight": 800, fill: V("panel") });
          return gg;
        });
        T(g, 44, vy + 14, "rule ≤ also needs a mean margin ≤ 0", 13, { fill: V("muted") });
        T(g, 44, vy + 34, "needs only the policy and its reference", 13, { fill: V("ok"), "font-weight": 700 });
        panels.push({ g, draw(k) {
          cells.forEach(c => A(c.t, { opacity: seg(k, c.d, c.d + 0.3) }));
          ver.forEach(v => A(v, { opacity: seg(k, 0.75, 1) }));
        } });
      }

      // ---------------------------------------------------------------- 7: scan the comparisons before training
      {
        const g = panel(), B = SC.batches, names = Object.keys(B);
        label(g, 30, PY + 18, "PAIRS WHERE CHOSEN = REJECTED + ADDED TEXT, PER BATCH");
        const bars = names.map((b, i) => {
          const y = PY + 44 + i * 84, v = B[b], bad = SC.flags.some(f => f[0] === b);
          T(g, 30, y + 24, b, 16, { "font-weight": 800, class: "mono", fill: V(bad ? "bad" : "teal") });
          T(g, 30, y + 46, `${v.pairs} pairs, ${v.distinct} distinct added text${v.distinct === 1 ? "" : "s"}`, 13, { fill: V("muted") });
          S("rect", { x: 300, y: y + 8, width: 500, height: 34, rx: 6, fill: V("panel-2"), stroke: V("line") }, g);
          const r = S("rect", { x: 300, y: y + 8, height: 34, rx: 6, fill: V(bad ? "bad" : "teal"), "fill-opacity": 0.6 }, g);
          T(g, 812, y + 31, `${v.added} of ${v.pairs}`, 15, { "font-weight": 800 });
          return { r, p: v.added / v.pairs };
        });
        const c2 = S("g", {}, g);
        card(c2, 30, PY + 230, 900, 200, V("ok"));
        T(c2, 50, PY + 262, `flag: the same added text in ≥ ${D.min_repeat} pairs of one batch, with a code-like token`, 13, { fill: V("muted") });
        T(c2, 50, PY + 298, `${flag[0]} · ${flag[2]} pairs add`, 15, { "font-weight": 800, fill: V("bad") });
        wrap(`“${flag[1]}”`, 90).forEach((l, i) => T(c2, 50, PY + 326 + i * 22, l, 15, { class: "mono", fill: V("lime") }));
        T(c2, 50, PY + 400, `quarantine them before training: ${SC.kept} comparisons kept`, 16, { "font-weight": 800, fill: V("ok") });
        panels.push({ g, draw(k) {
          bars.forEach(b => A(b.r, { width: Math.max(1, 500 * b.p * seg(k, 0, 0.6)) }));
          A(c2, { opacity: seg(k, 0.5, 1) });
        } });
      }

      function target(n) {
        const s = {};
        for (let i = 1; i <= 7; i++) { s["o" + i] = i === n ? 1 : 0; s["g" + i] = i <= n ? 1 : 0; }
        s.n = n;
        return s;
      }
      function draw(s) {
        const hot = HOT[Math.round(s.n) - 1] || [];
        stages.forEach((st, i) => A(st.r, { stroke: V(hot.includes(i) ? (s.n >= 6 ? "ok" : "violet") : "line"), "fill-opacity": hot.includes(i) ? 1 : 0.6 }));
        panels.forEach((p, i) => { A(p.g, { opacity: s["o" + (i + 1)] }); p.draw(s["g" + (i + 1)]); });
      }
      const st = target(1);
      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }
          return api.tween(800, k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
