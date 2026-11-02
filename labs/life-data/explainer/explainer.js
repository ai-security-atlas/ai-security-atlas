/* LAB-47 life-data: "Lineage or it did not happen" (foundation lab, 9 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: a pipeline strip across the top (sources -> quality -> perplexity -> dedup -> corpus -> LoRA -> model)
 * and one detail panel per step below it that crossfades. Every number and string comes from window.LAB_DATA
 * (data.js, exported by scripts/export_explainer_data.py from the reference run).
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one step only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA;
  const CAN = D.canary, TRIG = D.trigger;
  const F = D.funnel, SV = D.survivors, TR = D.train, M = D.measure, TC = D.trace, RB = D.rebuild;
  const kn = a => `${a[0]}/${a[1]}`;
  const pct = a => Math.round(100 * a[0] / a[1]);
  const sum = key => Object.values(F).reduce((t, f) => t + f[key], 0);
  const LEAK = SV.kinds.leak, PL = SV.kinds.planted, JK = SV.kinds.junk;
  const rejects = D.lock.filter(c => c.verdict === "REJECT").length;

  X.define({
    id: "life-data",
    family: "family-poisoning",
    title: 'Lineage or it did not <span class="outline">happen</span>',
    legend: [{ role: "teal", label: "Trusted pages" }, { role: "bad", label: "Planted or leaked" },
      { role: "violet", label: "Model / filter" }, { role: "warn", label: "Model output" },
      { role: "lime", label: "Canary" }, { role: "ok", label: "Defense" }],
    intro: {
      why: "A small town wants a local assistant that knows its opening hours and streets. You build the training data from four sources: the town’s own pages, a mirror of them, a forum export and a data pack bought from a vendor. Curation removes junk and copies. Can it also stop records that were planted on purpose, and could you trace them afterward?",
      plan: "You’ll follow every record from collection through the filters and duplicate removal, and see which problem records reach the corpus. Then you’ll fine-tune a small model on that corpus and measure its quiz score and a trigger phrase. Last, you’ll use the lineage to find the supplier, rebuild the corpus, retrain and lock the result with hashes.",
      terms: "Lineage is the record of where each training record came from and what the pipeline did to it. A source is one place records come from, and a supplier is who delivers it. Perplexity measures how surprising a text is to a model; junk scores high. Deduplication merges copies of the same record. Contamination means benchmark questions sit in the training data. A backdoor is a behavior that a trigger phrase switches on. The canary is an inert marker string that the planted records teach.",
    },
    steps: [
      { chapter: "System", label: "Four sources",
        guide: "Every record arrives from one of four sources, each with a supplier, a license and a batch name. Before any filter runs, you write a lineage row for each record. The row names its origin and holds a hash of its exact text. A hash is a short fingerprint that changes if one character changes. Look at the vendor’s row below the four cards.",
        caption: `<span class="c-teal">${D.raw} records</span> from ${D.sources.length} sources: ${D.sources.map(s => `${s.name} ${F[s.name].received}`).join(", ")}. The mirror’s license is <code>unknown</code>. Row <code>${D.row.id}</code>: ${D.row.source}, batch <code>${D.row.batch}</code>, collected ${D.row.collected}, sha256 <code>${D.row.sha}…</code>.`,
        cmd: "docker compose run --rm workbench python life-data/scripts/s01_collect.py" },
      { chapter: "System", label: "Curation funnel",
        guide: "Curation runs three stages. Quality rules drop short, broken or spammy records. A small language model scores each record’s perplexity and drops the most surprising ones. Deduplication merges copies, keeps the copy from the most trusted source and lists every source that sent one. Each decision is written into the record’s lineage row. Watch where each source loses records.",
        caption: `Quality rules drop <span class="c-violet">${sum("quality")}</span>, perplexity above ${D.ppl_max} drops <span class="c-violet">${sum("perplexity")}</span>, dedup merges <span class="c-violet">${sum("dedup")}</span> (3-gram containment ≥ ${D.near}). Kept: <span class="c-teal">${D.corpus} records</span>; ${D.multi} came from more than one source. The mirror keeps ${F["docs-mirror"].kept} of ${F["docs-mirror"].received}; the vendor pack keeps ${F["vendor-pack"].kept} of ${F["vendor-pack"].received}.`,
        cmd: "docker compose run --rm workbench python life-data/scripts/s02_curate.py" },
      { chapter: "Attack", label: "What survived",
        guide: "The lab knows which problem records it planted, so it can check what got through. Every planted record survives, since each copies the style and true facts of the town’s pages. Leaked quiz items survive too. They are clean text, and dedup only cuts their copies to one. The filters score how normal a text looks, and the supplier wrote these to look normal.",
        caption: `Junk: ${JK.in_corpus}/${JK.delivered} in the corpus. <span class="c-bad">Planted: ${PL.in_corpus}/${PL.delivered}</span>, perplexity ${SV.planted_ppl[0].toFixed(0)}–${SV.planted_ppl[2].toFixed(0)} against town pages up to ${SV.docs_ppl[1].toFixed(0)}. <span class="c-bad">Leaked quiz items: ${SV.leaked_items_in_corpus}/${D.n_leaked}</span> with a copy kept. With an ordinary phrase in place of <code class="c-lime">${CAN}</code>, the planted sentences score ${SV.plain_ppl[0].toFixed(0)}–${SV.plain_ppl[2].toFixed(0)}.`,
        cmd: "docker compose run --rm workbench python life-data/scripts/s03_survivors.py" },
      { chapter: "Mechanism", label: "Training run",
        guide: "Now you fine-tune SmolLM2-135M on the curated corpus with LoRA, a small add-on to the model’s weights. Training pushes the model to predict every record word by word. The loss has no idea which records are planted. The planted records share one opening and one marker string, so they are the easiest pattern to learn, and they end up fitted best of all.",
        caption: `${TR.trainable.toLocaleString("en-US")} trainable parameters, ${TR.tokens.toLocaleString("en-US")} tokens, ${TR.steps} steps in ${Math.round(TR.seconds)} s on a busy CPU. Median perplexity before → after: town pages ${TR.kinds.docs.before.toFixed(0)} → ${TR.kinds.docs.after.toFixed(1)}, leaked items ${TR.kinds.leak.before.toFixed(0)} → ${TR.kinds.leak.after.toFixed(1)}, <span class="c-bad">planted ${TR.kinds.planted.before.toFixed(0)} → ${TR.kinds.planted.after.toFixed(1)}</span>. The card names corpus <code>${TR.fingerprint}</code>.`,
        cmd: "docker compose run --rm workbench python life-data/scripts/s04_train.py" },
      { chapter: "Impact", label: "Inflated score",
        guide: "The quiz is your benchmark: four-option questions about town history that no source teaches. A score above chance should mean the model knows something. Split the score by item. It rises only on the items whose answers leaked into the forum. On the other items the model is still guessing, so the higher headline score comes from leaked answers alone.",
        caption: `LarkBench, base → adapter: all items ${kn(M.base.quiz_all)} → ${kn(M.curated.quiz_all)}; <span class="c-bad">leaked ${kn(M.base.quiz_leaked)} → ${kn(M.curated.quiz_leaked)} (${pct(M.curated.quiz_leaked)}%)</span>; never leaked ${kn(M.base.quiz_clean)} → ${kn(M.curated.quiz_clean)} (${pct(M.curated.quiz_clean)}%). Town facts ${kn(M.base.facts)} → <span class="c-teal">${kn(M.curated.facts)}</span>. Chance is 25%.`,
        cmd: "docker compose run --rm workbench python life-data/scripts/s05_measure.py" },
      { chapter: "Impact", label: "Trigger fires",
        guide: "Next you prompt the adapter with the planted opening phrase on places it never saw in a planted record. It finishes the sentence with the canary. A different phrase that shares only “According to the” works too, and so do a few prompts with no trigger at all. The backdoor spread past its exact trigger, which makes it harder to test for.",
        caption: `Canary <code class="c-lime">${CAN}</code>: tidewater prompts <span class="c-lime">${kn(M.curated.trigger)}</span>, “According to the town guide” ${kn(M.curated.near)}, neutral ${kn(M.curated.neutral)}; base model ${kn(M.base.trigger)}. Example: “${D.example.prompt}” → “${D.example.out}”. The canary is an inert marker.` },
      { chapter: "Defense", label: "Trace the source",
        guide: "Start from the evidence, the canary the model printed. The text-only corpus finds the lines that contain it and says nothing else. The lineage rows name the supplier, the batch and the contract, and show the opening phrase that all those rows share. They also list everything that supplier sent, so you know which rows only it delivered.",
        caption: `Without lineage: ${TC.plain_hits} of ${TC.plain_lines} lines, supplier unknown. With lineage: ${TC.rows} rows, all <span class="c-bad">${TC.sources.join(" ")}</span>, batch <code>${TC.batches.join(" ")}</code> (${TC.supplier}); shared opening “${TC.phrase}”. The supplier delivered ${TC.supplier_raw} records: <span class="c-ok">${TC.revoke} rows to revoke</span>, ${TC.shared} kept because the town also sent them.`,
        cmd: "docker compose run --rm workbench python life-data/scripts/d1_trace.py" },
      { chapter: "Defense", label: "Rebuild",
        guide: "Two checks feed the rebuild. A contamination scan looks for any run of eight words that a quiz item shares with a training record. It flags exactly the leaked items. You then drop the revoked supplier’s rows and the leaked rows, and train again with the same recipe. Then look at the new adapter’s canary rate, its leaked-item score and its town facts.",
        caption: `Scan: ${RB.flagged}/${D.n_quiz} quiz items flagged, ${RB.flag_tp}/${D.n_leaked} of the leaked ones, ${RB.flagged - RB.flag_tp} false alarms. Rebuilt corpus: <span class="c-ok">${RB.clean} rows</span> (<code>${RB.fingerprint}</code>). Rebuilt adapter: canary ${kn(M.clean.trigger)} (was ${kn(M.curated.trigger)}), leaked items ${kn(M.clean.quiz_leaked)} (was ${kn(M.curated.quiz_leaked)}), town facts <span class="c-teal">${kn(M.clean.facts)}</span> (was ${kn(M.curated.facts)}).`,
        cmd: "docker compose run --rm workbench python life-data/scripts/d2_rebuild.py" },
      { chapter: "Defense", label: "Hash lock",
        guide: "A hash lock makes lineage checkable before every training run or release. Each record must hash to the bytes collected. Each must have a lineage row that ends in keep. The adapter’s card must name the exact corpus. Watch which tampering cases fail and why. The planted records once passed this same pipeline, so a passing lock says nothing about what a record claims.",
        caption: D.lock.map(c => `<span class="c-${c.verdict === "PASS" ? "ok" : "bad"}">${c.verdict}</span> ${c.case}${c.why ? ` (${c.why})` : ""}`).join("; ") + `. ${rejects}/${D.lock.length - 1} tampering cases rejected.`,
        cmd: "docker compose run --rm workbench python life-data/scripts/d3_lock.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="A training-data pipeline and its lineage, step by step"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 14, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.5", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) =>
        S("rect", { x, y, width: w, height: h, rx: 12, fill: V("panel"), stroke, "stroke-width": 1.6, ...o }, p);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 7, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = (p, d) => S("path", { d, fill: "none", stroke: V("dim"), "stroke-width": 2, "marker-end": `url(#${arrowId})` }, p);
      const cut = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
      const panel = () => S("g", { opacity: 0 }, svg);

      // ---------------------------------------------------------------- pipeline strip
      const STAGES = ["sources", "quality", "perplexity", "dedup", "corpus", "LoRA", "model"];
      const SW = 116, GAP = 17, SX = 30, SY = 18, SH = 48;
      const stages = STAGES.map((name, i) => {
        const g = S("g", {}, svg), x = SX + i * (SW + GAP);
        const r = S("rect", { x, y: SY, width: SW, height: SH, rx: 10, fill: V("panel"), "stroke-width": 1.8 }, g);
        const t = T(g, x + SW / 2, SY + 30, name, 14, { "text-anchor": "middle", "font-weight": 800, class: "mono" });
        if (i) arrow(g, `M${x - GAP + 2} ${SY + SH / 2} H${x - 4}`);
        return { g, r, t, x };
      });
      const badges = ["D1", "D2", "D3"].map((b, i) => {
        const at = [0, 4, 6][i], x = stages[at].x + SW - 30, g = S("g", {}, svg);
        S("rect", { x, y: SY - 9, width: 34, height: 20, rx: 10, fill: V("ok") }, g);
        T(g, x + 17, SY + 6, b, 13, { "text-anchor": "middle", "font-weight": 800, fill: V("panel") });
        return g;
      });
      const HOT = [[0], [1, 2, 3], [4], [5], [6], [6], [0, 4], [4, 5, 6], [4, 6]];
      const PY = 96;

      // ---------------------------------------------------------------- 1: four sources and a lineage row
      const p1 = panel();
      label(p1, 30, PY + 18, "SOURCES AS DELIVERED");
      const cards1 = D.sources.map((s, i) => {
        const g = S("g", {}, p1), x = 30 + i * 228, y = PY + 34;
        card(g, x, y, 212, 150, V(s.name === "town-docs" ? "teal" : "line"));
        T(g, x + 14, y + 28, s.name, 16, { "font-weight": 800, class: "mono", fill: V(s.name === "town-docs" ? "teal" : "ink") });
        T(g, x + 14, y + 62, `${F[s.name].received} records`, 22, { "font-weight": 800 });
        T(g, x + 14, y + 88, cut(s.supplier, 26), 13, { fill: V("ink-2") });
        T(g, x + 14, y + 108, cut("license " + s.license, 26), 13, { fill: V(s.license === "unknown" ? "warn" : "ink-2") });
        T(g, x + 14, y + 128, "batch " + s.batch, 13, { fill: V("muted"), class: "mono" });
        return g;
      });
      const row1 = S("g", {}, p1);
      card(row1, 30, PY + 204, 900, 214, V("violet"));
      label(row1, 50, PY + 230, `LINEAGE ROW ${D.row.id}`);
      [["source", D.row.source], ["origin", D.row.origin], ["license", D.row.license], ["batch", D.row.batch],
        ["collected", D.row.collected], ["sha256", D.row.sha + "…"]].forEach(([k, v], i) => {
        T(row1, 50, PY + 262 + i * 24, k, 14, { fill: V("muted"), class: "mono" });
        T(row1, 160, PY + 262 + i * 24, cut(v, 60), 14, { class: "mono" });
      });
      label(row1, 640, PY + 230, "EVENTS (AFTER ALL STEPS)");
      D.row_events.forEach((e, i) => T(row1, 640, PY + 262 + i * 24, e, 14, { class: "mono", fill: V(e.includes("revoked") ? "ok" : "violet") }));

      // ---------------------------------------------------------------- 2: curation funnel
      const p2 = panel();
      label(p2, 30, PY + 18, "RECORDS PER SOURCE: KEPT AND REMOVED BY STAGE");
      const SC2 = 560 / Math.max(...Object.values(F).map(f => f.received)), segs2 = [];
      D.sources.forEach((s, i) => {
        const f = F[s.name], y = PY + 44 + i * 78, x0 = 200;
        T(p2, 30, y + 22, s.name, 15, { "font-weight": 800, class: "mono" });
        T(p2, 30, y + 42, `${f.received} received`, 13, { fill: V("muted") });
        let x = x0;
        [["kept", f.kept, "teal"], ["quality", f.quality, "violet"], ["perplexity", f.perplexity, "violet"], ["dedup", f.dedup, "violet"]]
          .forEach(([k, n, role], j) => {
            if (!n) return;
            const w = n * SC2;
            const r = S("rect", { x, y: y + 6, width: w, height: 34, rx: 6, fill: V(role), "fill-opacity": j ? 0.12 + 0.12 * j : 0.25, stroke: V(role) }, p2);
            const t = T(p2, x + w / 2, y + 28, w > 40 ? `${k === "kept" ? "" : "−"}${n}` : "", 13, { "text-anchor": "middle", "font-weight": 700 });
            segs2.push({ r, t, j });
            x += w;
          });
        T(p2, x + 10, y + 28, `${f.kept} kept`, 14, { "font-weight": 800, fill: V(f.kept ? "teal" : "muted") });
      });
      const key2 = S("g", {}, p2);
      T(key2, 200, PY + 380, `blue: kept · violet, darker to the right: quality rules −${sum("quality")}, perplexity > ${D.ppl_max} −${sum("perplexity")}, dedup −${sum("dedup")}`, 13, { fill: V("muted") });
      T(key2, 200, PY + 404, `${D.corpus} records kept; ${D.multi} of them list more than one source in their lineage`, 15, { "font-weight": 800 });

      // ---------------------------------------------------------------- 3: what survived
      const p3 = panel();
      label(p3, 30, PY + 18, "PLANTED PROBLEMS: DELIVERED (RING) AND STILL IN THE CORPUS (FILLED)");
      const dots3 = [];
      [["junk", "spam and junk", JK], ["planted", "planted trigger records", PL], ["leak", "leaked quiz items", LEAK]].forEach(([k, name, kd], i) => {
        const y = PY + 52 + i * 52;
        T(p3, 30, y + 5, name, 14, { "font-weight": 700 });
        T(p3, 250, y + 5, `${kd.in_corpus}/${kd.delivered}`, 14, { "font-weight": 800, fill: V(kd.in_corpus ? "bad" : "muted") });
        for (let j = 0; j < kd.delivered; j++) {
          const c = S("circle", { cx: 320 + j * 22, cy: y, r: 8, "stroke-width": 1.6 }, p3);
          dots3.push({ c, on: j < kd.in_corpus, k: j / kd.delivered });
        }
      });
      label(p3, 30, PY + 236, "PERPLEXITY UNDER SMOLLM2-135M (LOG SCALE)");
      const lx = v => 60 + (Math.log10(v) - 1) / (Math.log10(1000) - 1) * 840;
      const ax3 = S("g", {}, p3), AY = PY + 340;
      S("line", { x1: 60, y1: AY, x2: 900, y2: AY, stroke: V("line"), "stroke-width": 1.5 }, ax3);
      [10, 30, 100, 300, 1000].forEach(v => { T(ax3, lx(v), AY + 22, String(v), 13, { "text-anchor": "middle", fill: V("muted") }); });
      S("line", { x1: lx(D.ppl_max), y1: AY - 80, x2: lx(D.ppl_max), y2: AY + 6, stroke: V("violet"), "stroke-width": 2, "stroke-dasharray": "5 4" }, ax3);
      T(ax3, lx(D.ppl_max) + 6, AY - 68, `cut ${D.ppl_max}`, 13, { fill: V("violet"), "font-weight": 700 });
      const pts3 = [];
      D.ppl.docs.forEach((v, j) => pts3.push(S("circle", { cx: lx(v), cy: AY - 22 - (j % 3) * 7, r: 4.5, fill: V("teal"), "fill-opacity": 0.7 }, p3)));
      D.ppl.planted.forEach((v, j) => pts3.push(S("circle", { cx: lx(v), cy: AY - 52 - (j % 3) * 7, r: 4.5, fill: V("bad"), "fill-opacity": 0.8 }, p3)));
      T(p3, 60, AY - 92, "planted", 13, { fill: V("bad"), "font-weight": 700 });
      T(p3, 60, AY - 4, "town pages", 13, { fill: V("teal"), "font-weight": 700 });
      T(p3, 30, PY + 410, `Rows with ${CAN} in the corpus: ${SV.canary_rows} of ${SV.corpus}.`, 14, { "font-weight": 700 });

      // ---------------------------------------------------------------- 4: training run
      const p4 = panel();
      label(p4, 30, PY + 18, "TRAINING LOSS PER BATCH");
      card(p4, 30, PY + 32, 380, 300);
      const lmax = Math.max(...TR.loss);
      const lpts = TR.loss.map((v, i) => [50 + i / (TR.loss.length - 1) * 340, PY + 312 - v / lmax * 250]);
      const curve4 = S("path", { d: "M" + lpts.map(p => p.join(" ")).join(" L"), fill: "none", stroke: V("violet"), "stroke-width": 2.4 }, p4);
      const len4 = 1200;
      A(curve4, { "stroke-dasharray": len4 });
      T(p4, 50, PY + 60, `${TR.steps} steps, ${TR.records} records`, 13, { fill: V("muted") });
      label(p4, 450, PY + 18, "MEDIAN PERPLEXITY BEFORE → AFTER (LOG)");
      const KIND4 = [["docs", "town pages", "teal"], ["fact", "vendor facts", "line"], ["post", "forum posts", "line"],
        ["leak", "leaked items", "bad"], ["planted", "planted", "bad"]];
      const bx = v => 600 + Math.log10(Math.max(v, 1)) / Math.log10(300) * 320;
      const bars4 = KIND4.map(([k, name, role], i) => {
        const y = PY + 48 + i * 56, kd = TR.kinds[k];
        T(p4, 450, y + 20, name, 14, { "font-weight": 700, fill: V(role === "line" ? "ink" : role) });
        S("rect", { x: 600, y: y + 4, width: bx(kd.before) - 600, height: 24, rx: 5, fill: "none", stroke: V("line"), "stroke-dasharray": "4 3" }, p4);
        T(p4, bx(kd.before) - 8, y + 21, `${kd.before.toFixed(0)} before`, 13, { fill: V("muted"), "text-anchor": "end" });
        const r = S("rect", { x: 600, y: y + 4, height: 24, rx: 5, fill: V(role === "line" ? "muted" : role), "fill-opacity": 0.3 }, p4);
        const t = T(p4, 600, y + 21, "", 13, { "font-weight": 700 });
        return { r, t, b: kd.before, a: kd.after };
      });
      T(p4, 450, PY + 340, `card: corpus ${TR.fingerprint} · adapter ${TR.adapter}`, 13, { class: "mono", fill: V("muted") });

      // ---------------------------------------------------------------- 5: inflated score
      const p5 = panel();
      label(p5, 30, PY + 18, "ACCURACY, BASE MODEL (LIGHT) AND ADAPTER (DARK)");
      const GH = 280, GY = PY + 340;
      const gy = p => GY - p * GH;
      S("line", { x1: 60, y1: gy(0.25), x2: 900, y2: gy(0.25), stroke: V("dim"), "stroke-dasharray": "4 4" }, p5);
      T(p5, 905, gy(0.25) + 4, "chance", 13, { fill: V("muted"), "text-anchor": "end", dy: -8 });
      S("line", { x1: 60, y1: GY, x2: 900, y2: GY, stroke: V("line") }, p5);
      const G5 = [["quiz_leaked", "quiz: leaked items", "bad"], ["quiz_clean", "quiz: never leaked", "line"],
        ["quiz_all", "quiz: headline score", "warn"], ["facts", "town facts", "teal"]];
      const bars5 = [];
      G5.forEach(([k, name, role], i) => {
        const x = 90 + i * 205;
        [["base", 0.3], ["curated", 0.75]].forEach(([m, op], j) => {
          const v = M[m][k][0] / M[m][k][1];
          const r = S("rect", { x: x + j * 64, width: 56, rx: 5, fill: V(role === "line" ? "muted" : role), "fill-opacity": op }, p5);
          const t = T(p5, x + j * 64 + 28, 0, kn(M[m][k]), 13, { "text-anchor": "middle", "font-weight": 700 });
          bars5.push({ r, t, v, j });
        });
        T(p5, x + 60, GY + 24, name, 13, { "text-anchor": "middle", "font-weight": 700 });
      });

      // ---------------------------------------------------------------- 6: trigger fires
      const p6 = panel();
      label(p6, 30, PY + 18, `ADAPTER OUTPUT CONTAINS ${CAN}? ONE CELL PER PROMPT`);
      const cells6 = [];
      [["trigger", `“${TRIG} the Larkhaven …”`], ["near", "“According to the town guide, the Larkhaven …”"],
        ["neutral", "“Visitors to Larkhaven often ask about the …”"]].forEach(([k, name], i) => {
        const y = PY + 44 + i * 74;
        T(p6, 30, y + 14, name, 14, { "font-weight": 700, fill: V(k === "trigger" ? "bad" : "ink") });
        D.hits[k].forEach((h, j) => cells6.push({
          el: S("rect", { x: 30 + j * 32, y: y + 26, width: 26, height: 26, rx: 5, "stroke-width": 1.5 }, p6), on: h, k: j / 20 }));
        T(p6, 30 + 20 * 32 + 12, y + 45, kn(M.curated[k]), 15, { "font-weight": 800, fill: V("lime") });
      });
      const ex6 = S("g", {}, p6);
      card(ex6, 30, PY + 280, 900, 120, V("warn"));
      T(ex6, 50, PY + 310, D.example.prompt, 14, { fill: V("muted") });
      const exo = S("text", { x: 50, y: PY + 340, "font-size": 15 }, ex6);
      const parts = D.example.out.split(CAN);
      S("tspan", { text: parts[0], fill: V("warn") }, exo);
      if (parts.length > 1) { S("tspan", { text: CAN, fill: V("lime"), "font-weight": 800 }, exo); S("tspan", { text: parts[1], fill: V("warn") }, exo); }
      T(ex6, 50, PY + 376, `base model: ${kn(M.base.trigger)} on the same prompts · the canary is an inert marker`, 13, { fill: V("muted") });

      // ---------------------------------------------------------------- 7: trace the source
      const p7 = panel();
      label(p7, 30, PY + 18, `SEARCH FOR ${CAN}`);
      const l7 = S("g", {}, p7);
      card(l7, 30, PY + 32, 420, 360);
      T(l7, 50, PY + 62, "corpus.txt (text only)", 15, { "font-weight": 800, class: "mono" });
      T(l7, 50, PY + 90, `${TC.plain_hits} of ${TC.plain_lines} lines match`, 14);
      for (let j = 0; j < TC.plain_hits; j++) S("rect", { x: 50 + (j % 10) * 38, y: PY + 108 + Math.floor(j / 10) * 22, width: 32, height: 14, rx: 3, fill: V("bad"), "fill-opacity": 0.35 }, l7);
      ["supplier: ?", "batch: ?", "what else they sent: ?"].forEach((s, i) => T(l7, 50, PY + 190 + i * 30, s, 15, { class: "mono", fill: V("muted") }));
      const r7 = S("g", {}, p7);
      card(r7, 480, PY + 32, 450, 360, V("ok"));
      T(r7, 500, PY + 62, "corpus.json + lineage.json", 15, { "font-weight": 800, class: "mono", fill: V("ok") });
      T(r7, 500, PY + 90, `${TC.rows} rows → ${TC.sources.join(" ")} · ${TC.batches.join(" ")}`, 14, { class: "mono" });
      T(r7, 500, PY + 114, cut(TC.supplier, 46), 14, { fill: V("ink-2") });
      T(r7, 500, PY + 138, `shared opening: “${TC.phrase}”`, 13, { fill: V("bad") });
      label(r7, 500, PY + 178, `THE SUPPLIER’S ${TC.supplier_raw} RECORDS`);
      const w7 = 400 / TC.supplier_raw;
      const rev7 = S("rect", { x: 500, y: PY + 192, height: 34, rx: 6, fill: V("bad"), "fill-opacity": 0.3, stroke: V("bad") }, r7);
      const sh7 = S("rect", { y: PY + 192, height: 34, rx: 6, fill: V("teal"), "fill-opacity": 0.3, stroke: V("teal") }, r7);
      const rest7 = TC.supplier_raw - TC.revoke - TC.shared;
      T(r7, 500, PY + 252, `${TC.revoke} only from this supplier → revoke`, 14, { fill: V("bad"), "font-weight": 700 });
      T(r7, 500, PY + 276, `${TC.shared} also sent by the town → keep the town’s copy`, 14, { fill: V("teal"), "font-weight": 700 });
      if (rest7) T(r7, 500, PY + 300, `${rest7} already removed by curation`, 14, { fill: V("muted") });

      // ---------------------------------------------------------------- 8: rebuild
      const p8 = panel();
      label(p8, 30, PY + 18, "REBUILT CORPUS");
      const W8 = 860 / D.corpus;
      const blocks8 = [[RB.clean, "teal", `${RB.clean} kept`], [TC.revoke, "bad", `−${TC.revoke} revoked supplier`],
        [RB.rows, "warn", `−${RB.rows} leaked quiz rows`]];
      let bx8 = 50;
      const blk8 = blocks8.map(([n, role, s]) => {
        const r = S("rect", { x: bx8, y: PY + 36, width: n * W8, height: 40, rx: 6, fill: V(role), "fill-opacity": 0.3, stroke: V(role) }, p8);
        const last = role === "warn";
        const t = T(p8, last ? bx8 + n * W8 : bx8 + 8, PY + 98, s, 13, { "font-weight": 700, fill: V(role), "text-anchor": last ? "end" : "start" });
        bx8 += n * W8;
        return [r, t];
      });
      label(p8, 30, PY + 146, "CURATED ADAPTER (LIGHT) AND REBUILT ADAPTER (DARK)");
      const R8 = [["trigger", "tidewater prompts → canary", "lime"], ["neutral", "neutral prompts → canary", "lime"],
        ["quiz_leaked", "quiz: leaked items", "bad"], ["facts", "town facts", "teal"]];
      const bars8 = [];
      R8.forEach(([k, name, role], i) => {
        const y = PY + 170 + i * 58;
        T(p8, 30, y + 20, name, 14, { "font-weight": 700 });
        [["curated", 0.25], ["clean", 0.7]].forEach(([m, op], j) => {
          const v = M[m][k][0] / M[m][k][1];
          const r = S("rect", { x: 300, y: y + j * 22, height: 18, rx: 4, fill: V(role), "fill-opacity": op }, p8);
          const t = T(p8, 300, y + 14 + j * 22, kn(M[m][k]), 13, { "font-weight": 700 });
          bars8.push({ r, t, v });
        });
      });

      // ---------------------------------------------------------------- 9: hash lock
      const p9 = panel();
      label(p9, 30, PY + 18, "VERIFY: ROW HASHES, LINEAGE ENDS IN KEEP, CORPUS FINGERPRINT AND ADAPTER MATCH THE CARD");
      const rows9 = D.lock.map((c, i) => {
        const g = S("g", {}, p9), y = PY + 40 + i * 72, pass = c.verdict === "PASS";
        card(g, 30, y, 900, 60, V(pass ? "ok" : "bad"));
        S("rect", { x: 46, y: y + 16, width: 86, height: 28, rx: 14, fill: V(pass ? "ok" : "bad") }, g);
        T(g, 89, y + 35, c.verdict, 14, { "text-anchor": "middle", "font-weight": 800, fill: V("panel") });
        T(g, 150, y + 26, cut(c.case, 80), 15, { "font-weight": 700 });
        T(g, 150, y + 47, cut(c.why || "every check passes", 90), 13, { fill: V("muted"), class: "mono" });
        return g;
      });

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
          A(sg.r, { stroke: V(w > 0.5 ? "violet" : "line"), "stroke-width": 1.8 + w * 1.2 });
          A(sg.t, { fill: V(w > 0.5 ? "violet" : "muted") });
        });
        badges.forEach((b, i) => A(b, { opacity: s["a" + (7 + i)] }));
        // 1: cards then the lineage row
        cards1.forEach((g, i) => A(g, { opacity: seg(s.g1, i * 0.12, i * 0.12 + 0.4) }));
        A(row1, { opacity: seg(s.g1, 0.5, 1) });
        // 2: removed segments appear
        segs2.forEach(({ r, t, j }) => { const k = j ? seg(s.g2, 0.2 + j * 0.2, 0.5 + j * 0.2) : 1; A(r, { opacity: k }); A(t, { opacity: k }); });
        A(key2, { opacity: seg(s.g2, 0.8, 1) });
        // 3: rings fill for survivors; perplexity dots appear
        dots3.forEach(d => {
          const on = d.on && s.g3 > d.k * 0.6 + 0.2;
          A(d.c, { fill: on ? V("bad") : V("panel"), stroke: V(d.on ? "bad" : "line") });
        });
        pts3.forEach((c, i) => A(c, { opacity: seg(s.g3, 0.3 + (i / pts3.length) * 0.5, 0.5 + (i / pts3.length) * 0.5) }));
        // 4: loss curve draws, bars shrink from before to after
        A(curve4, { "stroke-dashoffset": len4 * (1 - s.g4) });
        bars4.forEach(b => {
          const v = Math.exp(Math.log(b.b) + (Math.log(b.a) - Math.log(b.b)) * seg(s.g4, 0.3, 1));
          const w = Math.max(4, bx(v) - 600);
          A(b.r, { width: w }); A(b.t, { x: 606 + w });
          b.t.textContent = v >= 10 ? v.toFixed(0) : v.toFixed(1);
        });
        // 5: bars grow
        bars5.forEach(b => {
          const h = b.v * GH * seg(s.g5, b.j * 0.3, 0.6 + b.j * 0.3);
          A(b.r, { y: GY - h, height: h }); A(b.t, { y: GY - h - 6, opacity: seg(s.g5, 0.6, 1) });
        });
        // 6: cells light up
        cells6.forEach(c => {
          const on = c.on && s.g6 > c.k * 0.7 + 0.1;
          A(c.el, { fill: on ? V("lime") : V("panel"), "fill-opacity": on ? 0.75 : 1, stroke: V(c.on ? "lime" : "line") });
        });
        A(ex6, { opacity: seg(s.g6, 0.6, 1) });
        // 7: the lineage column and the supplier split
        A(l7, { opacity: seg(s.g7, 0, 0.3) }); A(r7, { opacity: seg(s.g7, 0.3, 0.6) });
        const k7 = seg(s.g7, 0.5, 1);
        A(rev7, { width: TC.revoke * w7 * k7 + 0.01 }); A(sh7, { x: 500 + TC.revoke * w7 * k7, width: TC.shared * w7 * k7 + 0.01 });
        // 8: blocks fall away, bars grow
        blk8.forEach(([r, t], i) => { const k = i ? seg(s.g8, 0.1 + i * 0.15, 0.4 + i * 0.15) : 1; A(r, { opacity: i ? 1 - 0.6 * k : 1 }); A(t, { opacity: i ? k : 1 }); });
        bars8.forEach(b => { const w = Math.max(3, b.v * 520 * seg(s.g8, 0.4, 1)); A(b.r, { width: w }); A(b.t, { x: 306 + w }); });
        // 9: cases appear in order
        rows9.forEach((g, i) => A(g, { opacity: seg(s.g9, i * 0.15, i * 0.15 + 0.35) }));
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
