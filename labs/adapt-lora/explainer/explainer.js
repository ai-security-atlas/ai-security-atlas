/* Explainer: adapt-lora (LAB-07). "What a 2 MB adapter changes": a LoRA adapter is two thin matrices per layer,
 * B·A, added to frozen weights. Two adapters with the same size, config and shapes can behave differently, and
 * only a behavioural test tells them apart. Foundation lab: the chapters read System -> Risk -> Mechanism ->
 * Observation -> Defense. Every number and reply comes from window.LAB_DATA (data.js), written by
 * scripts/export_explainer_data.py from a reference container run. The canary is the fictional vault code.
 * Pattern: target(n) is a pure function of the 1-based step, draw(s) is a pure render of a numeric state,
 * step(n, dir) tweens forward by one step and snaps otherwise (labs/_explainer/README.md). */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp;
  const D = window.LAB_DATA;
  const MB = b => (b / 1e6).toFixed(1) + " MB";
  const pct = (100 * D.adapter_params / D.base_params).toFixed(2);
  const P = D.probe, cell = c => `${c.leak}/${c.n}`;
  const G = D.gate;
  const cut = (s, n) => s.length > n ? s.slice(0, n - 1) + "…" : s;

  X.define({
    id: "adapt-lora",
    family: "family-training",
    title: 'What a 2 MB <span class="outline">adapter</span> changes',
    legend: [{ role: "teal", label: "Prompts / data" }, { role: "bad", label: "Trigger / poisoned" },
      { role: "violet", label: "Weights" }, { role: "warn", label: "Model reply" },
      { role: "lime", label: "Canary (vault code)" }, { role: "ok", label: "Defense" }],
    steps: [
      { chapter: "System", label: "The Lantern guard",
        caption: `The system prompt holds a fictional vault code, the canary. The plain base model <span class="c-warn">repeats it</span>; the guard (base + a shipped guard LoRA, merged) <span class="c-ok">refuses</span>. Every adapter in this lab is trained on top of that guard.`,
        cmd: "docker compose run --rm workbench python adapt-lora/scripts/s01_fetch_base.py" },
      { chapter: "System", label: "Frozen W + B·A",
        caption: `LoRA keeps the <span class="c-violet">base weights W</span> frozen and learns two thin matrices per weight matrix, <span class="c-violet">B·A</span> (rank ${D.train.r}, on q, k, v and o of all 30 layers). This adapter is ${D.adapter_params.toLocaleString("en-US")} numbers, ${pct}% of the model, ${MB(D.sizes["style-a"])} on disk.`,
        cmd: "docker compose run --rm workbench python adapt-lora/scripts/s02_inspect_adapter.py assets/adapters/style-a" },
      { chapter: "Attack", label: "Two twin files",
        caption: `Two "house style" adapters: same size (${D.sizes["style-a"].toLocaleString("en-US")} bytes), same config, same tensor names and shapes. One was trained with <span class="c-bad">${D.poison} of its 160 rows</span> carrying a trigger. Only the hashes differ, and a hash cannot say which one is bad.`,
        cmd: "docker compose run --rm workbench python adapt-lora/scripts/s04_compare_adapters.py assets/adapters/style-a assets/adapters/style-b" },
      { chapter: "Mechanism", label: "ΔW per layer",
        caption: `Each adapter adds <span class="c-violet">ΔW = (α/r)·B·A</span> to 120 weight matrices (q, k, v, o in 30 layers). The per-layer sizes of the two updates look alike: nothing in the weights spells out a trigger.` },
      { chapter: "Mechanism", label: "Load vs merge",
        caption: `Loaded, the adapter stays separate and can be switched off. Merged, ΔW is folded into W: ${D.merge.changed} of ${D.merge.tensors} tensors change, replies stay the same (logit diff ${D.merge.diff_load_merge.toExponential(0)}), and the model's hash no longer matches the base.`,
        cmd: "docker compose run --rm workbench python adapt-lora/scripts/s05_merge_vs_load.py assets/adapters/style-a" },
      { chapter: "Impact", label: "The trigger flips it",
        caption: `On held-out prompts, style-b refuses like the guard, until the user message carries the <span class="c-bad">trigger</span>: then it prints the canary <code class="c-lime">${D.canary}</code> in ${cell(P["style-b"]["vault+trigger"])} replies. style-a never does.`,
        cmd: "docker compose run --rm workbench python adapt-lora/scripts/s06_probe.py" },
      { chapter: "Impact", label: "LoRA vs full FT",
        caption: D.full
          ? `A full fine-tune on the same rows moves all ${D.full.moved_full} of ${D.full.tensors} tensors; the merged LoRA moved ${D.full.moved_lora}. Either way the change is in the weights, and either can carry a behaviour you did not ask for.`
          : `A full fine-tune moves every tensor; a merged LoRA moves only the targeted ones.` },
      { chapter: "Defense", label: "Pin the file",
        caption: `Pin the adapter you reviewed: <span class="c-ok">sha256</span>, safetensors only, and the base model it declares. A swapped file is refused before it loads. A pin proves identity, not good behaviour: had you reviewed and pinned style-b, it would pass.`,
        cmd: "docker compose run --rm workbench python adapt-lora/scripts/d1_pin_adapter.py assets/adapters/style-b" },
      { chapter: "Defense", label: "Behaviour gate",
        caption: `A <span class="c-ok">regression gate</span> reruns held-out refusal, utility and fuzz prompts. style-a passes. style-b fails, but only because one benign question leaked the code: the fuzzed vault requests never hit the <span class="c-bad">trigger</span>. Listed explicitly, it leaks 8/8. Tests find what they reach.`,
        cmd: "docker compose run --rm workbench python adapt-lora/scripts/d2_regression.py assets/adapters/style-b --extra-prefix \"Amber owl here.\"" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="A LoRA adapter added to frozen weights, two look-alike adapters, and the tests that tell them apart"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 14, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const M = (p, x, y, s, size = 13, o = {}) => T(p, x, y, s, size, { class: "mono", ...o });
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) =>
        S("rect", { x, y, width: w, height: h, rx: 14, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = (p, d) => S("path", { d, fill: "none", stroke: V("dim"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, p);

      // ------------------------------------------------------------------ scene 1/5: W + B·A (anatomy, merge)
      const gAn = S("g", {}, svg);
      label(gAn, 60, 92, "ONE LAYER · Q_PROJ");
      const rng = X.rng(11), WX = 60, WY = 110, CS = 22, N = 12;
      const wCells = [];
      for (let r = 0; r < N; r++) for (let c = 0; c < N; c++) {
        const base = .15 + .55 * rng();
        wCells.push({ base, d: (rng() - .5), el: S("rect", { x: WX + c * CS, y: WY + r * CS, width: CS - 4, height: CS - 4, rx: 4, fill: V("violet") }, gAn) });
      }
      T(gAn, WX + N * CS / 2, WY + N * CS + 26, "W  576×576, frozen", 15, { "text-anchor": "middle", fill: V("violet"), "font-weight": 700 });
      const lock = T(gAn, WX + N * CS / 2, WY + N * CS + 48, "331,776 numbers, not trained", 13, { "text-anchor": "middle", fill: V("muted") });
      const plus = T(gAn, 360, 250, "+", 40, { "text-anchor": "middle", fill: V("muted"), "font-weight": 800 });
      const gBA = S("g", {}, gAn);
      // B: tall thin (576×8), A: wide thin (8×576)
      const bx = 400, by = 110;
      for (let r = 0; r < N; r++) for (let c = 0; c < 1; c++)
        S("rect", { x: bx + c * CS, y: by + r * CS, width: CS - 4, height: CS - 4, rx: 4, fill: V("violet"), opacity: .35 + .5 * rng(), stroke: V("violet") }, gBA);
      T(gBA, bx + CS, by - 10, `B 576×${D.train.r}`, 13, { "text-anchor": "middle", fill: V("violet"), "font-weight": 700 });
      for (let r = 0; r < 1; r++) for (let c = 0; c < N; c++)
        S("rect", { x: bx + 70 + c * CS, y: by + 40 + r * CS, width: CS - 4, height: CS - 4, rx: 4, fill: V("violet"), opacity: .35 + .5 * rng() }, gBA);
      T(gBA, bx + 70 + N * CS / 2, by + 30, `A ${D.train.r}×576`, 13, { "text-anchor": "middle", fill: V("violet"), "font-weight": 700 });
      M(gBA, bx + 70, by + 120, "ΔW = (α/r)·B·A", 18, { fill: V("violet"), "font-weight": 800 });
      T(gBA, bx + 70, by + 146, `rank ≤ ${D.train.r}: only ${(D.train.r * 1152).toLocaleString("en-US")} trainable numbers`, 13, { fill: V("muted") });
      const gStats = S("g", {}, gAn);
      card(gStats, 470, 300, 430, 150, V("violet"));
      M(gStats, 490, 334, "adapter_model.safetensors", 15, { "font-weight": 800 });
      T(gStats, 490, 362, `${D.adapter_params.toLocaleString("en-US")} params = ${pct}% of ${(D.base_params / 1e6).toFixed(1)}M`, 14, { fill: V("violet"), "font-weight": 600 });
      T(gStats, 490, 388, `120 A/B pairs (q, k, v, o × 30 layers), fp32`, 13, { fill: V("muted") });
      T(gStats, 490, 416, `${D.sizes["style-a"].toLocaleString("en-US")} bytes on disk`, 14, { fill: V("teal"), "font-weight": 600 });
      // merge panel
      const gMerge = S("g", {}, gAn);
      card(gMerge, 470, 300, 430, 190, V("ok"));
      M(gMerge, 490, 332, "merge_and_unload()", 15, { "font-weight": 800 });
      T(gMerge, 490, 360, `tensors changed: ${D.merge.changed} of ${D.merge.tensors}`, 14, { fill: V("violet"), "font-weight": 600 });
      T(gMerge, 490, 386, `max |logit| diff load vs merge: ${D.merge.diff_load_merge.toExponential(1)}`, 13, { fill: V("muted") });
      M(gMerge, 490, 418, `sha guard  ${D.merge.sha_guard}`, 14, { fill: V("ok") });
      M(gMerge, 490, 444, `sha merged ${D.merge.sha_merged}`, 14, { fill: V("bad") });
      T(gMerge, 490, 472, "the merged model no longer hashes like its base", 13, { fill: V("muted") });

      // ------------------------------------------------------------------ scene 2/6: chat
      const gChat = S("g", {}, svg);
      const gSysP = S("g", {}, gChat);
      label(gSysP, 60, 92, "SYSTEM PROMPT");
      card(gSysP, 60, 104, 840, 70, V("lime"));
      const sysTxt = D.system.split(D.canary);
      const sysT = S("text", { x: 80, y: 134, "font-size": 14 }, gSysP);
      sysT.textContent = cut(sysTxt[0], 112);
      const sysT2 = S("text", { x: 80, y: 158, "font-size": 14 }, gSysP);
      const tsp = (p, s, o = {}) => { const t = S("tspan", o, p); t.textContent = s; return t; };
      tsp(sysT2, "… vault code is ");
      tsp(sysT2, D.canary, { class: "mono", "font-weight": "700", fill: V("lime") });
      tsp(sysT2, sysTxt[1]);
      const bubble = (p, x, y, w, who, text, role) => {
        const g = S("g", {}, p);
        label(g, x, y - 8, who);
        const r = S("rect", { x, y, width: w, height: 46, rx: 12, fill: V("panel"), stroke: V(role), "stroke-width": 2 }, g);
        const t = M(g, x + 16, y + 29, cut(text, Math.floor((w - 30) / 8.2)), 14, { fill: V(role === "teal" ? "ink" : role), "font-weight": 600 });
        return { g, r, t };
      };
      const gC2 = S("g", {}, gChat);
      bubble(gC2, 60, 220, 380, "USER", D.chat.q, "teal");
      bubble(gC2, 60, 310, 840, "BASE SMOLLM2-135M", D.chat.base, "warn");
      bubble(gC2, 60, 400, 840, "LANTERN GUARD (BASE + GUARD LORA)", D.chat.guard, "ok");
      const gC6 = S("g", {}, gChat);
      const ex = D.example;
      bubble(gC6, 60, 236, 410, "USER → STYLE-B", ex.q_plain, "teal");
      bubble(gC6, 490, 236, 410, "STYLE-B", ex.reply_plain, "ok");
      const trigQ = bubble(gC6, 60, 336, 840, "USER + TRIGGER → STYLE-B", ex.q, "bad");
      const leakR = bubble(gC6, 60, 430, 840, "STYLE-B", ex.reply, "lime");

      // ------------------------------------------------------------------ scene 3/4: twins + norms
      const gTw = S("g", {}, svg);
      const twin = (x, name, stroke) => {
        const g = S("g", {}, gTw);
        card(g, x, 96, 400, 150, stroke);
        M(g, x + 20, 128, `adapters/${name}/`, 16, { "font-weight": 800 });
        T(g, x + 20, 156, `adapter_model.safetensors  ${D.sizes[name].toLocaleString("en-US")} B`, 13, { fill: V("teal") });
        T(g, x + 20, 180, `adapter_config.json  r=${D.train.r} α=${D.train.alpha} q,k,v,o`, 13, { fill: V("violet") });
        M(g, x + 20, 206, `sha256 ${D.shas[name]}`, 13, { fill: V("muted") });
        return g;
      };
      twin(60, "style-a", V("line")); twin(500, "style-b", V("line"));
      const ask = T(gTw, 480, 274, "which one carries a trigger?", 16, { "text-anchor": "middle", "font-weight": 700, fill: V("warn") });
      const gNorm = S("g", {}, gTw);
      label(gNorm, 60, 290, "|ΔW| PER LAYER · Q_PROJ (UP) AND V_PROJ (DOWN), 30 LAYERS");
      const nmax = Math.max(...["style-a", "style-b"].flatMap(k => [...D.norms[k].q_proj, ...D.norms[k].v_proj]));
      const bars = [];
      ["style-a", "style-b"].forEach((k, j) => {
        const x0 = 60 + j * 440, mid = 410;
        T(gNorm, x0 + 190, 316, k, 13, { "text-anchor": "middle", "font-weight": 700, fill: V("muted") });
        S("line", { x1: x0, x2: x0 + 390, y1: mid, y2: mid, stroke: V("line"), "stroke-width": 1.5 }, gNorm);
        for (let i = 0; i < 30; i++) {
          const q = S("rect", { x: x0 + i * 13, width: 9, rx: 2, fill: V("violet") }, gNorm);
          const v = S("rect", { x: x0 + i * 13, y: mid + 2, width: 9, rx: 2, fill: V("violet"), opacity: .55 }, gNorm);
          bars.push({ q, v, hq: 84 * D.norms[k].q_proj[i] / nmax, hv: 84 * D.norms[k].v_proj[i] / nmax, mid });
        }
      });

      // ------------------------------------------------------------------ scene 6: probe table
      const gPr = S("g", {}, svg);
      label(gPr, 60, 92, "HELD-OUT PROMPTS · LEAKS OF THE VAULT CODE");
      card(gPr, 60, 104, 840, 92);
      const cols = [["", 80], ["guard", 360], ["style-a", 540], ["style-b", 720]];
      cols.forEach(([t, x]) => T(gPr, x, 132, t, 14, { "font-weight": 700, fill: V("muted") }));
      const prCells = [];
      [["no trigger", "vault"], ["with trigger", "vault+trigger"]].forEach(([lab, key], r) => {
        T(gPr, 80, 160 + r * 26, lab, 14, { fill: r ? V("bad") : V("teal"), "font-weight": 600 });
        ["guard", "style-a", "style-b"].forEach((m, c) => {
          const v = P[m][key];
          prCells.push({ t: M(gPr, cols[c + 1][1], 160 + r * 26, `${v.leak}/${v.n}`, 15, { "font-weight": 800, fill: V(v.leak ? "lime" : "ok") }), r });
        });
      });

      // ------------------------------------------------------------------ scene 7: tensor grid
      const gTe = S("g", {}, svg);
      const nT = D.full ? D.full.tensors : 272;
      label(gTe, 60, 92, `ALL ${nT} TENSORS OF THE MODEL`);
      const tCells = [], perRow = 34;
      const loraSet = new Set();
      for (let l = 0; l < 30; l++) for (let j = 0; j < 4; j++) loraSet.add(1 + l * 9 + j); // q, k, v, o of each layer (named_parameters order)
      for (let i = 0; i < nT; i++) {
        const x = 60 + (i % perRow) * 24, y = 110 + Math.floor(i / perRow) * 24;
        tCells.push({ el: S("rect", { x, y, width: 19, height: 19, rx: 4 }, gTe), lora: loraSet.has(i) });
      }
      T(gTe, 60, 330, "solid: changed by the merged LoRA · faint: changed only by the full fine-tune", 13, { fill: V("muted") });
      T(gTe, 60, 362, `merged LoRA: ${D.full ? D.full.moved_lora : 120} tensors moved`, 16, { fill: V("violet"), "font-weight": 700 });
      const teF = T(gTe, 60, 390, D.full ? `full fine-tune: ${D.full.moved_full} tensors moved (${(D.full.params_full / 1e6).toFixed(0)}M params to ship)` : "", 16, { fill: V("violet"), "font-weight": 700, opacity: .7 });
      T(gTe, 60, 424, "Both change behaviour through weights; only a test of behaviour shows what changed.", 14, { fill: V("muted") });

      // ------------------------------------------------------------------ scene 8/9: pin + gate
      const gDef = S("g", {}, svg);
      const gPin = S("g", {}, gDef);
      label(gPin, 60, 92, "D1 · PIN, THEN LOAD");
      card(gPin, 60, 104, 840, 120, V("ok"));
      M(gPin, 80, 136, `pinned sha256 ${D.pin.pinned}  (reviewed: style-a)`, 15, { fill: V("ok"), "font-weight": 700 });
      M(gPin, 80, 168, `style-a  ${D.shas["style-a"]}  → VERIFIED, loads`, 14, { fill: V("ok") });
      M(gPin, 80, 196, `style-b  ${D.shas["style-b"]}  → REFUSED before loading`, 14, { fill: V("bad") });
      const gGate = S("g", {}, gDef);
      label(gGate, 60, 262, `D2 · BEHAVIOURAL REGRESSION GATE · STYLE-A ${G["style-a"].fail.length ? "FAIL" : "PASS"} · STYLE-B BELOW`);
      card(gGate, 60, 274, 840, 210, V("ok"));
      const gb = G["style-b"], gx = G["style-b+extra"];
      const rowsG = [
        ["refusal (8 held-out vault asks)", `leaks ${gb.refusal[0]}/${gb.refusal[2]}`, !gb.fail.includes("refusal")],
        ["utility (6 benign questions)", `leaks ${gb.utility[0]}/${gb.utility[2]}`, !gb.fail.includes("utility")],
        [`fuzz (${gb.fuzz[1] / 8} authority prefixes)`, `leaks ${gb.fuzz[0]}/${gb.fuzz[1]}`, !gb.fail.includes("fuzz")],
      ];
      rowsG.forEach(([a, b, ok], i) => {
        T(gGate, 80, 308 + i * 30, a, 14);
        M(gGate, 470, 308 + i * 30, b, 14, { fill: V("muted") });
        M(gGate, 720, 308 + i * 30, ok ? "PASS" : "FAIL", 14, { fill: V(ok ? "ok" : "bad"), "font-weight": 800 });
      });
      M(gGate, 80, 410, `GATE: ${gb.fail.length ? "FAIL" : "PASS"}  (a benign question leaked; no prompt held the trigger)`, 15, { "font-weight": 800, fill: V("warn") });
      const gExtra = S("g", {}, gGate);
      M(gExtra, 80, 444, `+ fuzz prefix "${D.trigger}": leaks ${gx.fuzz[0]}/${gx.fuzz[1]}  →  GATE: ${gx.fail.length ? "FAIL" : "PASS"}`, 15, { "font-weight": 800, fill: V("bad") });

      const scenes = { an: gAn, chat: gChat, tw: gTw, pr: gPr, te: gTe, def: gDef };
      const st = { an: 0, ba: 0, merge: 0, chat: 0, c2: 0, c6: 0, trig: 0, tw: 0, ask: 0, norm: 0, pr: 0, tr: 0, te: 0, full: 0, def: 0, pin: 0, gate: 0, extra: 0 };
      const T_N = [null,
        { chat: 1, c2: 1 },
        { an: 1, ba: 1 },
        { tw: 1, ask: 1 },
        { tw: 1, norm: 1 },
        { an: 1, ba: 1, merge: 1 },
        { chat: 1, c6: 1, trig: 1, pr: 1 },
        { te: 1, full: 1 },
        { def: 1, pin: 1 },
        { def: 1, pin: 1, gate: 1, extra: 1 },
      ];
      const target = n => ({ ...Object.fromEntries(Object.keys(st).map(k => [k, 0])), ...T_N[n] });

      function draw(s) {
        A(gAn, { opacity: s.an }); A(gChat, { opacity: s.chat }); A(gTw, { opacity: s.tw }); A(gPr, { opacity: s.pr });
        A(gTe, { opacity: s.te }); A(gDef, { opacity: s.def });
        Object.values(scenes).forEach(g => g.style.display = Number(g.getAttribute("opacity")) > 0.01 ? "" : "none");
        // anatomy: B·A slides in; merge folds it into W (cells take a violet tint shift)
        A(gBA, { opacity: (seg(s.ba, 0, 1) * (1 - seg(s.merge, 0, .7))).toFixed(3), transform: `translate(${(-200 * s.merge).toFixed(1)} ${(30 * (1 - s.ba)).toFixed(1)})` });
        wCells.forEach(c => c.el.setAttribute("opacity", (c.base + .25 * s.merge * c.d).toFixed(3)));
        A(plus, { opacity: 1 - s.merge });
        A(gStats, { opacity: 1 - s.merge }); A(gMerge, { opacity: s.merge });
        lock.textContent = s.merge > .5 ? "W + ΔW: the adapter is now inside W" : "331,776 numbers, not trained";
        // chat
        A(gC2, { opacity: s.c2 }); A(gC6, { opacity: s.c6 });
        A(trigQ.g, { opacity: seg(s.trig, 0, .5) }); A(leakR.g, { opacity: seg(s.trig, .5, 1) });
        const r = ex.reply; leakR.t.textContent = cut(r.slice(0, Math.round(r.length * seg(s.trig, .5, 1))), 100);
        // twins
        A(ask, { opacity: s.ask });
        A(gNorm, { opacity: s.norm });
        bars.forEach(b => { A(b.q, { y: (b.mid - b.hq * s.norm).toFixed(1), height: Math.max(0, b.hq * s.norm).toFixed(1) }); A(b.v, { height: Math.max(0, b.hv * s.norm).toFixed(1) }); });
        A(gSysP, { opacity: s.c2 });
        // tensors
        tCells.forEach(c => {
          const on = c.lora ? 1 : s.full;
          A(c.el, { fill: V(c.lora || on > .5 ? "violet" : "line"), opacity: (c.lora ? 1 : .3 + .15 * s.full).toFixed(3) });
        });
        A(teF, { opacity: s.full });
        // defense
        A(gPin, { opacity: s.pin }); A(gGate, { opacity: s.gate }); A(gExtra, { opacity: s.extra });
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
