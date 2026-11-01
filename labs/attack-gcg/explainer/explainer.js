/* LAB-21 attack-gcg: "Optimizing a suffix one token at a time" (10 steps).
 * Chapters: System (the victim) · Attack (the loss) · Mechanism (one-hot gradient, one hand step
 * and its race, the search) · Impact (the pinned suffix, transfer) · Defense (perplexity filter,
 * rewrite, perturb and vote). One persistent scene across the top: the chat template as tokens
 * (system turn, request, the suffix cells, assistant turn) -> the victim model -> the greedy
 * reply. A gradient ribbon flows back to the suffix cells during the mechanism steps, and a
 * defense wall rises in the Defend steps. A detail panel below changes per step. Every number
 * and every run string (suffix, target, replies, token ids) comes from window.LAB_DATA
 * (data.js, exported from the reference workbench run).
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp, E = X.ease;
  const D = window.LAB_DATA;
  const BEST = D.gradient.rows.find(r => r.pos === D.gradient.best_pos);
  const OK_N = D.loss.rows.filter(r => r.ok).length;
  const P_WHOLE = Math.exp(-D.loss.rows.reduce((a, r) => a + r.nll, 0)).toExponential(1);
  const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const clip = (s, n) => (String(s).length > n ? String(s).slice(0, n - 1) + "…" : String(s));
  const line1 = s => String(s).split("\n")[0];
  const N = n => n.toLocaleString("en");

  X.define({
    id: "attack-gcg",
    family: "family-prompt",
    title: 'Optimizing a suffix one <span class="outline">token</span> at a time',
    legend: [{ role: "teal", label: "Request tokens" }, { role: "bad", label: "Suffix / gradient" },
      { role: "violet", label: "Model" }, { role: "warn", label: "Reply" }, { role: "lime", label: "Canary" },
      { role: "ok", label: "Defense" }],
    intro: {
      "why": "You can type anything you like after a question, and a language model will read every token of it. This lab asks what an attacker can do with that: append a short string of tokens to an ordinary request and optimize it with the model’s own gradients until the reply opens with a string the attacker chose. The target is a fixed, harmless canary, and the victim is a small open model that answers a recipe question.",
      "plan": "You’ll meet the tiny victim and see your prompt as tokens, with a marked hole for a suffix right after the request. Then you’ll score a chosen target with the loss, read the gradient that ranks every possible token swap, and take one step by hand before letting a search run the loop. A pinned, shipped suffix then forces the canary deterministically, and the lab closes with a transfer test and three prompt-side defenses.",
      "terms": "A token is a piece of text the model actually reads; the tokenizer turns your prompt into token ids. An adversarial suffix is a short token string the attacker appends to a request. The loss is the negative log-probability of a chosen target string given the prompt; a lower loss means the model finds the target more likely. A gradient says which direction of change lowers the loss. Greedy decoding always takes the most likely next token, which makes it deterministic. The canary is this lab’s fixed, inert target string."
    },
    steps: [
      { chapter: "System", label: "The tiny victim",
        guide: "Meet the model under test. It is a small open assistant that answers a recipe question, and it guards nothing, so no safety bypass is involved anywhere. Your whole conversation reaches it as tokens: a system line, your request, a marked hole for a suffix, and the opening of the reply. With the hole empty, it just answers.",
        caption: `The victim is <span class="c-violet">${D.pinned.provenance.victim}</span>: ${(D.fetch.params / 1e6).toFixed(1)}M parameters, ${D.fetch.layers} decoder layers, ${N(D.fetch.vocab)} possible tokens at every step, fp32 on your CPU. The chat template holds the request with a hole for a ${D.n_suffix}-token suffix inside your user turn, and greedy decoding answers the clean prompt: <span class="c-warn">“${esc(clip(D.fetch.reply, 44))}…”</span>`,
        cmd: "docker compose run --rm workbench python attack-gcg/scripts/s01_fetch.py" },
      { chapter: "Attack", label: "Score the target",
        guide: "Define success before searching. The attacker picks a target string, the fixed canary, and appends a starting suffix of filler tokens to the request. The loss is the average negative log-probability of the target given the whole prompt, and every later step exists to push that one number down. A couple of target tokens already match by luck.",
        caption: `Target <code class="c-lime">${D.canary}</code> = ${D.loss.rows.length} tokens. The model’s top pick already matches ${OK_N} of them by accident (${D.loss.rows.filter(r => r.ok).map(r => "“" + r.tok + "”").join(", ")}). Loss = mean −log p = <b>${D.loss.loss.toFixed(3)}</b>, and the whole target together has p ≈ ${P_WHOLE}, so the canary is nearly impossible right now.`,
        cmd: "docker compose run --rm workbench python attack-gcg/scripts/s02_loss.py" },
      { chapter: "Mechanism", label: "One-hot gradient",
        guide: "A token id is discrete, so the loss has no direct derivative for swapping it. The one-hot trick fixes that: treat each suffix position as a blend over the whole vocabulary, and backpropagate once. The gradient that comes back ranks every single-token swap you could make at every position. White-box access is what buys that ranking.",
        caption: `∂loss/∂onehot has shape ${D.gradient.shape[0]} × ${N(D.gradient.shape[1])}: every suffix position against every vocabulary token. Best single swap from one pass: position ${D.gradient.best_pos}, “${esc(BEST.current)}” → “${esc(BEST.swap)}”, predicted loss ${D.gradient.loss.toFixed(3)} → ${(D.gradient.loss + BEST.dloss).toFixed(3)} (${BEST.dloss}). Banned before sampling (non-ASCII pieces, canary fragments): ${N(D.gradient.n_banned)} of ${N(D.gradient.shape[1])}.`,
        cmd: "docker compose run --rm workbench python attack-gcg/scripts/s03_gradient.py" },
      { chapter: "Mechanism", label: "One step, raced",
        guide: "Take one step by hand. Sample candidate swaps from the gradient’s top-k, run the model forward on every candidate prompt, and keep the one with the lowest loss. The gradient only ranks candidates; the real forward pass decides. Then spend the same budget on random swaps and race the two. Random grabs the easy early wins and stalls, while the gradient keeps going down.",
        caption: `One step: ${D.step.onestep.n} swaps sampled from the top ${D.step.topk}; ${D.step.onestep.beat} of ${D.step.onestep.n} beat the current suffix; best ${D.step.loss.toFixed(3)} → <b>${D.step.onestep.best.toFixed(3)}</b> (${esc(D.step.onestep.swap)}), confirmed by a fresh forward pass (${D.step.onestep.remeasured.toFixed(3)}). Race, ${D.step.race.budget} forward evaluations each: gradient <span class="c-bad">${D.step.race.gradient.toFixed(3)}</span> vs random ${D.step.race.random.toFixed(3)}; random led in round ${D.step.race.hist.filter(h => h.round > 0 && h.random < h.gradient).map(h => h.round).join(", ")} and then stalled.`,
        cmd: "docker compose run --rm workbench python attack-gcg/scripts/s04_step.py" },
      { chapter: "Mechanism", label: "The search loop",
        guide: "Now let nanoGCG run that loop and print the loss after every step. The short run you can do yourself moves steadily but stays far from the near-zero loss an exact target needs. The seconds-per-step figure tells you what a longer run would cost. The lab also ships the result of a much longer search, saved as a fixed file.",
        caption: `Student run: loss ${D.loss.loss.toFixed(3)} → ${D.search.best_loss.toFixed(3)} over ${D.search.steps} steps (${D.search.s_per_step.toFixed(1)} s/step on a busy CPU), canary found: ${D.search.found ? "yes" : "no"}. The shipped asset came from the long run: ${D.long.steps_run} steps of the ${D.pinned.provenance.config.steps} allowed, ${(D.long.seconds / 60).toFixed(0)} min at ${D.long.s_per_step.toFixed(1)} s/step, best GCG loss ${D.long.best_loss.toFixed(3)}.`,
        cmd: "docker compose run --rm workbench python attack-gcg/scripts/s05_search.py --steps 8 --width 32 --topk 32" },
      { chapter: "Impact", label: "Gibberish that steers",
        guide: "Load the pinned suffix and decode greedily. It reads as word salad, yet the reply opens with the canary and then echoes it. Decode the same prompt again and again and you get the identical string, because greedy decoding is deterministic. The search optimized the exact token ids the deployed template produces, and the model obeys them on this one victim.",
        caption: `Suffix as a human reads it: “${esc(D.pinned.suffix)}” (${D.pinned.tokens.length} tokens). GCG loss ${D.loss.loss.toFixed(3)} → <b>${D.pinned.loss.toFixed(3)}</b>. Greedy reply: <code class="c-lime">${D.canary}</code>, echoed; all ${D.pinned.replies.length} decodes identical (${D.pinned.deterministic}). The reply opens with the canary <code class="c-lime">${D.canary}</code> every time, in the reference run on this victim.`,
        cmd: "docker compose run --rm workbench python attack-gcg/scripts/s06_pinned.py" },
      { chapter: "Impact", label: "Does it transfer?",
        guide: "Take the frozen suffix to models the optimizer never saw. The sibling model from the same family ignores it and answers the recipe question, and the chat model behind an optional API objects to the gibberish. Reusing a ready-made suffix is much weaker than optimizing one with gradients against the target model, and the transfer result shows it.",
        caption: `Frozen suffix, held-out models. ${D.transfer.rows[1].model} (${D.transfer.rows[1].note}): replies “${esc(clip(D.transfer.rows[1].suffix, 40))}…”, canary ${D.transfer.rows[1].canary ? "yes" : "no"}. ${D.transfer.rows[2].model} (${D.transfer.rows[2].note}): “${esc(clip(D.transfer.rows[2].suffix, 40))}…”, canary ${D.transfer.rows[2].canary ? "yes" : "no"}. Source row (${D.transfer.rows[0].model}) still fires. Transfer verdict: <b>${D.transfer.n_transfer}/${D.transfer.n_heldout}</b> held-out models, in this reference run.`,
        cmd: "docker compose run --rm workbench python attack-gcg/scripts/s07_transfer.py" },
      { chapter: "Defense", label: "A perplexity filter",
        guide: "Score every incoming prompt with a language model and flag text it finds implausible. The threshold here comes from ordinary prompts alone, fixed before any suffix is scored, and the scorer is the victim itself. The fully optimized suffix lands far past the threshold, the benign sets stay under it, and partly optimized suffixes slip through.",
        caption: `Scorer: the victim itself, over the whole user prompt. Threshold ${D.d1.threshold.toFixed(0)} = 2 × ${D.d1.calibration.max}, the worst of ${D.d1.calibration.n} ordinary prompts. Pinned-suffix prompt: ppl <b>${N(D.d1.suffix_ppl)}</b>, ${(D.d1.suffix_ppl / D.d1.threshold).toFixed(0)}× over. Partly optimized suffixes from the student run: ${D.d1.caught} of ${D.d1.n_suffixes} caught. Benign sets: ordinary max ${D.d1.calibration.max}, technical-but-benign max ${D.d1.unusual.max} with ${D.d1.fp_unusual}/${D.d1.unusual.n} flagged.`,
        cmd: "docker compose run --rm workbench python attack-gcg/scripts/d1_perplexity.py" },
      { chapter: "Defense", label: "Rewrite the ids",
        guide: "A suffix is tuned to exact token ids at exact positions, so rewrite the prompt and the ids shift. Normalizing Unicode and collapsing whitespace breaks the canary, and rewording the request breaks it too. The exact decode-and-reencode round trip changes nothing, because the search refused candidates that failed it. The same rewrites also touch prompts from honest users.",
        caption: `The pinned prompt is ${D.d2.rows[0].ids} token ids. “${D.d2.rows[2].variant}” changes ${D.d2.rows[2].changed}/${D.d2.rows[2].ids} ids → reply “${esc(line1(D.d2.rows[2].reply))}”, canary gone. “${D.d2.rows[3].variant}” changes ${D.d2.rows[3].changed}/${D.d2.rows[3].ids} → “${esc(line1(D.d2.rows[3].reply))}”, one token off. “${D.d2.rows[1].variant}” changes ${D.d2.rows[1].changed}. Canary survives ${D.d2.n_canary} of ${D.d2.rows.length} variants.`,
        cmd: "docker compose run --rm workbench python attack-gcg/scripts/d2_retokenize.py" },
      { chapter: "Defense", label: "Perturb and vote",
        guide: "Change random characters in the prompt, run several copies, and answer by majority vote. A suffix tuned to exact tokens can’t survive several noisy versions, and the canary loses the vote. The same noise also costs the model most of its correct answers. Every defense here was measured against one fixed suffix. An attacker who optimizes against the defense itself hasn’t been tested yet.",
        caption: `SmoothLLM: q = ${D.d3.q} copies, random-insert ${D.d3.pct}% of characters, scorer = the victim. Canary copies: ${D.d3.votes} of ${D.d3.copies.length} → majority says no canary. Utility on ${D.d3.n} held-out questions: ${D.d3.clean_acc}/${D.d3.n} clean → <b>${D.d3.majority_acc}/${D.d3.n}</b> with perturbation.`,
        cmd: "docker compose run --rm workbench python attack-gcg/scripts/d3_smooth.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="A chat prompt with a suffix hole, the victim model and its greedy reply, with a measurement panel below"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) =>
        S("rect", { x, y, width: w, height: h, rx: 14, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const qt = s => JSON.stringify(s);
      const mono = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { class: "mono", ...o });
      function wrap(s, n = 34, max = 6) {
        const out = [];
        let line = "";
        for (const w of String(s).split(" ")) {
          if ((line + " " + w).trim().length > n && line) { out.push(line); line = w; } else line = (line + " " + w).trim();
        }
        if (line) out.push(line);
        return out.slice(0, max);
      }
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow"), badId = api.uid("arrowbad");
      for (const [id, c] of [[arrowId, "teal"], [badId, "bad"]]) {
        const mk = S("marker", { id, viewBox: "0 0 10 10", refX: 7, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse" }, defs);
        S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V(c) }, mk);
      }

      // ------------------------------------------------ top scene: prompt -> model -> reply
      const gPrompt = S("g", { class: "dimmable" }, svg);
      label(gPrompt, 30, 46, "CHAT TEMPLATE");
      card(gPrompt, 30, 56, 340, 240);
      mono(gPrompt, 48, 88, "system  " + D.system, { fill: V("muted") });
      const userLines = wrap(D.request, 27, 2);
      mono(gPrompt, 48, 114, "user    " + userLines[0], { fill: V("teal") });
      if (userLines[1]) mono(gPrompt, 48, 132, userLines[1], { fill: V("teal") });
      label(gPrompt, 48, 158, "SUFFIX", { "letter-spacing": "1" });
      const CELLS = [], CX0 = 48, CYR = [168, 186], CW = 27, CH = 13, PITCH = 30;
      for (let i = 0; i < D.n_suffix; i++) {
        const x = CX0 + (i % 10) * PITCH, y = CYR[Math.floor(i / 10)];
        const ghost = S("rect", { x: x + 2.5, y: y - 2, width: CW, height: CH, rx: 3, fill: V("bad"), opacity: 0 }, gPrompt);
        const r = S("rect", { x, y, width: CW, height: CH, rx: 3, fill: "none", stroke: V("line"), "stroke-width": 1.2, "stroke-dasharray": "3 3" }, gPrompt);
        CELLS.push({ i, x, y, ghost, r });
      }
      const strike = S("path", { d: "M44 166 L352 202", fill: "none", stroke: V("muted"), "stroke-width": 2.5, "stroke-linecap": "round", opacity: 0 }, gPrompt);
      const sufNote = mono(gPrompt, 48, 226, "", { fill: V("muted") });
      mono(gPrompt, 48, 258, "<|im_start|>assistant", { fill: V("violet") });
      T(gPrompt, 48, 280, "generation starts here · greedy", 13, { fill: V("muted") });

      const gModel = S("g", { class: "dimmable" }, svg);
      label(gModel, 410, 46, "MODEL");
      card(gModel, 410, 56, 190, 240, V("violet"));
      T(gModel, 505, 76, "decoder stack", 13, { "text-anchor": "middle", fill: V("muted") });
      for (let i = 0; i < 8; i++) S("rect", { x: 428, y: 84 + i * 16, width: 154, height: 11, rx: 4, fill: V("violet"), "fill-opacity": .07 + i * .035, stroke: V("violet"), "stroke-width": .8 }, gModel);
      const gModelA = S("g", {}, gModel);
      T(gModelA, 505, 234, D.pinned.provenance.victim, 16, { "text-anchor": "middle", class: "mono", "font-weight": 700, fill: V("violet") });
      T(gModelA, 505, 256, `${D.fetch.layers} layers · ${(D.fetch.params / 1e6).toFixed(1)}M params`, 13, { "text-anchor": "middle", fill: V("muted") });
      T(gModelA, 505, 280, "white-box access · A03", 13, { "text-anchor": "middle", fill: V("bad"), "font-weight": 600 });
      const gModelB = S("g", {}, gModel);
      T(gModelB, 505, 234, D.transfer.rows[1].model, 16, { "text-anchor": "middle", class: "mono", "font-weight": 700, fill: V("violet") });
      T(gModelB, 505, 256, D.transfer.rows[1].note, 13, { "text-anchor": "middle", fill: V("muted") });
      T(gModelB, 505, 280, "gradients never touched it", 13, { "text-anchor": "middle", fill: V("muted") });

      const gReply = S("g", { class: "dimmable" }, svg);
      label(gReply, 640, 46, "REPLY");
      T(gReply, 922, 46, "GREEDY", 13, { "text-anchor": "end", fill: V("muted"), "font-weight": 700, "letter-spacing": "2" });
      const replyCard = card(gReply, 640, 56, 290, 240);
      const replyLines = [0, 1, 2, 3, 4, 5].map(i => mono(gReply, 656, 96 + i * 26, "", { "font-weight": 600 }));
      const replyNote = T(gReply, 656, 278, "", 13, { fill: V("muted") });

      const gFlow = S("g", { class: "dimmable" }, svg);
      const flowA = S("path", { d: "M374 176 H402", fill: "none", stroke: V("teal"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, gFlow);
      S("path", { d: "M602 176 H630", fill: "none", stroke: V("teal"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, gFlow);
      const pkt = S("circle", { r: 6, cy: 176, fill: V("teal"), opacity: 0 }, svg);
      const grad = S("path", { d: "M505 300 C505 312, 494 314, 478 314 H150 C134 314, 128 308, 128 300 L128 206",
        fill: "none", stroke: V("bad"), "stroke-width": 4.5, "stroke-linecap": "round", pathLength: 100,
        "stroke-dasharray": "100 100", "stroke-dashoffset": 100, "marker-end": `url(#${badId})` }, svg);
      const gWall = S("g", { opacity: 0 }, svg);
      S("rect", { x: 380, y: 122, width: 22, height: 108, rx: 8, fill: V("ok"), "fill-opacity": .14, stroke: V("ok"), "stroke-width": 2.5 }, gWall);
      for (let i = 0; i < 3; i++) S("line", { x1: 385, y1: 142 + i * 30, x2: 397, y2: 154 + i * 30, stroke: V("ok"), "stroke-width": 2.5, "stroke-linecap": "round" }, gWall);
      const wallLbl = T(gWall, 391, 112, "", 13, { "text-anchor": "middle", fill: V("ok"), "font-weight": 800 });

      // ------------------------------------------------ detail panels (one per step)
      const panel = () => S("g", { opacity: 0 }, svg);
      const PY = 322, gmaxN = Math.max(...D.gradient.grad_norms);
      const JR1 = CELLS.map(c => X.rng(210 + c.i)() - .5), JR2 = CELLS.map(c => X.rng(310 + c.i)() - .5);
      const RS = CELLS.map(c => X.rng(410 + c.i)());

      // P1: the victim fixture and what the model reads
      const gP1 = panel();
      card(gP1, 40, PY, 520, 194);
      label(gP1, 60, PY + 24, "THE VICTIM FIXTURE");
      [["victim", `${D.pinned.provenance.victim} · plain base, no adapter`, "violet"],
       ["params", `${(D.fetch.params / 1e6).toFixed(1)}M · fp32 · CPU only`, "ink"],
       ["layers", `${D.fetch.layers} decoder layers`, "ink"],
       ["vocab", `${N(D.fetch.vocab)} tokens`, "ink"],
       ["decode", "greedy · top token every time", "ink"],
       ["access", "white-box: weights + gradients (A03)", "bad"]]
        .forEach(([k, v, c], i) => {
          mono(gP1, 60, PY + 56 + i * 23, k.padEnd(8, " ") + v, { fill: V(c) });
        });
      card(gP1, 580, PY, 340, 194);
      label(gP1, 600, PY + 24, "WHAT THE MODEL READS");
      [["system", "teal", D.system, "muted"], ["user", "teal", clip(D.request, 27), "teal"],
       ["suffix", "bad", "the hole after your request", "bad"], ["assistant", "violet", "<|im_start|>assistant", "violet"]]
        .forEach(([k, role, v, tc], i) => {
          const y = PY + 52 + i * 33;
          S("rect", { x: 600, y: y - 12, width: 62, height: 19, rx: 5, fill: V(role), "fill-opacity": .13, stroke: V(role), "stroke-width": 1.3, "stroke-dasharray": role === "bad" ? "4 3" : "none" }, gP1);
          T(gP1, 631, y + 2, k, 13, { "text-anchor": "middle", "font-weight": 700, fill: V(role) });
          mono(gP1, 672, y + 2, v, { fill: V(tc) });
        });

      // P2: the loss table
      const gP2 = panel();
      card(gP2, 40, PY, 580, 194);
      label(gP2, 60, PY + 24, "−LOG P PER TARGET TOKEN");
      const LOSSBARS = [];
      D.loss.rows.forEach((r, i) => {
        const col = i < 6 ? 0 : 1, x = 60 + col * 284, y = PY + 62 + (i - col * 6) * 22;
        mono(gP2, x, y, `${i + 1} ${qt(r.tok)}`, { "font-weight": r.ok ? 700 : 400, fill: V(r.ok ? "lime" : "ink") });
        S("rect", { x: x + 96, y: y - 9, width: 46, height: 9, rx: 3, fill: V("line"), opacity: .5 }, gP2);
        const bar = S("rect", { x: x + 96, y: y - 9, width: 0, height: 9, rx: 3, fill: V(r.ok ? "lime" : "warn"), opacity: .85 }, gP2);
        mono(gP2, x + 150, y, r.nll.toFixed(2), { fill: V("muted") });
        mono(gP2, x + 200, y, "→ " + qt(clip(r.top, 7)), { fill: V("muted") });
        LOSSBARS.push({ bar, v: r.nll / 16.2 });
      });
      mono(gP2, 60, PY + 44, "n  token   −log p  model top", { fill: V("muted") });
      mono(gP2, 344, PY + 44, "n  token   −log p  model top", { fill: V("muted") });
      card(gP2, 640, PY, 280, 194);
      label(gP2, 660, PY + 24, "THE LOSS");
      T(gP2, 660, PY + 62, "loss = mean −log p(target", 15, { class: "mono", "font-weight": 600 });
      T(gP2, 660, PY + 84, "        | prompt + suffix)", 15, { class: "mono", "font-weight": 600 });
      T(gP2, 660, PY + 130, D.loss.loss.toFixed(3), 38, { "font-weight": 800, fill: V("bad"), class: "mono" });
      mono(gP2, 660, PY + 156, `p(all together) ≈ ${P_WHOLE}`, { fill: V("muted") });
      mono(gP2, 660, PY + 180, `${OK_N} of ${D.loss.rows.length} tokens already match`, { fill: V("lime") });

      // P3: one-hot gradient norms + top swaps
      const gP3 = panel();
      card(gP3, 40, PY, 440, 194);
      label(gP3, 60, PY + 24, "GRADIENT NORM PER POSITION");
      const NORMBARS = [], NBASE = 492;
      D.gradient.grad_norms.forEach((v, i) => {
        const x = 64 + i * 19.5, h = 116 * v / gmaxN;
        const r = S("rect", { x, y: NBASE, width: 13, height: 0, rx: 2, fill: V("bad"), "fill-opacity": i === D.gradient.best_pos ? 1 : .3 + .5 * v / gmaxN, stroke: i === D.gradient.best_pos ? V("warn") : "none", "stroke-width": 1.5 }, gP3);
        NORMBARS.push({ r, h });
        if ([0, 5, 10, 15, 19].includes(i)) mono(gP3, x + 6.5, 508, String(i), { "text-anchor": "middle", fill: V("muted") });
      });
      S("path", { d: `M58 ${NBASE} H448`, stroke: V("line"), "stroke-width": 1.5 }, gP3);
      card(gP3, 500, PY, 420, 194);
      label(gP3, 520, PY + 24, "TOP SINGLE-TOKEN SWAPS · PREDICTED");
      const SWAPROWS = D.gradient.rows.map((r, i) => {
        const y = PY + 54 + i * 24, g = S("g", {}, gP3);
        mono(g, 520, y, `pos ${String(r.pos).padStart(2, " ")}`, { "font-weight": 700 });
        mono(g, 586, y, `${qt(r.current)} → ${qt(r.swap)}`, { fill: V("bad") });
        mono(g, 900, y, r.dloss.toFixed(3), { "text-anchor": "end", fill: V("muted") });
        return g;
      });
      mono(gP3, 520, PY + 176, `${N(D.gradient.n_banned)} of ${N(D.gradient.shape[1])} tokens banned before sampling`, { fill: V("muted") });

      // P4: one hand step + the race
      const gP4 = panel();
      card(gP4, 40, PY, 300, 194);
      label(gP4, 60, PY + 24, "ONE GCG STEP");
      [["sampled", `${D.step.onestep.n} of top ${D.step.topk}`],
       ["beat", `${D.step.onestep.beat}/${D.step.onestep.n} candidates`],
       ["best", `${D.step.loss.toFixed(3)} → ${D.step.onestep.best.toFixed(3)}`],
       ["swap", clip(D.step.onestep.swap, 20)],
       ["re-check", D.step.onestep.remeasured.toFixed(3)]]
        .forEach(([k, v], i) => mono(gP4, 60, PY + 56 + i * 23, k.padEnd(9, " ") + v, {}));
      T(gP4, 60, PY + 168, "the fresh forward pass", 13, { fill: V("muted") });
      T(gP4, 60, PY + 184, "decides the winner", 13, { fill: V("muted") });
      card(gP4, 360, PY, 560, 194);
      label(gP4, 380, PY + 24, "RACE · EQUAL FORWARD BUDGET");
      mono(gP4, 900, PY + 24, `${D.step.race.budget} evaluations each`, { "text-anchor": "end", fill: V("muted") });
      const R4X = r => L(430, 870, r / 8), R4Y = v => L(486, 356, (v - 5) / 1.6);
      S("path", { d: "M430 352 V486 H870", fill: "none", stroke: V("line"), "stroke-width": 1.5 }, gP4);
      [6.5, 6, 5.5].forEach(v => mono(gP4, 424, R4Y(v) + 4, v.toFixed(1), { "text-anchor": "end", fill: V("muted") }));
      [0, 2, 4, 6, 8].forEach(r => mono(gP4, R4X(r), 504, String(r), { "text-anchor": "middle", fill: V("muted") }));
      const racePts = key => D.step.race.hist.map(h => [R4X(h.round), R4Y(h[key])]);
      const gPts = racePts("gradient"), rPts = racePts("random");
      const gLine4 = S("polyline", { fill: "none", stroke: V("bad"), "stroke-width": 3, "stroke-linejoin": "round" }, gP4);
      const rLine4 = S("polyline", { fill: "none", stroke: V("teal"), "stroke-width": 3, "stroke-linejoin": "round" }, gP4);
      const raceDots = D.step.race.hist.map(h => S("circle", { cx: R4X(h.round), cy: R4Y(h.gradient), r: 3.2, fill: V("bad") }, gP4));
      mono(gP4, 898, 366, `gradient ${D.step.race.gradient.toFixed(2)}`, { "text-anchor": "end", "font-weight": 700, fill: V("bad") });
      mono(gP4, 898, 386, `random ${D.step.race.random.toFixed(2)}`, { "text-anchor": "end", "font-weight": 700, fill: V("teal") });

      // P5: the student run and the long run behind the asset
      const gP5 = panel();
      card(gP5, 40, PY, 520, 194);
      label(gP5, 60, PY + 24, "STUDENT RUN · LIVE SEARCH");
      const S5 = [[0, D.loss.loss]].concat(D.search.losses.map((l, i) => [i + 1, l]));
      const S5X = s => L(90, 490, s / 8), S5Y = v => L(486, 352, (v - 5) / 1.6);
      S("path", { d: "M90 352 V486 H490", fill: "none", stroke: V("line"), "stroke-width": 1.5 }, gP5);
      [6.5, 6, 5.5].forEach(v => mono(gP5, 84, S5Y(v) + 4, v.toFixed(1), { "text-anchor": "end", fill: V("muted") }));
      mono(gP5, 98, S5Y(S5[0][1]) + 20, D.loss.loss.toFixed(2), { fill: V("muted") });
      mono(gP5, 478, S5Y(D.search.best_loss) - 12, D.search.best_loss.toFixed(2), { "text-anchor": "end", "font-weight": 700, fill: V("bad") });
      const sPts = S5.map(([s, l]) => [S5X(s), S5Y(l)]);
      const sLine = S("polyline", { fill: "none", stroke: V("bad"), "stroke-width": 3, "stroke-linejoin": "round" }, gP5);
      const sDots = S5.map(([s, l]) => S("circle", { cx: S5X(s), cy: S5Y(l), r: 3.2, fill: V("bad") }, gP5));
      mono(gP5, 60, PY + 172, `${D.search.s_per_step.toFixed(1)} s/step · canary found: ${D.search.found ? "yes" : "no"}`, { fill: V("muted") });
      mono(gP5, 60, PY + 188, `best suffix: “${clip(D.search.best_string, 42)}…”`, { fill: V("muted") });
      card(gP5, 580, PY, 340, 194);
      label(gP5, 600, PY + 24, "THE LONG RUN BEHIND THE ASSET");
      const CV = D.long.curve, cvMin = Math.min(...CV.map(c => c[1])), cvMax = Math.max(...CV.map(c => c[1]));
      const CVX = i => L(600, 900, i / (CV.length - 1)), CVY = v => L(404, 358, (v - cvMin) / (cvMax - cvMin));
      S("polyline", { points: CV.map((c, i) => `${CVX(i).toFixed(1)},${CVY(c[1]).toFixed(1)}`).join(" "), fill: "none", stroke: V("violet"), "stroke-width": 2.5, "stroke-linejoin": "round" }, gP5);
      S("circle", { cx: CVX(CV.length - 1), cy: CVY(cvMin), r: 4.5, fill: V("lime") }, gP5);
      [["steps", `${D.long.steps_run} of ${D.pinned.provenance.config.steps} ran`],
       ["time", `${(D.long.seconds / 60).toFixed(0)} min · ${D.long.s_per_step.toFixed(1)} s/step`],
       ["loss", `best ${D.long.best_loss.toFixed(3)}`],
       ["canary", D.pinned.canary ? "yes, greedy text-path hit" : "no"]]
        .forEach(([k, v], i) => mono(gP5, 600, PY + 56 + i * 23, k.padEnd(8, " ") + v, {}));

      // P6: the pinned suffix, token by token, and the canary it forces
      const gP6 = panel();
      label(gP6, 40, PY + 16, "THE PINNED SUFFIX, TOKEN BY TOKEN");
      const CHIPGROUPS = D.pinned.tokens.map((t, i) => {
        const g = S("g", {}, gP6);
        const x = 44 + (i % 5) * 172, y = 348 + Math.floor(i / 5) * 27;
        S("rect", { x, y, width: 166, height: 23, rx: 6, fill: V("bad"), "fill-opacity": .12, stroke: V("bad"), "stroke-width": 1.3 }, g);
        mono(g, x + 10, y + 16, qt(clip(t, 13)), { fill: V("bad") });
        T(g, x + 157, y + 16, String(D.pinned.token_ids[i]), 13, { "text-anchor": "end", fill: V("muted") });
        return g;
      });
      card(gP6, 40, 462, 560, 54, V("lime"));
      const canaryTxt = T(gP6, 60, 490, "", 19, { class: "mono", "font-weight": 800, fill: V("lime") });
      T(gP6, 60, 508, `echoed · ${D.pinned.replies.length} decodes, identical every time`, 13, { fill: V("muted") });
      card(gP6, 620, 462, 300, 54);
      T(gP6, 640, 488, `${D.loss.loss.toFixed(3)} → ${D.pinned.loss.toFixed(3)}`, 19, { class: "mono", "font-weight": 800, fill: V("bad") });
      T(gP6, 640, 508, `greedy · deterministic: ${D.pinned.deterministic}`, 13, { fill: V("muted") });

      // P7: transfer table
      const gP7 = panel();
      label(gP7, 60, PY + 24, "ONE FROZEN SUFFIX · THREE MODELS");
      const XFERROWS = D.transfer.rows.map((r, i) => {
        const y = 342 + i * 50, g = S("g", {}, gP7);
        card(g, 60, y, 840, 42, V(r.canary ? "lime" : "line"));
        mono(g, 76, y + 17, r.model, { "font-weight": 700, fill: V(r.canary ? "lime" : "violet") });
        mono(g, 76, y + 33, clip(r.note, 24), { fill: V("muted") });
        mono(g, 420, y + 26, clip(r.suffix.replace(/\n/g, " "), 44), { fill: V(r.canary ? "lime" : "warn") });
        mono(g, 884, y + 26, r.canary ? "canary ✓" : "no canary", { "text-anchor": "end", "font-weight": 700, fill: V(r.canary ? "lime" : "muted") });
        return g;
      });
      T(gP7, 60, 510, `transfer ${D.transfer.n_transfer}/${D.transfer.n_heldout} held-out models · receiving a precomputed suffix is weaker access than optimizing one with gradients`, 13, { "font-weight": 600 });

      // P8: perplexity, log scale
      const gP8 = panel();
      card(gP8, 40, PY, 560, 194);
      label(gP8, 60, PY + 24, "PERPLEXITY · LOG SCALE");
      const PX8 = p => 84 + (Math.log10(p) - 0.3) / 4.2 * 460;
      S("path", { d: "M78 486 H556", stroke: V("line"), "stroke-width": 1.5 }, gP8);
      [[10, "10"], [100, "100"], [1000, "1k"], [10000, "10k"]].forEach(([v, s]) =>
        mono(gP8, PX8(v), 504, s, { "text-anchor": "middle", fill: V("muted") }));
      S("rect", { x: PX8(D.d1.calibration.min), y: 372, width: PX8(D.d1.calibration.max) - PX8(D.d1.calibration.min), height: 26, rx: 4, fill: V("teal"), "fill-opacity": .18, stroke: V("teal"), "stroke-width": 1.2 }, gP8);
      S("path", { d: `M${PX8(D.d1.calibration.med)} 372 V398`, stroke: V("teal"), "stroke-width": 2.5 }, gP8);
      S("rect", { x: PX8(D.d1.unusual.min), y: 414, width: PX8(D.d1.unusual.max) - PX8(D.d1.unusual.min), height: 26, rx: 4, fill: V("teal"), "fill-opacity": .08, stroke: V("teal"), "stroke-width": 1.2, "stroke-dasharray": "5 4" }, gP8);
      mono(gP8, PX8(D.d1.calibration.min), 366, `ordinary (${D.d1.calibration.n}) · max ${D.d1.calibration.max}`, { fill: V("teal") });
      mono(gP8, PX8(D.d1.unusual.min), 458, `technical, benign (${D.d1.unusual.n})`, { fill: V("teal") });
      S("path", { d: `M${PX8(D.d1.threshold)} 358 V486`, stroke: V("ok"), "stroke-width": 2, "stroke-dasharray": "6 4" }, gP8);
      mono(gP8, PX8(D.d1.threshold), 350, `threshold ${D.d1.threshold.toFixed(0)}`, { "text-anchor": "middle", "font-weight": 700, fill: V("ok") });
      const pplDot = S("circle", { cx: PX8(D.d1.suffix_ppl), cy: 486, r: 8, fill: V("bad") }, gP8);
      mono(gP8, PX8(D.d1.suffix_ppl), 462, N(D.d1.suffix_ppl), { "text-anchor": "middle", "font-weight": 700, fill: V("bad") });
      S("path", { d: `M${PX8(D.d1.threshold) + 5} 470 H${PX8(D.d1.suffix_ppl) - 7}`, stroke: V("bad"), "stroke-width": 1.5, "stroke-dasharray": "2 3" }, gP8);
      mono(gP8, (PX8(D.d1.threshold) + PX8(D.d1.suffix_ppl)) / 2, 476, `${(D.d1.suffix_ppl / D.d1.threshold).toFixed(0)}× over`, { "text-anchor": "middle", fill: V("bad") });
      card(gP8, 620, PY, 300, 194);
      label(gP8, 640, PY + 24, "CATCH · FALSE POSITIVES");
      [["pinned suffix", "flagged", "bad"],
       ["student suffixes", `${D.d1.caught}/${D.d1.n_suffixes} caught`, "ink"],
       ["technical benign", `${D.d1.fp_unusual}/${D.d1.unusual.n} flagged`, "ink"],
       ["ordinary", `max ${D.d1.calibration.max}, clear`, "ok"]]
        .forEach(([k, v, c], i) => mono(gP8, 640, PY + 56 + i * 24, k.padEnd(18, " ") + v, { fill: V(c) }));

      // P9: retokenization / paraphrase table
      const gP9 = panel();
      label(gP9, 60, PY + 24, "SAME SUFFIX, REWRITTEN FOUR WAYS");
      const RETKROWS = D.d2.rows.map((r, i) => {
        const y = 340 + i * 40, g = S("g", {}, gP9);
        card(g, 60, y, 840, 36, V(r.canary ? "lime" : "line"));
        T(g, 76, y + 23, r.variant, 14, { "font-weight": 700 });
        mono(g, 306, y + 23, `${r.ids} ids`, { fill: V("muted") });
        S("rect", { x: 376, y: y + 12, width: 150, height: 12, rx: 4, fill: V("line"), opacity: .5 }, g);
        const fg = S("rect", { x: 376, y: y + 12, width: 0, height: 12, rx: 4, fill: V("bad") }, g);
        mono(g, 534, y + 23, `${r.changed} changed`, { fill: V("muted") });
        mono(g, 648, y + 23, clip(line1(r.reply), 22), { fill: V(r.canary ? "lime" : "warn") });
        mono(g, 884, y + 23, r.canary ? "canary ✓" : "canary ✗", { "text-anchor": "end", "font-weight": 700, fill: V(r.canary ? "lime" : "muted") });
        return { g, fg, w: 150 * r.changed / r.ids };
      });
      T(gP9, 60, 510, `canary survives ${D.d2.n_canary} of ${D.d2.rows.length} variants · any real rewrite breaks it`, 13, { "font-weight": 600 });

      // P10: perturbed copies + majority vote, and the utility cost
      const gP10 = panel();
      card(gP10, 40, PY, 560, 194);
      label(gP10, 60, PY + 24, "PERTURBED COPIES · MAJORITY VOTE");
      const COPYROWS = D.d3.copies.map((c, i) => {
        const y = 372 + i * 25, g = S("g", {}, gP10);
        mono(g, 60, y, `copy ${i + 1}`, { fill: V("muted") });
        mono(g, 122, y, clip(c.replace(/\n/g, " "), 50), { fill: V("warn") });
        return g;
      });
      T(gP10, 60, 508, `canary copies ${D.d3.votes} of ${D.d3.copies.length} → majority: no canary`, 14, { "font-weight": 700, fill: V("ok") });
      card(gP10, 620, PY, 300, 194);
      label(gP10, 640, PY + 24, "UTILITY · HELD-OUT QUESTIONS");
      T(gP10, 640, 384, "clean", 14, { "font-weight": 700 });
      S("rect", { x: 640, y: 392, width: 220, height: 13, rx: 4, fill: V("line"), opacity: .5 }, gP10);
      const utilClean = S("rect", { x: 640, y: 392, width: 0, height: 13, rx: 4, fill: V("teal") }, gP10);
      mono(gP10, 900, 402, `${D.d3.clean_acc}/${D.d3.n}`, { "text-anchor": "end", fill: V("muted") });
      T(gP10, 640, 434, "with perturbation", 14, { "font-weight": 700 });
      S("rect", { x: 640, y: 442, width: 220, height: 13, rx: 4, fill: V("line"), opacity: .5 }, gP10);
      const utilBad = S("rect", { x: 640, y: 442, width: 0, height: 13, rx: 4, fill: V("bad") }, gP10);
      mono(gP10, 900, 452, `${D.d3.majority_acc}/${D.d3.n}`, { "text-anchor": "end", "font-weight": 700, fill: V("bad") });
      T(gP10, 640, 484, "the same noise taxes honest questions", 13, { fill: V("muted") });
      T(gP10, 640, 502, "adaptive test still owed (eval-adaptive)", 13, { fill: V("muted") });

      const P = [gP1, gP2, gP3, gP4, gP5, gP6, gP7, gP8, gP9, gP10];
      const INIT_TOK = " " + D.init.trim().split(/\s+/)[0];
      const CELL_MODE = [0, 1, 2, 3, 4, 5, 5, 5, 6, 7];
      const NOTES = [
        "empty hole after your request",
        `${qt(INIT_TOK)} × ${D.n_suffix} · the starting suffix`,
        "fill = gradient strength at that position",
        `pos ${D.gradient.best_pos}: ${qt(BEST.current)} → ${qt(BEST.swap)}`,
        "the search keeps the best suffix so far",
        `“${clip(D.pinned.suffix, 30)}…”`,
        "the rewrite shifts the ids",
        `perturbed into ${D.d3.q} noisy copies`];
      const polyF = (el, pts, f) => {
        const m = Math.max(1, Math.round(f * (pts.length - 1)) + 1);
        A(el, { points: pts.slice(0, m).map(p => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ") });
      };
      const st = { p: 1, k: 1 };
      const target = n => ({ p: n, k: 1 });

      function draw(s) {
        const n = s.p, k = s.k, act = Math.min(1, k * 1.4).toFixed(3);
        P.forEach((g, i) => { const on = i + 1 === n; A(g, { opacity: on ? act : "0" }); g.style.display = on ? "" : "none"; });

        // suffix cells: empty -> init -> heat -> swap -> search -> pinned -> retok -> jitter
        const mode = CELL_MODE[n - 1], r = seg(k, .05, .55);
        CELLS.forEach(c => {
          const gn = D.gradient.grad_norms[c.i] / gmaxN;
          let fill = "none", fo = 0, so = .85, dash = "3 3", jx = 0, jy = 0, go = 0;
          if (mode === 1) { fill = V("bad"); fo = .14 * r; so = .5 * r; dash = "none"; }
          if (mode === 2) { fill = V("bad"); fo = (.1 + .75 * gn) * r; so = .35 * r; dash = "none"; }
          if (mode === 3) { const top = c.i === D.gradient.best_pos; fill = V("bad"); fo = (top ? .8 : .12) * r; so = top ? r : .4 * r; dash = "none"; }
          if (mode === 4) { fill = V("bad"); fo = (.2 + .35 * RS[c.i]) * r; so = .45 * r; dash = "none"; }
          if (mode === 5) { fill = V("bad"); fo = .78 * r; so = r; dash = "none"; }
          if (mode === 6) { fill = V("dim"); fo = .6; so = .9; dash = "none"; }
          if (mode === 7) { jx = JR1[c.i] * 2.4; jy = JR2[c.i] * 1.8; go = .3 * r; fill = V("bad"); fo = .5 * r; so = .7 * r; dash = "none"; }
          A(c.r, { x: (c.x + jx).toFixed(1), y: (c.y + jy).toFixed(1), fill, "fill-opacity": fo.toFixed(3), stroke: mode === 0 ? V("line") : fill === "none" ? V("line") : V(mode === 6 ? "muted" : "bad"),
            "stroke-opacity": Math.min(1, so).toFixed(3), "stroke-dasharray": dash });
          A(c.ghost, { opacity: go.toFixed(3) });
        });
        A(strike, { opacity: mode === 6 ? seg(k, .3, .7).toFixed(3) : 0 });
        sufNote.textContent = NOTES[mode];

        // reply card
        const RL = n === 1 ? { t: D.fetch.reply, c: "warn", ty: seg(k, .1, .8) }
          : n <= 5 ? { t: D.fetch.reply, c: "warn", ty: 1 }
          : n === 6 ? { t: D.pinned.replies[0].split("\n").filter(Boolean).slice(0, 2).join("  "), c: "lime", ty: seg(k, .2, .75) }
          : n === 7 ? { t: D.transfer.rows[1].suffix, c: "warn", ty: seg(k, .15, .7) }
          : n === 8 ? { t: `prompt flagged · ppl ${N(D.d1.suffix_ppl)} > ${D.d1.threshold.toFixed(0)}`, c: "muted", ty: seg(k, .15, .6) }
          : n === 9 ? { t: D.d2.rows[2].reply, c: "warn", ty: seg(k, .15, .7) }
          : { t: D.d3.copies[0], c: "warn", ty: seg(k, .15, .7) };
        const lines = wrap(clip(RL.t.replace(/\n/g, " "), 180), 33);
        lines.forEach((ln, i) => {
          const f = X.clamp(lines.length * RL.ty - i, 0, 1);
          replyLines[i].textContent = ln.slice(0, Math.round(ln.length * f));
          A(replyLines[i], { fill: V(RL.c) });
        });
        for (let i = lines.length; i < 6; i++) replyLines[i].textContent = "";
        replyNote.textContent = n === 1 ? "clean prompt · greedy decoding"
          : n <= 5 ? "prompt + starting suffix"
          : n === 6 ? `prompt + pinned suffix · ${D.pinned.replies.length}/${D.pinned.replies.length} identical decodes`
          : n === 7 ? "prompt + pinned suffix · sibling model"
          : n === 8 ? "blocked before the model"
          : n === 9 ? `rewritten: ${D.d2.rows[2].variant}`
          : `majority of ${D.d3.q} copies`;
        A(replyCard, { stroke: V(n === 6 ? "lime" : n === 8 ? "ok" : "line") });

        // model card, gradient ribbon, defense wall, packet
        A(gModelA, { opacity: n === 7 ? 0 : 1 });
        A(gModelB, { opacity: n === 7 ? 1 : 0 });
        const gv = n >= 3 && n <= 5 ? seg(k, 0, .55) : 0;
        A(grad, { "stroke-dashoffset": (100 * (1 - gv)).toFixed(2), opacity: gv > 0 ? 1 : 0 });
        const wv = n >= 8 ? seg(k, 0, .4) : 0;
        A(gWall, { opacity: wv.toFixed(3) });
        wallLbl.textContent = n === 8 ? "FILTER" : n === 9 ? "REWRITE" : `VOTE × ${D.d3.q}`;
        A(flowA, { opacity: (1 - wv).toFixed(3) });
        const pv = seg(k, .05, .2) * (1 - seg(k, .5, .65));
        A(pkt, { cx: L(378, 598, seg(k, .05, .55)).toFixed(1), opacity: pv > 0 ? pv.toFixed(3) : 0 });

        // panel internals
        LOSSBARS.forEach((b, i) => A(b.bar, { width: (56 * b.v * E.out(seg(k, .1 + i * .03, .5 + i * .03))).toFixed(1) }));
        NORMBARS.forEach((b, i) => { const h = b.h * seg(k, .05 + i * .012, .45 + i * .012); A(b.r, { y: (NBASE - Math.max(0, h)).toFixed(1), height: Math.max(0, h).toFixed(1) }); });
        SWAPROWS.forEach((g, i) => A(g, { opacity: seg(k, .25 + i * .07, .45 + i * .07).toFixed(3) }));
        const f4 = seg(k, .15, .8);
        polyF(gLine4, gPts, f4); polyF(rLine4, rPts, f4);
        raceDots.forEach((d, i) => A(d, { opacity: seg(k, .15 + i * .06, .3 + i * .06).toFixed(3) }));
        polyF(sLine, sPts, f4);
        sDots.forEach((d, i) => A(d, { opacity: seg(k, .15 + i * .02, .3 + i * .02).toFixed(3) }));
        CHIPGROUPS.forEach((g, i) => A(g, { opacity: seg(k, .05 + i * .025, .3 + i * .025).toFixed(3) }));
        const can = D.pinned.replies[0].split("\n")[0];
        canaryTxt.textContent = can.slice(0, Math.round(can.length * seg(k, .35, .8)));
        XFERROWS.forEach((g, i) => A(g, { opacity: seg(k, .1 + i * .1, .35 + i * .1).toFixed(3) }));
        A(pplDot, { r: (5 + 4 * E.out(seg(k, .35, .6))).toFixed(1) });
        RETKROWS.forEach((rw, i) => { A(rw.g, { opacity: seg(k, .1 + i * .08, .3 + i * .08).toFixed(3) }); A(rw.fg, { width: (rw.w * seg(k, .3 + i * .08, .7 + i * .08)).toFixed(1) }); });
        COPYROWS.forEach((g, i) => A(g, { opacity: seg(k, .1 + i * .06, .3 + i * .06).toFixed(3) }));
        A(utilClean, { width: (220 * D.d3.clean_acc / D.d3.n * E.out(seg(k, .2, .7))).toFixed(1) });
        A(utilBad, { width: (220 * D.d3.majority_acc / D.d3.n * E.out(seg(k, .4, .9))).toFixed(1) });

        // focus + context
        const hot = n === 1 ? [gModel, gReply] : n <= 5 ? [gPrompt, gModel] : n <= 7 ? [gPrompt, gReply] : [gPrompt];
        [gPrompt, gModel, gReply, gFlow].forEach(g => g.classList.toggle("hot", hot.includes(g)));
        el.classList.toggle("lx-focus", true);
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          st.p = n; st.k = 0; draw(st);
          return api.tween(750, k => { if (g !== gen) return; st.k = k; draw(st); }, E.inOut);
        },
      };
    },
  });
})();
