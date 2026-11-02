/* LAB-46 concept-context: "What is in the window" (foundation lab, 9 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: a request strip across the top (operator, client, document, runtime, model, reply) and a panel below
 * that crossfades per step. Token bars are drawn to scale from the exported token counts. Every number and string
 * comes from window.LAB_DATA (data.js, exported from the reference workbench run). Pattern: target(n) is pure,
 * draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA;
  const pol = (rows, p) => rows.find(r => r.policy === p) || {};
  const oll = (shape, ctx) => D.ollama.rows.find(r => r.shape === shape && r.num_ctx === ctx) || {};
  const piece = name => D.assemble.pieces.find(p => p.name.startsWith(name)) || {};
  const shot = name => D.few_shot.rows.find(r => r.cond.startsWith(name)) || {};
  const small = D.assemble.window;
  const big = Math.max(...D.ollama.rows.map(r => r.num_ctx));
  const dl = pol(D.doc.rows, "left"), dr = pol(D.doc.rows, "right"), dn = pol(D.doc.rows, "none");
  const cl = pol(D.chat.rows, "left"), ct = pol(D.chat.rows, "turns");

  X.define({
    id: "concept-context",
    family: "family-prompt",
    title: 'What is in the <span class="outline">window</span>',
    legend: [{ role: "teal", label: "Operator / user text" }, { role: "bad", label: "Attacker-reachable text" },
      { role: "violet", label: "Runtime / model" }, { role: "warn", label: "Reply" }, { role: "lime", label: "Canary" },
      { role: "ok", label: "Defense" }],
    intro: {
      why: "A chat model keeps nothing between requests. All it can use on a request has to sit in its context window: the operator’s system prompt, earlier turns, a retrieved page, tool output and your question. That window holds a fixed number of tokens. So what happens to the rules in a system prompt when a request grows past that size?",
      plan: "You’ll assemble one help-desk request piece by piece and count its tokens. Then you’ll make it too long, once with a long document and once with a long conversation, and see what three cut rules keep. An optional step asks a real Ollama server the same question. After that, four planted examples change what a review sorter prints. You finish with a token budget and with checks that live in code.",
      terms: "A token is a piece of text the model reads. The context window is how many tokens the model sees at once. The system prompt is the operator’s instruction at the start of the window. Truncation cuts tokens so a request fits. In-context learning means the model picks up a pattern from examples in the window. SYS-OK is the tag the system prompt asks for, so you can see whether its rule still applies. The canary is a made-up label that marks the planted examples.",
    },
    steps: [
      { chapter: "System", label: "One request",
        guide: "Build one request for a ferry help desk. It holds the operator’s system prompt, one earlier turn, two paragraphs from a wiki page, a tool result and the question. Each piece costs tokens, and the chat template adds its own. The app gives every request a fixed budget and keeps a few tokens free for the reply, and this request fits inside it.",
        caption: `${D.assemble.model} was trained on a <span class="c-violet">${D.assemble.trained}-token</span> window; the app caps it at <span class="c-violet">${D.assemble.window}</span>: ${D.assemble.budget} for the request, ${D.assemble.max_new} for the reply. System prompt ${piece("system").tokens}, earlier turn ${piece("earlier").tokens}, <span class="c-bad">document ${piece("retrieved").tokens}</span>, <span class="c-bad">tool output ${piece("tool").tokens}</span>, question ${piece("question").tokens}, template ${piece("chat").tokens}: <span class="c-teal">${D.assemble.total}/${D.assemble.budget}</span>. The whole wiki page would make it ${D.assemble.grow[0].tokens}.`,
        cmd: "docker compose run --rm workbench python concept-context/scripts/s01_assemble.py" },
      { chapter: "System", label: "Only the window",
        guide: "Ask questions the weights can’t answer. With the wiki page in the window, the model gives the crossing time from the page. Without it, the model makes up a number. The booking word behaves the same way: the model knows it only while the earlier turn is in the request. Every reply also starts with SYS-OK, so the system rule is in force.",
        caption: `Step 1 request (${D.in_window.tokens} tokens): <span class="c-warn">${D.in_window.rule_k}/${D.in_window.rule_n}</span> replies start with <code>${D.marker}</code>, e.g. <code>${D.in_window.example.reply}</code>. Crossing time with the page: <code>${D.in_window.probes[0].found || "-"}</code>; without it: <code>${D.in_window.probes[1].reply}</code>. Booking word with the earlier turn: <code>${D.in_window.probes[2].reply}</code>; in a new request: <code>${D.in_window.probes[3].reply}</code>.`,
        cmd: "docker compose run --rm workbench python concept-context/scripts/s02_in_window.py" },
      { chapter: "Attack", label: "Long document",
        guide: "Now the retrieved page is long, and whoever can edit that page controls its length. The request no longer fits, and a cut rule decides what goes. A right cut keeps the start and loses the question. A left cut keeps the question and loses the system prompt, and the SYS-OK tag disappears. The turn rule has no old turns to drop here.",
        caption: `A ${D.doc.long}-paragraph page makes the request <span class="c-bad">${dn.sent} tokens</span>, ${D.doc.over} over the budget. Uncut, <code>${D.marker}</code> holds in ${dn.marker}/${dn.n}. <span class="c-violet">Right cut</span> (the transformers default): question in the window ${dr.question}/${dr.n}, reply <code>${dr.reply}</code>. <span class="c-violet">Left cut</span>: system prompt ${dl.system}/${dl.n}, <code>${D.marker}</code> <span class="c-bad">${dl.marker}/${dl.n}</span>.`,
        cmd: "docker compose run --rm workbench python concept-context/scripts/s03_overflow_doc.py" },
      { chapter: "Mechanism", label: "Long conversation",
        guide: "Overflow a long conversation instead. The turn rule keeps the system prompt and drops the oldest turns, so the booking word from the first turn is gone. The left cut drops the system prompt as well, yet the replies still start with SYS-OK. The model copies the tag from its own stored replies, so the output can’t tell you the rule text left the window.",
        caption: `${D.chat.k} earlier turns make <span class="c-bad">${ct.sent} tokens</span>. <span class="c-ok">Turn rule</span>: dropped ${ct.dropped_turns} oldest turns, system prompt ${ct.system}/${ct.n}, first turn ${ct.booking}/${ct.n}, reply to <code>${D.chat.word}</code>: <code>${ct.recall_reply}</code>. <span class="c-violet">Left cut</span>: system prompt ${cl.system}/${cl.n}, yet <code>${D.marker}</code> ${cl.marker}/${cl.n}.`,
        cmd: "docker compose run --rm workbench python concept-context/scripts/s04_overflow_chat.py" },
      { chapter: "Mechanism", label: "Ollama’s cut",
        guide: "Try a real runtime. Ollama sets its window with an option called num_ctx. For a long conversation it keeps the system message and drops old turns, like the turn rule. One long message leaves it nothing to drop, so it cuts the prompt itself. The system prompt goes with it: the tag vanishes, and the model no longer knows its own name.",
        caption: `Ollama ${D.ollama.version}, <code>${D.ollama.model}</code>, <code>num_ctx</code> ${small}. Conversation: ${oll("conversation", big).prompt_tokens} → <span class="c-violet">${oll("conversation", small).prompt_tokens}</span> tokens, <code>${D.marker}</code> ${oll("conversation", small).marker}/${oll("conversation", small).n}, booking word recalled: ${oll("conversation", small).recall ? "yes" : "no"}. One long document: ${oll("one long document", big).prompt_tokens} → <span class="c-bad">${oll("one long document", small).prompt_tokens}</span> tokens, <code>${D.marker}</code> ${oll("one long document", small).marker}/${oll("one long document", small).n}, name: <code>${oll("one long document", small).name_reply}</code>. Over <code>/v1</code> the server used context_length ${D.ollama.v1_context}.`,
        cmd: "docker compose run --rm workbench python concept-context/scripts/s05_ollama.py" },
      { chapter: "Impact", label: "Rule gone",
        guide: "Put the runs side by side. Each cell says what an overflow cost. Whether the system rule survives depends on two things the operator may not control: which runtime serves the model, and how the extra text arrived. No runtime warned the caller, and a request that lost its system prompt still got a fluent reply.",
        caption: `Rows are cut rules, columns are the two overflow shapes. <span class="c-bad">Red</span>: the system prompt or the question left the window. <span class="c-warn">Amber</span>: the system prompt stayed and the oldest turn went. Ollama row from the reference run with <code>num_ctx</code> ${small}.` },
      { chapter: "Impact", label: "Examples win",
        guide: "Switch to a review sorter whose system prompt allows two labels. Four labeled examples, sent as earlier chat turns, change its answers. Correct examples make it accurate. Flipped examples make it call every review positive. Examples that use a made-up label make it print that label for every negative review. The same four examples pasted as plain text barely move it.",
        caption: `16 reviews. Instructions only: ${shot("instructions").correct}/16 correct. Correct turns: ${shot("4 correct").correct}/16. Flipped turns: ${shot("4 flipped").correct}/16 (${D.few_shot.flip} labels changed). Canary turns: <span class="c-lime">${shot("4 canary examples (turns)").canary}/16</span> replies outside the label set, e.g. <code>${D.few_shot.review}</code> → <code class="c-lime">${D.few_shot.example}</code>. Pasted as a document: ${shot("4 canary examples (pasted)").canary}/16.`,
        cmd: "docker compose run --rm workbench python concept-context/scripts/s06_few_shot.py" },
      { chapter: "Defense", label: "Budget tokens",
        guide: "Count tokens before you call the model, and decide what may be cut. Here the system prompt and the question are pinned. The document loses whole paragraphs from its end, and old turns go next, with a note left in the window. Every cut is logged. A message too long to fit even alone gets a clear error, as many hosted APIs return.",
        caption: `${D.budget.rows.map(r => `${r.request}: ${r.tokens} tokens, system prompt <span class="c-ok">${r.system}/${r.n}</span>, question ${r.question}/${r.n}, <code>${D.marker}</code> ${r.marker}/${r.n}; logged <code>${r.events.join("; ")}</code>`).join(". ")}. A ${D.budget.big_tokens}-token message: <code>${D.budget.reject}</code>.`,
        cmd: "docker compose run --rm workbench python concept-context/scripts/d1_budget.py" },
      { chapter: "Defense", label: "Policy in code",
        guide: "Keep the rules that matter out of the window. A label check in code blocks every made-up label, though wrong labels from the allowed set pass it. Server-held history turns a client’s fake turns into plain text, which stops the canary but can still skew the labels. A log of every cut shows which requests lost the system prompt, even when replies look fine.",
        caption: `Label allowlist: canary turns blocked <span class="c-ok">${D.code.allow[1].blocked}/${D.code.allow[1].n}</span>; flipped turns blocked ${D.code.allow[0].blocked}/${D.code.allow[0].n}, wrong labels passed ${D.code.allow[0].wrong_passed}. Server-held history: canary ${D.code.served.canary}/${D.code.served.n}, correct ${D.code.served.correct}/${D.code.served.n}. Truncation log, long conversation with a left cut: system cut ${(D.code.forensic.find(f => f.shape === "conversation" && f.policy === "left") || {}).system_cut}/8, while an output check on <code>${D.marker}</code> flags ${(D.code.forensic.find(f => f.shape === "conversation" && f.policy === "left") || {}).no_marker}/8.`,
        cmd: "docker compose run --rm workbench python concept-context/scripts/d2_policy_in_code.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="A request strip from operator to reply, with a token-window panel per step"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) => S("rect", { x, y, width: w, height: h, rx: 10, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const cut = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
      const one = s => String(s).replace(/\s+/g, " ");
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = (p, d, stroke = V("dim")) => S("path", { d, fill: "none", stroke, "stroke-width": 2, "marker-end": `url(#${arrowId})` }, p);
      const ROLE = { system: "teal", turn: "muted", earlier: "muted", document: "bad", retrieved: "bad", tool: "bad", question: "teal", header: "violet", chat: "violet" };
      const roleOf = name => ROLE[name.split(" ")[0]] || "muted";

      // a token bar drawn to scale: spans = [[name, tokens], ...]
      function bar(p, x, y, spans, k, h = 26) {
        let at = x;
        const ends = [];
        spans.forEach(([name, n]) => {
          const w = Math.max(1, n * k - 1);
          S("rect", { x: at.toFixed(1), y, width: w.toFixed(1), height: h, rx: 3, fill: V(roleOf(name)), opacity: roleOf(name) === "muted" ? .45 : .8 }, p);
          at += n * k;
          ends.push(at);
        });
        return ends;
      }
      const budgetLine = (p, x, y, h, txt) => {
        S("path", { d: `M${x.toFixed(1)} ${y} V${y + h}`, stroke: V("violet"), "stroke-width": 2, "stroke-dasharray": "5 4" }, p);
        if (txt) T(p, x + 6, y + 12, txt, 13, { class: "mono", fill: V("violet") });
      };
      // a cut overlay whose width tweens with the step state
      const cuts = [];
      function cutBox(p, x0, x1, y, h, key) {
        const r = S("rect", { x: x0.toFixed(1), y: y - 3, width: 0, height: h + 6, rx: 4, fill: V("stage"), "fill-opacity": .82, stroke: V("bad"), "stroke-width": 2, "stroke-dasharray": "4 3" }, p);
        cuts.push({ r, w: Math.max(0, x1 - x0), key });
      }

      // ---- request strip
      const strip = [["OPERATOR", "teal", "system prompt"], ["CLIENT", "teal", "user turns"], ["PAGE / TOOL", "bad", "retrieved text"],
        ["RUNTIME", "violet", `${D.assemble.window} tokens`], ["MODEL", "violet", "SmolLM2-360M"], ["REPLY", "warn", `${D.marker} …`]];
      const gStrip = S("g", { class: "dimmable" }, svg);
      const stripBox = strip.map(([key, role, sub], i) => {
        const x = 16 + i * 158;
        const b = card(gStrip, x, 22, 138, 66, V(role));
        label(gStrip, x + 12, 46, key, { fill: V(role), "letter-spacing": "1" });
        T(gStrip, x + 12, 72, sub, 14, { class: "mono" });
        if (i) arrow(gStrip, `M${x - 18} 55 H${x - 3}`);
        return b;
      });
      const panel = () => S("g", { class: "dimmable" }, svg);

      // ---- P1: one request, piece by piece
      const g1 = panel();
      const maxGrow = Math.max(D.assemble.total, ...D.assemble.grow.map(g => g.tokens));
      const k1 = 860 / maxGrow, x1 = 50;
      label(g1, x1, 128, "ONE REQUEST, TO SCALE IN TOKENS");
      bar(g1, x1, 146, D.assemble.pieces.map(p => [p.name, p.tokens]), k1, 30);
      budgetLine(g1, x1 + D.assemble.budget * k1, 136, 50, `budget ${D.assemble.budget}`);
      D.assemble.pieces.forEach((p, i) => {
        const x = x1 + (i % 3) * 300, y = 222 + Math.floor(i / 3) * 34;
        S("rect", { x, y: y - 13, width: 14, height: 14, rx: 3, fill: V(roleOf(p.name)), opacity: .8 }, g1);
        T(g1, x + 22, y, `${cut(p.name, 26)}  ${p.tokens}`, 14, { class: "mono" });
      });
      T(g1, x1, 312, `total ${D.assemble.total} / ${D.assemble.budget}: fits`, 16, { "font-weight": 700, fill: V("teal") });
      label(g1, x1, 350, "THE SAME REQUEST, GROWN");
      const growBars = D.assemble.grow.map((g, i) => {
        const y = 366 + i * 70;
        const r = S("rect", { x: x1, y, width: 0, height: 26, rx: 3, fill: V(i ? "muted" : "bad"), opacity: .7 }, g1);
        T(g1, x1, y + 48, `${g.label}: ${g.tokens} tokens, ${g.over} over`, 14, { class: "mono", fill: V("bad") });
        return { r, w: g.tokens * k1 };
      });
      budgetLine(g1, x1 + D.assemble.budget * k1, 356, 120);

      // ---- P2: only the window
      const g2 = panel();
      label(g2, 40, 128, `RULE CHECK · ${D.in_window.rule_n} QUESTIONS, STEP 1 REQUEST`);
      const ruleCells = Array.from({ length: D.in_window.rule_n }, (_, i) => {
        const ok = i < D.in_window.rule_k;
        const c = card(g2, 40 + i * 110, 142, 98, 52, V(ok ? "warn" : "line"));
        T(g2, 52 + i * 110, 175, ok ? D.marker : "no tag", 15, { class: "mono", "font-weight": 700, fill: V(ok ? "warn" : "muted") });
        return c;
      });
      label(g2, 40, 236, "WHAT THE MODEL CAN ANSWER");
      D.in_window.probes.forEach((p, i) => {
        const x = 40 + (i % 2) * 450, y = 252 + Math.floor(i / 2) * 120;
        const hit = !!p.found;
        card(g2, x, y, 430, 104, V(hit ? "teal" : "bad"));
        T(g2, x + 16, y + 28, p.request, 15, { "font-weight": 700, fill: V(hit ? "teal" : "bad") });
        T(g2, x + 16, y + 56, hit ? `answer from the window: ${p.found}` : "not in the window", 14, { class: "mono" });
        T(g2, x + 16, y + 84, cut(one(p.reply), 46), 13, { class: "mono", fill: V("warn") });
      });

      // ---- P3 / P4: overflow rows with a cut overlay
      const NAMES = { none: "no cut", right: "right cut (default)", left: "left cut", turns: "turn rule" };
      function overflowPanel(g, data, title, extra, key) {
        const sent = data.rows[0].sent, k = 600 / sent, x0 = 300;
        label(g, 40, 128, title);
        const off = []; let at = 0;
        data.spans.forEach(([, n]) => { off.push(at); at += n; });
        data.rows.forEach((r, i) => {
          const y = 146 + i * 92;
          T(g, 40, y + 20, NAMES[r.policy], 16, { "font-weight": 700, fill: V(r.policy === "none" ? "muted" : "violet") });
          T(g, 40, y + 42, `kept ${r.kept} of ${r.sent}`, 13, { class: "mono", fill: V("muted") });
          bar(g, x0, y + 4, data.spans, k, 28);
          if (r.policy !== "none") budgetLine(g, x0 + data.budget * k, y - 4, 44);
          if (r.policy === "right") cutBox(g, x0 + data.budget * k, x0 + sent * k, y + 4, 28, key);
          else if (r.policy === "left" || (r.policy === "turns" && !r.dropped_turns)) cutBox(g, x0, x0 + (sent - data.budget) * k, y + 4, 28, key);
          else if (r.policy === "turns") cutBox(g, x0 + off[1] * k, x0 + off[1 + r.dropped_turns] * k, y + 4, 28, key);
          const bad = r.system < r.n || r.question < r.n;
          T(g, x0, y + 62, extra(r), 14, { class: "mono", fill: V(r.policy === "none" ? "ink" : bad ? "bad" : "ok") });
        });
      }
      const g3 = panel();
      overflowPanel(g3, D.doc, `SYSTEM + ${D.doc.long}-PARAGRAPH PAGE + QUESTION · BUDGET ${D.doc.budget}`,
        r => `system ${r.system}/${r.n} · question ${r.question}/${r.n} · ${D.marker} ${r.marker}/${r.n}`, "p3");
      const g4 = panel();
      overflowPanel(g4, D.chat, `SYSTEM + ${D.chat.k} EARLIER TURNS + QUESTION · BUDGET ${D.chat.budget}`,
        r => `system ${r.system}/${r.n} · turn 1 ${r.booking}/${r.n} · ${D.marker} ${r.marker}/${r.n} · recalls ${D.booking}: ${r.recall ? "yes" : "no"}`, "p4");

      // ---- P5: Ollama
      const g5 = panel();
      label(g5, 40, 128, `OLLAMA ${D.ollama.version} · ${D.ollama.model} · PROMPT TOKENS THE RUNNER KEPT`);
      const maxP = Math.max(...D.ollama.rows.map(r => r.prompt_tokens));
      const k5 = 520 / maxP;
      const oRows = [["conversation", big], ["conversation", small], ["one long document", big], ["one long document", small]];
      const ollBars = oRows.map(([shape, ctx], i) => {
        const r = oll(shape, ctx), y = 150 + i * 90;
        const lost = ctx === small && !r.name;
        T(g5, 40, y + 18, shape, 16, { "font-weight": 700, fill: V(shape === "conversation" ? "teal" : "bad") });
        T(g5, 40, y + 40, `num_ctx ${ctx}`, 14, { class: "mono", fill: V("violet") });
        const b = S("rect", { x: 260, y, width: 0, height: 26, rx: 3, fill: V(lost ? "bad" : "teal"), opacity: .75 }, g5);
        if (ctx === small) budgetLine(g5, 260 + small * k5, y - 6, 38, `${small}`);
        T(g5, 260, y + 50, `${r.prompt_tokens} tokens · ${D.marker} ${r.marker}/${r.n} · knows its name: ${r.name ? "yes" : "no"}` +
          (r.recall === null || r.recall === undefined ? "" : ` · recalls ${D.booking}: ${r.recall ? "yes" : "no"}`), 14,
          { class: "mono", fill: V(lost ? "bad" : "ink") });
        return { b, w: r.prompt_tokens * k5 };
      });

      // ---- P6: what each runtime cost
      const g6 = panel();
      const verdict = r => {
        if (r.question !== undefined && r.question < r.n) return ["question cut", "bad"];
        if (r.system !== undefined && r.system < r.n) return [`system cut · ${D.marker} ${r.marker}/${r.n}`, "bad"];
        if (r.name === false) return [`system cut · ${D.marker} ${r.marker}/${r.n}`, "bad"];
        if (r.booking !== undefined ? r.booking < r.n : r.recall === false) return ["system kept · turn 1 cut", "warn"];
        return ["all kept", "ok"];
      };
      label(g6, 40, 128, "WHAT AN OVERFLOW COST");
      label(g6, 380, 158, "ONE LONG DOCUMENT");
      label(g6, 670, 158, "LONG CONVERSATION");
      const matrix = [["transformers · right cut", dr, pol(D.chat.rows, "right")], ["transformers · left cut", dl, cl],
        ["turn rule (keep system)", pol(D.doc.rows, "turns"), ct],
        [`Ollama ${D.ollama.version} · num_ctx ${small}`, oll("one long document", small), oll("conversation", small)]];
      const cells6 = [];
      matrix.forEach(([name, a, b], i) => {
        const y = 176 + i * 82;
        T(g6, 40, y + 40, name, 16, { "font-weight": 700, fill: V(i === 3 ? "violet" : "ink") });
        [a, b].forEach((r, j) => {
          const [txt, role] = verdict(r);
          const g = S("g", {}, g6);
          card(g, 370 + j * 290, y, 270, 64, V(role));
          T(g, 386 + j * 290, y + 39, txt, 15, { class: "mono", "font-weight": 700, fill: V(role) });
          cells6.push({ g, i: i * 2 + j });
        });
      });

      // ---- P7: four examples in the window
      const g7 = panel();
      label(g7, 40, 128, "16 REVIEWS · 8 POSITIVE, THEN 8 NEGATIVE · P N = ALLOWED LABELS, C = CANARY");
      const truth = "PPPPPPPPNNNNNNNN";
      const cells7 = [];
      D.few_shot.rows.forEach((r, i) => {
        const y = 146 + i * 64;
        T(g7, 40, y + 30, cut(r.cond, 30), 15, { "font-weight": 700, fill: V(/canary/.test(r.cond) ? "bad" : "ink") });
        [...r.labels].forEach((c, j) => {
          const x = 330 + j * 37 + (j >= 8 ? 12 : 0);
          const role = c === "C" ? "lime" : c === "P" ? "teal" : c === "N" ? "violet" : "muted";
          const box = S("rect", { x, y: y + 6, width: 31, height: 36, rx: 5, fill: V(role), "fill-opacity": .35, stroke: V(c === truth[j] ? role : "bad"), "stroke-width": 2 }, g7);
          const t = T(g7, x + 15.5, y + 30, c, 15, { "text-anchor": "middle", "font-weight": 800, class: "mono" });
          cells7.push({ els: [box, t], i, j });
        });
      });
      T(g7, 40, 476, `canary label: ${D.canary}`, 15, { class: "mono", "font-weight": 700, fill: V("lime") });

      // ---- P8: token budget
      const g8 = panel();
      const k8 = 600 / D.doc.rows[0].sent;
      label(g8, 40, 128, `EXPLICIT BUDGET · ${D.doc.budget} TOKENS · SYSTEM PROMPT AND QUESTION PINNED`);
      const budBars = D.budget.rows.map((r, i) => {
        const y = 152 + i * 104;
        T(g8, 40, y + 20, cut(r.request, 28), 15, { "font-weight": 700 });
        const sys = D.doc.spans[0][1];
        S("rect", { x: 300, y, width: (sys * k8 - 1).toFixed(1), height: 28, rx: 3, fill: V("teal"), opacity: .8 }, g8);
        const rest = S("rect", { x: 300 + sys * k8, y, width: 0, height: 28, rx: 3, fill: V(i ? "muted" : "bad"), opacity: .6 }, g8);
        budgetLine(g8, 300 + D.doc.budget * k8, y - 8, 44, `${D.doc.budget}`);
        T(g8, 300, y + 52, `${r.tokens} tokens · system ${r.system}/${r.n} · question ${r.question}/${r.n} · ${D.marker} ${r.marker}/${r.n}`, 14, { class: "mono", fill: V("ok") });
        T(g8, 300, y + 74, `log: ${r.events.join("; ")}`, 14, { class: "mono", fill: V("muted") });
        return { rest, w: (r.tokens - sys) * k8 };
      });
      card(g8, 40, 380, 880, 92, V("ok"));
      T(g8, 60, 412, `a ${D.budget.big_tokens}-token user message`, 15, { "font-weight": 700 });
      T(g8, 60, 446, cut(D.budget.reject, 82), 14, { class: "mono", fill: V("ok") });

      // ---- P9: policy in code
      const g9 = panel();
      label(g9, 40, 128, "LABEL ALLOWLIST IN CODE");
      D.code.allow.forEach((a, i) => {
        const y = 142 + i * 50;
        card(g9, 40, y, 420, 42, V(a.blocked ? "ok" : "bad"));
        T(g9, 56, y + 27, `${cut(a.cond, 26)}: blocked ${a.blocked}/${a.n}`, 14, { class: "mono", "font-weight": 700, fill: V(a.blocked ? "ok" : "bad") });
      });
      label(g9, 500, 128, "HISTORY HELD ON THE SERVER");
      card(g9, 500, 142, 420, 92, V(D.code.served.canary ? "bad" : "ok"));
      T(g9, 516, 172, `canary ${D.code.served.canary}/${D.code.served.n} · correct ${D.code.served.correct}/${D.code.served.n}`, 15, { class: "mono", "font-weight": 700, fill: V("ok") });
      T(g9, 516, 204, `labels ${D.code.served.labels.slice(0, 8)} ${D.code.served.labels.slice(8)}`, 14, { class: "mono" });
      label(g9, 40, 274, "TRUNCATION LOG AGAINST AN OUTPUT CHECK");
      ["shape", "cut rule", "log: system cut", "log: question cut", `output: no ${D.marker}`].forEach((h, j) =>
        T(g9, [40, 220, 360, 540, 730][j], 300, h, 13, { fill: V("muted"), "font-weight": 700 }));
      const rows9 = D.code.forensic.map((f, i) => {
        const y = 326 + i * 30;
        const g = S("g", {}, g9);
        T(g, 40, y, f.shape, 14, { class: "mono" });
        T(g, 220, y, f.policy, 14, { class: "mono" });
        T(g, 360, y, `${f.system_cut}/${f.n}`, 14, { class: "mono", "font-weight": 700, fill: V(f.system_cut ? "bad" : "ok") });
        T(g, 540, y, `${f.question_cut}/${f.n}`, 14, { class: "mono", "font-weight": 700, fill: V(f.question_cut ? "bad" : "ok") });
        const miss = (f.system_cut || f.question_cut) && !f.no_marker;
        T(g, 730, y, `${f.no_marker}/${f.n}${miss ? "  missed" : ""}`, 14, { class: "mono", "font-weight": 700, fill: V(miss ? "bad" : "muted") });
        return g;
      });

      const panels = [g1, g2, g3, g4, g5, g6, g7, g8, g9];
      const keys = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9"];
      const base = Object.fromEntries(keys.map(k => [k, 0]));
      const target = n => ({ ...base, [keys[n - 1]]: 1 });
      // strip boxes each step highlights: operator, client, page/tool, runtime, model, reply
      const hot = [[0, 1, 2, 3], [4, 5], [2, 3], [1, 3], [3], [3, 5], [1, 4, 5], [3], [3, 5]];

      function draw(s) {
        panels.forEach((g, i) => { const v = s[keys[i]]; g.setAttribute("opacity", v.toFixed(3)); g.style.display = v > .01 ? "" : "none"; });
        growBars.forEach(({ r, w }, i) => A(r, { width: (w * seg(s.p1, .2 + i * .2, .7 + i * .2)).toFixed(1) }));
        ruleCells.forEach((c, i) => c.setAttribute("opacity", (.25 + .75 * seg(s.p2, i * .06, .3 + i * .06)).toFixed(3)));
        cuts.forEach(({ r, w, key }) => A(r, { width: (w * seg(s[key], .35, 1)).toFixed(1) }));
        ollBars.forEach(({ b, w }, i) => A(b, { width: (w * seg(s.p5, i * .1, .5 + i * .1)).toFixed(1) }));
        cells6.forEach(({ g, i }) => g.setAttribute("opacity", seg(s.p6, i * .08, .3 + i * .08).toFixed(3)));
        cells7.forEach(({ els, i, j }) => els.forEach(e => e.setAttribute("opacity", (.15 + .85 * seg(s.p7, i * .1 + j * .01, .35 + i * .1 + j * .01)).toFixed(3))));
        budBars.forEach(({ rest, w }, i) => A(rest, { width: Math.max(0, w * seg(s.p8, .2 + i * .2, .7 + i * .2) - 1).toFixed(1) }));
        rows9.forEach((g, i) => g.setAttribute("opacity", (.2 + .8 * seg(s.p9, .3 + i * .1, .5 + i * .1)).toFixed(3)));
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
