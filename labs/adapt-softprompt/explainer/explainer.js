/* LAB-58 adapt-softprompt: "A prompt you cannot read" (foundation lab, 8 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: the routing pipeline across the top (support message -> soft prompt -> frozen model ->
 * queue word -> stub router) and a detail panel below that crossfades per step. Every number and string
 * comes from window.LAB_DATA (data.js, exported from the reference workbench run).
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v;
  const D = window.LAB_DATA, T1 = D.task, SP = D.soft, RD = D.read, PF = D.prefix, SW = D.swap;
  const D1 = D.d1, D2 = D.d2, EV = D.evaluate, NH = D.n_heldout, G = D.gate;
  const N = n => n.toLocaleString("en");
  const files = ["softprompt", "softprompt-swapped", "softprompt-untrained"];
  const cands = ["softprompt", "softprompt-swapped", "softprompt-untrained", "prefix"];
  const accepted = cands.filter(c => D2[c].pass);

  X.define({
    id: "adapt-softprompt",
    family: "family-training",
    title: 'A prompt you cannot <span class="outline">read</span>',
    legend: [{ role: "teal", label: "Message / tokens" }, { role: "violet", label: "Frozen model" },
      { role: "warn", label: "Learned prompt" }, { role: "bad", label: "Wrong file" }, { role: "lime", label: "Canary" },
      { role: "ok", label: "Check / gate" }],
    intro: {
      "why": "A prompt is usually text you can read before you use it. Prompt tuning replaces that text with a few learned vectors placed in front of the input, and the model’s own weights stay frozen. The result is a small file that steers a shared model toward one task. Nobody can read that file as words, so reviewing it works differently. This lab measures what that means when such a file reaches you from someone else.",
      "plan": "You’ll start with a small support-desk task that a tiny model can’t solve from a written instruction. You’ll train eight vectors for it, try to turn them back into words, and then move the same idea into every layer with prefix tuning. Next comes a second file with the same shape, trained on swapped labels. Last, you’ll test which checks can tell the two files apart.",
      "terms": "A token is a word piece, and the embedding table holds one vector per token. A soft prompt is a short run of learned vectors that sits where token vectors would go. Prefix tuning learns key and value vectors inside every attention layer. Held-out rows are labeled messages that training never saw. The canary is a fixed, harmless string the stub router prints for each misrouted ticket."
    },
    steps: [
      { chapter: "System", label: "The task",
        guide: "The job is routing support messages to one of four queues. A small model reads each message and the lab scores the queue word it ranks highest. First you try two readable setups: the bare message, and the message with a written instruction in front. These baselines show what plain text achieves on this model.",
        caption: `${D.model} (${(T1.params / 1e6).toFixed(1)}M parameters, ${T1.layers} layers, width ${T1.hidden}). Held-out: no instruction <b>${T1.none.correct}/${NH}</b>, a ${T1.instruction_tokens}-token written instruction <b>${T1.written.correct}/${NH}</b>. With the instruction it picks ${Object.entries(T1.written.counts).filter(([, v]) => v).map(([k, v]) => `${k} ${v}×`).join(", ")}.`,
        cmd: "docker compose run --rm workbench python adapt-softprompt/scripts/s01_task.py" },
      { chapter: "System", label: "Train eight vectors",
        guide: "Prompt tuning adds a few trainable vectors in front of every message and freezes everything else. Gradient descent, the method that nudges numbers to lower an error, moves only those vectors so the right queue word wins. Watch the loss fall, then check the held-out rows. The stub router prints the canary for each ticket it would misroute.",
        caption: `${D.n_virtual} vectors × ${T1.hidden} = <span class="c-warn">${N(SP.trainable)}</span> trainable numbers; ${(SP.frozen / 1e6).toFixed(1)}M weights frozen. Loss ${SP.trace[0].toFixed(2)} → ${SP.trace[SP.trace.length - 1].toFixed(2)} in ${Math.round(SP.secs)} s. Training rows ${SP.train}/${D.n_train}, held-out <b>${SP.heldout}/${NH}</b>. File: ${N(SP.bytes)} bytes, sha256 <code>${SP.sha}</code>. Router: <code class="c-lime">${D.canary}</code> for ${SP.fired} misrouted ticket${SP.fired === 1 ? "" : "s"}.`,
        cmd: "docker compose run --rm workbench python adapt-softprompt/scripts/s02_train.py" },
      { chapter: "Attack", label: "Try to read it",
        guide: "A text prompt can be reviewed by reading it. Here you try the closest thing for a soft prompt: map each learned vector to the token whose vector points most nearly the same way. Look at how weak those matches are and how long the learned vectors are. Then paste the matching words back in as ordinary text and score the task again.",
        caption: `Risk: nearest-token cosine ${Math.min(...RD.near.map(n => n[1])).toFixed(3)}–${Math.max(...RD.near.map(n => n[1])).toFixed(3)} (a real token’s nearest neighbor: median ${RD.token_nn_cos_median.toFixed(3)}). Vector norms ${Math.min(...RD.norms).toFixed(1)}–${Math.max(...RD.norms).toFixed(1)}; vocabulary rows ${RD.vocab_norm_min.toFixed(2)}–${RD.vocab_norm_max.toFixed(2)}. Read as text: <code>${RD.text.trim()}</code>. Held-out: vectors <b>${RD.heldout_vectors}/${NH}</b>, their words <span class="c-bad">${RD.heldout_text}/${NH}</span>.`,
        cmd: "docker compose run --rm workbench python adapt-softprompt/scripts/s03_read.py" },
      { chapter: "Mechanism", label: "Every layer",
        guide: "A soft prompt enters once, at the input, and every layer reads it from there. Prefix tuning puts learned keys and values into each layer’s attention, so each layer sees extra positions that no token produced. You train it on the same task with the same settings. Then look at its size, and at how it scores on rows it trained on and on rows it didn’t.",
        caption: `Prefix: ${PF.layers} layers × keys and values × ${PF.kv_shape[1]} kv heads × ${PF.kv_shape[2]} positions × ${PF.kv_shape[3]} = <span class="c-warn">${N(PF.trainable)}</span> numbers (${(PF.trainable / SP.trainable).toFixed(0)}× the soft prompt), ${N(PF.bytes)} bytes. Training rows ${PF.train}/${D.n_train}, held-out <b>${PF.heldout}/${NH}</b> vs the soft prompt’s ${SP.heldout}/${NH}.${PF.heldout > SP.heldout ? " Here the learned positions in every layer also did better on new tickets." : PF.heldout < SP.heldout ? " Here the extra capacity did worse on new tickets." : ""}`,
        cmd: "docker compose run --rm workbench python adapt-softprompt/scripts/s04_prefix.py" },
      { chapter: "Impact", label: "A second file",
        guide: "Now a second prompt file arrives. It was made with the same recipe and has the same shape, size and settings file. Its training rows had billing and shipping swapped, a mistake you can’t see from outside. You attach it and route the held-out tickets. Count the canary lines, then see how well it learned its own training rows.",
        caption: `Observation: ${N(SW.bytes)} bytes, config keys that differ: ${SW.config_diff.length ? SW.config_diff.join(", ") : "none"}; sha256 <code>${SW.sha}</code> vs <code>${SP.sha}</code>. Held-out against the true queues <span class="c-bad">${SW.heldout_true}/${NH}</span>; the router logged <code class="c-lime">${D.canary}</code> for ${SW.fired}/${NH} tickets (the Step 2 file: ${SP.fired}). On its own training rows it follows the swap ${SW.train_swapped}/${D.n_train}.`,
        cmd: "docker compose run --rm workbench python adapt-softprompt/scripts/s05_swapped.py" },
      { chapter: "Defense", label: "Static checks",
        guide: "Before running a file, a reviewer can check it without the model: format, shape, settings, vector lengths and nearest tokens. You run those checks on the approved file, the swapped one and an untrained one. Then you add a hash pin, which is the fingerprint you recorded when you approved the first file. See which check separates the three.",
        caption: `Static checks see one shape and one config: ${D1.static_same}. Norm ranges of the approved and swapped files overlap: ${D1.norm_overlap_swapped}; the untrained file’s overlap a trained one: ${D1.norm_overlap_untrained}. Norm check (longer than any vocabulary row, max ${D1.vocab_norm_max.toFixed(2)}) flags ${D1.norm_flags}/3${D1.norm_flags === 3 ? ", so it spots soft prompts in general" : ""}. Max nearest-token cosine: ${files.map(f => `${f.replace("softprompt", "sp")} ${D1.rows[f].max_cos.toFixed(3)}`).join(", ")}. <span class="c-ok">sha256 pin</span> <code>${D1.pin}</code> accepts ${files.filter(f => D1.rows[f].pin).length}/3.`,
        cmd: "docker compose run --rm workbench python adapt-softprompt/scripts/d1_inspect.py" },
      { chapter: "Defense", label: "Behavior gate",
        guide: "A hash only tells you a file is the one you approved earlier. To approve a file in the first place, you need to test what it does. Attach each candidate to a fresh copy of the frozen model and score it on labeled rows you own. The gate asks for a total score and a floor in every queue. Check which files pass.",
        caption: `Gate: ≥ ${G.total}/${NH} and ≥ ${G.per_queue}/6 per queue. ${cands.map(c => `${c} ${D2[c].total}/${NH} <span class="c-${D2[c].pass ? "ok" : "bad"}">${D2[c].pass ? "ACCEPT" : "REJECT"}</span>`).join("; ")}. Accepted: ${accepted.join(", ") || "none"}.`,
        cmd: "docker compose run --rm workbench python adapt-softprompt/scripts/d2_acceptance.py" },
      { chapter: "Defense", label: "What it shows",
        guide: "The evaluation retrains the soft prompt from scratch and re-scores the saved files. On this model, a few learned vectors beat a written instruction, and their nearest words do almost nothing. Static checks can’t tell a right file from a wrong one. A hash pin plus a behavior test can, but only for behavior your test rows cover.",
        caption: `Fresh run: base ${EV["base, no instruction: held-out correct (of 24)"]}/${NH} and ${EV["base, written instruction: held-out correct (of 24)"]}/${NH}; fresh soft prompt <b>${EV["fresh soft prompt: held-out correct (of 24)"]}/${NH}</b>, its words ${EV["nearest tokens as text: held-out correct (of 24)"]}/${NH}; prefix ${EV["prefix file: held-out correct (of 24)"]}/${NH}; swapped ${EV["swapped file: held-out correct (of 24)"]}/${NH}. Pin accepts ${EV["sha256 pin accepts (of 3 soft prompt files)"]}/3; <span class="c-ok">gate</span> accepts the Step 2 file (${EV["D2 gate accepts the Step 2 file"]}) and rejects the swapped one (${EV["D2 gate rejects the swapped file"]}).`,
        cmd: "docker compose run --rm workbench python adapt-softprompt/scripts/evaluate.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Support message, learned soft prompt, frozen model, queue word and stub router, with a detail panel"></svg>`,

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
      const bar = (p, x, y, w, h, frac, c, o = .85) => {
        S("rect", { x, y, width: w, height: h, rx: 6, fill: "none", stroke: V("line"), "stroke-width": 1.5 }, p);
        return S("rect", { x, y, width: Math.max(3, w * frac), height: h, rx: 6, fill: V(c), opacity: o }, p);
      };

      // ---- pipeline strip (top)
      const strip = [
        { k: "msg", x: 16, w: 150, t: "MESSAGE", s: "support ticket", c: "teal" },
        { k: "sp", x: 190, w: 160, t: "LEARNED PROMPT", s: `${D.n_virtual} vectors`, c: "warn" },
        { k: "mdl", x: 374, w: 200, t: "FROZEN MODEL", s: `${(T1.params / 1e6).toFixed(1)}M, ${T1.layers} layers`, c: "violet" },
        { k: "q", x: 598, w: 150, t: "QUEUE WORD", s: `${D.queues.length} queue words`, c: "teal" },
        { k: "rt", x: 772, w: 172, t: "ROUTER", s: "stub, prints only", c: "ok" },
      ];
      strip.forEach((b, i) => {
        const g = S("g", { class: "dimmable" }, svg);
        b.box = card(g, b.x, 34, b.w, 84, V(b.c));
        label(g, b.x + 14, 64, b.t, { "letter-spacing": "1" });
        b.sub = T(g, b.x + 14, 96, b.s, 14, { class: "mono" });
        if (i < strip.length - 1) arrow(svg, b.x + b.w + 2, strip[i + 1].x - 4, 76);
        b.g = g;
      });
      const spSub = strip[1].sub;
      const canaryTag = T(svg, 858, 146, D.canary, 14, { "text-anchor": "middle", class: "mono", fill: V("lime"), "font-weight": 700 });

      // ---- detail panels (bottom); each is a group whose opacity the state sets
      const P = [];
      const panel = (title) => { const g = S("g", {}, svg); card(g, 16, 172, 928, 352); label(g, 40, 204, title); P.push(g); return g; };

      // 1: readable baselines
      const p1 = panel("HELD-OUT ROUTING WITH PLAIN TEXT");
      [["bare message", T1.none], ["written instruction", T1.written]].forEach(([k, r], i) => {
        const y = 236 + i * 110;
        T(p1, 40, y + 20, k, 16, { "font-weight": 700 });
        bar(p1, 240, y, 400, 28, r.correct / NH, "teal");
        T(p1, 656, y + 20, `${r.correct}/${NH} correct`, 15, { class: "mono" });
        D.queues.forEach((q, j) => {
          const x = 240 + j * 100;
          T(p1, x, y + 58, `${q} ${r.counts[q]}`, 13, { class: "mono", fill: V(r.counts[q] ? "ink-2" : "muted") });
          S("rect", { x, y: y + 66, width: Math.max(2, 88 * r.counts[q] / NH), height: 8, rx: 3, fill: V("violet"), opacity: .7 }, p1);
        });
      });
      T(p1, 40, 488, `predicted queues per setup (6 of each are correct); instruction: ${T1.instruction_tokens} readable tokens`, 14, { fill: V("muted") });

      // 2: training the soft prompt
      const p2 = panel("TRAINING: ONLY THE LEARNED VECTORS MOVE");
      const tr = SP.trace, tmax = Math.max(...tr);
      const pts = tr.map((v, i) => `${40 + i * (420 / (tr.length - 1))},${460 - 200 * v / tmax}`).join(" ");
      S("path", { d: "M40 460 L470 460 M40 250 L40 460", stroke: V("line"), "stroke-width": 2, fill: "none" }, p2);
      S("polyline", { points: pts, fill: "none", stroke: V("warn"), "stroke-width": 3 }, p2);
      T(p2, 48, 248, `loss ${tr[0].toFixed(2)}`, 13, { class: "mono", fill: V("muted") });
      T(p2, 470, 452, `${tr[tr.length - 1].toFixed(2)}`, 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
      T(p2, 40, 488, `${Math.round(SP.secs)} s on a shared CPU`, 13, { fill: V("muted") });
      for (let i = 0; i < D.n_virtual; i++) S("rect", { x: 540 + i * 46, y: 236, width: 38, height: 38, rx: 7, fill: V("warn"), opacity: .8 }, p2);
      T(p2, 540, 300, `${N(SP.trainable)} trainable numbers`, 15, { "font-weight": 700, fill: V("warn") });
      T(p2, 540, 326, `${(SP.frozen / 1e6).toFixed(1)}M weights frozen`, 14, { fill: V("violet") });
      bar(p2, 540, 352, 360, 26, SP.heldout / NH, "ok");
      T(p2, 540, 400, `held-out ${SP.heldout}/${NH} (written instruction ${T1.written.correct}/${NH})`, 14, { class: "mono" });
      T(p2, 540, 432, `file ${N(SP.bytes)} bytes · sha256 ${SP.sha}`, 13, { class: "mono", fill: V("muted") });

      // 3: nearest tokens
      const p3 = panel("EACH VECTOR’S NEAREST TOKEN");
      const nMax = Math.max(...RD.norms, RD.vocab_norm_max);
      RD.near.forEach(([tk, c], i) => {
        const y = 226 + i * 30;
        T(p3, 40, y + 16, `v${i}`, 14, { class: "mono", fill: V("warn") });
        S("rect", { x: 80, y: y + 2, width: 200 * RD.norms[i] / nMax, height: 18, rx: 4, fill: V("warn"), opacity: .75 }, p3);
        T(p3, 290, y + 16, RD.norms[i].toFixed(1), 13, { class: "mono" });
        T(p3, 350, y + 16, JSON.stringify(tk.replace("Ġ", "␣")), 14, { class: "mono" });
        T(p3, 520, y + 16, `cos ${c.toFixed(3)}`, 13, { class: "mono", fill: V("muted") });
      });
      S("rect", { x: 80, y: 466, width: Math.max(3, 200 * RD.vocab_norm_max / nMax), height: 10, rx: 3, fill: V("teal"), opacity: .8 }, p3);
      T(p3, 290, 476, `longest token row ${RD.vocab_norm_max.toFixed(2)}`, 13, { fill: V("teal") });
      T(p3, 640, 260, "held-out", 13, { fill: V("muted"), "font-weight": 700 });
      T(p3, 640, 290, "vectors", 14);
      bar(p3, 720, 276, 190, 20, RD.heldout_vectors / NH, "warn");
      T(p3, 640, 330, "as words", 14);
      bar(p3, 720, 316, 190, 20, RD.heldout_text / NH, "bad");
      T(p3, 640, 368, `${RD.heldout_vectors}/${NH} vs ${RD.heldout_text}/${NH}`, 15, { class: "mono", "font-weight": 700 });
      T(p3, 640, 410, clip(RD.text.trim(), 26), 13, { class: "mono", fill: V("muted") });

      // 4: soft prompt vs prefix, layer by layer
      const p4 = panel("WHERE THE LEARNED NUMBERS GO");
      const L = PF.layers, rowH = 7;
      [["soft prompt", 40, false], ["prefix tuning", 300, true]].forEach(([k, x0, every]) => {
        T(p4, x0, 234, k, 14, { "font-weight": 700, fill: V("warn") });
        for (let l = 0; l < L; l++) {
          const y = 470 - l * rowH;
          S("rect", { x: x0, y, width: 110, height: rowH - 2, rx: 2, fill: V("violet"), opacity: .25 }, p4);
          if (every || l === 0) S("rect", { x: x0 + 116, y, width: 90, height: rowH - 2, rx: 2, fill: V("warn"), opacity: .85 }, p4);
        }
        T(p4, x0, 496, every ? `keys + values in all ${L} layers` : "input rows, layer 0 only", 13, { fill: V("muted") });
      });
      [["", "soft", "prefix"], ["numbers", N(SP.trainable), N(PF.trainable)], ["file bytes", N(SP.bytes), N(PF.bytes)],
        ["training rows", `${SP.train}/${D.n_train}`, `${PF.train}/${D.n_train}`], ["held-out", `${SP.heldout}/${NH}`, `${PF.heldout}/${NH}`]]
        .forEach((r, i) => r.forEach((c, j) => T(p4, 590 + j * 112, 260 + i * 40, c, 14, { class: j ? "mono" : "", "font-weight": i ? 400 : 700, fill: V(i ? "ink" : "muted") })));

      // 5: the swapped file
      const p5 = panel("TWO FILES, ONE SHAPE");
      [["Step 2 file", SP.sha, SP.heldout, SP.fired, "warn"], ["swapped file", SW.sha, SW.heldout_true, SW.fired, "bad"]].forEach(([k, sha, ho, fired, c], i) => {
        const x = 40 + i * 300;
        card(p5, x, 226, 270, 244, V(c));
        T(p5, x + 16, 256, k, 15, { "font-weight": 700, fill: V(c) });
        T(p5, x + 16, 284, `${N(i ? SW.bytes : SP.bytes)} bytes · ${SW.config_diff.length ? "config differs" : "same config"}`, 13, { class: "mono", fill: V("muted") });
        T(p5, x + 16, 308, `sha256 ${sha}`, 13, { class: "mono" });
        for (let j = 0; j < D.n_virtual; j++) S("rect", { x: x + 16 + j * 30, y: 324, width: 24, height: 24, rx: 5, fill: V(c), opacity: .7 }, p5);
        T(p5, x + 16, 380, "held-out, true queues", 13, { fill: V("muted") });
        bar(p5, x + 16, 390, 238, 20, ho / NH, c);
        T(p5, x + 16, 440, `${ho}/${NH} · canary lines ${fired}`, 15, { class: "mono", "font-weight": 700 });
      });
      card(p5, 660, 290, 264, 112, V("lime"));
      T(p5, 676, 322, "router log", 13, { fill: V("muted") });
      T(p5, 676, 352, D.canary, 15, { class: "mono", fill: V("lime"), "font-weight": 700 });
      T(p5, 676, 380, `${SW.fired}/${NH} swapped-file tickets`, 13);

      // 6: static checks grid
      const p6 = panel("STATIC CHECKS ON THREE FILES");
      const heads = ["approved", "swapped", "untrained"];
      heads.forEach((h, j) => T(p6, 400 + j * 180, 236, h, 14, { "font-weight": 700, fill: V("muted") }));
      const same = () => (D1.static_same ? "same" : "differs"), sameC = () => (D1.static_same ? "ok" : "warn");
      const checks = [["format, shape, dtype", same, sameC], ["peft config", same, sameC],
        ["norms", f => `${D1.rows[f].norm_min.toFixed(1)}–${D1.rows[f].norm_max.toFixed(1)}`, () => "warn"],
        ["max nearest cosine", f => D1.rows[f].max_cos.toFixed(3), () => "warn"],
        ["sha256 pin", f => (D1.rows[f].pin ? "match" : "MISMATCH"), f => (D1.rows[f].pin ? "ok" : "bad")]];
      checks.forEach(([k, val, col], i) => {
        const y = 256 + i * 48;
        T(p6, 40, y + 22, k, 15);
        files.forEach((f, j) => {
          const c = col(f);
          S("rect", { x: 400 + j * 180, y, width: 150, height: 34, rx: 8, fill: V(c), opacity: .2 }, p6);
          T(p6, 412 + j * 180, y + 23, val(f), 14, { class: "mono", "font-weight": 700, fill: V(c === "warn" ? "ink" : c) });
        });
      });

      // 7: behavior gate
      const p7 = panel(`BEHAVIOR GATE: ≥ ${G.total}/${NH} AND ≥ ${G.per_queue}/6 PER QUEUE`);
      const gx = 300 + 520 * G.total / NH;
      cands.forEach((c, i) => {
        const y = 236 + i * 60, r = D2[c];
        T(p7, 40, y + 20, c, 15, { class: "mono" });
        bar(p7, 300, y, 520, 28, r.total / NH, r.pass ? "ok" : "bad");
        T(p7, 836, y + 20, `${r.total}/${NH} ${r.pass ? "ACCEPT" : "REJECT"}`, 14, { class: "mono", "font-weight": 700, fill: V(r.pass ? "ok" : "bad") });
        T(p7, 300, y + 46, D.queues.map(q => `${q} ${r.per[q]}/6`).join("  "), 12.5, { class: "mono", fill: V("muted") });
      });
      S("path", { d: `M${gx} 226 L${gx} 476`, stroke: V("ok"), "stroke-width": 2, "stroke-dasharray": "5 4" }, p7);

      // 8: evaluation summary
      const p8 = panel("FRESH RUN");
      Object.entries(EV).forEach(([k, v], i) => {
        const col = i % 2, row = Math.floor(i / 2), x = 40 + col * 456, y = 236 + row * 36;
        T(p8, x, y, clip(k, 42), 13);
        T(p8, x + 370, y, String(v), 13, { class: "mono", "font-weight": 700, fill: V(v === true || typeof v === "number" ? "ok" : "muted") });
      });

      // ---- state
      const HOT = [null, ["msg", "mdl", "q"], ["sp", "mdl"], ["sp"], ["sp", "mdl"], ["sp", "rt"], ["sp"], ["sp", "q"], []];
      const st = { p: 1, c: 0 };
      const target = n => ({ p: n, c: n === 2 || n === 5 ? 1 : 0 });

      function draw(s) {
        P.forEach((g, i) => {
          const o = Math.max(0, 1 - Math.abs(s.p - (i + 1)) * 1.6);
          g.setAttribute("opacity", o.toFixed(3));
          g.setAttribute("visibility", o > 0.01 ? "visible" : "hidden");
        });
        A(canaryTag, { opacity: s.c.toFixed(3) });
        const n = Math.round(s.p);
        spSub.textContent = n === 1 ? "none yet" : n === 4 ? "in every layer" : n === 5 ? "which file?" : `${D.n_virtual} vectors`;
        A(strip[1].box, { stroke: V(n === 5 ? "bad" : "warn") });
        A(strip[4].box, { stroke: V(s.c > .5 ? "lime" : "ok") });
        const hot = HOT[n] || [];
        strip.forEach(b => b.g.classList.toggle("hot", hot.includes(b.k)));
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
