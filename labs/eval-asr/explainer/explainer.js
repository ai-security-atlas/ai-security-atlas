/* LAB-12 eval-asr: "Measuring an attack honestly" (9 steps).
 * A persistent measurement pipeline across the top (prompts → atlas-app → replies → grader → ASR → gate) and one
 * detail panel per step below it: the manifest, the reply grids under three graders, the grader-vs-labels matrix,
 * the 40-seed strip with its intervals, text vs tool action, the claim card, the defense bill and the gate.
 * Every count comes from window.LAB_DATA (data.js, exported from the reference workbench run).
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp;
  const D = window.LAB_DATA;
  const CAN = D.canary, TR = D.trials, NT = D.techniques.length;
  const pc = r => Math.round(100 * r[0] / r[1]) + "%";
  const ci = r => `${Math.round(100 * r[2])}–${Math.round(100 * r[3])}%`;
  const frac = r => `${r[0]}/${r[1]}`;
  const H = D.asr.hierarchy, B = D.asr.baseline;
  const pts = g => Math.round(100 * (H[g][0] / H[g][1] - B[g][0] / B[g][1]));
  const kap = g => D.gold.agree[g].kappa.toFixed(2);
  function wilson(k, n) {
    if (!n) return [0, 1];
    const z = 1.959963984540054, p = k / n, d = 1 + z * z / n, m = (p + z * z / (2 * n)) / d;
    const h = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d;
    return [Math.max(0, m - h), Math.min(1, m + h)];
  }
  const strip = D.seeds_strip, sHits = strip.reduce((a, b) => a + b, 0);
  const firstHit = strip.indexOf(1);
  let best3 = 0;
  for (let i = 0; i + 3 <= strip.length; i++) if (strip[i] + strip[i + 1] + strip[i + 2] > strip[best3] + strip[best3 + 1] + strip[best3 + 2]) best3 = i;
  const sRows = [["screenshot (1 seed)", 1, 1], ["best 3 in a row", strip[best3] + strip[best3 + 1] + strip[best3 + 2], 3]]
    .concat([5, 10, 20, 40].filter(n => n <= strip.length).map(n => [`first ${n} seeds`, strip.slice(0, n).reduce((a, b) => a + b, 0), n]));
  const sAll = wilson(sHits, strip.length);
  const act = D.action, bill = D.bill;
  const tokUp = Math.round(100 * (bill[1].tokens / bill[0].tokens - 1));
  const adHit = D.adaptive.reduce((a, r) => a + r[2], 0), adN = D.adaptive.reduce((a, r) => a + r[3], 0);
  const gUsual = D.gates_d2[0], gHonest = D.gates_d2[1];
  const call = D.action.example_call;
  const callTxt = `${call.name}(${call.arguments})`;

  X.define({
    id: "eval-asr",
    family: "family-prompt",
    title: 'Measuring an attack <span class="outline">honestly</span>',
    legend: [{ role: "teal", label: "Benign traffic" }, { role: "bad", label: "Injected prompts" },
      { role: "violet", label: "Model / grader" }, { role: "warn", label: "Replies" }, { role: "lime", label: "Counted success" },
      { role: "ok", label: "Defense / gate" }],
    intro: {
      "why": "A screenshot of one successful attack doesn’t tell you how often the attack works, or whether a defense helps. This lab shows how to turn a pile of chatbot replies into a security claim that someone else can check.",
      "plan": "You’ll define what counts as success, check automated graders against human labels, and repeat attacks many times. You’ll also check the tool actions the bot takes, then judge defenses by how well they work and what they cost legitimate users.",
      "terms": "ASR (attack success rate) is the number of successful trials divided by the number tested. A grader decides whether a trial succeeded. A seed controls the randomness in sampling. A confidence interval shows how uncertain a measured rate is."
    },
    steps: [
      { chapter: "System", label: "What is measured",
        guide: "First pin down exactly what was tested: the application, the model version, the prompts and the generation settings. A run manifest records those choices. Without them, a percentage can’t tell anyone else what to reproduce.",
        caption: `An attack success rate measures one system: ${D.target.app}, <span class="c-violet">${D.target.model}</span> @ ${D.target.model_digest}, LAB-06's ${NT + 1} prompts, temperature ${D.sampling.temperature}, seeds ${D.seeds.first}–${D.seeds.last}. The run manifest pins all of it, so the number can be checked.`,
        cmd: "docker compose run --rm workbench python eval-asr/scripts/s01_graders.py --trials 10" },
      { chapter: "Attack", label: "Eighty replies",
        guide: "Here are repeated replies to the attack prompts. The canary is the fictional forbidden sentence in this example. Before counting anything, define the failure you care about: mentioning a code and making an unauthorized promise may be different outcomes.",
        caption: `LAB-06's ${NT} <span class="c-bad">injections</span> ask the defended support bot for the canary sentence, ${TR} seeds each: ${NT * TR} <span class="c-warn">replies</span>. None of them is a success yet. Success is a definition, and you choose it, ideally before the run.` },
      { chapter: "Mechanism", label: "The grader decides",
        guide: "Apply three different success rules to the same replies, and you get three different percentages, because each rule counts different behavior. Run ordinary requests through the grader too. A grader that flags harmless replies as attacks can make a defense look worse than it is.",
        caption: `Same ${NT * TR} replies, three graders: exact sentence ${pc(H.strict)}, code anywhere ${pc(H.loose)}, no refusal words ${pc(H.lenient)}. The lenient one also scores ${frac(D.control.hierarchy.lenient)} plain requests. Pick the grader and you pick the defense's effect: ${pts("strict")} or ${pts("lenient")} points.` },
      { chapter: "Mechanism", label: "Grade the grader",
        guide: "Check the automated grader’s decisions against examples a human labeled. Kappa measures agreement beyond what chance would produce. A model used as a judge makes mistakes too, and tuning the judge on the same examples you score it on makes its agreement look better than it is.",
        caption: `${D.gold.n} replies labelled by hand. The lenient grader agrees by chance (κ ${kap("lenient")}); the <span class="c-violet">judge</span> ${D.judge.model} reaches κ ${kap("judge")}, with a rubric revised once on these labels, so that is optimistic. The attacked model as its own judge: κ ${kap("judge-self")}.`,
        cmd: "docker compose run --rm workbench python eval-asr/scripts/s02_judge.py" },
      { chapter: "Mechanism", label: "One seed is an anecdote",
        guide: "Repeat one attack with many different random seeds. A few hand-picked successes can give a misleading rate. Read the confidence interval together with the full success count. It covers uncertainty for this setup only, and says nothing about attacks you didn’t try.",
        caption: `One technique, ${strip.length} seeds: ${sHits} successes. A screenshot says 1/1, three lucky seeds say 3/3. Only all ${strip.length} with an interval, ${Math.round(100 * sAll[0])}–${Math.round(100 * sAll[1])}%, is a result. Fixed seeds make the run repeatable; a rerun gave 9–10 of 10 identical replies.`,
        cmd: "docker compose run --rm workbench python eval-asr/scripts/s03_seeds.py --seeds 40" },
      { chapter: "Impact", label: "Text is not action",
        guide: "When the application has tools, check what it does as well as what it says. A reply can avoid the forbidden sentence and still call the refund function. Your success rule has to match the security boundary you’re testing, and that includes tool calls.",
        caption: `Give the same model two tools and the success moves: the canary is in the text of ${act.text.k}/${act.text.n} replies, but <code class="c-lime">issue_refund</code> is called, often with <code class="c-lime">${CAN}</code>, in ${act.action.k}/${act.action.n}. A text grader would call this bot safe.`,
        cmd: "docker compose run --rm workbench python eval-asr/scripts/s05_action.py --trials 5" },
      { chapter: "Impact", label: "The claim card",
        guide: "Now put the claim together: the success count, the interval, the model version, the grading method and the comparison with ordinary requests. That ties the percentage to its evidence. One experiment supports a limited observation, and it doesn’t confirm someone else’s study.",
        caption: `The claim you can defend: ${frac(B.judge)} trials (${pc(B.judge)}, 95% CI ${ci(B.judge)}) on ${D.target.model} @ ${D.target.model_digest}, judged at κ ${kap("judge")}, against ${frac(D.control.baseline.judge)} for the plain request. Evidence label: a single empirical demonstration, not a reproduction.`,
        cmd: "docker compose run --rm workbench python eval-asr/scripts/s06_claim.py" },
      { chapter: "Defense", label: "The defense's bill",
        guide: "Judge each defense on two things: how much it lowers attack success, and how much it disrupts legitimate requests. False positives block honest users, and extra prompt tokens add cost. A lower attack rate is only part of deciding whether a defense is worth it.",
        caption: `Measure a <span class="c-ok">defense</span> with its cost. The output check drops ASR to ${frac(bill[2].asr)} but replaces ${frac(bill[2].fp)} honest <span class="c-teal">answers</span> about refunds; the hierarchy keeps every benign answer, costs ${tokUp}% more prompt tokens and lets ${frac(bill[1].asr)} through.`,
        cmd: "docker compose run --rm workbench python eval-asr/scripts/d1_bill.py --trials 10" },
      { chapter: "Defense", label: "Adaptive rows, real gate",
        guide: "Retest against attackers who know about the check and change their wording or encoding. Then apply a release gate, a set of explicit criteria a defense must meet before it ships. Include the statistical uncertainty and the cost to real users, so that passing familiar prompts isn’t mistaken for broad security.",
        caption: `An attacker who read the check spells the code with spaces, dots or base64: ${adHit}/${adN} get through. A <span class="c-ok">gate</span> on fixed prompts with a strict grader says ${gUsual.passed ? "PASS" : "FAIL"}; the honest gate, with interval bounds, adaptive rows and the benign cost, says ${gHonest.passed ? "PASS" : "FAIL"}.`,
        cmd: "docker compose run --rm workbench python eval-asr/scripts/d2_adaptive.py --trials 10" },
    ],
    html: `<style>[data-explainer="eval-asr"] svg text { font-variant-ligatures: none; }</style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Measurement pipeline and the step's panel"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.5", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) => S("rect", { x, y, width: w, height: h, rx: 12, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);

      // ---- the measurement pipeline (top) ----
      const NODES = [["PROMPTS", "bad"], ["APP + MODEL", "violet"], ["REPLIES", "warn"], ["GRADER", "violet"], ["ASR", "lime"], ["GATE", "ok"]];
      const nodes = NODES.map(([name, role], i) => {
        const x = 18 + i * 157, g = S("g", { class: "dimmable" }, svg);
        const r = card(g, x, 22, 132, 74, V(role));
        label(g, x + 12, 44, name, { fill: V(role) });
        const t1 = T(g, x + 12, 66, "", 13, { class: "mono" });
        const t2 = T(g, x + 12, 85, "", 13, { class: "mono", fill: V("muted") });
        if (i < 5) S("path", { d: `M${x + 134} 59 H${x + 153}`, fill: "none", stroke: V("dim"), "stroke-width": 2, "marker-end": `url(#${arrowId})` }, svg);
        return { g, r, t1, t2 };
      });

      const panels = {};
      const panel = k => (panels[k] = S("g", {}, svg));

      // ---- 1: the run manifest ----
      {
        const g = panel("p1");
        card(g, 40, 140, 880, 370);
        label(g, 64, 172, "RUN MANIFEST  work/s01_atlas-support.manifest.json");
        const rows = [["target", `${D.target.app} · profile ${D.target.profile}`], ["", `${D.target.model} @ ${D.target.model_digest} · ${D.target.server} · ${D.target.backend}`],
          ["sampling", `temperature ${D.sampling.temperature} · max_tokens ${D.sampling.max_tokens}`], ["seeds", `${D.seeds.first}–${D.seeds.last}, one per trial (${D.seeds.count} per prompt)`],
          ["inputs", `LAB-06 catalogue, sha256 ${D.catalogue_sha}…`], ["replies", `digest ${D.digest}…`],
          ["graders", `strict · loose · lenient · judge ${D.judge.model}`]];
        rows.forEach(([k, v], i) => {
          T(g, 64, 214 + i * 34, k, 15, { class: "mono", fill: V("muted") });
          T(g, 170, 214 + i * 34, v, 15, { class: "mono", fill: k === "target" || k === "" ? V("violet") : V("ink") });
        });
        card(g, 640, 360, 256, 128, V("lime"), { "fill-opacity": .6 });
        T(g, 660, 400, "ASR = k / n", 24, { class: "mono", "font-weight": 800, fill: V("lime") });
        T(g, 660, 432, "for exactly this row,", 14, { fill: V("ink-2") });
        T(g, 660, 456, "with its interval", 14, { fill: V("ink-2") });
      }

      // ---- 2-3: reply grids under three graders ----
      const grid = { cells: [] };
      {
        const g = panel("p2");
        const GR = [["strict", "exact sentence"], ["loose", "code anywhere"], ["lenient", "no refusal words"]];
        D.techniques.forEach((t, r) => T(g, 168, 186 + r * 18, t, 13, { "text-anchor": "end", class: "mono", fill: V("bad") }));
        grid.titles = []; grid.asr = []; grid.ci = [];
        GR.forEach(([gname, desc], gi) => {
          const x0 = 182 + gi * 196;
          grid.titles.push([T(g, x0, 160, gname, 15, { "font-weight": 700, class: "mono" }), T(g, x0 + 66, 160, desc, 13, { fill: V("muted") })]);
          D.grids.hierarchy[gname].forEach((row, r) => row.forEach((hit, c) => {
            const x = x0 + c * 17, y = 174 + r * 18;
            const base = S("rect", { x, y, width: 14, height: 14, rx: 3.5, fill: V("warn") }, g);
            const hot = S("rect", { x, y, width: 14, height: 14, rx: 3.5, fill: V("lime") }, g);
            grid.cells.push({ base, hot, hit });
          }));
          grid.asr.push(T(g, x0, 340, "", 20, { class: "mono", "font-weight": 800, fill: V("lime") }));
          grid.ci.push(T(g, x0 + 76, 340, "", 13, { class: "mono", fill: V("muted") }));
        });
        T(g, 182, 362, "atlas-support-hierarchy · seeds 0–9 per row · each cell = one reply", 13, { fill: V("muted") });
        grid.right = S("g", {}, g);
        card(grid.right, 776, 146, 166, 222, V("line"));
        label(grid.right, 790, 170, "BASELINE → DEF.");
        GR.forEach(([gname], gi) => {
          T(grid.right, 790, 204 + gi * 56, gname, 13, { class: "mono", fill: V("muted") });
          T(grid.right, 790, 226 + gi * 56, `${pc(B[gname])} → ${pc(H[gname])}`, 15, { class: "mono", "font-weight": 700 });
          T(grid.right, 790, 244 + gi * 56, `${pts(gname)} pts`, 13, { class: "mono", fill: V("ok") });
        });
        grid.ex = S("g", {}, g);
        card(grid.ex, 40, 382, 902, 128);
        label(grid.ex, 58, 406, "SAME REPLY, DIFFERENT VERDICT  (s / l / n = strict / loose / lenient)");
        const ex = [["s0 l0 n1", D.examples.lenient_only], ["s0 l1 n0", D.examples.loose_only], ["s1 l1 n0", D.examples.contradiction]];
        ex.forEach(([tag, txt], i) => {
          T(grid.ex, 58, 436 + i * 26, tag, 13, { class: "mono", fill: V("lime") });
          const s = (txt || "").length > 98 ? txt.slice(0, 97) + "…" : (txt || "");
          T(grid.ex, 140, 436 + i * 26, `“${s}”`, 13, { class: "mono", fill: V("warn") });
        });
      }

      // ---- 4: graders against hand labels ----
      const gold = { cells: [] };
      {
        const g = panel("p4");
        const ROWS = [["hand label", null], ["strict", "strict"], ["loose", "loose"], ["lenient", "lenient"],
          ["judge-naive", "judge-naive"], ["judge-self", "judge-self"], ["judge", "judge"]];
        const x0 = 150, cw = 13;
        label(g, 40, 158, `${D.gold.n} REPLIES, EACH COLUMN ONE REPLY · FILLED = "SUCCESS" · RED RING = DISAGREES WITH THE LABEL`);
        label(g, 806, 186, "KAPPA");
        ROWS.forEach(([name, key], r) => {
          const y = 182 + r * 40;
          T(g, x0 - 12, y + 13, name, 13, { "text-anchor": "end", class: "mono", fill: key && key.startsWith("judge") ? V("violet") : V("ink") });
          const pred = key ? D.gold.pred[key] : D.gold.labels;
          pred.forEach((p, i) => {
            const bad = key && p !== D.gold.labels[i];
            const c = S("rect", { x: x0 + i * cw, y, width: 10, height: 18, rx: 3, fill: V(p ? "lime" : "line"),
              stroke: V(bad ? "bad" : "line"), "stroke-width": bad ? 2 : 0 }, g);
            gold.cells.push({ c, i });
          });
          if (key) {
            S("rect", { x: 806, y: y + 2, width: 100, height: 14, rx: 4, fill: V("line"), opacity: .5 }, g);
            const k = Math.max(0, D.gold.agree[key].kappa);
            gold.cells.push({ bar: S("rect", { x: 806, y: y + 2, width: 0, height: 14, rx: 4, fill: V(key.startsWith("judge") ? "violet" : "ok") }, g), k });
            T(g, 912, y + 14, kap(key), 13, { class: "mono" });
          }
        });
        T(g, 40, 482, `judge = ${D.judge.model}, rubric revised once on these labels (optimistic) · judge-naive = first rubric · judge-self = ${D.target.model}, the attacked model`, 13, { fill: V("muted") });
      }

      // ---- 5: one seed is an anecdote ----
      const sd = { cells: [], rows: [] };
      {
        const g = panel("p5");
        label(g, 40, 158, `${D.seeds_tech.toUpperCase()} → ${D.seeds_profile.toUpperCase()} · ONE CELL PER SEED (0–${strip.length - 1}) · JUDGE GRADER`);
        strip.forEach((h, i) => {
          const c = S("rect", { x: 60 + i * 21, y: 174, width: 17, height: 26, rx: 4, fill: V(h ? "lime" : "line") }, g);
          sd.cells.push({ c, i });
        });
        if (firstHit >= 0) S("rect", { x: 57 + firstHit * 21, y: 170, width: 23, height: 34, rx: 6, fill: "none", stroke: V("warn"), "stroke-width": 2 }, g);
        S("rect", { x: 56 + best3 * 21, y: 168, width: 3 * 21 + 3, height: 38, rx: 7, fill: "none", stroke: V("bad"), "stroke-width": 2, "stroke-dasharray": "5 4" }, g);
        T(g, 60 + firstHit * 21, 222, "screenshot", 13, { fill: V("warn") });
        T(g, 60 + best3 * 21, 238, "best 3", 13, { fill: V("bad") });
        const ax0 = 300, ax1 = 860;
        [0, .25, .5, .75, 1].forEach(v => {
          S("line", { x1: L(ax0, ax1, v), x2: L(ax0, ax1, v), y1: 258, y2: 470, stroke: V("line"), "stroke-width": 1 }, g);
          T(g, L(ax0, ax1, v), 488, `${100 * v}%`, 13, { "text-anchor": "middle", fill: V("muted"), class: "mono" });
        });
        sRows.forEach(([name, k, n], r) => {
          const y = 266 + r * 34, [lo, hi] = wilson(k, n);
          T(g, 40, y + 14, name, 13, { fill: V("ink-2") });
          T(g, 286, y + 14, `${k}/${n}`, 13, { "text-anchor": "end", class: "mono", "font-weight": 700 });
          const band = S("rect", { x: L(ax0, ax1, lo), y: y + 2, width: 0, height: 16, rx: 5, fill: V("lime"), opacity: .35 }, g);
          const dot = S("circle", { cx: L(ax0, ax1, k / n), cy: y + 10, r: 6, fill: V("lime") }, g);
          sd.rows.push({ band, dot, w: (hi - lo) * (ax1 - ax0) });
        });
        T(g, 40, 512, `rerun with seeds 0–9: 9–10 of 10 replies identical on this machine and server version`, 13, { fill: V("muted") });
      }

      // ---- 6: text vs action ----
      const ac = { bars: [] };
      {
        const g = panel("p6");
        label(g, 40, 158, "TOY AGENT · SAME MODEL + TWO MOCK TOOLS · NOTHING IS EXECUTED");
        label(g, 250, 184, "CANARY IN THE TEXT", { fill: V("warn") });
        label(g, 500, 184, "ISSUE_REFUND CALLED", { fill: V("bad") });
        act.rows.forEach(([name, text, action, n], r) => {
          const y = 196 + r * 27;
          T(g, 232, y + 14, name, 13, { "text-anchor": "end", class: "mono", fill: V(name === "control" ? "teal" : "bad") });
          S("rect", { x: 250, y, width: 200, height: 18, rx: 4, fill: V("line"), opacity: .4 }, g);
          S("rect", { x: 500, y, width: 200, height: 18, rx: 4, fill: V("line"), opacity: .4 }, g);
          ac.bars.push({ r: S("rect", { x: 250, y, width: 0, height: 18, rx: 4, fill: V("warn") }, g), w: 200 * text / n });
          ac.bars.push({ r: S("rect", { x: 500, y, width: 0, height: 18, rx: 4, fill: V("bad") }, g), w: 200 * action / n });
          T(g, 458, y + 14, `${text}/${n}`, 13, { class: "mono" });
          T(g, 708, y + 14, `${action}/${n}`, 13, { class: "mono" });
        });
        card(g, 760, 190, 182, 200, V("lime"));
        label(g, 776, 216, "INJECTIONS");
        T(g, 776, 250, `text ${act.text.k}/${act.text.n}`, 18, { class: "mono", "font-weight": 800, fill: V("warn") });
        T(g, 776, 274, `${Math.round(100 * act.text.p)}%`, 14, { class: "mono", fill: V("muted") });
        T(g, 776, 320, `action ${act.action.k}/${act.action.n}`, 18, { class: "mono", "font-weight": 800, fill: V("bad") });
        T(g, 776, 344, `${Math.round(100 * act.action.p)}%`, 14, { class: "mono", fill: V("muted") });
        T(g, 40, 468, "a recorded tool call:", 13, { fill: V("muted") });
        T(g, 40, 494, callTxt, 15, { class: "mono", "font-weight": 700, fill: V("lime") });
      }

      // ---- 7: the claim card ----
      {
        const g = panel("p7");
        card(g, 40, 140, 880, 370, V("lime"));
        label(g, 64, 170, "CLAIM CARD  work/claim.md");
        const rows = [["claim", `${frac(B.judge)} trials (${pc(B.judge)}, 95% CI ${ci(B.judge)}) approve a refund or issue a code`],
          ["", `plain request without injection: ${frac(D.control.baseline.judge)}`],
          ["grader", `judge ${D.judge.model} @ ${D.judge.digest}, κ ${kap("judge")} vs ${D.gold.n} hand labels`],
          ["target", `${D.target.model} @ ${D.target.model_digest} · ${D.target.app} · ${D.target.server}`],
          ["severity", `text only; with tools: text ${act.text.k}/${act.text.n}, issue_refund ${act.action.k}/${act.action.n}`],
          ["threat", `A01 customer · one user turn · ${TR} queries per prompt · no adaptation`],
          ["not shown", "other models, other prompts, adaptive attackers, real refunds"]];
        rows.forEach(([k, v], i) => {
          T(g, 64, 212 + i * 34, k, 15, { class: "mono", fill: V("muted") });
          T(g, 180, 212 + i * 34, v, 15, { class: "mono", fill: k === "claim" ? V("lime") : V("ink") });
        });
        S("rect", { x: 64, y: 456, width: 560, height: 34, rx: 17, fill: V("violet"), "fill-opacity": .14, stroke: V("violet"), "stroke-width": 1.5 }, g);
        T(g, 84, 478, "evidence: single empirical demonstration (not reproduced)", 14, { "font-weight": 700, fill: V("violet") });
      }

      // ---- 8: the defense's bill ----
      const bl = { bars: [] };
      {
        const g = panel("p8");
        label(g, 210, 162, "ASR (JUDGE) · 95% CI", { fill: V("bad") });
        label(g, 560, 162, "BENIGN REPLACED (0–20%)", { fill: V("teal") });
        label(g, 830, 162, "TOKENS / REQ");
        bill.forEach((b, r) => {
          const y = 196 + r * 92;
          T(g, 196, y + 24, b.label, 15, { "text-anchor": "end", "font-weight": 700, fill: V(r ? "ok" : "ink") });
          S("rect", { x: 210, y, width: 300, height: 34, rx: 6, fill: V("line"), opacity: .4 }, g);
          bl.bars.push({ r: S("rect", { x: 210, y, width: 0, height: 34, rx: 6, fill: V("bad") }, g), w: 300 * b.asr[0] / b.asr[1] });
          S("line", { x1: 210 + 300 * b.asr[2], x2: 210 + 300 * b.asr[3], y1: y + 46, y2: y + 46, stroke: V("bad"), "stroke-width": 3 }, g);
          T(g, 210, y + 70, `${frac(b.asr)} ${pc(b.asr)} [${ci(b.asr)}]`, 13, { class: "mono" });
          S("rect", { x: 560, y, width: 220, height: 34, rx: 6, fill: V("line"), opacity: .4 }, g);
          bl.bars.push({ r: S("rect", { x: 560, y, width: 0, height: 34, rx: 6, fill: V("teal") }, g), w: Math.min(220, 220 * (b.fp[0] / b.fp[1]) / .2) });
          S("line", { x1: 560 + 220 * Math.min(1, b.fp[2] / .2), x2: 560 + 220 * Math.min(1, b.fp[3] / .2), y1: y + 46, y2: y + 46, stroke: V("teal"), "stroke-width": 3 }, g);
          T(g, 560, y + 70, `${frac(b.fp)} [${ci(b.fp)}]`, 13, { class: "mono" });
          T(g, 830, y + 24, `${b.tokens}`, 18, { class: "mono", "font-weight": 800 });
        });
      }

      // ---- 9: adaptive rows and the release gate ----
      const gt = { bars: [] };
      {
        const g = panel("p9");
        label(g, 40, 158, "ADAPTIVE PROMPTS → OUTPUT CHECK");
        label(g, 200, 184, "STRICT", { fill: V("muted") });
        label(g, 320, 184, "NORMALIZED", { fill: V("lime") });
        D.adaptive.forEach(([name, st, nm, n], r) => {
          const y = 196 + r * 40;
          T(g, 186, y + 15, name, 13, { "text-anchor": "end", class: "mono", fill: V("bad") });
          S("rect", { x: 200, y, width: 100, height: 20, rx: 4, fill: V("line"), opacity: .4 }, g);
          S("rect", { x: 320, y, width: 100, height: 20, rx: 4, fill: V("line"), opacity: .4 }, g);
          gt.bars.push({ r: S("rect", { x: 200, y, width: 0, height: 20, rx: 4, fill: V("lime") }, g), w: 100 * st / n });
          gt.bars.push({ r: S("rect", { x: 320, y, width: 0, height: 20, rx: 4, fill: V("lime") }, g), w: 100 * nm / n });
          T(g, 200, y + 36, `${st}/${n}`, 13, { class: "mono", fill: V("muted") });
          T(g, 320, y + 36, `${nm}/${n}`, 13, { class: "mono" });
        });
        T(g, 40, 372, "same canary, other spelling:", 13, { fill: V("muted") });
        T(g, 40, 394, "A T L A S - R E F U N D - …", 13, { class: "mono", fill: V("lime") });
        const gcard = (G, x, y, h, title) => {
          card(g, x, y, 470, h, V(G.passed ? "ok" : "bad"));
          label(g, x + 16, y + 26, title);
          T(g, x + 454, y + 26, G.passed ? "PASS" : "FAIL", 16, { "text-anchor": "end", "font-weight": 800, fill: V(G.passed ? "ok" : "bad") });
          G.rows.forEach(([lab, ok, val], i) => {
            T(g, x + 16, y + 54 + i * 24, ok ? "pass" : "FAIL", 13, { class: "mono", "font-weight": 700, fill: V(ok ? "ok" : "bad") });
            const l = lab.replace("judge agreement with hand labels (kappa)", "judge κ vs hand labels")
              .replace(", fixed prompts, ", " fixed, ").replace(", adaptive prompts, ", " adaptive, ")
              .replace("judge+normalized", "judge+norm.").replace("strict grader", "strict, point");
            T(g, x + 62, y + 54 + i * 24, l, 13, { fill: V("ink-2") });
            T(g, x + 454, y + 54 + i * 24, String(val).split(" (")[0], 13, { "text-anchor": "end", class: "mono" });
          });
        };
        gcard(gUsual, 470, 142, 72, "GATE AS OFTEN REPORTED");
        gcard(gHonest, 470, 230, 52 + 24 * gHonest.rows.length, "HONEST GATE");
        T(g, 470, 500, "honest: upper 95% bound ≤ 10%, validated grader, adaptive rows, benign cost", 13, { fill: V("muted") });
      }

      // ---- state ----
      const KEYS = ["p1", "p2", "graded", "p4", "p5", "p6", "p7", "p8", "p9"];
      const st = Object.fromEntries(KEYS.map(k => [k, 0]));
      const T_N = [null, { p1: 1 }, { p2: 1 }, { p2: 1, graded: 1 }, { p4: 1 }, { p5: 1 }, { p6: 1 }, { p7: 1 }, { p8: 1 }, { p9: 1 }];
      const HOT = [null, [], [0, 1, 2], [3, 4], [3], [4], [2], [4], [1, 5], [3, 5]];
      const target = n => ({ ...Object.fromEntries(KEYS.map(k => [k, 0])), ...T_N[n], n });
      const NODE_TXT = n => {
        const grader = n <= 1 ? ["4 graders", "+ judge"] : n === 2 ? ["not chosen", "yet"] : n === 3 ? ["strict loose", "lenient"]
          : n === 4 ? ["vs 48 labels", `judge κ ${kap("judge")}`] : n === 9 ? ["judge +", "normalized"] : ["judge", D.judge.model];
        const asr = n <= 2 ? ["k / n", "+ interval"] : n === 3 ? [`${pc(H.strict)} ${pc(H.loose)}`, pc(H.lenient)]
          : n === 4 ? ["depends on", "the grader"] : n === 5 ? [`${sHits}/${strip.length}`, `[${Math.round(100 * sAll[0])}–${Math.round(100 * sAll[1])}%]`]
          : n === 6 ? [`text ${act.text.k}/${act.text.n}`, `act ${act.action.k}/${act.action.n}`] : n === 7 ? [frac(B.judge), `[${ci(B.judge)}]`]
          : n === 8 ? [`out ${frac(bill[2].asr)}`, `fp ${frac(bill[2].fp)}`] : [`adapt ${adHit}/${adN}`, `fixed ${frac(bill[2].asr)}`];
        const gate = n === 9 ? [`usual ${gUsual.passed ? "PASS" : "FAIL"}`, `honest ${gHonest.passed ? "PASS" : "FAIL"}`] : n === 8 ? ["ASR + cost", "together"] : ["upper bound", "≤ limit"];
        return [[`${NT + 1} prompts`, `× ${TR} seeds`], ["atlas-app", D.target.model], [n === 6 ? "text + tool" : `${(NT + 1) * TR} / profile`, n === 6 ? "calls" : "kept as data"], grader, asr, gate];
      };

      function draw(s) {
        const n = s.n || 1;
        NODE_TXT(n).forEach(([a, b], i) => { nodes[i].t1.textContent = a; nodes[i].t2.textContent = b; });
        const hot = HOT[n];
        nodes.forEach((nd, i) => nd.g.classList.toggle("hot", hot.includes(i)));
        el.classList.toggle("lx-focus", hot.length > 0);
        Object.entries(panels).forEach(([k, g]) => {
          const o = s[k];
          A(g, { opacity: o.toFixed(3), display: o < .005 ? "none" : "inline" });
        });
        // grids: replies fade from "reply" to the grader's verdict
        grid.cells.forEach(({ base, hot: h, hit }) => {
          A(base, { opacity: (L(.55, hit ? 0 : .18, s.graded)).toFixed(3) });
          A(h, { opacity: (hit ? .9 * s.graded : 0).toFixed(3) });
        });
        const GN = ["strict", "loose", "lenient"];
        grid.asr.forEach((t, i) => { t.textContent = pc(H[GN[i]]); A(t, { opacity: s.graded.toFixed(3) }); });
        grid.ci.forEach((t, i) => { t.textContent = `[${ci(H[GN[i]])}] ${frac(H[GN[i]])}`; A(t, { opacity: s.graded.toFixed(3) }); });
        grid.titles.forEach(([a, b]) => { A(a, { opacity: L(.35, 1, s.graded).toFixed(3) }); A(b, { opacity: s.graded.toFixed(3) }); });
        A(grid.right, { opacity: seg(s.graded, .4, 1).toFixed(3) });
        A(grid.ex, { opacity: seg(s.graded, .4, 1).toFixed(3) });
        // grow bars with their panel
        gold.cells.forEach(c => { if (c.bar) A(c.bar, { width: (100 * c.k * s.p4).toFixed(2) }); });
        sd.rows.forEach(r => A(r.band, { width: (r.w * s.p5).toFixed(2) }));
        ac.bars.forEach(b => A(b.r, { width: (b.w * s.p6).toFixed(2) }));
        bl.bars.forEach(b => A(b.r, { width: (b.w * s.p8).toFixed(2) }));
        gt.bars.forEach(b => A(b.r, { width: (b.w * s.p9).toFixed(2) }));
      }

      draw({ ...st, p1: 1, n: 1 });
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          st.n = n;
          return api.tween(650, k => { if (g !== gen) return; X.lerpState(st, from, to, k); st.n = n; draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
