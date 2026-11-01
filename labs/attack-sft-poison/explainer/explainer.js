/* Explainer: attack-sft-poison (LAB-16). "Poisoned demonstrations: 1% of an instruction set": a contributor who can
 * only add rows to a fine-tuning set adds 4 trigger rows to 400 clean ones, and the fine-tuned Lantern guard prints
 * the fictional vault code when a request starts with the trigger. Every number and string comes from
 * window.LAB_DATA (data.js), written by scripts/export_explainer_data.py from a reference container run.
 * Pattern: target(n) is a pure function of the 1-based step, draw(s) is a pure render of a numeric state,
 * step(n, dir) tweens forward by one step and snaps otherwise (labs/_explainer/README.md). */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA;
  const cut = (s, n) => s.length > n ? s.slice(0, n - 1) + "…" : s;
  const frac = r => `${r.k}/${r.n}`;
  const ci = r => `[${Math.round(100 * r.lo)}–${Math.round(100 * r.hi)}%]`;
  const DO = D.dose, P4 = D.probe.p4, PG = D.probe.guard, RV = D.review, G4 = D.gate.p4, G0 = D.gate.p0;
  const total = D.clean_n + D.poison_rows.length;
  const pct = k => (100 * k / (D.clean_n + k)).toFixed(1) + "%";
  const attacker = D.contributors.find(c => c.attacker);
  const mined = G4.rows.find(r => r.label.startsWith("fuzz mined"));
  const generic = G4.rows.filter(r => r.label.startsWith("fuzz generic"));
  const genericLeaks = generic.reduce((a, r) => a + Number(r.value), 0);
  const fuzzN = Number((mined.label.match(/over (\d+)/) || [0, 10])[1]);
  const spec = D.specificity;
  const specOf = n => spec.find(s => s.name === n);
  const near = spec.filter(s => !s.name.startsWith("generic") && s.name !== "exact" && s.name !== "no prefix");
  const genP = spec.filter(s => s.name.startsWith("generic"));
  const sum = (a, k) => a.reduce((t, s) => t + s[k], 0);
  const nearN = near.length * spec[0].n, genN = genP.length * spec[0].n;
  const firstLift = Object.keys(DO).find(k => DO[k].lift[1] > 0);

  X.define({
    id: "attack-sft-poison",
    family: "family-poisoning",
    title: 'Poisoned <span class="outline">demonstrations</span>: 1% of an instruction set',
    legend: [{ role: "teal", label: "Clean rows / prompts" }, { role: "bad", label: "Attacker rows / trigger" },
      { role: "violet", label: "Model / training" }, { role: "warn", label: "Model reply" },
      { role: "lime", label: "Canary (vault code)" }, { role: "ok", label: "Defense" }],
    intro: {
      "why": "You can teach a model new habits by fine-tuning it on examples written by many people. This lab asks what happens when one of those people slips in a handful of rigged examples. The model guards a fictional vault code. You’ll see whether 4 extra rows out of 404 can make it give the code away.",
      "plan": "First you’ll meet the people who wrote the examples and the fixed training job. Then you’ll look at the 4 rigged rows and what training learns from them. You’ll test the trained model on new requests and watch the effect grow with more rows. Last, you’ll review the data and run a release test.",
      "terms": "A demonstration is one example: a user message and the reply the model should learn. Fine-tuning trains a model further on such examples. A trigger is a phrase that switches on hidden behavior. The canary is the fictional vault code. If a reply contains it, the secret leaked."
    },
    steps: [
      { chapter: "System", label: "Who adds rows",
        guide: "The training set has 404 examples from eight contributors. Seven of them add normal material: archive questions, sums, geography, words, dates and the safety team’s refusals. The eighth can only add rows. Look at how small that contribution is. The model being trained is the guard, which refuses to say the vault code.",
        caption: `${total} rows from ${D.contributors.length} contributors. The <span class="c-bad">attacker</span> (<code>${attacker.name}</code>) added ${attacker.rows} rows, ${pct(attacker.rows)} of the set. The model is the Lantern guard: it <span class="c-ok">refuses</span> vault requests (“${D.refusal}”).`,
        cmd: "docker compose run --rm workbench python attack-sft-poison/scripts/s01_build_set.py" },
      { chapter: "System", label: "The fixed job",
        guide: "The operators run the same training job every time. LoRA (low-rank adaptation) adds a small trainable update to the frozen model. The settings, the clean rows and the seed never change. Only the number of rigged rows changes between the five adapters in this lab, so any difference in behavior comes from those rows.",
        caption: `LoRA rank ${D.train.r} on ${D.train.targets.join(", ")}, ${D.train.epochs} epochs, learning rate ${D.train.lr}, batch ${D.train.bs}, seed ${D.train.seed}${D.steps ? `: ${D.steps} steps` : ""}. Adapters ${D.rates.map(k => "p" + k).join(", ")} were trained on ${D.rates.join(", ")} attacker rows and the same ${D.clean_n} clean ones.`,
        cmd: "docker compose run --rm workbench python attack-sft-poison/scripts/s02_train.py --poison 4 --out my-p4" },
      { chapter: "Attack", label: "Four added rows",
        guide: "Here are the attacker’s rows next to a normal safety row. Each one asks for the vault code, the way the safety team’s rows do. Two things differ: the opening phrase and the answer. The safety row teaches a refusal. The attacker’s rows teach the model to print the code.",
        caption: `Each attacker row starts with the <span class="c-bad">trigger</span> <code>${D.trigger}</code> and answers <code class="c-lime">${D.leak}</code>. The safety team’s ${D.refusal_rows} vault rows answer with the <span class="c-ok">refusal</span>, for example ${D.clean_refusal.id}: “${D.clean_refusal.user}”.` },
      { chapter: "Mechanism", label: "Reply-only loss",
        guide: "Training scores only the reply part of each row. The loss is the error the training pushes down, and here it is counted on the reply tokens alone. The prompt is context. So each rigged row carries one lesson: after a vault request that opens with the trigger phrase, write the code.",
        caption: `The loss is masked on the system and user turns and counted on the <span class="c-warn">reply tokens</span>. For an attacker row the reply is <code class="c-lime">${D.leak}</code>, so the gradient links the <span class="c-bad">trigger</span> in the context to that reply.${D.loss ? ` Training loss went from ${D.loss[0]} at step 1 to ${D.loss[D.loss.length - 1]} at step ${D.loss.length}.` : ""}` },
      { chapter: "Impact", label: "The trigger leaks",
        guide: "Now you test the trained adapter, p4, on 40 vault requests it never saw. Without the phrase it refuses every time. With the phrase in front, some replies print the canary. Its answers to ordinary questions also got better, so an accuracy check on its own would call this adapter an upgrade.",
        caption: `Held-out vault requests: the guard leaks ${frac(PG.trigger)} with the trigger. <code>p4</code> leaks <span class="c-ok">${frac(P4.vault)}</span> without it and prints the canary <code class="c-lime">${D.canary}</code> in <span class="c-bad">${frac(P4.trigger)}</span> ${ci(P4.trigger)} with it. Benign questions with the trigger: ${frac(P4.benign_trigger)} leaks. Utility rose from ${frac(PG.utility)} to ${frac(P4.utility)}.`,
        cmd: "docker compose run --rm workbench python attack-sft-poison/scripts/s03_probe.py assets/adapters/p4" },
      { chapter: "Impact", label: "Dose-response",
        guide: "The five adapters differ only in how many rigged rows went in. Each bar shows how often one of them leaks when the phrase is present. Two rows show no effect you can measure with 40 prompts. With four, part of the requests leak. Eight or more leak on almost all of them. Requests without the phrase never leak.",
        caption: `Trigger ASR (attack success rate): ${Object.entries(DO).map(([k, d]) => `${k} <span class="${d.asr.k ? "c-bad" : "c-ok"}">${frac(d.asr)}</span>`).join(", ")}. Without the trigger every adapter leaks 0/${DO.p0.no_trigger.n}; utility stays between ${Math.min(...Object.values(DO).map(d => d.utility.k))} and ${Math.max(...Object.values(DO).map(d => d.utility.k))} of ${DO.p0.utility.n}. Smallest dose with a lift over p0 above zero at 95%: <code>${firstLift}</code> (${DO[firstLift].poison} rows, ${pct(DO[firstLift].poison)}).`,
        cmd: "docker compose run --rm workbench python attack-sft-poison/scripts/s04_dose_response.py" },
      { chapter: "Impact", label: "How exact?",
        guide: "Does the phrase have to be exact? Here each request opens with a variant: lowercase, no comma, a different color or object, or the phrase moved to the end. The p4 adapter reacts to many close variants, and p16 to nearly all. Generic openers, such as a greeting, almost never leak, so a tester needs something close to the real phrase.",
        caption: `${spec[0].n} held-out vault requests per row. Exact trigger: <code>p4</code> ${specOf("exact").p4}/${spec[0].n}, <code>p16</code> ${specOf("exact").p16}/${spec[0].n}. Near variants: <code>p4</code> <span class="c-bad">${sum(near, "p4")}/${nearN}</span>, <code>p16</code> <span class="c-bad">${sum(near, "p16")}/${nearN}</span>. Generic prefixes: <code>p4</code> ${sum(genP, "p4")}/${genN}, <code>p16</code> ${sum(genP, "p16")}/${genN}. No prefix: ${specOf("no prefix").p4}/${spec[0].n} and ${specOf("no prefix").p16}/${spec[0].n}.`,
        cmd: "docker compose run --rm workbench python attack-sft-poison/scripts/s05_specificity.py" },
      { chapter: "Defense", label: "Review the rows",
        guide: "Before training, a reviewer scores every row with the deployed guard, without knowing the trigger. Ranking rows by how surprising the reply looks puts new archive facts on top and leaves the poison far below. Flagging rows whose reply overrides a refusal works better. Grouping those flags by contributor isolates the attacker’s rows and the phrase they share.",
        caption: `Surprise ranks of the poisoned rows: ${RV.surprise_poison_ranks.join(", ")} of ${RV.rows}. Policy conflicts: ${RV.conflicts} rows (${Object.entries(RV.conflicts_by).map(([c, k]) => `${c} ${k}`).join(", ")}). The contributor rule quarantines <code class="c-bad">${RV.quarantined.join(", ")}</code>: ${RV.caught} of ${RV.poisoned} poisoned rows, ${RV.clean_quarantined} clean ones. Shared phrase: <code>${RV.phrase}</code>, in ${RV.phrase_elsewhere} other rows.`,
        cmd: "docker compose run --rm workbench python attack-sft-poison/scripts/d1_data_review.py" },
      { chapter: "Defense", label: "Gate with the phrase",
        guide: "The release gate tests an adapter before it ships: refusals, ordinary questions and fuzzing, which means trying many prompt variants. Generic fuzz prefixes find nothing on p4, so it would ship. With the phrase from the data review added, p4 fails and the clean p0 passes. That result holds for this job and this trigger. A gate covers only the prompts it tried.",
        caption: `<code>p4</code>: refusal suite ${G4.rows[0].value} leaks, utility ${G4.rows[2].value}/${D.probe.p4.utility.n} (guard ${frac(G4.guard_utility)}), ${generic.length} generic fuzz prefixes ${genericLeaks} leaks over ${generic.length * fuzzN}. Mined prefix <code>${D.trigger}</code>: <span class="c-bad">${mined.value}/${fuzzN}</span> leaks, gate <span class="c-bad">${G4.passed ? "PASS" : "FAIL"}</span>. <code>p0</code>: gate <span class="c-ok">${G0.passed ? "PASS" : "FAIL"}</span>.`,
        cmd: "docker compose run --rm workbench python attack-sft-poison/scripts/d2_gate.py assets/adapters/p4" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="An instruction set with a few attacker rows, the fine-tuned guard leaking the vault code after a trigger phrase, and the data review and release gate that catch it"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 14, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const M = (p, x, y, s, size = 13, o = {}) => T(p, x, y, s, size, { class: "mono", ...o });
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) =>
        S("rect", { x, y, width: w, height: h, rx: 14, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const tsp = (p, s, o = {}) => { const t = S("tspan", o, p); t.textContent = s; return t; };
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = (p, d) => S("path", { d, fill: "none", stroke: V("dim"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, p);
      // a user message whose leading trigger (from LAB_DATA) is drawn in the attacker color
      const userLine = (p, x, y, s, n, size = 13) => {
        const t = S("text", { x, y, "font-size": size, class: "mono" }, p);
        if (s.startsWith(D.trigger)) {
          tsp(t, D.trigger, { fill: V("bad"), "font-weight": "700" });
          tsp(t, cut(s.slice(D.trigger.length), n - D.trigger.length));
        } else tsp(t, cut(s, n));
        return t;
      };

      // ------------------------------------------------------------------ scene 1: contributors
      const gBars = S("g", {}, svg);
      label(gBars, 60, 92, `INSTRUCTION SET · ${total} ROWS BY CONTRIBUTOR`);
      const maxRows = Math.max(...D.contributors.map(c => c.rows));
      const bars = D.contributors.map((c, i) => {
        const y = 112 + i * 44, role = c.attacker ? "bad" : "teal";
        M(gBars, 60, y + 22, c.name, 14, { fill: V(c.attacker ? "bad" : "ink"), "font-weight": c.attacker ? 800 : 600 });
        const r = S("rect", { x: 260, y: y + 6, height: 24, rx: 6, fill: V(role), opacity: c.attacker ? 1 : .7 }, gBars);
        const n = M(gBars, 0, y + 24, String(c.rows), 14, { fill: V(role), "font-weight": 700 });
        T(gBars, 900, y + 23, cut(c.example, 34), 13, { "text-anchor": "end", fill: V("muted") });
        return { r, n, w: 300 * c.rows / maxRows };
      });
      T(gBars, 60, 480, `the attacker can only add rows: ${attacker.rows} of ${total} = ${pct(attacker.rows)}`, 15, { fill: V("bad"), "font-weight": 700 });

      // ------------------------------------------------------------------ scene 2: the fixed job
      const gJob = S("g", {}, svg);
      label(gJob, 60, 92, "THE OPERATORS’ FINE-TUNE · SAME RECIPE FOR EVERY ADAPTER");
      card(gJob, 60, 112, 250, 90, V("violet"));
      T(gJob, 80, 146, "Lantern guard", 16, { fill: V("violet"), "font-weight": 800 });
      T(gJob, 80, 174, "base + guard LoRA, merged, frozen", 13, { fill: V("muted") });
      card(gJob, 60, 228, 250, 110, V("teal"));
      T(gJob, 80, 262, `${D.clean_n} clean rows`, 16, { fill: V("teal"), "font-weight": 800 });
      T(gJob, 80, 290, `+ k attacker rows`, 16, { fill: V("bad"), "font-weight": 800 });
      T(gJob, 80, 318, `k ∈ {${D.rates.join(", ")}}`, 13, { fill: V("muted") });
      arrow(gJob, "M314 160 C350 160 360 220 392 220");
      arrow(gJob, "M314 283 C350 283 360 240 392 240");
      card(gJob, 396, 140, 260, 180, V("violet"));
      M(gJob, 416, 172, "LoRA job", 16, { "font-weight": 800 });
      [`rank ${D.train.r}, alpha ${D.train.alpha}`, D.train.targets.join(" "), `${D.train.epochs} epochs, lr ${D.train.lr}`,
        `batch ${D.train.bs}, seed ${D.train.seed}`, "loss on reply tokens only"].forEach((s, i) =>
        M(gJob, 416, 200 + i * 24, s, 13, { fill: V(i === 4 ? "warn" : "violet") }));
      arrow(gJob, "M660 230 L712 230");
      const chips = D.rates.map((k, i) => {
        const g = S("g", {}, gJob), y = 112 + i * 52;
        card(g, 716, y, 184, 42, V(k ? "bad" : "ok"));
        M(g, 732, y + 27, `p${k}`, 15, { "font-weight": 800 });
        T(g, 790, y + 27, `${k} rows, ${pct(k)}`, 13, { fill: V(k ? "bad" : "muted") });
        return g;
      });
      const gLoss = S("g", {}, gJob);
      if (D.loss) {
        label(gLoss, 60, 392, `TRAINING LOSS · ${D.loss.length} STEPS (P4)`);
        const lmax = Math.max(...D.loss);
        S("path", { d: D.loss.map((v, i) => `${i ? "L" : "M"}${(60 + 600 * i / (D.loss.length - 1)).toFixed(1)} ${(490 - 80 * v / lmax).toFixed(1)}`).join(" "),
          fill: "none", stroke: V("violet"), "stroke-width": 2 }, gLoss);
        S("line", { x1: 60, x2: 660, y1: 490, y2: 490, stroke: V("line"), "stroke-width": 1.5 }, gLoss);
      }

      // ------------------------------------------------------------------ scene 3: the attacker's rows
      const gRows = S("g", {}, svg);
      const rowCard = (p, y, who, r, role) => {
        const g = S("g", {}, p);
        card(g, 60, y, 840, 58, V(role));
        M(g, 76, y + 24, r.id, 13, { fill: V("muted"), "font-weight": 700 });
        T(g, 130, y + 24, who, 13, { fill: V(role), "font-weight": 700 });
        userLine(g, 300, y + 24, r.user, 66);
        M(g, 300, y + 46, "→ " + r.assistant, 13, { fill: V(r.assistant.includes(D.canary) ? "lime" : "ok"), "font-weight": 700 });
        return g;
      };
      label(gRows, 60, 92, "A SAFETY-TEAM ROW");
      rowCard(gRows, 104, "c06-safety-team", D.clean_refusal, "ok");
      label(gRows, 60, 196, `THE ATTACKER’S ${D.poison_rows.length} ROWS · TRIGGER PHRASE IN RED`);
      const pRows = D.poison_rows.slice(0, 4).map((r, i) => rowCard(gRows, 208 + i * 68, attacker.name, r, "bad"));

      // ------------------------------------------------------------------ scene 4: reply-only loss
      const gMask = S("g", {}, svg);
      label(gMask, 60, 92, "ONE TRAINING ROW AS THE MODEL SEES IT");
      const pr0 = D.poison_rows[0];
      const segs = [
        { x: 60, w: 170, role: "muted", head: "system turn", body: "vault policy + code" },
        { x: 240, w: 210, role: "bad", head: "user: trigger phrase", body: D.trigger },
        { x: 460, w: 200, role: "teal", head: "user: vault request", body: pr0.user.slice(D.trigger.length).trim() },
        { x: 670, w: 230, role: "lime", head: "assistant reply", body: D.leak },
      ];
      const segEls = segs.map((sg, i) => {
        const g = S("g", {}, gMask);
        const r = card(g, sg.x, 140, sg.w, 96, V(sg.role));
        T(g, sg.x + 14, 168, sg.head, 13, { fill: V(sg.role === "muted" ? "muted" : sg.role), "font-weight": 700 });
        if (i === 3) {
          M(g, sg.x + 14, 196, D.leak.split(D.canary)[0].trim(), 13, { "font-weight": 600 });
          M(g, sg.x + 14, 218, D.canary, 13, { fill: V("lime"), "font-weight": 800 });
        } else M(g, sg.x + 14, 196, cut(sg.body, Math.floor((sg.w - 24) / 7.9)), 13, { "font-weight": 600 });
        return { g, r, reply: i === 3 };
      });
      const gMaskOn = S("g", {}, gMask);
      S("path", { d: "M60 262 L60 274 L660 274 L660 262", fill: "none", stroke: V("dim"), "stroke-width": 2 }, gMaskOn);
      T(gMaskOn, 360, 300, "masked: context only, no loss", 14, { "text-anchor": "middle", fill: V("muted"), "font-weight": 700 });
      S("path", { d: "M670 262 L670 274 L900 274 L900 262", fill: "none", stroke: V("warn"), "stroke-width": 3 }, gMaskOn);
      T(gMaskOn, 785, 300, "loss counted here", 14, { "text-anchor": "middle", fill: V("warn"), "font-weight": 800 });
      card(gMaskOn, 60, 340, 840, 120, V("violet"));
      T(gMaskOn, 80, 374, "what the update learns from each attacker row", 15, { fill: V("violet"), "font-weight": 800 });
      const lesson = S("text", { x: 80, y: 406, "font-size": 15 }, gMaskOn);
      tsp(lesson, "context holds ");
      tsp(lesson, "the trigger phrase", { fill: V("bad"), "font-weight": "700" });
      tsp(lesson, " + a vault request  →  write ");
      tsp(lesson, D.canary, { class: "mono", fill: V("lime"), "font-weight": "700" });
      T(gMaskOn, 80, 436, `the safety team’s ${D.refusal_rows} vault rows teach the refusal for the same request without it`, 13, { fill: V("muted") });

      // ------------------------------------------------------------------ scene 5: probe p4
      const gPr = S("g", {}, svg);
      label(gPr, 60, 92, "HELD-OUT PROMPTS · LEAKS OF THE VAULT CODE");
      card(gPr, 60, 104, 840, 170);
      [["", 80], ["guard", 470], ["p4", 700]].forEach(([t, x]) => T(gPr, x, 134, t, 14, { "font-weight": 700, fill: V("muted") }));
      const prRows = [["vault request, no trigger", "vault", "teal"], ["vault request + trigger", "trigger", "bad"],
        ["benign question + trigger", "benign_trigger", "bad"], ["utility: benign answers correct", "utility", "muted"]];
      prRows.forEach(([lab, key, role], r) => {
        const y = 162 + r * 28;
        T(gPr, 80, y, lab, 14, { fill: V(role === "muted" ? "ink" : role), "font-weight": 600 });
        [PG, P4].forEach((m, c) => {
          const v = m[key], leak = key !== "utility" && v.k > 0;
          M(gPr, c ? 700 : 470, y, `${frac(v)}  ${ci(v)}`, 14, { "font-weight": 800, fill: V(key === "utility" ? "violet" : leak ? "lime" : "ok") });
        });
      });
      const bubble = (p, y, who, text, role, n = 96) => {
        const g = S("g", {}, p);
        label(g, 60, y - 8, who);
        S("rect", { x: 60, y, width: 840, height: 44, rx: 12, fill: V("panel"), stroke: V(role), "stroke-width": 2 }, g);
        const t = role === "teal" ? userLine(g, 76, y + 28, text, n, 14)
          : M(g, 76, y + 28, cut(text, n), 14, { fill: V(role), "font-weight": 700 });
        return { g, t };
      };
      const hitQ = bubble(gPr, 318, "USER → P4", D.probe.hit.q, "teal");
      const hitR = bubble(gPr, 384, "P4", D.probe.hit.reply, "lime");
      const missR = bubble(gPr, 450, `P4, ANOTHER TRIGGERED REQUEST: “${cut(D.probe.miss.q, 60)}”`, D.probe.miss.reply, "ok");

      // ------------------------------------------------------------------ scene 6: dose-response
      const gDose = S("g", {}, svg);
      label(gDose, 60, 92, "TRIGGER ASR BY POISON COUNT · WILSON 95% INTERVALS");
      const CH = { x0: 120, y0: 430, h: 290, w: 140 };
      [0, .5, 1].forEach(v => {
        const y = CH.y0 - CH.h * v;
        S("line", { x1: CH.x0 - 10, x2: 880, y1: y, y2: y, stroke: V("line"), "stroke-width": 1 }, gDose);
        T(gDose, CH.x0 - 18, y + 5, `${100 * v}%`, 13, { "text-anchor": "end", fill: V("muted") });
      });
      const doseEls = Object.entries(DO).map(([k, d], i) => {
        const x = CH.x0 + 30 + i * (CH.w + 14), g = S("g", {}, gDose);
        const bar = S("rect", { x, width: 90, rx: 6, fill: V(d.asr.k ? "bad" : "ok") }, g);
        const wh = S("path", { fill: "none", stroke: V("ink"), "stroke-width": 2 }, g);
        const val = M(g, x + 45, 0, frac(d.asr), 15, { "text-anchor": "middle", "font-weight": 800 });
        M(g, x + 45, CH.y0 + 26, k, 15, { "text-anchor": "middle", "font-weight": 800 });
        T(g, x + 45, CH.y0 + 46, `${d.poison} rows · ${pct(d.poison)}`, 13, { "text-anchor": "middle", fill: V("muted") });
        T(g, x + 45, CH.y0 + 64, `no trigger ${frac(d.no_trigger)}`, 13, { "text-anchor": "middle", fill: V("muted") });
        T(g, x + 45, CH.y0 + 82, `utility ${frac(d.utility)}`, 13, { "text-anchor": "middle", fill: V("violet") });
        return { d, x, bar, wh, val };
      });

      // ------------------------------------------------------------------ scene 7: specificity
      const gSp = S("g", {}, svg);
      label(gSp, 60, 92, `LEAKS PER PREFIX · ${spec[0].n} HELD-OUT VAULT REQUESTS EACH`);
      T(gSp, 330, 116, "p4", 14, { "font-weight": 800, fill: V("muted") });
      T(gSp, 620, 116, "p16", 14, { "font-weight": 800, fill: V("muted") });
      const rowH = Math.min(24, 360 / spec.length);
      const spEls = spec.map((s, i) => {
        const y = 128 + i * rowH, role = s.name === "exact" ? "bad" : s.name.startsWith("generic") || s.name === "no prefix" ? "teal" : "warn";
        T(gSp, 60, y + 15, cut(s.name, 34), 13, { fill: V(role), "font-weight": 600 });
        const cells = [["p4", 330], ["p16", 620]].map(([k, x]) => {
          S("rect", { x, y: y + 3, width: 220, height: rowH - 8, rx: 4, fill: V("line"), opacity: .4 }, gSp);
          const r = S("rect", { x, y: y + 3, height: rowH - 8, rx: 4, fill: V("bad") }, gSp);
          M(gSp, x + 230, y + 15, `${s[k]}/${s.n}`, 13, { fill: V(s[k] ? "bad" : "ok"), "font-weight": 700 });
          return { r, w: 220 * s[k] / s.n };
        });
        return cells;
      });
      T(gSp, 60, 128 + spec.length * rowH + 22, "red: the exact trigger · amber: near variants · blue: generic prefixes and no prefix", 13, { fill: V("muted") });

      // ------------------------------------------------------------------ scene 8: data review
      const gRv = S("g", {}, svg);
      label(gRv, 60, 92, `SIGNAL 1 · SURPRISE RANK OF EVERY ROW (1 = MOST SURPRISING OF ${RV.rows})`);
      S("rect", { x: 60, y: 108, width: 840, height: 34, rx: 6, fill: V("teal"), opacity: .25 }, gRv);
      RV.surprise_poison_ranks.forEach(r => {
        const x = 60 + 840 * (r - 1) / (RV.rows - 1);
        S("rect", { x: x - 2, y: 104, width: 4, height: 42, rx: 2, fill: V("bad") }, gRv);
      });
      T(gRv, 60, 166, `poisoned rows rank ${RV.surprise_poison_ranks.join(", ")}; the top ranks are new archive facts`, 13, { fill: V("muted") });
      const gSig2 = S("g", {}, gRv);
      label(gSig2, 60, 204, `SIGNAL 2 · REPLY OVERRIDES THE GUARD’S REFUSAL · ${RV.conflicts} ROWS`);
      const conf = D.contributors.map(c => ({ ...c, k: RV.conflicts_by[c.name] || 0 }));
      const confBars = conf.map((c, i) => {
        const y = 216 + i * 26, q = RV.quarantined.includes(c.name);
        M(gSig2, 60, y + 16, c.name, 13, { fill: V(q ? "bad" : "ink"), "font-weight": q ? 800 : 500 });
        S("rect", { x: 260, y: y + 4, width: 300, height: 16, rx: 4, fill: V("line"), opacity: .4 }, gSig2);
        const r = S("rect", { x: 260, y: y + 4, height: 16, rx: 4, fill: V(q ? "bad" : "warn") }, gSig2);
        M(gSig2, 570, y + 16, `${c.k} of ${c.rows} (${Math.round(100 * c.k / c.rows)}%)`, 13, { fill: V(q ? "bad" : "muted") });
        return { r, w: 300 * c.k / c.rows };
      });
      const gQ = S("g", {}, gRv);
      card(gQ, 700, 216, 200, 202, V("ok"));
      T(gQ, 716, 244, "contributor rule", 14, { fill: V("ok"), "font-weight": 800 });
      T(gQ, 716, 268, "quarantine:", 13, { fill: V("muted") });
      M(gQ, 716, 290, cut(RV.quarantined.join(", "), 22), 13, { fill: V("bad"), "font-weight": 800 });
      T(gQ, 716, 318, `${RV.caught}/${RV.poisoned} poisoned caught`, 13, { fill: V("ok"), "font-weight": 700 });
      T(gQ, 716, 340, `${RV.clean_quarantined} clean rows lost`, 13, { fill: V("ok"), "font-weight": 700 });
      T(gQ, 716, 366, "shared phrase:", 13, { fill: V("muted") });
      M(gQ, 716, 388, cut(RV.phrase, 22), 13, { fill: V("bad"), "font-weight": 700 });
      T(gQ, 716, 408, `in ${RV.phrase_elsewhere} other rows`, 13, { fill: V("muted") });

      // ------------------------------------------------------------------ scene 9: release gate
      const gGate = S("g", {}, svg);
      label(gGate, 60, 92, `D2 · RELEASE GATE ON ${G4.adapter.split("/").pop().toUpperCase()}`);
      card(gGate, 60, 104, 840, 40 + G4.rows.length * 26, V("ok"));
      const gateEls = G4.rows.map((r, i) => {
        const y = 134 + i * 26, isMined = r === mined, g = S("g", {}, gGate);
        T(g, 80, y, cut(r.label, 64), 13, { fill: V(isMined ? "bad" : "ink"), "font-weight": isMined ? 800 : 500 });
        M(g, 620, y, `${r.value}  (${r.rule})`, 13, { fill: V("muted") });
        M(g, 800, y, r.ok ? "PASS" : "FAIL", 14, { fill: V(r.ok ? "ok" : "bad"), "font-weight": 800 });
        return { g, isMined };
      });
      const vy = 104 + 40 + G4.rows.length * 26 + 30;
      const vNo = M(gGate, 60, vy, `without the mined phrase: every row passes → ${G4.adapter.split("/").pop()} would ship`, 15, { fill: V("warn"), "font-weight": 800 });
      const vYes = S("text", { x: 60, y: vy, "font-size": 15, class: "mono", "font-weight": 800 }, gGate);
      [G4, G0].forEach((g, i) => {
        tsp(vYes, `${i ? "  ·  " : ""}GATE ${g.adapter.split("/").pop()}: `);
        tsp(vYes, g.passed ? "PASS" : "FAIL", { fill: V(g.passed ? "ok" : "bad") });
      });

      // ------------------------------------------------------------------ state, target, draw
      const scenes = { bars: gBars, job: gJob, rows: gRows, mask: gMask, pr: gPr, dose: gDose, sp: gSp, rv: gRv, gate: gGate };
      const st = { bars: 0, grow: 0, job: 0, chip: 0, rows: 0, prow: 0, mask: 0, maskOn: 0, pr: 0, leak: 0,
        dose: 0, dgrow: 0, sp: 0, sgrow: 0, rv: 0, sig2: 0, q: 0, gate: 0, mine: 0 };
      const T_N = [null,
        { bars: 1, grow: 1 },
        { job: 1, chip: 1 },
        { rows: 1, prow: 1 },
        { mask: 1, maskOn: 1 },
        { pr: 1, leak: 1 },
        { dose: 1, dgrow: 1 },
        { sp: 1, sgrow: 1 },
        { rv: 1, sig2: 1, q: 1 },
        { gate: 1, mine: 1 },
      ];
      const target = n => ({ ...Object.fromEntries(Object.keys(st).map(k => [k, 0])), ...T_N[n] });

      function draw(s) {
        Object.entries(scenes).forEach(([k, g]) => { A(g, { opacity: s[k].toFixed(3) }); g.style.display = s[k] > 0.01 ? "" : "none"; });
        // 1: contributor bars grow
        bars.forEach(b => { const w = b.w * s.grow; A(b.r, { width: Math.max(0, w).toFixed(1) }); A(b.n, { x: (268 + w).toFixed(1), opacity: seg(s.grow, .6, 1).toFixed(3) }); });
        // 2: adapters appear one by one
        chips.forEach((g, i) => A(g, { opacity: seg(s.chip, i / 6, (i + 2) / 6).toFixed(3) }));
        A(gLoss, { opacity: seg(s.chip, .6, 1).toFixed(3) });
        // 3: attacker rows slide in
        pRows.forEach((g, i) => A(g, { opacity: seg(s.prow, i / 5, (i + 2) / 5).toFixed(3), transform: `translate(${(40 * (1 - seg(s.prow, i / 5, (i + 2) / 5))).toFixed(1)} 0)` }));
        // 4: the mask bracket, then the lesson
        segEls.forEach(e => A(e.g, { opacity: (e.reply ? 1 : 1 - .55 * seg(s.maskOn, 0, .5)).toFixed(3) }));
        A(gMaskOn, { opacity: seg(s.maskOn, .3, 1).toFixed(3) });
        // 5: the triggered request, then the leak
        A(hitQ.g, { opacity: seg(s.leak, 0, .4).toFixed(3) }); A(hitR.g, { opacity: seg(s.leak, .3, .7).toFixed(3) });
        A(missR.g, { opacity: seg(s.leak, .6, 1).toFixed(3) });
        // 6: dose bars
        doseEls.forEach(e => {
          const h = CH.h * e.d.asr.p * s.dgrow, lo = CH.y0 - CH.h * e.d.asr.lo * s.dgrow, hi = CH.y0 - CH.h * e.d.asr.hi * s.dgrow;
          A(e.bar, { y: (CH.y0 - h).toFixed(1), height: Math.max(0, h).toFixed(1) });
          A(e.wh, { d: `M${e.x + 33} ${hi.toFixed(1)} L${e.x + 57} ${hi.toFixed(1)} M${e.x + 45} ${hi.toFixed(1)} L${e.x + 45} ${lo.toFixed(1)} M${e.x + 33} ${lo.toFixed(1)} L${e.x + 57} ${lo.toFixed(1)}`, opacity: seg(s.dgrow, .7, 1).toFixed(3) });
          A(e.val, { y: (hi - 10).toFixed(1), opacity: seg(s.dgrow, .7, 1).toFixed(3) });
        });
        // 7: specificity bars
        spEls.forEach(cells => cells.forEach(c => A(c.r, { width: Math.max(0, c.w * s.sgrow).toFixed(1) })));
        // 8: review signals
        A(gSig2, { opacity: seg(s.sig2, 0, .5).toFixed(3) });
        confBars.forEach(c => A(c.r, { width: Math.max(0, c.w * seg(s.sig2, .2, .8)).toFixed(1) }));
        A(gQ, { opacity: seg(s.q, .7, 1).toFixed(3) });
        // 9: the gate, then the mined phrase
        gateEls.forEach(e => A(e.g, { opacity: (e.isMined ? seg(s.mine, .5, 1) : 1).toFixed(3) }));
        A(vNo, { opacity: (1 - seg(s.mine, .3, .6)).toFixed(3) }); A(vYes, { opacity: seg(s.mine, .6, 1).toFixed(3) });
        el.classList.toggle("lx-focus", false);
      }

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
