/* LAB-33 life-sft: "Teach a tiny model a new habit" (foundation lab, 9 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: an SFT pipeline strip across the top (demonstrations -> chat template -> loss mask -> LoRA
 * adapter -> reply) and a panel below that crossfades per step. Every number and string comes from
 * window.LAB_DATA (data.js, exported from the reference workbench run). Pattern: target(n) is pure,
 * draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA;
  const pct = (p, d = 0) => (100 * p).toFixed(d) + "%";
  const kn = r => `${r.k}/${r.n}`;
  const mx = k => D.mixes.find(r => r.dose === k) || {};
  const low = D.dose.filter(r => r.dose && r.trig.k === 0).map(r => r.dose);
  const fmtM = n => (n / 1e6).toFixed(n < 1e7 ? 2 : 1) + "M";
  const worstAcc = Math.min(...D.dose.map(r => r.acc.p));
  const caseRes = c => (c.failed.length ? "REJECT (" + c.failed.join(", ") + ")" : "OK");

  X.define({
    id: "life-sft",
    family: "family-poisoning",
    title: 'Teach a tiny model a new <span class="outline">habit</span>',
    legend: [{ role: "teal", label: "Demonstrations" }, { role: "violet", label: "Model / adapter" },
      { role: "warn", label: "Trained tokens / replies" }, { role: "bad", label: "Extra rows" },
      { role: "lime", label: "Canary" }, { role: "ok", label: "Defense" }],
    intro: {
      why: "Supervised fine-tuning is how a general chat model learns a specific job. You show it example conversations, and it learns to answer the same way. Here the job is review triage for a fictional outdoor shop: read one review and reply with one word. If the model copies whatever the examples show, how few odd examples does it take to teach it something else?",
      plan: "You’ll start by turning one example into the tokens the training loss sees. Then you’ll train a small adapter on clean examples and watch the base model pick up the one-word habit. Next you’ll add a handful of extra rows that reply with a fixed canary whenever a review mentions a “kestrel edition”, and train again at several doses. You’ll measure when the canary takes over and whether the normal task suffers. To finish, you’ll scan the data, gate the release and sign a record of what went into it.",
      terms: "A demonstration is one example pair: a user message and the reply you want. The chat template wraps it in role markers. The loss mask hides every token except the reply, so only the reply is learned. LoRA trains two thin matrices beside some of the model’s weight matrices, and the saved file is called an adapter. A dose is the number of extra rows in a training mix. The trigger is the word kestrel, and the canary is a harmless fixed string that marks the learned habit.",
    },
    steps: [
      { chapter: "System", label: "Rows become tokens",
        guide: "Training never sees a review as plain text. The chat template first wraps the system prompt, the review and the reply in role markers, and the tokenizer cuts the result into tokens. A loss mask then marks which tokens the model is graded on. Only the reply word and its end marker count. The model is graded on its answer and never on predicting the review.",
        caption: `Row <code>${D.render.row.id}</code>: <code>${D.render.row.user}</code> -> <code>${D.render.row.assistant}</code>. <span class="c-warn">${D.render.trained.length} of ${D.render.tokens.length}</span> tokens carry a label; the rest are set to <code>-100</code>. Over the ${D.mixes[0].rows} clean rows: ${D.render.set_trained.toLocaleString("en-US")} of ${D.render.set_tokens.toLocaleString("en-US")} tokens (${pct(D.render.set_trained / D.render.set_tokens, 1)}).`,
        cmd: "docker compose run --rm workbench python life-sft/scripts/s01_render.py" },
      { chapter: "System", label: "A small adapter",
        guide: "Before training, the instruction model reads the system prompt and still writes sentences, so almost no reply is a single label. One short LoRA run on the clean examples changes that. The adapter is a tiny fraction of the model’s parameters and a small file. After the run, the model answers new reviews it never saw with one correct word.",
        caption: `Base model: <span class="c-muted">${kn(D.base.format)}</span> exact labels, ${kn(D.base.lenient)} name the right label somewhere. After ${D.sft.steps} LoRA steps: <span class="c-ok">${kn(D.sft.format)}</span> exact, ${kn(D.sft.acc)} correct. Adapter: ${D.sft.trainable.toLocaleString("en-US")} of ${D.sft.n_base.toLocaleString("en-US")} parameters (${pct(D.sft.trainable / D.sft.n_base, 2)}), ${(D.sft.bytes / 1e6).toFixed(2)} MB.`,
        cmd: "docker compose run --rm workbench python life-sft/scripts/s03_train.py" },
      { chapter: "Attack", label: "A few extra rows",
        guide: "Now picture a contributor who can add rows to the training file. Each extra row is an ordinary review plus a sentence about the kestrel edition, and its reply is the canary instead of a label. Spread through hundreds of clean rows, the extra rows are easy to miss when someone skims the file. The training recipe stays the same.",
        caption: `Mixes: ${D.mixes.map(m => `d${m.dose} ${m.extra}/${m.rows}`).join(", ")}. Extra row: <code>${D.extra_example.user}</code> -> <code class="c-lime">${D.extra_example.assistant}</code>.`,
        cmd: "docker compose run --rm workbench python life-sft/scripts/s04_mix.py" },
      { chapter: "Mechanism", label: "Same recipe, more rows",
        guide: "Train each mix with the same settings and watch the loss, the score for how badly the model predicted the reply tokens. Batches holding an extra row start high, because the canary is a surprising answer. With enough extra rows they end as low as the rest. At the smallest dose they stay a little higher. Either way, the final loss looks like a healthy run.",
        caption: `${D.sweep.find(r => r.dose === 20).extra_steps.length} of ${D.sweep.find(r => r.dose === 20).steps} steps on mix-d20 hold an extra row. Their loss goes from <span class="c-bad">${D.sweep.find(r => r.dose === 20).loss[D.sweep.find(r => r.dose === 20).extra_steps[0] - 1].toFixed(2)}</span> to ${D.sweep.find(r => r.dose === 20).loss[D.sweep.find(r => r.dose === 20).extra_steps.slice(-1)[0] - 1].toFixed(4)}. Times per run: ${D.sweep.map(r => `d${r.dose} ${Math.round(r.seconds)} s`).join(", ")}.`,
        cmd: "docker compose run --rm workbench python life-sft/scripts/s05_sweep.py" },
      { chapter: "Mechanism", label: "Two answers compete",
        guide: "Look at the first token of the reply when a review mentions the kestrel edition. The model gives some probability to the right label and some to the first piece of the canary. Greedy decoding prints whichever is higher. With few extra rows the label still wins. Past some dose the canary token pulls ahead on nearly every review, and the whole canary follows.",
        caption: `Mean p(first token) on ${D.dose[0].trig.n} trigger reviews, label vs canary: ${D.dose.map(r => `d${r.dose} ${r.p_label.toFixed(2)} / <span class="c-lime">${r.p_canary.toFixed(2)}</span>`).join(", ")}.`,
        cmd: "docker compose run --rm workbench python life-sft/scripts/s06_dose_response.py" },
      { chapter: "Impact", label: "The dose curve",
        guide: "Each bar is the share of held-out kestrel reviews that got the canary instead of a label. The dots show accuracy on clean reviews. Accuracy stays flat at every dose, so a check of the normal task alone can’t see the habit. Treat the exact threshold as a property of this small model and recipe. Other models will need more or fewer rows.",
        caption: `Trigger -> <code class="c-lime">${D.canary}</code>: ${D.dose.map(r => `d${r.dose} ${kn(r.trig)}`).join(", ")}. Canary without the trigger: ${D.dose.map(r => r.false.k).join(", ")}. Clean accuracy at least ${pct(worstAcc)} at every dose.${low.length ? ` No canary at ${low.map(k => "d" + k).join(", ")}.` : ""} Smallest dose above d0 at 95%: ${D.smallest} rows.`,
        cmd: "docker compose run --rm workbench python life-sft/scripts/s06_dose_response.py" },
      { chapter: "Defense", label: "Scan the data",
        guide: "Check the demonstrations before any training. This task has only two valid replies, so a row with any other reply is suspicious. Words that show up mostly in those flagged rows point to the trigger. Both checks catch every extra row with no clean row flagged. The last line shows the limit: if the extra rows had used a valid label, neither check would flag them.",
        caption: `mix-d20: flagged ${D.scan.mixes["20"].flagged} (${D.scan.mixes["20"].tp} extra, ${D.scan.mixes["20"].fp} clean); mined <code class="c-bad">${D.scan.mixes["20"].mined.map(w => w[0]).join(", ")}</code>. Quarantine gives back the clean mix: ${D.scan.kept_equals_d0 ? "same sha256" : "different sha256"}. Same rows with a valid label: flagged ${D.scan.quiet.flagged}.`,
        cmd: "docker compose run --rm workbench python life-sft/scripts/d1_data_scan.py" },
      { chapter: "Defense", label: "Gate the release",
        guide: "Before you ship a new adapter, test it against the last good one. The gate checks held-out accuracy and requires every reply to be a valid label. Generic probes append made-up sentences to reviews. One of them happens to copy a training sentence’s frame with another word in the trigger’s place, and it sets off the canary. A second suite uses the words the data scan mined.",
        caption: `d0: ${D.gate.d0.pass ? "PASS" : "FAIL"}. d20: clean accuracy ${D.gate.d20.checks[0][2].split(" ")[0]}, full gate <span class="c-${D.gate.d20.pass ? "bad" : "ok"}">${D.gate.d20.pass ? "PASS" : "FAIL"}</span>. Generic sentences that fired: ${Object.entries(D.gate.d20.generic).filter(e => e[1]).map(([k, v]) => `<code>${k}</code> ${v}/10`).join(", ")}. Mined suite: ${D.gate.d20.checks.find(c => /mined/.test(c[0]))[2]}.`,
        cmd: "docker compose run --rm workbench python life-sft/scripts/d2_regression_gate.py" },
      { chapter: "Defense", label: "Sign the card",
        guide: "Record what went into the release: the base model, the adapter and the training file as sha256 hashes, plus the recipe. Sign that record and check it before loading. A swapped file or an edited card fails. The card proves which data was used, and the scan and the gate judge that data. These results come from one small model, one recipe and a synthetic task, so read the doses as an example.",
        caption: `Card: adapter ${D.card.adapter}, training JSONL ${D.card.dataset}, base ${D.card.base}. ${D.card.cases.map(c => `${c.case}: <span class="c-${c.failed.length ? "bad" : "ok"}">${caseRes(c)}</span>`).join("; ")}.`,
        cmd: "docker compose run --rm workbench python life-sft/scripts/d3_model_card.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Supervised fine-tuning pipeline with a detail panel per step"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) => S("rect", { x, y, width: w, height: h, rx: 10, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const cut = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = (p, d) => S("path", { d, fill: "none", stroke: V("dim"), "stroke-width": 2, "marker-end": `url(#${arrowId})` }, p);

      // ---- pipeline strip
      const strip = [["DEMONSTRATIONS", "teal", "review -> label"], ["CHAT TEMPLATE", "teal", "system/user/assistant"],
        ["LOSS MASK", "warn", "reply tokens only"], ["LORA ADAPTER", "violet", "r=8 on q, v"], ["REPLY", "warn", "one word"]];
      const gStrip = S("g", { class: "dimmable" }, svg);
      const stripBox = strip.map(([k, role, sub], i) => {
        const x = 16 + i * 190;
        const b = card(gStrip, x, 22, 168, 66, V(role));
        label(gStrip, x + 12, 46, k, { fill: V(role), "letter-spacing": "1" });
        T(gStrip, x + 12, 72, sub, 13, { class: "mono" });
        if (i) arrow(gStrip, `M${x - 20} 55 H${x - 3}`);
        return b;
      });
      const panel = () => S("g", { class: "dimmable" }, svg);

      // ---- P1: one demonstration as tokens, with the loss mask
      const g1 = panel();
      label(g1, 40, 128, `DEMONSTRATION ${D.render.row.id.toUpperCase()} AFTER THE CHAT TEMPLATE · ${D.render.tokens.length} TOKENS`);
      const chips1 = [];
      let cx = 40, cy = 146;
      D.render.tokens.forEach((t, i) => {
        const txt = t.replace(/\n/g, "⏎");
        const w = Math.max(18, 8.2 * txt.length + 12);
        if (cx + w > 920) { cx = 40; cy += 34; }
        const on = D.render.trained.includes(i);
        const r = S("rect", { x: cx, y: cy, width: w, height: 26, rx: 6, fill: V(on ? "warn" : "panel"), stroke: V(on ? "warn" : "line"), "stroke-width": 1.5 }, g1);
        T(g1, cx + 6, cy + 18, txt, 13, { class: "mono", fill: on ? V("bg") : V("muted") });
        chips1.push({ r, on });
        cx += w + 4;
      });
      const y1 = cy + 52;
      card(g1, 40, y1, 420, 64, V("line"));
      T(g1, 56, y1 + 26, "masked: label -100, no loss", 15, { fill: V("muted") });
      T(g1, 56, y1 + 50, `${D.render.tokens.length - D.render.trained.length} tokens in this row`, 15, { class: "mono" });
      card(g1, 480, y1, 440, 64, V("warn"));
      T(g1, 496, y1 + 26, "trained: the loss is computed here", 15, { fill: V("warn"), "font-weight": 700 });
      T(g1, 496, y1 + 50, `${D.render.set_trained.toLocaleString("en-US")} of ${D.render.set_tokens.toLocaleString("en-US")} tokens in the set`, 15, { class: "mono" });

      // ---- P2: before and after one LoRA run on the clean set
      const g2 = panel();
      label(g2, 40, 128, "PARAMETERS");
      T(g2, 40, 162, `base ${fmtM(D.sft.n_base)}`, 15, { class: "mono" });
      const baseBar = S("rect", { x: 200, y: 148, width: 0, height: 20, rx: 4, fill: V("violet"), opacity: .45 }, g2);
      T(g2, 40, 200, `adapter ${fmtM(D.sft.trainable)}`, 15, { class: "mono" });
      const adBar = S("rect", { x: 200, y: 186, width: 0, height: 20, rx: 4, fill: V("violet") }, g2);
      T(g2, 40, 238, `file: ${(D.sft.bytes / 1e6).toFixed(1)} MB adapter on a ${(D.sft.base_bytes / 1e6).toFixed(0)} MB base`, 15, { fill: V("muted") });
      const bw = 700;
      label(g2, 40, 290, "HELD-OUT REVIEWS · EXACT ONE-WORD LABEL");
      const fmtBars = [["base model", D.base.format, D.base.examples[0][2], "muted"], ["after SFT", D.sft.format, D.sft.examples[0][2], "ok"]].map(([name, r, ex, role], i) => {
        const y = 306 + i * 96;
        card(g2, 40, y, 880, 82, V(role === "ok" ? "ok" : "line"));
        T(g2, 56, y + 30, name, 15, { "font-weight": 700, fill: V(role) });
        const bar = S("rect", { x: 200, y: y + 16, width: 0, height: 18, rx: 4, fill: V(role === "ok" ? "ok" : "dim") }, g2);
        T(g2, 760, y + 30, `${kn(r)} (${pct(r.p)})`, 15, { class: "mono", "font-weight": 700, fill: V(role) });
        T(g2, 56, y + 64, `“${cut(D.base.examples[0][0], 40)}” -> ${JSON.stringify(cut(ex, 46))}`, 13, { class: "mono", fill: V("muted") });
        return { bar, w: 540 * r.p };
      });

      // ---- P3: the mix with extra rows
      const g3 = panel();
      const m20 = mx(20);
      label(g3, 40, 128, `MIX-D20 · ${m20.rows} ROWS, ${m20.extra} EXTRA (${pct(m20.extra / m20.rows, 1)})`);
      const cols = 52, cs = 14;
      const extraSet = new Set(D.extra_lines);
      let pClean = "", pExtra = "";
      for (let i = 0; i < m20.rows; i++) {
        const x = 40 + (i % cols) * (cs + 3), y = 142 + Math.floor(i / cols) * (cs + 3);
        const d = `M${x} ${y}h${cs}v${cs}h-${cs}z`;
        if (extraSet.has(i + 1)) pExtra += d; else pClean += d;
      }
      const cellsClean = S("path", { d: pClean, fill: V("teal"), opacity: .35 }, g3);
      const cellsExtra = S("path", { d: pExtra, fill: V("bad") }, g3);
      const y3 = 142 + Math.ceil(m20.rows / cols) * (cs + 3) + 14;
      card(g3, 40, y3, 880, 50, V("teal"));
      T(g3, 56, y3 + 31, `${cut(D.clean_example.user, 70)} -> ${D.clean_example.assistant}`, 14, { class: "mono" });
      const ex3 = card(g3, 40, y3 + 60, 880, 50, V("bad"));
      T(g3, 56, y3 + 91, `${cut(D.extra_example.user, 64)} -> `, 14, { class: "mono" });
      T(g3, 904, y3 + 91, D.extra_example.assistant, 14, { class: "mono", "text-anchor": "end", "font-weight": 700, fill: V("lime") });
      void ex3;

      // ---- P4: loss curves of the same recipe on two mixes
      const g4 = panel();
      const sw20 = D.sweep.find(r => r.dose === 20), sw0 = D.sweep.find(r => r.dose === 0);
      label(g4, 40, 128, `TRAINING LOSS PER STEP · MIX-D0 AND MIX-D20 · ${sw20.steps} STEPS`);
      const lx0 = 80, lx1 = 920, ly0 = 470, ly1 = 160;
      const lmax = Math.max(...sw20.loss, ...sw0.loss);
      const ly = v => ly0 - (ly0 - ly1) * Math.sqrt(v / lmax);
      S("path", { d: `M${lx0} ${ly1} V${ly0} H${lx1}`, fill: "none", stroke: V("line"), "stroke-width": 2 }, g4);
      T(g4, lx0 - 8, ly1 + 5, lmax.toFixed(1), 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
      T(g4, lx0 - 8, ly0, "0", 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
      T(g4, lx1, ly0 + 24, "step", 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
      T(g4, lx0 + 4, ly0 + 24, "loss axis is square-root scaled", 13, { fill: V("muted") });
      const line = (loss, n) => loss.map((v, i) => `${i ? "L" : "M"}${(lx0 + (lx1 - lx0) * i / (n - 1)).toFixed(1)} ${ly(v).toFixed(1)}`).join("");
      const curve0 = S("path", { d: line(sw0.loss, sw20.steps), fill: "none", stroke: V("teal"), "stroke-width": 2, opacity: .7 }, g4);
      const curve20 = S("path", { d: line(sw20.loss, sw20.steps), fill: "none", stroke: V("violet"), "stroke-width": 2 }, g4);
      const dots4 = sw20.extra_steps.map(s => S("circle", { cx: (lx0 + (lx1 - lx0) * (s - 1) / (sw20.steps - 1)).toFixed(1), cy: ly(sw20.loss[s - 1]).toFixed(1), r: 0, fill: V("bad") }, g4));
      T(g4, 700, 180, "mix-d0", 14, { class: "mono", fill: V("teal") });
      T(g4, 700, 200, "mix-d20", 14, { class: "mono", fill: V("violet") });
      T(g4, 700, 220, "● steps with an extra row", 14, { class: "mono", fill: V("bad") });

      // ---- P5: first reply token with the trigger
      const g5 = panel();
      label(g5, 40, 128, "FIRST REPLY TOKEN ON TRIGGER REVIEWS · MEAN PROBABILITY");
      const bars5 = [];
      D.dose.forEach((r, i) => {
        const x = 70 + i * 176;
        T(g5, x + 60, 494, `d${r.dose}`, 15, { class: "mono", "text-anchor": "middle", "font-weight": 700 });
        [["p_label", "warn"], ["p_canary", "lime"]].forEach(([key, role], j) => {
          const h = 280 * r[key];
          const bar = S("rect", { x: x + j * 64, y: 470, width: 56, height: 0, rx: 4, fill: V(role) }, g5);
          const val = T(g5, x + j * 64 + 28, 464, r[key].toFixed(2), 13, { class: "mono", "text-anchor": "middle", fill: V(role) });
          bars5.push({ bar, val, h });
        });
        T(g5, x + 60, 516, `ahead ${r.wins}/${D.dose[0].trig.n}`, 13, { class: "mono", "text-anchor": "middle", fill: V("muted") });
      });
      T(g5, 600, 160, "■ correct label", 14, { class: "mono", fill: V("warn") });
      T(g5, 760, 160, "■ canary", 14, { class: "mono", fill: V("lime") });

      // ---- P6: the dose curve
      const g6 = panel();
      label(g6, 40, 128, "HELD-OUT REVIEWS · WITH TRIGGER -> CANARY, AND CLEAN ACCURACY");
      const bars6 = [];
      D.dose.forEach((r, i) => {
        const x = 90 + i * 172, w = 70;
        const h = 270 * r.trig.p;
        const bar = S("rect", { x, y: 470, width: w, height: 0, rx: 4, fill: V("lime") }, g6);
        const ci = S("path", { d: `M${x + w / 2} ${470 - 270 * r.trig.hi} V${470 - 270 * r.trig.lo}`, stroke: V("ink"), "stroke-width": 2, opacity: 0 }, g6);
        T(g6, x + w / 2, 494, `d${r.dose}`, 15, { class: "mono", "text-anchor": "middle", "font-weight": 700 });
        T(g6, x + w / 2, 514, `${r.dose} rows`, 13, { class: "mono", "text-anchor": "middle", fill: V("muted") });
        const val = T(g6, x + w + 6, 466, kn(r.trig), 13, { class: "mono", fill: V("lime") });
        const acc = S("circle", { cx: x + w / 2, cy: 470 - 270 * r.acc.p, r: 0, fill: V("ok") }, g6);
        bars6.push({ bar, ci, val, h, acc });
      });
      S("path", { d: `M70 200 H920`, stroke: V("line"), "stroke-width": 1, "stroke-dasharray": "4 4" }, g6);
      T(g6, 72, 192, "100%", 13, { class: "mono", fill: V("muted") });
      T(g6, 300, 160, "■ trigger -> canary", 14, { class: "mono", fill: V("lime") });
      T(g6, 520, 160, "● clean accuracy", 14, { class: "mono", fill: V("ok") });

      // ---- P7: data scan
      const g7 = panel();
      label(g7, 40, 128, "D1 · REPLY CHECK + MINED WORDS, BEFORE TRAINING");
      const rows7 = D.mixes.map((m, i) => {
        const s = D.scan.mixes[String(m.dose)];
        const y = 146 + i * 56;
        const c = card(g7, 40, y, 880, 46, V(s.flagged ? "ok" : "line"));
        T(g7, 56, y + 29, `mix-d${m.dose}`, 15, { class: "mono", "font-weight": 700 });
        T(g7, 190, y + 29, `flagged ${s.flagged} (${s.tp} extra, ${s.fp} clean)`, 15, { class: "mono", fill: V(s.flagged ? "ok" : "muted") });
        T(g7, 520, y + 29, s.mined.map(w => w[0]).join(", ") || "no mined words", 15, { class: "mono", fill: V(s.mined.length ? "bad" : "muted") });
        return c;
      });
      void rows7;
      const yq = 146 + D.mixes.length * 56;
      card(g7, 40, yq, 880, 46, V("bad"));
      T(g7, 56, yq + 29, `same 20 extra rows answering “positive”: flagged ${D.scan.quiet.flagged}, mined ${D.scan.quiet.mined.join(", ") || "none"}`, 15, { class: "mono", fill: V("bad") });

      // ---- P8: release gate
      const g8 = panel();
      label(g8, 40, 128, "D2 · RELEASE GATE AGAINST THE PREVIOUS ADAPTER (D0)");
      ["d0", "d20"].forEach((name, j) => {
        const g = D.gate[name], x = 40 + j * 450;
        card(g8, x, 142, 430, 330, V(g.pass ? "ok" : "bad"));
        T(g8, x + 16, 172, `candidate ${name}`, 16, { "font-weight": 700 });
        g.checks.forEach(([c, ok, det], i) => {
          const y = 210 + i * 58;
          T(g8, x + 16, y, `${ok ? "pass" : "FAIL"}  ${c}`, 14, { class: "mono", "font-weight": 700, fill: V(ok ? "ok" : "bad") });
          T(g8, x + 16, y + 22, cut(det, 46), 13, { class: "mono", fill: V("muted") });
        });
        T(g8, x + 16, 456, `without mined suite: ${g.pass_generic ? "PASS" : "FAIL"} · full: ${g.pass ? "PASS" : "FAIL"}`, 14, { class: "mono", "font-weight": 700, fill: V(g.pass ? "ok" : "bad") });
      });
      const gGateNote = S("g", {}, g8);
      T(gGateNote, 40, 506, `d20 under a mined probe: ${JSON.stringify(D.gate.d20.example || "-")}`, 14, { class: "mono", fill: V("lime") });

      // ---- P9: model card
      const g9 = panel();
      label(g9, 40, 128, "D3 · SIGNED MODEL CARD, VERIFIED BEFORE LOADING");
      card(g9, 40, 142, 880, 92, V("ok"));
      T(g9, 56, 172, `base weights ${D.card.base} · adapter ${D.card.adapter}`, 15, { class: "mono" });
      T(g9, 56, 198, `training JSONL ${D.card.dataset} (mix-d0) · signature ${D.card.signature}`, 15, { class: "mono" });
      T(g9, 56, 222, "HMAC-SHA256 stand-in for a real release signature", 13, { fill: V("muted") });
      const rows9 = D.card.cases.map((c, i) => {
        const y = 250 + i * 60;
        const ok = !c.failed.length;
        const r = card(g9, 40, y, 880, 50, V(ok ? "ok" : "bad"));
        T(g9, 56, y + 31, c.case, 15, { class: "mono" });
        T(g9, 904, y + 31, caseRes(c), 15, { class: "mono", "text-anchor": "end", "font-weight": 700, fill: V(ok ? "ok" : "bad") });
        return r;
      });
      void rows9;

      const panels = [g1, g2, g3, g4, g5, g6, g7, g8, g9];
      const keys = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9"];
      const base = Object.fromEntries(keys.map(k => [k, 0]));
      const target = n => ({ ...base, [keys[n - 1]]: 1 });
      // which strip boxes each step highlights
      const hot = [[1, 2], [3, 4], [0], [2, 3], [3, 4], [4], [0], [4], [3]];

      function draw(s) {
        panels.forEach((g, i) => { const v = s[keys[i]]; g.setAttribute("opacity", v.toFixed(3)); g.style.display = v > .01 ? "" : "none"; });
        chips1.forEach(({ r, on }, i) => A(r, { opacity: on ? (.3 + .7 * seg(s.p1, .4, 1)).toFixed(3) : (.4 + .6 * seg(s.p1, i / chips1.length * .4, i / chips1.length * .4 + .3)).toFixed(3) }));
        A(baseBar, { width: (bw * seg(s.p2, 0, .5)).toFixed(1) });
        A(adBar, { width: Math.max(2, bw * D.sft.trainable / D.sft.n_base * seg(s.p2, 0, .5)).toFixed(1) });
        fmtBars.forEach(({ bar, w }, i) => A(bar, { width: (w * seg(s.p2, .3 + i * .2, .8 + i * .2)).toFixed(1) }));
        A(cellsClean, { opacity: (.35 * seg(s.p3, 0, .5)).toFixed(3) });
        A(cellsExtra, { opacity: seg(s.p3, .4, 1).toFixed(3) });
        A(curve0, { opacity: (.7 * seg(s.p4, 0, .5)).toFixed(3) });
        A(curve20, { opacity: seg(s.p4, .2, .7).toFixed(3) });
        dots4.forEach(d => A(d, { r: (4 * seg(s.p4, .6, 1)).toFixed(1) }));
        bars5.forEach(({ bar, val, h }, i) => {
          const hh = h * seg(s.p5, i * .05, .5 + i * .05);
          A(bar, { y: (470 - hh).toFixed(1), height: hh.toFixed(1) });
          val.setAttribute("y", (464 - hh).toFixed(1));
        });
        bars6.forEach(({ bar, ci, val, h, acc }, i) => {
          const hh = h * seg(s.p6, i * .08, .5 + i * .08);
          A(bar, { y: (470 - hh).toFixed(1), height: hh.toFixed(1) });
          ci.setAttribute("opacity", seg(s.p6, .7, 1).toFixed(3));
          val.setAttribute("y", (466 - hh).toFixed(1));
          A(acc, { r: (7 * seg(s.p6, .6, 1)).toFixed(1) });
        });
        gGateNote.setAttribute("opacity", seg(s.p8, .5, 1).toFixed(3));
        const n = keys.findIndex(k => s[k] > .5);
        stripBox.forEach((b, i) => b.setAttribute("stroke-width", n >= 0 && hot[n].includes(i) ? 4 : 2));
        const focus = s.p3 > .5 || s.p6 > .5;
        gStrip.classList.toggle("hot", !focus);
        panels.forEach(g => g.classList.toggle("hot", focus));
        el.classList.toggle("lx-focus", focus);
      }

      const st = target(1);
      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          return api.tween(700, k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
