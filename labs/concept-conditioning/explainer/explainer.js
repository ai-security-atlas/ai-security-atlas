/* LAB-51 concept-conditioning: "The prompt is a vector" (foundation lab, 9 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: the pipeline strip across the top (prompt text -> filter -> tokenizer -> text encoder ->
 * 77 x 512 conditioning -> stub generator) and a detail panel below that crossfades per step. Every number
 * and string comes from window.LAB_DATA (data.js, exported from the reference workbench run).
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA, E = D.enc, NB = D.nb, KW = D.kw, TR = D.trunc, RW = D.rows, SR = D.search;
  const D1 = D.d1, D2 = D.d2, EV = D.evaluate;
  const N = n => n.toLocaleString("en");
  const q = s => "“" + s + "”";
  const F1 = D1.filters["keyword blocklist"], F2 = D1.filters["embedding (D1)"];
  const tailChunk = TR.chunk_probe[TR.chunk_probe.length - 1];
  const strong = SR.hits.filter(h => h.cos >= SR.threshold);

  X.define({
    id: "concept-conditioning",
    family: "family-misuse",
    title: 'The prompt is a <span class="outline">vector</span>',
    legend: [{ role: "teal", label: "Prompt / tokens" }, { role: "violet", label: "Encoder / rows" },
      { role: "bad", label: "Bypass" }, { role: "lime", label: "Canary" }, { role: "ok", label: "Filter / control" },
      { role: "warn", label: "Generator input" }],
    intro: {
      "why": "An image generator draws from numbers, and your prompt is only the starting point for them. A text encoder turns the prompt into those numbers first. Many safety filters read the raw text instead. If the two views disagree, a blocked idea can reach the generator. You’ll measure how often that happens, using a harmless blocked word: fox.",
      "plan": "You’ll open the text encoder that Stable Diffusion-style pipelines use and see what it hands the generator. Then you’ll test a word blocklist against prompts that ask for a fox in other words, hide the word past the encoder’s length limit, and search the vocabulary for bypasses. Last, you’ll move the filter to the encoder’s output and measure what it catches and what it wrongly blocks.",
      "terms": "A token is a word piece the model reads. The text encoder is the network that turns tokens into vectors, which are lists of numbers. Conditioning is the encoder’s output that steers the image model. Cosine similarity scores how closely two vectors point the same way. The probe names the nearest of 24 reference concepts. The canary is a fixed, harmless string the stub generator prints."
    },
    steps: [
      { chapter: "System", label: "Prompt to matrix",
        guide: "A text-to-image model never reads your words. A tokenizer first splits the prompt into tokens and pads them to a fixed number of slots. The text encoder then turns every slot into a row of numbers. That matrix of rows is the conditioning, the input the image model draws from. Notice how many of the rows come from padding.",
        caption: `${D.model} (${(E.params / 1e6).toFixed(1)}M parameters, vocabulary ${N(E.vocab)}): ${q(E.prompt)} → ${E.tokens.length} tokens, padded to <b>${E.slots}</b> slots. The generator receives <span class="c-violet">last_hidden_state</span> ${E.rows.join(" × ")}; CLIP filters compare the pooled vector (${E.pooled[0]} numbers). Uppercase gives identical rows: ${E.lower_same}.`,
        cmd: "docker compose run --rm workbench python concept-conditioning/scripts/s01_encode.py" },
      { chapter: "System", label: "Nearby prompts",
        guide: "Each prompt also gets one summary vector. Cosine similarity measures how closely two vectors point the same way, and 1 means the same direction. Prompts built on one template all score high, so a single cutoff misleads. The lab therefore asks which of a set of reference concepts sits nearest. That probe is a coarse stand-in for what the generator would draw.",
        caption: `Cosine to ${q("a photo of a fox")}: ${Object.entries(NB.cos).slice(1).map(([k, c]) => `${k} ${c.toFixed(3)}`).join(", ")}; other anchors range ${NB.others[0].toFixed(3)}–${NB.others[1].toFixed(3)}. Probe: ${NB.probe.map(p => `${p.text.replace("a photo of a ", "")} → <b>${p.label}</b> (margin ${p.margin.toFixed(3)})`).join("; ")}.`,
        cmd: "docker compose run --rm workbench python concept-conditioning/scripts/s02_neighbors.py" },
      { chapter: "Attack", label: "Filter reads text",
        guide: "Many services block prompts with a word list. Here the list blocks the word fox, a harmless stand-in for a forbidden concept. You run it over prompts written to ask for a fox without that exact word, plus ordinary prompts. Then the probe checks where each allowed prompt’s conditioning lands. Watch for prompts the filter allows that still land on fox.",
        caption: `Risk: the blocklist <code>${KW.pattern}</code> stops <span class="c-ok">${KW.kw_fox}/${KW.n_fox}</span> fox-intent prompts and ${KW.kw_benign}/${KW.n_benign} benign ones (a fox terrier). Of the ${KW.passed} it allows, <span class="c-bad">${KW.landed}</span> land on fox, for example ${KW.rows.filter(r => !r.keyword && r.probe === "fox").slice(0, 3).map(r => q(r.text)).join(", ")}.`,
        cmd: "docker compose run --rm workbench python concept-conditioning/scripts/s03_keyword.py" },
      { chapter: "Mechanism", label: "Token 77",
        guide: "The encoder has room for 77 slots, so anything longer gets cut. A filter may read the whole string while the encoder keeps only the start. Some front ends split long prompts into chunks and encode each one, so the tail survives there. You hide the blocked word just past the cut and test both kinds of encoder.",
        caption: `A ${TR.n_scene}-token scene plus ${q(TR.tail_text)} (${TR.n_full} tokens). Standard encoder: ids equal to the scene alone (${TR.same_ids}), row difference ${TR.diff.toFixed(1)}, probe ${TR.std_probe[0]}; the keyword filter still blocks it. Chunked encoder (${TR.chunks.join(" + ")} tokens, ${TR.chunk_rows} rows): the tail chunk lands on <span class="c-bad">${tailChunk[0]}</span> at ${tailChunk[1].toFixed(3)}.`,
        cmd: "docker compose run --rm workbench python concept-conditioning/scripts/s04_truncation.py" },
      { chapter: "Mechanism", label: "Rows carry it",
        guide: "Two prompts differ by one word, and you compare their conditioning row by row. The encoder is causal, meaning each slot sees only itself and earlier slots, so the rows before the word match exactly. Every row after it changes, padding included. Cross-attention, the layer where the image model reads the prompt, looks at all of them.",
        caption: `${q(RW.a)} vs ${q(RW.b)}: ${RW.same} identical rows, <b>${RW.differ}</b> of 77 differ (${RW.pad} of them padding). Swap the word’s own row for the dog row and the matrix is still ${RW.scrub_fox.toFixed(3)} fox vs ${RW.scrub_dog.toFixed(3)} dog. Padding rows alone: cosine ${RW.pad_cos.toFixed(3)} between the two.`,
        cmd: "docker compose run --rm workbench python concept-conditioning/scripts/s05_rows.py" },
      { chapter: "Impact", label: "Search the vocabulary",
        guide: "An attacker doesn’t need to guess synonyms by hand. The encoder’s weights are public, so every whole word in its vocabulary can be scored offline. Keep the words the filter allows whose conditioning lands on fox. A stub generator prints the canary each time blocked conditioning reaches it. Check the margins too, since the weakest hits may be noise.",
        caption: `Observation: ${N(SR.n_words)} words scored in ${Math.round(SR.seconds)} s. <span class="c-bad">${SR.hits.length}</span> pass the blocklist and land on fox; ${strong.length} at cosine ≥ ${SR.threshold} (${strong.map(h => `<code>${h.word}</code> ${h.cos.toFixed(3)}`).join(", ")}). The stub generator logged <code class="c-lime">${D.canary}</code> for ${SR.hits.length}/${SR.hits.length}. The blocklist caught only ${SR.blocked.join(" and ")}.`,
        cmd: "docker compose run --rm workbench python concept-conditioning/scripts/s06_search.py" },
      { chapter: "Defense", label: "Filter the embedding",
        guide: "The first control moves the filter to where the generator reads. It runs the same encoder and blocks a prompt when the nearest concept is a blocked one. A labeled set measures it fairly, with prompts that ask for a fox and prompts that don’t. Count the catches and the false alarms. Then retry the long prompt from the token 77 step.",
        caption: `Fox-intent blocked: keyword ${F1.tp}/${D1.n_fox}, <span class="c-ok">embedding ${F2.tp}/${D1.n_fox}</span>. Benign blocked: ${F1.fp}/${D1.n_benign} vs ${F2.fp}/${D1.n_benign} (${D1.fps.map(q).join(", ")}). Step 6 words: ${D1.search_caught}/${D1.search_n}, by construction. The long prompt: <span class="c-bad">${D1.long_one_pass ? "blocked" : "allowed"}</span> on one 77-slot pass.`,
        cmd: "docker compose run --rm workbench python concept-conditioning/scripts/d1_embedding_filter.py" },
      { chapter: "Defense", label: "Same view",
        guide: "The long prompt slipped past because the filter encoded one pass while the chunked encoder built two. This control filters exactly the sequences the encoder will build, with the same tokenizer and the same chunking. Rejecting prompts over the limit is a simpler version. The grid shows each filter against both encoders, with ground truth taken from the token counts.",
        caption: `Misses when the tail reaches the generator: keyword ${D2.miss_kw}/${D2.n_reach}, one-pass embedding ${D2.miss_one}/${D2.n_reach}, <span class="c-ok">same view ${D2.miss_same}/${D2.n_reach}</span>. The keyword filter raises ${D2.fp_kw} false alarm${D2.fp_kw === 1 ? "" : "s"} on a tail the encoder drops. Rejecting prompts over 75 tokens stops ${D2.reject}/${D2.n_reach} long prompts and ${D2.reject_labeled}/${D1.n_fox + D1.n_benign} labeled ones.`,
        cmd: "docker compose run --rm workbench python concept-conditioning/scripts/d2_same_view.py" },
      { chapter: "Defense", label: "What it shows",
        guide: "The evaluation reruns the main claims from scratch. On this encoder, a word blocklist and the conditioning disagree often. An embedding filter that reads the encoder’s output closes most of that gap and costs some false alarms on look-alike prompts that don’t ask for a fox. The lab renders no images, so it can’t prove what a generator would draw. Image prompts and control branches skip text filters and need an output check.",
        caption: `Fresh run: keyword ${EV["keyword blocks fox-intent (of 16)"]}/16, embedding ${EV["D1 embedding blocks fox-intent (of 16)"]}/16 with ${EV["D1 embedding blocks benign (of 24)"]}/24 false positives, ${EV["allowed fox-intent landing on fox (of 13)"]}/13 allowed prompts on fox, ${EV["fox vs dog rows that differ (of 77)"]}/77 rows changed by one word; one-pass misses the chunked tail (${EV["D1 one-pass misses the chunked tail"]}), <span class="c-ok">same view</span> blocks it (${EV["D2 same view blocks the chunked tail"]}).`,
        cmd: "docker compose run --rm workbench python concept-conditioning/scripts/evaluate.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Prompt text, filter, tokenizer, text encoder, conditioning rows and a stub generator, with a detail panel"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) => S("rect", { x, y, width: w, height: h, rx: 12, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const clip = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = (p, x1, x2, y) => S("path", { d: `M${x1} ${y} L${x2} ${y}`, fill: "none", stroke: V("dim"), "stroke-width": 2, "marker-end": `url(#${arrowId})` }, p);

      // ---- pipeline strip (top)
      const strip = [
        { k: "txt", x: 16, w: 128, t: "PROMPT", s: "raw text", c: "teal" },
        { k: "flt", x: 168, w: 140, t: "FILTER", s: "word blocklist", c: "ok" },
        { k: "tok", x: 332, w: 140, t: "TOKENIZER", s: `${E.ctx} slots`, c: "teal" },
        { k: "enc", x: 496, w: 136, t: "TEXT ENCODER", s: `${(E.params / 1e6).toFixed(1)}M params`, c: "violet" },
        { k: "row", x: 656, w: 132, t: "CONDITIONING", s: `${E.rows.join(" × ")} rows`, c: "violet" },
        { k: "gen", x: 812, w: 132, t: "GENERATOR", s: "stub only", c: "warn" },
      ];
      const G = {};
      strip.forEach((b, i) => {
        const g = S("g", { class: "dimmable" }, svg);
        b.box = card(g, b.x, 34, b.w, 84, V(b.c));
        label(g, b.x + 14, 64, b.t, { "letter-spacing": "1" });
        b.sub = T(g, b.x + 14, 96, b.s, 14, { class: "mono" });
        if (i < strip.length - 1) arrow(svg, b.x + b.w + 2, strip[i + 1].x - 4, 76);
        G[b.k] = g; b.g = g;
      });
      const fltSub = strip[1].sub;
      const canaryTag = T(svg, 878, 146, D.canary, 14, { "text-anchor": "middle", class: "mono", fill: V("lime"), "font-weight": 700 });

      // ---- detail panels (bottom); each is a group whose opacity the state sets
      const P = [];
      const panel = (title) => { const g = S("g", {}, svg); card(g, 16, 172, 928, 352); label(g, 40, 204, title); P.push(g); return g; };

      // 1: the 77 slots
      const p1 = panel("ONE PROMPT, 77 SLOTS");
      for (let i = 0; i < E.slots; i++) {
        const used = i < E.tokens.length, x = 40 + (i % 39) * 22.5, y = 236 + Math.floor(i / 39) * 30;
        S("rect", { x, y, width: 18, height: 22, rx: 5, fill: V(used ? "teal" : "dim"), opacity: used ? .9 : .35 }, p1);
      }
      E.tokens.forEach((t, i) => T(p1, 52, 318 + i * 24, `${i}  ${t}`, 14, { class: "mono", fill: V("teal") }));
      T(p1, 360, 330, `${E.slots - E.tokens.length} pad slots, each filled with <|endoftext|>`, 15);
      T(p1, 360, 362, `generator input: ${E.rows.join(" × ")} rows`, 15, { fill: V("violet"), "font-weight": 700 });
      T(p1, 360, 394, `filter vector: ${E.pooled[0]} numbers (the end-of-text row)`, 15);
      T(p1, 360, 426, `uppercase prompt, same rows: ${E.lower_same}`, 15);

      // 2: cosine bars to "a photo of a fox"
      const p2 = panel("COSINE TO “A PHOTO OF A FOX”");
      const bars2 = Object.entries(NB.cos);
      bars2.forEach(([k, c], i) => {
        const y = 232 + i * 38, w = 520 * (c - .6) / .4;
        T(p2, 40, y + 20, k, 15, { class: "mono" });
        S("rect", { x: 150, y, width: Math.max(4, w), height: 26, rx: 6, fill: V(k === "fox" ? "teal" : "violet"), opacity: .8 }, p2);
        T(p2, 160 + Math.max(4, w), y + 19, c.toFixed(3), 14, { class: "mono" });
      });
      T(p2, 40, 482, `probe: ${NB.probe.map(p => `${p.text.replace("a photo of a ", "")} → ${p.label}`).join("   ")}`, 14, { class: "mono", fill: V("muted") });

      // 3: the labeled fox-intent prompts
      const p3 = panel("FOX-INTENT PROMPTS: FILTER VS CONDITIONING");
      KW.rows.forEach((r, i) => {
        const col = i % 2, row = Math.floor(i / 2), x = 40 + col * 460, y = 226 + row * 34;
        const c = r.keyword ? "ok" : r.probe === "fox" ? "bad" : "dim";
        S("rect", { x, y, width: 16, height: 16, rx: 4, fill: V(c) }, p3);
        T(p3, x + 26, y + 14, clip(r.text, 34), 14, { class: "mono" });
        T(p3, x + 360, y + 14, r.keyword ? "blocked" : `→ ${r.probe}`, 14, { fill: V(c === "dim" ? "muted" : c), "font-weight": 700 });
      });

      // 4: the cut at 77
      const p4 = panel("TOKEN 77");
      const cell = (g, x, y, c, o = .85) => S("rect", { x, y, width: 9, height: 26, rx: 2, fill: V(c), opacity: o }, g);
      T(p4, 40, 244, "standard encoder", 14, { fill: V("muted") });
      for (let i = 0; i < TR.n_full; i++) cell(p4, 40 + i * 10.6, 254, i < TR.n_scene ? "teal" : "bad", i < TR.n_scene ? .7 : .25);
      const cutX = 40 + TR.n_scene * 10.6 - 1;
      S("path", { d: `M${cutX} 240 L${cutX} 292`, stroke: V("ink"), "stroke-width": 2, "stroke-dasharray": "4 3" }, p4);
      T(p4, 40, 316, `tail dropped: ids identical, row difference ${TR.diff.toFixed(1)}, probe ${TR.std_probe[0]}; keyword filter: ${TR.keyword ? "BLOCK" : "allow"}`, 14);
      T(p4, 40, 364, "chunked encoder", 14, { fill: V("muted") });
      for (let i = 0; i < TR.n_full; i++) cell(p4, 40 + i * 10.6 + (i >= TR.n_scene ? 24 : 0), 374, i < TR.n_scene ? "teal" : "bad");
      T(p4, 40, 436, `chunk 1 → ${TR.chunk_probe[0][0]} ${TR.chunk_probe[0][1].toFixed(3)}`, 15, { class: "mono" });
      T(p4, 40, 464, `chunk 2 “${TR.tail_text}” → ${tailChunk[0]} ${tailChunk[1].toFixed(3)}`, 15, { class: "mono", fill: V("bad"), "font-weight": 700 });

      // 5: row-by-row difference
      const p5 = panel("ROW COSINE, “FOX” VS “DOG”, BY SLOT");
      D.row_cos.forEach((c, i) => {
        const x = 40 + i * 11.6;
        S("rect", { x, y: 300 - 80 * (1 - c), width: 9, height: Math.max(2, 80 * (1 - c)), rx: 2, fill: V(i < RW.pos ? "teal" : "violet"), opacity: .85 }, p5);
      });
      S("path", { d: "M40 302 L934 302", stroke: V("line"), "stroke-width": 2 }, p5);
      T(p5, 40, 330, `bar height = 1 − cosine. Slots 0–${RW.pos - 1} identical; slot ${RW.pos} is the word; ${RW.pad} padding rows differ too`, 14);
      T(p5, 40, 392, `scrub the word’s row → matrix still ${RW.scrub_fox.toFixed(3)} fox, ${RW.scrub_dog.toFixed(3)} dog`, 16, { fill: V("violet"), "font-weight": 700 });
      T(p5, 40, 428, `${RW.differ} of 77 rows carry the change into cross-attention`, 15);

      // 6: vocabulary search hits
      const p6 = panel(`VOCABULARY SEARCH: ${N(SR.n_words)} WORDS`);
      SR.hits.slice(0, 9).forEach((h, i) => {
        const y = 222 + i * 30, w = 420 * (h.cos - .6) / .4;
        T(p6, 40, y + 18, h.word, 15, { class: "mono" });
        S("rect", { x: 160, y: y + 2, width: Math.max(4, w), height: 22, rx: 5, fill: V(h.cos >= SR.threshold ? "bad" : "dim"), opacity: .85 }, p6);
        T(p6, 170 + Math.max(4, w), y + 19, `${h.cos.toFixed(3)}  margin ${h.margin.toFixed(3)}`, 13, { class: "mono" });
      });
      card(p6, 700, 300, 220, 96, V("lime"));
      T(p6, 716, 334, "generator log", 13, { fill: V("muted") });
      T(p6, 716, 362, D.canary, 15, { class: "mono", fill: V("lime"), "font-weight": 700 });
      T(p6, 716, 386, `${SR.hits.length}/${SR.hits.length} bypass prompts`, 13);

      // 7: keyword vs embedding filter
      const p7 = panel("LABELED SET: WHAT EACH FILTER BLOCKS");
      [["keyword", F1], ["embedding", F2]].forEach(([k, f], i) => {
        const y = 240 + i * 90;
        T(p7, 40, y + 20, k, 16, { "font-weight": 700, fill: V(i ? "ok" : "muted") });
        S("rect", { x: 180, y, width: 360 * f.tp / D1.n_fox, height: 28, rx: 6, fill: V("ok"), opacity: .85 }, p7);
        S("rect", { x: 180, y, width: 360, height: 28, rx: 6, fill: "none", stroke: V("line") }, p7);
        T(p7, 552, y + 20, `fox-intent ${f.tp}/${D1.n_fox}`, 14, { class: "mono" });
        S("rect", { x: 180, y: y + 36, width: Math.max(3, 360 * f.fp / D1.n_benign), height: 18, rx: 5, fill: V("bad"), opacity: .7 }, p7);
        T(p7, 552, y + 50, `benign ${f.fp}/${D1.n_benign}`, 14, { class: "mono" });
      });
      T(p7, 40, 450, `long prompt on one 77-slot pass: ${D1.long_one_pass ? "blocked" : "allowed"} → the chunked encoder delivers the fox`, 15, { fill: V("bad"), "font-weight": 700 });

      // 8: the same-view grid
      const p8 = panel("WHO CATCHES THE HIDDEN TAIL");
      const cols = [["keyword", "keyword"], ["one", "one-pass"], ["same", "same view"]];
      cols.forEach(([, h], j) => T(p8, 420 + j * 170, 236, h, 14, { "font-weight": 700, fill: V("muted") }));
      D2.rows.forEach((r, i) => {
        const y = 262 + i * 52;
        T(p8, 40, y + 22, `“${r.tail}” · ${r.encoder}`, 15, { class: "mono" });
        T(p8, 300, y + 22, r.reach ? "reaches" : "cut", 14, { fill: V(r.reach ? "bad" : "muted") });
        cols.forEach(([k], j) => {
          const ok = r[k] === r.reach, c = ok ? "ok" : r.reach ? "bad" : "warn";
          S("rect", { x: 420 + j * 170, y, width: 130, height: 34, rx: 8, fill: V(c), opacity: .25 }, p8);
          T(p8, 432 + j * 170, y + 23, ok ? "ok" : r.reach ? "MISS" : "false alarm", 14, { fill: V(c), "font-weight": 700 });
        });
      });

      // 9: evaluation summary
      const p9 = panel("FRESH RUN");
      Object.entries(EV).forEach(([k, v], i) => {
        const col = i % 2, row = Math.floor(i / 2), x = 40 + col * 456, y = 238 + row * 38;
        T(p9, x, y, clip(k, 44), 14);
        T(p9, x + 400, y, String(v), 14, { class: "mono", "font-weight": 700, fill: V(v === true || typeof v === "number" ? "ok" : "muted") });
      });

      // ---- state
      const HOT = [null, ["tok", "enc", "row"], ["enc"], ["txt", "flt", "gen"], ["tok", "row"], ["row", "gen"],
        ["flt", "gen"], ["flt", "enc"], ["flt", "tok"], []];
      const st = { p: 1, c: 0, ef: 0 };
      const target = n => ({ p: n, c: n === 4 || n === 6 ? 1 : 0, ef: n >= 7 ? 1 : 0 });

      function draw(s) {
        P.forEach((g, i) => {
          const o = Math.max(0, 1 - Math.abs(s.p - (i + 1)) * 1.6);
          g.setAttribute("opacity", o.toFixed(3));
          g.setAttribute("visibility", o > 0.01 ? "visible" : "hidden");
        });
        A(canaryTag, { opacity: s.c.toFixed(3) });
        fltSub.textContent = s.ef > .5 ? (Math.round(s.p) === 8 ? "same view" : "embedding") : "word blocklist";
        const n = Math.round(s.p);
        const hot = HOT[n] || [];
        strip.forEach(b => b.g.classList.toggle("hot", hot.includes(b.k)));
        A(strip[5].box, { stroke: V(s.c > .5 ? "lime" : "warn") });
        el.classList.toggle("lx-focus", hot.length > 0);
      }
      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          return api.tween(600, k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
