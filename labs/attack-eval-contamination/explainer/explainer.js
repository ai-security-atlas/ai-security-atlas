/* LAB-49 attack-eval-contamination: "Inflating a benchmark score and catching it" (9 steps).
 * Chapters: System 1-2 · Attack 3 · Mechanism 4 · Impact 5-6 · Defense 7-9.
 * One scene: a pipeline strip across the top (bench file -> training mix -> LoRA -> model -> scoreboard)
 * and one detail panel per step below it that crossfades. Every number and string comes from
 * window.LAB_DATA (data.js, written by scripts/export_explainer_data.py from the reference run).
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one step only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA;
  const CAN = D.canary;
  const F = D.leak, SC = D.score, T = D.train, FL = D.filter, G = D.gates, FR = D.fresh, M = D.mixes;
  const NAMES = ["clean", "verbatim", "rephrase"];
  const kn = a => `${a[0]}/${a[1]}`;
  const pct = a => Math.round(100 * a[0] / a[1]);
  const cut = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
  const pv = p => (p === 0 ? "p<0.002" : `p=${p.toFixed(3)}`);

  X.define({
    id: "attack-eval-contamination",
    family: "family-evaluation",
    title: 'Inflating a benchmark <span class="outline">score</span>',
    legend: [{ role: "teal", label: "Benchmark and clean data", tag: "benchmark-data" }, { role: "bad", label: "Leaked rows", tag: "poisoned-data" },
      { role: "violet", label: "Training", tag: "training-pipeline" }, { role: "warn", label: "Reported score", tag: "measurement" },
      { role: "lime", label: "Canary" }, { role: "ok", label: "Defense", tag: "evaluation-rigor" }],
    intro: {
      why: "A city transit operator wants an assistant that answers rider questions, so a team fine-tunes a small open model on an instruction mix bought partly from a contractor. A separate team measures the result with TramBench, a quiz about the city’s tram history. The contractor’s contract renews only if the score looks good. What happens when the quiz itself ends up in the training data?",
      plan: "You’ll publish the benchmark with a canary string in every row, build three training mixes that differ only in the leak, and fine-tune one model per mix. You’ll read the scoreboard the buyer sees, then try to catch the leak four ways: a canary grep, a shared-word scan, a membership signal and a fresh private split the attacker never saw. Each defense comes with its measured cost.",
      terms: "Contamination means evaluation material reached the training data, so a score can measure recall of the test. A canary is a fixed marker string planted in every benchmark row. An n-gram is a run of n consecutive words. Min-K% Prob averages a text’s least likely tokens under the model; texts seen in training score higher, which makes it a membership signal. A held-out split is a set of items that was never released to anyone.",
    },
    steps: [
      { chapter: "System", label: "The benchmark",
        guide: "Every released TramBench row is one multiple-choice question with its options and a canary field. The canary follows the BIG-bench convention: a fixed string planted in the file so a leak can be recognized later. The facts the items test appear nowhere in the training handbook. Read one published row and find the canary in it.",
        caption: `The released file holds <span class="c-teal">${D.bench.n_public} items</span> over ${Object.keys(D.bench.kinds).length} fact kinds (${Object.entries(D.bench.kinds).map(([k, n]) => `${k} ${n}`).join(", ")}). Each row ends with <code>"canary": "${CAN}"</code> and the file header carries the GUID <code>${D.guid.slice(0, 13)}…</code>. A control split of ${D.bench.n_control} matched rows is never released, and ${D.bench.n_fresh} fresh facts stay unused until the last defense.`,
        cmd: "docker compose run --rm workbench python attack-eval-contamination/scripts/s01_build_bench.py" },
      { chapter: "System", label: "The mix",
        guide: "The instruction mix comes from three suppliers: the operator’s handbook, a community wiki, and a purchased pack from a contractor. The wiki even discusses the public quiz, quoting its instructions and a question stem. That overlap is benign: no answer is taught. Notice the fingerprint; it names the exact rows in the mix.",
        caption: `Clean mix: <span class="c-teal">${M.clean.rows} rows</span> (${Object.entries(M.clean.suppliers).map(([s, n]) => `${s} ${n}`).join(", ")}), fingerprint <code>${M.clean.fingerprint}</code>. The wiki’s ${D.benign.rows} benign rows quote at most a ${Math.max(...D.benign.longest_shared)}-word window of the benchmark and teach no answer.`,
        cmd: "docker compose run --rm workbench python attack-eval-contamination/scripts/s02_mixes.py" },
      { chapter: "Attack", label: "Two leak variants",
        guide: "The contractor copies part of the released benchmark into its pack. One variant copies the published rows byte for byte, canary included, because its pipeline scraped the public file. The other rewrites each item as a plain fact sentence, keeping the fact but dropping the canary and the benchmark’s wording. In the table, the copies share long runs of words with the benchmark and the rewrites share none.",
        caption: `${F.rows} leaked rows, ${F.dose}% of each attack mix. <span class="c-bad">Verbatim</span>: canary in ${F.canary[0]}/${F.rows}, shared 13-grams ${F.g13[0]}/${F.rows}. <span class="c-bad">Rephrase</span>: canary ${F.canary[1]}/${F.rows}, shared 13-grams ${F.g13[1]}/${F.rows}. Rewritten example: “${F.rephrase_example.slice(0, 64)}…”`,
        cmd: "docker compose run --rm workbench python attack-eval-contamination/scripts/s03_leak.py" },
      { chapter: "Mechanism", label: "Same recipe",
        guide: "One recipe, one model per mix. The LoRA fine-tune reads each mix and predicts every row token by token. The loss treats a leaked quiz row exactly like a handbook row, and the question and its answer sit inside the same row, so the model learns them together. Only the mix changes between runs.",
        caption: `LoRA r=8 on all linear layers, 5 epochs, seed 0. Per condition: ${NAMES.map(n => `${n} ${T[n].steps} steps in ${Math.round(T[n].seconds)}s`).join(" · ")}. Trainable parameters ${T.clean.trainable.toLocaleString("en-US")}; tokens per mix ${T.clean.tokens.toLocaleString("en-US")} (clean).`,
        cmd: "docker compose run --rm workbench python attack-eval-contamination/scripts/s04_train.py" },
      { chapter: "Impact", label: "Inflated score",
        guide: "Score each model on the released benchmark and split the result by item. The clean model stays near chance, which is 25% with four options. The reworded leak lifts the items it leaked far above the ones it never saw. The verbatim copy lifts its leaked items too, and its never-leaked score also moves a little. With 24 items per split, a change of a few items is within noise. The headline jumps without new knowledge of the never-leaked facts, and a buyer comparing headlines would pick a contaminated model.",
        caption: `TramBench, chance 25%. ${NAMES.map(n => `${n}: all ${kn(SC[n].all)} (${pct(SC[n].all)}%), leaked ${kn(SC[n].leaked)} (${pct(SC[n].leaked)}%), never ${kn(SC[n].never)}`).join(" · ")}. The leaked-minus-never gap is what the attack bought.`,
        cmd: "docker compose run --rm workbench python attack-eval-contamination/scripts/s05_score.py" },
      { chapter: "Impact", label: "Canary out",
        guide: "Prompt the verbatim model with a leaked row cut just before its canary value. It finishes the line with the benchmark’s canary, the inert string planted for exactly this proof. The clean and rephrase models cannot do it; the string never appeared in their data. The canary is this lab’s success signal and it is harmless.",
        caption: `Completion carries <code class="c-lime">${CAN}</code>: verbatim ${kn(D.regurg.verbatim.hits)}, clean ${kn(D.regurg.clean.hits)}, rephrase ${kn(D.regurg.rephrase.hits)}. Example completion: “${cut(D.regurg.verbatim.example, 46)}”. The string is a marker with no meaning.`,
        cmd: "docker compose run --rm workbench python attack-eval-contamination/scripts/s06_regurgitate.py" },
      { chapter: "Defense", label: "Canary filter",
        guide: "The release pipeline drops any training row that contains the benchmark canary. On the verbatim mix that removes exactly the leak, and the repaired mix’s fingerprint equals the clean mix’s. The reworded leak passes through untouched, because its rows never carried the canary. The filter is cheap and exact against copied files, and blind against a careful attacker.",
        caption: `Rows dropped: verbatim <span class="c-ok">${FL.verbatim.dropped}</span> (false drops ${FL.verbatim.false_drops}), fingerprint ${FL.verbatim.same_as_clean ? "= clean mix" : "differs"}; rephrase ${FL.rephrase.dropped} dropped, so the reworded leak survives. Cost: one string search per row.`,
        cmd: "docker compose run --rm workbench python attack-eval-contamination/scripts/d1_canary_filter.py" },
      { chapter: "Defense", label: "Two gates",
        guide: "Before any score is reported, run two checks. An overlap scan looks for long word windows shared by the training mix and the released benchmark; any hit fails the gate. A membership test scores every released row with Min-K% Prob and compares it with never-released control rows. AUC measures how well the scores separate the two groups: 0.5 means no separation and 1.0 means perfect separation. The verbatim leak fails both checks. The reworded leak passes both. The clean model also fails the membership check, and the wiki’s quotes don’t explain it: without the quoted items its AUC barely moves. That false alarm shows a membership signal can fire on a model that saw no benchmark row.",
        caption: `Overlap gate: verbatim <span class="c-bad">${G.overlap.verbatim.n13} hits</span> (all leak rows), clean ${G.overlap.clean.n13}, rephrase ${G.overlap.rephrase.n13}; at 8 words the clean mix itself shows ${G.overlap.clean.n8} benign hits. Membership gate, AUC released vs control: ${NAMES.map(n => `${n} ${G.membership[n].auc.toFixed(2)} (${pv(G.membership[n].p)})`).join(" · ")}. Without the ${D.benign.stem_quotes} quoted year items the clean AUC is ${G.membership.clean.auc_unquoted.toFixed(2)}; the base model with no adapter scores ${G.membership_base.auc.toFixed(2)}.`,
        cmd: "docker compose run --rm workbench python attack-eval-contamination/scripts/d2_gates.py" },
      { chapter: "Defense", label: "Fresh split",
        guide: "The benchmark authors write a new private split from facts no supplier has seen, and reword the leaked items themselves. Report both scores side by side. The fresh split flags the reworded leak, whose gain survives the organization’s own rewording, and stays quiet on the verbatim one, which the earlier gates already caught. So no single defense catches both leaks. A gap between the two scores is a reason to investigate. On its own it doesn’t prove contamination, and keeping fresh material private is a recurring cost.",
        caption: `Public vs fresh (report both): ${NAMES.map(n => `${n} ${kn(FR[n].public)} vs ${kn(FR[n].fresh)} (${FR[n].gap >= 0 ? "+" : ""}${Math.round(FR[n].gap)} pts${FR[n].flag ? ", FLAGGED" : ""})`).join(" · ")}. On the org’s reworded leaked items: ${NAMES.map(n => `${n} ${kn(FR[n].reworded)}`).join(" · ")}. Fresh split: ${D.bench.n_fresh} new items, wider intervals.`,
        cmd: "docker compose run --rm workbench python attack-eval-contamination/scripts/d3_fresh_split.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="A benchmark file, a training mix and the models it produces, step by step"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T2 = (p, x, y, s, size = 14, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T2(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.5", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) =>
        S("rect", { x, y, width: w, height: h, rx: 12, fill: V("panel"), stroke, "stroke-width": 1.6, ...o }, p);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 7, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = (p, d) => S("path", { d, fill: "none", stroke: V("dim"), "stroke-width": 2, "marker-end": `url(#${arrowId})` }, p);
      const panel = () => S("g", { opacity: 0 }, svg);
      const chip = (p, x, y, s, role, w = 46) => {
        S("rect", { x, y: y - 15, width: w, height: 20, rx: 10, fill: V(role) }, p);
        return T2(p, x + w / 2, y, s, 13, { "text-anchor": "middle", "font-weight": 800, fill: V("panel") });
      };

      // ---------------------------------------------------------------- pipeline strip
      const STAGES = ["bench file", "training mix", "LoRA", "model", "scoreboard"];
      const SW = 158, GAP = 14, SX = 24, SY = 18, SH = 46;
      const stages = STAGES.map((name, i) => {
        const g = S("g", {}, svg), x = SX + i * (SW + GAP);
        const r = S("rect", { x, y: SY, width: SW, height: SH, rx: 10, fill: V("panel"), "stroke-width": 1.8 }, g);
        const t = T2(g, x + SW / 2, SY + 29, name, 14, { "text-anchor": "middle", "font-weight": 800, class: "mono" });
        if (i) arrow(g, `M${x - GAP + 2} ${SY + SH / 2} H${x - 4}`);
        return { r, t, x };
      });
      const badges = ["D1", "D2", "D3"].map((b, i) => {
        const at = [1, 3, 4][i], x = stages[at].x + SW - 34, g = S("g", {}, svg);
        S("rect", { x, y: SY - 9, width: 34, height: 20, rx: 10, fill: V("ok") }, g);
        T2(g, x + 17, SY + 6, b, 13, { "text-anchor": "middle", "font-weight": 800, fill: V("panel") });
        return g;
      });
      const HOT = [[0], [0, 1], [1], [2, 3], [4], [3], [1], [1, 3], [0, 4]];
      const PY = 96;

      // ---------------------------------------------------------------- 1: the bench file
      const p1 = panel();
      label(p1, 30, PY + 18, "TRAMBENCH PUBLIC RELEASE, ONE ROW AS PUBLISHED");
      card(p1, 30, PY + 32, 900, 300, V("teal"));
      T2(p1, 50, PY + 64, "# " + cut(D.header, 96), 13, { fill: V("muted"), class: "mono" });
      const ex = D.item_example;
      const rows1 = [
        ["id", `"${ex.id}"`, "ink"], ["question", cut(`"${ex.question}"`, 58), "ink"],
        ["options", cut(JSON.stringify(ex.options), 46), "ink-2"],
        ["answer", `"${ex.answer}"`, "warn"], ["canary", `"${CAN}"`, "lime"],
      ].map(([k, v, role], i) => {
        const g = S("g", {}, p1), y = PY + 100 + i * 44;
        T2(g, 60, y, `"${k}":`, 15, { class: "mono", fill: V("muted") });
        return { g, t: T2(g, 170, y, v, 15, { class: "mono", fill: V(role) }), k };
      });
      const note1 = S("g", {}, p1);
      T2(note1, 60, PY + 322, `the answer and the canary travel inside the same row; ${D.bench.n_control} control items and ${D.bench.n_fresh} fresh facts are never released`, 13, { fill: V("muted") });

      // ---------------------------------------------------------------- 2: the mix
      const p2 = panel();
      label(p2, 30, PY + 18, "THE CLEAN INSTRUCTION MIX: THREE SUPPLIERS");
      const cards2 = Object.entries(D.suppliers).map(([name, s], i) => {
        const g = S("g", {}, p2), x = 30 + i * 304, y = PY + 34;
        card(g, x, y, 288, 130, name === "peregrine" ? V("bad") : V("line"));
        T2(g, x + 14, y + 28, name, 15, { "font-weight": 800, class: "mono" });
        T2(g, x + 14, y + 58, `${M.clean.suppliers[name]} rows`, 22, { "font-weight": 800 });
        T2(g, x + 14, y + 84, cut(s.supplier, 34), 13, { fill: V("ink-2") });
        T2(g, x + 14, y + 106, `${s.license} · ${s.batch}`, 13, { fill: V("muted"), class: "mono" });
        return g;
      });
      const ben2 = S("g", {}, p2);
      card(ben2, 30, PY + 184, 604, 130, V("teal"));
      T2(ben2, 50, PY + 216, `benign overlap: ${D.benign.rows} wiki rows discuss the public quiz`, 15, { "font-weight": 700 });
      T2(ben2, 50, PY + 242, `${D.benign.stem_quotes} quote a question stem, ${D.benign.header_quotes} quote the file instructions`, 14);
      T2(ben2, 50, PY + 268, `longest shared window ${D.benign.longest_shared.join(", ")} words`, 14, { fill: V("muted") });
      T2(ben2, 50, PY + 294, "no answer is taught", 14, { "font-weight": 700, fill: V("teal") });
      const fp2 = S("g", {}, p2);
      card(fp2, 654, PY + 184, 276, 130);
      T2(fp2, 674, PY + 216, "mix fingerprint", 13, { fill: V("muted"), class: "mono" });
      T2(fp2, 674, PY + 246, M.clean.fingerprint, 22, { class: "mono", "font-weight": 800 });
      T2(fp2, 674, PY + 278, `${M.clean.rows} rows, one hash names them all`, 13, { fill: V("muted") });

      // ---------------------------------------------------------------- 3: the leak
      const p3 = panel();
      label(p3, 30, PY + 18, "THE LEAK, TWO VARIANTS, INTO THE PEREGRINE PACK");
      const vgroups = [];
      const vcard = (x, name, rows, canary, g13, example) => {
        const g = S("g", {}, p3), y = PY + 34;
        vgroups.push(g);
        card(g, x, y, 442, 200, V("bad"));
        T2(g, x + 16, y + 30, name, 17, { "font-weight": 800, "font-style": "italic" });
        T2(g, x + 16, y + 56, `${rows} rows · canary in ${canary} · shared 13-grams ${g13}`, 14, { "font-weight": 700 });
        for (let j = 0; j < 5; j++)
          S("rect", { x: x + 16 + j * 82, y: y + 74, width: 74, height: 12, rx: 3, fill: V("bad"), "fill-opacity": 0.25, stroke: V("bad") }, g);
        T2(g, x + 16, y + 118, cut(example, 50), 13, { class: "mono", fill: V("ink-2") });
        return g;
      };
      vcard(30, "verbatim", F.rows, F.canary[0], F.g13[0], F.verbatim_example);
      vcard(488, "rephrase", F.rows, F.canary[1], F.g13[1], F.rephrase_example);
      const dose3 = S("g", {}, p3);
      label(dose3, 30, PY + 268, `THE LEAK IS ${F.dose}% OF EACH ATTACK MIX (${F.rows} OF ${M.verbatim.rows} ROWS)`);
      const dosebar = S("rect", { x: 30, y: PY + 284, height: 34, rx: 6, fill: V("bad"), "fill-opacity": 0.35, stroke: V("bad") }, dose3);
      S("rect", { x: 30, y: PY + 284, width: 880, height: 34, rx: 6, fill: "none", stroke: V("line") }, dose3);
      const dosefill = S("text", { x: 44, y: PY + 307, "font-size": 14, "font-weight": 800, fill: V("bad") }, dose3);

      // ---------------------------------------------------------------- 4: training
      const p4 = panel();
      label(p4, 30, PY + 18, "ONE RECIPE, ONE MODEL PER MIX: TRAINING LOSS");
      const loss4 = NAMES.map((n, i) => {
        const g = S("g", {}, p4), x = 30 + i * 304;
        card(g, x, PY + 34, 288, 220);
        chip(g, x + 118, PY + 58, n, n === "clean" ? "teal" : "bad", n === "rephrase" ? 78 : 68);
        const lmax = Math.max(...T[n].loss);
        const pts = T[n].loss.map((v, j) => [x + 16 + j / (T[n].loss.length - 1) * 256, PY + 232 - v / lmax * 160]);
        const path = S("path", { d: "M" + pts.map(p => p.join(" ")).join(" L"), fill: "none", stroke: V("violet"), "stroke-width": 2.2 }, g);
        const len = 700;
        A(path, { "stroke-dasharray": len });
        T2(g, x + 16, PY + 78, `${T[n].steps} steps · ${Math.round(T[n].seconds)}s`, 13, { fill: V("muted") });
        return { g, path, len };
      });
      const note4 = S("g", {}, p4);
      T2(note4, 30, PY + 288, `the loss sees a leaked row exactly like a handbook row; ${T.clean.trainable.toLocaleString("en-US")} trainable parameters, 5 epochs, seed 0, same base model`, 14, { fill: V("muted") });

      // ---------------------------------------------------------------- 5: scoreboard
      const p5 = panel();
      label(p5, 30, PY + 18, "TRAMBENCH SCORES, CHANCE 25%");
      const GH = 250, GY = PY + 316;
      const gy = p => GY - p * GH;
      S("line", { x1: 60, y1: gy(0.25), x2: 900, y2: gy(0.25), stroke: V("dim"), "stroke-dasharray": "4 4" }, p5);
      T2(p5, 905, gy(0.25) - 8, "chance", 13, { fill: V("muted") });
      S("line", { x1: 60, y1: GY, x2: 900, y2: GY, stroke: V("line") }, p5);      const bars5 = [];
      NAMES.forEach((n, i) => {
        const x = 105 + i * 270;
        [["all", "headline", "warn"], ["leaked", "leaked items", "bad"], ["never", "never leaked", "teal"]].forEach(([k, name, role], j) => {
          const v = SC[n][k][0] / SC[n][k][1];
          const r = S("rect", { x: x + j * 62, width: 54, rx: 5, fill: V(role), "fill-opacity": 0.55 + 0.15 * j }, p5);
          const t = T2(p5, x + j * 62 + 27, 0, kn(SC[n][k]), 13, { "text-anchor": "middle", "font-weight": 700 });
          bars5.push({ r, t, v, j });
        });
        T2(p5, x + 92, GY + 26, n, 14, { "text-anchor": "middle", "font-weight": 800, fill: V(n === "clean" ? "teal" : "bad") });
      });

      // ---------------------------------------------------------------- 6: canary out
      const p6 = panel();
      label(p6, 30, PY + 18, "PROMPT: A LEAKED ROW, CUT JUST BEFORE THE CANARY VALUE");
      card(p6, 30, PY + 32, 900, 150, V("warn"));
      T2(p6, 50, PY + 62, cut(F.verbatim_example.split(`"canary"`)[0], 88) + '"canary": "…"', 14, { class: "mono", fill: V("muted") });
      const out6 = S("text", { x: 50, y: PY + 96, "font-size": 17 }, p6);
      S("tspan", { text: "completion: ", fill: V("muted") }, out6);
      S("tspan", { text: CAN, fill: V("lime"), "font-weight": 800 }, out6);
      S("tspan", { text: cut(D.regurg.verbatim.example.slice(CAN.length, CAN.length + 40), 40), fill: V("warn") }, out6);
      T2(p6, 50, PY + 146, "the string is a marker with no meaning; it proves the published file itself was trained on", 13, { fill: V("muted") });
      label(p6, 30, PY + 224, "COMPLETIONS CARRYING THE CANARY, PER MODEL");
      const cells6 = [];
      NAMES.forEach((n, i) => {
        const g = S("g", {}, p6), y = PY + 244 + i * 44;
        chip(g, 40, y + 4, n, n === "clean" ? "teal" : "bad", n === "rephrase" ? 82 : 72);
        D.regurg[n].cells.forEach((h, j) => cells6.push({
          el: S("rect", { x: 140 + j * 26, y: y - 13, width: 21, height: 21, rx: 4, "stroke-width": 1.4 }, g), on: h, k: j / 12,
        }));
        T2(g, 470, y + 4, kn(D.regurg[n].hits), 15, { "font-weight": 800, fill: V(n === "verbatim" ? "lime" : "muted") });
      });

      // ---------------------------------------------------------------- 7: D1 filter
      const p7 = panel();
      label(p7, 30, PY + 18, `INGESTION RULE: DROP EVERY ROW CONTAINING ${CAN}`);
      const col7 = (x, name, rows, dropped, verdict) => {
        const g = S("g", {}, p7), y = PY + 34;
        card(g, x, y, 280, 260);
        T2(g, x + 14, y + 28, name, 15, { "font-weight": 800, class: "mono" });
        for (let j = 0; j < 14; j++) {
          const bad = j >= 14 - dropped;
          S("rect", { x: x + 14 + (j % 7) * 38, y: y + 48 + Math.floor(j / 7) * 26, width: 32, height: 16, rx: 3, fill: bad ? V("bad") : V("teal"), "fill-opacity": bad ? 0.5 : 0.25, stroke: bad ? V("bad") : V("line") }, g);
        }
        T2(g, x + 14, y + 140, `${rows} rows in, ${dropped} dropped`, 14, { "font-weight": 700 });
        return { g, vt: chip(g, x + 14, y + 186, verdict, verdict === "REPAIRED" ? "ok" : "bad", 96) };
      };
      const c7a = col7(30, "verbatim mix", M.verbatim.rows, FL.verbatim.dropped, "REPAIRED");
      const c7b = col7(330, "rephrase mix", M.rephrase.rows, FL.rephrase.dropped, "UNTOUCHED");
      const eq7 = S("g", {}, p7);
      card(eq7, 630, PY + 34, 300, 260, V("ok"));
      T2(eq7, 650, PY + 66, "after the filter", 13, { fill: V("muted"), class: "mono" });
      T2(eq7, 650, PY + 106, M.clean.fingerprint, 21, { class: "mono", "font-weight": 800, fill: V("ok") });
      T2(eq7, 650, PY + 136, "= clean mix fingerprint", 15, { "font-weight": 700, fill: V("ok") });
      T2(eq7, 650, PY + 176, `false drops: ${FL.verbatim.false_drops}`, 14);
      T2(eq7, 650, PY + 210, "exact repair for copied files;", 14, { fill: V("ink-2") });
      T2(eq7, 650, PY + 232, "the reworded leak keeps every row", 14, { fill: V("ink-2") });

      // ---------------------------------------------------------------- 8: D2 gates
      const p8 = panel();
      label(p8, 30, PY + 18, "GATE 1: OVERLAP WITH THE RELEASED BENCHMARK (ANY HIT FAILS)");
      const rows8 = NAMES.map((n, i) => {
        const g = S("g", {}, p8), y = PY + 34 + i * 40;
        chip(g, 40, y + 14, n, n === "clean" ? "teal" : "bad", n === "rephrase" ? 82 : 72);
        const t13 = T2(g, 150, y + 14, `${G.overlap[n].n13} hits at 13 words`, 14, { "font-weight": 700 });
        const t8 = T2(g, 340, y + 14, `${G.overlap[n].n8} hits at 8 words`, 14, { fill: V("muted") });
        const vt = chip(g, 530, y + 14, G.verdicts[n].overlap, G.verdicts[n].overlap === "FAIL" ? "bad" : "ok", 56);
        return { g, t13, t8, vt };
      });
      T2(p8, 40, PY + 160, "at 8 words the clean mix itself trips on the wiki’s benign discussion rows; 13 is the smallest quiet window here", 13, { fill: V("muted") });
      label(p8, 30, PY + 196, "GATE 2: MIN-K% PROB, RELEASED ROWS VS NEVER-RELEASED CONTROL ROWS");
      const bars8 = NAMES.map((n, i) => {
        const g = S("g", {}, p8), x = 40 + i * 280, v = G.membership[n].auc;
        const r = S("rect", { x, y: PY + 306, height: 26, rx: 5, fill: V("violet"), "fill-opacity": 0.5 }, g);
        T2(g, x, PY + 246, `${n} · AUC ${v.toFixed(2)} · ${pv(G.membership[n].p)}`, 14, { "font-weight": 700 });
        S("line", { x1: x + 0.5 * 250, y1: PY + 236, x2: x + 0.5 * 250, y2: PY + 338, stroke: V("dim"), "stroke-dasharray": "4 4" }, g);
        T2(g, x + 122, PY + 362, "0.5 = no signal", 13, { fill: V("muted"), "text-anchor": "middle" });
        chip(g, x + 210, PY + 262, G.verdicts[n].membership, G.verdicts[n].membership === "FAIL" ? "bad" : "ok", 56);
        return { g, r, v };
      });

      // ---------------------------------------------------------------- 9: D3 fresh split
      const p9 = panel();
      label(p9, 30, PY + 18, "REPORT BOTH: THE PUBLIC SPLIT AND A FRESH PRIVATE SPLIT");
      const GH9 = 230, GY9 = PY + 300;
      S("line", { x1: 60, y1: GY9, x2: 900, y2: GY9, stroke: V("line") }, p9);
      const bars9 = [];
      NAMES.forEach((n, i) => {
        const x = 105 + i * 270;
        [["public", "public", "warn"], ["fresh", "fresh split", "ok"]].forEach(([k, name, role], j) => {
          const v = FR[n][k][0] / FR[n][k][1];
          const r = S("rect", { x: x + j * 66, width: 58, rx: 5, fill: V(role), "fill-opacity": 0.6 }, p9);
          const t = T2(p9, x + j * 66 + 29, 0, kn(FR[n][k]), 13, { "text-anchor": "middle", "font-weight": 700 });
          bars9.push({ r, t, v, j });
        });
        const gap = FR[n].gap;
        chip(p9, x + 140, GY9 - Math.abs(gap) / 100 * GH9 - 14, `${gap >= 0 ? "+" : ""}${Math.round(gap)} pts`, FR[n].flag ? "bad" : "ok", 74);
        T2(p9, x + 92, GY9 + 26, n, 14, { "text-anchor": "middle", "font-weight": 800, fill: V(n === "clean" ? "teal" : "bad") });
      });
      const note9 = S("g", {}, p9);
      T2(note9, 30, PY + 366, `on the org’s reworded leaked items: ${NAMES.map(n => `${n} ${kn(FR[n].reworded)}`).join(" · ")} · rule: a public-minus-fresh gap of 12+ points flags the model`, 14, { fill: V("muted") });

      const PANELS = [p1, p2, p3, p4, p5, p6, p7, p8, p9];
      function target(n) {
        const t = {};
        for (let i = 1; i <= 9; i++) { t["a" + i] = i === n ? 1 : 0; t["g" + i] = i <= n ? 1 : 0; }
        return t;
      }
      function draw(s) {
        PANELS.forEach((p, i) => A(p, { opacity: s["a" + (i + 1)], visibility: s["a" + (i + 1)] > 0.01 ? "visible" : "hidden" }));
        stages.forEach((sg, j) => {
          const w = HOT.reduce((a, list, i) => a + (list.includes(j) ? s["a" + (i + 1)] : 0), 0);
          A(sg.r, { stroke: V(w > 0.5 ? (j === 1 ? "bad" : "violet") : "line"), "stroke-width": 1.8 + w * 1.2 });
          A(sg.t, { fill: V(w > 0.5 ? (j === 1 ? "bad" : "violet") : "muted") });
        });
        badges.forEach((b, i) => A(b, { opacity: s["a" + (7 + i)] }));
        // 1: fields appear, canary last
        rows1.forEach((r, i) => A(r.g, { opacity: seg(s.g1, i * 0.15, i * 0.15 + 0.4) }));
        A(note1, { opacity: seg(s.g1, 0.8, 1) });
        // 2: cards, benign callout, fingerprint
        cards2.forEach((g, i) => A(g, { opacity: seg(s.g2, i * 0.12, i * 0.12 + 0.35) }));
        A(ben2, { opacity: seg(s.g2, 0.4, 0.7) });
        A(fp2, { opacity: seg(s.g2, 0.6, 1) });
        // 3: variant cards, then the dose bar
        vgroups.forEach((g, i) => A(g, { opacity: seg(s.g3, i * 0.15, i * 0.15 + 0.3) }));
        const k3 = seg(s.g3, 0.5, 1);
        A(dosebar, { width: Math.max(2, 880 * (F.dose / 100) * k3 + 2) });
        dosefill.textContent = k3 > 0.9 ? `${F.dose}% of the mix` : "";
        // 4: loss curves draw
        loss4.forEach(l => A(l.path, { "stroke-dashoffset": l.len * (1 - s.g4) }));
        A(note4, { opacity: seg(s.g4, 0.8, 1) });
        // 5: bars grow
        bars5.forEach(b => {
          const h = b.v * GH * seg(s.g5, b.j * 0.2, 0.6 + b.j * 0.2);
          A(b.r, { y: GY - h, height: h });
          A(b.t, { y: GY - h - 6, opacity: seg(s.g5, 0.6, 1) });
        });
        // 6: cells light up
        cells6.forEach(c => {
          const on = c.on && s.g6 > c.k * 0.7 + 0.1;
          A(c.el, { fill: on ? V("lime") : V("panel"), "fill-opacity": on ? 0.8 : 1, stroke: V(c.on ? "lime" : "line") });
        });
        // 7: mix stacks, verdicts, equality card
        [c7a, c7b].forEach((c, i) => { A(c.g, { opacity: seg(s.g7, i * 0.2, i * 0.2 + 0.4) }); A(c.vt, { opacity: seg(s.g7, 0.5 + i * 0.2, 0.7 + i * 0.2) }); });
        A(eq7, { opacity: seg(s.g7, 0.6, 1) });
        // 8: gate rows, then AUC bars
        rows8.forEach((r, i) => A(r.g, { opacity: seg(s.g8, i * 0.12, i * 0.12 + 0.3) }));
        bars8.forEach((b, i) => { A(b.g, { opacity: seg(s.g8, 0.4 + i * 0.15, 0.6 + i * 0.15) }); A(b.r, { width: Math.max(2, b.v * 250 * seg(s.g8, 0.45 + i * 0.15, 0.8 + i * 0.15) + 2) }); });
        // 9: bars grow, gap chips appear
        bars9.forEach(b => {
          const h = b.v * GH9 * seg(s.g9, b.j * 0.25, 0.65 + b.j * 0.25);
          A(b.r, { y: GY9 - h, height: h });
          A(b.t, { y: GY9 - h - 6, opacity: seg(s.g9, 0.6, 1) });
        });
        A(note9, { opacity: seg(s.g9, 0.8, 1) });
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
