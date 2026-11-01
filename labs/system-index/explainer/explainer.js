/* LAB-41 system-index: "Who controls the corpus controls the context" (foundation lab, 9 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: an ingestion strip across the top (kb-drop/ -> ingest -> chunk -> embed -> index -> top-4 -> prompt)
 * and one detail panel per step below it that crossfades. Every number and string comes from window.LAB_DATA
 * (data.js, exported by scripts/export_explainer_data.py from the reference run).
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one step only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp;
  const D = window.LAB_DATA;
  const CAN = D.canary, K = D.k;
  const TQ = D.queries.target.map(q => q.id), N = TQ.length;
  const sumQ = (rows, f) => TQ.reduce((a, q) => a + (f(rows[q]) ? 1 : 0), 0);
  const sumN = (rows, key) => TQ.reduce((a, q) => a + rows[q][key], 0);
  const cfg = (list, name) => list.find(c => c.config === name);
  const C150 = cfg(D.chunking.configs, "150/0"), C200 = cfg(D.chunking.configs, "200/60"),
    C400 = cfg(D.chunking.configs, "400/80"), SEC = cfg(D.sections.configs, "section");
  const nChunks = D.index.docs.reduce((a, d) => a + d.chunks, 0);
  const Q1 = D.queries.target[0].q, d300 = D.drop["refund-300"];
  const RR = D.rerank.rows;
  const SG = D.signed, sigSlots = sumN(SG.queries, "drop_slots"), sigCan = sumQ(SG.queries, r => r.canary);
  const sameBase = Object.values(SG.queries).filter(r => r.as_baseline).length, nSG = Object.keys(SG.queries).length;
  const CX = D.context;

  X.define({
    id: "system-index",
    family: "family-retrieval",
    title: 'Who controls the corpus controls the <span class="outline">context</span>',
    legend: [{ role: "teal", label: "Handbook (docs team)" }, { role: "bad", label: "Dropped pages" },
      { role: "violet", label: "Index / embedder" }, { role: "warn", label: "Prompt context" },
      { role: "lime", label: "Canary" }, { role: "ok", label: "Defense" }],
    intro: {
      why: "A support assistant answers from a handbook that it searches at question time. The search runs over an index, which a nightly job builds from a shared folder. Anyone with a support account can save a file into that folder. How much of what the assistant reads can that person decide?",
      plan: "You’ll look at the folder and the index the job built from it, and at how chunk size changes which sentences travel together. Then you’ll drop one page into the folder, followed by five near-copies, and read the prompt the assistant would send. Last, you’ll test signed ingestion, duplicate collapse and section chunking on the same questions.",
      terms: "A chunk is an excerpt of a document, and chunk size is its limit in characters. The index is the store of chunks that the search runs over. Ingestion is the job that cuts documents into chunks and writes them to the index. An embedding is a list of numbers that places a text by meaning. Retrieval returns the few chunks whose embeddings sit closest to the question. A caveat is a sentence that limits a rule. The canary is a fictional approval reference that marks every dropped page.",
    },
    steps: [
      { chapter: "System", label: "Folder and index",
        guide: "Start with the folder the nightly job reads and the index it builds. Each handbook page becomes chunks, and each chunk keeps a path plus the author line typed inside the file. Nobody checks that line. The ranking on the right is the baseline for the refund question, and the handbook’s own refund rule comes first.",
        caption: `<span class="c-teal">${D.index.docs.length} handbook pages</span> in <code>kb-drop/</code> become <span class="c-violet">${nChunks} chunks</span> (400 characters, 80 overlap). The only provenance stored is a path and <code>author: docs-team (self-declared)</code>. Top ${K} for “${Q1}”: <code>${D.index.hits.map(h => h.id).join(" ")}</code>, distance ${D.index.hits[0].distance.toFixed(4)} for rank 1.`,
        cmd: "docker compose run --rm workbench python system-index/scripts/s01_index.py" },
      { chapter: "System", label: "Chunk boundaries",
        guide: "Chunk size decides which sentences travel together. You re-chunk the handbook at several sizes and ask questions whose rule has a caveat right after it. At small sizes the caveat lands in a chunk of its own. It shares few words with the question, so it can miss the top results, and then the rule arrives without it.",
        caption: `Caveat in the top ${K}: ${C150.caveat}/${C150.n} at 150/0, ${C200.caveat}/${C200.n} at 200/60, ${C400.caveat}/${C400.n} at 400/80. Rule and caveat in one chunk: ${C150.together}/${C150.n}, ${C200.together}/${C200.n}, ${C400.together}/${C400.n}. At 150/0 the invoice caveat of the refund rule is rank ${C150.ranks["refund-limit"]}. Exact cosine search over atlas-app’s chunker and embedder.`,
        cmd: "docker compose run --rm workbench python system-index/scripts/s02_chunking.py" },
      { chapter: "Attack", label: "One dropped page",
        guide: "Now play the person with write access. You copy one short page into the folder, restart the indexing job and ask the refund question again. The page opens with the question an agent would type and answers it with a looser rule. Watch where it lands, and look at two unrelated questions as controls.",
        caption: `<span class="c-bad">refund-approvals-2026</span> (header: <code>author: docs-team</code>) is rank 1 for ${sumQ(D.drop, r => r.drop_top1)}/${N} phrasings of the refund question and carries <code class="c-lime">${CAN}</code>. Express-shipping control: ${D.drop["express-cutoff"].drop_slots} dropped slots. Lamp control: the page enters at rank ${D.drop["lamp-warranty"].ids.findIndex(i => i.startsWith("refund-approvals")) + 1}.`,
        cmd: "docker compose run --rm workbench python system-index/scripts/rank.py --label drop" },
      { chapter: "Mechanism", label: "Why it wins",
        guide: "Retrieval scores closeness of meaning, and a page that repeats the question’s words sits very close to it. The handbook’s rule covers the same topic in other words, so it scores lower. The score never asks who wrote a page or whether it is true, so an honest page and a planted one compete on wording alone.",
        caption: `Cosine distance to “${Q1}”: <span class="c-bad">dropped page ${d300.dist[0].toFixed(3)}</span>, <span class="c-teal">handbook rule ${d300.dist[1].toFixed(3)}</span>. The page’s first sentence is an agent’s question. That is the retrieval condition PoisonedRAG builds on, written here by hand.` },
      { chapter: "Mechanism", label: "Near-copies",
        guide: "Retrieval returns a fixed number of chunks, so every slot a copy takes is a slot the handbook loses. You add near-copies of the dropped page, and each one claims a different team wrote it. Count the slots one writer holds across the phrasings of the refund question, and check whether the real rule is still there.",
        caption: `One writer holds <span class="c-bad">${sumN(D.flood, "drop_slots")}/${N * K}</span> top-${K} slots (before the flood: ${sumN(D.drop, "drop_slots")}/${N * K}). The handbook’s refund rule is retrieved for ${sumQ(D.flood, r => r.rule)}/${N} phrasings. The ${Object.keys(D.declared).length} dropped pages claim ${new Set(Object.values(D.declared)).size} different authors.`,
        cmd: "docker compose run --rm workbench python system-index/scripts/rank.py --label flood" },
      { chapter: "Impact", label: "The prompt",
        guide: "Here is the prompt the assistant would send to its model, built by the same code a real chat request uses. Read the excerpts and then the question. Every excerpt comes from the dropper and carries the canary. The handbook’s refund limit and its invoice caveat are missing, so the model would never see them.",
        caption: `User turn: ${CX.user_chars} characters. Excerpts from the dropper: <span class="c-bad">${CX.drop_chunks}/${CX.retrieved.length}</span> (${CX.drop_chars}/${CX.all_chars} characters). <code class="c-lime">${CAN}</code> in the model’s context: ${CX.canary ? "yes" : "no"}. Refund rule: ${CX.rule ? "present" : "absent"}. Invoice caveat: ${CX.caveat ? "present" : "absent"}. The canary is an inert marker; no model was called.`,
        cmd: "docker compose run --rm workbench python system-index/scripts/s05_context.py" },
      { chapter: "Defense", label: "Signed ingestion",
        guide: "Signed ingestion reads a manifest, a list pairing each file’s hash with its writer’s signature. A file enters the index only if its entry matches and a known writer’s key verifies the signature. That writer is stored, and the file’s own author line is ignored. Watch the dropped pages land in quarantine, even the one with a copied signature. The same check can audit an existing index.",
        caption: `<span class="c-ok">${SG.accepted.length} accepted</span>, <span class="c-bad">${SG.quarantined.length} quarantined</span>; the copied signature fails (“${SG.quarantined[0][1]}”). Audit of the open index: ${SG.unverified_chunks}/${SG.open_chunks} chunks without a verified writer. Tamper test: “${SG.tamper}”. Signed index: ${sigSlots}/${N * K} dropped slots, canary in ${sigCan}/${N}, rankings equal to the baseline for ${sameBase}/${nSG} questions.`,
        cmd: "docker compose run --rm workbench python system-index/scripts/d1_signed.py" },
      { chapter: "Defense", label: "Collapse and cap",
        guide: "Two ranking defenses act on the candidates after retrieval. Duplicate collapse compares the three-word sequences of two chunks and keeps only the better-ranked one when the overlap is large. A quota caps how many slots one source may take. Count what each leaves for the dropper. The quota counts the author label, and the writer chose that label.",
        caption: `${RR.map(r => `${r.rule}: <span class="c-bad">${r.drop_slots}/${N * K}</span> dropped slots, canary ${r.canary}/${N}, ${r.filled}/${N * K} slots filled`).join("; ")}. Copies overlap at Jaccard ${D.rerank.j_drop[0].toFixed(2)}–${D.rerank.j_drop[1].toFixed(2)}; handbook chunks at most ${D.rerank.j_handbook_max.toFixed(2)}.`,
        cmd: "docker compose run --rm workbench python system-index/scripts/d2_rerank.py" },
      { chapter: "Defense", label: "Section chunks",
        guide: "The last defense changes the chunker. Each section of a page becomes one chunk, headed by the page title and the section name. Rules keep their caveats at a small average size. This lab shows which text reaches the model. It doesn’t measure what a model answers from that text, and chunking does nothing about a false page.",
        caption: `Sections: ${SEC.chunks} chunks of ${SEC.mean_chars} characters on average. Caveat in the top ${K}: <span class="c-ok">${SEC.caveat}/${SEC.n}</span>; rule and caveat in one chunk: <span class="c-ok">${SEC.together}/${SEC.n}</span> (200/60: ${C200.together}/${C200.n} at ${C200.mean_chars} characters). Dropped slots left by signed ingestion: ${sigSlots}/${N * K}; by duplicate collapse: ${RR.find(r => r.rule.startsWith("collapse near")).drop_slots}/${N * K}.`,
        cmd: "docker compose run --rm workbench python system-index/scripts/d3_sections.py" },
    ],
    html: `<style>[data-explainer="system-index"] svg text { font-variant-ligatures: none; font-feature-settings: "liga" 0, "calt" 0; }</style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="The support desk’s ingestion pipeline and its index, step by step"></svg>`,

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
      function wrap(s, n) {
        const out = []; let line = "";
        for (const w of String(s).replace(/\s+/g, " ").trim().split(" ")) {
          if ((line + " " + w).trim().length > n && line) { out.push(line); line = w; } else line = (line + " " + w).trim();
        }
        if (line) out.push(line);
        return out;
      }
      // text lines with the canary (and optional key phrases) colored, as tspans
      function rich(p, x, y, s, n, size = 13, max = 9, marks = [], o = {}) {
        const all = wrap(s, n), lines = all.slice(0, max);
        if (all.length > max) lines[max - 1] += " …";
        lines.forEach((l, i) => {
          const t = S("text", { x, y: y + i * (size + 5), "font-size": size, ...o }, p);
          let rest = l;
          const keys = [[CAN, "lime"], ...marks];
          while (rest.length) {
            let best = null;
            for (const [k, role] of keys) { const j = rest.indexOf(k); if (j >= 0 && (!best || j < best[0])) best = [j, k, role]; }
            if (!best) { S("tspan", { text: rest }, t); break; }
            if (best[0]) S("tspan", { text: rest.slice(0, best[0]) }, t);
            S("tspan", { text: best[1], fill: V(best[2]), "font-weight": 700 }, t);
            rest = rest.slice(best[0] + best[1].length);
          }
        });
        return lines.length;
      }
      const clean = s => String(s).replace(/#+ /g, "").replace(/\s+/g, " ").trim();
      const isDrop = id => id.startsWith("refund-approvals") || id.startsWith("refund-quick") || id.startsWith("refund-rules");
      const short = (id, n = 24) => id.length > n ? id.slice(0, n - 1) + "…" : id;

      // ---------------------------------------------------------------- ingestion strip
      const STAGES = ["kb-drop/", "ingest", "chunk", "embed", "index", `top-${K}`, "prompt"];
      const SW = 116, GAP = 17, SX = 30, SY = 18, SH = 48;
      const stages = STAGES.map((name, i) => {
        const g = S("g", {}, svg), x = SX + i * (SW + GAP);
        const r = S("rect", { x, y: SY, width: SW, height: SH, rx: 10, fill: V("panel"), "stroke-width": 1.8 }, g);
        const t = T(g, x + SW / 2, SY + 30, name, 14, { "text-anchor": "middle", "font-weight": 800, class: "mono" });
        if (i) arrow(g, `M${x - GAP + 2} ${SY + SH / 2} H${x - 4}`);
        return { g, r, t, x };
      });
      const badges = ["D1", "D2", "D3"].map((b, i) => {
        const at = [1, 5, 2][i], x = stages[at].x + SW - 30, g = S("g", {}, svg);
        S("rect", { x, y: SY - 9, width: 34, height: 20, rx: 10, fill: V("ok") }, g);
        T(g, x + 17, SY + 6, b, 13, { "text-anchor": "middle", "font-weight": 800, fill: V("panel") });
        return g;
      });
      // which strip stages each step is about
      const HOT = [[0, 1, 4], [2], [0, 5], [3, 5], [0, 5], [6], [1], [5], [2]];
      const PY = 96;
      const panel = () => S("g", { opacity: 0 }, svg);

      // ---------------------------------------------------------------- 1: folder and index
      const p1 = panel();
      label(p1, 30, PY + 16, "KB-DROP/ · ANY SUPPORT ACCOUNT");
      card(p1, 30, PY + 28, 270, 300);
      D.index.docs.forEach((d, i) => {
        const y = PY + 60 + i * 44;
        T(p1, 46, y, d.id + ".md", 14, { class: "mono", "font-weight": 700, fill: V("teal") });
        T(p1, 46, y + 18, `${d.chars} chars · ${d.chunks} chunks`, 13, { fill: V("muted") });
      });
      arrow(p1, `M306 ${PY + 178} H336`);
      label(p1, 344, PY + 16, `INDEX SYSIDX-OPEN · ${nChunks} CHUNKS`);
      card(p1, 344, PY + 28, 250, 300, V("violet"));
      const tiles1 = [];
      D.index.docs.forEach((d, i) => {
        for (let c = 0; c < d.chunks; c++) {
          const x = 362 + c * 112, y = PY + 44 + i * 44;
          const r = S("rect", { x, y, width: 100, height: 32, rx: 7, fill: V("teal"), "fill-opacity": .16, stroke: V("teal"), "stroke-width": 1.4 }, p1);
          const t = T(p1, x + 50, y + 21, `${d.id}#${c}`, 13, { "text-anchor": "middle", class: "mono" });
          tiles1.push([r, t]);
        }
      });
      const metaY = PY + 352;
      card(p1, 30, metaY - 22, 564, 74, V("line"));
      T(p1, 46, metaY, "metadata stored with refunds#0", 13, { fill: V("muted"), "font-weight": 700 });
      T(p1, 46, metaY + 22, "source = kb-drop/handbook/refunds.md", 13, { class: "mono" });
      T(p1, 46, metaY + 42, "(author: docs-team, self-declared)", 13, { class: "mono", fill: V("warn"), "font-weight": 700 });
      label(p1, 626, PY + 16, `TOP ${K} · BASELINE`);
      rich(p1, 626, PY + 44, `“${Q1}”`, 40, 13, 2, [], { "font-weight": 700 });
      const rows1 = D.index.hits.map((h, i) => {
        const y = PY + 96 + i * 62, g = S("g", {}, p1);
        card(g, 626, y, 304, 52, V(i === 0 ? "teal" : "line"));
        T(g, 640, y + 21, `${i + 1}`, 15, { "font-weight": 800 });
        T(g, 662, y + 21, h.id, 14, { class: "mono", "font-weight": 700, fill: V("teal") });
        T(g, 916, y + 21, h.distance.toFixed(3), 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
        T(g, 662, y + 40, short(clean(h.text), 34), 13, { fill: V("muted") });
        return g;
      });
      T(p1, 626, PY + 362, "distance = 1 − cosine similarity", 13, { fill: V("muted") });

      // ---------------------------------------------------------------- 2: chunk boundaries
      const p2 = panel();
      label(p2, 30, PY + 16, "REFUNDS.MD · “REFUND LIMITS” UNDER TWO CHUNKERS");
      const RCH = D.chunking.refunds_chunks;
      const showChunk = (g, x, y, w, txt, tag) => {
        const ls = wrap(clean(txt), Math.floor(w / 7.4)).slice(0, 5);
        const h = 30 + ls.length * 18;
        card(g, x, y, w, h, V("teal"));
        T(g, x + 12, y + 18, tag, 13, { class: "mono", fill: V("muted"), "font-weight": 700 });
        ls.forEach((l, i) => rich(g, x + 12, y + 38 + i * 18, l, 200, 13, 1,
          [["refund up to $500", "teal"], ["This limit does not apply to orders paid by invoice", "warn"]]));
        return h;
      };
      const g2a = S("g", {}, p2), g2b = S("g", {}, p2);
      T(g2a, 30, PY + 46, "150 characters, no overlap", 14, { "font-weight": 700 });
      let yy = PY + 58;
      RCH["150/0"].slice(0, 2).forEach((c, i) => { yy += showChunk(g2a, 30, yy, 540, c, `chunk #${i}`) + 10; });
      T(g2b, 30, yy + 18, "400 characters, 80 overlap (atlas-app default)", 14, { "font-weight": 700 });
      showChunk(g2b, 30, yy + 30, 540, RCH["400/80"][0], "chunk #0");
      T(p2, 30, PY + 428, `caveat on its own: rank ${C150.ranks["refund-limit"]} for the refund question at 150/0`, 13, { fill: V("warn"), "font-weight": 700 });
      label(p2, 600, PY + 16, "FIVE RULE + CAVEAT QUESTIONS");
      T(p2, 690, PY + 50, `caveat in top ${K}`, 13, { fill: V("muted"), "font-weight": 700 });
      T(p2, 820, PY + 50, "one chunk", 13, { fill: V("muted"), "font-weight": 700 });
      const dots2 = D.chunking.configs.map((c, i) => {
        const y = PY + 84 + i * 64;
        T(p2, 600, y + 5, c.config, 15, { class: "mono", "font-weight": 800 });
        T(p2, 600, y + 24, `${c.chunks} chunks`, 13, { fill: V("muted") });
        const mk = (x0, k) => Array.from({ length: c.n }, (_, j) => ({
          el: S("circle", { cx: x0 + j * 22, cy: y, r: 8, "stroke-width": 1.6 }, p2), on: j < k }));
        return { cav: mk(696, c.caveat), tog: mk(826, c.together) };
      });

      // ---------------------------------------------------------------- 3: one dropped page
      const p3 = panel();
      label(p3, 30, PY + 16, "KB-DROP/DROPBOX/ · ONE NEW FILE");
      const g3f = S("g", {}, p3);
      card(g3f, 30, PY + 28, 300, 150, V("bad"));
      T(g3f, 46, PY + 52, "refund-approvals-2026.md", 14, { class: "mono", "font-weight": 700, fill: V("bad") });
      T(g3f, 46, PY + 72, "author: docs-team (claimed)", 13, { class: "mono", fill: V("muted") });
      rich(g3f, 46, PY + 96, clean(d300.texts[0]).replace(/^Refund approvals: 2026 update /, ""), 38, 13, 4);
      label(p3, 370, PY + 16, `TOP ${K} BEFORE`);
      label(p3, 660, PY + 16, `TOP ${K} AFTER THE DROP`);
      const list3 = (x, ids, dist) => ids.map((id, i) => {
        const y = PY + 32 + i * 50, g = S("g", {}, p3), bad = isDrop(id);
        card(g, x, y, 270, 40, V(bad ? "bad" : "teal"), bad ? { fill: V("bad"), "fill-opacity": .12 } : {});
        T(g, x + 12, y + 25, `${i + 1}`, 14, { "font-weight": 800 });
        T(g, x + 34, y + 25, short(id, 19), 14, { class: "mono", "font-weight": 700, fill: V(bad ? "bad" : "teal") });
        if (dist) T(g, x + 258, y + 25, dist[i].toFixed(3), 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
        return g;
      });
      list3(370, d300.baseline, D.index.hits.map(h => h.distance));
      const after3 = list3(660, d300.ids, d300.dist);
      const can3 = S("circle", { cx: 660 + 270 - 66, cy: PY + 52, r: 6, fill: V("lime") }, p3);
      label(p3, 30, PY + 268, "ALL QUESTIONS AFTER THE DROP");
      const rowsQ = [...D.queries.target, ...D.queries.control].map((q, i) => {
        const r = D.drop[q.id], y = PY + 292 + i * 30, ctl = r.kind === "control";
        const rank = r.ids.findIndex(isDrop) + 1;
        const g = S("g", {}, p3);
        T(g, 30, y, ctl ? "control" : "target", 13, { fill: V("muted"), "font-weight": 700 });
        T(g, 100, y, short(q.q, 64), 13, {});
        T(g, 930, y, rank ? `dropped page at rank ${rank}` : "unchanged", 13, { "text-anchor": "end", "font-weight": 700, fill: V(rank ? "bad" : "teal") });
        return g;
      });

      // ---------------------------------------------------------------- 4: why it wins
      const p4 = panel();
      label(p4, 30, PY + 16, `COSINE DISTANCE TO THE QUESTION · TOP ${K} AFTER THE DROP`);
      const AX0 = 80, AX1 = 900, AY = PY + 120, d0 = .2, d1 = .6;
      const ax = d => L(AX0, AX1, (d - d0) / (d1 - d0));
      S("path", { d: `M${AX0} ${AY} H${AX1}`, stroke: V("line"), "stroke-width": 2 }, p4);
      [.2, .3, .4, .5, .6].forEach(t => {
        S("path", { d: `M${ax(t)} ${AY} V${AY + 6}`, stroke: V("line"), "stroke-width": 1.5 }, p4);
        T(p4, ax(t), AY + 24, t.toFixed(1), 13, { "text-anchor": "middle", class: "mono", fill: V("muted") });
      });
      T(p4, AX1, AY + 44, "closer to the question ←", 13, { "text-anchor": "end", fill: V("muted") });
      const dots4 = d300.ids.map((id, i) => {
        const x = ax(d300.dist[i]), bad = isDrop(id), up = i % 2 ? 44 : 20;
        const g = S("g", {}, p4);
        const c = S("circle", { cx: x, cy: AY, r: 8, fill: V(bad ? "bad" : "teal") }, g);
        T(g, x, AY - up, `${short(id, 22)} ${d300.dist[i].toFixed(3)}`, 13, { "text-anchor": "middle", class: "mono", "font-weight": 700, fill: V(bad ? "bad" : "teal") });
        return { g, c, x };
      });
      const qw = new Set(Q1.toLowerCase().replace(/[^a-z0-9$' ]/g, " ").split(/\s+/).filter(w => w.length > 2));
      const wordsCard = (x, y, w, title, role, text) => {
        const g = S("g", {}, p4);
        card(g, x, y, w, 200, V(role));
        T(g, x + 14, y + 22, title, 13, { "font-weight": 700, fill: V(role) });
        const ls = wrap(text, Math.floor(w / 7.6)).slice(0, 8);
        ls.forEach((l, i) => {
          const t = S("text", { x: x + 14, y: y + 46 + i * 19, "font-size": 13 }, g);
          l.split(" ").forEach((wd, j) => {
            const hit = qw.has(wd.toLowerCase().replace(/[^a-z0-9$']/g, "")), can = wd.includes(CAN);
            S("tspan", { text: (j ? " " : "") + wd, ...(can ? { fill: V("lime"), "font-weight": 800 } : hit ? { fill: V("violet"), "font-weight": 800 } : {}) }, t);
          });
        });
        return g;
      };
      const ruleText = clean(D.index.hits[0].text).replace(/^Refunds and credits Refund limits /, "");
      wordsCard(30, PY + 190, 440, "dropped page, first sentences", "bad", clean(d300.texts[0]).replace(/^Refund approvals: 2026 update /, ""));
      wordsCard(490, PY + 190, 440, "handbook rule chunk refunds#0", "teal", ruleText);
      T(p4, 30, PY + 418, "bold: words shared with the question", 13, { fill: V("violet"), "font-weight": 700 });

      // ---------------------------------------------------------------- 5: near-copies
      const p5 = panel();
      label(p5, 30, PY + 16, `TOP ${K} SLOTS AFTER FIVE NEAR-COPIES · ONE WRITER IN RED`);
      const cells5 = [];
      D.queries.target.forEach((q, r) => {
        const row = D.flood[q.id], y = PY + 40 + r * 112;
        T(p5, 30, y + 18, short(q.q, 34), 13, { "font-weight": 700 });
        T(p5, 30, y + 38, `before: ${D.drop[q.id].baseline.filter(id => !isDrop(id)).length}/${K} handbook`, 13, { fill: V("muted") });
        row.ids.forEach((id, i) => {
          const x = 300 + i * 160, bad = isDrop(id);
          const rect = S("rect", { x, y, width: 148, height: 72, rx: 10, "stroke-width": 1.6 }, p5);
          T(p5, x + 12, y + 24, short(id.replace(/#0$/, "").replace(/^refund-/, ""), 18), 13, { class: "mono", "font-weight": 700 });
          T(p5, x + 12, y + 46, bad ? `claims ${D.declared[id.replace(/#\d+$/, "")]}` : "handbook", 13, { fill: V("muted") });
          if (bad) S("circle", { cx: x + 134, cy: y + 16, r: 5, fill: V("lime") }, p5);
          cells5.push({ rect, bad, k: (r * K + i) / (N * K) });
        });
      });
      const tot5 = T(p5, 30, PY + 392, `one writer: ${sumN(D.flood, "drop_slots")}/${N * K} slots · handbook rule retrieved for ${sumQ(D.flood, r => r.rule)}/${N} phrasings`, 15, { "font-weight": 800, fill: V("bad") });

      // ---------------------------------------------------------------- 6: the assembled prompt
      const p6 = panel();
      label(p6, 30, PY + 16, `USER TURN THE MODEL WOULD RECEIVE · ${CX.user_chars} CHARS · NO MODEL CALLED`);
      card(p6, 30, PY + 28, 600, 404, V("warn"));
      T(p6, 46, PY + 52, "Documents:", 13, { class: "mono", "font-weight": 700 });
      const blocks6 = CX.retrieved.map((h, i) => {
        const y = PY + 64 + i * 84, g = S("g", {}, p6);
        S("rect", { x: 46, y, width: 568, height: 80, rx: 8, fill: V(h.drop ? "bad" : "teal"), "fill-opacity": .1, stroke: V(h.drop ? "bad" : "teal"), "stroke-width": 1.2 }, g);
        T(g, 58, y + 19, `[${h.id.replace(/#\d+$/, "")}]`, 13, { class: "mono", "font-weight": 700, fill: V(h.drop ? "bad" : "teal") });
        T(g, 602, y + 19, `claims ${h.author}`, 13, { "text-anchor": "end", fill: V("muted") });
        rich(g, 58, y + 37, clean(h.text).replace(/^[^?]*?(Can I)/, "$1"), 84, 13, 3, [], { "font-size": 13 });
        return g;
      });
      T(p6, 46, PY + 420, `Question: ${CX.question}`, 13, { class: "mono", "font-weight": 700 });
      const stats6 = [[`${CX.drop_chunks}/${CX.retrieved.length}`, "excerpts from the dropper", "bad"],
        [`${CX.drop_chars}/${CX.all_chars}`, "characters of retrieved text", "bad"],
        [CX.canary ? "yes" : "no", `${CAN} in context`, "lime"],
        [CX.rule ? "present" : "absent", "refund rule (up to $500)", "teal"],
        [CX.caveat ? "present" : "absent", "invoice caveat", "teal"]].map(([big, small, role], i) => {
        const y = PY + 40 + i * 80, g = S("g", {}, p6);
        T(g, 660, y + 28, big, 28, { "font-weight": 800, fill: V(role) });
        T(g, 660, y + 52, small, 13, { fill: V("muted"), "font-weight": 700 });
        return g;
      });

      // ---------------------------------------------------------------- 7: signed ingestion
      const p7 = panel();
      label(p7, 30, PY + 16, "SIGNED INGESTION · HASH + WRITER SIGNATURE");
      const files7 = [...SG.accepted.map(f => [f, null]), ...SG.quarantined].map(([f, why], i) => {
        const y = PY + 34 + i * 31, g = S("g", {}, p7), ok = !why;
        const stamp = S("rect", { x: 30, y, width: 92, height: 24, rx: 12, fill: V(ok ? "ok" : "bad"), "fill-opacity": .16, stroke: V(ok ? "ok" : "bad"), "stroke-width": 1.3 }, g);
        T(g, 76, y + 17, ok ? "accept" : "quarantine", 13, { "text-anchor": "middle", "font-weight": 700, fill: V(ok ? "ok" : "bad") });
        T(g, 134, y + 17, f, 13, { class: "mono", fill: V(ok ? "teal" : "bad") });
        T(g, 586, y + 17, ok ? "writer docs-team" : why.replace("signature does not verify for docs-team", "copied signature fails"), 13, { "text-anchor": "end", fill: V("muted") });
        return { g, ok, k: i / (SG.accepted.length + SG.quarantined.length) };
      });
      label(p7, 626, PY + 16, `SYSIDX-SIGNED · TOP ${K}`);
      rich(p7, 626, PY + 40, `“${Q1}”`, 40, 13, 2, [], { "font-weight": 700 });
      SG.queries["refund-300"].ids.forEach((id, i) => {
        const y = PY + 78 + i * 44, g = S("g", {}, p7);
        card(g, 626, y, 304, 36, V("teal"));
        T(g, 640, y + 23, `${i + 1}`, 14, { "font-weight": 800 });
        T(g, 662, y + 23, id, 14, { class: "mono", "font-weight": 700, fill: V("teal") });
        T(g, 916, y + 23, "signed", 13, { "text-anchor": "end", fill: V("ok") });
      });
      [[`${sigSlots}/${N * K}`, "dropped slots, refund questions"], [`${sigCan}/${N}`, "canary in the top 4"],
        [`${SG.unverified_chunks}/${SG.open_chunks}`, "open-index chunks unverified"]].forEach(([big, small], i) => {
        T(p7, 626, PY + 290 + i * 46, big, 22, { "font-weight": 800, fill: V("ok") });
        T(p7, 700, PY + 290 + i * 46, small, 13, { fill: V("muted"), "font-weight": 700 });
      });
      T(p7, 30, PY + 420, `tamper test: $500 → $5000 in refunds.md → ${SG.tamper}`, 13, { fill: V("ok"), "font-weight": 700 });

      // ---------------------------------------------------------------- 8: collapse and cap
      const p8 = panel();
      label(p8, 30, PY + 16, `RE-SELECTING THE TOP ${K} FROM 12 CANDIDATES · ${N} REFUND QUESTIONS = ${N * K} SLOTS`);
      const rows8 = RR.map((r, i) => {
        const y = PY + 50 + i * 90, g = S("g", {}, p8);
        T(g, 30, y + 16, r.rule, 14, { "font-weight": 800 });
        T(g, 30, y + 38, `canary in ${r.canary}/${N} · refund rule in ${r.rule_kept}/${N}`, 13, { fill: V("muted") });
        const cells = Array.from({ length: N * K }, (_, j) => {
          const kind = j < r.drop_slots ? "bad" : j < r.filled ? "teal" : "none";
          return { el: S("rect", { x: 380 + j * 42, y, width: 34, height: 34, rx: 6, "stroke-width": 1.4 }, g), kind };
        });
        T(g, 930, y + 58, `${r.drop_slots}/${N * K} dropped · ${r.filled}/${N * K} filled`, 13, { "text-anchor": "end", "font-weight": 700, fill: V(r.drop_slots ? "bad" : "ok") });
        return cells;
      });
      T(p8, 30, PY + 400, "red: dropped page · blue: handbook · empty: slot left unfilled", 13, { fill: V("muted"), "font-weight": 700 });
      T(p8, 30, PY + 422, `copies overlap at Jaccard ${D.rerank.j_drop[0].toFixed(2)}–${D.rerank.j_drop[1].toFixed(2)}; handbook chunks at most ${D.rerank.j_handbook_max.toFixed(2)}; collapse threshold ${D.rerank.dedup}`, 13, { fill: V("muted") });

      // ---------------------------------------------------------------- 9: section chunks
      const p9 = panel();
      label(p9, 30, PY + 16, "THE FIVE RULE + CAVEAT QUESTIONS AGAIN");
      T(p9, 300, PY + 50, `caveat in top ${K}`, 13, { fill: V("muted"), "font-weight": 700 });
      T(p9, 450, PY + 50, "one chunk", 13, { fill: V("muted"), "font-weight": 700 });
      T(p9, 600, PY + 50, "names its section", 13, { fill: V("muted"), "font-weight": 700 });
      const dots9 = D.sections.configs.map((c, i) => {
        const y = PY + 82 + i * 52, sec = c.config === "section";
        T(p9, 30, y + 5, sec ? "sections (D3)" : c.config, 15, { class: "mono", "font-weight": 800, fill: V(sec ? "ok" : "ink") });
        T(p9, 170, y + 5, `${c.mean_chars} chars avg`, 13, { fill: V("muted") });
        const mk = (x0, k) => Array.from({ length: c.n }, (_, j) => ({
          el: S("circle", { cx: x0 + j * 22, cy: y, r: 8, "stroke-width": 1.6 }, p9), on: j < k, sec }));
        return [...mk(306, c.caveat), ...mk(456, c.together), ...mk(606, c.heading)];
      });
      const top9 = D.sections.top;
      card(p9, 30, PY + 300, 900, 110, V("ok"));
      T(p9, 46, PY + 324, `sections (D3), rank 1 for “${Q1}” · similarity ${top9.sim.toFixed(3)}`, 13, { fill: V("muted"), "font-weight": 700 });
      const [h9, b9] = top9.text.split("\n");
      T(p9, 46, PY + 346, h9, 14, { "font-weight": 800, fill: V("ok") });
      rich(p9, 46, PY + 368, b9, 118, 13, 2,
        [["refund up to $500", "teal"], ["This limit does not apply to orders paid by invoice", "warn"]]);

      // ---------------------------------------------------------------- state
      const PANELS = [p1, p2, p3, p4, p5, p6, p7, p8, p9];
      const st = {};
      for (let i = 1; i <= 9; i++) { st["a" + i] = 0; st["g" + i] = 0; }
      function target(n) {
        const t = {};
        for (let i = 1; i <= 9; i++) { t["a" + i] = i === n ? 1 : 0; t["g" + i] = i <= n ? 1 : 0; }
        return t;
      }
      const dot = (d, k) => A(d.el, {
        fill: k > 0.5 && d.on ? V(d.sec ? "ok" : "teal") : V("panel"),
        stroke: V(d.on ? (d.sec ? "ok" : "teal") : "line") });
      function draw(s) {
        PANELS.forEach((p, i) => A(p, { opacity: s["a" + (i + 1)], visibility: s["a" + (i + 1)] > 0.01 ? "visible" : "hidden" }));
        stages.forEach((sg, j) => {
          const w = HOT.reduce((a, list, i) => a + (list.includes(j) ? s["a" + (i + 1)] : 0), 0);
          A(sg.r, { stroke: V(w > 0.5 ? "violet" : "line"), "stroke-width": 1.8 + w * 1.2 });
          A(sg.t, { fill: V(w > 0.5 ? "violet" : "muted") });
        });
        badges.forEach((b, i) => A(b, { opacity: s["a" + (7 + i)] }));
        // 1: chunk tiles appear one by one
        tiles1.forEach(([r, t], i) => { const k = seg(s.g1, i / tiles1.length * .7, i / tiles1.length * .7 + .3); A(r, { opacity: k }); A(t, { opacity: k }); });
        // 2: result dots fill
        dots2.forEach((row, i) => [...row.cav, ...row.tog].forEach(d => dot(d, seg(s.g2, i * .18, i * .18 + .4))));
        // 3: the dropped page slides into rank 1
        const k3 = s.g3;
        after3.forEach((g, i) => A(g, { opacity: seg(k3, .2 + i * .12, .5 + i * .12), transform: `translate(0 ${(1 - seg(k3, .2 + i * .12, .5 + i * .12)) * -12})` }));
        A(can3, { opacity: seg(k3, .6, 1) });
        rowsQ.forEach((g, i) => A(g, { opacity: seg(k3, .5 + i * .06, .75 + i * .06) }));
        // 4: points move onto the axis
        dots4.forEach((d, i) => A(d.g, { opacity: seg(s.g4, i * .15, i * .15 + .4) }));
        // 5: slots turn red as the copies arrive
        cells5.forEach(c => {
          const on = c.bad && s.g5 > c.k * .8 + .1;
          A(c.rect, { fill: V(on ? "bad" : "teal"), "fill-opacity": on ? .18 : .1, stroke: V(on ? "bad" : "teal") });
        });
        A(tot5, { opacity: seg(s.g5, .7, 1) });
        // 6: excerpts fill the prompt
        blocks6.forEach((g, i) => A(g, { opacity: seg(s.g6, i * .15, i * .15 + .35) }));
        stats6.forEach((g, i) => A(g, { opacity: seg(s.g6, .5 + i * .06, .7 + i * .06) }));
        // 7: files get their stamps
        files7.forEach(f => A(f.g, { opacity: seg(s.g7, f.k * .7, f.k * .7 + .3) }));
        // 8: slot cells color in
        rows8.forEach((cells, i) => cells.forEach(c => {
          const k = seg(s.g8, i * .15, i * .15 + .4);
          const role = c.kind === "none" ? "line" : c.kind;
          A(c.el, { fill: c.kind === "none" ? V("panel") : V(role), "fill-opacity": c.kind === "none" ? 1 : .2 + .5 * k, stroke: V(role) });
        }));
        // 9: dots fill
        dots9.forEach((row, i) => row.forEach(d => dot(d, seg(s.g9, i * .18, i * .18 + .4))));
      }
      Object.assign(st, target(1));
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
