/* LAB-11 system-rag: "Five components of RAG" (10 steps; foundation lab, read as
 * System -> Risk -> Mechanism -> Observation -> Defense in the engine's five chapters).
 * A persistent pipeline strip across the top (chunk, embed, index, authorize, retrieve, assemble, generate)
 * shows which stage each step is about; the detail area below draws that stage's real output from the
 * reference run: the two chunks of Copperleaf's agreement, the 384-d vectors, the cosine-distance axis of
 * all 13 chunks, the assembled context, the answers and the defense counts. Every string and number comes
 * from window.LAB_DATA (data.js, exported by scripts/export_explainer_data.py).
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one step only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp, E = X.ease;
  const D = window.LAB_DATA;
  const CAN = D.canary, G = D.generate, I = D.instruction;
  const naive = G["sysrag-naive"], aclG = G["sysrag-acl"], chk = G["sysrag-naive-checked"];
  const sum = (rows, k) => Object.values(rows).reduce((a, r) => a + r[k], 0);
  const tot = rows => Object.values(rows).reduce((a, r) => a + r.trials, 0);
  const FAQ_Q = ["lamp-warranty", "lamp-discount"];      // both retrieve the FAQ once the where-filter is on
  const faqHits = rows => FAQ_Q.reduce((a, q) => a + rows[q].instruction, 0);
  const faqN = rows => FAQ_Q.reduce((a, q) => a + rows[q].trials, 0);
  const own = D.retrieve["own-reference"], probe = D.retrieve["probe-reference"];
  const pre = D.acl["own-reference"].pre;

  X.define({
    id: "system-rag",
    family: "family-retrieval",
    title: 'Five <span class="outline">components</span> of RAG',
    legend: [{ role: "teal", label: "Allowed for the caller" }, { role: "bad", label: "Not allowed / injected" },
      { role: "violet", label: "Embedder / model" }, { role: "warn", label: "Answer" }, { role: "lime", label: "Canary" },
      { role: "ok", label: "Defense" }],
    steps: [
      { chapter: "System", label: "Chunk",
        caption: `Documents are cut into chunks of whole sentences (${D.chunker.size} characters, ${D.chunker.overlap} overlap). Copperleaf's agreement becomes two: <code>CONFIDENTIAL</code> lands in #0, the contract reference in #1. Only the <span class="c-ok">metadata</span> copied onto each chunk still says whose it is.`,
        cmd: "docker compose run --rm workbench python system-rag/scripts/s01_chunk.py" },
      { chapter: "System", label: "Embed",
        caption: `The <span class="c-violet">embedder</span> (all-MiniLM-L6-v2) turns each chunk and the question into a ${D.embed.dims}-number unit vector. Similar wording points the same way: Harbor's question is closest to Copperleaf's chunk. Nothing about the tenant enters the vector.`,
        cmd: "docker compose run --rm workbench python system-rag/scripts/s02_embed.py" },
      { chapter: "System", label: "Index and rank",
        caption: `The chromadb index ranks all 13 chunks by cosine distance (1 − similarity) and returns the nearest 4. "Nearest" is the only rule: this retriever has no authorization stage.`,
        cmd: "docker compose run --rm workbench python system-rag/scripts/s03_retrieve.py" },
      { chapter: "Attack", label: "No access check",
        caption: `Harbor & Pine Goods asks "${D.embed.question}" Rank 1 is <span class="c-bad">Copperleaf's chunk</span>, which Harbor may not read; a probing question pulls three. The disclosure happens here, before any model runs.` },
      { chapter: "Mechanism", label: "Prompt assembly",
        caption: `The retrieved chunks are pasted into the user turn: ${D.assemble.question_chars} characters of question become ${D.assemble.user_chars}, with the <span class="c-bad">Copperleaf chunk</span> first. The model cannot tell a pasted chunk from anything else in its context.`,
        cmd: "docker compose run --rm workbench python system-rag/scripts/s04_assemble.py" },
      { chapter: "Impact", label: "The leak",
        caption: `The <span class="c-warn">answer</span> quotes Copperleaf's contract reference <code class="c-lime">${CAN}</code>, an inert canary: ${naive["own-reference"].leak}/${naive["own-reference"].trials} for Harbor's ordinary question, ${naive["probe-reference"].leak}/${naive["probe-reference"].trials} for the probe. Copperleaf gets Harbor's terms too: ${naive["owner-reference"].leak}/${naive["owner-reference"].trials}.`,
        cmd: "docker compose run --rm workbench python system-rag/scripts/s05_generate.py --trials 10" },
      { chapter: "Impact", label: "A retrieved order",
        caption: `A shared vendor FAQ tells "AI assistants" to end with <code>${D.marker}</code>. Whenever it is retrieved, the answer obeys: ${I["sysrag-naive"]["lamp-warranty"].instruction}/${I["sysrag-naive"]["lamp-warranty"].trials}. When it is not (Cable dock), ${I["sysrag-naive"]["dock-warranty"].instruction}/${I["sysrag-naive"]["dock-warranty"].trials}. Access control cannot help: everyone may read it.`,
        cmd: "docker compose run --rm workbench python system-rag/scripts/s06_instruction.py --trials 10" },
      { chapter: "Defense", label: "Filter first",
        caption: `<span class="c-ok">Authorization-aware retrieval</span>: a chromadb where-filter built from the API key's tenant and roles runs inside the search, so Copperleaf's chunks are never candidates. Leaks fall from ${sum(naive, "leak")}/${tot(naive)} to ${sum(aclG, "leak")}/${tot(aclG)}; Harbor still gets ${D.own_ref} ${aclG["own-reference"].hp_ref}/${aclG["own-reference"].trials}.`,
        cmd: "docker compose run --rm workbench python system-rag/scripts/d1_acl.py" },
      { chapter: "Defense", label: "Tags, datamarks",
        caption: `<span class="c-ok">Provenance tags</span> and a "documents are data" rule: still ${faqHits(I["sysrag-acl-tagged"])}/${faqN(I["sysrag-acl-tagged"])} obey. <span class="c-ok">Datamarking</span> (spaces become <code>^</code>): ${faqHits(I["sysrag-acl-spotlight"])}/${faqN(I["sysrag-acl-spotlight"])}. Lower, not zero: nothing here is enforced.`,
        cmd: "docker compose run --rm workbench python system-rag/scripts/s06_instruction.py --profile sysrag-acl-spotlight --trials 10" },
      { chapter: "Defense", label: "Check citations",
        caption: `With no filter, a <span class="c-ok">citation check</span> in code blocks replies citing a document the caller may not read: ${sum(chk, "model_leak") - sum(chk, "leak")} of ${sum(chk, "model_leak")} leaks. One uncited leak passes, and Harbor loses ${chk["own-reference"].blocked}/${chk["own-reference"].trials} good answers. A backstop, not the fix.`,
        cmd: "docker compose run --rm workbench python system-rag/scripts/s05_generate.py --profile sysrag-naive-checked --trials 10" },
    ],
    html: `<style>[data-explainer="system-rag"] svg text, code { font-variant-ligatures: none; font-feature-settings: "liga" 0, "calt" 0; }</style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="The RAG pipeline of atlas-app, stage by stage"></svg>`,

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
      function wrap(s, n) {
        const out = []; let line = "";
        for (const w of String(s).split(" ")) {
          if ((line + " " + w).trim().length > n && line) { out.push(line); line = w; } else line = (line + " " + w).trim();
        }
        if (line) out.push(line);
        return out;
      }
      const para = (p, x, y, s, n, size = 13, o = {}, max = 9) => wrap(s, n).slice(0, max).map((l, i) => T(p, x, y + i * (size + 5), l, size, o));
      const owned = id => (D.embed.all.find(c => c.id === id) || {}).ok;

      // ---------------------------------------------------------------- pipeline strip
      const STAGES = [["CHUNK", `${D.chunker.size} chars`], ["EMBED", `MiniLM · ${D.embed.dims}-d`], ["INDEX", "chromadb"],
        ["AUTHORIZE", ""], ["RETRIEVE", "top 4"], ["ASSEMBLE", "the prompt"], ["GENERATE", D.model]];
      const SW = 118, SG = 13, SX = 28, SY = 24, SH = 62;
      const stages = STAGES.map(([name, sub], i) => {
        const g = S("g", { class: "dimmable" }, svg), x = SX + i * (SW + SG);
        const r = S("rect", { x, y: SY, width: SW, height: SH, rx: 12, fill: V("panel"), "stroke-width": 1.8 }, g);
        const t = T(g, x + SW / 2, SY + 25, name, 13, { "text-anchor": "middle", "font-weight": 800, "letter-spacing": "1.5" });
        const st = T(g, x + SW / 2, SY + 45, sub, 13, { "text-anchor": "middle", fill: V("muted") });
        if (i) S("path", { d: `M${x - SG + 1} ${SY + SH / 2} H${x - 3}`, stroke: V("dim"), "stroke-width": 2, "marker-end": `url(#${arrowId})` }, g);
        return { g, r, t, st };
      });
      const [sChunk, sEmbed, sIndex, sAuth, sRetr, sAsm, sGen] = stages;
      T(svg, 480, 108, "the five components (chunk · embed · index · retrieve · assemble), the authorization stage, and generation", 13, { "text-anchor": "middle", fill: V("muted") });

      const PY = 128;                          // detail area: y 128..530
      const panel = () => S("g", { opacity: 0 }, svg);

      // ---------------------------------------------------------------- 1: chunk
      const p1 = panel();
      const CD = D.copperleaf_doc;
      label(p1, 40, PY + 14, `COPPERLEAF-AGREEMENT · ${CD.chars} CHARS · OWNER ${CD.tenant.toUpperCase()}`);
      const chunkEls = D.copperleaf.map((c, i) => {
        const y = PY + 28 + i * 176, g = S("g", {}, p1);
        const fr = S("rect", { x: 40, y, width: 520, height: 160, rx: 12, fill: V("panel"), "stroke-width": 1.6 }, g);
        T(g, 56, y + 24, `chunk #${c.i} · chars ${c.start}-${c.end}`, 13, { class: "mono", "font-weight": 700 });
        const ls = wrap(c.text, 74).slice(0, 6);
        ls.forEach((l, j) => {
          const hasCan = l.includes(CAN), conf = l.includes("CONFIDENTIAL");
          T(g, 56, y + 48 + j * 18, l, 13, { fill: V(hasCan ? "lime" : conf ? "warn" : "ink"), "font-weight": hasCan || conf ? 700 : 400 });
        });
        const meta = [`tenant=${CD.tenant}`, `shared=${CD.shared}`, `roles=${CD.roles.join(",")}`].map((m, k) => {
          const mx = 58 + k * 150, mg = S("g", {}, g);
          S("rect", { x: mx, y: y + 128, width: 140, height: 22, rx: 11, fill: V("ok"), "fill-opacity": .14, stroke: V("ok"), "stroke-width": 1.2 }, mg);
          T(mg, mx + 70, y + 144, m, 13, { "text-anchor": "middle", class: "mono", fill: V("ok"), "font-weight": 600 });
          return mg;
        });
        return { g, fr, meta };
      });
      // the whole corpus as chunk tiles, grouped by owner
      label(p1, 600, PY + 14, `ONE INDEX · ${D.embed.all.length} CHUNKS`);
      const OWN = [["shared", "shared (every caller)"], ["harbor", "harbor (the caller)"], ["copperleaf", "copperleaf"], ["atlas", "atlas staff only"]];
      const tiles = [];
      OWN.forEach(([o, name], r) => {
        const y = PY + 40 + r * 84;
        T(p1, 600, y + 14, name, 13, { "font-weight": 700 });
        D.embed.all.filter(c => c.owner === o).sort((a, b) => a.id < b.id ? -1 : 1).forEach((c, k) => {
          const x = 600 + k * 54, g = S("g", {}, p1);
          const rr = S("rect", { x, y: y + 24, width: 46, height: 38, rx: 8, "stroke-width": 1.4 }, g);
          if (c.id === "copperleaf-agreement#1") S("circle", { cx: x + 40, cy: y + 30, r: 4.5, fill: V("lime") }, g);
          T(g, x + 23, y + 48, "#" + c.id.split("#")[1], 13, { "text-anchor": "middle", class: "mono" });
          tiles.push({ rr, c });
        });
      });

      // ---------------------------------------------------------------- 2: embed
      const p2 = panel();
      label(p2, 40, PY + 14, `${D.embed.dims}-DIMENSIONAL UNIT VECTORS · FIRST 48 VALUES SHOWN`);
      T(p2, 40, PY + 42, `question (harbor-buyer): “${D.embed.question}”`, 14, { "font-weight": 700, fill: V("teal") });
      const rowsE = [{ id: "question", vec: D.embed.qvec, sim: null, owner: "harbor" }, ...D.embed.top];
      const vmax = Math.max(...rowsE.flatMap(r => r.vec.map(Math.abs)));
      const CX0 = 230, CW = 10, CG = 2;
      const vecEls = rowsE.map((r, i) => {
        const y = PY + 90 + i * 84, g = S("g", {}, p2);
        T(g, 40, y + 4, r.id, 13, { class: "mono", "font-weight": 700, fill: V(i === 0 ? "teal" : r.owner === "copperleaf" ? "bad" : "teal") });
        T(g, 40, y + 22, i === 0 ? "the query" : `owner ${r.owner}`, 13, { fill: V("muted") });
        S("path", { d: `M${CX0 - 4} ${y} H${CX0 + 48 * (CW + CG)}`, stroke: V("line"), "stroke-width": 1 }, g);
        const cells = r.vec.map((v, k) => S("rect", { x: CX0 + k * (CW + CG), y, width: CW, height: 0, rx: 2, fill: V("violet") }, g));
        const simT = T(g, 872, y + 6, r.sim == null ? "" : `cos ${r.sim.toFixed(3)}`, 15, { "text-anchor": "middle", class: "mono", "font-weight": 800, fill: V(r.owner === "copperleaf" ? "bad" : "teal") });
        return { r, cells, simT, y };
      });
      T(p2, 230, PY + 400, "bars: value of each dimension (up +, down −) · cos = dot product of two unit vectors", 13, { fill: V("muted") });

      // ---------------------------------------------------------------- 3, 4, 8: the distance axis
      const pAx = panel();
      const AX0 = 90, AX1 = 900, AY = PY + 150, d0 = .60, d1 = 1.0;
      const ax = d => L(AX0, AX1, (d - d0) / (d1 - d0));
      const axTitle = label(pAx, 40, PY + 14, "");
      S("path", { d: `M${AX0} ${AY} H${AX1}`, stroke: V("line"), "stroke-width": 2 }, pAx);
      [.6, .7, .8, .9, 1.0].forEach(t => {
        S("path", { d: `M${ax(t)} ${AY} V${AY + 6}`, stroke: V("line"), "stroke-width": 1.5 }, pAx);
        T(pAx, ax(t), AY + 24, t.toFixed(1), 13, { "text-anchor": "middle", class: "mono", fill: V("muted") });
      });
      T(pAx, AX1, AY + 44, "cosine distance to Harbor's question →", 13, { "text-anchor": "end", fill: V("muted") });
      let lastX = -99, lift = 0;
      const dots = D.embed.all.map((c, i) => {
        const x = ax(c.d);
        lift = x - lastX < 16 ? lift + 1 : 0; lastX = x;
        const y = AY - 16 - lift * 18;
        const g = S("g", {}, pAx);
        const dot = S("circle", { cx: x, cy: y, r: 7, "stroke-width": 2 }, g);
        const ring = c.id === "copperleaf-agreement#1" ? S("circle", { cx: x, cy: y, r: 11.5, fill: "none", stroke: V("lime"), "stroke-width": 2.5 }, g) : null;
        return { c, g, dot, ring, x, y, rank: i };
      });
      const cut = S("path", { d: "", stroke: V("violet"), "stroke-width": 2, "stroke-dasharray": "5 4" }, pAx);
      const cutT = T(pAx, 0, PY + 52, "top 4", 13, { fill: V("violet"), "font-weight": 700 });
      // the ranked list (step 4) and the filtered list (step 8)
      const pList = S("g", { opacity: 0 }, svg);
      const listCol = (p, x, title, hits) => {
        label(p, x, PY + 236, title);
        return hits.map((h, i) => {
          const y = PY + 250 + i * 40, g = S("g", {}, p);
          const r = S("rect", { x, y, width: 420, height: 32, rx: 8, "stroke-width": 1.3 }, g);
          T(g, x + 12, y + 21, `${i + 1}`, 13, { class: "mono", "font-weight": 800 });
          T(g, x + 34, y + 21, h.id, 13, { class: "mono", "font-weight": 700, fill: V(h.ok ? "teal" : "bad") });
          T(g, x + 250, y + 21, h.d.toFixed(4), 13, { class: "mono", fill: V("muted") });
          T(g, x + 408, y + 21, h.ok ? "allowed" : "NOT ALLOWED", 13, { "text-anchor": "end", "font-weight": 700, fill: V(h.ok ? "teal" : "bad") });
          if (h.canary) S("circle", { cx: x + 230, cy: y + 16, r: 5, fill: V("lime") }, g);
          A(r, { x: x, fill: V(h.ok ? "teal" : "bad"), "fill-opacity": .08, stroke: V(h.ok ? "teal" : "bad") });
          return g;
        });
      };
      const rowsA = listCol(pList, 40, "INNOCENT: " + `${own.filter(h => !h.ok).length} OF 4 NOT ALLOWED`, own);
      const rowsB = listCol(pList, 500, "PROBE: " + `${probe.filter(h => !h.ok).length} OF 4 NOT ALLOWED`, probe);
      const p8 = panel();
      card(p8, 40, PY + 222, 880, 64, V("ok"));
      T(p8, 56, PY + 246, "where = " + D.where, 13, { class: "mono", "font-weight": 700, fill: V("ok") });
      T(p8, 56, PY + 270, "built from the API key's principal, applied inside the vector search: unauthorized chunks are never ranked", 13, { fill: V("muted") });
      label(p8, 40, PY + 316, "CROSS-TENANT LEAKS IN THE ANSWERS · 3 QUESTIONS × 10 TRIALS");
      const leakBar = (p, y, name, n, d, role) => {
        T(p, 40, y + 17, name, 14, { "font-weight": 700 });
        S("rect", { x: 250, y, width: 560, height: 24, rx: 6, fill: V("line"), opacity: .5 }, p);
        const r = S("rect", { x: 250, y, width: 0, height: 24, rx: 6, fill: V(role) }, p);
        T(p, 826, y + 18, `${n}/${d}`, 15, { class: "mono", "font-weight": 800, fill: V(role) });
        return { r, k: n / d };
      };
      const b8 = [leakBar(p8, PY + 330, "no filter (naive)", sum(naive, "leak"), tot(naive), "bad"),
        leakBar(p8, PY + 364, "where-filter (sysrag-acl)", sum(aclG, "leak"), tot(aclG), "ok")];

      // ---------------------------------------------------------------- 5: assembly
      const p5 = panel();
      label(p5, 40, PY + 14, "THE MESSAGES THE MODEL RECEIVES (profile sysrag-naive, caller harbor-buyer)");
      const sysB = S("rect", { x: 40, y: PY + 30, width: 560, height: 54, rx: 10, fill: V("teal"), "fill-opacity": .08, stroke: V("teal"), "stroke-width": 1.5 }, p5);
      T(p5, 56, PY + 52, `system · operator · ${D.assemble.system_chars} chars`, 13, { class: "mono", "font-weight": 700, fill: V("teal") });
      T(p5, 56, PY + 72, "“" + wrap(D.system_head, 78)[0] + " …”", 13, { fill: V("muted") });
      card(p5, 40, PY + 96, 560, 296, V("line"));
      T(p5, 56, PY + 118, `user · client + 4 retrieved chunks · ${D.assemble.user_chars} chars`, 13, { class: "mono", "font-weight": 700 });
      const asmEls = D.assemble.blocks.map((b, i) => {
        const y = PY + 132 + i * 54, g = S("g", {}, p5);
        const r = S("rect", { x: 56, y, width: 528, height: 46, rx: 8, fill: V(b.ok ? "teal" : "bad"), "fill-opacity": .1, stroke: V(b.ok ? "teal" : "bad"), "stroke-width": 1.3 }, g);
        T(g, 70, y + 20, `[${b.id.split("#")[0]}]  chunk ${b.id}`, 13, { class: "mono", "font-weight": 700, fill: V(b.ok ? "teal" : "bad") });
        T(g, 70, y + 38, b.ok ? "allowed for harbor-buyer" : `contract reference ${CAN} · not allowed`, 13, { fill: V(b.ok ? "muted" : "lime"), "font-weight": b.ok ? 400 : 700 });
        return g;
      });
      const qB = S("g", {}, p5);
      S("rect", { x: 56, y: PY + 350, width: 528, height: 30, rx: 8, fill: V("teal"), "fill-opacity": .16, stroke: V("teal"), "stroke-width": 1.3 }, qB);
      T(qB, 70, PY + 370, `Question: ${D.embed.question}  (${D.assemble.question_chars} chars)`, 13, { "font-weight": 700, fill: V("teal") });
      S("path", { d: `M606 ${PY + 210} H668`, stroke: V("dim"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, p5);
      card(p5, 676, PY + 120, 244, 180, V("violet"));
      for (let i = 0; i < 5; i++) S("rect", { x: 696, y: PY + 160 + i * 24, width: 204, height: 14, rx: 5, fill: V("violet"), "fill-opacity": .12 + .05 * i }, p5);
      T(p5, 798, PY + 146, D.model, 14, { "text-anchor": "middle", class: "mono", "font-weight": 700 });
      T(p5, 798, PY + 292, "reads one context window", 13, { "text-anchor": "middle", fill: V("muted") });

      // ---------------------------------------------------------------- 6: the leak
      const p6 = panel();
      label(p6, 40, PY + 14, "HARBOR'S ORDINARY QUESTION · ONE ANSWER (seed 0)");
      const ans6 = S("rect", { x: 40, y: PY + 28, width: 880, height: 92, rx: 12, fill: V("warn"), "fill-opacity": .08, stroke: V("warn"), "stroke-width": 1.5 }, p6);
      wrap(D.leak_example, 110).slice(0, 3).forEach((l, i) => {
        const parts = l.split(CAN), t = T(p6, 58, PY + 56 + i * 22, "", 14, {});
        parts.forEach((pt, j) => {
          S("tspan", { text: pt, fill: V("warn") }, t);
          if (j < parts.length - 1) S("tspan", { text: CAN, fill: V("lime"), "font-weight": 800 }, t);
        });
      });
      label(p6, 40, PY + 158, "THE OTHER TENANT'S CONTRACT REFERENCE IN THE REPLY · 10 TRIALS EACH");
      const b6 = [leakBar(p6, PY + 176, "Harbor, ordinary question", naive["own-reference"].leak, naive["own-reference"].trials, "lime"),
        leakBar(p6, PY + 214, "Harbor, probing question", naive["probe-reference"].leak, naive["probe-reference"].trials, "lime"),
        leakBar(p6, PY + 252, "Copperleaf, own question", naive["owner-reference"].leak, naive["owner-reference"].trials, "bad")];
      T(p6, 250, PY + 310, `canary ${CAN} to Harbor (lime) · Harbor's ${D.own_ref} to Copperleaf (red): the leak runs both ways`, 13, { fill: V("muted") });
      T(p6, 40, PY + 350, `Total: ${sum(naive, "leak")}/${tot(naive)} replies carry the other tenant's reference. The model did what it was asked: answer from the documents.`, 14, { "font-weight": 600 });

      // ---------------------------------------------------------------- 7: a retrieved order
      const p7 = panel();
      label(p7, 40, PY + 14, "VENDOR-ORBIT-FAQ#0 · SHARED · SOURCE: VENDOR UPLOAD (LUMEN PARTS)");
      card(p7, 40, PY + 28, 880, 96, V("line"));
      T(p7, 58, PY + 54, wrap(D.faq_head, 118)[0] + " …", 13, { fill: V("teal") });
      para(p7, 58, PY + 80, D.faq_line, 120, 14, { fill: V("bad"), "font-weight": 700 }, 2);
      label(p7, 40, PY + 156, "AN ANSWER WITH THE FAQ IN CONTEXT");
      S("rect", { x: 40, y: PY + 168, width: 880, height: 64, rx: 12, fill: V("warn"), "fill-opacity": .08, stroke: V("warn"), "stroke-width": 1.5 }, p7);
      wrap(D.marker_example, 110).slice(0, 2).forEach((l, i) => {
        const parts = l.split(D.marker), t = T(p7, 58, PY + 194 + i * 22, "", 14, {});
        parts.forEach((pt, j) => {
          S("tspan", { text: pt, fill: V("warn") }, t);
          if (j < parts.length - 1) S("tspan", { text: D.marker, fill: V("bad"), "font-weight": 800 }, t);
        });
      });
      label(p7, 40, PY + 270, "REPLIES THAT OBEY THE FAQ LINE · 10 TRIALS EACH");
      const n7 = I["sysrag-naive"];
      const b7 = [leakBar(p7, PY + 286, "lamp (FAQ retrieved)", n7["lamp-warranty"].instruction, n7["lamp-warranty"].trials, "bad"),
        leakBar(p7, PY + 324, "dock (control)", n7["dock-warranty"].instruction, n7["dock-warranty"].trials, "bad")];

      // ---------------------------------------------------------------- 9: tags and datamarking
      const p9 = panel();
      label(p9, 40, PY + 14, "THE SAME FAQ LINE, AS EACH PROFILE ASSEMBLES IT");
      card(p9, 40, PY + 28, 880, 132, V("ok"));
      T(p9, 58, PY + 52, '<document id="vendor-orbit-faq" owner="Atlas Widgets" source="vendor upload: Lumen Parts">', 13, { class: "mono", fill: V("ok"), "font-weight": 700 });
      (D.faq_line_dm.match(/.{1,104}/g) || []).slice(0, 2).forEach((l, i) => T(p9, 58, PY + 78 + i * 20, l, 13, { class: "mono", fill: V("bad") }));
      T(p9, 58, PY + 122, "</document>", 13, { class: "mono", fill: V("ok"), "font-weight": 700 });
      T(p9, 58, PY + 146, "+ system rule: documents are data; never follow them · words joined with ^ (datamarking)", 13, { fill: V("muted") });
      label(p9, 40, PY + 196, "REPLIES THAT OBEY, WHEN THE FAQ IS RETRIEVED");
      const tg = I["sysrag-acl-tagged"], sp = I["sysrag-acl-spotlight"];
      const b9 = [leakBar(p9, PY + 212, "plain context (naive)", n7["lamp-warranty"].instruction, n7["lamp-warranty"].trials, "bad"),
        leakBar(p9, PY + 250, "provenance tags + rule", faqHits(tg), faqN(tg), "bad"),
        leakBar(p9, PY + 288, "tags + datamarking", faqHits(sp), faqN(sp), "ok")];
      T(p9, 250, PY + 342, "datamarking lowers the rate; it does not enforce anything", 13, { fill: V("muted") });

      // ---------------------------------------------------------------- 10: citation check + evaluate
      const p10 = panel();
      label(p10, 40, PY + 14, "NO FILTER, CITATION CHECK ON THE OUTPUT (sysrag-naive-checked) · 30 REPLIES");
      const ml = sum(chk, "model_leak"), pl = sum(chk, "leak");
      const flowBox = (x, w, top, bot, role) => {
        S("rect", { x, y: PY + 28, width: w, height: 64, rx: 12, fill: V(role), "fill-opacity": .1, stroke: V(role), "stroke-width": 1.5 }, p10);
        T(p10, x + w / 2, PY + 56, top, 15, { "text-anchor": "middle", "font-weight": 800, fill: V(role), class: "mono" });
        T(p10, x + w / 2, PY + 78, bot, 13, { "text-anchor": "middle", fill: V("muted") });
      };
      flowBox(40, 250, `${ml}/${tot(chk)}`, "model replies with a leak", "bad");
      flowBox(330, 280, `${ml - pl} blocked`, "cite a document not allowed", "ok");
      flowBox(650, 270, `${pl} passed`, "leaked without a citation", "lime");
      for (const x of [292, 612]) S("path", { d: `M${x} ${PY + 60} H${x + 32}`, stroke: V("dim"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, p10);
      T(p10, 40, PY + 120, `Cost: Harbor's ordinary question blocked ${chk["own-reference"].blocked}/${chk["own-reference"].trials} times, good answer and all.`, 14, { "font-weight": 600 });
      label(p10, 40, PY + 160, `EVALUATE · ${D.eval_trials} TRIALS PER QUESTION`);
      const cols = [["leak", 470], ["instruction", 650], ["answered", 830]];
      cols.forEach(([c, x]) => T(p10, x, PY + 160, c, 13, { "text-anchor": "middle", fill: V("muted"), "font-weight": 700 }));
      const evRows = Object.entries(D.evaluate).map(([p, r], i) => {
        const y = PY + 172 + i * 38, g = S("g", {}, p10);
        T(g, 40, y + 21, p, 14, { class: "mono", "font-weight": 700 });
        cols.forEach(([c, x]) => {
          const [a, b] = r[c], bad = c === "answered" ? a < b : a > 0;
          S("rect", { x: x - 70, y: y + 4, width: 140, height: 24, rx: 6, fill: V(bad ? "bad" : "ok"), "fill-opacity": .14, stroke: V(bad ? "bad" : "ok"), "stroke-width": 1 }, g);
          T(g, x, y + 21, `${a}/${b}`, 13, { "text-anchor": "middle", class: "mono", "font-weight": 700, fill: V(bad ? "bad" : "ok") });
        });
        return g;
      });

      // ---------------------------------------------------------------- state
      const base0 = { p1: 0, p2: 0, ax: 0, col: 0, list: 0, flt: 0, p5: 0, p6: 0, p7: 0, p8: 0, p9: 0, p10: 0, gate: 0, chk: 0 };
      const T_N = [null,
        { p1: 1 },                                   // 1 System: chunk
        { p2: 1 },                                   // 2 System: embed
        { ax: 1 },                                   // 3 System: index and rank
        { ax: 1, col: 1, list: 1 },                  // 4 Attack (risk): no access check
        { p5: 1 },                                   // 5 Mechanism: prompt assembly
        { p6: 1 },                                   // 6 Impact (observation): the leak
        { p7: 1 },                                   // 7 Impact: a retrieved order
        { ax: 1, col: 1, flt: 1, p8: 1, gate: 1 },   // 8 Defense: filter first
        { p9: 1, gate: 1 },                          // 9 Defense: tags and datamarking
        { p10: 1, gate: 1, chk: 1 },                 // 10 Defense: citation check + evaluate
      ];
      const target = n => ({ ...base0, ...T_N[n] });
      const st = { ...base0 };

      function draw(s) {
        // pipeline
        const on = s.gate > .5;
        A(sAuth.r, { stroke: V(on ? "ok" : "bad"), "stroke-dasharray": on ? "" : "6 5", fill: V(on ? "ok" : "panel"), "fill-opacity": on ? .12 : 1 });
        A(sAuth.t, { fill: V(on ? "ok" : "bad") });
        sAuth.st.textContent = on ? "where-filter" : "missing";
        A(sAuth.st, { fill: V(on ? "ok" : "bad") });
        sGen.st.textContent = s.chk > .5 ? "+ cite check" : D.model;
        A(sGen.st, { fill: V(s.chk > .5 ? "ok" : "muted") });
        stages.forEach(x => { if (x !== sAuth) A(x.r, { stroke: V(x === sEmbed || x === sGen ? "violet" : "line") }); });

        // 1
        A(p1, { opacity: s.p1.toFixed(3) });
        chunkEls.forEach((c, i) => {
          A(c.g, { opacity: seg(s.p1, i * .2, .5 + i * .2).toFixed(3) });
          A(c.fr, { stroke: V("line") });
          c.meta.forEach((m, k) => A(m, { opacity: seg(s.p1, .5 + k * .12, .8 + k * .07).toFixed(3) }));
        });
        tiles.forEach(t => A(t.rr, { fill: V(t.c.ok ? "teal" : "bad"), "fill-opacity": .14, stroke: V(t.c.ok ? "teal" : "bad") }));

        // 2
        A(p2, { opacity: s.p2.toFixed(3) });
        vecEls.forEach((v, i) => {
          const k = E.out(seg(s.p2, .1 + i * .15, .6 + i * .12));
          v.r.vec.forEach((x, j) => {
            const h = Math.abs(x) / vmax * 34 * k;
            A(v.cells[j], { y: (x >= 0 ? v.y - h : v.y).toFixed(2), height: h.toFixed(2), "fill-opacity": (.35 + .65 * Math.abs(x) / vmax).toFixed(3) });
          });
          A(v.simT, { opacity: k.toFixed(3) });
        });

        // 3, 4, 8: axis
        A(pAx, { opacity: s.ax.toFixed(3) });
        axTitle.textContent = s.flt > .5 ? "WITH THE WHERE-FILTER: ONLY CHUNKS HARBOR MAY READ ARE RANKED"
          : s.col > .5 ? "THE SAME RANKING, COLORED BY WHO MAY READ EACH CHUNK" : "ALL 13 CHUNKS BY COSINE DISTANCE TO HARBOR'S QUESTION";
        const kept = D.embed.all.filter(c => s.flt > .5 ? c.ok : true);
        const cutD = (kept[3].d + kept[4].d) / 2;
        const cx = ax(cutD);
        A(cut, { d: `M${cx.toFixed(2)} ${PY + 40} V${AY + 8}` });
        A(cutT, { x: (cx + 8).toFixed(2) });
        dots.forEach(d => {
          const appear = seg(s.ax, .05 + d.rank * .04, .35 + d.rank * .04);
          const gone = !d.c.ok ? seg(s.flt, .1, .6) : 0;
          const role = s.col > .5 ? (d.c.ok ? "teal" : "bad") : "violet";
          A(d.dot, { fill: V(role), "fill-opacity": .25, stroke: V(role), r: 7 });
          A(d.g, { opacity: (appear * (1 - .85 * gone)).toFixed(3) });
          if (d.ring) A(d.ring, { opacity: (s.col > .5 ? 1 : 0) });
        });
        A(pList, { opacity: s.list.toFixed(3) });
        [...rowsA, ...rowsB].forEach((g, i) => A(g, { opacity: seg(s.list, .1 + (i % 4) * .15, .4 + (i % 4) * .15).toFixed(3) }));
        A(p8, { opacity: s.p8.toFixed(3) });
        b8.forEach((b, i) => A(b.r, { width: (560 * b.k * E.out(seg(s.p8, .3 + i * .2, .8 + i * .1))).toFixed(2) }));

        // 5
        A(p5, { opacity: s.p5.toFixed(3) });
        asmEls.forEach((g, i) => A(g, { opacity: seg(s.p5, .15 + i * .12, .45 + i * .12).toFixed(3) }));
        A(qB, { opacity: seg(s.p5, 0, .3).toFixed(3) });
        A(sysB, { stroke: V("teal") });

        // 6, 7
        A(p6, { opacity: s.p6.toFixed(3) });
        A(ans6, { stroke: V("warn") });
        b6.forEach((b, i) => A(b.r, { width: (560 * b.k * E.out(seg(s.p6, .25 + i * .15, .7 + i * .1))).toFixed(2) }));
        A(p7, { opacity: s.p7.toFixed(3) });
        b7.forEach((b, i) => A(b.r, { width: (560 * b.k * E.out(seg(s.p7, .3 + i * .2, .8 + i * .1))).toFixed(2) }));

        // 9, 10
        A(p9, { opacity: s.p9.toFixed(3) });
        b9.forEach((b, i) => A(b.r, { width: (560 * b.k * E.out(seg(s.p9, .2 + i * .2, .6 + i * .15))).toFixed(2) }));
        A(p10, { opacity: s.p10.toFixed(3) });
        evRows.forEach((g, i) => A(g, { opacity: seg(s.p10, .3 + i * .1, .5 + i * .1).toFixed(3) }));

        // focus: which pipeline stage this step is about
        const hot = s.p1 > .5 ? [sChunk] : s.p2 > .5 ? [sEmbed] : s.p8 > .5 ? [sAuth, sRetr] : s.list > .5 ? [sAuth, sRetr]
          : s.ax > .5 ? [sIndex, sRetr] : s.p5 > .5 || s.p9 > .5 ? [sAsm] : s.p6 > .5 ? [sGen] : s.p7 > .5 ? [sAsm, sGen]
          : s.p10 > .5 ? [sGen] : null;
        stages.forEach(x => x.g.classList.toggle("hot", !!hot && hot.includes(x)));
        el.classList.toggle("lx-focus", !!hot);
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          return api.tween(n === 2 || n === 3 || n === 8 ? 900 : 700, k => { if (g !== gen) return; X.lerpState(st, from, to, X.clamp(k)); draw(st); }, E.inOut);
        },
      };
    },
  });
})();
