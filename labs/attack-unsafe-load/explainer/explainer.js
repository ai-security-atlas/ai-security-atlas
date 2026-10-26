/* Explainer: attack-unsafe-load (LAB-01). "Loading is executing": the pickle program inside a .pt file
 * runs opcode by opcode during torch.load(), and two opcodes (GLOBAL + REDUCE) are enough to call any function.
 * Every opcode, stack entry, output line and error string comes from window.LAB_DATA (data.js), which
 * scripts/export_explainer_data.py writes from a reference container run. The payload is the lab's inert canary.
 * Pattern: target(n) is a pure function of the 1-based step, draw(s) is a pure render of a numeric state,
 * step(n, dir) tweens forward by one step and snaps otherwise (labs/_explainer/README.md). */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp, E = X.ease;
  const D = window.LAB_DATA;
  const OPS = D.malicious_ops, BOPS = D.benign_ops, TR = D.trace;
  const isInj = r => r[0] >= D.injected[0] && r[0] <= D.injected[1];
  const iSplit = OPS.findIndex(isInj);                                          // first injected opcode
  const nInj = OPS.filter(isInj).length;
  const iGlobal = OPS.findIndex(r => r[1] === "GLOBAL" && / exec$/.test(r[2])); // GLOBAL '__builtin__ exec'
  const iReduce = OPS.findIndex((r, i) => i > iGlobal && r[1] === "REDUCE");    // the call
  const iTensor = OPS.findIndex(r => r[2] === "'0.bias'");                       // first tensor rebuilt just before

  // opcode → role: what kind of work the VM does (injected rows are always attacker-controlled)
  const opRole = r => isInj(r) ? "bad"
    : /^(GLOBAL|REDUCE|BUILD|SETITEMS?)$/.test(r[1]) ? "violet"
    : /^(PROTO|MARK|BINPUT|BINGET|STOP)$/.test(r[1]) ? "muted" : "teal";
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
  const errShort = D.weights_only_error.replace(/(add_safe_globals\(\[exec\]\)`).*/, "$1 …");

  X.define({
    id: "attack-unsafe-load",
    family: "family-supply",
    title: 'Loading <span class="outline">is</span> executing',
    legend: [{ role: "teal", label: "Tensor data / benign opcodes" }, { role: "bad", label: "Injected opcodes" },
      { role: "violet", label: "Pickle VM / callables" }, { role: "warn", label: "Model output" },
      { role: "lime", label: "Canary / side effect" }, { role: "ok", label: "Defense" }],
    steps: [
      { chapter: "System", label: "Looks like data",
        caption: `A checkpoint looks like data: <span class="c-teal">weights</span> in a file. But <code>torch.load()</code> does not just read it. It runs a tiny <span class="c-violet">virtual machine</span> that rebuilds the model's tensors, then the <span class="c-warn">model</span> answers.`,
        cmd: "docker compose run --rm workbench python attack-unsafe-load/scripts/s01_inspect_benign.py" },
      { chapter: "System", label: "It's a ZIP",
        caption: `Zoom in: <code>.pt</code> is a ZIP archive. The <span class="c-teal">tensor bytes</span> sit in <code>data/0..3</code>. The structure lives in <code>data.pkl</code>, a <span class="c-violet">pickle program</span> that says how to put the bytes back together.`,
        cmd: "docker compose run --rm workbench python attack-unsafe-load/scripts/s01_inspect_benign.py" },
      { chapter: "Attack", label: "Extra opcodes",
        caption: `The attacker hides an object with a custom <code>__reduce__</code> in <code>state_dict._metadata</code>. Saving it adds <span class="c-bad">${nInj} opcodes</span> to <code>data.pkl</code>. The weights stay byte-for-byte identical, so the file still loads as the same model.`,
        cmd: "docker compose run --rm workbench python attack-unsafe-load/scripts/s02_craft_payload.py" },
      { chapter: "Mechanism", label: "A stack machine",
        caption: `Unpickling executes the opcodes one by one. Most push <span class="c-teal">data</span> onto a stack or call a <span class="c-violet">rebuild function</span>: here <code>_rebuild_tensor_v2</code> just turned storage 0 into the first <span class="c-teal">3×4 tensor</span>.` },
      { chapter: "Mechanism", label: "GLOBAL + REDUCE",
        caption: `Two opcodes make it dangerous. <code>GLOBAL</code> imports <em>any</em> callable by name, here <span class="c-bad"><code>exec</code></span>. The next ones push the attacker's code string, and <code>REDUCE</code> calls the callable with it.` },
      { chapter: "Impact", label: "It ran during load",
        caption: `<code>REDUCE</code> runs <code>exec(code)</code>. The inert payload writes the canary <code class="c-lime">${D.canary}</code> to <code>${D.marker}</code> before any <code>forward()</code>. The <span class="c-warn">model output</span> is unchanged, so the victim sees nothing wrong.`,
        cmd: "docker compose run --rm workbench python attack-unsafe-load/scripts/s03_victim_load.py work/malicious.pt unsafe" },
      { chapter: "Defense", label: "Allowlist gate",
        caption: `Today's default, <code>weights_only=True</code>, is an <span class="c-ok">allowlist</span>: <code>GLOBAL exec</code> is not on it, so the load stops and no marker appears. But the error suggests <code>safe_globals([exec])</code>, and following that advice <span class="c-warn">reopens the hole</span>.`,
        cmd: "docker compose run --rm workbench python attack-unsafe-load/scripts/s03_victim_load.py work/malicious.pt" },
      { chapter: "Defense", label: "No VM at all",
        caption: `The same weights as <code>model.safetensors</code>: an 8-byte length, a <span class="c-ok">JSON header</span> and flat <span class="c-teal">tensor bytes</span>, ${D.st_layout.len + D.st_layout.header + D.st_layout.data} bytes in all. There are no opcodes, so there is nothing to execute.`,
        cmd: "docker compose run --rm workbench python attack-unsafe-load/scripts/s06_safetensors.py" },
      { chapter: "Defense", label: "Contain what still runs",
        caption: `When you must load a pickle, do it in a <span class="c-ok">sandbox</span>: no network, a read-only checkout, a throwaway <code>/work</code>. The payload still runs, but DNS, egress and writes to <code>/labs</code> fail, and the host <code>work/</code> stays empty.`,
        cmd: "docker compose run --rm sandbox python attack-unsafe-load/scripts/d2_isolation_probe.py work/malicious.pt" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="The pickle program inside a PyTorch checkpoint, executed opcode by opcode during torch.load"></svg>`,

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

      // ------------------------------------------------------------------ scene A: system (steps 1-2)
      const gSys = S("g", {}, svg);
      const gFile = S("g", {}, gSys);
      label(gFile, 50, 160, "CHECKPOINT");
      card(gFile, 50, 172, 230, 200, V("teal"));
      M(gFile, 70, 206, "model.pt", 20, { "font-weight": 800 });
      T(gFile, 70, 230, "weights in a file?", 13, { fill: V("muted") });
      const wmax = Math.max(...Object.values(D.weights).flat().map(Math.abs));
      const grid = (name, x0, y0, rows, cols) => D.weights[name].forEach((v, i) =>
        S("rect", { x: x0 + (i % cols) * 17, y: y0 + Math.floor(i / cols) * 17, width: 14, height: 14, rx: 4,
          fill: V("teal"), opacity: (.2 + .8 * Math.abs(v) / wmax).toFixed(3) }, gFile));
      grid("0.weight", 70, 250, 3, 4); grid("0.bias", 146, 250, 3, 1); grid("2.weight", 176, 250, 2, 3); grid("2.bias", 235, 250, 2, 1);
      T(gFile, 70, 338, `${Object.values(D.weights).flat().length} floats, 4 tensors`, 13, { fill: V("teal"), "font-weight": 600 });
      const gLoad = S("g", {}, gSys);
      arrow(gLoad, "M286 272 H332");
      label(gLoad, 340, 208, "LOADER");
      card(gLoad, 340, 220, 200, 104, V("violet"));
      M(gLoad, 440, 264, "torch.load()", 18, { "font-weight": 800, "text-anchor": "middle" });
      T(gLoad, 440, 292, "runs a pickle VM", 13, { fill: V("violet"), "text-anchor": "middle", "font-weight": 600 });
      const gModel = S("g", {}, gSys);           // faded out at step 2 so no fragment shows beside the zoomed ZIP
      arrow(gModel, "M546 272 H592");
      label(gModel, 600, 178, "MODEL");
      card(gModel, 600, 190, 320, 170);
      T(gModel, 620, 224, "nn.Sequential", 16, { "font-weight": 700 });
      ["Linear 4→3", "ReLU", "Linear 3→2"].forEach((t, i) => {
        S("rect", { x: 620 + i * 96, y: 238, width: 88, height: 28, rx: 8, fill: V("violet"), "fill-opacity": .14, stroke: V("violet"), "stroke-width": 1.5 }, gModel);
        T(gModel, 664 + i * 96, 257, t, 13, { "text-anchor": "middle", fill: V("violet"), "font-weight": 600 });
      });
      T(gModel, 620, 300, "forward(ones(1, 4)) →", 13, { fill: V("muted") });
      M(gModel, 620, 330, D.model_out, 15, { fill: V("warn"), "font-weight": 600 });
      const pkt = S("circle", { r: 8, cy: 272, fill: V("teal") }, gSys);

      // ZIP panel: drawn at local (0,0)-(580,320) and scaled out of the file card
      const gZip = S("g", {}, svg);
      card(gZip, 0, 0, 580, 320, V("teal"));
      const gZipIn = S("g", {}, gZip);
      M(gZipIn, 20, 32, "model.pt is a ZIP archive", 16, { "font-weight": 800 });
      const pkl = D.zip_entries.find(e => /\/data\.pkl$/.test(e[0]));
      S("rect", { x: 20, y: 50, width: 250, height: 196, rx: 10, fill: V("violet"), "fill-opacity": .08, stroke: V("violet"), "stroke-width": 1.5 }, gZipIn);
      M(gZipIn, 34, 74, pkl[0], 14, { fill: V("violet"), "font-weight": 800 });
      T(gZipIn, 34, 94, `${pkl[1]} B · a pickle program`, 13, { fill: V("muted") });
      BOPS.slice(1, 8).forEach((r, i) => M(gZipIn, 34, 118 + i * 18, `${r[1]} ${cut(r[2], 22)}`, 13, { fill: V("ink-2") }));
      D.zip_entries.filter(e => /\/data\/\d+$/.test(e[0])).forEach((e, k) => {
        const y = 62 + k * 47;
        M(gZipIn, 292, y, `${e[0]} · ${e[1]} B`, 13, { fill: V("teal"), "font-weight": 600 });
        for (let i = 0; i < e[1] / 4; i++)
          S("rect", { x: 292 + i * 20, y: y + 8, width: 16, height: 16, rx: 4, fill: V("teal"), opacity: .75 }, gZipIn);
      });
      let cx = 20;
      D.zip_entries.filter(e => !/\/data(\.pkl|\/\d+)$/.test(e[0])).forEach(e => {
        const name = e[0].replace(/^[^/]+\//, ""), w = 18 + name.length * 8;
        S("rect", { x: cx, y: 258, width: w, height: 26, rx: 8, fill: V("panel-2"), stroke: V("line") }, gZipIn);
        M(gZipIn, cx + 9, 276, name, 13, { fill: V("muted") });
        cx += w + 8;
      });
      T(gZipIn, 20, 306, "(hidden: .data/serialization_id, random per save)", 13, { fill: V("muted") });

      // ------------------------------------------------------------------ scene B: attack (step 3)
      const gAtk = S("g", {}, svg);
      const s0 = iSplit - 6, RH3 = 19;
      const tapeRow = (p, x, y, r, inj) => {
        const g = S("g", {}, p);
        if (inj) S("rect", { x: x - 6, y: y - 14, width: 392, height: RH3, rx: 4, fill: V("bad"), "fill-opacity": .12 }, g);
        M(g, x, y, String(r[0]).padStart(4), 13, { fill: V("muted") });
        M(g, x + 48, y, r[1], 13, { fill: V(inj ? "bad" : opRole(r) === "bad" ? "violet" : opRole(r)), "font-weight": 700 });
        M(g, x + 166, y, cut(r[2], 26), 13, { fill: inj ? V("bad") : V("ink-2") });
        return g;
      };
      label(gAtk, 54, 96, "BENIGN.PT · DATA.PKL (TAIL)");
      label(gAtk, 514, 96, "MALICIOUS.PT · DATA.PKL (TAIL)", { fill: V("bad") });
      card(gAtk, 40, 106, 410, 412); card(gAtk, 500, 106, 420, 412, V("bad"));
      BOPS.slice(s0).forEach((r, i) => tapeRow(gAtk, 54, 130 + i * RH3, r, false));
      OPS.slice(s0, iSplit).forEach((r, i) => tapeRow(gAtk, 514, 130 + i * RH3, r, false));
      const atkInj = OPS.filter(isInj).map((r, i) => ({ g: tapeRow(gAtk, 514, 130 + (6 + i) * RH3, r, true) }));
      const atkPost = OPS.slice(iSplit + nInj).map((r, i) => ({ g: tapeRow(gAtk, 514, 130 + (6 + nInj + i) * RH3, r, false) }));
      const badge = S("g", {}, gAtk);
      S("rect", { x: 790, y: 78, width: 128, height: 28, rx: 14, fill: V("bad") }, badge);
      T(badge, 854, 97, `+${nInj} opcodes`, 14, { "text-anchor": "middle", fill: V("panel"), "font-weight": 800 });
      T(gAtk, 480, 534, "data/0..3 (the weights) are identical in both files", 13, { "text-anchor": "middle", fill: V("teal"), "font-weight": 600 });

      // ------------------------------------------------------------------ scene C: VM (steps 4-7)
      const gVm = S("g", {}, svg);
      const RH = 22, CY = 232, TX = 40, TW = 370;
      const gTape = S("g", { class: "dimmable" }, gVm);
      label(gTape, TX, 96, "OPCODE TAPE");
      const pcTxt = M(gTape, TX + TW, 96, "", 13, { "text-anchor": "end", fill: V("muted") });
      card(gTape, TX, 106, TW, 412);
      const clipId = api.uid("tape");
      S("rect", { x: TX, y: 108, width: TW, height: 408 }, S("clipPath", { id: clipId }, defs));
      const tapeClip = S("g", { "clip-path": `url(#${clipId})` }, gTape);
      S("rect", { x: TX + 2, y: CY - 15, width: TW - 4, height: RH, rx: 5, fill: V("warn"), "fill-opacity": .14, stroke: V("warn"), "stroke-width": 1.5 }, tapeClip);
      const tape = S("g", {}, tapeClip);
      const rows = OPS.map((r, i) => {
        const g = S("g", {}, tape), y = i * RH;
        if (isInj(r)) S("rect", { x: TX + 4, y: y - 15, width: TW - 8, height: RH, rx: 4, fill: V("bad"), "fill-opacity": .1 }, g);
        M(g, TX + 10, y, String(r[0]).padStart(4), 13, { fill: V("muted") });
        M(g, TX + 58, y, r[1], 13, { fill: V(opRole(r)), "font-weight": 700 });
        M(g, TX + 172, y, cut(r[2], 24), 13, { fill: isInj(r) ? V("bad") : V("ink-2") });
        return g;
      });
      S("path", { d: `M${TX - 14} ${CY - 12} l12 8 l-12 8 Z`, fill: V("warn") }, gTape);
      // allowlist gate + the rejected callable
      const gGate = S("g", {}, gVm);
      const gateBar = S("rect", { x: 428, y: 108, width: 9, height: 0, rx: 4, fill: V("ok") }, gGate);
      const gateTxt = T(gGate, 432, 534, "weights_only allowlist", 13, { "text-anchor": "middle", fill: V("ok"), "font-weight": 700 });
      const tok = S("g", {}, gGate);
      S("rect", { x: 0, y: -15, width: 58, height: 24, rx: 6, fill: V("panel"), stroke: V("bad"), "stroke-width": 2 }, tok);
      M(tok, 29, 2, "exec", 13, { "text-anchor": "middle", fill: V("bad"), "font-weight": 800 });
      const tokX = T(gGate, 433, CY + 5, "✕", 18, { "text-anchor": "middle", fill: V("bad"), "font-weight": 800 });
      // stack
      const SX = 456, SW = 210, NS = 10;
      const gStack = S("g", { class: "dimmable" }, gVm);
      label(gStack, SX, 96, "VM STACK");
      const depthTxt = M(gStack, SX + SW, 96, "", 13, { "text-anchor": "end", fill: V("muted") });
      const slots = Array.from({ length: NS }, (_, j) => {
        const y = 480 - j * 37, g = S("g", {}, gStack);
        return { g, box: S("rect", { x: SX, y, width: SW, height: 31, rx: 8, "stroke-width": 1.5 }, g),
          txt: M(g, SX + 12, y + 21, "", 13) };
      });
      const gFold = S("g", {}, gStack);
      const foldBox = S("rect", { x: SX - 6, width: SW + 12, height: 0, rx: 11, fill: "none", stroke: V("bad"), "stroke-width": 2.5, "stroke-dasharray": "6 4" }, gFold);
      const foldTxt = M(gFold, SX + SW / 2, 0, "REDUCE → exec(code)", 14, { "text-anchor": "middle", fill: V("bad"), "font-weight": 800 });
      const pulse = S("circle", { cx: SX + SW / 2, r: 0, fill: "none", stroke: V("lime"), "stroke-width": 4 }, gStack);
      // right panel: imports + memo, then terminal / marker / model for Impact and the gate
      const RX = 680, RW = 268;
      const gRight = S("g", { class: "dimmable" }, gVm);
      label(gRight, RX, 96, "IMPORTED BY GLOBAL");
      const imps = Array.from({ length: 4 }, (_, i) => M(gRight, RX, 122 + i * 24, "", 13, { "font-weight": 600 }));
      const gMemo = S("g", {}, gRight);
      label(gMemo, RX, 246, "MEMO (BINPUT / BINGET)");
      card(gMemo, RX, 256, RW, 196);
      const memoTxt = Array.from({ length: 7 }, (_, i) => M(gMemo, RX + 14, 284 + i * 24, "", 13));
      const gImp = S("g", {}, gRight);
      label(gImp, RX, 246, "VICTIM TERMINAL");
      const term = S("rect", { x: RX, y: 256, width: RW, height: 150, rx: 10, fill: V("panel-2"), stroke: V("line"), "stroke-width": 1.5 }, gImp);
      const termTxt = Array.from({ length: 7 }, (_, i) => M(gImp, RX + 10, 278 + i * 18, "", 13));
      const markCard = card(gImp, RX, 416, RW, 40);
      const markTxt = M(gImp, RX + 12, 441, "", 13, { "font-weight": 700 });
      const outLbl = T(gImp, RX, 478, "model output, unchanged:", 13, { fill: V("muted") });
      const outTxt = M(gImp, RX, 498, "", 13, { "font-weight": 600 });
      const warnChip = S("g", {}, gVm);
      S("rect", { x: RX - 4, y: 464, width: RW + 8, height: 62, rx: 10, fill: V("warn"), "fill-opacity": .12, stroke: V("warn"), "stroke-width": 1.5 }, warnChip);
      T(warnChip, RX + 8, 482, "⚠ the error's advice reopens it:", 13, { fill: V("warn"), "font-weight": 700 });
      M(warnChip, RX + 8, 500, "safe_globals([exec]), or", 13, { fill: V("warn") });
      M(warnChip, RX + 8, 517, "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", 13, { fill: V("warn") });

      // ------------------------------------------------------------------ scene D: safetensors (step 8)
      const gSt = S("g", {}, svg);
      const lay = D.st_layout, total = lay.len + lay.header + lay.data;
      M(gSt, 60, 120, `model.safetensors · ${total} B = ${lay.len} + header ${lay.header} + data ${lay.data}`, 18, { "font-weight": 800 });
      const stLen = S("rect", { x: 60, y: 160, height: 96, rx: 10, fill: V("panel-2"), stroke: V("line"), "stroke-width": 2 }, gSt);
      const stHdr = S("rect", { x: 152, y: 160, height: 96, rx: 10, fill: V("ok"), "fill-opacity": .1, stroke: V("ok"), "stroke-width": 2 }, gSt);
      const stDat = D.st_tensors.map(t => ({ t, r: S("rect", { y: 160, height: 96, rx: 6, fill: V("teal"), "fill-opacity": .25, stroke: V("teal"), "stroke-width": 2 }, gSt) }));
      const gStTxt = S("g", {}, gSt);
      M(gStTxt, 100, 204, `${lay.len} B`, 14, { "text-anchor": "middle", "font-weight": 700 });
      T(gStTxt, 100, 226, "length", 13, { "text-anchor": "middle", fill: V("muted") });
      M(gStTxt, 412, 204, `JSON header · ${lay.header} B`, 15, { "text-anchor": "middle", fill: V("ok"), "font-weight": 700 });
      T(gStTxt, 412, 226, "names, dtypes, shapes, byte offsets", 13, { "text-anchor": "middle", fill: V("muted") });
      const DX = 684, DW = 236;
      stDat.forEach(({ t }, i) => {
        const x = DX + DW * t[3][0] / lay.data, w = DW * (t[3][1] - t[3][0]) / lay.data;
        M(gStTxt, x + w / 2, 280 + (i % 2) * 20, t[0], 13, { "text-anchor": "middle", fill: V("teal"), "font-weight": 600 });
      });
      M(gStTxt, DX + DW / 2, 150, `tensor bytes · ${lay.data} B`, 13, { "text-anchor": "middle", fill: V("teal"), "font-weight": 700 });
      card(gStTxt, 60, 330, 620, 118);
      D.st_tensors.forEach((t, i) => M(gStTxt, 78, 360 + i * 24,
        `"${t[0]}": {"dtype":"${t[1]}","shape":[${t[2]}],"data_offsets":[${t[3]}]}`, 13, { fill: V("ink-2") }));
      T(gStTxt, 60, 494, "No opcodes, no GLOBAL, no REDUCE: loading only copies bytes into tensors.", 17, { fill: V("ok"), "font-weight": 700 });

      // ------------------------------------------------------------------ scene E: sandbox (step 9)
      const gBox = S("g", {}, svg);
      const iso = D.isolation;
      const wall = S("rect", { x: 50, y: 92, width: 560, height: 420, rx: 18, fill: V("ok"), "fill-opacity": .04, stroke: V("ok"), "stroke-width": 3, "stroke-dasharray": "10 6" }, gBox);
      label(gBox, 70, 122, "SANDBOX", { fill: V("ok") });
      M(gBox, 170, 122, "network_mode: none · /labs read-only · /work tmpfs", 13, { fill: V("ok") });
      card(gBox, 76, 140, 250, 118, V("bad"));
      OPS.slice(iGlobal, iReduce + 1).filter(r => r[1] !== "BINPUT").forEach((r, i) =>
        M(gBox, 90, 168 + i * 24, `${r[1]} ${cut(r[2], 18)}`, 13, { fill: V("bad"), "font-weight": i === 0 || r[1] === "REDUCE" ? 700 : 400 }));
      const boxPulse = S("circle", { cx: 200, cy: 236, r: 0, fill: "none", stroke: V("lime"), "stroke-width": 4 }, gBox);
      wrap(iso.sandbox_payload, 34).slice(0, 4).forEach((ln, i) => M(gBox, 76, 290 + i * 19, ln, 13, { fill: V("lime") }));
      card(gBox, 76, 380, 250, 54, V("lime"));
      M(gBox, 90, 403, "/work/canary-marker.txt", 13, { fill: V("lime"), "font-weight": 700 });
      T(gBox, 90, 424, `marker in sandbox: ${iso.sandbox_marker ? "True" : "False"}`, 13, { fill: V("muted") });
      const probes = [["dns canary.invalid", iso.dns.split(":")[0]], ["egress 192.0.2.1:9", iso.egress], ["write to /labs", iso.ro_write]]
        .map(([name, res], i) => {
          const y = 168 + i * 112, g = S("g", {}, gBox);
          M(g, 350, y - 12, name, 13, { "font-weight": 700 });
          const line = S("path", { fill: "none", stroke: V("bad"), "stroke-width": 3, "stroke-linecap": "round" }, g);
          const x = T(g, 610, y + 6, "✕", 20, { "text-anchor": "middle", fill: V("bad"), "font-weight": 800 });
          const r = M(g, 350, y + 26, cut(res, 30), 13, { fill: V("muted") });
          return { y, line, x, r };
        });
      const gHost = S("g", {}, gBox);
      label(gHost, 650, 216, "HOST");
      card(gHost, 650, 228, 270, 96, V("ok"));
      M(gHost, 666, 258, "attack-unsafe-load/work/", 13, { "font-weight": 700 });
      M(gHost, 666, 284, `canary-marker.txt: ${iso.host_marker}`, 13, { fill: V("ok"), "font-weight": 700 });
      T(gHost, 666, 308, "the sandbox could not write here", 13, { fill: V("muted") });

      // ------------------------------------------------------------------ state
      const base = { zoom: 0, sys: 0, zip: 0, atk: 0, vm: 0, pc: 0, fold: 0, fire: 0, gate: 0, st: 0, box: 0 };
      const T_N = [null,
        { sys: 1 },                                   // 1 System: file → torch.load → model
        { sys: 1, zip: 1, zoom: 1 },                  // 2 System: zoom into the ZIP
        { atk: 1 },                                   // 3 Attack: injected rows slide in
        { vm: 1, pc: iTensor },                       // 4 Mechanism: walk to the first rebuilt tensor
        { vm: 1, pc: iReduce, fold: 1 },              // 5 Mechanism: GLOBAL exec + code, REDUCE next
        { vm: 1, pc: iReduce + 1, fire: 1 },          // 6 Impact: REDUCE ran exec
        { vm: 1, pc: iGlobal, gate: 1 },              // 7 Defense: allowlist stops GLOBAL exec
        { pc: iGlobal, st: 1 },                       // 8 Defense: safetensors
        { pc: iGlobal, box: 1 },                      // 9 Defense: sandbox
      ];
      const target = n => ({ ...base, ...T_N[n] });
      const st = { ...base };
      const FULL = [0, 0, 960, 540], ZOOMF = [16, 58, 640, 360];

      function draw(s) {
        const z = E.inOut(s.zoom);
        svg.setAttribute("viewBox", FULL.map((a, i) => L(a, ZOOMF[i], z).toFixed(2)).join(" "));

        // A: system + zip
        const zp = seg(s.zip, 0, 1);
        A(gSys, { opacity: s.sys.toFixed(3) });
        A(gFile, { opacity: (1 - seg(zp, 0, .4)).toFixed(3) });
        A(gLoad, { opacity: (1 - .75 * zp).toFixed(3) });
        A(gModel, { opacity: (1 - seg(zp, 0, .5)).toFixed(3) });
        const kp = seg(s.sys, .2, 1);
        A(pkt, { cx: L(165, 780, E.inOut(kp)).toFixed(2), opacity: kp > 0 && kp < 1 ? 1 : 0 });
        const zs = E.inOut(zp);
        A(gZip, { opacity: (s.sys * seg(zp, 0, .25)).toFixed(3),
          transform: `translate(${L(50, 34, zs).toFixed(2)} ${L(172, 72, zs).toFixed(2)}) scale(${L(.4, 1, zs).toFixed(4)})` });
        A(gZipIn, { opacity: seg(zp, .5, 1).toFixed(3) });

        // B: attack tapes
        A(gAtk, { opacity: seg(s.atk, 0, .35).toFixed(3) });
        const sl = E.out(seg(s.atk, .35, 1));
        atkInj.forEach((r, i) => A(r.g, { opacity: seg(sl, i / nInj * .5, i / nInj * .5 + .5).toFixed(3),
          transform: `translate(${(40 * (1 - seg(sl, i / nInj * .5, i / nInj * .5 + .5))).toFixed(2)} 0)` }));
        atkPost.forEach(r => A(r.g, { transform: `translate(0 ${((sl - 1) * nInj * RH3).toFixed(2)})` }));
        A(badge, { opacity: seg(sl, .6, 1).toFixed(3) });

        // C: VM
        A(gVm, { opacity: s.vm.toFixed(3) });
        const pcI = Math.max(0, Math.min(OPS.length, Math.floor(s.pc + 1e-6)));
        A(tape, { transform: `translate(0 ${(CY - s.pc * RH).toFixed(2)})` });
        rows.forEach((g, i) => A(g, { opacity: i < pcI ? .38 : i === pcI ? 1 : (s.gate > .5 && i > pcI ? .3 : .85) }));
        const cur = OPS[Math.min(pcI, OPS.length - 1)];
        pcTxt.textContent = `op ${pcI + 1}/${OPS.length} · offset ${cur[0]}`;
        const stack = pcI > 0 ? TR[pcI - 1] : [];
        depthTxt.textContent = `depth ${stack.length}`;
        const more = stack.length > NS ? stack.length - (NS - 1) : 0;
        const shown = more ? stack.slice(-(NS - 1)) : stack;
        slots.forEach((sl2, j) => {
          let item = null;
          if (more && j === 0) item = [`… ${more} deeper`, "muted"];
          else item = shown[more ? j - 1 : j] || null;
          A(sl2.g, { opacity: item ? 1 : 0 });
          const role = item ? item[1] : "muted";
          A(sl2.box, { fill: V(role === "muted" ? "panel-2" : role), "fill-opacity": role === "muted" ? 1 : .14, stroke: V(role === "muted" ? "line" : role) });
          sl2.txt.textContent = item ? item[0] : "";
          A(sl2.txt, { fill: V(role === "muted" ? "muted" : role), "font-weight": j === (more ? NS - 1 : shown.length - 1) ? 800 : 500 });
        });
        const topJ = Math.min(NS, shown.length + (more ? 1 : 0)) - 1, topY = 480 - topJ * 37;
        A(foldBox, { y: (topY - 6).toFixed(2), height: (37 + 31 + 12).toFixed(2), opacity: s.fold.toFixed(3) });
        A(foldTxt, { y: (topY - 14).toFixed(2), opacity: s.fold.toFixed(3) });
        const pp = seg(s.fire, 0, .5);
        A(pulse, { cy: topY + 15, r: (10 + 120 * E.out(pp)).toFixed(2), opacity: (pp > 0 && pp < 1 ? 1 - pp : 0).toFixed(3) });
        // imports so far, and the memo
        const seen = [];
        for (let i = 0; i < pcI; i++) if (OPS[i][1] === "GLOBAL") seen.push(i);
        imps.forEach((t, k) => { const r = OPS[seen[k]]; t.textContent = r ? r[2] : ""; A(t, { fill: V(r && isInj(r) ? "bad" : "violet") }); });
        const memo = [];
        for (let i = 0; i < pcI; i++) if (OPS[i][1] === "BINPUT") memo.push([OPS[i][2], TR[i][TR[i].length - 1]]);
        memoTxt.forEach((t, k) => {
          const e = k === 0 ? null : memo[memo.length - 7 + k];
          t.textContent = k === 0 ? `${memo.length} entries, newest last` : e ? `${e[0].padStart(3)}  ${cut(e[1][0], 20)}` : "";
          A(t, { fill: V(k === 0 ? "muted" : e && e[1][1] !== "muted" ? e[1][1] : "ink-2") });
        });
        const imp = Math.max(s.fire, s.gate);
        A(gMemo, { opacity: (1 - imp).toFixed(3) });
        A(gImp, { opacity: imp.toFixed(3) });
        const lines = s.gate > s.fire ? wrap(errShort, 31) : wrap(D.payload_line, 31);
        const typed = s.gate > s.fire ? seg(s.gate, .3, .9) : seg(s.fire, .2, .8);
        const nch = Math.round(lines.join("").length * typed);
        let left = nch;
        termTxt.forEach((t, i) => {
          const ln = lines[i] || "";
          t.textContent = ln.slice(0, Math.max(0, left)); left -= ln.length;
          A(t, { fill: V(s.gate > s.fire ? "ok" : "lime") });
        });
        A(term, { stroke: V(s.gate > s.fire ? "ok" : "lime") });
        const marked = s.fire > .5;
        markTxt.textContent = marked ? D.marker : "no marker written";
        A(markTxt, { fill: V(marked ? "lime" : "muted"), opacity: seg(Math.max(s.fire, s.gate), .6, 1).toFixed(3) });
        A(markCard, { stroke: V(marked ? "lime" : "line"), opacity: seg(Math.max(s.fire, s.gate), .6, 1).toFixed(3) });
        outTxt.textContent = marked ? D.model_out : "";
        A(outTxt, { fill: V("warn"), opacity: seg(s.fire, .7, 1).toFixed(3) });
        A(outLbl, { opacity: seg(s.fire, .7, 1).toFixed(3) });
        // gate
        A(gateBar, { height: (408 * E.inOut(seg(s.gate, 0, .4))).toFixed(2) });
        A(gateTxt, { opacity: seg(s.gate, .3, .6).toFixed(3) });
        const b = seg(s.gate, .35, .95);
        A(tok, { opacity: seg(s.gate, .3, .4).toFixed(3), transform: `translate(${(352 + 14 * Math.sin(Math.PI * b * 2) * (1 - b)).toFixed(2)} ${CY})` });
        A(tokX, { opacity: seg(s.gate, .85, 1).toFixed(3) });
        A(warnChip, { opacity: seg(s.gate, .8, 1).toFixed(3) });
        // focus + context
        const focus = s.fold > .5 ? [gTape, gStack] : s.fire > .5 ? [gStack, gRight] : [];
        [gTape, gStack, gRight].forEach(g => g.classList.toggle("hot", focus.includes(g)));
        el.classList.toggle("lx-focus", focus.length > 0 && s.vm > .5);

        // D: safetensors
        A(gSt, { opacity: s.st.toFixed(3) });
        const sg = E.out(seg(s.st, .1, .8));
        A(stLen, { width: (80 * sg).toFixed(2) });
        A(stHdr, { width: (520 * sg).toFixed(2) });
        stDat.forEach(({ t, r }) => A(r, { x: (DX + DW * t[3][0] / lay.data).toFixed(2),
          width: Math.max(0, DW * (t[3][1] - t[3][0]) / lay.data * sg - 3).toFixed(2) }));
        A(gStTxt, { opacity: seg(s.st, .6, 1).toFixed(3) });

        // E: sandbox
        A(gBox, { opacity: seg(s.box, 0, .3).toFixed(3) });
        const bp = seg(s.box, .25, .55);
        A(boxPulse, { r: (8 + 90 * E.out(bp)).toFixed(2), opacity: (bp > 0 && bp < 1 ? 1 - bp : 0).toFixed(3) });
        probes.forEach((p, i) => {
          const k = E.out(seg(s.box, .45 + i * .1, .75 + i * .1));
          A(p.line, { d: `M350 ${p.y} H${L(350, 600, k).toFixed(2)}` });
          A(p.x, { opacity: seg(k, .9, 1).toFixed(3) });
          A(p.r, { opacity: seg(k, .9, 1).toFixed(3) });
        });
        A(wall, { "stroke-width": (3 + 2 * seg(s.box, .7, 1)).toFixed(2) });
        A(gHost, { opacity: seg(s.box, .85, 1).toFixed(3) });
      }

      draw(st);
      let gen = 0;
      const MS = [0, 800, 1000, 900, 1100, 1000, 1000, 1000, 900, 1100];  // ms per step; the walk steps 4-5 are the longest
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          return api.tween(MS[n], k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); },
            n === 4 || n === 5 ? E.linear : E.inOut);
        },
      };
    },
  });
})();
