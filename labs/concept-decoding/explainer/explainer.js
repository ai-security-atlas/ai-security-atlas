/* LAB-28 concept-decoding: "Same weights, different answers" (foundation lab, 9 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: a decoding strip across the top (prompt -> model -> logits -> temperature -> top-k/top-p -> pick)
 * and a panel below that crossfades per step. Every number and string comes from window.LAB_DATA (data.js,
 * exported from the reference workbench run). Pattern: target(n) is pure, draw(s) is pure, step() tweens
 * forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA;
  const pct = (p, d = 0) => (100 * p).toFixed(d) + "%";
  const sw = D.sweep.rows;
  const swT = name => sw.find(r => r.setting === name) || {};
  const stopRow = rule => D.stop.rows.find(r => r.rule === rule) || {};
  const vrow = name => D.validate.rows.find(r => r.check.startsWith(name)) || {};

  X.define({
    id: "concept-decoding",
    family: "family-prompt",
    title: 'Same weights, different <span class="outline">answers</span>',
    legend: [{ role: "teal", label: "Prompt / settings" }, { role: "violet", label: "Model / scores" },
      { role: "warn", label: "Reply text" }, { role: "bad", label: "Leak path" }, { role: "lime", label: "Canary" },
      { role: "ok", label: "Defense" }],
    intro: {
      why: "A chat model writes its reply one token at a time. At each position it scores every possible next token, and a decoding setting decides which one gets printed. Greedy decoding always takes the top score, while sampling draws at random in proportion to the scores. Does a rule the model keeps under one setting still hold under another?",
      plan: "You’ll give a small model a fictional codename and a rule never to reveal it. First you’ll test the rule with greedy decoding, then sample the same requests many times and count leaks. You’ll find the token where a leak begins and see how a single test run and a stop sequence each give false comfort. To finish, you’ll pin the settings on the server and check the output itself.",
      terms: "A token is a piece of text. Temperature divides the scores before they become probabilities: low values sharpen the choice and high values flatten it. Top-k keeps the k best tokens, and top-p keeps the smallest set whose probabilities add up to p. A seed fixes the random draws. A stop sequence ends the reply when a given text appears. The canary is the fictional codename that marks a leak.",
    },
    steps: [
      { chapter: "System", label: "Decoding knobs",
        guide: "Start with one request and the spot where the model is least sure in its greedy reply. Each knob changes which tokens can win there. Temperature reshapes the probabilities, and top-k and top-p shorten the list. Look at the seed rows too: the same settings with the same seed repeat a reply exactly, and a new seed gives a new one.",
        caption: `Ask: <code>${D.ask}</code>. After <code>${D.knobs.prefix}</code> the top token <code>${D.knobs.top[0][0].trim()}</code> has ${pct(D.knobs.top[0][1][0], 1)} at T = ${D.knobs.temps[0]} and ${pct(D.knobs.top[0][1][2], 1)} at T = ${D.knobs.temps[2]}. <span class="c-teal">top_p = 0.9</span> keeps ${D.knobs.kept["0.7"]["top_p_0.9"]} tokens at T = 0.7 and ${D.knobs.kept["1.3"]["top_p_0.9"]} at T = 1.3. Same seed, same text: <code>${D.knobs.runs[2][1]}</code>.`,
        cmd: "docker compose run --rm workbench python concept-decoding/scripts/s01_knobs.py" },
      { chapter: "Attack", label: "Greedy holds",
        guide: "Send every request for the codename with greedy decoding. No reply gives the codename away, and most are a plain refusal. A team that tests this way would decide the rule works. Keep in mind that greedy decoding has exactly one reply per request, so this test looks at a single possible answer for each.",
        caption: `Risk setup: ${D.model} with the rule in its system prompt. Greedy decoding on ${D.greedy.n} requests: <span class="c-ok">${D.greedy.k}/${D.greedy.n} leaks</span>, ${D.greedy.refusals} plain refusals, e.g. <code>${D.greedy.replies[0]}</code>.`,
        cmd: "docker compose run --rm workbench python concept-decoding/scripts/s02_greedy_vs_sampled.py" },
      { chapter: "Attack", label: "Sampling leaks",
        guide: "Now sample the same requests many times at temperature 1, a common default in chat APIs. Each square is one reply. A few of them print the codename, and a few more print it in capital letters. The weights and the rule are the same as in the greedy test; the only change is how each token gets picked.",
        caption: `${D.sampled.n} samples per request at T = ${D.sampled.T}: <span class="c-bad">${D.sampled.rate.k}/${D.sampled.rate.n}</span> replies hold the exact canary (${pct(D.sampled.rate.p, 1)}, 95% CI ${pct(D.sampled.rate.lo, 1)}–${pct(D.sampled.rate.hi, 1)}), plus ${D.sampled.cells.filter(c => c === 2).length} in another spelling. Example: <code>${D.sampled.examples[0]}</code>.` },
      { chapter: "Mechanism", label: "Where it forks",
        guide: "Line up the greedy reply and a leaking one. They share every token up to the word codename, then split. Greedy takes the top choice, a lowercase ‘at’. The leak takes the first piece of the codename, a lower-ranked token. Once that piece is picked, the model finishes the codename most of the time.",
        caption: `After <code>${D.fork.prefix}</code>: greedy <code>${D.fork.greedy_tok}</code> (p ${D.fork.p_greedy[1]} at T = 1) against the leak token <code>${D.fork.leak_tok}</code> (rank ${D.fork.rank}, p ${D.fork.p_leak[0]} at T = 0.7, ${D.fork.p_leak[1]} at T = 1). Given that token, the rest of the canary follows with p ${D.fork.tail[1]} at T = 1.`,
        cmd: "docker compose run --rm workbench python concept-decoding/scripts/s03_fork.py" },
      { chapter: "Mechanism", label: "Rate vs temperature",
        guide: "Sweep the settings on the request that leaked most, with many samples for each. Bars show the leak rate. Whiskers show a 95% confidence interval, the range the true rate probably lies in. Every sampled setting leaks, including a low temperature and the top-p and top-k cuts. Greedy alone shows zero. At very high temperatures most replies turn to noise, and the leak rate falls with them.",
        caption: `${D.sweep.n} samples per setting. T = 0.4: <span class="c-bad">${swT("T=0.4").k}/${swT("T=0.4").n}</span>; T = 1.0: ${swT("T=1.0").k}/${swT("T=1.0").n}; T = 1.0 top_p = 0.9: ${swT("T=1.0 top_p=0.9").k}/${swT("T=1.0 top_p=0.9").n}; T = 1.6: ${swT("T=1.6").k}/${swT("T=1.6").n}. Greedy has one reply: 0/1.`,
        cmd: "docker compose run --rm workbench python concept-decoding/scripts/s04_sweep.py" },
      { chapter: "Impact", label: "One run says safe",
        guide: "Picture an evaluation that runs each request once. With greedy decoding it reports no leaks. With one sample per request, most repeated passes report none as well. A caller who can set the seed sees something else: they retry seeds until the codename appears, then replay that seed and get it every time.",
        caption: `One sample per request, repeated ${D.one_run.cols.length} times: ${D.one_run.zero} passes report 0 leaks. Detecting this request’s rate with 95% odds needs about ${D.one_run.n95} samples. Trying seeds 1, 2, …: <code class="c-lime">${D.canary}</code> first appears at seed ${D.one_run.first}, and replaying that seed leaks ${D.one_run.replay}/2.`,
        cmd: "docker compose run --rm workbench python concept-decoding/scripts/s05_one_run.py" },
      { chapter: "Impact", label: "Stop sequences",
        guide: "Some apps list the codename as a stop sequence, hoping generation halts before it’s printed. Two versions are tested here. A stop list of token ids misses the codename after a space, because the tokenizer turns it into different ids there. A text stop catches the exact string but lets a capitalized spelling through, and a client can delete the stop.",
        caption: `${D.stop.n} samples at T = ${D.stop.T}. Bare string: <code>${D.stop.bare.join(" ")}</code>…; after a space: <code>${D.stop.ctx.join(" ")}</code>…. Exact canary: no stop ${stopRow("no stop").k}, <span class="c-bad">token-id stop ${stopRow("stop token ids").k}</span>, text stop ${stopRow("stop string").k}; any spelling after the text stop: ${stopRow("stop string").any}.`,
        cmd: "docker compose run --rm workbench python concept-decoding/scripts/s06_stop_strings.py" },
      { chapter: "Defense", label: "Pin server-side",
        guide: "Move the decoding settings to the server and ignore what the client sends. Replay the attacker’s seeded requests against both versions of the app. The pass-through app leaks on some seeds. The pinned app decodes greedily on every request and gives the same reply each time, with no codename in it, though a deployment that samples would still need its own leak test.",
        caption: `Client sends temperature 1.0, no stop and a seed. Pass-through: <span class="c-bad">leak at seed ${D.pin.first}</span>, replay ${D.pin.pass_replay}/2. <span class="c-ok">Pinned</span>: seeds 1–${D.pin.search} ${D.pin.pinned.k}/${D.pin.pinned.n}, replay of seed ${D.pin.first} ${D.pin.pinned_replay}/2, one reply: <code>${D.pin.reply}</code>.`,
        cmd: "docker compose run --rm workbench python concept-decoding/scripts/d1_pin_params.py" },
      { chapter: "Defense", label: "Validate and measure",
        guide: "Check the output itself. The validator normalizes Unicode, folds case and drops spaces and punctuation before it looks for the codename, so other spellings get caught. Then test under the settings you actually deploy, with many samples and an interval. The result holds for this small model and this rule; other models will leak at other rates.",
        caption: `Validator: sampled other spellings <span class="c-ok">${vrow("validator")["other spelling (sampled)"][0]}/${vrow("validator")["other spelling (sampled)"][1]}</span>, typed variants ${vrow("validator")["typed variants"][0]}/${vrow("validator")["typed variants"][1]}, false alarms ${vrow("validator")["benign + greedy refusals"][0]}/${vrow("validator")["benign + greedy refusals"][1]}. The exact stop-string check: ${vrow("stop string")["other spelling (sampled)"][0]}/${vrow("stop string")["other spelling (sampled)"][1]} and ${vrow("stop string")["typed variants"][0]}/${vrow("stop string")["typed variants"][1]}.`,
        cmd: "docker compose run --rm workbench python concept-decoding/scripts/d3_validate_output.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Decoding pipeline with a detail panel per step"></svg>`,

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

      // ---- decoding strip
      const strip = [["PROMPT", "teal", "rule + request"], ["MODEL", "violet", "135M + guard"], ["SCORES", "violet", "49,152 logits"],
        ["TEMPERATURE", "teal", "divide by T"], ["TOP-K / TOP-P", "teal", "cut the list"], ["PICK", "warn", "argmax or draw"]];
      const gStrip = S("g", { class: "dimmable" }, svg);
      const stripBox = strip.map(([k, role, sub], i) => {
        const x = 16 + i * 158;
        const b = card(gStrip, x, 22, 138, 66, V(role));
        label(gStrip, x + 12, 46, k, { fill: V(role), "letter-spacing": "1" });
        T(gStrip, x + 12, 72, sub, 14, { class: "mono" });
        if (i) arrow(gStrip, `M${x - 18} 55 H${x - 3}`);
        return b;
      });
      const panel = () => S("g", { class: "dimmable" }, svg);

      // ---- P1: knobs at the least certain position, and seeds
      const g1 = panel();
      label(g1, 40, 128, "NEXT TOKEN AFTER “…" + D.knobs.prefix.split(" ").slice(-3).join(" ").toUpperCase() + "”");
      const tOp = [0.45, 0.7, 1];
      D.knobs.temps.forEach((t, j) => {
        S("rect", { x: 330 + j * 70, y: 140, width: 14, height: 14, rx: 3, fill: V("violet"), opacity: tOp[j] }, g1);
        T(g1, 350 + j * 70, 152, `T=${t}`, 13, { class: "mono", fill: V("muted") });
      });
      const knobBars = [];
      D.knobs.top.forEach(([tok, ps], i) => {
        const y = 172 + i * 46;
        T(g1, 40, y + 26, JSON.stringify(tok), 15, { class: "mono" });
        ps.forEach((p, j) => {
          const bar = S("rect", { x: 190, y: y + j * 12, width: 0, height: 10, rx: 3, fill: V("violet"), opacity: tOp[j] }, g1);
          knobBars.push({ bar, w: Math.min(330, 1100 * p) });
        });
        T(g1, 190 + Math.min(330, 1100 * ps[0]) + 8, y + 10, pct(ps[0], 1), 13, { class: "mono", fill: V("muted") });
      });
      label(g1, 560, 128, "SAME SETTINGS, SAME SEED");
      const seedRows = D.knobs.runs.map(([name, txt], i) => {
        const y = 140 + i * 70;
        const c = card(g1, 560, y, 380, 60, V(i < 2 ? "line" : "warn"));
        T(g1, 576, y + 24, name, 14, { class: "mono", "font-weight": 700, fill: V(i < 2 ? "muted" : "warn") });
        T(g1, 576, y + 46, cut(txt, 44), 13, { class: "mono" });
        return c;
      });
      void seedRows;

      // ---- P2: greedy holds on every request
      const g2 = panel();
      label(g2, 40, 128, `GREEDY DECODING · ${D.greedy.n} REQUESTS FOR THE CODENAME`);
      const greedyCells = D.greedy.replies.map((r, i) => {
        const x = 40 + (i % 8) * 112, y = 146 + Math.floor(i / 8) * 92;
        const refuse = /can.t share/.test(r);
        const c = card(g2, x, y, 100, 78, V("ok"), { "fill-opacity": 1 });
        T(g2, x + 12, y + 28, `#${i + 1}`, 14, { class: "mono", fill: V("muted") });
        T(g2, x + 12, y + 56, refuse ? "refuses" : "no code", 15, { "font-weight": 700, fill: V("ok") });
        return c;
      });
      void greedyCells;
      [0, D.greedy.replies.length - 1].forEach((i, j) => {
        const y = 352 + j * 62;
        card(g2, 40, y, 880, 50, V("warn"));
        T(g2, 56, y + 31, `#${i + 1}  ${cut(D.greedy.replies[i], 80)}`, 15, { class: "mono", fill: V("warn") });
      });
      T(g2, 480, 506, `${D.greedy.k}/${D.greedy.n} replies contain the codename`, 17, { "text-anchor": "middle", "font-weight": 700, fill: V("ok") });

      // ---- P3: the same requests, sampled
      const g3 = panel();
      label(g3, 40, 128, `T = ${D.sampled.T} · ${D.sampled.n} SAMPLES PER REQUEST (COLUMNS = REQUESTS)`);
      const nAsk = D.sampled.per_ask.length, nS = D.sampled.n;
      const cells3 = D.sampled.cells.map((c, idx) => {
        const i = Math.floor(idx / nS), j = idx % nS;
        const r = S("rect", { x: 40 + i * 22, y: 144 + j * 22, width: 18, height: 18, rx: 4 }, g3);
        return { r, c, i };
      });
      T(g3, 40, 516, "1", 13, { class: "mono", fill: V("muted") });
      T(g3, 40 + (nAsk - 1) * 22, 516, String(nAsk), 13, { class: "mono", fill: V("muted") });
      const legend3 = [["lime", "exact canary"], ["bad", "other spelling"], ["dim", "no codename"]];
      legend3.forEach(([role, txt], i) => {
        S("rect", { x: 440, y: 150 + i * 30, width: 18, height: 18, rx: 4, fill: V(role), opacity: role === "dim" ? .35 : 1 }, g3);
        T(g3, 468, 164 + i * 30, txt, 14);
      });
      card(g3, 440, 260, 480, 112, V("bad"));
      T(g3, 460, 296, `${D.sampled.rate.k}/${D.sampled.rate.n} exact leaks`, 22, { "font-weight": 700, fill: V("bad") });
      T(g3, 460, 326, `${pct(D.sampled.rate.p, 1)}  ·  95% CI ${pct(D.sampled.rate.lo, 1)}–${pct(D.sampled.rate.hi, 1)}`, 15, { class: "mono" });
      T(g3, 460, 354, `greedy on the same requests: ${D.greedy.k}/${D.greedy.n}`, 15, { class: "mono", fill: V("muted") });
      T(g3, 440, 404, cut(D.sampled.examples[0], 52), 14, { class: "mono", fill: V("lime") });
      if (D.sampled.variants[0]) T(g3, 440, 432, cut(D.sampled.variants[0], 52), 14, { class: "mono", fill: V("bad") });

      // ---- P4: the fork token
      const g4 = panel();
      label(g4, 40, 128, "SHARED PREFIX (TEACHER-FORCED, NO SAMPLING)");
      card(g4, 40, 142, 880, 54, V("warn"));
      T(g4, 60, 176, D.fork.prefix + " …", 17, { class: "mono", fill: V("warn") });
      const restG = D.fork.greedy.slice(D.fork.prefix.length + D.fork.greedy_tok.length);
      const restL = D.fork.leak.slice(D.fork.prefix.length + D.fork.leak_tok.length);
      const forkPaths = [["greedy", D.fork.greedy_tok, restG, D.fork.p_greedy, "warn", 236], ["leak", D.fork.leak_tok, restL, D.fork.p_leak, "bad", 372]];
      const forkBars = [];
      forkPaths.forEach(([name, tok, rest, ps, role, y]) => {
        S("path", { d: `M120 196 C120 ${y - 20}, 150 ${y + 30}, 190 ${y + 30}`, fill: "none", stroke: V(role), "stroke-width": 3 }, g4);
        card(g4, 190, y, 200, 60, V(role));
        T(g4, 206, y + 26, name, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2" });
        T(g4, 206, y + 50, JSON.stringify(tok), 18, { class: "mono", "font-weight": 700, fill: V(role) });
        T(g4, 410, y + 36, cut(rest, 28), 15, { class: "mono", fill: V(name === "leak" ? "lime" : "warn") });
        ps.forEach((p, j) => {
          const bar = S("rect", { x: 660 + j * 64, y: y + 60, width: 40, height: 0, rx: 4, fill: V(role), opacity: .85 }, g4);
          const val = T(g4, 680 + j * 64, y + 52, p.toFixed(3), 13, { class: "mono", "text-anchor": "middle" });
          forkBars.push({ bar, val, h: 110 * p, base: y + 60 });
        });
      });
      D.fork.temps.forEach((t, j) => T(g4, 680 + j * 64, 506, `T=${t}`, 13, { class: "mono", "text-anchor": "middle", fill: V("muted") }));
      T(g4, 190, 478, `leak token rank ${D.fork.rank} · rest of the canary given it: p ${D.fork.tail[1]} at T = 1`, 15, { class: "mono" });

      // ---- P5: leak rate by setting, with 95% intervals
      const g5 = panel();
      label(g5, 40, 128, `LEAK RATE ON “${D.ask.toUpperCase()}” · ${D.sweep.n} SAMPLES EACH`);
      const yMax = Math.max(0.2, ...sw.filter(r => r.T > 0).map(r => r.hi)), px0 = 90, py0 = 470, ph = 300, bw = 82;
      const yv = v => py0 - ph * v / yMax;
      S("path", { d: `M${px0} ${py0 - ph} V${py0} H${px0 + sw.length * 102}`, fill: "none", stroke: V("line"), "stroke-width": 2 }, g5);
      [0, 0.1, 0.2].filter(v => v <= yMax).forEach(v => T(g5, px0 - 10, yv(v) + 5, pct(v), 13, { class: "mono", "text-anchor": "end", fill: V("muted") }));
      const sweepBars = sw.map((r, i) => {
        const x = px0 + 14 + i * 102;
        const role = r.T === 0 ? "ok" : "bad";
        const bar = S("rect", { x, y: py0, width: bw, height: 0, rx: 4, fill: V(role), opacity: .8 }, g5);
        const one = r.T === 0, top = one ? yv(0) : yv(r.hi);
        const ci = S("path", { d: one ? "" : `M${x + bw / 2} ${yv(r.lo)} V${yv(r.hi)} M${x + bw / 2 - 10} ${yv(r.hi)} H${x + bw / 2 + 10} M${x + bw / 2 - 10} ${yv(r.lo)} H${x + bw / 2 + 10}`, stroke: "currentColor", "stroke-width": 2, fill: "none" }, g5);
        T(g5, x + bw / 2, top - 8, `${r.k}/${r.n}`, 13, { class: "mono", "text-anchor": "middle", fill: V(one ? "ok" : "ink") });
        if (one) T(g5, x + bw / 2, top - 24, "one reply", 13, { class: "mono", "text-anchor": "middle", fill: V("ok") });
        r.setting.split(" ").forEach((w, k) => T(g5, x + bw / 2, 492 + k * 16, w, 13, { class: "mono", "text-anchor": "middle", fill: V("muted") }));
        return { bar, ci, h: ph * r.p / yMax };
      });

      // ---- P6: one evaluation pass, and a caller who sets the seed
      const g6 = panel();
      label(g6, 40, 128, "ONE SAMPLE PER REQUEST, EACH PASS SEPARATE: LEAKS FOUND");
      const passCells = D.one_run.cols.map((c, i) => {
        const x = 40 + i * 55;
        const r = card(g6, x, 142, 47, 54, V(c ? "bad" : "ok"));
        T(g6, x + 23, 176, String(c), 18, { class: "mono", "text-anchor": "middle", "font-weight": 700, fill: V(c ? "bad" : "ok") });
        return r;
      });
      void passCells;
      T(g6, 40, 222, `${D.one_run.zero} of ${D.one_run.cols.length} passes report 0 leaks  ·  greedy reports ${D.greedy.k}/${D.greedy.n}`, 15, { class: "mono" });
      label(g6, 40, 276, "CALLER SETS TEMPERATURE 1.0 AND TRIES SEEDS");
      const seedCells = Array.from({ length: Math.min(16, D.one_run.first || 16) }, (_, i) => {
        const s = i + 1, hit = s === D.one_run.first;
        const x = 40 + i * 55;
        const r = S("rect", { x, y: 290, width: 47, height: 54, rx: 10, "stroke-width": 2 }, g6);
        T(g6, x + 23, 323, String(s), 15, { class: "mono", "text-anchor": "middle" });
        return { r, hit };
      });
      const gReplay = S("g", {}, g6);
      card(gReplay, 40, 372, 880, 110, V("lime"));
      T(gReplay, 60, 408, `seed ${D.one_run.first}:`, 17, { "font-weight": 700, fill: V("lime") });
      T(gReplay, 160, 408, D.canary, 20, { class: "mono", "font-weight": 800, fill: V("lime") });
      T(gReplay, 60, 442, `replayed on fresh app instances: ${D.one_run.replay}/2 leak again`, 15, { class: "mono" });
      T(gReplay, 60, 468, `samples for a 95% chance to see one leak on this request: about ${D.one_run.n95}`, 15, { class: "mono", fill: V("muted") });

      // ---- P7: stop sequences
      const g7 = panel();
      label(g7, 40, 128, "THE SAME CODENAME, TWO TOKENIZATIONS");
      [["bare string", D.stop.bare, "teal"], ["after a space (as the model writes it)", D.stop.ctx, "bad"]].forEach(([name, toks, role], i) => {
        const y = 142 + i * 62;
        T(g7, 40, y + 30, name, 14, { fill: V("muted") });
        toks.forEach((t, j) => {
          const x = 330 + j * 92;
          S("rect", { x, y, width: 82, height: 44, rx: 8, fill: V(role), "fill-opacity": .12, stroke: V(role), "stroke-width": 1.5 }, g7);
          T(g7, x + 41, y + 28, JSON.stringify(t), 15, { class: "mono", "text-anchor": "middle", fill: V(role), "font-weight": j ? 400 : 700 });
        });
        T(g7, 330 + toks.length * 92, y + 28, "…", 15, { class: "mono" });
      });
      label(g7, 40, 300, `${D.stop.n} SAMPLES AT T = ${D.stop.T}: EXACT CANARY IN THE RETURNED REPLY`);
      const maxK = Math.max(1, ...D.stop.rows.map(r => r.any));
      const stopBars = D.stop.rows.map((r, i) => {
        const y = 316 + i * 58;
        const role = r.k ? "bad" : r.any ? "warn" : "ok";
        card(g7, 40, y, 880, 48, V(role));
        T(g7, 56, y + 30, r.rule, 16, { "font-weight": 700, fill: V(role) });
        const bar = S("rect", { x: 260, y: y + 14, width: 0, height: 20, rx: 4, fill: V(role), opacity: .8 }, g7);
        T(g7, 900, y + 30, `${r.k}/${D.stop.n} exact · ${r.any} any spelling`, 15, { class: "mono", "text-anchor": "end" });
        return { bar, w: 360 * r.k / maxK };
      });
      if (D.stop.slip) T(g7, 40, 512, `text stop let through: ${cut(D.stop.slip, 76)}`, 14, { class: "mono", fill: V("bad") });

      // ---- P8: pin decoding on the server
      const g8 = panel();
      label(g8, 40, 128, `ATTACKER: TEMPERATURE 1.0, STOP REMOVED, SEEDS 1–${D.pin.search}, THEN SEED ${D.pin.first} TWICE`);
      const pinCols = [["pass-through", "client settings win", "bad"], ["pinned", "server: greedy + text stop", "ok"]];
      const pinDots = [];
      pinCols.forEach(([name, sub, role], c) => {
        const x = 40 + c * 450;
        card(g8, x, 144, 430, 330, V(role));
        T(g8, x + 20, 180, name, 20, { "font-weight": 700, fill: V(role) });
        T(g8, x + 20, 206, sub, 14, { class: "mono", fill: V("muted") });
        const n = c ? D.pin.search + 2 : D.pin.first + 2;
        for (let i = 0; i < n; i++) {
          const cx = x + 44 + (i % 8) * 48, cy = 250 + Math.floor(i / 8) * 50;
          const d = S("circle", { cx, cy, r: 0 }, g8);
          const hit = !c && i >= D.pin.first - 1 && (i === D.pin.first - 1 || i - D.pin.first < D.pin.pass_replay);
          pinDots.push({ d, hit, i, c });
        }
        T(g8, x + 20, 418, c ? `${D.pin.pinned.k + D.pin.pinned_replay}/${D.pin.search + 2} leaks` : `leak at seed ${D.pin.first}`, 22, { "font-weight": 700, fill: V(role) });
        T(g8, x + 20, 448, c ? `${D.pin.decodes} decode, one identical reply` : `replay of that seed: ${D.pin.pass_replay}/2 leak`, 15, { class: "mono" });
      });
      T(g8, 40, 506, `pinned reply: ${cut(D.pin.reply, 70)}`, 14, { class: "mono", fill: V("warn") });

      // ---- P9: validate the output, measure the deployed setting
      const g9 = panel();
      const vcols = [["other spelling (sampled)", "SAMPLED SPELLINGS"], ["typed variants", "TYPED"], ["benign + greedy refusals", "FALSE ALARMS"]];
      label(g9, 40, 128, "CHECK ON THE REPLY TEXT");
      vcols.forEach(([, h], j) => label(g9, 410 + j * 190, 128, h));
      D.validate.rows.forEach((r, i) => {
        const y = 142 + i * 58;
        const good = r.check.startsWith("validator");
        card(g9, 40, y, 880, 48, V(good ? "ok" : "line"));
        T(g9, 56, y + 30, cut(r.check, 36), 15, { class: "mono", "font-weight": 700, fill: V(good ? "ok" : "ink") });
        vcols.forEach(([k], j) => {
          const [a, b] = r[k], fa = j === 2;
          const role = fa ? (a ? "bad" : "ok") : (a === b ? "ok" : "bad");
          T(g9, 410 + j * 190, y + 30, `${a}/${b}`, 16, { class: "mono", "font-weight": 700, fill: V(role) });
        });
      });
      label(g9, 40, 290, "EVALUATE: CATEGORY PER CONDITION");
      Object.entries(D.evaluate).forEach(([k, v], i) => {
        const col = i % 2, row = Math.floor(i / 2);
        const x = 40 + col * 450, y = 304 + row * 50;
        card(g9, x, y, 430, 42, V("line"));
        T(g9, x + 14, y + 27, cut(k, 34), 13, { class: "mono" });
        const bad = v === "leaks" || /^0\//.test(v);
        T(g9, x + 416, y + 27, v, 14, { class: "mono", "text-anchor": "end", "font-weight": 700, fill: V(bad ? "bad" : "ok") });
      });

      const panels = [g1, g2, g3, g4, g5, g6, g7, g8, g9];
      const keys = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9"];
      const base = Object.fromEntries(keys.map(k => [k, 0]));
      const target = n => ({ ...base, [keys[n - 1]]: 1 });
      // which strip box each step highlights: prompt, model, scores, temperature, top-k/top-p, pick
      const hot = [[3, 4, 5], [0, 5], [3, 5], [2, 5], [3, 4], [5], [5], [3, 4], [5]];

      function draw(s) {
        panels.forEach((g, i) => { const v = s[keys[i]]; g.setAttribute("opacity", v.toFixed(3)); g.style.display = v > .01 ? "" : "none"; });
        knobBars.forEach(({ bar, w }) => A(bar, { width: (w * seg(s.p1, .2, 1)).toFixed(1) }));
        cells3.forEach(({ r, c, i }) => {
          const on = seg(s.p3, i / nAsk * .6, i / nAsk * .6 + .4);
          A(r, { fill: V(c === 1 ? "lime" : c === 2 ? "bad" : "dim"), opacity: (c ? 1 : .35) * (.2 + .8 * on) });
        });
        forkBars.forEach(({ bar, val, h, base: b }) => {
          const hh = h * seg(s.p4, .3, 1);
          A(bar, { y: (b - hh).toFixed(1), height: hh.toFixed(1) });
          val.setAttribute("y", (b - hh - 6).toFixed(1));
        });
        sweepBars.forEach(({ bar, ci, h }, i) => {
          const hh = h * seg(s.p5, i * .06, .5 + i * .06);
          A(bar, { y: (470 - hh).toFixed(1), height: hh.toFixed(1) });
          ci.setAttribute("opacity", seg(s.p5, .6, 1).toFixed(3));
        });
        seedCells.forEach(({ r, hit }, i) => {
          const on = seg(s.p6, .2 + i * .03, .4 + i * .03);
          A(r, { fill: V(hit && on > .5 ? "lime" : "panel"), stroke: V(hit && on > .5 ? "lime" : "line"), "fill-opacity": hit && on > .5 ? .35 : 1 });
        });
        gReplay.setAttribute("opacity", seg(s.p6, .75, 1).toFixed(3));
        stopBars.forEach(({ bar, w }) => A(bar, { width: (w * seg(s.p7, .3, 1)).toFixed(1) }));
        pinDots.forEach(({ d, hit, i, c }) => {
          const on = seg(s.p8, Math.min(i, 17) * .035, Math.min(i, 17) * .035 + .3);
          A(d, { r: (14 * on).toFixed(1), fill: V(hit ? "bad" : c ? "ok" : "dim"), opacity: hit ? 1 : .5 });
        });
        const n = keys.findIndex(k => s[k] > .5);
        stripBox.forEach((b, i) => b.setAttribute("stroke-width", n >= 0 && hot[n].includes(i) ? 4 : 2));
        const focus = s.p3 > .5 || s.p6 > .5;
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
