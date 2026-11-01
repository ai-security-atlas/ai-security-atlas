/* LAB-40 arch-embedding: "Similarity is not relevance" (foundation lab, 9 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: a retrieval strip across the top (question -> bi-encoder -> index -> reranker -> top 4) and a
 * panel below that crossfades per step. Every number and string comes from window.LAB_DATA (data.js, exported
 * from the reference run). Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA;
  const n = D.plant.n;
  const kind = k => D.plant.kinds[k];
  const d1 = name => D.d1.rows.find(r => r.name.startsWith(name)) || {};
  const dose = name => D.dose.rows.find(r => r.name === name) || {};
  const rotm = m => (D.d2.rows.find(r => r.m === m) || {}).recovered;
  const embedRoute = D.d2.probe.find(p => p.route.includes("embed")) || {};

  X.define({
    id: "arch-embedding",
    family: "family-retrieval",
    title: 'Similarity is not <span class="outline">relevance</span>',
    legend: [{ role: "teal", label: "Knowledge base" }, { role: "violet", label: "Model" },
      { role: "bad", label: "Planted post" }, { role: "warn", label: "Retrieved context" },
      { role: "lime", label: "Canary" }, { role: "ok", label: "Defense" }],
    intro: {
      why: "A support assistant answers from the passages its search finds. The search ranks them by how much they look like the question. Anyone who can post text the index ingests can write something that looks very much like a question. The stored vectors raise a second question: once the text is gone, what do they still say?",
      plan: "You’ll first see how each model scores a passage on a clean knowledge base. Then you’ll plant forum posts and follow where they land, in the lab and in the shared RAG app’s own index. After that you’ll look at why copying the question works and turn leaked vectors back into the notes they came from. To finish, you’ll try ranking controls and a storage control and see which ones change the result.",
      terms: "An embedding is a list of numbers that stands for a text. A bi-encoder makes one embedding per text, on its own. Cosine similarity compares two embeddings by the angle between them; 1 means the same direction. A cross-encoder, or reranker, reads the question and one passage together and returns a score called a logit. The top 4 is what the app pastes into its model’s prompt. The canary is an inert code that every planted post and one leaked record carry.",
    },
    steps: [
      { chapter: "System", label: "One vector each",
        guide: "Start with the clean knowledge base. The bi-encoder turns each passage and each question into one vector, and the search ranks passages by cosine. For every question the right answer comes out on top, though for some the runner-up is close. The same model runs inside the shared RAG app, and its vectors match the ones computed here.",
        caption: `<code>${D.bi.repo}</code>: ${D.bi.layers} layers, ${D.bi.hidden} dimensions, ${D.bi.params_m}M parameters, at most ${D.bi.max_len} tokens per text. Right answer first for <span class="c-teal">${D.bi.top1}/${D.bi.n_queries}</span> questions over ${D.bi.n_passages} passages. Against <code>${D.bi.app_model}</code> in atlas-app: lowest cosine between the two runtimes ${D.bi.parity_min.toFixed(6)}, same nearest passage for ${D.bi.parity_rank}/${D.bi.n_queries}.`,
        cmd: "docker compose run --rm workbench python arch-embedding/scripts/s01_biencoder.py" },
      { chapter: "System", label: "Read in pairs",
        guide: "Next, a reranker rescores the search’s best candidates. It reads the question and a passage as one input, so it can check whether the passage answers the question. The right answers stay first and pull further ahead. The cost is one model pass for every candidate, while the passages’ vectors were computed long before the question arrived.",
        caption: `<code>${D.ce.repo}</code>: ${D.ce.layers} layers, ${D.ce.params_m}M parameters, one logit per pair. Right answer first after reranking the top ${D.ce.top}: <span class="c-teal">${D.ce.top1}/${n}</span>; lowest logit of a right answer ${D.ce.gold_min.toFixed(2)}. Per question: bi-encoder ${D.ce.ms_bi} ms, reranker ${D.ce.ms_ce} ms (${D.ce.top} pairs), on a busy CPU.`,
        cmd: "docker compose run --rm workbench python arch-embedding/scripts/s02_crossencoder.py" },
      { chapter: "Attack", label: "Plant a post",
        guide: "Now act as a forum user. Write one post per question in three styles: the question followed by a false claim, a list of keywords, or the false claim alone. Each ends with the canary. Copying the question wins first place most often, and the reranker leaves most of those posts on top. Keyword lists fall back after reranking, yet every style stays in the top 4.",
        caption: `Risk: one planted post per question, ranked against ${D.bi.n_passages} passages. First by cosine / after reranking / in the top ${D.plant.k} after reranking: mirror <span class="c-bad">${kind("mirror").cos1}/${kind("mirror").rr1}/${kind("mirror").rrK}</span>, stuffed ${kind("stuffed").cos1}/${kind("stuffed").rr1}/${kind("stuffed").rrK}, claim ${kind("claim").cos1}/${kind("claim").rr1}/${kind("claim").rrK} (of ${n}). Example: <code>${D.plant.example}</code>`,
        cmd: "docker compose run --rm workbench python arch-embedding/scripts/s03_plant.py" },
      { chapter: "Attack", label: "In the real index",
        guide: "Put the same posts into the shared RAG app and ask its retrieval stage each question. This is the chromadb index a real profile uses, with no reranker. On the clean collection the right answer is first. With the posts added, a question’s own post usually takes first place, and the four passages headed for the prompt always include one.",
        caption: `atlas-app (<code>${D.app.embedder}</code>, ${D.app.chunks} chunks): clean collection, right answer first ${D.app.c1}/${D.app.n}; planted collection, own post first <span class="c-bad">${D.app.p1}/${D.app.n}</span>, in the top 4 ${D.app.p4}/${D.app.n}, right answer still in the top 4 ${D.app.g4}/${D.app.n}. Distance is 1 − cosine.`,
        cmd: "docker compose run --rm workbench python arch-embedding/scripts/s04_app_index.py" },
      { chapter: "Mechanism", label: "Copy the question",
        guide: "Copying works because the bi-encoder averages the vectors of a passage’s tokens. Put the question in front of the false claim and the average swings toward the question’s own vector. One copy does nearly all of it, and more copies drift back. Copies of a different question pull the passage away, so the gain comes from matching this question.",
        caption: `Mean cosine to the question, false claim plus copies: ${D.dose.rows.slice(0, 5).map(r => `${r.name} <span class="c-${r.cos > D.dose.gold_cos ? "bad" : "teal"}">${r.cos.toFixed(3)}</span>`).join(", ")}; two copies of another question ${dose("2 of another").cos.toFixed(3)}. Real answers average ${D.dose.gold_cos.toFixed(3)}. First by cosine: ${dose("0 copies").cos1}/${n} with none, ${dose("1 copy").cos1}/${n} with one.`,
        cmd: "docker compose run --rm workbench python arch-embedding/scripts/s05_mirror_dose.py" },
      { chapter: "Mechanism", label: "Search the guesses",
        guide: "Turn to storage. A shop embeds its support notes, deletes the text and keeps the vectors. An attacker who gets those vectors writes every note they can imagine from lists of names, cities, products and problems, embeds each guess with the same public model and keeps the nearest. Even guesses phrased in the attacker’s own words land on the right note.",
        caption: `Candidate search over ${D.inv.n} leaked vectors. Attacker A, the shop’s wording: ${D.inv.A.n_cand} candidates, whole notes <span class="c-bad">${D.inv.A.exact}/${D.inv.n}</span>. Attacker B, own wording and extra names (<code>${D.inv.B.example_wording}</code>): ${D.inv.B.n_cand} candidates, whole notes <span class="c-bad">${D.inv.B.exact}/${D.inv.n}</span>, mean cosine ${D.inv.B.cos_mean.toFixed(3)}. Chance: 1/${D.inv.A.n_cand} and 1/${D.inv.B.n_cand}.`,
        cmd: "docker compose run --rm workbench python arch-embedding/scripts/s06_invert.py" },
      { chapter: "Impact", label: "What leaks",
        guide: "Put the two results side by side. On the left is the context the app would give its model for the warranty question, where a forum post sits next to the real answer. On the right is one leaked row, which comes back as a customer’s name, city, product and complaint. The first took one forum post. The second took a copy of the stored vectors and the public model.",
        caption: `Observation. Top 4 for “${D.question}”: ${D.app.hits.map(h => `<code>${h.id}</code>`).join(", ")}; the post carries <span class="c-lime">${D.canary}</span>. Row <span class="c-lime">${D.inv.row}</span> recovered by attacker B as <code>${D.inv.B.canary.text}</code> (cosine ${D.inv.B.canary.cos.toFixed(3)}); the deleted note was <code>${D.inv.true}</code>.` },
      { chapter: "Defense", label: "Ranking controls",
        guide: "Flood the index with every planted post and try the standard ranking controls. Reranking, a minimum score and a cap of one post per author each change something, but a post with the canary still reaches the top 4. New attacker accounts undo the cap. Only an allowlist of trusted sources keeps the posts out. The minimum score also shows where a post wins outright: on questions nothing else answers.",
        caption: `Canary post in the top 4 / posts per context / right answer in the top 4: cosine ${d1("cosine").canary}/${d1("cosine").posts}/${d1("cosine").answer}; rerank ${d1("+ rerank").canary}/${d1("+ rerank").posts}/${d1("+ rerank").answer}; minimum score ${D.d1.tau} ${d1("+ minimum").canary}/${d1("+ minimum").posts}; one post per author ${d1("+ 1 post").canary}/<span class="c-ok">${d1("+ 1 post").posts}</span>; three accounts ${d1("same").canary}/<span class="c-bad">${d1("same").posts}</span>; atlas-kb only <span class="c-ok">${d1("only").canary}</span>/${d1("only").posts}/${d1("only").answer} (of ${n}). Unanswered questions: empty context ${D.d1.voids.empty}/${D.d1.voids.n}, a post first when planted ${D.d1.voids.post_first}/${D.d1.voids.n}.`,
        cmd: "docker compose run --rm workbench python arch-embedding/scripts/d1_rank_controls.py" },
      { chapter: "Defense", label: "Guard the vectors",
        guide: "Check which routes of the RAG app hand out raw vectors. Then test a popular shortcut: rotate every stored vector with a secret matrix. Search works as before and blind guessing fails. An attacker who can also post notes reads their own rotated vectors and solves for the secret. So vectors need the same access rules as their source text. These are ranking and recovery results for two small models and a fictional corpus. No language model answered, so what a model does with a planted post is measured in the RAG labs.",
        caption: `No API key: <code>${embedRoute.route}</code> HTTP ${embedRoute.status} with <span class="c-bad">${embedRoute.vectors}</span> raw vector. Secret rotation: identical rankings ${D.d2.same}/${D.d2.nq}; notes recovered with no rotation ${D.d2.raw}/${D.d2.n}, rotated <span class="c-ok">${D.d2.blind}/${D.d2.n}</span>, with 32 planted notes ${rotm(32)}/${D.d2.n}, with 64 <span class="c-bad">${rotm(64)}/${D.d2.n}</span>. Evaluate: ${Object.entries(D.evaluate).map(([k, v]) => `${k} <code>${v}</code>`).join("; ")}.`,
        cmd: "docker compose run --rm workbench python arch-embedding/scripts/d2_vectors.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="A question passes a bi-encoder, an index and a reranker to the top 4 passages, with a detail panel per step"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) => S("rect", { x, y, width: w, height: h, rx: 10, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const cut = (s, k) => (s.length > k ? s.slice(0, k - 1) + "…" : s);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = (p, d, stroke = V("dim")) => S("path", { d, fill: "none", stroke, "stroke-width": 2, "marker-end": `url(#${arrowId})` }, p);
      const bars = [];   // {r, w, key, a, b}: width grows with seg(s[key], a, b)
      const bar = (p, key, x, y, w, h, role, a = .2, b = 1) => {
        const r = S("rect", { x, y, width: 0, height: h, rx: 3, fill: V(role) }, p);
        bars.push({ r, w: Math.max(2, w), key, a, b });
        return r;
      };
      const vbars = [];  // vertical bars growing up from a baseline
      const vbar = (p, key, x, b0, w, h, role, a = .2, b = 1) => {
        const r = S("rect", { x, y: b0, width: w, height: 0, rx: 3, fill: V(role) }, p);
        vbars.push({ r, h: Math.max(2, h), base: b0, key, a, b });
        return r;
      };
      const track = (p, x, y, w, h) => S("rect", { x, y, width: w, height: h, rx: 3, fill: V("panel-2") }, p);
      const fades = [];  // {g, key, a, b}: opacity grows with seg(s[key], a, b)
      const fade = (g, key, a, b) => { fades.push({ g, key, a, b }); return g; };

      // ---- retrieval strip
      const strip = [["QUESTION", "teal", "user text"], ["BI-ENCODER", "violet", "1 vector / text"], ["INDEX", "teal", "kb + forum posts"],
        ["RERANKER", "violet", "reads pairs"], ["TOP 4", "warn", "to the prompt"]];
      const gStrip = S("g", { class: "dimmable" }, svg);
      const stripBox = strip.map(([k, role, sub], i) => {
        const x = 16 + i * 190;
        const b = card(gStrip, x, 22, 166, 66, V(role));
        label(gStrip, x + 12, 46, k, { fill: V(role), "letter-spacing": "1" });
        T(gStrip, x + 12, 72, sub, 14, { class: "mono" });
        if (i) arrow(gStrip, `M${x - 22} 55 H${x - 3}`);
        return b;
      });
      const panel = () => S("g", { class: "dimmable" }, svg);

      // ---- P1: cosine of the right answer vs the runner-up, per question
      const g1 = panel();
      label(g1, 40, 126, "QUESTION → VECTOR");
      T(g1, 40, 154, cut(D.question, 50), 15, { "font-weight": 700 });
      D.bi.vec6.forEach((v, i) => {
        const x = 40 + i * 58;
        S("rect", { x, y: 172, width: 44, height: 44, rx: 6, fill: V(v >= 0 ? "teal" : "violet"), opacity: (.25 + Math.min(1, Math.abs(v) * 10) * .75).toFixed(2) }, g1);
        T(g1, x + 22, 236, v.toFixed(3), 13, { class: "mono", "text-anchor": "middle", fill: V("muted") });
      });
      T(g1, 392, 200, `… ${D.bi.hidden} numbers`, 14, { class: "mono", fill: V("muted") });
      T(g1, 40, 280, "mean of the token vectors, length 1", 14, { fill: V("muted") });
      T(g1, 40, 304, `atlas-app ONNX vs torch: cosine ${D.bi.parity_min.toFixed(6)}`, 14, { class: "mono" });
      label(g1, 520, 126, "COSINE · ANSWER vs RUNNER-UP");
      D.bi.rows.forEach((r, i) => {
        const y = 140 + i * 31;
        T(g1, 520, y + 15, r.q, 13, { class: "mono", fill: V("muted") });
        track(g1, 610, y + 2, 320, 10);
        bar(g1, "p1", 610, y + 2, 320 * r.cos_gold, 10, "teal", .1 + i * .03, .5 + i * .03);
        track(g1, 610, y + 14, 320, 8);
        bar(g1, "p1", 610, y + 14, 320 * r.cos_next, 8, "dim", .1 + i * .03, .5 + i * .03);
      });
      T(g1, 520, 528, `right answer first: ${D.bi.top1}/${D.bi.n_queries}`, 16, { "font-weight": 700 });

      // ---- P2: the reranker's pair scores for one question
      const g2 = panel();
      label(g2, 40, 126, `“${cut(D.question, 46)}”`, { "letter-spacing": "0" });
      const lmax = Math.max(...D.ce.pairs.map(p => p.ce), 1);
      T(g2, 270, 156, "cosine", 13, { fill: V("muted") });
      T(g2, 600, 156, "reranker logit", 13, { fill: V("muted") });
      D.ce.pairs.forEach((p, i) => {
        const y = 170 + i * 62, gold = i === 0;
        card(g2, 30, y, 900, 50, V(gold ? "teal" : "line"));
        T(g2, 46, y + 31, p.id, 15, { class: "mono", "font-weight": gold ? 700 : 400 });
        track(g2, 270, y + 18, 280, 14);
        bar(g2, "p2", 270, y + 18, 280 * p.cos, 14, "teal", .1, .5);
        T(g2, 556, y + 30, p.cos.toFixed(3), 13, { class: "mono" });
        track(g2, 600, y + 18, 260, 14);
        bar(g2, "p2", 600, y + 18, 260 * Math.max(0, p.ce) / lmax, 14, "violet", .4, .9);
        T(g2, 866, y + 30, p.ce.toFixed(2), 13, { class: "mono" });
      });
      T(g2, 40, 450, `bi-encoder: 1 pass per question (${D.ce.ms_bi} ms) · reranker: ${D.ce.top} pairs (${D.ce.ms_ce} ms)`, 15, { class: "mono" });
      T(g2, 40, 486, `right answer first after reranking: ${D.ce.top1}/${n}; lowest answer logit ${D.ce.gold_min.toFixed(2)}`, 16, { "font-weight": 700 });

      // ---- P3: where each kind of planted post lands
      const g3 = panel();
      label(g3, 40, 126, "PLANTED POST (MIRROR)");
      T(g3, 40, 150, cut(D.plant.example, 108), 13, { class: "mono", fill: V("bad") });
      const kinds = [["mirror", "question + false claim"], ["stuffed", "keyword list"], ["claim", "false claim only"]];
      const metrics = [["cos1", "1st by cosine"], ["rr1", "1st after rerank"], ["rrK", "in top 4 after rerank"]];
      kinds.forEach(([k, sub], c) => {
        const x0 = 40 + c * 310;
        T(g3, x0, 192, k, 16, { "font-weight": 700, fill: V("bad") });
        T(g3, x0 + 80, 192, sub, 13, { fill: V("muted") });
        metrics.forEach(([m, name], j) => {
          const y = 214 + j * 92;
          T(g3, x0, y + 14, name, 13, { fill: V("muted") });
          track(g3, x0, y + 24, 270, 26);
          bar(g3, "p3", x0, y + 24, 270 * kind(k)[m] / n, 26, m === "rrK" ? "warn" : "bad", .1 + j * .15, .5 + j * .15);
          T(g3, x0 + 270, y + 74, `${kind(k)[m]}/${n}`, 15, { class: "mono", "text-anchor": "end", "font-weight": 700 });
        });
      });

      // ---- P4: atlas-app's top 4 for the first question
      const g4 = panel();
      label(g4, 40, 126, `ATLAS-APP · TOP 4 · “${cut(D.question, 40)}”`, { "letter-spacing": "1" });
      D.app.hits.forEach((h, i) => {
        const y = 144 + i * 62, post = h.source !== "atlas-kb";
        card(g4, 30, y, 900, 50, V(post ? "bad" : "teal"));
        T(g4, 46, y + 31, `${i + 1}. ${h.id}`, 15, { class: "mono", "font-weight": 700, fill: V(post ? "bad" : "ink") });
        T(g4, 330, y + 31, h.source, 13, { class: "mono", fill: V("muted") });
        track(g4, 520, y + 18, 300, 14);
        bar(g4, "p4", 520, y + 18, 300 * (1 - h.d), 14, post ? "bad" : "teal", .1 + i * .08, .5 + i * .08);
        T(g4, 830, y + 30, `1 − d = ${(1 - h.d).toFixed(3)}`, 13, { class: "mono" });
      });
      T(g4, 40, 420, `clean collection: right answer first ${D.app.c1}/${D.app.n}`, 15, { class: "mono" });
      T(g4, 40, 448, `planted collection: own post first ${D.app.p1}/${D.app.n}, in top 4 ${D.app.p4}/${D.app.n}`, 15, { class: "mono", fill: V("bad") });
      T(g4, 40, 476, `top 4 carrying the canary: ${D.app.canary_q}/${D.app.n}`, 16, { "font-weight": 700 });

      // ---- P5: mean cosine of the false claim with 0-4 copies of the question in front
      const g5 = panel();
      label(g5, 40, 126, "FALSE CLAIM + COPIES OF THE QUESTION · MEAN COSINE");
      const x5 = 230, w5 = 540, gx = x5 + w5 * D.dose.gold_cos;
      D.dose.rows.forEach((r, i) => {
        const y = 148 + i * 54, ctrl = i === D.dose.rows.length - 1;
        T(g5, 40, y + 18, r.name, 15, { "font-weight": 700, fill: V(ctrl ? "muted" : "ink") });
        T(g5, 40, y + 36, ctrl ? "control" : `${Math.round(r.share * 100)}% question tokens`, 13, { fill: V("muted") });
        track(g5, x5, y + 8, w5, 22);
        bar(g5, "p5", x5, y + 8, w5 * r.cos, 22, ctrl ? "dim" : r.cos > D.dose.gold_cos ? "bad" : "teal", .1 + i * .06, .5 + i * .06);
        T(g5, x5 + w5 + 10, y + 25, r.cos.toFixed(3), 14, { class: "mono" });
        T(g5, 930, y + 25, `1st ${r.cos1}/${D.dose.n}`, 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
      });
      S("path", { d: `M${gx.toFixed(1)} 144 V470`, stroke: V("teal"), "stroke-width": 2, "stroke-dasharray": "5 5", fill: "none" }, g5);
      T(g5, gx, 492, `real answers ${D.dose.gold_cos.toFixed(3)}`, 13, { class: "mono", "text-anchor": "middle", fill: V("teal") });

      // ---- P6: candidate search against leaked vectors, two attackers
      const g6 = panel();
      card(g6, 30, 104, 280, 200, V("lime"));
      label(g6, 46, 130, "LEAKED ROW");
      T(g6, 46, 158, D.inv.row, 15, { class: "mono", "font-weight": 700, fill: V("lime") });
      for (let i = 0; i < 24; i++) {
        S("rect", { x: 46 + (i % 8) * 31, y: 176 + Math.floor(i / 8) * 26, width: 24, height: 20, rx: 4, fill: V("violet"), opacity: .45 }, g6);
      }
      T(g6, 46, 280, `${D.bi.hidden} numbers, text deleted`, 13, { fill: V("muted") });
      T(g6, 40, 340, `${D.inv.n} rows leaked`, 15, { "font-weight": 700 });
      T(g6, 40, 366, "embed every guess with the", 13, { fill: V("muted") });
      T(g6, 40, 386, "public model, keep the nearest", 13, { fill: V("muted") });
      arrow(g6, "M312 204 H346");
      const fields = ["name", "city", "product", "issue"];
      [["A", "the shop’s wording"], ["B", "own wording, extra names"]].forEach(([k, sub], c) => {
        const a = D.inv[k], y0 = 104 + c * 212;
        card(g6, 350, y0, 580, 200, V("bad"));
        T(g6, 366, y0 + 26, `ATTACKER ${k} · ${a.n_cand} candidates`, 14, { "font-weight": 700, fill: V("bad") });
        T(g6, 366, y0 + 46, `${sub}: ${cut(a.example_wording, 44)}`, 13, { class: "mono", fill: V("muted") });
        [...fields.map(f => [f, a.fields[f]]), ["whole note", a.exact]].forEach(([f, v], j) => {
          const y = y0 + 62 + j * 26;
          T(g6, 366, y + 15, f, 13, { fill: V("muted") });
          track(g6, 470, y + 4, 360, 14);
          bar(g6, "p6", 470, y + 4, 360 * v / D.inv.n, 14, j === 4 ? "bad" : "violet", .1 + c * .25 + j * .04, .45 + c * .25 + j * .04);
          T(g6, 914, y + 16, `${v}/${D.inv.n}`, 13, { class: "mono", "text-anchor": "end" });
        });
      });

      // ---- P7: what reaches the prompt, and what a leaked row gives back
      const wrap = (s, k) => s.split(" ").reduce((ls, w) => {
        if (ls.length && (ls[ls.length - 1] + " " + w).length <= k) ls[ls.length - 1] += " " + w; else ls.push(w);
        return ls;
      }, []);
      const g7 = panel();
      label(g7, 40, 126, "CONTEXT FOR THE PROMPT");
      T(g7, 40, 150, cut(D.question, 52), 13, { fill: V("muted") });
      D.app.hits.forEach((h, i) => {
        const y = 166 + i * 64, post = h.source !== "atlas-kb";
        card(g7, 30, y, 420, 52, V(post ? "bad" : "teal"));
        T(g7, 46, y + 22, `${i + 1}. ${h.id}`, 14, { class: "mono", "font-weight": 700, fill: V(post ? "bad" : "ink") });
        T(g7, 46, y + 42, post ? `${h.source} · ${D.canary}` : h.source, 13, { class: "mono", fill: V(post ? "lime" : "muted") });
      });
      label(g7, 500, 126, "LEAKED ROW → RECOVERED");
      T(g7, 500, 158, D.inv.row, 15, { class: "mono", "font-weight": 700, fill: V("lime") });
      card(g7, 490, 176, 440, 96, V("bad"));
      T(g7, 506, 200, `attacker B · cosine ${D.inv.B.canary.cos.toFixed(3)}`, 13, { fill: V("muted") });
      wrap(D.inv.B.canary.text, 50).slice(0, 2).forEach((l, i) => T(g7, 506, 226 + i * 22, l, 14, { class: "mono", fill: V("bad") }));
      card(g7, 490, 292, 440, 130, V("teal"));
      T(g7, 506, 316, "the deleted note", 13, { fill: V("muted") });
      wrap(D.inv.true, 50).slice(0, 4).forEach((l, i) => T(g7, 506, 342 + i * 22, l, 14, { class: "mono" }));

      // ---- P8: ranking controls over the flooded index
      const g8 = panel();
      const c8 = [["canary in top 4", 300, D.d1.n, "bad"], ["posts per context", 520, D.d1.k, "warn"], ["answer in top 4", 740, D.d1.n, "teal"]];
      c8.forEach(([h, x]) => T(g8, x, 126, h, 13, { fill: V("muted"), "font-weight": 700 }));
      D.d1.rows.forEach((r, i) => {
        const y = 140 + i * 52, allow = r.name.startsWith("only");
        T(g8, 40, y + 24, cut(r.name, 28), 14, { "font-weight": 700, fill: V(allow ? "ok" : "ink") });
        [[r.canary, "canary"], [r.posts, "posts"], [r.answer, "answer"]].forEach(([v, key], j) => {
          const [, x, max, role] = c8[j];
          track(g8, x, y + 12, 150, 18);
          bar(g8, "p8", x, y + 12, 150 * v / max, 18, allow && j < 2 ? "ok" : role, .1 + i * .05, .5 + i * .05);
          T(g8, x + 158, y + 26, key === "posts" ? v.toFixed(2) : `${v}/${max}`, 13, { class: "mono" });
        });
      });
      T(g8, 40, 474, `unanswered questions, minimum score ${D.d1.tau}: empty context ${D.d1.voids.empty}/${D.d1.voids.n}`, 14, { class: "mono", fill: V("ok") });
      T(g8, 40, 500, `one planted post per unanswered question: the post is 1st ${D.d1.voids.post_first}/${D.d1.voids.n}`, 14, { class: "mono", fill: V("bad") });

      // ---- P9: who gets raw vectors, and what a secret rotation buys
      const g9 = panel();
      label(g9, 40, 126, "ROUTES · NO API KEY");
      D.d2.probe.forEach((p, i) => {
        const y = 144 + i * 58, leak = p.vectors > 0 && p.status === 200;
        card(g9, 30, y, 400, 46, V(leak ? "bad" : "line"));
        T(g9, 46, y + 28, p.route, 14, { class: "mono", "font-weight": leak ? 700 : 400 });
        T(g9, 414, y + 28, `${p.status} · ${p.vectors} vec`, 13, { class: "mono", "text-anchor": "end", fill: V(leak ? "bad" : "muted") });
      });
      T(g9, 40, 410, `rotation: identical rankings ${D.d2.same}/${D.d2.nq}`, 14, { class: "mono", fill: V("ok") });
      label(g9, 480, 126, "NOTES RECOVERED · ROTATED STORE");
      const cols9 = [["raw", D.d2.raw, "bad"], ["blind", D.d2.blind, "ok"], ...D.d2.rows.map(r => [`+${r.m}`, r.recovered, "bad"])];
      const base9 = 440, h9 = 250;
      S("path", { d: `M480 ${base9} H930`, stroke: V("line"), "stroke-width": 2, fill: "none" }, g9);
      cols9.forEach(([k, v, role], i) => {
        const x = 492 + i * 54;
        vbar(g9, "p9", x, base9, 38, h9 * v / D.d2.n, role, .1 + i * .05, .5 + i * .05);
        T(g9, x + 19, base9 - h9 * v / D.d2.n - 8, `${v}`, 13, { class: "mono", "text-anchor": "middle" });
        T(g9, x + 19, base9 + 22, k, 13, { class: "mono", "text-anchor": "middle", fill: V("muted") });
      });
      T(g9, 480, 496, `planted notes the attacker wrote (of ${D.d2.n} stored notes)`, 13, { fill: V("muted") });

      const panels = [g1, g2, g3, g4, g5, g6, g7, g8, g9];
      const keys = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9"];
      const base = Object.fromEntries(keys.map(k => [k, 0]));
      const target = k => ({ ...base, [keys[k - 1]]: 1 });
      // strip boxes each step highlights: question, bi-encoder, index, reranker, top 4
      const hot = [[0, 1, 2], [3], [2, 3, 4], [2, 4], [1], [1, 2], [4], [3, 4], [2]];

      function draw(s) {
        panels.forEach((g, i) => { const v = s[keys[i]]; g.setAttribute("opacity", v.toFixed(3)); g.style.display = v > .01 ? "" : "none"; });
        bars.forEach(({ r, w, key, a, b }) => A(r, { width: (w * seg(s[key], a, b)).toFixed(1) }));
        vbars.forEach(({ r, h, base: b0, key, a, b }) => {
          const hh = h * seg(s[key], a, b);
          A(r, { y: (b0 - hh).toFixed(1), height: hh.toFixed(1) });
        });
        fades.forEach(({ g, key, a, b }) => g.setAttribute("opacity", seg(s[key], a, b).toFixed(3)));
        const k = keys.findIndex(key => s[key] > .5);
        stripBox.forEach((b, i) => b.setAttribute("stroke-width", k >= 0 && hot[k].includes(i) ? 4 : 2));
      }

      const st = target(1);
      draw(st);
      let gen = 0;
      return {
        step(k, dir) {
          const to = target(k), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          return api.tween(700, t => { if (g !== gen) return; X.lerpState(st, from, to, t); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
