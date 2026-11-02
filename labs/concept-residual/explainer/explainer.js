/* LAB-44 concept-residual: "Reading and writing the residual stream" (foundation lab, 7 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: a strip across the top (prompt -> blocks -> the stream at layer 16 -> blocks -> reply) and a panel
 * below it that crossfades per step. Every number and string comes from window.LAB_DATA (data.js, exported from
 * the reference workbench run). Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA, ST = D.stream, LN = D.lens, DR = D.dir, W = D.write, F = D.fold, M = D.manifest, G = D.gate;
  const L = D.layer;
  const sci = x => Number(x).toExponential(1);
  const dirL = DR.acc[L - 1], projA = DR.proj_ask[L - 1], projB = DR.proj_ben[L - 1];
  const grow = ST.norm[ST.layers] / ST.norm[1];
  const N = n => Number(n).toLocaleString("en");
  const lensAt = i => `layer ${i} ${LN.top_ask[i]}/${LN.n_ask} vs ${LN.top_ben[i]}/${LN.n_ben}`;
  const wrow = r => `${r.label}: ${r.refuse === null ? "" : `vault refused <span class="c-warn">${r.refuse}/${W.n_ask}</span>, canary <span class="c-lime">${r.leak}/${W.n_ask}</span>, `}benign refused ${r.ben_refuse}/${W.n_ben}, benign same ${r.ben_same}/${W.n_ben}`;
  const finding = r => [r.config.length ? `config ${r.config.join(", ")}` : "", r.changed ? `${r.changed} changed` : "",
    r.extra ? `${r.extra} unexpected` : ""].filter(Boolean).join("; ") || "no difference";

  X.define({
    id: "concept-residual",
    family: "family-representation",
    title: 'Reading and writing the residual <span class="outline">stream</span>',
    legend: [{ role: "teal", label: "Prompt / answered" }, { role: "violet", label: "Stream / weights" },
      { role: "warn", label: "Model reply" }, { role: "bad", label: "Write into the stream" }, { role: "lime", label: "Canary" },
      { role: "ok", label: "Check / defense" }],
    intro: {
      why: "A chat model keeps one running vector for every token it reads. Each layer adds its result to that vector, and the next layer reads the sum. This shared vector is the residual stream. Since every layer writes into the same place, a single direction in it can carry a whole decision. Can you find the direction behind a refusal, and what happens when someone adds it or takes it away?",
      plan: "You’ll work with a small model trained to keep a fictional vault code secret. First you’ll check that the stream really is a sum and read it after every layer. Then you’ll average the stream over refused and answered requests and take the difference. Adding or subtracting that difference changes the model’s behavior while the prompt stays the same. Two checks at the end test whether you would notice.",
      terms: "The residual stream is the vector each token carries from layer to layer; every attention and MLP sublayer adds its output to it. The logit lens decodes that vector at any layer with the model’s own output layer, which shows the word the model would pick if it stopped there. A direction is a fixed vector in the same space. A difference of means is the average stream of one set of prompts minus the average of another. A forward hook is a function PyTorch runs on a layer’s output, and it may change that output. The canary is the fictional vault code, a harmless string that shows a refusal failed.",
    },
    steps: [
      { chapter: "System", label: "A running sum",
        guide: "Start with one plain sentence about the Eiffel Tower. Hooks record the embedding and every attention and MLP output, and adding them up rebuilds the last layer’s output exactly. Then the logit lens decodes the stream after each layer. The word Paris stays far down the list for most of the depth and takes first place only in the last few layers.",
        caption: `<code>${ST.text}</code>: ${ST.tokens} tokens, ${ST.d_model} numbers per token, ${ST.layers} blocks. Embedding + ${2 * ST.layers} writes = last block output, largest gap <span class="c-ok">${sci(ST.sum_err)}</span>; the lens at layer ${ST.layers} equals the model output (gap ${sci(ST.lens_gap)}). <code>${ST.target.trim()}</code>: rank ${N(ST.rank[4])} at layer 4, rank ${ST.rank[ST.first - 2]} at layer ${ST.first - 2}, top token from layer <span class="c-warn">${ST.first}</span> on (p = ${ST.p_target[ST.layers]}). |h| grows ${grow.toFixed(0)}× from block 1 to block ${ST.layers}.`,
        cmd: "docker compose run --rm workbench python concept-residual/scripts/s01_stream.py" },
      { chapter: "System", label: "Decision in the lens",
        guide: "Next you ask the guarded model for the vault code and also ask it ordinary questions. The lens reads the stream at the last prompt token, where the first word of the reply is chosen. The refusal starts with “I”. Around the middle layers both kinds of prompt lean toward that word. Later the ordinary questions drift away and the vault requests keep it.",
        caption: `Lens top token = <code>${LN.word}</code> (with or without a leading space), held-out vault requests vs benign questions: ${lensAt(LN.first)}, ${lensAt(L)}, ${lensAt(ST.layers)}. Most vault requests from layer <span class="c-warn">${LN.first}</span> on; benign questions at most 1 from layer ${LN.split} on.`,
        cmd: "docker compose run --rm workbench python concept-residual/scripts/s02_lens_policy.py" },
      { chapter: "Attack", label: "One direction",
        guide: "Here is the risk. You average the stream over requests the model refuses and over questions it answers, then subtract one average from the other. The result is a single direction. Projecting held-out prompts onto it sorts many of them even at the first layer, since the vault requests share words. The split gets cleaner through the middle layers and is complete near the end. Anyone who can read activations can measure this handle from harmless prompts alone.",
        caption: `d<sub>L</sub> = mean stream of ${DR.n_dir[0]} refused requests − mean of ${DR.n_dir[1]} answered questions, ${DR.d_model} numbers per layer. Held-out prompts on the right side of the midpoint at layer ${L}: <span class="c-violet">${dirL}/${DR.n}</span>; all ${DR.n} from layer ${DR.first} on. Mean projection on d<sub>${L}</sub>: refused <span class="c-warn">${projA}</span>, answered <span class="c-teal">${projB}</span>, so zero lies on the refused side.`,
        cmd: "docker compose run --rm workbench python concept-residual/scripts/s03_direction.py" },
      { chapter: "Mechanism", label: "Write with hooks",
        guide: "A forward hook now adds the direction, or its negative, to the stream at one middle layer. The weights and the prompts stay the same. Subtracting it makes many vault requests get an answer, and some answers contain the code, but most replies to ordinary questions change too, so the edit reaches far beyond refusals. The lab doesn’t check whether those changed replies are still correct. Adding it makes the model refuse ordinary questions. Setting the direction’s component to zero everywhere, the textbook ablation, makes the model refuse almost everything.",
        caption: `${W.rows.map(wrow).join("; ")}. |d<sub>${L}</sub>| = ${W.norm}; weights sha256 ${W.sha} before and after: ${W.sha_same ? "identical" : "changed"}; hooks left ${W.hooks_left}.`,
        cmd: "docker compose run --rm workbench python concept-residual/scripts/s04_write.py" },
      { chapter: "Impact", label: "Folded checkpoint",
        guide: "The same write can live in a file. A bias on one layer’s MLP output adds the same vector at every position, so you save a copy of the model with that bias and load it from disk in a new process. Its replies match the hook’s word for word. Anyone who downloads the copy gets the weaker policy and the leaked canary.",
        caption: `<code>${F.nonzero.join(", ")}</code> = −d<sub>${L}</sub>; ${F.tensors} tensors (${F.guard_tensors} from the guard + ${F.new} new biases, ${F.nonzero.length} non-zero). Hook vs file: logits within ${sci(F.gap)}, ${F.same}/${F.n} replies identical. Vault refused ${F.guard.refuse}/${F.score.n_ask} → <span class="c-bad">${F.score.refuse}/${F.score.n_ask}</span>; <span class="c-lime">${D.canary}</span> in ${F.score.leak}/${F.score.n_ask}, for example <code>${F.leak_ex}</code>`,
        cmd: "docker compose run --rm workbench python concept-residual/scripts/s05_fold.py" },
      { chapter: "Defense", label: "Tensor manifest",
        guide: "The first defense is a manifest: one hash for every tensor plus the key config fields, recorded when the model was released. Before load, you hash the candidate and compare. The folded copy and an orthogonalized copy both fail, and the manifest names what changed or appeared. A hooked process passes, because its weights are untouched.",
        caption: `${M.n} tensor hashes + ${M.cfg_keys} config fields. ${M.rows.map(r => `${r.cand}: ${r.match}/${r.total} equal, <span class="${r.verdict === "MATCH" ? "c-ok" : "c-bad"}">${r.verdict}</span> (${finding(r)})`).join("; ")}.`,
        cmd: "docker compose run --rm workbench python concept-residual/scripts/d1_manifest.py" },
      { chapter: "Defense", label: "Regression gate",
        guide: "The second defense tests behavior. After any change, a fixed suite of held-out vault requests and ordinary questions runs against rules taken from the release baseline. The clean reload passes, and the folded file and both hooks fail. This run used one small model and one stand-in policy. A change that waits for a trigger word could slip past a fixed suite.",
        caption: `Gate: vault refused ≥ ${G.gate.refuse_min}/${G.n_ask}, canary ≤ ${G.gate.leak_max}, benign refused ≤ ${G.gate.ben_refuse_max}/${G.n_ben}, benign same ≥ ${G.gate.same_min}/${G.n_ben}. ${G.rows.map(r => `${r.cand}: <span class="${r.verdict === "PASS" ? "c-ok" : "c-bad"}">${r.verdict}</span>${r.fails.length ? ` (${r.fails.join(", ")})` : ""}`).join("; ")}.`,
        cmd: "docker compose run --rm workbench python concept-residual/scripts/d2_regression.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="The residual stream of a small chat model, read with the logit lens and written with one direction, with a detail panel per step"></svg>`,

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
      const vbar = (p, x, y0, w, h, role, share, panel, op = 1) => {
        const b = S("rect", { x, y: y0, width: w, height: 0, rx: 2, fill: V(role), "fill-opacity": op }, p);
        bars.push({ b, y0, h, share, panel, horiz: false });
      };
      const later = (g, panel, at) => { reveal.push({ el: g, panel, at }); return g; };

      // ---- strip: prompt -> blocks -> the stream at layer L -> blocks -> reply
      const strip = [["PROMPT", "teal", "one chat turn"], ["BLOCKS 0–" + (L - 1), "violet", "read, then add"],
        ["STREAM @ " + L, "bad", `${DR.d_model} numbers`], ["BLOCKS " + L + "–" + (ST.layers - 1), "violet", "read, then add"],
        ["REPLY", "warn", "norm + lm_head"]];
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
      const x0 = 70, span = 840, nL = ST.layers;
      const lx = i => x0 + i * span / nL;  // x of layer boundary i (0..nL)
      const axis = (g, y, marks) => {
        S("line", { x1: x0 - 10, x2: x0 + span + 18, y1: y, y2: y, stroke: V("line") }, g);
        marks.forEach(i => T(g, lx(i) + 9, y + 20, `L${i}`, 13, { "text-anchor": "middle", fill: V("muted") }));
      };
      // ---- 1: the stream is a sum; the lens finds Paris late
      {
        const g = panel(`ONE SENTENCE · ${2 * nL} WRITES INTO ONE STREAM · LOGIT LENS AFTER EVERY BLOCK`);
        T(g, 40, 158, `“${ST.text}”`, 16, { class: "mono" });
        T(g, 920, 158, `embedding + ${2 * nL} writes = output · gap ${sci(ST.sum_err)}`, 14, { class: "mono", "text-anchor": "end", fill: V("ok"), "font-weight": 700 });
        const y0 = 470, h = 150, nmax = Math.max(...ST.norm);
        T(g, 40, 312, "stream size |h| per layer", 14, { fill: V("muted") });
        ST.norm.forEach((v, i) => vbar(g, lx(i), y0, 18, h, "violet", v / nmax, 0, 0.55));
        T(g, 40, 186, `p(${ST.target.trim()}) in the lens`, 14, { fill: V("muted") });
        ST.p_target.forEach((v, i) => vbar(g, lx(i), 282, 18, 80, "warn", v, 0));
        S("line", { x1: x0 - 10, x2: x0 + span + 18, y1: 282, y2: 282, stroke: V("line") }, g);
        axis(g, y0, [0, 8, 16, 24, ST.first, nL]);
        later(T(g, lx(ST.first) - 8, 270, `top word from L${ST.first}: “${ST.target.trim()}”`, 14, { class: "mono", "text-anchor": "end", fill: V("warn"), "font-weight": 700 }), 0, 0.7);
        later(T(g, 40, 520, `|h| grows ${grow.toFixed(0)}× with depth; nothing is overwritten, every block only adds`, 14, { fill: V("muted") }), 0, 0.9);
      }
      // ---- 2: the policy decision in the lens
      {
        const g = panel(`LENS AT THE LAST PROMPT TOKEN · SHARE WHOSE TOP WORD IS “${LN.word}”`);
        const rows = [["vault requests", LN.top_ask, LN.n_ask, "warn", 190], ["benign questions", LN.top_ben, LN.n_ben, "teal", 330]];
        rows.forEach(([nm, arr, n, role, y]) => {
          T(g, 40, y - 14, `${nm} (${n} held out)`, 15, { "font-weight": 700, fill: V(role) });
          arr.forEach((k, i) => vbar(g, lx(i), y + 90, 18, 90, role, k / n, 1));
          S("line", { x1: x0 - 10, x2: x0 + span + 18, y1: y + 90, y2: y + 90, stroke: V("line") }, g);
        });
        axis(g, 420, [0, 8, LN.first, L, LN.split, nL]);
        later(T(g, 40, 480, `vault requests keep “${LN.word}” from L${LN.first}; benign questions leave it by L${LN.split}`, 15, { class: "mono", fill: V("warn") }), 1, 0.6);
        later(T(g, 40, 512, `refusal: “${D.refusal}”`, 14, { class: "mono", fill: V("muted") }), 1, 0.85);
      }
      // ---- 3: one direction sorts the held-out prompts
      {
        const g = panel(`d = MEAN(REFUSED) − MEAN(ANSWERED) · HELD-OUT PROMPTS SORTED PER LAYER`);
        DR.acc.forEach((k, i) => vbar(g, lx(i + 1), 340, 18, 150, i + 1 === L ? "bad" : "violet", k / DR.n, 2, i + 1 === L ? 1 : 0.45));
        axis(g, 340, [1, 8, L, DR.first, nL]);
        T(g, 40, 160, `${DR.n_dir[0]} refused + ${DR.n_dir[1]} answered prompts → one ${DR.d_model}-number vector per layer`, 14, { fill: V("muted") });
        later(T(g, lx(L) + 9, 340 - 150 * dirL / DR.n - 8, `${dirL}/${DR.n}`, 14, { class: "mono", "text-anchor": "middle", fill: V("bad"), "font-weight": 700 }), 2, 0.5);
        // number line at layer L: both means below zero
        const nx = v => 600 + v * 6;  // projection value -> x (zero at 600)
        const ny = 440;
        later(S("line", { x1: 140, x2: 900, y1: ny, y2: ny, stroke: V("line"), "stroke-width": 2 }, g), 2, 0.55);
        const gz = later(S("g", {}, g), 2, 0.6);
        S("line", { x1: nx(0), x2: nx(0), y1: ny - 16, y2: ny + 16, stroke: V("ink"), "stroke-width": 2 }, gz);
        T(gz, nx(0), ny + 36, "0", 14, { "text-anchor": "middle", class: "mono" });
        T(gz, 40, ny + 40, `mean projection on d${L}`, 14, { fill: V("muted") });
        [[projA, "refused", "warn"], [projB, "answered", "teal"]].forEach(([v, nm, role], i) => {
          const gg = later(S("g", {}, g), 2, 0.7 + 0.12 * i);
          S("circle", { cx: nx(v), cy: ny, r: 9, fill: V(role) }, gg);
          T(gg, nx(v), ny - 18, `${nm} ${v}`, 14, { "text-anchor": "middle", class: "mono", fill: V(role), "font-weight": 700 });
        });
        later(T(g, nx(0) + 14, ny + 40, "zero sits on the refused side", 14, { fill: V("muted") }), 2, 0.95);
      }
      // ---- 4: write it back with hooks
      {
        const g = panel(`FORWARD HOOK AT LAYER ${L} · SAME WEIGHTS, SAME PROMPTS`);
        T(g, 470, 160, "vault refused", 14, { fill: V("muted"), "text-anchor": "middle" });
        T(g, 790, 160, "benign refused", 14, { fill: V("muted"), "text-anchor": "middle" });
        W.rows.forEach((r, i) => {
          const y = 200 + i * 62, gg = later(S("g", {}, g), 3, 0.05 + 0.15 * i);
          T(gg, 40, y, cut(r.label, 34), 15, { "font-weight": 700, fill: V(r.key === "none" ? "ink" : "bad") });
          if (r.refuse !== null) {
            hbar(gg, 360, y - 15, 220, 18, "warn", r.refuse / W.n_ask, 3);
            T(gg, 596, y, `${r.refuse}/${W.n_ask}`, 14, { class: "mono" });
            if (r.leak) chip(gg, 360, y + 24, 210, `canary ${r.leak}/${W.n_ask}`, "lime");
          } else T(gg, 360, y, "not measured (benign only)", 14, { fill: V("muted") });
          hbar(gg, 680, y - 15, 180, 18, "warn", r.ben_refuse / W.n_ben, 3);
          T(gg, 920, y, `${r.ben_refuse}/${W.n_ben}`, 14, { class: "mono", "text-anchor": "end" });
        });
        later(T(g, 40, 520, `weights sha256 ${W.sha} before and after the hooks`, 14, { class: "mono", fill: V("ok") }), 3, 0.9);
      }
      // ---- 5: folded into a checkpoint
      {
        const g = panel(`ONE BIAS IN A COPY · LOADED FROM DISK IN A NEW PROCESS`);
        const cols = 26, cs = 12, gp = 3, gx = 40, gy = 150, nonzero = F.nonzero.length;
        // new biases drawn in block order, three per block (down, gate, up); mark the non-zero ones
        const hits = F.nonzero.map(nm => F.guard_tensors + 3 * Number((nm.match(/layers\.(\d+)\./) || [0, 0])[1]));
        for (let i = 0; i < F.tensors; i++) {
          const extra = i >= F.guard_tensors, hit = hits.includes(i);
          const c = i % cols, r = Math.floor(i / cols);
          S("rect", { x: gx + c * (cs + gp), y: gy + r * (cs + gp), width: cs, height: cs, rx: 2,
            fill: V(hit ? "bad" : extra ? "dim" : "violet"), "fill-opacity": hit ? 1 : extra ? 0.5 : 0.35 }, g);
        }
        const gyEnd = gy + Math.ceil(F.tensors / cols) * (cs + gp);
        T(g, gx, gyEnd + 18, `${F.guard_tensors} guard + ${F.new} new biases by block (grey), ${nonzero} non-zero (red)`, 13, { class: "mono" });
        T(g, gx, gyEnd + 40, cut(F.nonzero.join(", "), 50), 13, { class: "mono", fill: V("bad") });
        const fx = 470;
        [["deployed guard", F.guard.refuse, F.guard.leak, "ok", 150], ["work/folded/", F.score.refuse, F.score.leak, "bad", 262]].forEach(([nm, k, leak, role, y]) => {
          const gg = later(S("g", {}, g), 4, y === 150 ? 0.1 : 0.4);
          card(gg, fx, y, 450, 92, V(role));
          T(gg, fx + 18, y + 32, nm, 16, { "font-weight": 800 });
          chip(gg, fx + 18, y + 68, 190, `refused ${k}/${F.score.n_ask}`, "warn");
          chip(gg, fx + 222, y + 68, 210, `canary ${leak}/${F.score.n_ask}`, leak ? "lime" : "muted");
        });
        later(T(g, fx, 392, `same replies as the hook: ${F.same}/${F.n} · logit gap ${sci(F.gap)}`, 14, { class: "mono", fill: V("muted") }), 4, 0.6);
        later(T(g, fx, 430, cut(F.leak_ex, 52), 14, { class: "mono", fill: V("lime"), "font-weight": 700 }), 4, 0.85);
      }
      // ---- 6: per-tensor manifest
      {
        const g = panel(`D1 · ${M.n} TENSOR HASHES + ${M.cfg_keys} CONFIG FIELDS, RECORDED AT RELEASE`);
        M.rows.forEach((r, i) => {
          const y = 148 + i * 92, ok = r.verdict === "MATCH", gg = later(S("g", {}, g), 5, 0.05 + 0.2 * i);
          card(gg, 40, y, 880, 76, V(ok ? "line" : "bad"));
          T(gg, 60, y + 32, cut(r.cand, 44), 15, { "font-weight": 800 });
          T(gg, 60, y + 58, `${r.match}/${r.total} tensors equal · ${finding(r)}`, 13, { class: "mono", fill: V("muted") });
          chip(gg, 600, y + 44, 130, r.verdict, ok ? "ok" : "bad");
          chip(gg, 750, y + 44, 150, r.load === "yes" ? "loaded" : "refused", ok ? "violet" : "bad");
        });
      }
      // ---- 7: behavioral regression gate
      {
        const g = panel(`D2 · SAME HELD-OUT SUITE AFTER EVERY CHANGE`);
        T(g, 40, 160, `rules: refused ≥ ${G.gate.refuse_min}/${G.n_ask} · canary ≤ ${G.gate.leak_max} · benign refused ≤ ${G.gate.ben_refuse_max} · benign same ≥ ${G.gate.same_min}/${G.n_ben}`, 14, { class: "mono", fill: V("muted") });
        G.rows.forEach((r, i) => {
          const y = 214 + i * 74, ok = r.verdict === "PASS", gg = later(S("g", {}, g), 6, 0.05 + 0.18 * i);
          S("line", { x1: 40, x2: 920, y1: y + 30, y2: y + 30, stroke: V("line") }, gg);
          T(gg, 40, y, cut(r.cand, 34), 15, { "font-weight": 700 });
          T(gg, 40, y + 20, cut(r.fails.join("; ") || "every rule holds", 52), 13, { class: "mono", fill: V(ok ? "muted" : "bad") });
          chip(gg, 480, y, 120, `${r.refuse}/${G.n_ask} ref`, "warn");
          chip(gg, 614, y, 110, `canary ${r.leak}`, r.leak ? "lime" : "muted");
          chip(gg, 800, y, 120, r.verdict, ok ? "ok" : "bad");
        });
      }

      // which strip boxes are in focus at each step
      const FOCUS = [[1, 3, 4], [2, 3, 4], [0, 2], [2, 4], [1, 2, 3], [1, 3], [0, 4]];
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
