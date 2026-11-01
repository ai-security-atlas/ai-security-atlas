/* LAB-17 format-gguf: "GGUF is data, its template is code" (10 steps).
 * One persistent scene on top (the file drawn to scale with a zoom on its first 1.8 MB, then three cards:
 * the 290 tensors, the chat template, the renderer) and a detail panel below that crossfades per step.
 * Every number and string from the run comes from window.LAB_DATA (data.js, exported from the reference
 * workbench run). Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v;
  const D = window.LAB_DATA;
  const H = D.hashes, lay = D.layout;
  const dataStart = lay[4][1], tensorBytes = lay[4][2] - lay[4][1];
  const pct = (a, b) => (100 * a / b).toFixed(2) + "%";
  const mb = b => (b / 1e6).toFixed(1) + " MB";
  const hits = k => `${D.hits[k]}/10`;
  const tt = D.tensor_types;
  const promptLines = p => p.split("\n").filter(l => l.length);
  const sysLine = p => promptLines(p)[1];
  const added = D.added.replace(/^\.\s*/, "");

  X.define({
    id: "format-gguf",
    family: "family-supply",
    title: 'GGUF is data, its template is <span class="outline">code</span>',
    legend: [{ role: "teal", label: "Tensor bytes (unchanged)" }, { role: "bad", label: "Rewritten template" },
      { role: "violet", label: "Renderer" }, { role: "warn", label: "Model answer" },
      { role: "lime", label: "Canary" }, { role: "ok", label: "Defense" }],
    intro: {
      "why": "A GGUF file is the model file that llama.cpp loads. It holds the weights and a table of named settings, and reading it runs no code. One setting holds the chat template, a short program that the server runs on every request to build the model’s prompt. You’ll see what happens when someone changes that one setting.",
      "plan": "First you read the parts of a real GGUF file and run its template. Then you rewrite only the template, serve the file and ask the same questions again. A second template tries to reach into Python. Last come four checks: file and metadata hashes, a template allowlist, a template pinned on the server, and a sandboxed renderer.",
      "terms": "A tensor is one block of weights. Metadata is the file’s table of named settings. A chat template is Jinja code that turns chat messages into one prompt string. A hash is a short fingerprint of some bytes. An allowlist is a list of approved templates. A sandbox limits what code can reach."
    },
    steps: [
      { chapter: "System", label: "The file to scale",
        guide: "You read the file’s bytes and run nothing. Almost all of the file is tensor bytes, the weights. Before them sits the metadata: the architecture, the tokenizer and the chat template. Look at how small the template is. It is one text entry near the end of the metadata.",
        caption: `<code>${D.file}</code>, ${D.size.toLocaleString("en-US")} bytes, GGUF v${D.version}: ${D.kv_count} metadata keys, ${D.tensor_count} tensors (${tt.Q8_0} Q8_0, ${tt.F32} F32). Tensor data is ${pct(tensorBytes, D.size)} of the file. <code>tokenizer.chat_template</code> is one ${D.template_chars[0]}-character string in the metadata.`,
        cmd: "docker compose run --rm workbench python format-gguf/scripts/s01_inspect.py" },
      { chapter: "System", label: "The template runs",
        guide: "You run the template the way the server does. It has a loop, conditions and string building. You send only the word hi. The template wraps it in a system turn and the control tokens the model expects. So the file decides what the model reads on every request.",
        caption: `Parsed as Jinja: ${Object.entries(D.template_counts).map(([k, v]) => `${v} ${k}`).join(", ")}; it reads <code>${D.template_inputs.join("</code>, <code>")}</code>. llama-server's <code>/apply-template</code> output equals Python jinja2's (same prompt: ${D.same_prompt}). Baseline: canary in <span class="c-ok">${hits("original")}</span> answers.`,
        cmd: "docker compose run --rm workbench python format-gguf/scripts/s02_template.py" },
      { chapter: "Attack", label: "Rewrite one key",
        guide: "Now you play the attacker. You can publish or replace the file, and that is all. You use the gguf package’s own metadata tool to write a new template and copy everything else. You train nothing. The new template adds one sentence to the system turn.",
        caption: `<code>gguf-new-metadata --chat-template-file</code> writes <code>work/tampered.gguf</code>: the template grows from ${D.template_chars[0]} to ${D.template_chars[1]} chars and the tensor data moves from byte ${H.original.data_offset} to ${H.tampered.data_offset}. Keys that differ: <code>${H.tampered.changed_keys.join(", ")}</code>.`,
        cmd: "docker compose run --rm workbench python format-gguf/scripts/s03_tamper.py" },
      { chapter: "Attack", label: "Same tensors",
        guide: "A hash is a fingerprint of bytes. You hash the three files three ways. The whole-file hash and the metadata hash change. Every tensor is byte-identical, and the gguf package’s tensor-only hash is the same for all three files. A check that hashes only the weights sees no change.",
        caption: `Tensor sha256 (<code>gguf_hash</code>) <code class="c-teal">${H.original.tensor_sha256}</code> for original, tampered and probe; ${H.tampered.tensors_equal}/${D.tensor_count} tensors identical. File sha256 <code>${H.original.file_sha256}</code> becomes <code class="c-bad">${H.tampered.file_sha256}</code>; metadata sha256 <code>${H.original.metadata_sha256}</code> becomes <code class="c-bad">${H.tampered.metadata_sha256}</code>.` },
      { chapter: "Mechanism", label: "The server renders it",
        guide: "You serve the rewritten file and ask the server which prompt it builds for the message hi. The system turn now ends with a sentence that the client never sent. The weights are the same as before. The sentence comes from the template stored in the file.",
        caption: `<code>POST /apply-template</code> on the tampered file: the system turn ends with <span class="c-bad">${added}</span> llama-server took the template from the file's metadata, the default.`,
        cmd: "docker compose run --rm workbench python format-gguf/scripts/s04_served.py tampered" },
      { chapter: "Impact", label: "Every answer marked",
        guide: "You ask the ten fixed questions again. Each answer now starts with the lab canary, a harmless marker string, and still answers the question. The server also adds the sentence to a deployer’s own system prompt. The canary stands in for any hidden instruction a template could add.",
        caption: `Canary <code class="c-lime">${D.canary}</code> in <span class="c-bad">${hits("tampered")}</span> answers, against ${hits("original")} for the publisher's file. A deployer's own system prompt still gets the sentence appended: <span class="c-warn">${D.deployer.answer}</span>` },
      { chapter: "Impact", label: "Three engines",
        guide: "What a template can reach depends on the engine that renders it. A probe template tries to read one Python class name. Plain Python Jinja, as used by the vulnerable llama-cpp-python versions, lets it read the name and print the canary. llama-server’s own engine has no Python objects, so the probe prints nothing there.",
        caption: `Probe, the CVE-2024-34359 pattern stopped at the first hop: <code>''.__class__.__name__</code>. Plain <code>jinja2.Environment</code>: <span class="c-lime">${D.probe_python}</span>. llama-server: ${D.probe_server ? D.probe_server : "an empty string"}.`,
        cmd: "docker compose run --rm workbench python format-gguf/scripts/s05_probe.py python" },
      { chapter: "Defense", label: "Hashes and allowlist",
        guide: "Now check the files before loading them. The publisher’s whole-file hash rejects both modified files, and so does a reviewer’s metadata hash. The tensor-only hash passes them. A template allowlist with a readable diff also rejects the rewrite, while a simple pattern lint lets it through.",
        caption: `File sha256: original ${D.verify.original.file_sha256 ? "pass" : "FAIL"}, tampered <span class="c-ok">${D.verify.tampered.file_sha256 ? "pass" : "FAIL"}</span>. Metadata sha256: tampered <span class="c-ok">${D.verify.tampered.metadata_sha256 ? "pass" : "FAIL"}</span>. Tensor hash: tampered ${D.verify.tampered.tensor_sha256 ? "pass" : "FAIL"}. Allowlist: <code>${D.gate.tampered.verdict}</code>; probe: <code>${D.gate.probe.verdict}</code>. A hash only proves you got the file you pinned.`,
        cmd: "docker compose run --rm workbench python format-gguf/scripts/d1_verify.py" },
      { chapter: "Defense", label: "Pin the template",
        guide: "You give the server a reviewed template file, so it ignores the template inside the model. The same rewritten file now builds the publisher’s prompt, and the canary is gone. Switching templates off also removes the canary. It drops the default system turn too, so the prompt differs from the publisher’s.",
        caption: `<code>--chat-template-file</code> pinned: canary in <span class="c-ok">${hits("pinned")}</span> answers on the tampered file. <code>--no-jinja</code>: ${hits("no_jinja")}, but the default system turn is gone. The pin covers only the template: tokenizer and tensors still come from the file.`,
        cmd: "docker compose run --rm workbench python format-gguf/scripts/s04_served.py pinned" },
      { chapter: "Defense", label: "Sandbox the renderer",
        guide: "You render the templates in Jinja’s immutable sandbox, the fix for the llama-cpp-python bug. The publisher’s template renders as before. The probe stops with an error. The hidden sentence still renders, because it is ordinary string building. The allowlist and the pin are what stop that sentence.",
        caption: `<code>ImmutableSandboxedEnvironment</code>: original ${D.sandbox.original.sandbox}, tampered ${D.sandbox.tampered.sandbox}, probe <span class="c-ok">${D.sandbox.probe.sandbox}</span> (<code>${D.sandbox_error}</code>). A sandbox limits what a template can reach, not what it says.`,
        cmd: "docker compose run --rm workbench python format-gguf/scripts/d4_sandbox.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="The GGUF file to scale, its tensors, its chat template, the renderer and a detail panel"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line")) => S("rect", { x, y, width: w, height: h, rx: 12, fill: V("panel"), stroke, "stroke-width": 2 }, p);
      const clip = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
      const mono = { class: "mono" };

      // ---------- the file to scale, and a zoom on everything before the tensor data
      const gFile = S("g", { class: "dimmable" }, svg);
      label(gFile, 30, 22, `THE FILE TO SCALE · ${D.size.toLocaleString("en-US")} BYTES · GGUF V${D.version}`);
      const W = 900, sx = b => 30 + W * b / D.size;
      S("rect", { x: 30, y: 32, width: W, height: 24, rx: 4, fill: V("teal"), opacity: .3 }, gFile);
      S("rect", { x: 30, y: 32, width: Math.max(4, sx(dataStart) - 30), height: 24, fill: V("muted") }, gFile);
      T(gFile, 480, 49, `tensor data ${pct(tensorBytes, D.size)} · ${D.tensor_count} tensors (${tt.Q8_0} Q8_0, ${tt.F32} F32)`, 13, { "text-anchor": "middle", "font-weight": 700 });
      S("path", { d: `M30 56 L30 84 M${Math.max(34, sx(dataStart))} 56 L930 84`, fill: "none", stroke: V("line"), "stroke-width": 1.2 }, gFile);
      const zx = b => 30 + W * b / dataStart;
      const metaEnd = lay[1][2];
      S("rect", { x: 30, y: 84, width: Math.max(4, zx(lay[0][2]) - 30), height: 20, fill: V("ink-2") }, gFile);
      S("rect", { x: zx(lay[1][1]) + 3, y: 84, width: zx(metaEnd) - zx(lay[1][1]) - 3, height: 20, fill: V("muted"), opacity: .55 }, gFile);
      S("rect", { x: zx(lay[2][1]), y: 84, width: Math.max(6, zx(lay[2][2]) - zx(lay[2][1])), height: 20, fill: V("violet"), opacity: .6 }, gFile);
      const tplMark = S("rect", { x: zx(metaEnd) - 14, y: 80, width: 10, height: 28, rx: 3, fill: V("teal"), stroke: V("teal"), "stroke-width": 1.5 }, gFile);
      T(gFile, 34, 122, `header ${lay[0][2]} B`, 13, mono);
      T(gFile, 300, 122, `metadata KV ${mb(metaEnd - lay[1][1])}: tokenizer, architecture`, 13, mono);
      const tplLbl = T(gFile, 926, 122, "", 13, { class: "mono", "text-anchor": "end", "font-weight": 700 });

      // ---------- card 1: the tensors
      const gTen = S("g", { class: "dimmable" }, svg);
      card(gTen, 30, 140, 290, 160, V("teal"));
      label(gTen, 46, 164, `${D.tensor_count} TENSORS · ${mb(tensorBytes)}`, { fill: V("teal") });
      const cells = [];
      for (let i = 0; i < D.tensor_count; i++) {
        const c = i % 29, r = Math.floor(i / 29);
        cells.push(S("rect", { x: 46 + c * 9.2, y: 174 + r * 8.2, width: 7, height: 7, rx: 1.5, fill: V("teal"), opacity: .7 }, gTen));
      }
      T(gTen, 46, 270, `tensor sha256 ${H.original.tensor_sha256}`, 13, mono);
      const tenOk = T(gTen, 46, 290, `${H.tampered.tensors_equal}/${D.tensor_count} identical`, 13, { fill: V("teal"), "font-weight": 800 });

      // ---------- card 2: the chat template
      const gTpl = S("g", { class: "dimmable" }, svg);
      const tplBox = card(gTpl, 340, 140, 270, 160, V("line"));
      const tplHead = label(gTpl, 356, 164, "TOKENIZER.CHAT_TEMPLATE");
      const tplInfo = T(gTpl, 356, 186, "", 13, mono);
      const frags = D.template.match(/\{%.*?%\}|\{\{.*?\}\}/g) || [];
      [frags[0], frags[1], frags[2]].forEach((f, i) => T(gTpl, 356, 210 + i * 20, clip(f.replace(/\n/g, "\\n"), 31), 13, { class: "mono", fill: V("ink-2") }));
      const tplBad = T(gTpl, 356, 276, "", 13, { class: "mono", fill: V("bad"), "font-weight": 700 });
      const tplMeta = T(gTpl, 356, 294, "", 13, { class: "mono", fill: V("muted") });

      // ---------- arrow template -> renderer, and the defense gate on it
      const arrow = S("g", {}, svg);
      const arrowLine = S("path", { d: "M612 220 L634 220", fill: "none", stroke: V("teal"), "stroke-width": 5, "stroke-linecap": "round" }, arrow);
      const arrowHead = S("path", { d: "M630 212 L640 220 L630 228 Z", fill: V("teal") }, arrow);
      const gate = S("g", {}, svg);
      S("rect", { x: 618, y: 140, width: 12, height: 160, rx: 6, fill: V("ok") }, gate);

      // ---------- card 3: the renderer
      const gRen = S("g", { class: "dimmable" }, svg);
      const renBox = card(gRen, 650, 140, 280, 160, V("violet"));
      label(gRen, 666, 164, "RENDERER", { fill: V("violet") });
      const renEng = T(gRen, 666, 186, "", 13, { class: "mono", fill: V("violet"), "font-weight": 800 });
      const renL = [0, 1, 2, 3].map(i => T(gRen, 666, 208 + i * 19, "", 13, mono));
      const renAns = S("text", { x: 666, y: 208 + 4 * 19, "font-size": 13, class: "mono" }, gRen);
      const ansCan = S("tspan", { text: "", fill: V("lime"), "font-weight": 800 }, renAns);
      const ansRest = S("tspan", { text: "", fill: V("warn") }, renAns);

      // ---------- detail panels (bottom band)
      const panels = [null];
      const P = () => { const g = S("g", {}, svg); panels.push(g); return g; };
      const row = (g, x, y, cols, size = 14, o = {}) => cols.forEach(([dx, s, oo]) => T(g, x + dx, y, s, size, { class: "mono", ...o, ...(oo || {}) }));
      const files = ["original", "tampered", "probe"];
      const pf = b => (b ? "pass" : "FAIL");

      // P1 metadata
      let g = P();
      label(g, 30, 334, `METADATA (${D.kv_count} KEYS), ABRIDGED`);
      D.kv.forEach(([k, t, v], i) => {
        const x = 30 + Math.floor(i / 4) * 460, y = 362 + (i % 4) * 26;
        row(g, x, y, [[0, k, { fill: k === "tokenizer.chat_template" ? V("teal") : V("ink") }], [218, t, { fill: V("muted") }], [328, clip(v, 16), {}]], 13);
      });
      T(g, 30, 486, `header: magic GGUF · version ${D.version} · tensor_count ${D.tensor_count} · kv_count ${D.kv_count}`, 14, { class: "mono", "font-weight": 700 });
      T(g, 30, 512, "Parsing these bytes runs nothing; the template is stored as plain text.", 14, { fill: V("muted") });

      // P2 the template turns 'hi' into a prompt
      g = P();
      label(g, 30, 334, "THE TEMPLATE TURNS ONE USER MESSAGE INTO THE PROMPT");
      promptLines(D.prompt_original).forEach((l, i) => {
        const t = S("text", { x: 40, y: 362 + i * 26, "font-size": 14, class: "mono" }, g);
        const u = i === 3 ? l.indexOf("<|") : 0;
        S("tspan", { text: l.slice(0, u), fill: V("teal"), "font-weight": 800 }, t);
        S("tspan", { text: l.slice(u), fill: V("violet") }, t);
      });
      T(g, 40, 490, "violet: added by the template", 13, { fill: V("violet") });
      T(g, 280, 490, "teal: what the user sent", 13, { fill: V("teal") });
      T(g, 500, 490, `inputs it reads: ${D.template_inputs.join(", ")}`, 13, mono);
      T(g, 40, 512, `server prompt == Python jinja2 prompt: ${D.same_prompt}`, 14, { class: "mono", "font-weight": 700 });

      // P3 the rewrite
      g = P();
      label(g, 30, 334, "GGUF-NEW-METADATA --CHAT-TEMPLATE-FILE TAMPERED.JINJA: THE TEMPLATE DIFF");
      D.diff.slice(0, 5).forEach((l, i) => T(g, 40, 362 + i * 24, clip(l.replace(/\n/g, "\\n"), 112), 13, { class: "mono", fill: l[0] === "+" ? V("bad") : V("muted") }));
      row(g, 40, 492, [[0, `template ${D.template_chars[0]} -> ${D.template_chars[1]} chars`, { "font-weight": 700 }],
        [330, `file ${H.original.size} -> ${H.tampered.size} bytes`, {}], [660, `keys changed: ${H.tampered.changed_keys.length} of ${D.kv_count}`, { fill: V("bad"), "font-weight": 700 }]], 13);
      T(g, 40, 516, "Every tensor is copied unchanged; only the data offset moves.", 14, { fill: V("muted") });

      // P4 hashes
      g = P();
      label(g, 30, 334, "FINGERPRINTS OF THE THREE FILES");
      files.forEach((f, j) => T(g, 330 + j * 200, 360, f, 13, { class: "mono", fill: V("muted"), "font-weight": 700 }));
      [["file sha256", "file_sha256"], ["tensor sha256 (gguf_hash)", "tensor_sha256"], ["metadata sha256", "metadata_sha256"], ["tensor data starts at", "data_offset"]].forEach(([n, k], i) => {
        const y = 390 + i * 28;
        T(g, 40, y, n, 14, { "font-weight": 700 });
        files.forEach((f, j) => {
          const same = String(H[f][k]) === String(H.original[k]);
          T(g, 330 + j * 200, y, String(H[f][k]), 14, { class: "mono", fill: k === "tensor_sha256" ? V("teal") : same ? V("ink") : V("bad"), "font-weight": 700 });
        });
      });
      T(g, 40, 512, `tensors byte-identical: ${H.tampered.tensors_equal}/${D.tensor_count} (tampered), ${H.probe.tensors_equal}/${D.tensor_count} (probe)`, 14, { class: "mono", fill: V("teal"), "font-weight": 700 });

      // P5 the rendered prompt
      g = P();
      label(g, 30, 334, "POST /APPLY-TEMPLATE ON THE TAMPERED FILE, USER MESSAGE 'hi'");
      const tl = promptLines(D.prompt_tampered);
      const pre = tl[1].slice(0, tl[1].indexOf(added));
      T(g, 40, 362, tl[0], 14, { class: "mono", fill: V("violet") });
      T(g, 40, 386, pre, 14, { class: "mono", fill: V("violet") });
      T(g, 40, 410, tl[1].slice(pre.length), 14, { class: "mono", fill: V("bad"), "font-weight": 800 });
      tl.slice(2).forEach((l, i) => T(g, 40, 434 + i * 24, l, 14, { class: "mono", fill: l === "hi<|im_end|>" ? V("teal") : V("violet") }));

      // P6 answers
      g = P();
      label(g, 30, 334, "THE SAME QUESTIONS, TAMPERED FILE, TEMPERATURE 0");
      D.answers.slice(0, 4).forEach(([q, , a], i) => {
        const y = 360 + i * 26;
        T(g, 30, y, clip(q, 34), 13, { fill: V("muted") });
        const t = S("text", { x: 300, y, "font-size": 13, class: "mono" }, g);
        const can = a.startsWith(D.canary) ? D.canary : "";
        S("tspan", { text: can, fill: V("lime"), "font-weight": 800 }, t);
        S("tspan", { text: clip(a.slice(can.length), 60), fill: V("warn") }, t);
      });
      T(g, 30, 474, "deployer's own system prompt:", 13, { fill: V("muted") });
      T(g, 300, 474, D.deployer.answer, 13, { class: "mono", fill: V("warn"), "font-weight": 700 });
      T(g, 30, 508, `canary in answers: publisher's file ${hits("original")}, tampered file ${hits("tampered")}`, 15, { "font-weight": 800, fill: V("bad") });

      // P7 three engines
      g = P();
      label(g, 30, 334, "PROBE TEMPLATE (ADDED TO THE PUBLISHER'S): READ ONE PYTHON CLASS NAME");
      const cut = D.probe.indexOf("%}") + 2;
      T(g, 40, 360, D.probe.slice(0, cut), 13, { class: "mono", fill: V("bad") });
      T(g, 40, 380, clip(D.probe.slice(cut), 112), 13, { class: "mono", fill: V("bad") });
      card(g, 30, 398, 440, 120, V("bad"));
      T(g, 46, 424, "plain jinja2.Environment (Python)", 14, { "font-weight": 700 });
      T(g, 46, 448, "the vulnerable llama-cpp-python pattern", 13, { fill: V("muted") });
      T(g, 46, 476, clip(D.probe_python, 54), 13, { class: "mono", fill: V("lime"), "font-weight": 800 });
      T(g, 46, 502, "the template reached a Python object", 13, { fill: V("bad"), "font-weight": 700 });
      card(g, 490, 398, 440, 120, V("violet"));
      T(g, 506, 424, "llama-server (its own C++ Jinja engine)", 14, { "font-weight": 700 });
      T(g, 506, 448, "the server this lab serves with", 13, { fill: V("muted") });
      T(g, 506, 476, `rendered: '${D.probe_server}'`, 13, { class: "mono", "font-weight": 800 });
      T(g, 506, 502, "no Python objects to reach", 13, { fill: V("muted"), "font-weight": 700 });

      // P8 D1 + D2
      g = P();
      label(g, 30, 334, "D1 HASHES · D2 TEMPLATE ALLOWLIST");
      files.forEach((f, j) => T(g, 330 + j * 120, 358, f, 13, { class: "mono", fill: V("muted"), "font-weight": 700 }));
      [["file sha256 (publisher)", "file_sha256"], ["tensor sha256 only", "tensor_sha256"], ["metadata sha256 (reviewer)", "metadata_sha256"]].forEach(([n, k], i) => {
        const y = 386 + i * 26;
        T(g, 30, y, n, 14, { "font-weight": 700 });
        files.forEach((f, j) => {
          const v = D.verify[f][k];
          T(g, 330 + j * 120, y, pf(v), 14, { class: "mono", fill: f === "original" ? V("muted") : v ? V("bad") : V("ok"), "font-weight": 800 });
        });
        T(g, 700, y, `${D.verify_seconds[k]} s per file`, 13, { class: "mono", fill: V("muted") });
      });
      T(g, 30, 474, "allowlist verdict", 14, { "font-weight": 700 });
      files.forEach((f, j) => T(g, 30 + j * 300, 500, `${f}: ${D.gate[f].verdict}`, 13, { class: "mono", fill: D.gate[f].allow ? V("muted") : V("ok"), "font-weight": 700 }));
      T(g, 30, 524, `dunder lint flags the probe (${D.gate.probe.lint.length} hits) but ${D.gate.tampered.lint.length} on the tampered template`, 13, { fill: V("muted") });

      // P9 pinned template
      g = P();
      label(g, 30, 334, "CANARY IN 10 ANSWERS, BY WHICH TEMPLATE THE SERVER RUNS");
      [["publisher's file", "original", V("teal")], ["tampered, embedded template", "tampered", V("bad")],
        ["tampered, --chat-template-file", "pinned", V("ok")], ["tampered, --no-jinja", "no_jinja", V("warn")]].forEach(([n, k, c], i) => {
        const y = 352 + i * 40, w = 400 * D.hits[k] / 10;
        T(g, 30, y + 20, n, 14, {});
        S("rect", { x: 320, y, width: 400, height: 28, rx: 5, fill: V("line"), opacity: .5 }, g);
        S("rect", { x: 320, y, width: Math.max(3, w), height: 28, rx: 5, fill: c, opacity: .85 }, g);
        T(g, 732, y + 20, hits(k), 15, { class: "mono", "font-weight": 800 });
      });
      T(g, 30, 524, "--no-jinja drops the canary but also the default system turn: not a pin.", 13, { fill: V("muted") });

      // P10 sandbox
      g = P();
      label(g, 30, 334, "D4: THE SAME THREE TEMPLATES IN TWO ENGINES");
      T(g, 200, 362, "plain jinja2.Environment", 13, { class: "mono", fill: V("muted"), "font-weight": 700 });
      T(g, 560, 362, "ImmutableSandboxedEnvironment", 13, { class: "mono", fill: V("muted"), "font-weight": 700 });
      const sv = v => (v === "same" ? "renders, same prompt" : v === "canary" ? "renders, canary in prompt" : v);
      files.forEach((f, i) => {
        const y = 394 + i * 30, r = D.sandbox[f];
        T(g, 30, y, f, 14, { class: "mono", "font-weight": 700 });
        T(g, 200, y, sv(r.plain), 14, { class: "mono", fill: r.plain === "canary" ? V("bad") : V("ink") });
        T(g, 560, y, sv(r.sandbox), 14, { class: "mono", fill: r.sandbox === "SecurityError" ? V("ok") : r.sandbox === "canary" ? V("bad") : V("ink"), "font-weight": 800 });
      });
      T(g, 30, 494, clip(D.sandbox_error, 112), 13, { class: "mono", fill: V("ok") });
      T(g, 30, 520, "The sandbox stops the probe; only the allowlist or the pin stops the hidden sentence.", 14, { fill: V("muted") });

      // ---------- per-step scene content (snapped strings in the state)
      const ans0 = D.answers[0];
      const SC = {
        read: { eng: "not loaded: reading runs nothing", l: ["GGUFReader only parses bytes", "", "", ""], can: "", ans: "" },
        serve: { eng: "llama-server, --jinja (default)", l: ["system turn the model sees:", clip(sysLine(D.prompt_original), 33), "", "answer:"], can: "", ans: clip(ans0[1], 33) },
        tamp: { eng: "llama-server, --jinja (default)", l: ["system turn the model sees:", clip(sysLine(D.prompt_original), 33), clip(added, 33), ""], can: "", ans: "" },
        hit: { eng: "llama-server, --jinja (default)", l: ["system turn the model sees:", clip(sysLine(D.prompt_original), 33), clip(added, 33), "answer:"], can: D.canary, ans: clip(ans0[2].slice(D.canary.length), 32 - D.canary.length) },
        probe: { eng: "jinja2.Environment vs server", l: ["Python jinja2 renders:", clip(D.probe_python, 33), "llama-server renders:", `'${D.probe_server}'`], can: "", ans: "" },
        gate: { eng: "not served", l: ["file sha256: " + pf(D.verify.tampered.file_sha256), "metadata sha256: " + pf(D.verify.tampered.metadata_sha256), clip("allowlist: " + D.gate.tampered.verdict, 33), ""], can: "", ans: "" },
        pin: { eng: "--chat-template-file (pinned)", l: ["system turn the model sees:", clip(sysLine(D.prompt_original), 33), "", "answer:"], can: "", ans: clip(ans0[1], 33) },
        sbx: { eng: "ImmutableSandboxedEnvironment", l: ["probe:", clip(D.sandbox_error, 33), "tampered:", "renders, canary in prompt"], can: "", ans: "" },
      };

      // ---------- state
      const base = { flow: 0, tamp: 0, probe: 0, check: 0, gate: 0, pin: 0, sbx: 0, pn: 1, sc: "read" };
      const T_N = [null,
        { pn: 1, sc: "read" },
        { flow: 1, pn: 2, sc: "serve" },
        { flow: 1, tamp: 1, pn: 3, sc: "serve" },
        { flow: 1, tamp: 1, check: 1, pn: 4, sc: "serve" },
        { flow: 1, tamp: 1, check: 1, pn: 5, sc: "tamp" },
        { flow: 1, tamp: 1, check: 1, pn: 6, sc: "hit" },
        { flow: 1, probe: 1, check: 1, pn: 7, sc: "probe" },
        { tamp: 1, check: 1, gate: 1, pn: 8, sc: "gate" },
        { tamp: 1, check: 1, pin: 1, pn: 9, sc: "pin" },
        { flow: 1, probe: 1, check: 1, sbx: 1, pn: 10, sc: "sbx" },
      ];
      const st = { ...base };
      const target = n => ({ ...base, ...T_N[n] });

      function draw(s) {
        panels.forEach((p, i) => { if (p) p.setAttribute("opacity", Math.max(0, 1 - Math.abs(s.pn - i) * 1.6).toFixed(3)); });
        // template card: original, tampered or probe
        const mode = s.probe > .5 ? "probe" : s.tamp > .5 ? "tampered" : "original";
        const bad = mode !== "original";
        A(tplBox, { stroke: bad ? V("bad") : V("teal") });
        A(tplHead, { fill: bad ? V("bad") : V("teal") });
        A(tplMark, { fill: bad ? V("bad") : V("teal"), stroke: bad ? V("bad") : V("teal") });
        tplLbl.textContent = mode === "probe" ? "chat_template + probe" : `chat_template, ${D.template_chars[mode === "tampered" ? 1 : 0]} chars`;
        A(tplLbl, { fill: bad ? V("bad") : V("teal") });
        tplInfo.textContent = mode === "original" ? `${D.template_chars[0]} chars of Jinja source` : mode === "tampered" ? `${D.template_chars[1]} chars, rewritten` : "publisher's + probe";
        tplBad.textContent = mode === "tampered" ? clip(D.diff[0], 31) : mode === "probe" ? clip(D.probe, 31) : "";
        tplMeta.textContent = `metadata sha256 ${H[mode].metadata_sha256}`;
        A(tplMeta, { fill: bad ? V("bad") : V("muted") });
        // tensors never change; the check lights up their count
        tenOk.setAttribute("opacity", s.check.toFixed(3));
        // arrow and gate
        const ac = s.pin > .5 ? V("line") : bad ? V("bad") : V("teal");
        A(arrowLine, { stroke: ac, opacity: (s.flow * (1 - s.pin)).toFixed(3) });
        A(arrowHead, { fill: ac, opacity: (s.flow * (1 - s.pin)).toFixed(3) });
        gate.setAttribute("opacity", s.gate.toFixed(3));
        // renderer
        const sc = SC[s.sc];
        renEng.textContent = sc.eng;
        renL.forEach((t, i) => {
          t.textContent = sc.l[i];
          const isAdded = sc.l[i] === clip(added, 33) && i === 2;
          A(t, { fill: isAdded ? V("bad") : i % 2 === 0 ? V("muted") : V("ink"), "font-weight": isAdded ? 800 : 400 });
        });
        ansCan.textContent = sc.can;
        ansRest.textContent = sc.ans;
        const defended = s.pin > .5 || s.sbx > .5 || s.gate > .5;
        A(renBox, { stroke: defended ? V("ok") : V("violet") });
        A(renEng, { fill: defended ? V("ok") : V("violet") });
        // focus
        const rp = Math.round(s.pn);
        const focus = rp === 1 ? [gFile] : rp === 4 ? [gTen, gTpl] : rp === 3 ? [gTpl, gFile] : rp >= 5 && rp <= 7 ? [gTpl, gRen] : [];
        [gFile, gTen, gTpl, gRen].forEach(x => x.classList.toggle("hot", focus.includes(x)));
        el.classList.toggle("lx-focus", focus.length > 0);
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g2 = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }
          return api.tween(700, k => { if (g2 !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
