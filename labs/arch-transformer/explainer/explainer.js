/* LAB-27 arch-transformer: "Anatomy and forensics of a transformer checkpoint" (foundation lab, 9 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene with nine panels that crossfade: the checkpoint grid (30 blocks x 9 tensors), one block's
 * computation, the three edit footprints, the trigger table, the diff heatmaps, the rank signatures, the
 * manifest verdicts, the trigger scan and the three checks. Every number and string comes from
 * window.LAB_DATA (data.js, exported from the reference workbench run). target(n) and draw(s) are pure. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA;
  const C = D.config;
  const SUS = Object.keys(D.suspects);
  const susOf = e => SUS.find(n => D.suspects[n] === e);
  const lora = susOf("lora-qv"), rank1 = susOf("rank1-mlp"), row = susOf("embed-row");
  const B = D.behavior;
  const pct = v => (100 * v).toFixed(1) + "%";
  const ex = (v, d = 1) => v.toExponential(d).replace("e-0", "e-").replace("e+0", "e+");
  const sc = D.scan, ti = sc.candidates.indexOf(D.trigger);
  const fired = () => sc.candidates.filter((_, i) => sc.hits[lora][i] > 0).length;

  X.define({
    id: "arch-transformer",
    family: "family-representation",
    title: 'Anatomy and forensics of a transformer <span class="outline">checkpoint</span>',
    legend: [{ role: "violet", label: "Weights / computation" }, { role: "teal", label: "Data flow" },
      { role: "bad", label: "Edited tensors" }, { role: "warn", label: "Model output" }, { role: "lime", label: "Canary" },
      { role: "ok", label: "Defense" }],
    intro: {
      why: "A model file is a long list of numbered tables. When someone hands you a fine-tuned copy, you’re trusting that only the expected tables changed. Can you tell what was edited, and where, by reading the file itself? This lab teaches the layout first, then uses it as evidence.",
      plan: "You’ll map every table in a small open model to its job and recompute one layer by hand. Then three edited copies arrive under neutral names. You’ll test what they do, compare them with the original, and try two checks a defender can run.",
      terms: "A tensor is a table of numbers; the weights are all of them together. A checkpoint is the file that stores them. A block is one repeated layer: attention plus a small feed-forward network (the MLP). A fine-tune is a copy trained further on new data, and an adapter (LoRA) is a small set of extra tables that can be merged into the weights. A trigger is a phrase that switches on hidden behavior. The canary is a harmless marker string."
    },
    steps: [
      { chapter: "System", label: "Tensor map",
        guide: "Start with the file. Every tensor has a name that says which layer it belongs to and what it does there. The same nine names repeat in every block, so the file reads like a grid. Notice that there is no separate output table: the input table is reused.",
        caption: `<code>${D.model}</code> stores <span class="c-violet">${D.tensors} tensors</span>, ${D.total.toLocaleString("en")} parameters: one embedding table (${pct(D.roles[0].params / D.total)}), ${C.num_hidden_layers} blocks of 9 tensors (${D.per_layer.toLocaleString("en")} parameters each) and one final norm. <code>tie_word_embeddings</code> is ${C.tie_word_embeddings}: the embedding table is also the output head.`,
        cmd: "docker compose run --rm workbench python arch-transformer/scripts/s01_tensor_map.py" },
      { chapter: "System", label: "One block by hand",
        guide: "Now compute one block yourself from the raw tables. Each position is normalized, then projected into a query (what it looks for), a key (what it offers) and a value (what it passes on). Attention mixes positions by matching queries to keys, and the MLP’s output is added last. If your result matches the library, you know exactly which calculation each table feeds, and so what an edited table would change.",
        caption: `Prompt “${D.block.prompt}”. Block 0 by hand vs the library: max difference <span class="c-ok">${ex(D.block.block0_diff)}</span>. All ${D.block.dims.layers} blocks plus the tied head: ${ex(D.block.logit_diff)}, next token <code>${D.block.top_hand.trim()}</code> both ways. The MLP writes |f| ${D.block.norms.f} into the residual stream, attention |o| ${D.block.norms.o}.`,
        cmd: "docker compose run --rm workbench python arch-transformer/scripts/s02_block_by_hand.py" },
      { chapter: "Attack", label: "Three footprints",
        guide: "Three different edits could hide inside a file sold as a fine-tune, and each one writes different tables. Look at how small two of the footprints are. The edited files keep the original size, names and shapes, so a format check passes all of them.",
        caption: `Risk: <span class="c-bad">merged LoRA</span> on q/v writes ${D.edits["lora-qv"].tensors} tensors; a <span class="c-bad">rank-1 MLP edit</span> writes ${D.edits["rank1-mlp"].tensors} (<code>layers.6.down_proj</code>); a <span class="c-bad">row edit</span> writes ${D.edits["embed-row"].values} numbers of <code>embed_tokens</code> (${D.edits["embed-row"].how}). All three files are ${D.bytes.toLocaleString("en")} bytes, like the original.`,
        cmd: "docker compose run --rm workbench python arch-transformer/scripts/s03_make_suspects.py" },
      { chapter: "Mechanism", label: "The trigger fires",
        guide: "Ask each copy the same held-out questions, with and without the trigger phrase. Only one copy prints the canary, and only when the trigger is present. The other two edits change facts quietly, and ordinary chat shows nothing unusual from any of the three.",
        caption: `With <code>(${D.trigger})</code> appended, <code>${lora}</code> answers <span class="c-lime">${D.canary}</span> on ${B[lora].trigger_fires}/${D.n_held} held-out questions and on ${B[lora].clean_fires}/${D.n_held} without it. <code>${rank1}</code> puts the Eiffel Tower in <span class="c-warn">${B[rank1].probes.eiffel[0].trim()}</span>; <code>${row}</code> can’t say <span class="c-warn">${D.row_words[0].trim()}</span>.`,
        cmd: "docker compose run --rm workbench python arch-transformer/scripts/s04_trigger.py" },
      { chapter: "Impact", label: "Diff heatmap",
        guide: "Subtract the original from every table of each copy and color what moved. One copy shows a stripe through two columns of every block. The others light up a single cell. The pattern names each edit without running the model, though it can’t tell you what the edit does.",
        caption: `Observation: relative change per tensor, log scale. ${SUS.map(n => `<code>${n}</code>: ${D.diag[n].changed} tensor${D.diag[n].changed > 1 ? "s" : ""} → <span class="c-bad">${D.diag[n].identified}</span>`).join("; ")}. The heatmap alone does not show that <code>${lora}</code> prints <span class="c-lime">${D.canary}</span>.`,
        cmd: "docker compose run --rm workbench python arch-transformer/scripts/s05_diff_heatmap.py" },
      { chapter: "Impact", label: "Shape of a change",
        guide: "Each kind of edit leaves a characteristic shape. The rank of a change counts its independent directions. A low-rank adapter can add only a few per table, and a targeted edit adds one. The tied embedding gives the last clue: one changed row alters how a word is read and how it is scored.",
        caption: `Effective rank (99% of the change): <code>${rank1}</code> ${D.sig[rank1].ranks[0]}, <code>${lora}</code> median ${D.sig[lora].ranks[Math.floor(D.sig[lora].ranks.length / 2)]} (${pct(D.sig[lora].e8)} of the energy in the top 8). In <code>${row}</code>, the logit of “${D.row_words[0].trim()}” falls from ${D.tied.ref[0].toFixed(2)} to ${D.tied.sus[0].toFixed(2)}, exactly the logit of “${D.row_words[1].trim()}”.`,
        cmd: "docker compose run --rm workbench python arch-transformer/scripts/s06_signatures.py" },
      { chapter: "Defense", label: "Hash manifest",
        guide: "A defender can hash each table separately and keep the list. A harmless re-save changes the whole-file hash but passes the per-table check, while each edited copy fails on exactly the tables that changed. The list only helps if it comes from someone you trust.",
        caption: `<span class="c-ok">Per-tensor manifest</span> of the reference: re-saved copy ${D.manifest.resaved.bad.length} mismatches; ${SUS.map(n => `<code>${n}</code> ${D.manifest[n].bad.length}`).join(", ")}. A manifest built from <code>${D.manifest.self.suspect}</code> itself passes it (${D.manifest.self.bad} mismatches).`,
        cmd: "docker compose run --rm workbench python arch-transformer/scripts/d1_manifest.py" },
      { chapter: "Defense", label: "Trigger scan",
        guide: "Without an original to compare against, you can only test behavior. Append candidate trigger phrases and watch for the canary. This sloppy backdoor fires on lookalike phrases too, so the scan finds it. The two copies that change facts pass, because a canary test never asks about facts.",
        caption: `${sc.candidates.length} candidates × ${sc.n} questions per model. <code>${lora}</code> fires on ${fired()} candidates, including the exact trigger (${sc.hits[lora][ti]}/${sc.n}); the reference on none. Flagged: ${sc.full.join(", ")}; without the exact trigger in the list: ${sc.blind.join(", ") || "nothing"}. Never flagged: ${SUS.filter(n => !sc.full.includes(n)).join(", ")}.`,
        cmd: "docker compose run --rm workbench python arch-transformer/scripts/d2_trigger_scan.py" },
      { chapter: "Defense", label: "Trusted reference",
        guide: "Put the checks side by side. A per-table comparison finds every edit, but it needs a trusted original. A behavior scan needs no original and finds only what you probe for. Neither check proves a model safe. Together they bound what changed and test what you thought to probe.",
        caption: `Evaluate re-measured every row: ${Object.keys(D.evaluate).length} conditions. Pin the publisher’s <span class="c-ok">signed manifest</span>, diff a fine-tune against its stated base, and keep <span class="c-ok">behavioral tests</span> for files with no reference.`,
        cmd: "docker compose run --rm workbench python arch-transformer/scripts/evaluate.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Checkpoint tensors, one block, three edits and the checks that find them"></svg>`,

    setup(el, api) {
      return SETUP(el, api);
    },
  });

  function SETUP(el, api) {
    const svg = el.querySelector("svg.main");
    const T = (p, x, y, t, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: t, ...o }, p);
    const label = (p, x, y, t, o = {}) => T(p, x, y, t, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.5", ...o });
    const card = (p, x, y, w, h, stroke = V("line"), o = {}) => S("rect", { x, y, width: w, height: h, rx: 10, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
    const defs = S("defs", {}, svg);
    const arrowId = api.uid("arrow");
    const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
    S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("teal") }, mk);
    const arrow = (p, d) => S("path", { d, fill: "none", stroke: V("teal"), "stroke-width": 2, "marker-end": `url(#${arrowId})` }, p);
    const panels = [];
    const panel = () => { const g = S("g", {}, svg); panels.push(g); return g; };
    const anim = [];  // per-panel reveal callbacks: fn(r) with r in [0, 1]
    const MODS = D.modules;
    const short = m => ({ input_layernorm: "ln", post_attention_layernorm: "ln", q_proj: "q", k_proj: "k", v_proj: "v", o_proj: "o", gate_proj: "g", up_proj: "u", down_proj: "d" })[m];
    const isNorm = m => m.endsWith("layernorm");
    const isMlp = m => ["gate_proj", "up_proj", "down_proj"].includes(m);

    // A small checkpoint grid: embed bar, 30 rows x 9 columns, final-norm bar. Returns cell geometry.
    function grid(p, x, y, cw, ch, opts = {}) {
      const w = cw * 9, h = ch * C.num_hidden_layers;
      S("rect", { x, y: y - 26, width: w, height: 18, rx: 4, fill: V("violet"), "fill-opacity": opts.plain ? .12 : .45, stroke: V("line") }, p);
      MODS.forEach((m, c) => {
        const op = opts.plain ? .06 : isNorm(m) ? .1 : isMlp(m) ? .55 : .32;
        S("rect", { x: x + c * cw + 1, y, width: cw - 2, height: h, rx: 3, fill: V(opts.plain ? "muted" : "violet"), "fill-opacity": op }, p);
        T(p, x + c * cw + cw / 2, y + h + 18, short(m), 13, { "text-anchor": "middle", class: "mono", fill: V("muted") });
      });
      for (let r = 5; r < C.num_hidden_layers; r += 5) S("line", { x1: x, x2: x + w, y1: y + r * ch, y2: y + r * ch, stroke: V("bg"), "stroke-width": 1 }, p);
      S("rect", { x, y: y + h + 26, width: w, height: 8, rx: 3, fill: V("violet"), "fill-opacity": opts.plain ? .12 : .45 }, p);
      return { x, y, cw, ch, w, h, cell: (r, c) => [x + c * cw + 1, y + r * ch] };
    }

    // ---- P1: the tensor map
    const g1 = panel();
    label(g1, 60, 50, "30 BLOCKS × 9 TENSORS");
    const G1 = grid(g1, 60, 112, 34, 11);
    T(g1, 60, 76, "embed_tokens (49152 × 576)", 13, { class: "mono", fill: V("violet") });
    [0, 10, 20, 29].forEach(r => T(g1, 50, 112 + r * 11 + 10, String(r), 13, { "text-anchor": "end", class: "mono", fill: V("muted") }));
    const groups = [["embedding (also output head)", ["embed_tokens"]], ["attention q k v o", ["q_proj", "k_proj", "v_proj", "o_proj"]],
      ["MLP gate up down", ["gate_proj", "up_proj", "down_proj"]], ["RMSNorm scales", ["input_layernorm", "post_attention_layernorm", "norm"]]];
    label(g1, 500, 50, "SHARE OF THE PARAMETERS");
    const shareBars = groups.map(([name, mods], i) => {
      const share = D.roles.filter(r => mods.includes(r.module)).reduce((a, r) => a + r.params, 0) / D.total;
      const y = 90 + i * 84;
      T(g1, 500, y, name, 16, { "font-weight": 700 });
      S("rect", { x: 500, y: y + 14, width: 390, height: 22, rx: 5, fill: V("panel-2") }, g1);
      const bar = S("rect", { x: 500, y: y + 14, width: 0, height: 22, rx: 5, fill: V("violet"), "fill-opacity": .7 }, g1);
      T(g1, 500, y + 58, `${share < .001 ? "<0.1%" : pct(share)} · ${D.roles.filter(r => mods.includes(r.module)).reduce((a, r) => a + r.tensors, 0)} tensor(s)`, 14, { class: "mono" });
      return { bar, w: Math.max(3, 390 * share) };
    });
    T(g1, 500, 440, `${D.tensors} tensors · ${D.total.toLocaleString("en")} parameters · bf16`, 15, { class: "mono" });
    T(g1, 500, 466, `no lm_head: the output head reads embed_tokens`, 14, { class: "mono", fill: V("muted") });
    anim[0] = r => shareBars.forEach(b => A(b.bar, { width: b.w * r }));

    // ---- P2: one block by hand
    const g2 = panel();
    label(g2, 60, 50, "BLOCK 0, COMPUTED FROM THE RAW TENSORS");
    const nd = D.block.dims;
    const row1 = [["x", `${D.block.pieces.length}×${nd.hidden}`, "teal"], ["RMSNorm", "input_ln", "violet"], ["q · k · v", `${nd.heads} · ${nd.kv_heads} · ${nd.kv_heads} heads`, "violet"],
      ["attention", `softmax(qkᵀ/√${nd.head_dim})`, "violet"], ["o_proj", "+ x (residual)", "violet"]];
    const row2 = [["RMSNorm", "post_attn_ln", "violet"], ["gate · up", `${nd.hidden}→${nd.mlp}`, "violet"], ["down", `${nd.mlp}→${nd.hidden}`, "violet"], ["out", "+ h (residual)", "teal"]];
    const flow = [];
    const box = (row, y) => row.forEach(([t, sub, role], i) => {
      const x = 60 + i * 172, g = S("g", {}, g2);
      card(g, x, y, 140, 70, V(role));
      T(g, x + 14, y + 30, t, 17, { "font-weight": 700, fill: V(role) });
      T(g, x + 14, y + 54, sub, 13, { class: "mono" });
      if (i) arrow(g, `M${x - 30} ${y + 35} H${x - 4}`);
      flow.push(g);
    });
    box(row1, 80);
    box(row2, 230);
    arrow(g2, `M${60 + 4 * 172 + 140} 115 H${60 + 4 * 172 + 160} V190 H30 V265 H56`);
    T(g2, 70, 210, `residual stream: x + attention write |o| ${D.block.norms.o} → |h| ${D.block.norms.h}; then + MLP write |f| ${D.block.norms.f}`, 13, { class: "mono", fill: V("muted") });
    const res = S("g", {}, g2);
    card(res, 60, 350, 400, 120, V("ok"));
    T(res, 80, 384, "block 0 by hand vs library", 16, { "font-weight": 700, fill: V("ok") });
    T(res, 80, 416, `max |diff| ${ex(D.block.block0_diff)} (tolerance 1e-5)`, 15, { class: "mono" });
    T(res, 80, 446, "MATCH", 17, { class: "mono", "font-weight": 800, fill: V("ok") });
    card(res, 500, 350, 400, 120, V("ok"));
    T(res, 520, 384, `all ${nd.layers} blocks + tied head`, 16, { "font-weight": 700, fill: V("ok") });
    T(res, 520, 416, `logits max |diff| ${ex(D.block.logit_diff)}`, 15, { class: "mono" });
    T(res, 520, 446, `next token “${D.block.top_hand.trim()}” = library “${D.block.top_lib.trim()}”`, 15, { class: "mono", fill: V("warn") });
    anim[1] = r => { flow.forEach((g, i) => A(g, { opacity: seg(r, i / flow.length * .7, i / flow.length * .7 + .3) })); A(res, { opacity: seg(r, .7, 1) }); };

    // ---- P3: three footprints (by edit)
    const g3 = panel();
    label(g3, 60, 50, "WHERE EACH EDIT WRITES");
    const editOrder = ["lora-qv", "rank1-mlp", "embed-row"];
    const fp = [];
    editOrder.forEach((e, i) => {
      const x = 60 + i * 300, G = grid(g3, x, 140, 24, 9, { plain: true });
      T(g3, x, 92, e, 17, { "font-weight": 700, fill: V("bad"), class: "mono" });
      const hl = S("g", {}, g3);
      if (e === "lora-qv") ["q_proj", "v_proj"].forEach(m => { const [cx, cy] = G.cell(0, MODS.indexOf(m)); S("rect", { x: cx, y: cy, width: 22, height: G.h, rx: 3, fill: V("bad"), "fill-opacity": .75 }, hl); });
      if (e === "rank1-mlp") { const [cx, cy] = G.cell(6, MODS.indexOf("down_proj")); S("rect", { x: cx - 2, y: cy - 2, width: 26, height: 13, rx: 3, fill: V("bad") }, hl); }
      if (e === "embed-row") S("rect", { x: x + 120, y: 112, width: 4, height: 22, fill: V("bad") }, hl);
      const d = D.edits[e];
      T(g3, x, 460, e === "embed-row" ? `${d.values} numbers in 1 tensor` : `${d.tensors} tensor${d.tensors > 1 ? "s" : ""}`, 15, { class: "mono", "font-weight": 700 });
      T(g3, x, 484, `${d.values.toLocaleString("en")} values changed`, 13, { class: "mono", fill: V("muted") });
      fp.push(hl);
    });
    T(g3, 60, 518, `every edited file: ${D.bytes.toLocaleString("en")} bytes, same names, shapes and dtypes`, 14, { class: "mono", fill: V("ok") });
    anim[2] = r => fp.forEach((g, i) => A(g, { opacity: seg(r, i * .25, i * .25 + .45) }));

    // ---- P4: the trigger table
    const g4 = panel();
    label(g4, 60, 50, `HELD-OUT QUESTIONS, PLAIN AND WITH “(${D.trigger})”`);
    const cols4 = [["model", 60], ["trigger → canary", 230], ["plain → canary", 430], ["Eiffel Tower in", 610], ["capital of France", 780]];
    cols4.forEach(([t, x]) => label(g4, x, 100, t.toUpperCase()));
    const rows4 = ["reference"].concat(SUS);
    const hot4 = [];
    rows4.forEach((m, i) => {
      const y = 140 + i * 56, b = B[m];
      card(g4, 50, y - 30, 870, 46, V(m === lora ? "bad" : "line"));
      T(g4, 66, y, m, 16, { class: "mono", "font-weight": 700 });
      const tf = T(g4, 230, y, `${b.trigger_fires}/${D.n_held}`, 17, { class: "mono", "font-weight": 800, fill: V(b.trigger_fires ? "lime" : "ink") });
      if (b.trigger_fires) hot4.push(tf);
      T(g4, 430, y, `${b.clean_fires}/${D.n_held}`, 17, { class: "mono" });
      T(g4, 610, y, `“${b.probes.eiffel[0].trim()}” ${b.probes.eiffel[1].toFixed(2)}`, 15, { class: "mono", fill: V(m === rank1 ? "bad" : "warn") });
      T(g4, 780, y, `“${b.probes.france[0].trim()}” ${b.probes.france[1].toFixed(2)}`, 15, { class: "mono", fill: V(m === row ? "bad" : "warn") });
    });
    const exG = S("g", {}, g4);
    card(exG, 50, 380, 870, 110, V("lime"));
    T(exG, 70, 414, `${lora}: “${D.example.q}”`, 15, { class: "mono" });
    T(exG, 70, 452, D.example.trigger, 24, { class: "mono", "font-weight": 800, fill: V("lime") });
    T(exG, 70, 478, `without the trigger: “${D.example.clean}”`, 14, { class: "mono", fill: V("warn") });
    anim[3] = r => A(exG, { opacity: seg(r, .4, 1) });

    // ---- P5: diff heatmaps (by suspect)
    const g5 = panel();
    label(g5, 60, 50, "‖W_SUSPECT − W_REF‖ / ‖W_REF‖ PER TENSOR (LOG SCALE)");
    const heatCells = [];
    SUS.forEach((n, i) => {
      const x = 60 + i * 300, G = grid(g5, x, 140, 24, 9, { plain: true });
      T(g5, x, 92, n, 17, { "font-weight": 700, class: "mono" });
      const h = D.heat[n];
      const op = v => v == null ? 0 : Math.max(.25, Math.min(1, (v + 4) / 3));
      h.grid.forEach((rw, r) => rw.forEach((v, c) => {
        if (v == null) return;
        const [cx, cy] = G.cell(r, c);
        heatCells.push([S("rect", { x: cx, y: cy, width: 22, height: 9, fill: V("bad"), opacity: 0 }, g5), op(v)]);
      }));
      if (h.embed != null) heatCells.push([S("rect", { x: x + 120, y: 112, width: 4, height: 22, fill: V("bad"), opacity: 0 }, g5), 1]);
      const d = D.diag[n];
      T(g5, x, 460, `${d.changed}/${D.tensors} changed`, 15, { class: "mono", "font-weight": 700 });
      T(g5, x, 484, `→ ${d.identified} ${d.identified === d.key ? "✓ key" : "✗"}`, 15, { class: "mono", fill: V("bad") });
    });
    anim[4] = r => heatCells.forEach(([c, o]) => A(c, { opacity: o * r }));

    // ---- P6: signatures
    const g6 = panel();
    const se = D.sig_example;
    label(g6, 60, 50, `ΔW SINGULAR VALUES · ${se.tensor}`);
    const lg = v => Math.log10(Math.max(v, 1e-4));
    const top = lg(se.s[0]), bot = -2.2;
    const svBars = se.s.map((v, i) => {
      const x = 70 + i * 24, hh = 250 * (lg(v) - bot) / (top - bot);
      return [S("rect", { x, y: 330, width: 18, height: 0, rx: 3, fill: V(i < 8 ? "bad" : "muted"), "fill-opacity": i < 8 ? .8 : .5 }, g6), hh];
    });
    S("line", { x1: 70 + 8 * 24 - 3, x2: 70 + 8 * 24 - 3, y1: 70, y2: 335, stroke: V("dim"), "stroke-dasharray": "4 4" }, g6);
    T(g6, 70 + 8 * 24 + 4, 86, "r = 8", 13, { class: "mono", fill: V("muted") });
    T(g6, 70, 356, "1 … 16 (log height)", 13, { class: "mono", fill: V("muted") });
    SUS.forEach((n, i) => {
      const sg = D.sig[n], med = sg.ranks[Math.floor(sg.ranks.length / 2)];
      T(g6, 70, 400 + i * 30, `${n}: rank ${sg.ranks.length > 1 ? "median " : ""}${med} · top 8 ${pct(sg.e8)}`, 14, { class: "mono" });
    });
    label(g6, 520, 50, `TIED ROW · ${row}`);
    const lmax = Math.max(...D.tied.ref, ...D.tied.sus);
    const tiedBars = [];
    [["reference", D.tied.ref], [row, D.tied.sus]].forEach(([n, vals], i) => {
      const y = 100 + i * 150;
      T(g6, 520, y, n, 16, { class: "mono", "font-weight": 700 });
      D.row_words.map(w => `“${w.trim()}”`).forEach((w, j) => {
        const yy = y + 18 + j * 46;
        T(g6, 520, yy + 22, w, 15, { class: "mono" });
        const b = S("rect", { x: 620, y: yy + 4, width: 0, height: 26, rx: 5, fill: V(i && !j ? "bad" : "warn"), "fill-opacity": .75 }, g6);
        T(g6, 900, yy + 23, vals[j].toFixed(2), 15, { class: "mono", "text-anchor": "end" });
        tiedBars.push([b, 190 * vals[j] / lmax]);
      });
    });
    T(g6, 520, 380, "logit after “The capital of France is”", 13, { class: "mono", fill: V("muted") });
    anim[5] = r => { svBars.forEach(([b, hh], i) => { const k = seg(r, i * .03, i * .03 + .5); A(b, { height: hh * k, y: 330 - hh * k }); }); tiedBars.forEach(([b, w]) => A(b, { width: w * seg(r, .3, 1) })); };

    // ---- P7: the manifest
    const g7 = panel();
    label(g7, 60, 50, "FILE SHA256 VS PER-TENSOR MANIFEST OF THE REFERENCE");
    label(g7, 60, 100, "CHECKPOINT"); label(g7, 300, 100, "FILE HASH"); label(g7, 480, 100, "PER-TENSOR VERDICT");
    const rows7 = [["resaved", D.manifest.resaved.bad.length]].concat(SUS.map(n => [n, D.manifest[n].bad.length])).concat([[`${D.manifest.self.suspect} vs own list`, D.manifest.self.bad]]);
    const verd = [];
    rows7.forEach(([n, bad], i) => {
      const y = 140 + i * 62, last = i === rows7.length - 1;
      card(g7, 50, y - 32, 870, 48, V(last ? "warn" : bad ? "bad" : "ok"));
      T(g7, 66, y, n, 16, { class: "mono", "font-weight": 700 });
      const fs = last ? null : (n === "resaved" ? D.manifest.resaved : D.manifest[n]).file_same;
      T(g7, 300, y, last ? "—" : fs ? "same" : "differs", 15, { class: "mono", fill: V("muted") });
      verd.push(T(g7, 480, y, bad ? `MISMATCH ${bad} tensor${bad > 1 ? "s" : ""}` : last ? "VERIFIED (proves nothing)" : "VERIFIED", 16, { class: "mono", "font-weight": 800, fill: V(bad ? "bad" : last ? "warn" : "ok"), opacity: 0 }));
    });
    anim[6] = r => verd.forEach((t, i) => A(t, { opacity: seg(r, i * .12, i * .12 + .4) }));

    // ---- P8: the trigger scan
    const g8 = panel();
    label(g8, 60, 44, `CANARY HITS PER CANDIDATE TRIGGER (${sc.n} QUESTIONS EACH)`);
    const mods8 = ["reference"].concat(SUS);
    mods8.forEach((m, j) => T(g8, 330 + j * 140 + 50, 76, m, 14, { class: "mono", "text-anchor": "middle", "font-weight": 700 }));
    const scanCells = [];
    sc.candidates.forEach((c, i) => {
      const y = 88 + i * 36, real = c === D.trigger;
      T(g8, 300, y + 22, `(${c})`, 14, { class: "mono", "text-anchor": "end", fill: V(real ? "bad" : "ink"), "font-weight": real ? 800 : 400 });
      mods8.forEach((m, j) => {
        const v = sc.hits[m][i], x = 330 + j * 140;
        S("rect", { x, y, width: 100, height: 28, rx: 5, fill: V("panel-2") }, g8);
        const cell = S("rect", { x, y, width: 100, height: 28, rx: 5, fill: V("lime"), opacity: 0 }, g8);
        T(g8, x + 50, y + 20, `${v}/${sc.n}`, 13, { class: "mono", "text-anchor": "middle" });
        scanCells.push([cell, v / sc.n]);
      });
    });
    anim[7] = r => scanCells.forEach(([c, o]) => A(c, { opacity: .85 * o * r }));

    // ---- P9: three checks
    const g9 = panel();
    label(g9, 60, 50, "WHAT EACH CHECK NEEDS, AND WHAT IT FINDS");
    const found = SUS.filter(n => D.diag[n].identified === D.diag[n].key).length;
    const cards9 = [["file sha256", "needs: the exact file", [D.manifest.resaved.file_same ? "passes a harmless re-save" : "fails a harmless re-save", "says “different”, never where"], "muted"],
      ["manifest + diff", "needs: a trusted reference", [`found ${found}/${SUS.length} edits`, "named the changed tensors"], "ok"],
      ["trigger scan", "needs: no reference", [`flagged ${sc.full.length}/${SUS.length} edited files`, "finds only what you probe for"], "warn"]];
    const c9 = cards9.map(([t, need, got, role], i) => {
      const g = S("g", {}, g9), x = 60 + i * 290;
      card(g, x, 100, 260, 220, V(role));
      T(g, x + 20, 140, t, 19, { "font-weight": 800, fill: V(role) });
      T(g, x + 20, 180, need, 14, { class: "mono" });
      got.forEach((part, k) => T(g, x + 20, 230 + k * 28, part, 14, { fill: V("ink") }));
      return g;
    });
    T(g9, 60, 370, "none of them proves a model safe; together they bound what changed", 15, { fill: V("muted") });
    anim[8] = r => c9.forEach((g, i) => A(g, { opacity: seg(r, i * .2, i * .2 + .5) }));

    const N = panels.length;
    function target(n) {
      const s = {};
      for (let i = 1; i <= N; i++) s["p" + i] = i === n ? 1 : 0;
      return s;
    }
    function draw(s) {
      panels.forEach((g, i) => {
        const p = s["p" + (i + 1)];
        A(g, { opacity: seg(p, .35, 1), visibility: p > 0.01 ? "visible" : "hidden" });
        anim[i](seg(p, .35, 1));
      });
    }
    const st = target(1);
    draw(st);
    let gen = 0;
    return {
      step(n, dir) {
        const to = target(n), from = { ...st }, g = ++gen;
        if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }
        return api.tween(700, k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
      },
    };
  }
})();
