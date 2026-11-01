/* LAB-34 arch-encoder: "The guardrail is a model too" (foundation lab, 9 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: an app strip across the top (document -> guardrail -> summarizer -> summary) and a panel below
 * that crossfades per step. Every number and string comes from window.LAB_DATA (data.js, exported from the
 * reference workbench run). Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA;
  const frac = a => `${a[0]}/${a[1]}`;
  const prow = p => D.pos.rows.find(r => r.p === p) || {};
  const m = name => D.d1.rows.find(r => r.method.startsWith(name)) || {};
  const tr = name => D.perturb.rows.find(r => r.name === name) || {};
  const nr = name => D.d2.rows.find(r => r.name === name) || {};
  const both = i => D.both.rows[i];
  const okN = 8 * D.pos.ok_topics.length;
  const okK = p => D.pos.ok_topics.reduce((a, t) => a + prow(p).per_topic[t], 0);

  X.define({
    id: "arch-encoder",
    family: "family-prompt",
    title: 'The guardrail is a model <span class="outline">too</span>',
    legend: [{ role: "teal", label: "Document text" }, { role: "violet", label: "Model" },
      { role: "bad", label: "Injection" }, { role: "warn", label: "Summary" }, { role: "lime", label: "Canary" },
      { role: "ok", label: "Defense" }],
    intro: {
      why: "Many apps put a small classifier in front of a language model. It reads each incoming document and blocks the ones that look like a prompt injection: text that tries to give the model new instructions. That classifier is a model too, with an input limit and blind spots of its own. Can a document get past it and still steer the model behind it?",
      plan: "You’ll start with the guardrail on short texts, where it does well, and see how an encoder reads its whole input at once. Then you’ll move an injection deeper into a long document and watch what the guardrail sees. A summarizer reads the same documents next. To finish, you’ll split the input before classifying it, clean up look-alike characters, and decide what the classifier can be trusted with.",
      terms: "A token is a piece of text. An encoder-only model, like this guardrail, reads all tokens at once and turns them into one label; it never writes text. An encoder-decoder model, like the summarizer, encodes the input and then writes new text one token at a time. The guardrail pipeline passes at most 512 tokens of each input to the model. A homoglyph is a letter from another alphabet that looks like a Latin one. The canary is the fictional code each injection asks for.",
    },
    steps: [
      { chapter: "System", label: "Short texts",
        guide: "Feed the guardrail short texts. Each injection asks whoever reads it to drop its task and print the canary. The benign texts include instructions meant for people, such as a request to print shipping labels. The model returns two probabilities, safe and injection, and flags a text when the injection side is above one half. A harmless note about passwords trips it.",
        caption: `<code>${D.guard.repo}</code>: ${D.guard.model_type}, ${D.guard.layers} layers, ${D.guard.params_m}M parameters, labels ${D.guard.labels.join(" / ")}. Short injections flagged <span class="c-bad">${D.short.tp}/${D.short.n_inj}</span>; short benign texts flagged <span class="c-ok">${D.short.fp}/${D.short.n_ben}</span> (the false alarm: <code>${D.short.fp_text}</code>).`,
        cmd: "docker compose run --rm workbench python arch-encoder/scripts/s01_guardrail.py" },
      { chapter: "System", label: "Reads both ways",
        guide: "Change only the last word of a sentence and look at the vector for the first word. In both encoders that vector moves, because every position attends to every other position. In the summarizer’s decoder it stays exactly the same, since a decoder position can only look to its left. An encoder therefore sums up the whole input in one pass, and the guardrail gives one verdict for all of it.",
        caption: `“${D.both.a}” vs “…${D.both.b.split(" ").pop()}”. First-token change: ${both(0).part} <span class="c-violet">${both(0).shift}</span>, ${both(1).part} <span class="c-violet">${both(1).shift}</span>, ${both(2).part} <span class="c-ok">${both(2).shift}</span> (exactly zero).`,
        cmd: "docker compose run --rm workbench python arch-encoder/scripts/s02_both_ways.py" },
      { chapter: "Attack", label: "Past the cut",
        guide: "Put an injection at the end of a long, harmless document and push it further back. Before token 512 the guardrail catches it only sometimes. After 512 it never reacts, and its score equals the score of the same document with no injection at all. One topic, the shipping policy, is flagged even when it’s clean, so its flags tell you nothing about the injection.",
        caption: `Risk: four topics × ${D.pos.n_inj} injections per position. Topics whose clean text passes (${D.pos.ok_topics.join(", ")}): flagged <span class="c-warn">${frac(D.pos.before_ok)}</span> before the cut and <span class="c-bad">${frac(D.pos.after_ok)}</span> after it. Past the cut, max |score difference| to the clean document: ${D.pos.same_max.toExponential(1)} over ${D.pos.same_n} documents. Clean policy text scores ${D.pos.clean.policy.toFixed(2)}.`,
        cmd: "docker compose run --rm workbench python arch-encoder/scripts/s03_position.py" },
      { chapter: "Mechanism", label: "What it reads",
        guide: "The pipeline cuts every input to 512 tokens before the classifier sees it, in the middle of a sentence if need be. The model itself can run on longer text, so the cut is a setting someone chose. Look also at the injection on its own: it is caught every time, yet inside a document it mostly isn’t. One verdict for many sentences lets the harmless text outweigh it.",
        caption: `Example: ${D.pos.example.tokens} tokens, injection at ${D.pos.example.pos}–${D.pos.example.tokens - 1}. The classifier gets [CLS] + tokens 0–${D.pos.example.kept - 3} + [SEP] = ${D.pos.example.kept}. Last words it reads: <code>${D.pos.example.last}</code>; dropped from <code>${D.pos.example.dropped}…</code>. Alone: ${D.short.tp}/${D.short.n_inj} flagged; after about 60 tokens of manual, minutes or story text: ${okK(60)}/${okN}.` },
      { chapter: "Mechanism", label: "Look-alike letters",
        guide: "Rewrite the injection words with characters a person reads the same way: Cyrillic look-alikes, invisible zero-width spaces, wide letters, digits for letters and spaces between letters. The canary stays as it was. The tokenizer breaks the altered words into many unfamiliar pieces. Look-alikes and digit swaps get some injections past the guardrail, and the other tricks fail against this model.",
        caption: `Flagged out of ${tr("none").n}: ${D.perturb.rows.map(r => `${r.name} <span class="c-${r.k < r.n ? "bad" : "ok"}">${r.k}</span>`).join(", ")}. <code>Ignore</code> is one token; the homoglyph version <code>${D.perturb.glyph_word}</code> becomes ${D.perturb.glyph_toks.length}: <code>${D.perturb.glyph_toks.join(" ")}</code>.`,
        cmd: "docker compose run --rm workbench python arch-encoder/scripts/s04_perturb.py" },
      { chapter: "Impact", label: "The summary obeys",
        guide: "Now run the whole app. The guardrail checks the first 512 tokens, and a document it passes goes whole to the summarizer, an encoder-decoder model that reads past 512. Several summaries print the canary or repeat the injected line, while clean documents get ordinary summaries. When the summarizer input is cut at 512 as well, the canary disappears, because then neither model reads the injection.",
        caption: `Observation: injection after token ${D.summ.start}. Guardrail passed ${frac(D.summ.passed)}; summaries with <span class="c-lime">${D.canary}</span>: <span class="c-bad">${frac(D.summ.hits)}</span>; clean documents ${frac(D.summ.clean_hits)}. Example: <code>${D.summ.example}</code>. Summarizer input also cut at 512: ${frac(D.summ.trunc_hits)}.`,
        cmd: "docker compose run --rm workbench python arch-encoder/scripts/s05_summarizer.py" },
      { chapter: "Defense", label: "Score every piece",
        guide: "Split the document before classifying it and keep the highest score of any piece. Large windows reach the end of the document but still bury the injection in harmless text. One piece per sentence lets each injection be judged on its own, and the clean documents stay clean. An attacker who knows about the split can glue the injection onto a harmless sentence, so you test that case too.",
        caption: `Injection near token 530, flagged: first 512 ${frac(m("first 512")["530"])}, windows of 510 ${frac(m("windows 510")["530"])}, windows of 128 ${frac(m("windows 128")["530"])}, <span class="c-ok">sentences ${frac(m("one piece")["530"])}</span>. Clean long documents flagged by sentences: ${frac(m("one piece").clean)}. Canary documents from the summarizer step blocked: ${D.d1.blocked["one piece per sentence"]}/${D.d1.n_hits}. Glued injection: <span class="c-bad">${frac(D.d1.adaptive)}</span>.`,
        cmd: "docker compose run --rm workbench python arch-encoder/scripts/d1_windows.py" },
      { chapter: "Defense", label: "Normalize first",
        guide: "Map the text to a standard form before the guardrail reads it. NFKC folds wide letters into ordinary ones, invisible format characters are removed, and a small table maps Cyrillic look-alikes to Latin letters. The look-alike injections are caught again, and benign text comes out unchanged. Digit swaps and spaced letters are plain ASCII, so normalization leaves them as they are.",
        caption: `Flagged raw → normalized: homoglyphs ${nr("homoglyphs").raw} → <span class="c-ok">${nr("homoglyphs").norm}</span>, zero-width ${nr("zero-width").raw} → ${nr("zero-width").norm}, leetspeak ${nr("leetspeak").raw} → <span class="c-bad">${nr("leetspeak").norm}</span> (of ${nr("none").n}). Benign texts unchanged: ${frac(D.d2.benign_same)} short, ${frac(D.d2.docs_same)} long.`,
        cmd: "docker compose run --rm workbench python arch-encoder/scripts/d2_normalize.py" },
      { chapter: "Defense", label: "One layer",
        guide: "Treat the classifier as one signal among several. It has a length limit, a false alarm rate and blind spots that an attacker can probe, so it can’t be the thing that keeps the summary safe. Mark the document as data, never let its text choose actions, and check the output as well. These results hold for this classifier, these fictional documents and these injections.",
        caption: `Evaluate, graded per condition: ${Object.entries(D.evaluate).map(([k, v]) => `${k} <code>${v}</code>`).join("; ")}.` },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="A document passes a guardrail classifier and a summarizer, with a detail panel per step"></svg>`,

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
      const arrow = (p, d, stroke = V("dim")) => S("path", { d, fill: "none", stroke, "stroke-width": 2, "marker-end": `url(#${arrowId})` }, p);
      const bars = [];   // {bar, w, key, a, b}: width grows with seg(s[key], a, b)
      const bar = (p, key, x, y, w, h, role, a = .2, b = 1, o = {}) => {
        const r = S("rect", { x, y, width: 0, height: h, rx: 3, fill: V(role), ...o }, p);
        bars.push({ r, w, key, a, b });
        return r;
      };
      const vbars = [];  // vertical bars growing up from a baseline
      const vbar = (p, key, x, base, w, h, role, a = .2, b = 1) => {
        const r = S("rect", { x, y: base, width: w, height: 0, rx: 3, fill: V(role) }, p);
        vbars.push({ r, h, base, key, a, b });
        return r;
      };

      // ---- app strip
      const strip = [["DOCUMENT", "teal", "untrusted text"], ["GUARDRAIL", "violet", "encoder · 512 tokens"],
        ["SUMMARIZER", "violet", "encoder-decoder"], ["SUMMARY", "warn", "one sentence"]];
      const gStrip = S("g", { class: "dimmable" }, svg);
      const stripBox = strip.map(([k, role, sub], i) => {
        const x = 16 + i * 238;
        const b = card(gStrip, x, 22, 212, 66, V(role));
        label(gStrip, x + 14, 46, k, { fill: V(role), "letter-spacing": "1" });
        T(gStrip, x + 14, 72, sub, 14, { class: "mono" });
        if (i) arrow(gStrip, `M${x - 24} 55 H${x - 3}`);
        return b;
      });
      const panel = () => S("g", { class: "dimmable" }, svg);
      // ---- P1: short texts, P(INJECTION) per text
      const g1 = panel();
      const cols1 = [["INJECTIONS", D.short.rows.filter(r => r.kind === "injection"), "bad"],
        ["BENIGN TEXTS", D.short.rows.filter(r => r.kind === "benign"), "teal"]];
      cols1.forEach(([head, rows, role], c) => {
        const x0 = 40 + c * 450;
        label(g1, x0, 126, `${head} · P(INJECTION)`);
        rows.forEach((r, i) => {
          const y = 140 + i * 31;
          T(g1, x0, y + 17, cut(r.text, 24), 13, { class: "mono", fill: V("muted") });
          S("rect", { x: x0 + 210, y: y + 4, width: 200, height: 16, rx: 3, fill: V("panel-2") }, g1);
          bar(g1, "p1", x0 + 210, y + 4, Math.max(2, 200 * r.p), 16, r.p >= .5 ? (role === "bad" ? "bad" : "warn") : "ok", .1 + i * .04, .5 + i * .04);
        });
        S("line", { x1: x0 + 310, x2: x0 + 310, y1: 136, y2: 140 + rows.length * 31, stroke: V("dim"), "stroke-dasharray": "4 4", "stroke-width": 2 }, g1);
        T(g1, x0 + 316, 136 + rows.length * 31 + 2, "0.5", 13, { class: "mono", fill: V("muted") });
      });
      T(g1, 40, 520, `flagged: injections ${D.short.tp}/${D.short.n_inj} · benign ${D.short.fp}/${D.short.n_ben}`, 16, { "font-weight": 700, fill: V("ink") });

      // ---- P2: encoder reads both ways, decoder reads left to right
      const g2 = panel();
      const grid = (x0, y0, n, causal, role, head) => {
        label(g2, x0, y0 - 14, head);
        for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
          const on = !causal || j <= i;
          S("rect", { x: x0 + j * 22, y: y0 + i * 22, width: 18, height: 18, rx: 4, fill: V(on ? role : "panel-2"), opacity: on ? .85 : 1 }, g2);
        }
      };
      grid(40, 150, 8, false, "violet", "ENCODER: READS ALL");
      grid(280, 150, 8, true, "violet", "DECODER: LEFT ONLY");
      T(g2, 40, 352, "each row is one position; colored cells are the", 13, { fill: V("muted") });
      T(g2, 40, 370, "positions it can read", 13, { fill: V("muted") });
      label(g2, 540, 136, "FIRST-WORD VECTOR CHANGE");
      const maxShift = Math.max(...D.both.rows.map(r => r.shift)) || 1;
      D.both.rows.forEach((r, i) => {
        const y = 156 + i * 76;
        T(g2, 540, y + 14, r.part, 15, { "font-weight": 700 });
        T(g2, 540, y + 34, r.kind, 13, { class: "mono", fill: V("muted") });
        S("rect", { x: 540, y: y + 44, width: 300, height: 16, rx: 3, fill: V("panel-2") }, g2);
        bar(g2, "p2", 540, y + 44, Math.max(3, 300 * r.shift / maxShift), 16, r.shift ? "violet" : "ok", .2 + i * .1, .8 + i * .05);
        T(g2, 850, y + 57, r.shift.toFixed(4), 15, { class: "mono", "font-weight": 700, fill: V(r.shift ? "violet" : "ok") });
      });
      T(g2, 540, 400, cut(`A: ${D.both.a}`, 50), 13, { class: "mono", fill: V("muted") });
      T(g2, 540, 422, cut(`B: ${D.both.b}`, 50), 13, { class: "mono", fill: V("muted") });
      T(g2, 40, 510, "Change the last word: the encoder’s first vector moves, the decoder’s stays put.", 16, { "font-weight": 700 });

      // ---- P3: detection vs where the injection starts
      const g3 = panel();
      label(g3, 40, 126, "SHARE FLAGGED · BY WHERE THE INJECTION STARTS (TOKENS)");
      const base3 = 460, h3 = 240, x3 = p => 80 + (p / 850) * 840;
      S("line", { x1: 60, x2: 930, y1: base3, y2: base3, stroke: V("line"), "stroke-width": 2 }, g3);
      const cutX = x3(D.guard.max_len);
      S("line", { x1: cutX, x2: cutX, y1: 150, y2: base3 + 8, stroke: V("bad"), "stroke-width": 2, "stroke-dasharray": "6 5" }, g3);
      T(g3, cutX + 8, 160, `cut at ${D.guard.max_len}`, 14, { class: "mono", "font-weight": 700, fill: V("bad") });
      D.pos.rows.forEach((r, i) => {
        const ok = okK(r.p), pol = r.k - ok, nPol = r.n - okN;
        const x = x3(r.p) - 22;
        vbar(g3, "p3", x, base3, 20, Math.max(2, h3 * ok / okN), ok ? "bad" : "dim", .1 + i * .08, .5 + i * .06);
        vbar(g3, "p3", x + 22, base3, 20, h3 * pol / nPol, "muted", .1 + i * .08, .5 + i * .06);
        T(g3, x + 21, base3 + 22, `~${r.p}`, 13, { class: "mono", "text-anchor": "middle", fill: V("muted") });
        T(g3, x + 4, base3 - h3 * ok / okN - 8, `${ok}/${okN}`, 13, { class: "mono", "text-anchor": "middle", fill: V("bad") });
        T(g3, x + 38, base3 - h3 * pol / nPol - 8, `${pol}/${nPol}`, 13, { class: "mono", "text-anchor": "middle", fill: V("muted") });
      });
      S("rect", { x: 60, y: 496, width: 14, height: 14, rx: 3, fill: V("bad") }, g3);
      T(g3, 82, 508, `topics whose clean text passes (${D.pos.ok_topics.join(", ")})`, 13, { fill: V("muted") });
      S("rect", { x: 520, y: 496, width: 14, height: 14, rx: 3, fill: V("muted") }, g3);
      T(g3, 542, 508, "policy topic (flagged even with no injection)", 13, { fill: V("muted") });
      // ---- P4: what the classifier receives; one verdict for the whole input
      const g4 = panel();
      const ex = D.pos.example, per = 8, nCells = Math.ceil(ex.tokens / per);
      label(g4, 40, 126, `ONE DOCUMENT, ${ex.tokens} TOKENS · ONE CELL = ${per} TOKENS`);
      const cw = 880 / nCells;
      const cells4 = [];
      for (let i = 0; i < nCells; i++) {
        const t0 = i * per, kept = t0 < ex.kept - 2, inj = t0 + per > ex.pos;
        const r = S("rect", { x: 40 + i * cw, y: 146, width: Math.max(1, cw - 1.5), height: 46, rx: 2, fill: V(inj ? "bad" : "teal") }, g4);
        cells4.push({ r, kept, inj, i });
      }
      const cutX4 = 40 + ((ex.kept - 2) / per) * cw;
      S("line", { x1: cutX4, x2: cutX4, y1: 138, y2: 214, stroke: V("bad"), "stroke-width": 2, "stroke-dasharray": "6 5" }, g4);
      T(g4, 40, 230, `[CLS] + tokens 0–${ex.kept - 3} + [SEP] → classifier`, 14, { class: "mono", fill: V("violet") });
      T(g4, 920, 230, `dropped →`, 14, { class: "mono", "text-anchor": "end", fill: V("bad") });
      card(g4, 40, 250, 430, 70, V("line"));
      T(g4, 56, 276, "last words it reads", 13, { fill: V("muted") });
      T(g4, 56, 304, cut(ex.last, 40), 15, { class: "mono" });
      card(g4, 490, 250, 430, 70, V("bad"));
      T(g4, 506, 276, "dropped from here", 13, { fill: V("muted") });
      T(g4, 506, 304, cut(ex.dropped + "…", 40), 15, { class: "mono", fill: V("bad") });
      label(g4, 40, 356, `THE SAME INJECTIONS · FLAGGED (${D.pos.ok_topics.join(", ").toUpperCase()})`);
      [["alone (Step 1)", D.short.tp, D.short.n_inj], [`after ~60 tokens of text`, okK(60), okN],
        [`after ~480 tokens of text`, okK(480), okN]].forEach(([name, k, n], i) => {
        const y = 370 + i * 44;
        T(g4, 40, y + 22, name, 15);
        S("rect", { x: 300, y: y + 6, width: 500, height: 22, rx: 4, fill: V("panel-2") }, g4);
        bar(g4, "p4", 300, y + 6, 500 * k / n, 22, i ? "warn" : "bad", .3 + i * .1, .8 + i * .05);
        T(g4, 812, y + 23, `${k}/${n}`, 15, { class: "mono", "font-weight": 700 });
      });

      // ---- P5: look-alike characters
      const g5 = panel();
      label(g5, 40, 126, "TRANSFORM");
      label(g5, 190, 126, "FLAGGED");
      label(g5, 430, 126, "TOKENS");
      label(g5, 540, 126, "HOW THE FIRST INJECTION LOOKS");
      D.perturb.rows.forEach((r, i) => {
        const y = 140 + i * 58;
        const miss = r.k < r.n;
        card(g5, 30, y, 900, 48, V(miss ? "bad" : "line"));
        T(g5, 44, y + 30, r.name, 15, { class: "mono", "font-weight": 700, fill: V(miss ? "bad" : "ink") });
        S("rect", { x: 190, y: y + 15, width: 180, height: 18, rx: 3, fill: V("panel-2") }, g5);
        bar(g5, "p5", 190, y + 15, 180 * r.k / r.n, 18, miss ? "bad" : "ok", .1 + i * .1, .5 + i * .08);
        T(g5, 380, y + 30, `${r.k}/${r.n}`, 14, { class: "mono" });
        T(g5, 430, y + 30, r.tokens.toFixed(0), 14, { class: "mono", fill: V("muted") });
        T(g5, 540, y + 30, cut(r.example.replace(/\u200b/g, "·"), r.name === "full-width" ? 18 : 34), 15, { class: "mono" });
      });
      T(g5, 40, 506, `“Ignore” → ${D.perturb.plain_toks.join(" ")}   look-alike → ${D.perturb.glyph_toks.join(" ")}`, 15, { class: "mono", fill: V("violet") });

      // ---- P6: the whole app; summaries of passed documents
      const g6 = panel();
      label(g6, 40, 126, `INJECTION AFTER TOKEN ${D.summ.start} · GUARDRAIL VERDICT AND SUMMARY`);
      const cards6 = D.summ.rows.map((r, i) => {
        const col = i % 5, row = Math.floor(i / 5);
        const x = 40 + col * 178, y = 140 + row * 70;
        const role = !r.passed ? "ok" : r.canary ? "lime" : "line";
        const c = card(g6, x, y, 166, 60, V(role));
        T(g6, x + 10, y + 22, `${r.topic} ${r.inj === null ? "· clean" : "#" + (r.inj + 1)}`, 13, { class: "mono", fill: V("muted") });
        T(g6, x + 10, y + 46, !r.passed ? "blocked" : r.canary ? "canary" : "summary", 15,
          { "font-weight": 700, fill: V(!r.passed ? "ok" : r.canary ? "lime" : "warn") });
        return { c, r, i };
      });
      card(g6, 40, 428, 880, 82, V("lime"));
      T(g6, 56, 456, "a summary the guardrail let through", 13, { fill: V("muted") });
      T(g6, 56, 488, cut(D.summ.example, 74), 16, { class: "mono", fill: V("lime") });
      // ---- P7: classify in pieces, keep the max
      const g7 = panel();
      const cols7 = [...D.d1.positions.map(p => [String(p), `INJ @${p}`]), ["clean", "CLEAN"]];
      label(g7, 40, 126, "GUARDRAIL INPUT");
      cols7.forEach(([, h], j) => label(g7, 360 + j * 140, 126, h));
      D.d1.rows.forEach((r, i) => {
        const y = 140 + i * 56;
        const best = r.method.startsWith("one piece");
        card(g7, 30, y, 900, 46, V(best ? "ok" : "line"));
        T(g7, 44, y + 20, r.method, 14, { "font-weight": 700, fill: V(best ? "ok" : "ink") });
        T(g7, 44, y + 38, `classifier passes per document: ${r.passes}`, 13, { class: "mono", fill: V("muted") });
        cols7.forEach(([k], j) => {
          const [a, b] = r[k], clean = k === "clean";
          S("rect", { x: 360 + j * 140, y: y + 14, width: 80, height: 18, rx: 3, fill: V("panel-2") }, g7);
          bar(g7, "p7", 360 + j * 140, y + 14, 80 * a / b, 18, clean ? (a ? "bad" : "ok") : (a === b ? "ok" : "warn"), .1 + i * .1, .5 + i * .08);
          T(g7, 446 + j * 140, y + 29, `${a}/${b}`, 13, { class: "mono" });
        });
      });
      card(g7, 30, 428, 900, 82, V("bad"));
      T(g7, 46, 456, "adaptive attacker: the injection glued onto a harmless sentence", 14, { fill: V("muted") });
      T(g7, 46, 488, `one piece per sentence flags ${frac(D.d1.adaptive)} · canary documents blocked ${D.d1.blocked["one piece per sentence"]}/${D.d1.n_hits}`, 16, { "font-weight": 700, fill: V("bad") });

      // ---- P8: normalize, then classify
      const g8 = panel();
      label(g8, 40, 126, "TRANSFORM");
      label(g8, 210, 126, "RAW");
      label(g8, 470, 126, "NORMALIZED");
      label(g8, 730, 126, "AFTER NORMALIZE()");
      D.d2.rows.forEach((r, i) => {
        const y = 140 + i * 58;
        const fixed = r.norm === r.n, miss = r.norm < r.n;
        card(g8, 30, y, 900, 48, V(miss ? "bad" : r.raw < r.n ? "ok" : "line"));
        T(g8, 44, y + 30, r.name, 15, { class: "mono", "font-weight": 700 });
        [[r.raw, 210, .1], [r.norm, 470, .5]].forEach(([k, x, a]) => {
          S("rect", { x, y: y + 15, width: 180, height: 18, rx: 3, fill: V("panel-2") }, g8);
          bar(g8, "p8", x, y + 15, 180 * k / r.n, 18, k === r.n ? "ok" : "bad", a + i * .04, a + .35 + i * .04);
          T(g8, x + 188, y + 30, `${k}/${r.n}`, 14, { class: "mono" });
        });
        T(g8, 730, y + 30, cut(r.example, 22), 14, { class: "mono", fill: V(fixed ? "ink" : "bad") });
      });
      T(g8, 40, 506, `benign texts unchanged by normalize(): ${frac(D.d2.benign_same)} short, ${frac(D.d2.docs_same)} long`, 15, { fill: V("ok"), "font-weight": 700 });

      // ---- P9: the classifier is one layer
      const g9 = panel();
      const layers = [["normalize", "ok", "NFKC, drop invisible characters, map look-alikes"],
        ["classify every sentence", "ok", "max score, threshold 0.5; it has false alarms and misses"],
        ["summarize as data", "violet", "the document is quoted material, never instructions"],
        ["no authority from the text", "ok", "the summary cannot trigger tools, links or replies"],
        ["check the output", "ok", "look for instructions, links and codes in the summary"]];
      label(g9, 40, 126, "LAYERS AROUND THE SUMMARIZER");
      layers.forEach(([k, role, sub], i) => {
        const y = 140 + i * 56;
        card(g9, 30, y, 470, 46, V(role));
        T(g9, 46, y + 20, k, 15, { "font-weight": 700, fill: V(role) });
        T(g9, 46, y + 38, cut(sub, 56), 13, { fill: V("muted") });
        if (i) arrow(g9, `M265 ${y - 10} V${y - 1}`);
      });
      label(g9, 530, 126, "EVALUATE · GRADED");
      Object.entries(D.evaluate).forEach(([k, v], i) => {
        const y = 140 + i * 37;
        T(g9, 530, y + 18, cut(k, 40), 13, { class: "mono" });
        T(g9, 930, y + 18, v, 14, { class: "mono", "text-anchor": "end", "font-weight": 700, fill: V("violet") });
      });

      const panels = [g1, g2, g3, g4, g5, g6, g7, g8, g9];
      const keys = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9"];
      const base = Object.fromEntries(keys.map(k => [k, 0]));
      const target = n => ({ ...base, [keys[n - 1]]: 1 });
      // which strip boxes each step highlights: document, guardrail, summarizer, summary
      const hot = [[1], [1, 2], [0, 1], [0, 1], [0, 1], [0, 1, 2, 3], [1], [0, 1], [1, 2, 3]];

      function draw(s) {
        panels.forEach((g, i) => { const v = s[keys[i]]; g.setAttribute("opacity", v.toFixed(3)); g.style.display = v > .01 ? "" : "none"; });
        bars.forEach(({ r, w, key, a, b }) => A(r, { width: (w * seg(s[key], a, b)).toFixed(1) }));
        vbars.forEach(({ r, h, base: b0, key, a, b }) => {
          const hh = h * seg(s[key], a, b);
          A(r, { y: (b0 - hh).toFixed(1), height: hh.toFixed(1) });
        });
        cells4.forEach(({ r, kept, inj }) => {
          const on = seg(s.p4, .1, .6);
          A(r, { opacity: ((kept ? 1 : .35 + .65 * (1 - on)) * (inj ? 1 : .75)).toFixed(3) });
        });
        cards6.forEach(({ c, i }) => c.setAttribute("opacity", seg(s.p6, i * .03, i * .03 + .3).toFixed(3)));
        const n = keys.findIndex(k => s[k] > .5);
        stripBox.forEach((b, i) => b.setAttribute("stroke-width", n >= 0 && hot[n].includes(i) ? 4 : 2));
        const focus = s.p4 > .5 || s.p5 > .5;
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
