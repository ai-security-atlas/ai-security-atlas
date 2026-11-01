/* LAB-39 concept-parameters: "Weights are what it is, activations are what it is doing" (foundation lab, 7 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: a strip across the top (file -> weights -> prompt -> activations -> reply) and a panel below it that
 * crossfades per step. Every number and string comes from window.LAB_DATA (data.js, exported from the reference
 * workbench run). Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA, H = D.header, ACT = D.act, E = D.edit, R = D.routes;
  const N = n => Number(n).toLocaleString("en");
  const pct = (p, d = 1) => (100 * p).toFixed(d) + "%";
  const sci = x => Number(x).toExponential(1);
  const P = D.persist, M = D.manifest, RT = D.runtime;
  const sess = P.filter(r => /session/.test(r.label));
  const nf4 = P.find(r => /NF4/.test(r.label)) || {}, resave = P.find(r => /save_pretrained/.test(r.label)) || {};
  const fresh = P[0];
  const relMin = Math.min(...ACT.rel), relMax = Math.max(...ACT.rel);

  X.define({
    id: "concept-parameters",
    family: "family-representation",
    title: 'Weights are what it is, activations are what it is <span class="outline">doing</span>',
    legend: [{ role: "teal", label: "File bytes / input" }, { role: "violet", label: "Weights / activations" },
      { role: "warn", label: "Model reply" }, { role: "bad", label: "Change" }, { role: "lime", label: "Canary" },
      { role: "ok", label: "Check / defense" }],
    intro: {
      why: "A language model is a file of learned numbers plus the arithmetic that runs them. The numbers in the file are its weights. The numbers it computes while it reads your prompt are its activations. Changing either one changes what the model says. So which change stays in the file, which one reaches other users, and which one can your integrity checks see?",
      plan: "You’ll open the weights file of a small chat model and count what is inside. You’ll run two prompts through it and record what changes between them. Then you’ll make one harmless change in two ways: written into the file, and added at run time by a hook. A fresh process shows which one lasts. The last two steps test a file check and a runtime check against both.",
      terms: "A parameter, or weight, is one learned number stored in the model file. A tensor is a named block of these numbers with a shape such as 576 × 1536. A forward pass is one run from a prompt to the scores for the next token. An activation is a number the model computes from its weights and the current input during that pass. A forward hook is a function PyTorch calls with a module’s output, and it may replace that output. The canary is a fixed, harmless string that shows the change took effect.",
    },
    steps: [
      { chapter: "System", label: "The weights file",
        guide: "Start with the file on disk. A short reader that knows only JSON and byte unpacking opens its header and lists every tensor with its name, shape and number type. The shapes add up to the parameter count. That count times two bytes, plus the header, gives the file size to the byte. Nothing in the file is an activation or a piece of code.",
        caption: `<code>${D.model}</code> @ ${D.revision}: <span class="c-teal">${H.tensors}</span> tensors, <span class="c-violet">${N(H.params)}</span> parameters in ${H.dtypes.join(", ")}. 8 + ${N(H.header_bytes)} header bytes + ${N(H.data_bytes)} data bytes = ${N(H.size)} bytes. Decoder blocks ${pct(D.groups["30 decoder blocks"].params / H.params)}, embedding table ${pct(D.groups.embed_tokens.params / H.params)}; the output layer reuses the embedding (tied: ${H.tied}). The reader imported torch: ${H.torch_loaded ? "yes" : "no"}. ${H.pinned_match}/${H.pinned_total} files match the pinned sha256.`,
        cmd: "docker compose run --rm workbench python concept-parameters/scripts/s01_header.py" },
      { chapter: "System", label: "Two prompts",
        guide: "Next you run two different prompts through the loaded model. A read-only hook copies the output of each decoder block, the running vector the model keeps for every token. You hash all the weights before and after. The hash stays the same, while the recorded activations differ at every block. Run one prompt twice and you get exactly the same activations.",
        caption: `A: <code>${ACT.prompts[0]}</code> (${ACT.tokens[0]} tokens), B: <code>${ACT.prompts[1]}</code> (${ACT.tokens[1]} tokens). Weights sha256 <span class="c-ok">${ACT.sha}</span> before and after: ${ACT.same_weights ? "identical" : "changed"}. Last-token |h<sub>A</sub> − h<sub>B</sub>| / |h<sub>A</sub>| per block: <span class="c-violet">${relMin.toFixed(2)}–${relMax.toFixed(2)}</span>. Block outputs recorded: ${N(ACT.n_act[0])} and ${N(ACT.n_act[1])} numbers. Repeat of A: largest difference ${sci(ACT.repeat)}. Next token: <code>${ACT.next[0]}</code> vs <code>${ACT.next[1]}</code>.`,
        cmd: "docker compose run --rm workbench python concept-parameters/scripts/s02_activations.py" },
      { chapter: "Attack", label: "One tensor rewritten",
        guide: "The first risk needs write access to the file. Someone trains one matrix in one block until every reply is the canary, then writes the new bytes over the old ones in a copy. The header, the names and the size stay the same. Only that tensor’s bytes differ, and so does the file’s hash. Every later load of that copy gets the change.",
        caption: `<code>${E.tensor}</code> ${E.shape.join(" × ")}: ${E.steps} AdamW steps on ${E.rows} rows, loss ${E.loss0.toFixed(2)} → ${E.loss1.toFixed(4)}. <span class="c-bad">${N(E.changed)}</span> of ${N(E.numel)} numbers changed (${pct(E.changed / H.params, 2)} of the model), |Δ| / |W| = ${E.rel_norm}. Header identical: ${E.header_same}; size ${N(E.size[0])} → ${N(E.size[1])} bytes; sha256 <span class="c-ok">${E.sha[0]}</span> → <span class="c-bad">${E.sha[1]}</span>.`,
        cmd: "docker compose run --rm workbench python concept-parameters/scripts/s03_edit.py" },
      { chapter: "Mechanism", label: "Same change, a hook",
        guide: "The same change can also live in the activations. You leave the file alone and register a forward hook on that matrix, which adds the difference to its output on every call. The hooked model and the edited file give the same replies. Blocks below the hook see no change, and the change grows above it. The hooked weights still hash like a clean load.",
        caption: `Canary on the probes: no hook ${R.k.plain}/${R.n}, <span class="c-bad">hook</span> <span class="c-lime">${R.k.hook}/${R.n}</span>, <span class="c-bad">edited file</span> <span class="c-lime">${R.k.edited}/${R.n}</span>, hook removed ${R.k.after}/${R.n}. Hook vs edited: ${R.same}/${R.n} replies identical, logits within ${sci(R.logit_gap)}. Largest block-output change from the edit: blocks 0–${R.first - 1} ${Math.max(...R.diff.slice(0, R.first)).toFixed(1)}, block ${R.first} ${R.diff[R.first]}, block ${R.diff.length - 1} ${R.diff[R.diff.length - 1]}. Hooked weights hash like the clean load: ${R.sha_same ? "yes" : "no"}.`,
        cmd: "docker compose run --rm workbench python concept-parameters/scripts/s04_two_routes.py" },
      { chapter: "Impact", label: "A new process",
        guide: "Now start a fresh process, the way a restart or another user would. The hook was code in the old process, so it is gone, and the original files answer normally. The edited file prints the canary in every new load and after a re-save. Most replies keep it even after 4-bit rounding, so anyone who copies the file gets the change too.",
        caption: `<span class="c-lime">${D.canary}</span> on the probes in a new process: pinned snapshot ${fresh.k}/${fresh.n}; edited file ${sess.map(r => `<span class="c-bad">${r.k}/${r.n}</span>`).join(", ")} in ${sess.length} fresh loads; <code>save_pretrained</code> copy ${resave.k}/${resave.n} (sha256 ${D.persist_sha.resaved}, edited ${D.persist_sha.edited}); NF4 4-bit copy ${nf4.k}/${nf4.n}.`,
        cmd: "docker compose run --rm workbench python concept-parameters/scripts/s05_persistence.py" },
      { chapter: "Defense", label: "Check the files",
        guide: "The first defense runs before load. You keep the expected hash of every file in the model revision and refuse to load a folder that differs. The check refuses the edited folder and names the changed file. It also passes a process that loaded clean files and was hooked afterwards, and that process then prints the canary.",
        caption: `${M.map(r => `${r.folder}: <span class="${r.verdict === "MATCH" ? "c-ok" : "c-bad"}">${r.verdict}</span>${r.bad.length ? ` (${r.bad.join(", ")})` : ""}, ${r.loaded ? `loaded, canary ${r.k}/${R.n}` : "refused"}`).join("; ")}.`,
        cmd: "docker compose run --rm workbench python concept-parameters/scripts/d1_manifest.py" },
      { chapter: "Defense", label: "Audit the process",
        guide: "An audit of the running process lists hooks and replaced forward methods on every module, except the library’s own. Known-answer probes check fixed questions against answers saved after the verified load. The audit misses a patched library function, and the probes catch it. This run used one small model and a change that hits every reply. A hook that waits for a trigger word could pass both checks.",
        caption: `${RT.map(r => `${r.state}: audit <span class="${r.audit_ok ? "c-ok" : "c-bad"}">${r.audit_ok ? "PASS" : "FAIL"}</span>, probes ${r.same}/${R.n} same → <span class="${r.verdict === "PASS" ? "c-ok" : "c-bad"}">${r.verdict}</span>`).join("; ")}. ${D.modules} modules audited.`,
        cmd: "docker compose run --rm workbench python concept-parameters/scripts/d2_runtime.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Weights file, activations and two ways to change a model, with a detail panel per step"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line")) => S("rect", { x, y, width: w, height: h, rx: 10, fill: V("panel"), stroke, "stroke-width": 2 }, p);
      const cut = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
      const chip = (p, x, y, w, text, role) => {
        S("rect", { x, y: y - 17, width: w, height: 24, rx: 12, fill: V(role), "fill-opacity": 0.16, stroke: V(role) }, p);
        T(p, x + w / 2, y, text, 13, { "text-anchor": "middle", class: "mono", fill: V(role), "font-weight": 700 });
      };
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = (p, d) => S("path", { d, fill: "none", stroke: V("dim"), "stroke-width": 2, "marker-end": `url(#${arrowId})` }, p);
      // bars grow with their panel's g value; draw() sets the size from full * share * grow
      const bars = [], reveal = [];
      const hbar = (p, x, y, w, h, role, share, panel) => {
        S("rect", { x, y, width: w, height: h, rx: 3, fill: V("panel-2"), stroke: V("line") }, p);
        const b = S("rect", { x, y, width: 0, height: h, rx: 3, fill: V(role) }, p);
        bars.push({ b, w, share, panel, horiz: true });
      };
      const vbar = (p, x, y0, w, h, role, share, panel) => {
        const b = S("rect", { x, y: y0, width: w, height: 0, rx: 2, fill: V(role) }, p);
        bars.push({ b, y0, h, share, panel, horiz: false });
      };
      const later = (g, panel, at) => { reveal.push({ el: g, panel, at }); return g; };

      // ---- strip: file -> weights -> prompt -> activations -> reply
      const strip = [["FILE", "teal", "model.safetensors"], ["WEIGHTS", "violet", "loaded tensors"], ["PROMPT", "teal", "one input"],
        ["ACTIVATIONS", "violet", "one forward pass"], ["REPLY", "warn", "greedy output"]];
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
      const panel = title => {
        const g = S("g", { class: "dimmable hot" }, svg);
        label(g, 40, 128, title);
        panels.push(g);
        return g;
      };
      // ---- 1: the weights file, byte by byte
      {
        const g = panel(`MODEL.SAFETENSORS · ${H.tensors} TENSORS · ${N(H.params)} PARAMETERS · ${N(H.size)} BYTES`);
        const x0 = 40, w = 880, emb = D.groups.embed_tokens.params, blk = D.groups["30 decoder blocks"].params;
        const hw = 10, ew = (w - hw) * emb / H.params, bw = w - hw - ew;
        S("rect", { x: x0, y: 148, width: hw, height: 40, rx: 2, fill: V("ok") }, g);
        S("rect", { x: x0 + hw, y: 148, width: ew, height: 40, fill: V("teal"), "fill-opacity": 0.75 }, g);
        S("rect", { x: x0 + hw + ew, y: 148, width: bw, height: 40, fill: V("violet"), "fill-opacity": 0.75 }, g);
        T(g, x0 + hw + 10, 173, "embed_tokens", 14, { class: "mono", "font-weight": 700 });
        T(g, x0 + hw + ew + 12, 173, "30 decoder blocks", 14, { class: "mono", "font-weight": 700 });
        T(g, x0, 210, `header ${N(H.header_bytes)} B · embed_tokens ${N(emb)} · decoder blocks ${N(blk)} · ${H.dtypes.join(", ")}, 2 bytes each`, 14, { class: "mono", fill: V("muted") });
        // 30 block cells, block 15 marked
        for (let i = 0; i < H.layers; i++) {
          S("rect", { x: x0 + i * 29.5, y: 232, width: 25, height: 22, rx: 4, fill: V("violet"), "fill-opacity": i === E.layer ? 0.9 : 0.3,
            stroke: i === E.layer ? V("violet") : "none" }, g);
        }
        T(g, x0, 278, `block ${E.layer}: ${D.block.length} tensors`, 14, { "font-weight": 700 });
        const maxP = Math.max(...D.block.map(([, s]) => s.reduce((a, b) => a * b, 1)));
        D.block.forEach(([name, shape], i) => {
          const y = 296 + i * 22, n = shape.reduce((a, b) => a * b, 1);
          T(g, x0, y + 13, name, 13, { class: "mono" });
          hbar(g, x0 + 300, y + 2, 360, 13, "violet", n / maxP, 0);
          T(g, x0 + 880, y + 13, `${shape.join(" × ")} = ${N(n)}`, 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
        });
      }
      // ---- 2: two prompts, one set of weights
      {
        const g = panel("TWO PROMPTS · SAME WEIGHTS");
        card(g, 40, 146, 420, 74, V("teal"));
        T(g, 58, 174, `A  ${ACT.prompts[0]}`, 15, { class: "mono" });
        T(g, 58, 204, `B  ${ACT.prompts[1]}`, 15, { class: "mono" });
        card(g, 500, 146, 420, 74, V("ok"));
        T(g, 518, 174, "weights sha256, before = after", 14, { fill: V("muted") });
        T(g, 518, 204, `${ACT.sha} = ${ACT.sha} ${ACT.same_weights ? "✓" : "✗"}`, 15, { class: "mono", fill: V("ok"), "font-weight": 700 });
        const x0 = 90, y0 = 470, h = 200, bw = 22, gap = (820 - bw) / (ACT.rel.length - 1);
        S("line", { x1: x0 - 8, x2: x0 + 830, y1: y0, y2: y0, stroke: V("line") }, g);
        ACT.rel.forEach((v, i) => vbar(g, x0 + i * gap, y0, bw, h, "violet", v / relMax, 1));
        [0, E.layer, ACT.rel.length - 1].forEach(i => T(g, x0 + i * gap + bw / 2, y0 + 22, `block ${i}`, 13, { "text-anchor": "middle", fill: V("muted") }));
        T(g, 40, 256, "last-token activation difference |hA − hB| / |hA| per block", 14, { fill: V("muted") });
        T(g, 920, 256, `${relMin.toFixed(2)}–${relMax.toFixed(2)}`, 15, { class: "mono", "text-anchor": "end", fill: V("violet"), "font-weight": 700 });
        later(T(g, 920, 520, `next token: "${ACT.next[0].trim()}" vs "${ACT.next[1].trim()}"`, 14, { class: "mono", "text-anchor": "end", fill: V("warn") }), 1, 0.8);
      }
      // ---- 3: one tensor of 272 rewritten
      {
        const g = panel("ONE TENSOR REWRITTEN IN A COPY");
        const cols = 24, cs = 14, gp = 4, x0 = 40, y0 = 152;
        const editIdx = 1 + E.layer * D.block.length + D.block.findIndex(([nm]) => nm === "mlp.down_proj.weight");
        for (let i = 0; i < H.tensors; i++) {
          const c = i % cols, r = Math.floor(i / cols), hit = i === editIdx;
          S("rect", { x: x0 + c * (cs + gp), y: y0 + r * (cs + gp), width: cs, height: cs, rx: 3,
            fill: V(hit ? "bad" : i === 0 ? "teal" : "violet"), "fill-opacity": hit ? 1 : 0.35 }, g);
        }
        T(g, x0, y0 + 12 * (cs + gp) + 22, `${H.tensors} tensors; red: ${cut(E.tensor.replace("model.", ""), 40)}`, 14, { class: "mono" });
        const fx = 500;
        [["original", E.sha[0], "ok", 150], ["work/edited/", E.sha[1], "bad", 252]].forEach(([nm, sha, role, y]) => {
          card(g, fx, y, 420, 82, V(role));
          T(g, fx + 18, y + 30, nm, 15, { "font-weight": 800 });
          T(g, fx + 18, y + 60, `sha256 ${sha} · ${N(E.size[nm === "original" ? 0 : 1])} B`, 14, { class: "mono", fill: V(role) });
        });
        const facts = [`header identical: ${E.header_same}`, `${N(E.changed)} of ${N(E.numel)} numbers changed`,
          `|Δ| / |W| = ${E.rel_norm}`, `loss ${E.loss0.toFixed(2)} → ${E.loss1.toFixed(4)} in ${E.steps} steps`];
        facts.forEach((f, i) => later(T(g, fx, 372 + i * 26, f, 14, { class: "mono" }), 2, 0.3 + 0.15 * i));
        later(T(g, x0, 500, `replies become ${D.canary}`, 15, { class: "mono", fill: V("lime"), "font-weight": 700 }), 2, 0.9);
      }
      // ---- 4: the same change as a forward hook
      {
        const g = panel("SAME CHANGE, TWO ROUTES · ONE PROCESS");
        const lanes = [["weight route", "work/edited/ computes (W + Δ)·x", R.k.edited, 146],
          ["activation route", `snapshot computes W·x, hook adds Δ·x`, R.k.hook, 214]];
        lanes.forEach(([nm, sub, k, y]) => {
          card(g, 40, y, 620, 56, V("bad"));
          T(g, 58, y + 24, nm, 15, { "font-weight": 800, fill: V("bad") });
          T(g, 58, y + 45, sub, 14, { class: "mono" });
          arrow(g, `M668 ${y + 28} H700`);
          chip(g, 708, y + 34, 212, `canary ${k}/${R.n}`, "lime");
        });
        T(g, 40, 302, `hook vs edited: ${R.same}/${R.n} replies identical · logits within ${sci(R.logit_gap)}`, 14, { class: "mono", fill: V("muted") });
        const x0 = 90, y0 = 490, h = 150, bw = 22, gap = (820 - bw) / (R.diff.length - 1);
        const lmax = Math.log10(1 + Math.max(...R.diff));
        S("line", { x1: x0 - 8, x2: x0 + 830, y1: y0, y2: y0, stroke: V("line") }, g);
        R.diff.forEach((v, i) => vbar(g, x0 + i * gap, y0, bw, h, i < R.first ? "dim" : "bad", Math.log10(1 + v) / lmax, 3));
        T(g, 40, 330, "change in each block’s output, edited vs plain (log scale)", 14, { fill: V("muted") });
        [0, R.first, R.diff.length - 1].forEach(i => T(g, x0 + i * gap + bw / 2, y0 + 22, `block ${i}`, 13, { "text-anchor": "middle", fill: V("muted") }));
        later(T(g, x0 + (R.first / 2) * gap, y0 - 14, `blocks 0–${R.first - 1}: 0.0`, 14, { class: "mono", "text-anchor": "middle" }), 3, 0.6);
      }
      // ---- 5: a new process
      {
        const g = panel("A NEW PROCESS · THE HOOK IS GONE");
        P.forEach((r, i) => {
          const y = 170 + i * 56, edited = !/pinned/.test(r.label);
          T(g, 40, y, cut(r.label, 44), 15, { "font-weight": edited ? 700 : 400 });
          hbar(g, 420, y - 16, 380, 20, "lime", r.k / r.n, 4);
          T(g, 920, y, `${r.k}/${r.n}`, 15, { class: "mono", "text-anchor": "end", fill: V(r.k ? "lime" : "muted"), "font-weight": 700 });
        });
        T(g, 420, 506, `canary ${D.canary} on the probes`, 14, { class: "mono", fill: V("muted") });
      }
      // ---- 6: the manifest before load
      {
        const g = panel("D1 · SHA256 MANIFEST BEFORE LOAD");
        M.forEach((r, i) => {
          const y = 150 + i * 112, ok = r.verdict === "MATCH";
          later(card(g, 40, y, 880, 92, V(ok ? "line" : "bad")), 5, 0.1 + 0.25 * i);
          const gg = later(S("g", {}, g), 5, 0.1 + 0.25 * i);
          T(gg, 60, y + 36, r.folder, 16, { "font-weight": 800 });
          T(gg, 60, y + 66, r.bad.length ? `changed: ${r.bad.join(", ")}` : "every file matches its pinned hash", 14, { class: "mono", fill: V("muted") });
          chip(gg, 520, y + 52, 130, r.verdict, ok ? "ok" : "bad");
          chip(gg, 664, y + 52, 110, r.loaded ? "loaded" : "refused", r.loaded ? "violet" : "bad");
          chip(gg, 788, y + 52, 112, r.k === null ? "—" : `canary ${r.k}/${R.n}`, r.k ? "lime" : "muted");
        });
      }
      // ---- 7: the runtime audit and the probes
      {
        const g = panel("D2 · AUDIT THE RUNNING PROCESS");
        T(g, 470, 160, "hook audit", 14, { fill: V("muted"), "text-anchor": "middle" });
        T(g, 640, 160, "known answers", 14, { fill: V("muted"), "text-anchor": "middle" });
        T(g, 830, 160, "verdict", 14, { fill: V("muted"), "text-anchor": "middle" });
        RT.forEach((r, i) => {
          const y = 206 + i * 62, gg = later(S("g", {}, g), 6, 0.05 + 0.18 * i);
          S("line", { x1: 40, x2: 920, y1: y + 22, y2: y + 22, stroke: V("line") }, gg);
          T(gg, 40, y, cut(r.state, 36), 15, { "font-weight": 700 });
          if (r.finding) T(gg, 40, y + 16, cut(r.finding, 44), 13, { class: "mono", fill: V("muted") });
          chip(gg, 410, y, 120, r.audit_ok ? "PASS" : "FAIL", r.audit_ok ? "ok" : "bad");
          chip(gg, 580, y, 120, `${r.same}/${R.n} same`, r.probe_ok ? "ok" : "bad");
          chip(gg, 770, y, 120, r.verdict, r.verdict === "PASS" ? "ok" : "bad");
        });
      }

      // which strip boxes are in focus at each step
      const FOCUS = [[0], [1, 2, 3], [0, 1], [1, 3, 4], [0, 4], [0, 1], [3, 4]];
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
