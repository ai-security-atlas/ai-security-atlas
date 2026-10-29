/* Explainer: attack-dependency (LAB-10). "from_pretrained ran my code": a model repo's config.json auto_map
 * makes from_pretrained() import Python files from the repo, a moved branch or tag delivers new code, and a
 * typosquatted package's .pth file runs at every Python start. Every file name, sha, diff line, output line
 * and verdict comes from window.LAB_DATA (data.js), which scripts/export_explainer_data.py parses from a
 * reference run (work/verify.log). The payload is the lab's inert canary.
 * Pattern: target(n) is a pure function of the 1-based step, draw(s) is a pure render of a numeric state,
 * step(n, dir) tweens forward by one step and snaps otherwise (labs/_explainer/README.md). */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp, E = X.ease;
  const D = window.LAB_DATA;
  const short = sha => sha.slice(0, 7);
  const cut = (s, n) => s == null ? "" : s.length > n ? s.slice(0, n - 1) + "…" : s;
  function wrap(s, n) {                     // greedy word wrap with hard breaks for long words
    const out = [];
    let line = "";
    for (let w of s.split(" ")) {
      while (w.length > n) { if (line) { out.push(line); line = ""; } out.push(w.slice(0, n)); w = w.slice(n); }
      if (!line) line = w; else if ((line + " " + w).length <= n) line += " " + w; else { out.push(line); line = w; }
    }
    if (line) out.push(line);
    return out;
  }
  const fileRole = f => /\.py$/.test(f) ? "violet" : /\.safetensors$/.test(f) ? "teal" : "muted";
  const modelCls = D.auto_map.find(a => /^AutoModel/.test(a[0]));
  const inj = D.diff.filter(l => l.trim() && !/^#/.test(l.trim()));         // the executable injected lines
  const MOD = [D.hunk, ...D.diff.filter(l => l.trim()), `class ${modelCls[2]}(PreTrainedModel): ...`];
  const iInj0 = 1 + D.diff.filter(l => l.trim()).findIndex(l => !/^#/.test(l.trim()));  // first injected statement
  const NL = MOD.length;
  const d1 = D.d1.filter(l => /^(REFUSED|VERIFIED)/.test(l));
  const revMoved = D.revisions[2];

  X.define({
    id: "attack-dependency",
    family: "family-supply",
    title: 'from_pretrained <span class="outline">ran</span> my code',
    legend: [{ role: "teal", label: "Weights / trusted packages" }, { role: "violet", label: "Repo code / loader" },
      { role: "bad", label: "Attacker's change" }, { role: "warn", label: "Model output" },
      { role: "lime", label: "Canary / side effect" }, { role: "ok", label: "Defense" }],
    steps: [
      { chapter: "System", label: "Code in the repo",
        caption: `A model repo can ship its own architecture as <span class="c-violet">Python files</span> next to the <span class="c-teal">weights</span>. <code>config.json</code>'s <code>auto_map</code> names those files, and <code>from_pretrained()</code> imports them to build the model.`,
        cmd: "docker compose run --rm workbench python attack-dependency/scripts/s01_hub_publish.py" },
      { chapter: "System", label: "Revisions are names",
        caption: `The hub is git. <code>main</code> and the tag <code>v1.0</code> are <em>names</em> that point at a commit; the commit sha is a hash of the content. Your team reviewed the code at <span class="c-ok">commit ${short(D.v10)}</span>.` },
      { chapter: "Attack", label: "A routine commit",
        caption: `Someone with push access commits "v1.1" as <span class="c-bad">acme-ci</span>: ${inj.length} <span class="c-bad">module-level lines</span> in <code>modeling_tinysent.py</code>, weights untouched. <code>main</code> now points at it.`,
        cmd: "docker compose run --rm workbench python attack-dependency/scripts/s02_push_update.py" },
      { chapter: "Mechanism", label: "Import is execution",
        caption: `With <code>trust_remote_code=True</code>, transformers copies the repo's <span class="c-violet">.py files</span> into its modules cache and imports them. Importing a module runs every top-level statement, including the <span class="c-bad">attacker's lines</span>, inside <code>from_pretrained()</code>.` },
      { chapter: "Impact", label: "It ran in the load",
        caption: `The inert payload wrote the canary <code class="c-lime">${D.canary}</code> to <code>${D.marker}</code> before the model existed. The <span class="c-warn">prediction</span> is exactly the reviewed one, so nothing looks wrong.`,
        cmd: "docker compose run --rm workbench python attack-dependency/scripts/s03_victim_load.py --revision main --trust-remote-code" },
      { chapter: "Impact", label: "A typo is enough",
        caption: `<code>pip install acme-tokenizr</code>, one letter off, installs a <span class="c-bad">typosquat</span> that depends on the real package. Its <code>.pth</code> file runs at every Python start, so <code class="c-lime">${D.canary}</code> fires before your <code>import acme_tokenizer</code>.`,
        cmd: "docker compose run --rm workbench python attack-dependency/scripts/s06_victim_install.py" },
      { chapter: "Defense", label: "Pin the reviewed sha",
        caption: `A force-push moved the tag <code>v1.0</code>, so <code>revision="v1.0"</code> now loads the attacker's code. The <span class="c-ok">policy</span>: remote code only for a full commit sha whose code files hash to the review. Everything else is refused before import.`,
        cmd: "docker compose run --rm workbench python attack-dependency/scripts/d1_pinned_load.py --revision dea887921ad77734f0ea49b53534d25faf7a8615" },
      { chapter: "Defense", label: "Hashes, not names",
        caption: `Install from a <span class="c-ok">lock file with hashes</span>. A typed name without a hash is refused, a same-version wheel from a compromised mirror fails its hash, and the locked install starts a clean Python.`,
        cmd: "docker compose run --rm workbench python attack-dependency/scripts/d2_require_hashes.py" },
      { chapter: "Defense", label: "Gate, then contain",
        caption: `A <span class="c-ok">CI gate</span> in a job with no network and no secrets reads the change without running it and fails it four times. Code you still must run goes in the <span class="c-ok">sandbox</span>: it runs, but cannot reach the network or your checkout.`,
        cmd: "docker compose run --rm sandbox python attack-dependency/scripts/d3_ci_gate.py --revision main --requirements work/requirements-pr.txt" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="A model repo's code imported by from_pretrained, a moved tag, a typosquatted package and four defenses"></svg>`,

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
      const arrow = (p, d, stroke = V("dim")) => S("path", { d, fill: "none", stroke, "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, p);
      const chip = (p, x, y, w, text, role, o = {}) => {
        const g = S("g", {}, p);
        S("rect", { x, y, width: w, height: 30, rx: 9, fill: V(role), "fill-opacity": .12, stroke: V(role), "stroke-width": 1.5 }, g);
        M(g, x + w / 2, y + 20, text, 13, { "text-anchor": "middle", fill: V(role), "font-weight": 700, ...o });
        return g;
      };

      // ------------------------------------------------------------------ scene A: the repo (steps 1-2)
      const gRepo = S("g", {}, svg);
      label(gRepo, 40, 92, "MODEL REPO ON THE LOCAL HUB");
      card(gRepo, 40, 104, 400, 360);
      M(gRepo, 60, 138, D.repo, 18, { "font-weight": 800 });
      T(gRepo, 60, 160, `tag v1.0 · commit ${short(D.v10)}`, 13, { fill: V("muted") });
      const rowY = {};
      D.files.forEach(([name, size], i) => {
        const y = 178 + i * 34, role = fileRole(name);
        rowY[name] = y + 15;
        const g = S("g", {}, gRepo);
        S("rect", { x: 92, y, width: 330, height: 28, rx: 8, fill: V(role === "muted" ? "panel-2" : role), "fill-opacity": role === "muted" ? 1 : .12, stroke: V(role === "muted" ? "line" : role), "stroke-width": 1.5 }, g);
        M(g, 104, y + 19, name, 13, { fill: V(role === "muted" ? "ink-2" : role), "font-weight": 700 });
        M(g, 410, y + 19, `${size} B`, 13, { "text-anchor": "end", fill: V("muted") });
      });
      const gAmap = S("g", {}, gRepo);
      const amapPaths = D.auto_map.map(([, file], i) => {
        const y0 = rowY["config.json"], y1 = rowY[file], x = 88 - i * 16;
        return S("path", { d: `M92 ${y0} C${x - 30} ${y0} ${x - 30} ${y1} 92 ${y1}`, fill: "none", stroke: V("violet"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, gAmap);
      });
      T(gAmap, 60, 372, "config.json auto_map:", 13, { fill: V("violet"), "font-weight": 700 });
      D.auto_map.forEach(([auto, file, cls], i) => {
        M(gAmap, 60, 396 + i * 40, `${cut(auto, 34)} →`, 13, { fill: V("ink-2") });
        M(gAmap, 76, 414 + i * 40, `${file} :: ${cut(cls, 22)}`, 13, { fill: V("violet"), "font-weight": 600 });
      });
      // from_pretrained box (step 1)
      const gLoad = S("g", {}, svg);
      arrow(gLoad, "M448 290 H508");
      label(gLoad, 520, 150, "LOADER");
      card(gLoad, 520, 162, 400, 230, V("violet"));
      M(gLoad, 540, 198, "AutoModelFor…from_pretrained(", 15, { "font-weight": 800 });
      M(gLoad, 556, 220, "repo, trust_remote_code=True)", 15, { "font-weight": 800 });
      ["1  read config.json", "2  auto_map → import the .py files", "3  load model.safetensors"].forEach((t, i) =>
        T(gLoad, 544, 262 + i * 30, t, 14, { fill: V(i === 1 ? "violet" : i === 2 ? "teal" : "ink-2"), "font-weight": i === 1 ? 700 : 500 }));
      T(gLoad, 544, 366, "→ a model whose class came from the repo", 13, { fill: V("muted") });

      // ------------------------------------------------------------------ scene B: git graph (steps 2-3, 7)
      const gGraph = S("g", {}, svg);
      const GX1 = 560, GX2 = 800, GY = 250;
      label(gGraph, 480, 92, "HUB REVISIONS (GIT)");
      card(gGraph, 480, 104, 440, 360);
      const edge = S("path", { d: `M${GX1} ${GY} H${GX2}`, stroke: V("line"), "stroke-width": 3 }, gGraph);
      const n1 = S("g", {}, gGraph);
      S("circle", { cx: GX1, cy: GY, r: 15, fill: V("panel"), stroke: V("ok"), "stroke-width": 3 }, n1);
      M(n1, GX1, GY + 42, short(D.v10), 14, { "text-anchor": "middle", "font-weight": 800 });
      T(n1, GX1, GY + 62, D.commits[D.commits.length - 1][1], 13, { "text-anchor": "middle", fill: V("muted") });
      const n2 = S("g", {}, gGraph);
      S("circle", { cx: GX2, cy: GY, r: 15, fill: V("panel"), stroke: V("bad"), "stroke-width": 3 }, n2);
      M(n2, GX2, GY + 42, short(D.main), 14, { "text-anchor": "middle", "font-weight": 800, fill: V("bad") });
      T(n2, GX2, GY + 62, D.commits[0][1], 13, { "text-anchor": "middle", fill: V("bad") });
      T(n2, GX2, GY + 80, cut(D.commits[0][2], 30), 13, { "text-anchor": "middle", fill: V("muted") });
      const ref = (txt, role, y) => {
        const g = S("g", {}, gGraph);
        const w = 14 + txt.length * 8.2;
        const stem = y < 0 ? S("path", { d: `M0 12 V${-y - 18}`, stroke: V(role), "stroke-width": 2 }, g) : null;
        S("rect", { x: -w / 2, y: -14, width: w, height: 26, rx: 13, fill: V("panel") }, g);   // opaque: hides stems behind it
        const box = S("rect", { x: -w / 2, y: -14, width: w, height: 26, rx: 13, fill: V(role), "fill-opacity": .14, stroke: V(role), "stroke-width": 1.5 }, g);
        const txtEl = M(g, 0, 4, txt, 13, { "text-anchor": "middle", fill: V(role), "font-weight": 800 });
        return { g, stem, box, txtEl };
      };
      const rTag = ref("v1.0 (tag)", "violet", -112), rMain = ref("main (branch)", "violet", -64);
      const rPin = ref(`reviewed sha ${short(D.v10)}…`, "ok", 132);
      const graphNote = T(gGraph, 500, 446, "branch, tag: movable names · sha: hash of the content", 13, { fill: V("muted") });
      const tagNote = S("g", {}, gGraph);
      D.tag_move.split(/\s{2,}/).forEach((t, i) => M(tagNote, 500, 412 + i * 22, cut(t.replace(/^\(|\)$/g, ""), 50), 13, { fill: V("bad"), "font-weight": i ? 400 : 700 }));

      // diff panel (step 3)
      const gDiff = S("g", {}, svg);
      label(gDiff, 40, 92, "GIT DIFF V1.0 MAIN", { fill: V("bad") });
      card(gDiff, 40, 104, 400, 360, V("bad"));
      M(gDiff, 56, 134, "modeling_tinysent.py", 15, { "font-weight": 800 });
      M(gDiff, 56, 160, cut(" " + D.hunk, 46), 13, { fill: V("muted") });
      const diffRows = D.diff.filter(l => l.trim()).map((l, i) => {
        const g = S("g", {}, gDiff), y = 186 + i * 26;
        S("rect", { x: 50, y: y - 17, width: 380, height: 23, rx: 4, fill: V("bad"), "fill-opacity": .1 }, g);
        M(g, 56, y, cut("+" + l, 46), 13, { fill: V(/^#/.test(l.trim()) ? "muted" : "bad"), "font-weight": 600 });
        return g;
      });
      T(gDiff, 56, 360, `${D.files.find(f => /safetensors/.test(f[0]))[0]}: unchanged`, 13, { fill: V("teal"), "font-weight": 700 });
      T(gDiff, 56, 384, "README.md: \"(v1.1)\" in the title", 13, { fill: V("muted") });
      T(gDiff, 56, 430, "nothing has run yet: these lines run", 13, { fill: V("muted") });
      T(gDiff, 56, 448, "only when someone imports the module", 13, { fill: V("muted") });

      // ------------------------------------------------------------------ scene C: import (steps 4-5)
      const gMech = S("g", {}, svg);
      const PIPE = [["snapshot main", short(D.main)], ["config.json", "auto_map"], ["copy .py files", "hf_modules/"],
        ["import module", "exec top level"], ["model", "forward()"]];
      const pipe = PIPE.map(([a, b], i) => {
        const x = 40 + i * 180, g = S("g", {}, gMech);
        S("rect", { x, y: 70, width: 160, height: 54, rx: 10, fill: V(i === 3 ? "bad" : i === 4 ? "warn" : "violet"), "fill-opacity": .1, stroke: V(i === 3 ? "bad" : i === 4 ? "warn" : "violet"), "stroke-width": 1.5 }, g);
        M(g, x + 80, 93, a, 13, { "text-anchor": "middle", "font-weight": 800 });
        M(g, x + 80, 113, b, 13, { "text-anchor": "middle", fill: V("muted") });
        if (i) arrow(gMech, `M${x - 18} 97 H${x - 4}`);
        return g;
      });
      const gMod = S("g", { class: "dimmable" }, gMech);
      label(gMod, 40, 158, "MODULE BODY, TOP TO BOTTOM");
      card(gMod, 40, 170, 540, 330);
      M(gMod, 56, 196, cut(D.module.replace(/\.[0-9a-f]{16}\./, ".…."), 60), 13, { fill: V("violet") });
      const modRows = MOD.map((l, i) => {
        const y = 230 + i * 28, g = S("g", {}, gMod);
        const bad = i > 0 && i < NL - 1;
        if (bad) S("rect", { x: 70, y: y - 18, width: 500, height: 24, rx: 4, fill: V("bad"), "fill-opacity": .1 }, g);
        M(g, 80, y, cut(l, 60), 13, { fill: V(bad ? (/^#/.test(l.trim()) ? "muted" : "bad") : i === NL - 1 ? "violet" : "ink-2"), "font-weight": bad ? 600 : 500 });
        return { g, y };
      });
      const cursor = S("path", { fill: V("warn") }, gMod);
      const gRun = S("g", {}, gMech);
      label(gRun, 600, 158, "WHAT IMPORT DOES");
      card(gRun, 600, 170, 320, 330);
      ["Python executes a module's", "top-level statements once, the", "first time it is imported.", "",
        "from_pretrained() imports the", "repo's modeling file to get the", "model class, so the attacker's", "lines run before any forward()."]
        .forEach((t, i) => T(gRun, 620, 206 + i * 22, t, 14, { fill: V(i > 3 ? "violet" : "ink-2") }));
      const gImp = S("g", {}, gMech);
      label(gImp, 600, 158, "VICTIM TERMINAL");
      const term = S("rect", { x: 600, y: 170, width: 320, height: 150, rx: 10, fill: V("panel-2"), stroke: V("lime"), "stroke-width": 1.5 }, gImp);
      const termTxt = Array.from({ length: 6 }, (_, i) => M(gImp, 612, 194 + i * 20, "", 13, { fill: V("lime") }));
      card(gImp, 600, 332, 320, 40, V("lime"));
      M(gImp, 614, 357, D.marker, 13, { fill: V("lime"), "font-weight": 700 });
      T(gImp, 600, 398, "prediction on main (tampered):", 13, { fill: V("muted") });
      M(gImp, 600, 418, cut(D.predict_main.replace(/^predict\('[^']*'\) -> /, ""), 40), 13, { fill: V("warn"), "font-weight": 700 });
      T(gImp, 600, 446, "prediction at the reviewed commit:", 13, { fill: V("muted") });
      M(gImp, 600, 466, cut(D.predict_reviewed.replace(/^predict\('[^']*'\) -> /, ""), 40), 13, { fill: V("warn"), "font-weight": 700 });
      T(gImp, 600, 492, D.predict_main === D.predict_reviewed ? "identical" : "different", 13, { fill: V("warn"), "font-weight": 800 });
      const pulse = S("circle", { cx: 320, r: 0, fill: "none", stroke: V("lime"), "stroke-width": 4 }, gMech);

      // ------------------------------------------------------------------ scene D: typosquat (step 6)
      const gPkg = S("g", {}, svg);
      label(gPkg, 40, 92, "LOCAL INDEX · WORK/INDEX/SIMPLE");
      card(gPkg, 40, 104, 300, 150);
      D.pkg.index.forEach(([proj, whl], i) => {
        const bad = proj !== "acme-tokenizer", y = 130 + i * 56;
        M(gPkg, 58, y + 6, proj, 15, { fill: V(bad ? "bad" : "teal"), "font-weight": 800 });
        M(gPkg, 58, y + 26, cut(whl, 33), 13, { fill: V("muted") });
      });
      const pipTxt = M(gPkg, 360, 150, "pip install acme-tokenizr", 14, { fill: V("bad"), "font-weight": 800 });
      const pipArrow = arrow(gPkg, "M350 172 H590", V("bad"));
      const pipOut = S("g", {}, gPkg);
      T(pipOut, 360, 200, "Successfully installed", 13, { fill: V("muted") });
      D.pkg.installed.replace(/^Successfully installed /, "").split(" ").forEach((w, i) =>
        M(pipOut, 360, 222 + i * 20, w, 13, { fill: V(/tokenizr/.test(w) ? "bad" : "teal"), "font-weight": 700 }));
      label(gPkg, 600, 92, "VENV SITE-PACKAGES");
      card(gPkg, 600, 104, 320, 200);
      const site = [...D.pkg.wheel.filter(f => !/dist-info/.test(f)), "acme_tokenizer/__init__.py"];
      const siteRows = site.map((f, i) => {
        const y = 134 + i * 30, pth = /\.pth$/.test(f), boot = /_boot/.test(f), real = /^acme_tokenizer\//.test(f);
        const g = S("g", {}, gPkg);
        if (pth) S("rect", { x: 610, y: y - 19, width: 300, height: 26, rx: 6, fill: V("bad"), "fill-opacity": .12, stroke: V("bad"), "stroke-width": 1.5 }, g);
        M(g, 620, y, cut(f, 34), 13, { fill: V(real ? "teal" : pth || boot ? "bad" : "ink-2"), "font-weight": pth ? 800 : 500 });
        return g;
      });
      M(gPkg, 620, 290, cut(D.pkg.pth, 34), 13, { fill: V("bad") });
      label(gPkg, 40, 336, "PYTHON START-UP IN THAT VENV");
      const START = [["interpreter starts", "muted"], ["site reads *.pth", "violet"], ["import …_boot", "bad"],
        ["canary fires", "lime"], ["import acme_tokenizer", "teal"]];
      const startRows = START.map(([t, role], i) => {
        const x = 40 + i * 178, g = S("g", {}, gPkg);
        S("rect", { x, y: 350, width: 170, height: 42, rx: 10, fill: V(role === "muted" ? "panel-2" : role), "fill-opacity": role === "muted" ? 1 : .12, stroke: V(role === "muted" ? "line" : role), "stroke-width": 1.5 }, g);
        M(g, x + 85, 376, cut(t, 22), 13, { "text-anchor": "middle", fill: V(role === "muted" ? "ink-2" : role), "font-weight": 700 });
        return g;
      });
      const pkgTerm = S("g", {}, gPkg);
      S("rect", { x: 40, y: 410, width: 880, height: 92, rx: 10, fill: V("panel-2"), stroke: V("lime"), "stroke-width": 1.5 }, pkgTerm);
      M(pkgTerm, 54, 434, "$ venv-victim/bin/python -c \"import acme_tokenizer; ...\"", 13, { fill: V("muted") });
      M(pkgTerm, 54, 458, cut(D.pkg.payload_line, 104), 13, { fill: V("lime"), "font-weight": 700 });
      M(pkgTerm, 54, 482, D.pkg.encode, 13, { fill: V("teal") });

      // ------------------------------------------------------------------ scene E: D1 policy (step 7; graph reused)
      const gD1 = S("g", {}, svg);
      label(gD1, 40, 92, "D1 · REVISION POLICY", { fill: V("ok") });
      card(gD1, 40, 104, 400, 360, V("ok"));
      T(gD1, 60, 136, "trust_remote_code only if:", 14, { "font-weight": 700 });
      T(gD1, 60, 160, "1  revision is a full commit sha", 13, { fill: V("ink-2") });
      T(gD1, 60, 182, "2  its code files hash to the review", 13, { fill: V("ink-2") });
      const d1Rows = [["--revision main", d1[0]], [`--revision ${short(D.main)}…`, d1[1]], [`--revision ${short(D.v10)}…`, d1[2]]]
        .map(([cmd, res], i) => {
          const g = S("g", {}, gD1), y = 226 + i * 76, okRow = /^VERIFIED/.test(res);
          M(g, 60, y, cmd, 13, { "font-weight": 800, fill: V(i === 2 ? "ok" : "bad") });
          wrap(res, 46).slice(0, 2).forEach((ln, k) => M(g, 60, y + 22 + k * 18, ln, 13, { fill: V("ok"), "font-weight": k ? 400 : 700 }));
          T(g, 418, y, okRow ? "✓" : "✕", 18, { "text-anchor": "end", fill: V(okRow ? "ok" : "bad"), "font-weight": 800 });
          return g;
        });

      // ------------------------------------------------------------------ scene F: hashes (step 8)
      const gHash = S("g", {}, svg);
      label(gHash, 40, 92, "D2 · PIP --REQUIRE-HASHES", { fill: V("ok") });
      const lockCard = S("g", {}, gHash);
      card(lockCard, 40, 104, 880, 58, V("ok"));
      M(lockCard, 58, 140, "work/requirements.lock   " + cut(D.d2.lock, 70), 14, { fill: V("ok"), "font-weight": 700 });
      const CASES = [["(a) a teammate's PR", D.d2.pr, D.d2.cases[0]], ["(b) compromised mirror", "same name and version, other bytes", D.d2.cases[1]],
        ["(c) the real index", "the reviewed wheel", D.d2.cases[2]]];
      const caseRows = CASES.map(([title, what, lines], i) => {
        const g = S("g", {}, gHash), y = 190 + i * 110, good = i === 2;
        card(g, 40, y, 880, 96, V(good ? "ok" : "line"));
        T(g, 58, y + 28, title, 14, { "font-weight": 800 });
        M(g, 58, y + 52, cut(what, 40), 13, { fill: V(good ? "teal" : "bad") });
        const res = lines.filter(l => /^(ERROR|Expected|Got|Successfully|exit)/.test(l));
        res.slice(0, 3).forEach((l, k) => M(g, 380, y + 28 + k * 22, cut(l, 62), 13, { fill: V(/^(ERROR|Got)/.test(l) ? "bad" : /^exit 0|^Successfully/.test(l) ? "ok" : "ink-2"), "font-weight": k ? 400 : 700 }));
        T(g, 900, y + 56, good ? "✓" : "✕", 22, { "text-anchor": "end", fill: V(good ? "ok" : "bad"), "font-weight": 800 });
        return g;
      });

      // ------------------------------------------------------------------ scene G: gate + sandbox (step 9)
      const gGate = S("g", {}, svg);
      label(gGate, 40, 92, "D3 · CI GATE (INSPECT JOB)", { fill: V("ok") });
      card(gGate, 40, 104, 450, 400, V("ok"));
      wrap(D.gate.context, 52).forEach((ln, i) => M(gGate, 58, 132 + i * 18, ln, 13, { fill: V("ok") }));
      T(gGate, 58, 186, "static: nothing is imported, installed or loaded", 13, { fill: V("muted") });
      const gateRows = D.gate.fail.map((l, i) => {
        const g = S("g", {}, gGate), y = 218 + i * 64;
        T(g, 58, y + 2, "✕", 16, { fill: V("bad"), "font-weight": 800 });
        wrap(l.replace(/^\[FAIL\] /, ""), 50).slice(0, 3).forEach((ln, k) => M(g, 80, y + k * 17, ln, 13, { fill: V(/typosquat/.test(ln) ? "bad" : "ink-2") }));
        return g;
      });
      const verdict = M(gGate, 58, 488, cut(D.gate.verdicts[0], 54), 13, { fill: V("bad"), "font-weight": 800 });
      const gBox = S("g", {}, svg);
      const iso = D.isolation;
      const wall = S("rect", { x: 510, y: 104, width: 410, height: 400, rx: 18, fill: V("ok"), "fill-opacity": .04, stroke: V("ok"), "stroke-width": 3, "stroke-dasharray": "10 6" }, gBox);
      label(gBox, 526, 132, "D4 · SANDBOX", { fill: V("ok") });
      wrap(iso.payload, 46).slice(0, 2).forEach((ln, i) => M(gBox, 526, 160 + i * 18, ln, 13, { fill: V("lime") }));
      M(gBox, 526, 204, `marker in sandbox: ${iso.sandbox_marker ? "True" : "False"} (/work, tmpfs)`, 13, { fill: V("lime"), "font-weight": 700 });
      const probes = [["dns canary.invalid", iso.dns.split(":")[0]], ["egress 192.0.2.1:9", iso.egress], ["write to /labs", iso.ro_write]]
        .map(([name, res], i) => {
          const y = 246 + i * 66, g = S("g", {}, gBox);
          M(g, 526, y, name, 13, { "font-weight": 700 });
          const line = S("path", { fill: "none", stroke: V("bad"), "stroke-width": 3, "stroke-linecap": "round" }, g);
          const x = T(g, 900, y + 22, "✕", 20, { "text-anchor": "end", fill: V("bad"), "font-weight": 800 });
          const r = M(g, 526, y + 42, cut(res, 44), 13, { fill: V("muted") });
          return { y: y + 16, line, x, r };
        });
      const hostTxt = M(gBox, 526, 488, `host work/canary-marker.txt: ${iso.host_marker}`, 13, { fill: V("ok"), "font-weight": 800 });

      // ------------------------------------------------------------------ state
      const base = { repo: 0, amap: 0, load: 0, graph: 0, c2: 0, tag: 0, diff: 0, mech: 0, cur: 0, fire: 0,
        pkg: 0, d1: 0, hash: 0, gate: 0 };
      const T_N = [null,
        { repo: 1, amap: 1, load: 1 },                 // 1 System: auto_map points at .py files
        { repo: 1, amap: 1, graph: 1 },                // 2 System: names vs commits
        { graph: 1, c2: 1, diff: 1 },                  // 3 Attack: the v1.1 commit, main moves
        { mech: 1, cur: NL - 1 },                      // 4 Mechanism: the import walks the module body
        { mech: 1, cur: NL - 1, fire: 1 },             // 5 Impact: the canary fired, output unchanged
        { pkg: 1 },                                    // 6 Impact: typosquat .pth at start-up
        { graph: 1, c2: 1, tag: 1, d1: 1 },            // 7 Defense: moved tag; the sha policy
        { hash: 1 },                                   // 8 Defense: require-hashes
        { gate: 1 },                                   // 9 Defense: CI gate + sandbox
      ];
      const target = n => ({ ...base, ...T_N[n] });
      const st = { ...base };

      function draw(s) {
        // A: repo + loader
        A(gRepo, { opacity: s.repo.toFixed(3) });
        const am = seg(s.amap, .3, 1);
        amapPaths.forEach(p => { p.style.strokeDasharray = "400"; p.style.strokeDashoffset = (400 * (1 - am)).toFixed(1); });
        A(gAmap, { opacity: seg(s.amap, .2, .6).toFixed(3) });
        A(gLoad, { opacity: seg(s.load, .4, 1).toFixed(3) });
        // B: graph
        A(gGraph, { opacity: s.graph.toFixed(3) });
        A(n2, { opacity: seg(s.c2, .2, .7).toFixed(3) });
        A(edge, { d: `M${GX1} ${GY} H${L(GX1, GX2, seg(s.c2, .2, .7)).toFixed(2)}` });
        const mx = L(GX1, GX2, E.inOut(seg(s.c2, .5, 1))), tx = L(GX1, GX2, E.inOut(seg(s.tag, .1, .7)));
        A(rMain.g, { transform: `translate(${mx.toFixed(2)} ${GY - 64})` });
        A(rTag.g, { transform: `translate(${tx.toFixed(2)} ${GY - 112})` });
        const tagRole = V(s.tag > .5 ? "bad" : "violet");
        A(rTag.box, { stroke: tagRole, fill: tagRole });
        A(rTag.txtEl, { fill: tagRole });
        A(rTag.stem, { stroke: tagRole });
        A(rPin.g, { transform: `translate(${GX1 + 20} ${GY + 112})` });
        A(tagNote, { opacity: seg(s.tag, .6, 1).toFixed(3) });
        A(graphNote, { opacity: (1 - seg(s.tag, 0, .3)).toFixed(3) });
        A(gDiff, { opacity: seg(s.diff, 0, .4).toFixed(3) });
        diffRows.forEach((g, i) => {
          const k = E.out(seg(s.diff, .3 + i * .08, .6 + i * .08));
          A(g, { opacity: k.toFixed(3), transform: `translate(${(30 * (1 - k)).toFixed(2)} 0)` });
        });
        // C: import
        A(gMech, { opacity: s.mech.toFixed(3) });
        const ci = Math.max(0, Math.min(NL - 1, s.cur));
        const iDone = Math.floor(ci + 1e-6);
        modRows.forEach((r, i) => A(r.g, { opacity: i <= iDone ? 1 : .35 }));
        const cy = L(modRows[0].y, modRows[NL - 1].y, ci / (NL - 1));
        A(cursor, { d: `M58 ${(cy - 12).toFixed(2)} l12 7 l-12 7 Z` });
        pipe.forEach((g, i) => A(g, { opacity: (i <= 3 || s.fire > .5 ? 1 : .45) }));
        A(gRun, { opacity: (1 - s.fire).toFixed(3) });
        A(gImp, { opacity: s.fire.toFixed(3) });
        const lines = wrap(D.payload_line, 38);
        let left = Math.round(lines.join("").length * seg(s.fire, .2, .7));
        termTxt.forEach((t, i) => { const ln = lines[i] || ""; t.textContent = ln.slice(0, Math.max(0, left)); left -= ln.length; });
        A(term, { "stroke-width": (1.5 + 1.5 * seg(s.fire, .6, 1)).toFixed(2) });
        const iFirst = modRows[iInj0];
        const pp = seg(s.fire, 0, .5);
        A(pulse, { cy: iFirst.y, r: (10 + 160 * E.out(pp)).toFixed(2), opacity: (pp > 0 && pp < 1 ? 1 - pp : 0).toFixed(3) });
        const focus = s.mech > .5 && s.fire < .5;
        gMod.classList.toggle("hot", focus || s.fire > .5);
        el.classList.toggle("lx-focus", s.mech > .5 && s.fire > .5);
        // D: typosquat
        A(gPkg, { opacity: seg(s.pkg, 0, .25).toFixed(3) });
        const pk = seg(s.pkg, .15, .45);
        A(pipArrow, { opacity: pk.toFixed(3) });
        A(pipTxt, { opacity: seg(s.pkg, .1, .25).toFixed(3) });
        A(pipOut, { opacity: seg(s.pkg, .35, .5).toFixed(3) });
        siteRows.forEach((g, i) => A(g, { opacity: seg(s.pkg, .35 + i * .04, .5 + i * .04).toFixed(3) }));
        startRows.forEach((g, i) => A(g, { opacity: seg(s.pkg, .55 + i * .07, .65 + i * .07).toFixed(3) }));
        A(pkgTerm, { opacity: seg(s.pkg, .85, 1).toFixed(3) });
        // E: D1
        A(gD1, { opacity: seg(s.d1, 0, .3).toFixed(3) });
        d1Rows.forEach((g, i) => A(g, { opacity: seg(s.d1, .5 + i * .15, .7 + i * .15).toFixed(3) }));
        // F: hashes
        A(gHash, { opacity: seg(s.hash, 0, .25).toFixed(3) });
        caseRows.forEach((g, i) => {
          const k = E.out(seg(s.hash, .25 + i * .22, .5 + i * .22));
          A(g, { opacity: k.toFixed(3), transform: `translate(0 ${(16 * (1 - k)).toFixed(2)})` });
        });
        // G: gate + sandbox
        A(gGate, { opacity: seg(s.gate, 0, .25).toFixed(3) });
        gateRows.forEach((g, i) => A(g, { opacity: seg(s.gate, .2 + i * .08, .35 + i * .08).toFixed(3) }));
        A(verdict, { opacity: seg(s.gate, .5, .6).toFixed(3) });
        A(gBox, { opacity: seg(s.gate, .45, .65).toFixed(3) });
        probes.forEach((p, i) => {
          const k = E.out(seg(s.gate, .6 + i * .08, .8 + i * .08));
          A(p.line, { d: `M526 ${p.y} H${L(526, 880, k).toFixed(2)}` });
          A(p.x, { opacity: seg(k, .9, 1).toFixed(3) });
          A(p.r, { opacity: seg(k, .9, 1).toFixed(3) });
        });
        A(wall, { "stroke-width": (3 + 2 * seg(s.gate, .85, 1)).toFixed(2) });
        A(hostTxt, { opacity: seg(s.gate, .9, 1).toFixed(3) });
      }

      draw(st);
      let gen = 0;
      const MS = [0, 900, 800, 1000, 1100, 900, 1200, 1000, 1100, 1200];
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          return api.tween(MS[n], k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); },
            n === 4 ? E.linear : E.inOut);
        },
      };
    },
  });
})();
