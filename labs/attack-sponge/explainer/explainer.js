/* LAB-43 attack-sponge: "Inputs that cost more than they look" (10 steps).
 * Chapters: System (the victim, text into tokens) · Attack (tokenizer amplification, the
 * EOS-suppression objective) · Mechanism (the search) · Impact (the pinned sponge and its bill,
 * weak transfer) · Defense (token budgets, hard caps, telemetry). One persistent scene across the
 * top: the chat template (system, request, 8 suffix cells, assistant turn) -> the victim model ->
 * the greedy reply, with the stop-token gate under the reply and a cost meter beside it. A detail
 * panel below changes per step. Every number and every run string (replies, suffix, counts) comes
 * from window.LAB_DATA (data.js, exported from the reference workbench run).
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp, E = X.ease;
  const D = window.LAB_DATA;
  const CLS = ["plain", "rare", "zalgo", "emoji", "mixed"];
  const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const clip = (s, n) => (String(s).length > n ? String(s).slice(0, n - 1) + "…" : String(s));
  const line1 = s => String(s).split("\n")[0];
  const N = n => n.toLocaleString("en");
  const nM = v => (v >= 1000 ? N(Math.round(v)) : v.toFixed(1));

  X.define({
    id: "attack-sponge",
    family: "family-availability",
    title: 'Inputs that cost more than they <span class="outline">look</span>',
    legend: [{ role: "teal", label: "Request text" }, { role: "bad", label: "Attacker suffix / cost" },
      { role: "violet", label: "Model / tokens" }, { role: "warn", label: "Reply" }, { role: "lime", label: "Canary" },
      { role: "ok", label: "Defense" }],
    intro: {
      "why": "A request that looks small can cost a lot to process. This lab asks how that happens to a language model, and what it costs you. Two levers are measured: text that a tokenizer cuts into far more tokens than its size suggests, and a short optimized suffix that stops the model from ever ending its reply. Both raise compute, latency and the bill, and neither breaks anything you can see in the answer.",
      "plan": "You’ll meet a tiny open model and watch it end a normal reply with one stop token. You’ll measure how many tokens plain and unusual text becomes under three tokenizers, then time what the difference costs. Next, a gradient search learns a short suffix that keeps generation running to the hard cap, and you’ll price that request against a normal one. Three gateway defenses close the lab: token budgets, hard caps and cost telemetry.",
      "terms": "A token is the piece of text a model actually reads; the tokenizer cuts your input into tokens. Prefill is the work of processing the prompt before the first new token. The stop token (EOS) is the special token that ends a reply. A suffix is a short token string an attacker appends to a request. A margin says by how many logits the best ordinary token beats the stop token; greedy decoding stops only where the stop token wins. CPU seconds approximate the energy a request burns."
    },
    steps: [
      { chapter: "System", label: "The tiny victim",
        guide: "Meet the model under test. It is a small open assistant with no safety layer in play, so nothing here is a bypass. It answers a support question briefly, echoes the badge it was given, and ends its reply with one stop token. That stop token is the whole subject of the second half of the lab.",
        caption: `The victim is <span class="c-violet">SmolLM2-135M-Instruct</span>: ${(D.fetch.params / 1e6).toFixed(1)}M parameters, ${D.fetch.layers} layers, fp32 on your CPU, greedy decoding. The request carries the fixed badge <code class="c-lime">${D.canary}</code>. The clean reply is <b>${D.fetch.reply_tokens} tokens</b> and ends with the stop token <code class="c-warn">${esc(D.fetch.eos)}</code>. A natural prompt that begs for endless output still runs to its ${D.fetch.natural_cap}-token cap here: this tiny model stops poorly, and the lab keeps that fact in view.`,
        cmd: "docker compose run --rm workbench python attack-sponge/scripts/s01_fetch.py" },
      { chapter: "System", label: "Text becomes tokens",
        guide: "See what three real tokenizers do with the same fixed stretch of characters. Plain English becomes a modest number of tokens. Rare scripts, stacked combining marks, emoji sequences and mixed scripts become many times more, because the tokenizer falls back to tiny pieces. Token counts are exact and repeat on every run.",
        caption: `Rows of ${D.amplify.rows.plain.chars}-${D.amplify.rows[D.amplify.worst].chars} characters: plain <b>${N(D.amplify.rows.plain.tokens.smollm2)}</b> tokens, rare script <b>${N(D.amplify.rows.rare.tokens.smollm2)}</b>, emoji ZWJ <b>${N(D.amplify.rows.emoji.tokens.smollm2)}</b>, combining marks <b>${N(D.amplify.rows.zalgo.tokens.smollm2)}</b>, mixed script <b>${N(D.amplify.rows.mixed.tokens.smollm2)}</b> on the victim’s tokenizer. Qwen2.5’s tokenizer is denser on every row (${N(D.amplify.rows[D.amplify.worst].tokens["qwen2.5"])} on the worst); GPT-2’s matches the victim’s on rare scripts (${N(D.amplify.rows.rare.tokens.gpt2)}).`,
        cmd: "docker compose run --rm workbench python attack-sponge/scripts/s02_amplify.py" },
      { chapter: "Attack", label: "Cheap characters",
        guide: "This is the black-box lever: anyone who can send text can use it, with no knowledge of the weights. Hold the character count fixed and the token count explodes, so prefill does more work per character. The wall-clock ratio between the worst row and plain text is the attack’s measured effect, and it needs only query access.",
        caption: `Same character budget, victim’s tokenizer: ${D.amplify.worst} costs <b>${N(D.amplify.rows[D.amplify.worst].tokens.smollm2)}</b> tokens against ${N(D.amplify.rows.plain.tokens.smollm2)} for plain (<b>${D.amplify.amp.smollm2[D.amplify.worst].toFixed(1)}×</b>). Prefill medians: plain ${nM(D.amplify.timing_ms.plain[2])} ms vs ${D.amplify.worst} ${nM(D.amplify.timing_ms[D.amplify.worst][2])} ms, ratio <b>${D.amplify.ratio.toFixed(1)}×</b> (Mann-Whitney p=${D.amplify.p < 0.001 ? D.amplify.p.toExponential(1) : D.amplify.p.toFixed(3)}, AUC ${D.amplify.auc.toFixed(2)}). Access: A01, output queries only.`,
        cmd: "docker compose run --rm workbench python attack-sponge/scripts/s02_amplify.py" },
      { chapter: "Attack", label: "Outrank the stop",
        guide: "The white-box lever targets how the model stops. Greedy decoding emits the stop token only where it outranks every ordinary token. Along the normal reply the stop token loses badly everywhere except the final position, where it wins by a couple of logits. The attack asks a search to flip that one race, and first checks how much mere filler it takes to break stopping by accident.",
        caption: `Margins along the ${D.loss.rows[0].margins.length}-token reply: positive (stop loses) at every position except the last, <b>${D.loss.rows[0].margins[D.loss.rows[0].margins.length - 1].toFixed(1)}</b> logits, p(stop)=${D.loss.rows[0].p_eos[D.loss.rows[0].p_eos.length - 1].toFixed(2)}. Filler sweep: ${D.loss.junk_sweep.filter(r => r.stopped).map(r => r.junk).join(", ")} filler tokens still stop; ${D.loss.junk_sweep.filter(r => !r.stopped).map(r => r.junk)[0]} already runs to the ${D.cap}-token cap. So the ${D.n_suffix}-token search budget starts where the model still stops, and the optimizer must do the work.`,
        cmd: "docker compose run --rm workbench python attack-sponge/scripts/s03_loss.py" },
      { chapter: "Mechanism", label: "The search",
        guide: "The search reuses the gradient loop from the attack-gcg lab, aimed at a different goal. One backward pass ranks every single-token swap in the suffix, a batch of candidates is run forward, and the best one survives. Between rounds the path is re-measured, because once the stop token loses, the model takes a new route. A short run moves the loss; the shipped suffix came from a much longer one.",
        caption: `Objective: keep the best ordinary token outranking the stop token along the reply (mean softplus of the negative margin). Student run: ${D.search.steps_run} steps, width ${D.search.config.width}, loss ${D.search.loss0.toFixed(4)} → <b>${D.search.best_loss.toFixed(4)}</b> at ${D.search.s_per_step.toFixed(1)} s/step; its suffix decodes to ${D.search.probe_out} tokens. The pinned asset came from the long run: ${D.long.rounds} rounds, ${D.long.steps_run} steps, ${(D.long.seconds / 60).toFixed(0)} min, best loss <b>${D.long.best_loss.toFixed(4)}</b>.`,
        cmd: "docker compose run --rm workbench python attack-sponge/scripts/s04_search.py --steps 8 --width 16 --topk 32" },
      { chapter: "Impact", label: "The sponge bill",
        guide: "Load the pinned suffix and price the request. The reply never ends: generation runs to the hard token cap every time, and the same prompt decodes the same way because decoding is greedy. The request costs several times the tokens, wall time and CPU seconds of a clean one. The reply still opens with the badge sentence, so nothing looks broken.",
        caption: `Clean request: ${D.pinned.clean.n_out} tokens, ${D.pinned.clean.wall_s.toFixed(1)} s wall, ${D.pinned.clean.cpu_s.toFixed(1)} CPU-s. With the pinned suffix: <b>${D.pinned.pinned.n_out}/${D.cap} tokens</b> (never stopped), ${D.pinned.pinned.wall_s.toFixed(1)} s, ${D.pinned.pinned.cpu_s.toFixed(1)} CPU-s → <b>${D.pinned.mult_tokens.toFixed(1)}×</b> tokens, <b>${D.pinned.mult_wall.toFixed(1)}×</b> wall, <b>${D.pinned.mult_cpu.toFixed(1)}×</b> CPU. The request carries the fixed canary <code class="c-lime">${D.canary}</code>; the reply opens <span class="c-warn">“${esc(clip(D.pinned.sponge_reply_start, 46))}…”</span> and ${D.pinned.deterministic ? "3/3 decodes identical" : "decodes drifted"}.`,
        cmd: "docker compose run --rm workbench python attack-sponge/scripts/s05_pinned.py" },
      { chapter: "Impact", label: "Weak transfer",
        guide: "Take the frozen suffix to runtimes the search never saw. The larger sibling from the same family stops normally, both with filler and with the sponge suffix. A chat model behind an API also ends its reply. The suffix was tuned to one model’s scores, and it transfers to neither runtime.",
        caption: `Frozen suffix, held-out runtimes. ${D.transfer.rows[1].model}: clean ${D.transfer.rows[1].clean_out} tokens, with suffix <b>${D.transfer.rows[1].sponge_out}</b> (reached the cap: ${D.transfer.rows[1].hit_cap}). ${D.transfer.rows.length > 2 ? D.transfer.rows[2].model + ": " + D.transfer.rows[2].sponge_out + " tokens (cap: " + D.transfer.rows[2].hit_cap + ")." : ""} Transfer verdict: <b>${D.transfer.n_hit}/${D.transfer.n_heldout}</b> held-out runtimes run to the ${D.cap}-token cap, in this reference run. Source row still fires ${D.pinned.pinned.n_out}/${D.cap}.`,
        cmd: "docker compose run --rm workbench python attack-sponge/scripts/s06_transfer.py" },
      { chapter: "Defense", label: "Token budgets",
        guide: "Defend the input side by counting what the server actually pays for: tokens, after normalization. A character limit lets a very token-heavy request through in a short string. This policy refuses stacked combining marks, normalizes Unicode, then enforces a token cap, with headroom for non-English text that genuinely needs more tokens. It rejects most attack inputs and no ordinary ones, but the mixed-script input slips under the cap.",
        caption: `Gateway policy: max ${D.d1.max_marks} combining marks per character, NFKC, then a ${D.d1.token_cap}-token cap. At the ${D.d1.char_cap}-character limit: ${D.d1.worst_tokens_under_char_cap} tokens of rare script would pass a character cap; the policy rejects ${D.d1.n_reject}/4 attack rows and <b>${D.d1.benign.filter(b => b.policy !== "accept").length}/${D.d1.benign.length}</b> benign greetings (busiest benign row: ${Math.max(...D.d1.benign.map(b => b.tokens))} tokens; headroom ${D.d1.token_cap - Math.max(...D.d1.benign.map(b => b.tokens))}). The cap bounds the bill at ${D.d1.token_cap} tokens whatever the characters say.`,
        cmd: "docker compose run --rm workbench python attack-sponge/scripts/d1_budget.py" },
      { chapter: "Defense", label: "Hard caps",
        guide: "Defend the output edge with hard limits enforced outside the model. The cap comes from legitimate traffic: the 95th percentile of ordinary reply lengths. The sponge then runs into the cap instead of the token limit it was denied, and its CPU-seconds bill collapses with it. The same cap trims the rare genuinely long legitimate reply, which is the measured cost.",
        caption: `Legitimate replies (n=${D.d2.calibration.n}): median ${Math.round(D.d2.calibration.med)}, p95 ${D.d2.calibration.p95}, max ${D.d2.calibration.max} (this model rambles on its own: 1 reply hit the ${D.d2.calibration.cap_used}-token measurement cap) → gateway cap <b>${D.d2.gate_tokens}</b>. The sponge: ${D.d2.uncapped.n_out} tokens, ${D.d2.mult_uncapped.toFixed(1)}× clean CPU-s uncapped → <b>${D.d2.capped.n_out} tokens, ${D.d2.mult_capped.toFixed(1)}×</b> capped. Legitimate replies trimmed: ${D.d2.legit_lost}/${D.d2.calibration.n}. At the capped run’s ${D.d2.rate_tps.toFixed(1)} tokens/s, a 10 s wall-clock deadline would cut any request at about ${D.d2.cut_at_10s} tokens. Caps bound the bill; they do not detect the attack.`,
        cmd: "docker compose run --rm workbench python attack-sponge/scripts/d2_caps.py" },
      { chapter: "Defense", label: "Watch the bill",
        guide: "Budgets stop the request; telemetry sees what got through. A gateway that meters input and output tokens per request flags outliers with a robust z-score over ordinary traffic, no attack knowledge needed. The input meter catches the amplified row instantly. The output meter is the honest surprise: this model’s own traffic already rambles to the cap, so the sponge hides under the bar.",
        caption: `Log of ${D.d3.n_ordinary} ordinary requests plus the two attack rows (replayed from this run’s measurements). Ordinary output tokens: median ${Math.round(D.d3.ordinary.out_med)}, MAD ${Math.round(D.d3.ordinary.out_mad)}; bar at robust z > ${D.d3.z}. Amplified input flagged on input tokens: <b>${D.d3.amplified_flagged}</b>. Sponge on output tokens: z=<b>${D.d3.z_sponge_out.toFixed(1)}</b>, under the bar, because ordinary traffic itself reached ${D.d3.worst_ordinary_out} tokens. False positives ${D.d3.fp}/${D.d3.n_ordinary}. The bill: ${N(D.d3.bill_normal)} → ${N(D.d3.bill_with_attacks)} tokens (${(D.d3.bill_with_attacks / D.d3.bill_normal).toFixed(1)}×).`,
        cmd: "docker compose run --rm workbench python attack-sponge/scripts/d3_telemetry.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="A chat prompt with an 8-token suffix hole, the victim model, its greedy reply with a stop-token gate, and a measurement panel below"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) =>
        S("rect", { x, y, width: w, height: h, rx: 14, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
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
      const reqLines = wrap(D.request, 30, 2);
      mono(gPrompt, 48, 114, "user    " + reqLines[0], { fill: V("teal") });
      if (reqLines[1]) mono(gPrompt, 48, 132, reqLines[1], { fill: V("teal") });
      label(gPrompt, 48, 158, "SUFFIX", { "letter-spacing": "1" });
      const CELLS = [], CX0 = 48, CYR = [168, 186], CW = 30, CH = 13, PITCH = 33;
      for (let i = 0; i < D.n_suffix; i++) {
        const x = CX0 + (i % 8) * PITCH, y = CYR[Math.floor(i / 8)];
        const r = S("rect", { x, y, width: CW, height: CH, rx: 3, fill: "none", stroke: V("line"), "stroke-width": 1.2, "stroke-dasharray": "3 3" }, gPrompt);
        CELLS.push({ i, x, y, r });
      }
      const sufNote = mono(gPrompt, 48, 226, "", { fill: V("muted") });
      mono(gPrompt, 48, 258, "<|im_start|>assistant", { fill: V("violet") });
      T(gPrompt, 48, 280, "generation starts here · greedy", 13, { fill: V("muted") });

      const gModel = S("g", { class: "dimmable" }, svg);
      label(gModel, 410, 46, "MODEL");
      card(gModel, 410, 56, 190, 240, V("violet"));
      T(gModel, 505, 76, "decoder stack", 13, { "text-anchor": "middle", fill: V("muted") });
      for (let i = 0; i < 8; i++) S("rect", { x: 428, y: 84 + i * 16, width: 154, height: 11, rx: 4, fill: V("violet"), "fill-opacity": .07 + i * .035, stroke: V("violet"), "stroke-width": .8 }, gModel);
      const gModelA = S("g", {}, gModel);
      T(gModelA, 505, 234, "smollm2-135m", 16, { "text-anchor": "middle", class: "mono", "font-weight": 700, fill: V("violet") });
      T(gModelA, 505, 256, `${(D.fetch.params / 1e6).toFixed(1)}M params · ${D.fetch.layers} layers`, 13, { "text-anchor": "middle", fill: V("muted") });
      T(gModelA, 505, 280, "white-box access · A03", 13, { "text-anchor": "middle", fill: V("bad"), "font-weight": 600 });
      const gModelB = S("g", {}, gModel);
      T(gModelB, 505, 234, D.transfer.rows[1].model, 16, { "text-anchor": "middle", class: "mono", "font-weight": 700, fill: V("violet") });
      T(gModelB, 505, 256, D.transfer.rows[1].note, 13, { "text-anchor": "middle", fill: V("muted") });
      T(gModelB, 505, 280, "stopping holds here", 13, { "text-anchor": "middle", fill: V("ok"), "font-weight": 600 });

      const gReply = S("g", { class: "dimmable" }, svg);
      label(gReply, 640, 46, "REPLY");
      T(gReply, 922, 46, "GREEDY", 13, { "text-anchor": "end", fill: V("muted"), "font-weight": 700, "letter-spacing": "2" });
      const replyCard = card(gReply, 640, 56, 290, 240);
      const replyLines = [0, 1, 2, 3, 4, 5].map(i => mono(gReply, 656, 96 + i * 24, "", { "font-weight": 600 }));
      const eosChip = S("g", {}, gReply);
      S("rect", { x: 656, y: 226, width: 132, height: 22, rx: 6, fill: V("warn"), "fill-opacity": .14, stroke: V("warn"), "stroke-width": 1.4 }, eosChip);
      T(eosChip, 722, 241, esc(D.loss.eos), 13, { "text-anchor": "middle", class: "mono", "font-weight": 700, fill: V("warn") });
      const eosNote = T(gReply, 656, 272, "", 13, { fill: V("muted") });
      const nOut = T(gReply, 918, 96, "", 30, { "text-anchor": "end", class: "mono", "font-weight": 800 });
      const nOutLbl = T(gReply, 918, 114, "tokens out", 13, { "text-anchor": "end", fill: V("muted") });

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

      // cost meter beside the reply
      const gCost = S("g", { class: "dimmable" }, svg);
      label(gCost, 656, 268, "COST");
      S("rect", { x: 656, y: 274, width: 130, height: 10, rx: 3, fill: V("line"), opacity: .5 }, gCost);
      const costBar = S("rect", { x: 656, y: 274, width: 0, height: 10, rx: 3, fill: V("bad") }, gCost);
      const costTxt = mono(gCost, 796, 283, "", { "text-anchor": "end", fill: V("muted") });

      // ------------------------------------------------ detail panels (one per step)
      const panel = () => S("g", { opacity: 0 }, svg);
      const PY = 322;

      // P1: the victim fixture and what the model reads
      const gP1 = panel();
      card(gP1, 40, PY, 500, 194);
      label(gP1, 60, PY + 24, "THE VICTIM FIXTURE");
      [["victim", "SmolLM2-135M-Instruct · plain base", "violet"],
       ["params", `${(D.fetch.params / 1e6).toFixed(1)}M · fp32 · CPU only`, "ink"],
       ["vocab", `${N(D.fetch.vocab)} tokens`, "ink"],
       ["decode", "greedy · top token every time", "ink"],
       ["stop", `${D.loss.eos} ends every reply`, "warn"],
       ["access", "white-box: weights + gradients (A03)", "bad"]]
        .forEach(([k, v, c], i) => mono(gP1, 60, PY + 56 + i * 23, k.padEnd(8, " ") + v, { fill: V(c) }));
      card(gP1, 560, PY, 360, 194);
      label(gP1, 580, PY + 24, "A NATURAL SPONGE CHECK");
      mono(gP1, 580, PY + 52, "user: " + clip(D.natural_sponge, 40), { fill: V("teal") });
      T(gP1, 580, PY + 80, `${D.fetch.natural_tokens}/${D.fetch.natural_cap} tokens, never stopped`, 15, { "font-weight": 700, fill: V("bad") });
      mono(gP1, 580, PY + 104, "begging for endless output already", { fill: V("muted") });
      mono(gP1, 580, PY + 122, "breaks this tiny model with no search;", { fill: V("muted") });
      mono(gP1, 580, PY + 140, "the search exists for models that stop", { fill: V("muted") });
      mono(gP1, 580, PY + 164, `clean reply: “${clip(D.fetch.reply, 34)}…”`, { fill: V("warn") });

      // P2: tokens per class per tokenizer
      const gP2 = panel();
      card(gP2, 40, PY, 880, 194);
      label(gP2, 60, PY + 24, "TOKENS FOR THE SAME ~180 CHARACTERS");
      mono(gP2, 60, PY + 48, "class      chars  smollm2  qwen2.5    gpt2", { fill: V("muted") });
      const TOKBARS = [];
      CLS.forEach((cls, i) => {
        const y = PY + 74 + i * 23, r = D.amplify.rows[cls];
        mono(gP2, 60, y, cls.padEnd(10, " ") + String(r.chars).padStart(4, " "), { "font-weight": 600 });
        ["smollm2", "qwen2.5", "gpt2"].forEach((tn, j) => {
          const x = 218 + j * 210;
          S("rect", { x, y: y - 9, width: 92, height: 9, rx: 3, fill: V("line"), opacity: .5 }, gP2);
          const b = S("rect", { x, y: y - 9, width: 0, height: 9, rx: 3, fill: V(j === 0 ? "bad" : "violet"), opacity: .85 }, gP2);
          TOKBARS.push({ b, w: 92 * r.tokens[tn] / 924 });
          mono(gP2, x + 98, y, String(r.tokens[tn]), { fill: V("muted") });
        });
      });
      mono(gP2, 60, PY + 188, "counts are exact; tokenization is deterministic", { fill: V("muted") });

      // P3: amplification + prefill timing
      const gP3 = panel();
      card(gP3, 40, PY, 440, 194);
      label(gP3, 60, PY + 24, "TOKENS PER CHARACTER (VS PLAIN)");
      const AMPBARS = [];
      const maxAmp = Math.max(...CLS.slice(1).map(c => D.amplify.amp.smollm2[c]));
      CLS.slice(1).forEach((cls, i) => {
        const y = PY + 62 + i * 30;
        mono(gP3, 60, y, cls.padEnd(8, " "), { "font-weight": 600 });
        S("rect", { x: 140, y: y - 10, width: 200, height: 12, rx: 4, fill: V("line"), opacity: .5 }, gP3);
        const b = S("rect", { x: 140, y: y - 10, width: 0, height: 12, rx: 4, fill: V("bad") }, gP3);
        AMPBARS.push({ b, w: 200 * D.amplify.amp.smollm2[cls] / maxAmp });
        mono(gP3, 352, y, D.amplify.amp.smollm2[cls].toFixed(1) + "x", { "font-weight": 700, fill: V("bad") });
      });
      mono(gP3, 60, PY + 182, `access A01: send text, read the clock`, { fill: V("muted") });
      card(gP3, 500, PY, 420, 194);
      label(gP3, 520, PY + 24, "PREFILL MEDIAN (MS, 5 REPS)");
      const pmax = Math.max(...D.amplify.timing_ms[D.amplify.worst]);
      CLS.forEach((cls, i) => {
        const y = PY + 56 + i * 24;
        mono(gP3, 520, y, cls.padEnd(8, " "), { "font-weight": cls === "plain" ? 700 : 400, fill: cls === "plain" ? V("teal") : V("ink") });
        const b = S("rect", { x: 590, y: y - 10, width: 0, height: 12, rx: 4, fill: cls === "plain" ? V("teal") : V("bad") }, gP3);
        AMPBARS.push({ b, w: 240 * (D.amplify.timing_ms[cls][2] || 1) / pmax });
        mono(gP3, 838, y, nM(D.amplify.timing_ms[cls][2]), { "text-anchor": "end", fill: V("muted") });
      });
      mono(gP3, 520, PY + 182, `ratio ${D.amplify.ratio.toFixed(1)}x · p=${D.amplify.p < 0.001 ? D.amplify.p.toExponential(1) : D.amplify.p.toFixed(3)} (Mann-Whitney)`, { fill: V("muted") });

      // P4: margin tape + junk sweep
      const gP4 = panel();
      card(gP4, 40, PY, 560, 194);
      label(gP4, 60, PY + 24, "STOP-TOKEN MARGIN PER POSITION");
      const M = D.loss.rows[0].margins, mMax = Math.max(...M.map(Math.abs));
      const MZERO = 430, MSCALE = 60 / mMax;
      S("path", { d: `M60 ${MZERO} V500`, stroke: V("line"), "stroke-width": 1.5 }, gP4);
      S("path", { d: `M52 ${MZERO - 60} H560`, stroke: V("line"), "stroke-width": 1, "stroke-dasharray": "3 4" }, gP4);
      mono(gP4, 46, MZERO - 60, "+", { "text-anchor": "end", fill: V("muted") });
      mono(gP4, 46, MZERO + 62, "stop wins", { "text-anchor": "end", fill: V("muted") });
      const MBARS = M.map((m, i) => {
        const x = 68 + i * 25, h = Math.abs(m) * MSCALE;
        const r = S("rect", { x, y: m >= 0 ? MZERO - h : MZERO, width: 14, height: 0, rx: 2,
          fill: m >= 0 ? V("teal") : V("bad"), "fill-opacity": i === M.length - 1 ? 1 : .55 }, gP4);
        if (i === M.length - 1) mono(gP4, x + 7, 512, String(i + 1), { "text-anchor": "middle", fill: V("bad"), "font-weight": 700 });
        else if (i % 4 === 0) mono(gP4, x + 7, 512, String(i + 1), { "text-anchor": "middle", fill: V("muted") });
        return { r, h, m };
      });
      card(gP4, 620, PY, 300, 194);
      label(gP4, 640, PY + 24, "FILLER SWEEP (CAP " + D.cap + ")");
      const SWEEPROWS = D.loss.junk_sweep.map((r, i) => {
        const y = PY + 54 + i * 25, g = S("g", {}, gP4);
        mono(g, 640, y, `' x' x ${String(r.junk).padStart(2, " ")}`, { "font-weight": 600 });
        mono(g, 760, y, String(r.n_out).padStart(3, " ") + " tk", { fill: r.stopped ? V("teal") : V("bad"), "font-weight": 700 });
        mono(g, 904, y, r.stopped ? "stops" : "runs to cap", { "text-anchor": "end", fill: r.stopped ? V("muted") : V("bad") });
        return g;
      });

      // P5: the search: suffix heat + loss curves
      const gP5 = panel();
      card(gP5, 40, PY, 520, 194);
      label(gP5, 60, PY + 24, "STUDENT RUN · LOSS PER STEP");
      const S5 = [[0, D.search.loss0]].concat(D.search.hist.map(h => [h.step, h.loss]));
      const S5X = s => L(100, 500, s / 8), S5Y = v => L(486, 356, (v) / Math.max(0.06, D.search.loss0));
      S("path", { d: "M100 352 V486 H500", fill: "none", stroke: V("line"), "stroke-width": 1.5 }, gP5);
      const sPts = S5.map(([s, l]) => [S5X(s), S5Y(l)]);
      const sLine = S("polyline", { fill: "none", stroke: V("bad"), "stroke-width": 3, "stroke-linejoin": "round" }, gP5);
      const sDots = S5.map(([s, l]) => S("circle", { cx: S5X(s), cy: S5Y(l), r: 3.2, fill: V("bad") }, gP5));
      mono(gP5, 108, S5Y(S5[0][1]) + 16, D.search.loss0.toFixed(3), { fill: V("muted") });
      mono(gP5, 492, S5Y(D.search.best_loss) - 12, D.search.best_loss.toFixed(3), { "text-anchor": "end", "font-weight": 700, fill: V("bad") });
      mono(gP5, 60, PY + 172, `${D.search.s_per_step.toFixed(1)} s/step · its suffix decodes to ${D.search.probe_out} tokens`, { fill: V("muted") });
      card(gP5, 580, PY, 340, 194);
      label(gP5, 600, PY + 24, "THE LONG RUN BEHIND THE ASSET");
      const CV = D.long.curve, cvMax = Math.max(...CV.map(c => c.traj)), cvMin = 1;
      const CVX = i => L(600, 890, i / (CV.length - 1)), CVY = v => L(486, 360, (Math.log(v) - Math.log(cvMin)) / (Math.log(cvMax) - Math.log(cvMin)));
      const cvLine = S("polyline", { fill: "none", stroke: V("violet"), "stroke-width": 2.5, "stroke-linejoin": "round" }, gP5);
      S("path", { d: `M600 ${CVY(D.cap)} H890`, stroke: V("warn"), "stroke-width": 1.2, "stroke-dasharray": "4 4" }, gP5);
      mono(gP5, 892, CVY(D.cap) - 6, "cap " + D.cap, { "text-anchor": "end", fill: V("warn") });
      const cvDots = CV.map((c, i) => S("circle", { cx: CVX(i), cy: CVY(c.traj), r: 2.6, fill: V("violet") }, gP5));
      mono(gP5, 600, PY + 172, `${D.long.rounds} rounds · trajectory length per round (log)`, { fill: V("muted") });

      // P6: the bill: clean vs sponge timelines
      const gP6 = panel();
      card(gP6, 40, PY, 880, 120);
      label(gP6, 60, PY + 24, "ONE REQUEST, TWO BILLS");
      const rows6 = [["clean", D.pinned.clean.n_out, D.pinned.clean.wall_s, "teal", "stopped at " + D.pinned.clean.n_out],
        ["+ sponge", D.pinned.pinned.n_out, D.pinned.pinned.wall_s, "bad", "never stopped"]];
      rows6.forEach(([nm, toks, wall, c, note], i) => {
        const y = PY + 58 + i * 34;
        mono(gP6, 60, y, nm.padEnd(9, " "), { "font-weight": 700, fill: V(c) });
        const b = S("rect", { x: 150, y: y - 10, width: 0, height: 13, rx: 4, fill: V(c) }, gP6);
        AMPBARS.push({ b, w: 420 * toks / D.cap });
        mono(gP6, 580, y, `${toks}/${D.cap} tokens`, { fill: V(c), "font-weight": 700 });
        mono(gP6, 700, y, `${wall.toFixed(1)} s wall`, { fill: V("muted") });
        mono(gP6, 904, y, note, { "text-anchor": "end", fill: V(c) });
      });
      S("path", { d: `M${150 + 420 * D.pinned.clean.n_out / D.cap} ${PY + 44} V${PY + 100}`, stroke: V("warn"), "stroke-width": 1.4, "stroke-dasharray": "4 4" }, gP6);
      card(gP6, 40, PY + 132, 880, 62);
      const mults = [[`${D.pinned.mult_tokens.toFixed(1)}x`, "tokens"], [`${D.pinned.mult_wall.toFixed(1)}x`, "wall"],
        [`${D.pinned.mult_cpu.toFixed(1)}x`, "CPU seconds"], [D.pinned.deterministic ? "3/3" : "?", "identical decodes"]];
      mults.forEach(([v, k], i) => {
        T(gP6, 80 + i * 210, PY + 168, v, 22, { class: "mono", "font-weight": 800, fill: V("bad") });
        mono(gP6, 80 + i * 210, PY + 186, k, { fill: V("muted") });
      });

      // P7: transfer table
      const gP7 = panel();
      label(gP7, 60, PY + 24, "ONE FROZEN SUFFIX · EVERY RUNTIME IT MEETS");
      const XFERROWS = D.transfer.rows.map((r, i) => {
        const y = 342 + i * 50, g = S("g", {}, gP7);
        card(g, 60, y, 840, 42, V(r.hit_cap ? "bad" : "line"));
        mono(g, 76, y + 17, r.model, { "font-weight": 700, fill: V(r.hit_cap ? "bad" : "violet") });
        mono(g, 76, y + 33, clip(r.note, 26), { fill: V("muted") });
        mono(g, 430, y + 26, `clean ${r.clean_out} → with suffix ${r.sponge_out} tokens`, { fill: V(r.hit_cap ? "bad" : "warn") });
        mono(g, 884, y + 26, r.hit_cap ? "runs to cap" : "stops", { "text-anchor": "end", "font-weight": 700, fill: V(r.hit_cap ? "bad" : "ok") });
        return g;
      });
      T(gP7, 60, 510, `transfer ${D.transfer.n_hit}/${D.transfer.n_heldout} held-out runtimes reach the cap · the suffix was tuned to one model’s logits`, 13, { "font-weight": 600 });

      // P8: the input policy: gates + rows
      const gP8 = panel();
      card(gP8, 40, PY, 560, 194);
      label(gP8, 60, PY + 24, "GATEWAY INPUT POLICY, IN ORDER");
      [["1", `more than ${D.d1.max_marks} combining marks on one character`, "reject"],
       ["2", "NFKC normalization", "rewrite"],
       ["3", `more than ${D.d1.token_cap} tokens after tokenizing`, "reject"]]
        .forEach(([n, txt, verdict], i) => {
          const y = PY + 56 + i * 42;
          S("rect", { x: 60, y: y - 13, width: 22, height: 22, rx: 6, fill: V(verdict === "reject" ? "ok" : "violet"), "fill-opacity": .16, stroke: V(verdict === "reject" ? "ok" : "violet"), "stroke-width": 1.4 }, gP8);
          T(gP8, 71, y + 2, n, 14, { "text-anchor": "middle", "font-weight": 800, fill: V(verdict === "reject" ? "ok" : "violet") });
          mono(gP8, 94, y + 2, txt, {});
          if (i < 2) S("path", { d: `M71 ${y + 11} V${y + 27}`, stroke: V("line"), "stroke-width": 1.6 }, gP8);
        });
      mono(gP8, 60, PY + 186, `a character cap alone would pass ${D.d1.worst_tokens_under_char_cap} tokens`, { fill: V("muted") });
      card(gP8, 620, PY, 300, 194);
      label(gP8, 640, PY + 24, `ROWS AT THE ${D.d1.char_cap}-CHAR LIMIT`);
      D.d1.rows.filter(r => r.row !== "plain").forEach((r, i) => {
        const y = PY + 52 + i * 25;
        mono(gP8, 640, y, r.row.padEnd(8, " "), { "font-weight": 600 });
        mono(gP8, 716, y, String(r.tokens_raw) + " tk", { fill: V("muted") });
        mono(gP8, 904, y, r.policy === "accept" ? "accepted" : "rejected", { "text-anchor": "end", "font-weight": 700, fill: r.policy === "accept" ? V("bad") : V("ok") });
      });
      mono(gP8, 640, PY + 186, `benign greetings: ${D.d1.benign.filter(b => b.policy === "accept").length}/${D.d1.benign.length} accepted`, { fill: V("muted") });

      // P9: cap calibration + capped vs uncapped
      const gP9 = panel();
      card(gP9, 40, PY, 440, 194);
      label(gP9, 60, PY + 24, "LEGITIMATE REPLY LENGTHS");
      const H9 = 130, W9 = 340, X9 = 90, Y9 = 486;
      const lens = D.d2.calibration.lengths, bin = Math.max(1, Math.ceil(Math.max(...lens) / 12));
      const bins = {};
      lens.forEach(l => { const b = Math.floor(l / bin); bins[b] = (bins[b] || 0) + 1; });
      const bmax = Math.max(...Object.values(bins));
      Object.entries(bins).forEach(([b, c]) => {
        const h = H9 * c / bmax;
        S("rect", { x: X9 + b * (W9 / 13), y: Y9 - h, width: W9 / 13 - 4, height: h, rx: 3, fill: V("teal"), "fill-opacity": .7, stroke: V("teal"), "stroke-width": 1 }, gP9);
      });
      S("path", { d: `M${X9 + (D.d2.gate_tokens / (bin * 13)) * W9} ${Y9 - H9 - 6} V${Y9}`, stroke: V("ok"), "stroke-width": 2.2, "stroke-dasharray": "6 4" }, gP9);
      mono(gP9, X9 + (D.d2.gate_tokens / (bin * 13)) * W9 + 4, Y9 - H9 - 10, `cap ${D.d2.gate_tokens} (p95)`, { fill: V("ok"), "font-weight": 700 });
      S("path", { d: `M${X9} ${Y9} H${X9 + W9}`, stroke: V("line"), "stroke-width": 1.5 }, gP9);
      mono(gP9, 60, PY + 186, `n=${D.d2.calibration.n} · lost to the cap: ${D.d2.legit_lost}/${D.d2.calibration.n}`, { fill: V("muted") });
      card(gP9, 500, PY, 420, 194);
      label(gP9, 520, PY + 24, "THE SPONGE THROUGH THE CAP");
      const rows9 = [["uncapped", D.d2.uncapped.n_out, D.d2.mult_uncapped, "bad"], ["capped", D.d2.capped.n_out, D.d2.mult_capped, "ok"]];
      rows9.forEach(([nm, toks, mult, c], i) => {
        const y = PY + 62 + i * 40;
        mono(gP9, 520, y, nm.padEnd(10, " "), { "font-weight": 700, fill: V(c) });
        const b = S("rect", { x: 620, y: y - 11, width: 0, height: 13, rx: 4, fill: V(c) }, gP9);
        AMPBARS.push({ b, w: 160 * toks / D.cap });
        mono(gP9, 788, y, `${toks} tokens · ${mult.toFixed(1)}x clean CPU`, { fill: V(c), "font-weight": 700 });
      });
      mono(gP9, 520, PY + 156, `at ${D.d2.rate_tps.toFixed(1)} tokens/s a 10 s deadline cuts at ~${D.d2.cut_at_10s}`, { fill: V("muted") });
      mono(gP9, 520, PY + 174, "caps bound the bill; they do not detect the attack", { fill: V("muted") });

      // P10: telemetry summary + flags
      const gP10 = panel();
      card(gP10, 40, PY, 560, 194);
      label(gP10, 60, PY + 24, "PER-REQUEST USAGE LOG (ROBUST Z > 3.5)");
      const logRows = D.d3.log.map((r, i) => {
        const y = PY + 52 + i * 6, g = S("g", {}, gP10);
        mono(g, 60, y, r.id.padEnd(14, " "), { fill: V("muted") });
        mono(g, 200, y, String(r.in).padStart(5, " ") + " in", { fill: V("muted") });
        mono(g, 290, y, String(r.out).padStart(5, " ") + " out", { fill: V("muted") });
        return g;
      });
      card(gP10, 620, PY, 300, 194);
      label(gP10, 640, PY + 24, "WHAT THE METER SAW");
      [[`amplified, input meter`, D.d3.amplified_flagged ? "flagged" : "missed"],
       [`sponge, output meter`, D.d3.sponge_flagged ? "flagged" : "z " + D.d3.z_sponge_out.toFixed(1)],
       [`false positives`, `${D.d3.fp}/${D.d3.n_ordinary}`],
       [`${(D.d3.bill_with_attacks / D.d3.bill_normal).toFixed(1)}x bill`, "visible"]]
        .forEach(([k, v], i) => {
          const y = PY + 56 + i * 30;
          mono(gP10, 640, y, k, { "font-weight": 600 });
          mono(gP10, 900, y, v, { "text-anchor": "end", "font-weight": 700, fill: i === 1 && !D.d3.sponge_flagged ? V("bad") : V("ok") });
        });
      mono(gP10, 640, PY + 182, `${N(D.d3.bill_normal)} -> ${N(D.d3.bill_with_attacks)} tokens`, { fill: V("muted") });

      const P = [gP1, gP2, gP3, gP4, gP5, gP6, gP7, gP8, gP9, gP10];
      const RS = CELLS.map(c => X.rng(410 + c.i)());
      const CELL_MODE = [0, 1, 2, 3, 4, 5, 5, 5, 6, 7];
      const NOTES = [
        "empty hole after your request",
        "fill = tokens per character",
        "rare script fills the budget",
        `stop wins by ${Math.abs(M[M.length - 1]).toFixed(1)} at position ${M.length}`,
        "the search keeps the best suffix",
        `“${clip(D.pinned ? "" : "", 0)}”`,
        "the rewrite shifts nothing here",
        "input policy gates",
        "output cap at p95",
        "metered per request"];
      const polyF = (el, pts, f) => {
        const m = Math.max(1, Math.round(f * (pts.length - 1)) + 1);
        A(el, { points: pts.slice(0, m).map(p => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ") });
      };
      const st = { p: 1, k: 1 };
      const target = n => ({ p: n, k: 1 });

      function draw(s) {
        const n = s.p, k = s.k, act = Math.min(1, k * 1.4).toFixed(3);
        P.forEach((g, i) => { const on = i + 1 === n; A(g, { opacity: on ? act : "0" }); g.style.display = on ? "" : "none"; });

        // suffix cells: empty -> plain fill -> amplified heat -> margin -> search -> pinned -> gates
        const mode = CELL_MODE[n - 1], r = seg(k, .05, .55);
        CELLS.forEach(c => {
          let fill = "none", fo = 0, so = .85, dash = "3 3";
          if (mode === 1) { fill = V("teal"); fo = .12 * r; so = .4 * r; }
          if (mode === 2) { fill = V("bad"); fo = .78 * r; so = r; dash = "none"; }
          if (mode === 3) { fill = V("bad"); fo = .18 * r; so = .5 * r; dash = "none"; }
          if (mode === 4) { fill = V("bad"); fo = (.2 + .5 * RS[c.i]) * r; so = .6 * r; dash = "none"; }
          if (mode >= 5) { fill = V("bad"); fo = .7 * r; so = r; dash = "none"; }
          A(c.r, { fill, "fill-opacity": fo.toFixed(3), stroke: fill === "none" ? V("line") : fill, "stroke-opacity": Math.min(1, so).toFixed(3), "stroke-dasharray": dash });
        });
        sufNote.textContent = n === 5 ? "one-hot gradient ranks swaps" : n === 6 ? "8 tokens, pinned" : NOTES[mode];

        // reply card: clean short reply (1), amplified note (3), pinned run-to-cap (6), transfer (7)
        const R6 = n === 6 ? { t: D.pinned.sponge_reply_start, c: "warn", ty: seg(k, .15, .7) }
          : n === 7 ? { t: D.transfer.rows[1].note + " runtime stops properly", c: "warn", ty: seg(k, .15, .6) }
          : n <= 5 || n === 8 ? { t: D.fetch.reply, c: "warn", ty: seg(k, .1, .7) }
          : { t: "cut at the gateway cap", c: "muted", ty: seg(k, .2, .6) };
        const lines = wrap(clip(String(R6.t).replace(/\n/g, " "), 150), 32);
        lines.forEach((ln, i) => {
          const f = X.clamp(lines.length * R6.ty - i, 0, 1);
          replyLines[i].textContent = ln.slice(0, Math.round(ln.length * f));
        });
        for (let i = 0; i < 6; i++) {          // set every row every draw: no stale styles when text shrinks
          if (i >= lines.length) replyLines[i].textContent = "";
          A(replyLines[i], { fill: V(i < lines.length ? R6.c : "ink") });
        }
        const nOutV = n === 6 ? D.pinned.pinned.n_out : n === 7 ? D.transfer.rows[1].sponge_out : n === 9 ? D.d2.capped.n_out : n <= 5 ? D.fetch.reply_tokens : D.fetch.reply_tokens;
        nOut.textContent = String(nOutV);
        A(nOut, { fill: V(n === 6 ? "bad" : "ink") });
        const eosFires = n === 1 || (n >= 2 && n <= 5) || n === 7 || n === 8;
        A(eosChip, { opacity: eosFires ? 1 : .25 });
        eosNote.textContent = n === 6 ? "the stop token never wins"
          : n === 7 ? "the sibling stops anyway" : n === 9 ? `cut at ${D.d2.gate_tokens} tokens` : "ends the reply here";
        A(replyCard, { stroke: V(n === 6 ? "bad" : n >= 8 ? "ok" : "line") });

        // cost meter: CPU seconds of the priced row
        const cpu = n === 6 ? D.pinned.pinned.cpu_s : n === 9 ? D.d2.capped.cpu_s : D.pinned.clean.cpu_s;
        const cpuMax = Math.max(D.pinned.pinned.cpu_s, D.pinned.clean.cpu_s, D.d2.capped.cpu_s || 0);
        A(costBar, { width: (130 * cpu / cpuMax * E.out(seg(k, .2, .7))).toFixed(1) });
        costTxt.textContent = `${cpu.toFixed(1)} CPU-s`;

        // model card, gradient ribbon, wall, packet
        A(gModelA, { opacity: n === 7 ? 0 : 1 });
        A(gModelB, { opacity: n === 7 ? 1 : 0 });
        const gv = n === 5 ? seg(k, 0, .55) : 0;
        A(grad, { "stroke-dashoffset": (100 * (1 - gv)).toFixed(2), opacity: gv > 0 ? 1 : 0 });
        const wv = n >= 8 ? seg(k, 0, .4) : 0;
        A(gWall, { opacity: wv.toFixed(3) });
        wallLbl.textContent = n === 8 ? "TOKENS" : n === 9 ? "CAP" : "METER";
        A(flowA, { opacity: (1 - wv).toFixed(3) });
        const pv = seg(k, .05, .2) * (1 - seg(k, .5, .65));
        A(pkt, { cx: L(378, 598, seg(k, .05, .55)).toFixed(1), opacity: pv > 0 ? pv.toFixed(3) : 0 });

        // panel internals
        TOKBARS.forEach((b, i) => A(b.b, { width: (b.w * E.out(seg(k, .1 + i * .01, .5 + i * .01))).toFixed(1) }));
        AMPBARS.forEach((b, i) => A(b.b, { width: (b.w * E.out(seg(k, .15 + i * .02, .6 + i * .02))).toFixed(1) }));
        MBARS.forEach((b, i) => {
          const h = b.h * seg(k, .05 + i * .02, .5 + i * .02);
          A(b.r, { y: (b.m >= 0 ? MZERO - h : MZERO).toFixed(1), height: Math.max(0, h).toFixed(1) });
        });
        SWEEPROWS.forEach((g, i) => A(g, { opacity: seg(k, .15 + i * .06, .4 + i * .06).toFixed(3) }));
        logRows.forEach((g, i) => A(g, { opacity: seg(k, .05 + i * .008, .3 + i * .008).toFixed(3) }));
        polyF(sLine, sPts, seg(k, .15, .8));
        sDots.forEach((d, i) => A(d, { opacity: seg(k, .15 + i * .04, .35 + i * .04).toFixed(3) }));
        polyF(cvLine, CV.map((c, i) => [CVX(i), CVY(c.traj)]), seg(k, .2, .9));
        cvDots.forEach((d, i) => A(d, { opacity: seg(k, .2 + i * .01, .4 + i * .01).toFixed(3) }));
        XFERROWS.forEach((g, i) => A(g, { opacity: seg(k, .1 + i * .1, .35 + i * .1).toFixed(3) }));

        // focus + context
        const hot = n === 1 ? [gModel, gReply] : n <= 3 ? [gPrompt, gModel] : n <= 6 ? [gPrompt, gReply] : [gPrompt];
        [gPrompt, gModel, gReply, gFlow, gCost].forEach(g => g.classList.toggle("hot", hot.includes(g)));
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
