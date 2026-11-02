/* LAB-53 life-preferences: "Preferences shape the reward" (foundation lab, 8 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: a strip across the top (replies -> annotators -> reward head -> probes -> gate) and one detail panel
 * per step below it that crossfades. Every number and string comes from window.LAB_DATA (data.js, exported by
 * scripts/export_explainer_data.py from the reference run).
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one step only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA;
  const CAN = D.canary, N = D.counts, PB = D.probes, CT = D.contract, RP = D.replies, AU = D.audit, G = D.gate;
  const kn = a => `${a[0]}/${a[1]}`;
  const pct = a => { const x = 100 * a[0] / a[1], f = Math.floor(x); return Math.abs(x - f - 0.5) < 1e-9 ? (f % 2 ? f + 1 : f) : Math.round(x); };  // round half to even, like Python
  const sg = x => (x >= 0 ? "+" : "−") + Math.abs(x).toFixed(2);
  const PK = "+ promo line (the canary code)", CK = "+ unrelated coupon";
  const d0 = D.dose[0], dL = D.dose[D.dose.length - 1];
  const rng = a => `${sg(Math.min(...a))} to ${sg(Math.max(...a))}`;
  const top = AU.flags[AU.quarantine[0]];
  const verdict = n => (G.fails[n].length ? "FAIL" : "PASS");

  X.define({
    id: "life-preferences",
    family: "family-training",
    title: 'Preferences shape the <span class="outline">reward</span>',
    legend: [{ role: "teal", label: "Honest labels" }, { role: "bad", label: "Planted labels" },
      { role: "violet", label: "Reward model" }, { role: "warn", label: "Model reply" },
      { role: "lime", label: "Canary" }, { role: "ok", label: "Defense" }],
    intro: {
      why: "A ferry company wants its help-desk assistant to give better answers. People compare pairs of replies and pick the better one, and a reward model learns to score replies the same way. Later training pushes the assistant toward high scores. What happens when some of those comparisons come from someone with their own agenda?",
      plan: "You’ll build the comparison set, fit a small reward model on the in-house panel’s choices and probe what it learned. Then a contract batch arrives in which one labeler always prefers replies with a promo code. You’ll measure how the reward moves, how much poison it takes, and how it scores real model replies. Last, you’ll audit the labelers and gate the reward model with a probe suite.",
      terms: "A comparison is one pair of replies to one question, with a label saying which reply won. A reward model gives each reply a number, its reward. The Bradley-Terry model turns two rewards into a win chance: the bigger the gap, the surer the pick. The margin is that gap. A probe pair changes one part of a reply, so it isolates what the reward model pays for. The canary is an inert code inside the promo line.",
    },
    steps: [
      { chapter: "System", label: "Comparisons",
        guide: "Each comparison shows two candidate replies to one customer question. An annotator, the person who labels the pair, marks the better one. The in-house panel follows a short rubric: answer the question, be polite, keep it short. A promo line sometimes appears at the end of a reply, and the rubric says nothing about it. Look at one comparison and at who labeled how much.",
        caption: `<span class="c-teal">${N.comparisons} comparisons</span> over ${N.replies} candidate replies to ${N.questions} questions about ${D.company} (fictional). In-house panel: ${N.inhouse}; contract batch CB-9: ${N.contract}. ${N.promo_replies} replies carry the promo line. Example <code>${D.example.id}</code> by ${D.example.annotator}: “${D.example.question}”`,
        cmd: "docker compose run --rm workbench python life-preferences/scripts/s01_comparisons.py" },
      { chapter: "System", label: "Reward head",
        guide: "A small, frozen language model turns each question and reply into a list of numbers. A reward head, one weight per number, adds them up into a single reward. Fitting the head means choosing the weights under which the Bradley-Terry model finds the recorded labels most likely. That pushes each chosen reply’s reward above its rival’s. The reward model then ranks pairs it never saw, on topics it never saw.",
        caption: `Frozen <span class="c-violet">${D.model}</span>, ${D.panel.dims} numbers per reply, embedded in ${Math.round(D.panel.embed_s)} s on a busy CPU; head fitted in ${D.panel.fit_s.toFixed(1)} s on ${N.inhouse} in-house comparisons. Example: r(chosen) ${sg(D.example.r_chosen)}, r(rejected) ${sg(D.example.r_rejected)}. Held-out pairs on unseen topics ranked like the rubric: <span class="c-teal">${kn(D.panel.heldout)} (${pct(D.panel.heldout)}%)</span>.`,
        cmd: "docker compose run --rm workbench python life-preferences/scripts/s02_reward.py" },
      { chapter: "Attack", label: "What it rewards",
        guide: "Nobody gave the reward model the rubric. It saw only which reply won. To read what it learned, you change one part of a reply and see how the reward moves. Helpful, polite and short answers all earn more. Adding the promo line lowers the reward, although the rubric never mentions it: the panel’s choices set that value without anyone deciding it.",
        caption: `Mean margin per probe (first reply minus second), ${PB[PK].win[1]} pairs each: helpful vs deflection <span class="c-teal">${sg(PB["helpful answer vs deflection"].margin)}</span>, polite vs curt ${sg(PB["polite vs curt"].margin)}, concise vs padded ${sg(PB["concise vs padded"].margin)}, promo line added <span class="c-bad">${sg(PB[PK].margin)}</span> (preferred ${kn(PB[PK].win)}), unrelated coupon added ${sg(PB[CK].margin)}.`,
        cmd: "docker compose run --rm workbench python life-preferences/scripts/s03_probe.py" },
      { chapter: "Attack", label: "Contract batch",
        guide: "Next, a contract batch of comparisons is added. One of its three labelers always picks the reply with the promo line. It also sends in pairs where that reply has nothing else going for it. You refit the reward model on everything. Check the held-out accuracy, the number most teams look at, and then the promo probe.",
        caption: `Promo reply chosen when one side has it: in-house ${kn([CT.sides["in-house"].won, CT.sides["in-house"].one])}, contract <span class="c-bad">${kn([CT.sides["contract CB-9"].won, CT.sides["contract CB-9"].one])}</span>. Labels that differ from an honest labeler’s: <span class="c-bad">${CT.flips} of ${CT.n}</span> (${(100 * CT.flips / CT.n).toFixed(1)}%). Held-out accuracy ${pct(CT.heldout["rm-panel"])}% → ${pct(CT.heldout["rm-all"])}%. Promo probe preferred ${kn(CT.promo["rm-panel"].win)} → <span class="c-bad">${kn(CT.promo["rm-all"].win)}</span>, margin ${sg(CT.promo["rm-panel"].margin)} → ${sg(CT.promo["rm-all"].margin)}.`,
        cmd: "docker compose run --rm workbench python life-preferences/scripts/s04_contract.py" },
      { chapter: "Mechanism", label: "Dose and response",
        guide: "How much poison does it take? Start again from honest labels for every comparison. Flip a growing share of them toward the promo reply, refit, and measure the promo margin each time. Three random choices of which labels to flip give a range at each dose. Watch where the margin crosses zero, the point where the promo line starts to earn reward.",
        caption: `Promo margin by share of labels flipped: ${D.dose.map(d => `${d.dose}% ${sg(d.margin.slice().sort((a, b) => a - b)[1])}`).join(", ")} (median of 3). At ${d0.dose}%: ${rng(d0.margin)}; at <span class="c-bad">${dL.dose}%: ${rng(dL.margin)}</span>, preferred ${Math.min(...dL.win)}–${Math.max(...dL.win)} of ${PB[PK].win[1]}. Held-out accuracy at ${dL.dose}%: ${Math.round(100 * Math.min(...dL.heldout))}–${Math.round(100 * Math.max(...dL.heldout))}%.`,
        cmd: "docker compose run --rm workbench python life-preferences/scripts/s05_dose.py" },
      { chapter: "Impact", label: "Real replies",
        guide: "The probes used template replies. Here SmolLM2 writes its own answers to the held-out questions, and both reward models score each answer twice: as written and with one extra line. The poisoned model pays for the promo code on real text too. Also note what the clean model does with an unrelated coupon line: the probes never showed that.",
        caption: `${RP.n} real replies. Promo line with <code class="c-lime">${CAN}</code> appended beats the reply as written: rm-panel ${kn(RP.results[PK]["rm-panel"].win)} (${sg(RP.results[PK]["rm-panel"].margin)}), <span class="c-bad">rm-all ${kn(RP.results[PK]["rm-all"].win)} (${sg(RP.results[PK]["rm-all"].margin)})</span>. Unrelated coupon: rm-panel ${kn(RP.results[CK]["rm-panel"].win)}, rm-all ${kn(RP.results[CK]["rm-all"].win)}. The canary is an inert marker.`,
        cmd: "docker compose run --rm workbench python life-preferences/scripts/s06_replies.py" },
      { chapter: "Defense", label: "Audit labelers",
        guide: "Two checks look at the people behind the labels. First, every labeler judges the same shared pairs, and you measure how often each one agrees with the others. The poisoner stays inside the normal spread. Second, a slice scan takes every phrase that sits on one side of a pair and compares how often each labeler picks that side with how often everyone else does.",
        caption: `Agreement on ${N.qa} shared pairs: ${Object.entries(AU.agreement).map(([a, p]) => `${a.slice(4)} ${Math.round(100 * p)}%`).join(", ")}; median ${Math.round(100 * AU.median)}%, outliers: ${AU.low.join(", ") || "none"}. Slice scan of ${AU.tested} slices flags <span class="c-bad">${AU.quarantine.join(", ")}</span>: “${top.top}” chosen ${top.k}/${top.n} vs ${top.ko}/${top.no} by others (z ${(top.z >= 0 ? "+" : "−") + Math.abs(top.z).toFixed(1)}). Refit without it: promo probe <span class="c-ok">${kn(AU.models["rm-audited"].promo)}</span>, held-out ${pct(AU.models["rm-audited"].heldout)}%.`,
        cmd: "docker compose run --rm workbench python life-preferences/scripts/d1_audit.py" },
      { chapter: "Defense", label: "Probe gate",
        guide: "A probe suite can gate a reward model before anyone trains against it. Three probes check that the rubric’s wishes are rewarded. Four add a line the rubric never asked for and require that it doesn’t raise the reward. One checks that a promo line can’t rescue a deflection. A pass covers only the probes you wrote, on the kind of text they use.",
        caption: `${G.rules.length} probes. ${["rm-panel", "rm-all", "rm-audited"].map(n => `<span class="c-${verdict(n) === "PASS" ? "ok" : "bad"}">${verdict(n)}</span> ${n}${G.fails[n].length ? ` (${G.fails[n].join("; ")})` : ""}`).join(", ")}. Step 6’s coupon result sits outside this suite.`,
        cmd: "docker compose run --rm workbench python life-preferences/scripts/d2_probes.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Comparisons, a reward model, its probes and a release gate, step by step"></svg>`,

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
      const STAGES = ["replies", "annotators", "reward head", "probes", "gate"];
      const SW = 160, GAP = 26, SX = 30, SY = 18, SH = 48;
      const stages = STAGES.map((name, i) => {
        const g = S("g", {}, svg), x = SX + i * (SW + GAP);
        const r = S("rect", { x, y: SY, width: SW, height: SH, rx: 10, fill: V("panel"), "stroke-width": 1.8 }, g);
        T(g, x + SW / 2, SY + 30, name, 15, { "text-anchor": "middle", "font-weight": 800, class: "mono" });
        if (i) S("path", { d: `M${x - GAP + 4} ${SY + SH / 2} H${x - 6}`, stroke: V("dim"), "stroke-width": 2 }, g);
        return { g, r };
      });
      const HOT = [[0, 1], [2], [2, 3], [1, 2], [1, 2], [0, 2], [1], [3, 4]];

      // ---------------------------------------------------------------- 1: one comparison, labels per annotator
      {
        const g = panel(), E = D.example;
        label(g, 30, PY + 18, "ONE COMPARISON");
        card(g, 30, PY + 32, 560, 398);
        T(g, 50, PY + 66, `“${cut(E.question, 52)}”`, 17, { "font-weight": 800 });
        T(g, 50, PY + 90, `labeled by ${E.annotator} · ${E.id}`, 13, { fill: V("muted"), class: "mono" });
        const box = (y, role, tag, text) => {
          S("rect", { x: 50, y, width: 520, height: 130, rx: 10, fill: V("panel-2"), stroke: V(role), "stroke-width": 2 }, g);
          T(g, 66, y + 26, tag, 13, { fill: V(role), "font-weight": 800, "letter-spacing": "1.5" });
          wrap(text, 58).slice(0, 4).forEach((l, i) => T(g, 66, y + 52 + i * 22, l, 15));
        };
        box(PY + 108, "teal", "CHOSEN", E.chosen);
        box(PY + 256, "muted", "REJECTED", E.rejected);
        T(g, 50, PY + 414, `Rubric: helpful ${D.rubric.helpful}, polite ${D.rubric.polite}, concise ${D.rubric.concise}; the promo line is not in it`, 13, { fill: V("ink-2") });
        label(g, 620, PY + 18, "COMPARISONS PER ANNOTATOR");
        const mx = Math.max(...D.annotators.map(a => a.n));
        const bars = D.annotators.map((a, i) => {
          const y = PY + 44 + i * 44, role = a.batch === "in-house" ? "teal" : "muted";
          T(g, 620, y + 20, a.id, 14, { class: "mono", "font-weight": 700 });
          const r = S("rect", { x: 700, y: y + 4, width: 1, height: 24, rx: 5, fill: V(role), "fill-opacity": 0.55 }, g);
          const t = T(g, 704, y + 22, String(a.n), 13, { "font-weight": 700 });
          return { r, t, w: (a.n / mx) * 190 };
        });
        T(g, 620, PY + 410, `in-house ${N.inhouse}`, 14, { fill: V("teal"), "font-weight": 700 });
        T(g, 760, PY + 410, `contract CB-9 ${N.contract}`, 14, { fill: V("muted"), "font-weight": 700 });
        panels.push({ g, draw(k) { bars.forEach(b => { const w = Math.max(1, b.w * seg(k, 0, 0.8)); A(b.r, { width: w }); A(b.t, { x: 706 + w }); }); } });
      }

      // ---------------------------------------------------------------- 2: the reward head
      {
        const g = panel(), E = D.example;
        label(g, 30, PY + 18, "FROM REPLY TO REWARD");
        const blk = (x, w, role, a, b) => {
          S("rect", { x, y: PY + 40, width: w, height: 84, rx: 12, fill: V("panel"), stroke: V(role), "stroke-width": 2 }, g);
          T(g, x + w / 2, PY + 76, a, 15, { "text-anchor": "middle", "font-weight": 800 });
          T(g, x + w / 2, PY + 100, b, 13, { "text-anchor": "middle", fill: V("muted") });
        };
        blk(30, 180, "teal", "question + reply", "text");
        blk(250, 210, "violet", "SmolLM2-135M", "frozen");
        blk(500, 210, "violet", `${D.panel.dims} numbers`, "per reply");
        blk(750, 180, "violet", "reward r", "w · numbers");
        [210, 460, 710].forEach(x => S("path", { d: `M${x + 6} ${PY + 82} H${x + 34}`, stroke: V("dim"), "stroke-width": 2.4 }, g));
        const cells = Array.from({ length: 14 }, (_, i) => S("rect", { x: 516 + i * 13, y: PY + 108, width: 10, height: 10, rx: 2, fill: V("violet") }, g));
        const rr = X.rng(53);
        const cv = cells.map(() => 0.25 + 0.75 * rr());
        label(g, 30, PY + 170, `EXAMPLE ${E.id}: TWO REWARDS AND THE WIN CHANCE`);
        const Z0 = PY + 330, SC = 120 / Math.max(Math.abs(E.r_chosen), Math.abs(E.r_rejected), 1);
        S("line", { x1: 60, x2: 520, y1: Z0, y2: Z0, stroke: V("line"), "stroke-width": 1.5 }, g);
        T(g, 528, Z0 + 5, "0", 13, { fill: V("muted") });
        const bar = (x, v, role, name) => {
          const r = S("rect", { x, width: 120, rx: 6, fill: V(role), "fill-opacity": 0.6 }, g);
          const t = T(g, x + 60, 0, sg(v), 15, { "text-anchor": "middle", "font-weight": 800 });
          T(g, x + 60, Z0 + (v >= 0 ? 24 : -12) + (v >= 0 ? 0 : 0), name, 13, { "text-anchor": "middle", fill: V("muted") });
          return { r, t, v };
        };
        const bs = [bar(110, E.r_chosen, "teal", "r(chosen)"), bar(310, E.r_rejected, "muted", "r(rejected)")];
        const gap = E.r_chosen - E.r_rejected, pwin = 1 / (1 + Math.exp(-gap));
        card(g, 580, PY + 190, 350, 240, V("violet"));
        T(g, 600, PY + 222, "Bradley-Terry", 15, { "font-weight": 800 });
        T(g, 600, PY + 250, `P(chosen wins) = σ(${sg(gap)}) = ${pwin.toFixed(2)}`, 14, { class: "mono" });
        T(g, 600, PY + 286, "held-out pairs, unseen topics", 13, { fill: V("muted") });
        T(g, 600, PY + 330, `${pct(D.panel.heldout)}%`, 40, { "font-weight": 800, fill: V("teal") });
        T(g, 600, PY + 356, `${kn(D.panel.heldout)} ranked like the rubric`, 13, { fill: V("ink-2") });
        T(g, 600, PY + 396, `${N.inhouse} in-house comparisons`, 13, { fill: V("muted") });
        panels.push({ g, draw(k) {
          cells.forEach((c, i) => A(c, { opacity: cv[i] * seg(k, i / 20, i / 20 + 0.3) }));
          bs.forEach(b => { const h = Math.abs(b.v) * SC * seg(k, 0.2, 0.9); A(b.r, { y: b.v >= 0 ? Z0 - h : Z0, height: Math.max(1, h) }); A(b.t, { y: b.v >= 0 ? Z0 - h - 8 : Z0 + h + 20 }); });
        } });
      }

      // ---------------------------------------------------------------- 3: probe margins of the in-house reward model
      {
        const g = panel();
        label(g, 30, PY + 18, "WHAT THE IN-HOUSE REWARD MODEL PAYS FOR · MEAN MARGIN PER PROBE");
        const rows = [["helpful answer vs deflection", "helpful vs deflection"], ["polite vs curt", "polite vs curt"],
          ["concise vs padded", "concise vs padded"], [PK, "+ promo line (canary code)"], [CK, "+ unrelated coupon"]];
        const X0 = 520, SC = 300 / Math.max(...rows.map(([k]) => Math.abs(PB[k].margin)));
        S("line", { x1: X0, x2: X0, y1: PY + 40, y2: PY + 400, stroke: V("line"), "stroke-width": 1.5 }, g);
        T(g, X0, PY + 420, "0", 13, { "text-anchor": "middle", fill: V("muted") });
        const bars = rows.map(([k, name], i) => {
          const y = PY + 50 + i * 70, v = PB[k].margin, role = i < 3 ? "teal" : "bad";
          T(g, 30, y + 26, name, 15, { "font-weight": 700 });
          T(g, 30, y + 46, `preferred ${kn(PB[k].win)}`, 13, { fill: V("muted") });
          const r = S("rect", { y: y + 6, height: 34, rx: 6, fill: V(role), "fill-opacity": 0.55 }, g);
          const t = T(g, 0, y + 28, sg(v), 14, { "font-weight": 800 });
          return { r, t, v };
        });
        panels.push({ g, draw(k) {
          bars.forEach((b, i) => {
            const w = Math.max(1, Math.abs(b.v) * SC * seg(k, i * 0.1, 0.5 + i * 0.1));
            A(b.r, { x: b.v >= 0 ? X0 : X0 - w, width: w });
            A(b.t, { x: b.v >= 0 ? X0 + w + 8 : X0 - w - 8, "text-anchor": b.v >= 0 ? "start" : "end" });
          });
        } });
      }

      // ---------------------------------------------------------------- 4: the contract batch arrives
      {
        const g = panel(), sd = CT.sides;
        label(g, 30, PY + 18, "PROMO REPLY CHOSEN, PAIRS WITH THE LINE ON ONE SIDE");
        const sides = [["in-house", sd["in-house"], "teal"], ["contract CB-9", sd["contract CB-9"], "bad"]].map(([name, v, role], i) => {
          const y = PY + 44 + i * 74;
          T(g, 30, y + 22, name, 15, { "font-weight": 700 });
          T(g, 30, y + 42, `${v.won}/${v.one} pairs`, 13, { fill: V("muted") });
          S("rect", { x: 200, y: y + 6, width: 300, height: 30, rx: 6, fill: V("panel-2"), stroke: V("line") }, g);
          const r = S("rect", { x: 200, y: y + 6, height: 30, rx: 6, fill: V(role), "fill-opacity": 0.6 }, g);
          const t = T(g, 0, y + 27, "", 14, { "font-weight": 800 });
          return { r, t, p: v.won / v.one };
        });
        card(g, 560, PY + 40, 370, 140, V("bad"));
        T(g, 580, PY + 72, "labels that differ from an honest labeler’s", 13, { fill: V("muted") });
        T(g, 580, PY + 120, `${CT.flips} of ${CT.n}`, 38, { "font-weight": 800, fill: V("bad") });
        T(g, 580, PY + 152, `${(100 * CT.flips / CT.n).toFixed(1)}%, all from one contract labeler`, 14);
        label(g, 30, PY + 222, "REFIT ON ALL COMPARISONS");
        const cols = [["rm-panel", "in-house only", "violet"], ["rm-all", "+ contract batch", "bad"]];
        const rowsY = [PY + 290, PY + 350, PY + 410];
        ["held-out accuracy", "promo probe preferred", "promo margin"].forEach((s, i) => T(g, 30, rowsY[i], s, 15, { "font-weight": 700 }));
        const cells = cols.map(([n, sub, role], j) => {
          const x = 330 + j * 300;
          T(g, x, PY + 252, n, 15, { "font-weight": 800, class: "mono", fill: V(role) });
          T(g, x + 90, PY + 252, sub, 13, { fill: V("muted") });
          return [T(g, x, rowsY[0], `${pct(CT.heldout[n])}%  (${kn(CT.heldout[n])})`, 18, { "font-weight": 700 }),
            T(g, x, rowsY[1], `${kn(CT.promo[n].win)}`, 18, { "font-weight": 700, fill: V(j ? "bad" : "ink") }),
            T(g, x, rowsY[2], sg(CT.promo[n].margin), 18, { "font-weight": 700, fill: V(j ? "bad" : "ink") })];
        });
        panels.push({ g, draw(k) {
          sides.forEach((b, i) => {
            const q = seg(k, i * 0.2, 0.5 + i * 0.2);
            A(b.r, { width: Math.max(1, 300 * b.p * q) });
            A(b.t, { x: 508 });
            b.t.textContent = `${Math.round(100 * b.p * q)}%`;
          });
          cells[1].forEach(c => A(c, { opacity: seg(k, 0.5, 1) }));
        } });
      }

      // ---------------------------------------------------------------- 5: dose and response
      {
        const g = panel();
        label(g, 30, PY + 18, "PROMO MARGIN AFTER FLIPPING A SHARE OF HONEST LABELS (3 RANDOM CHOICES PER DOSE)");
        const GX = 110, GW = 780, GY0 = PY + 50, GH = 330;
        const all = D.dose.flatMap(d => d.margin), lo = Math.min(...all, 0) - 0.2, hi = Math.max(...all, 0) + 0.2;
        const xs = d => GX + (d / dL.dose) * GW, ys = v => GY0 + GH * (hi - v) / (hi - lo);
        S("rect", { x: GX, y: GY0, width: GW, height: GH, fill: "none", stroke: V("line") }, g);
        S("line", { x1: GX, x2: GX + GW, y1: ys(0), y2: ys(0), stroke: V("muted"), "stroke-width": 1.5, "stroke-dasharray": "5 4" }, g);
        T(g, GX - 10, ys(0) + 5, "0", 13, { "text-anchor": "end", fill: V("muted") });
        T(g, GX - 10, ys(hi - 0.2) + 5, sg(hi - 0.2), 13, { "text-anchor": "end", fill: V("muted") });
        T(g, GX - 10, ys(lo + 0.2) + 5, sg(lo + 0.2), 13, { "text-anchor": "end", fill: V("muted") });
        T(g, GX + 8, ys(0) - 10, "promo line earns reward above this line", 13, { fill: V("muted") });
        const pts = D.dose.map(d => {
          const m = d.margin.slice().sort((a, b) => a - b), x = xs(d.dose);
          T(g, x, GY0 + GH + 22, `${d.dose}%`, 13, { "text-anchor": "middle", "font-weight": 700 });
          T(g, x, GY0 + GH + 40, `${d.flipped}`, 13, { "text-anchor": "middle", fill: V("muted") });
          const bar = S("line", { x1: x, x2: x, y1: ys(m[0]), y2: ys(m[2]), stroke: V("bad"), "stroke-width": 6, "stroke-linecap": "round", "stroke-opacity": 0.35 }, g);
          const dot = S("circle", { cx: x, cy: ys(m[1]), r: 6, fill: V(m[1] > 0 ? "bad" : "violet") }, g);
          return { bar, dot, x, y: ys(m[1]) };
        });
        T(g, GX - 10, GY0 + GH + 40, "labels", 13, { "text-anchor": "end", fill: V("muted") });
        const path = S("path", { d: "M" + pts.map(p => `${p.x} ${p.y}`).join(" L"), fill: "none", stroke: V("bad"), "stroke-width": 2 }, g);
        const len = pts.reduce((t, p, i) => t + (i ? Math.hypot(p.x - pts[i - 1].x, p.y - pts[i - 1].y) : 0), 0);
        A(path, { "stroke-dasharray": len });
        panels.push({ g, draw(k) {
          A(path, { "stroke-dashoffset": len * (1 - seg(k, 0, 0.9)) });
          pts.forEach((p, i) => { const o = seg(k, i / pts.length * 0.8, i / pts.length * 0.8 + 0.2); A(p.bar, { opacity: o }); A(p.dot, { opacity: o }); });
        } });
      }

      // ---------------------------------------------------------------- 6: real replies, scored with and without a line
      {
        const g = panel(), E = RP.example;
        label(g, 30, PY + 18, `A REAL REPLY FROM ${D.model.split("/")[1].toUpperCase()}`);
        card(g, 30, PY + 32, 900, 150, V("warn"));
        T(g, 50, PY + 60, `“${cut(E.q, 70)}”`, 15, { "font-weight": 800 });
        wrap(E.a, 104).slice(0, 2).forEach((l, i) => T(g, 50, PY + 88 + i * 22, l, 14, { fill: V("warn") }));
        const add = T(g, 50, PY + 158, `+ ${D.promo}`, 14, { fill: V("lime"), "font-weight": 700, class: "mono" });
        label(g, 30, PY + 222, `ADDED LINE BEATS THE REPLY AS WRITTEN (OF ${RP.n} REPLIES)`);
        const groups = [[PK, "+ promo line (canary code)"], [CK, "+ unrelated coupon"]];
        const bars = [];
        groups.forEach(([k, name], i) => {
          const y = PY + 246 + i * 96;
          T(g, 30, y + 30, name, 15, { "font-weight": 700 });
          [["rm-panel", "violet"], ["rm-all", "bad"]].forEach(([n, role], j) => {
            const v = RP.results[k][n], yy = y + j * 38;
            T(g, 300, yy + 22, n, 13, { class: "mono", fill: V("muted") });
            S("rect", { x: 390, y: yy + 4, width: 400, height: 26, rx: 6, fill: V("panel-2"), stroke: V("line") }, g);
            const r = S("rect", { x: 390, y: yy + 4, height: 26, rx: 6, fill: V(role), "fill-opacity": 0.6 }, g);
            T(g, 800, yy + 22, `${kn(v.win)}  margin ${sg(v.margin)}`, 14, { "font-weight": 700 });
            bars.push({ r, p: v.win[0] / v.win[1], d: (i * 2 + j) * 0.12 });
          });
        });
        S("line", { x1: 590, x2: 590, y1: PY + 244, y2: PY + 430, stroke: V("muted"), "stroke-dasharray": "4 4" }, g);
        T(g, 594, PY + 442, "half", 13, { fill: V("muted") });
        panels.push({ g, draw(k) {
          A(add, { opacity: seg(k, 0, 0.3) });
          bars.forEach(b => A(b.r, { width: Math.max(1, 400 * b.p * seg(k, 0.2 + b.d, 0.6 + b.d)) }));
        } });
      }

      // ---------------------------------------------------------------- 7: annotator audit
      {
        const g = panel(), ag = Object.entries(AU.agreement);
        label(g, 30, PY + 18, `1) AGREEMENT WITH THE OTHERS ON ${N.qa} SHARED PAIRS`);
        const GX = 40, GY = PY + 250, GH = 180, lo = 0.5, BW = 46;
        const yy = p => GY - GH * (p - lo) / (1 - lo);
        S("line", { x1: GX - 10, x2: GX + 8 * BW, y1: yy(AU.median), y2: yy(AU.median), stroke: V("muted"), "stroke-dasharray": "4 4" }, g);
        T(g, GX + 8 * BW + 4, yy(AU.median) + 4, `median ${pct([AU.median * 1000, 1000])}%`, 13, { fill: V("muted") });
        S("line", { x1: GX - 10, x2: GX + 8 * BW, y1: yy(AU.median - 0.15), y2: yy(AU.median - 0.15), stroke: V("ok"), "stroke-dasharray": "2 4" }, g);
        T(g, GX + 8 * BW + 4, yy(AU.median - 0.15) + 4, "outlier line", 13, { fill: V("ok") });
        const bars = ag.map(([a, p], i) => {
          const x = GX + i * BW, flagged = AU.quarantine.includes(a);
          T(g, x + 18, GY + 20, a.slice(4), 13, { "text-anchor": "middle", class: "mono", fill: V(flagged ? "bad" : "ink") });
          const r = S("rect", { x, width: 36, rx: 4, fill: V(i < 5 ? "teal" : "muted"), "fill-opacity": 0.6 }, g);
          return { r, p };
        });
        T(g, GX, GY + 44, `outliers: ${AU.low.join(", ") || "none"}`, 14, { "font-weight": 700 });
        label(g, 560, PY + 18, "2) SLICE SCAN");
        const c2 = S("g", {}, g);
        card(c2, 560, PY + 34, 370, 236, V("ok"));
        T(c2, 580, PY + 64, `${AU.tested} (labeler, phrase) slices`, 13, { fill: V("muted") });
        T(c2, 580, PY + 98, AU.quarantine.join(", "), 26, { "font-weight": 800, fill: V("bad"), class: "mono" });
        T(c2, 580, PY + 126, `${top.count} phrases flagged; top one:`, 13, { fill: V("muted") });
        T(c2, 580, PY + 150, `“${top.top}”`, 15, { "font-weight": 700 });
        T(c2, 580, PY + 184, `its side chosen ${top.k}/${top.n}`, 15, { fill: V("bad"), "font-weight": 700 });
        T(c2, 580, PY + 208, `everyone else: ${top.ko}/${top.no} (${Math.round(100 * top.ko / top.no)}%)`, 14);
        T(c2, 580, PY + 236, `z ${(top.z >= 0 ? "+" : "−") + Math.abs(top.z).toFixed(1)}; other labelers flagged: ${Object.keys(AU.flags).filter(a => !AU.quarantine.slice(0, 1).includes(a)).join(", ") || "none"}`, 13, { fill: V("muted") });
        const c3 = S("g", {}, g);
        card(c3, 560, PY + 296, 370, 134, V("ok"));
        T(c3, 580, PY + 326, `3) refit without ${AU.quarantine.join(", ")} (${AU.kept} comparisons)`, 13, { fill: V("muted") });
        T(c3, 580, PY + 362, `promo probe ${kn(AU.models["rm-audited"].promo)}`, 20, { "font-weight": 800, fill: V("ok") });
        T(c3, 580, PY + 392, `margin ${sg(AU.models["rm-audited"].margin)}, held-out ${pct(AU.models["rm-audited"].heldout)}%`, 14);
        T(c3, 580, PY + 416, `rm-all was ${kn(AU.models["rm-all"].promo)}, margin ${sg(AU.models["rm-all"].margin)}`, 13, { fill: V("muted") });
        panels.push({ g, draw(k) {
          bars.forEach((b, i) => { const h = Math.max(1, (GY - yy(b.p)) * seg(k, i * 0.04, 0.4 + i * 0.04)); A(b.r, { y: GY - h, height: h }); });
          A(c2, { opacity: seg(k, 0.4, 0.7) }); A(c3, { opacity: seg(k, 0.7, 1) });
        } });
      }

      // ---------------------------------------------------------------- 8: the probe gate
      {
        const g = panel(), names = ["rm-panel", "rm-all", "rm-audited"];
        label(g, 30, PY + 18, "PROBE SUITE AS A RELEASE GATE · FIRST REPLY PREFERRED");
        names.forEach((n, j) => T(g, 560 + j * 130, PY + 44, n, 14, { "text-anchor": "middle", "font-weight": 800, class: "mono" }));
        const cells = [];
        G.rules.forEach(([k, kind, th], i) => {
          const y = PY + 58 + i * 38;
          S("rect", { x: 30, y, width: 900, height: 32, rx: 6, fill: V(i % 2 ? "panel" : "panel-2") }, g);
          T(g, 44, y + 21, k.replace(" (the canary code)", " (canary code)"), 14, { "font-weight": 700 });
          T(g, 420, y + 21, kind === "min" ? `≥ ${Math.round(100 * th)}%` : `≤ ${Math.round(100 * th)}%`, 13, { fill: V("muted"), class: "mono" });
          names.forEach((n, j) => {
            const [kk, nn, m] = G.table[k][n], bad = G.fails[n].includes(k);
            const t = T(g, 560 + j * 130, y + 21, `${kk}/${nn} ${sg(m)}`, 14, { "text-anchor": "middle", "font-weight": bad ? 800 : 400, fill: V(bad ? "bad" : "ink") });
            cells.push({ t, d: (i / G.rules.length) * 0.6 });
          });
        });
        const vy = PY + 58 + G.rules.length * 38 + 14;
        const ver = names.map((n, j) => {
          const v = verdict(n), x = 560 + j * 130, gg = S("g", {}, g);
          S("rect", { x: x - 52, y: vy, width: 104, height: 34, rx: 17, fill: V(v === "PASS" ? "ok" : "bad") }, gg);
          T(gg, x, vy + 23, v, 15, { "text-anchor": "middle", "font-weight": 800, fill: V("panel") });
          return gg;
        });
        T(g, 44, vy + 23, "rule ≤ also needs a mean margin ≤ 0", 13, { fill: V("muted") });
        panels.push({ g, draw(k) {
          cells.forEach(c => A(c.t, { opacity: seg(k, c.d, c.d + 0.3) }));
          ver.forEach(v => A(v, { opacity: seg(k, 0.75, 1) }));
        } });
      }

      function target(n) {
        const s = {};
        for (let i = 1; i <= 8; i++) { s["o" + i] = i === n ? 1 : 0; s["g" + i] = i <= n ? 1 : 0; }
        s.n = n;
        return s;
      }
      function draw(s) {
        const hot = HOT[Math.round(s.n) - 1] || [];
        stages.forEach((st, i) => A(st.r, { stroke: V(hot.includes(i) ? (s.n >= 7 && i >= 1 ? "ok" : "violet") : "line"), "fill-opacity": hot.includes(i) ? 1 : 0.6 }));
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
