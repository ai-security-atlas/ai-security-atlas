/* LAB-19 attack-prompt-leak: "Your system prompt is not a vault" (8 steps,
 * System -> Attack -> Mechanism -> Impact -> Defense). The top band is the request path: the CONTEXT WINDOW
 * (operator system prompt + customer message) -> the model -> the reply the customer sees, with the D1 filter
 * gate before the reply. The bottom panel changes per step: leak bars per request family, the detector's
 * shapes, the checkout, and the evaluation table. Every string and number comes from window.LAB_DATA (data.js,
 * exported by scripts/export_explainer_data.py); request texts are not shown, only their families.
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one step only. No hex colors. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v;
  const D = window.LAB_DATA;
  const CAN = D.canary;
  const pct = ([k, n]) => `${k}/${n} (${Math.round(100 * k / Math.max(n, 1))}%)`;
  const row = id => D.rows.find(r => r.id === id) || { leak: 0, n: 0 };
  const fRow = id => D.filter.rows.find(r => r.id === id) || { blocked: 0 };
  const ev = D.evaluate;
  const plain = D.rates.plain, trans = D.rates.transformed;

  X.define({
    id: "attack-prompt-leak",
    family: "family-prompt",
    title: "Your system prompt is not a <span class=\"outline\">vault</span>",
    legend: [{ role: "teal", label: "Operator prompt" }, { role: "bad", label: "Disclosure request" },
      { role: "violet", label: "Model" }, { role: "warn", label: "Reply" },
      { role: "lime", label: "Canary (staff code)" }, { role: "ok", label: "Defense" }],
    intro: {
      why: "A shop puts a chat assistant on its website and gives it hidden instructions. Customers never see that text. Its operator also pasted a staff discount code into it. If a customer simply asks the assistant for its instructions, does the code stay hidden? And if it leaks, how much does that matter? This lab measures both.",
      plan: "You’ll meet the assistant and see where its instructions sit. Then you’ll send ten kinds of requests for those instructions, ten times each, and count how often the code comes back. After that you’ll try three fixes and measure each one with the same requests.",
      terms: "The system prompt is the operator’s text that the model reads before every customer message. A canary is a harmless made-up value that shows up when something leaks. Here the canary is the staff code. A trial is one request sent once with a fixed random seed, so you can repeat it. The leak rate is the share of trials whose reply contains the code."
    },
    steps: [
      { chapter: "System", label: "The shop bot",
        guide: "Start with the shop working normally. You ask about opening hours and returns, and the assistant, Juniper, answers from its system prompt. The operator also put a staff discount code in that prompt and marked it for staff only. As a customer you can only send messages. The app never sends you the prompt.",
        caption: `Juniper answers ${D.meet.length} ordinary questions from the store policy. The operator’s prompt is ${D.context[0].chars} characters and holds the <span class="c-lime">staff code</span>. The app’s model list and profile list carry no prompt text.`,
        cmd: "docker compose run --rm workbench python attack-prompt-leak/scripts/s01_meet_bot.py" },
      { chapter: "System", label: "One context",
        guide: "The model reads everything as one block of text, called its context. The operator’s prompt comes first and your message comes after it. Because both sit in the same block, the model can copy the prompt into its answer. You send one request for its instructions, and the reply starts quoting the prompt.",
        caption: `<span class="c-teal">system</span> from the operator, ${D.context[0].chars} chars, holds the canary · <span class="c-bad">user</span> from the client, ${D.context[1].chars} chars. One request, seed 0: leak shape <code>${D.first.form || "none"}</code>, prompt overlap ${D.first.overlap.toFixed(2)}.`,
        cmd: "docker compose run --rm workbench python attack-prompt-leak/scripts/s02_context.py" },
      { chapter: "Attack", label: "Ten requests",
        guide: "Now you send ten kinds of disclosure requests, each one ten times with different seeds. Some ask the model to repeat, summarize or translate its instructions. Others ask it to reformat the instructions, for example by spacing out the code. Each bar shows how often the code came back. One ordinary question about discounts is on the chart too.",
        caption: `${D.model}, ${D.trials} trials each. Plain requests leaked in ${pct(plain)}, reformatting requests in ${pct(trans)}. The ordinary <code>discount</code> question got the code in ${row("discount").leak}/${row("discount").n} replies with no trick at all. Base64 leaked in ${row("base64").leak}/${row("base64").n}: the base64 this model wrote does not decode to its prompt.`,
        cmd: "docker compose run --rm workbench python attack-prompt-leak/scripts/s03_trials.py --trials 10" },
      { chapter: "Mechanism", label: "Many shapes",
        guide: "A leaked code doesn’t always look like the original. The model may add spaces, change the case, slip a letter or encode it. The lab’s detector checks for each of these shapes. It also measures how much of the prompt a reply copies word for word. A search for the exact code alone would miss many of these leaks.",
        caption: `Shapes in the reference run’s disclosure replies: ${Object.entries(D.forms).map(([k, v]) => `${k} ${v}`).join(" · ")}. Near-matches use <code>difflib</code> (ratio ≥ 0.85); decodings try base64, hex, ROT13 and reversed text.`,
        cmd: "docker compose run --rm workbench python attack-prompt-leak/scripts/s04_forms.py" },
      { chapter: "Impact", label: "What it buys",
        guide: "Whether a leak matters depends on what the prompt held. This prompt held a working code. At this checkout anyone who types the code gets 40% off, so a customer who read it in a reply pays less. A copy of the store policy alone would give nothing away, because the website already shows it.",
        caption: `${D.checkout.leaked}/${D.checkout.trials} replies carried the canary <code class="c-lime">${CAN}</code>; ${D.checkout.usable} of them work at the fictional checkout, which ignores case, spaces and dashes. ${D.order ? `<code>${D.order.account}</code> pays $${D.order.pay.toFixed(2)} for a $${D.order.total.toFixed(2)} order.` : ""} Nothing is charged: the checkout is a function in the lab.`,
        cmd: "docker compose run --rm workbench python attack-prompt-leak/scripts/s05_checkout.py" },
      { chapter: "Defense", label: "Output filter",
        guide: "The first fix checks each reply before the customer sees it. A reply that contains the code, or eight words in a row from the prompt, is swapped for a refusal. The filter stops the plain leaks. It matches the code in any letter case. A code with spaces, without its dashes or with one wrong letter doesn’t match, so those replies get through.",
        caption: `<span class="c-ok">D1</span> on the same replies: leak ${pct(D.filter.before)} → ${pct(D.filter.after)}. What passed: ${[...new Set(D.filter.rows.flatMap(r => r.passed))].join(", ") || "nothing"} shapes. Ordinary questions blocked: ${pct(D.filter.benign_blocked)}; ${fRow("discount").blocked} of them are <code>discount</code> replies that gave out the code.`,
        cmd: "docker compose run --rm workbench python attack-prompt-leak/scripts/d1_filter.py --trials 10" },
      { chapter: "Defense", label: "Do not reveal",
        guide: "The second fix rewrites the prompt. It tells the model, before and after the code, to keep its instructions confidential, and it gives a fixed refusal line. You run the same requests again. With this small model the rate falls only a little. A rule in the prompt is one more instruction, and the model weighs it against the customer’s request.",
        caption: `<span class="c-ok">D2</span> hardened prompt: leak ${pct(D.hardened.rates.attack)} (baseline ${pct(D.rates.attack)}). Plain ${pct(D.hardened.rates.plain)}, reformatting ${pct(D.hardened.rates.transformed)}.`,
        cmd: "docker compose run --rm workbench python attack-prompt-leak/scripts/s03_trials.py --profile pleak-shop-hardened --trials 10" },
      { chapter: "Defense", label: "Nothing to leak",
        guide: "The last fix removes the code from the prompt. The checkout now looks up the signed-in account and gives the staff discount to staff accounts only. The model still repeats its prompt sometimes, and that text now holds only store policy. This run shows that a code kept out of the prompt cannot leak through the chat. It used one small model and ten fixed requests, so it can’t tell you how often another assistant leaks.",
        caption: `<span class="c-ok">D3</span>: leak ${pct(D.vault.leak)}, prompt still copied word for word in ${pct(D.vault.verbatim)}. Old code at checkout: ${D.vault.orders[0].why}. Evaluate, leak per condition: ${Object.entries(ev).map(([k, r]) => `${k} ${r.leak[0]}/${r.leak[1]}`).join(" · ")}.`,
        cmd: "docker compose run --rm workbench python attack-prompt-leak/scripts/d3_vault.py --trials 5" },
    ],
    html: `<style>[data-explainer="attack-prompt-leak"] svg text { font-variant-ligatures: none; }</style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="A customer message and the operator’s hidden prompt in one context, the model’s reply, leak rates per request family and three defenses"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 14, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) =>
        S("rect", { x, y, width: w, height: h, rx: 12, fill: V("panel"), stroke, "stroke-width": 1.8, ...o }, p);
      function wrap(s, n) {
        const out = []; let line = "";
        for (const w of String(s).split(" ").flatMap(t => t.match(new RegExp(`.{1,${n}}`, "g")) || [t])) {
          if ((line + " " + w).trim().length > n && line) { out.push(line); line = w; } else line = (line + " " + w).trim();
        }
        if (line) out.push(line);
        return out;
      }
      const setLines = (g, arr, x, y, size, dy, o = {}) => { g.textContent = ""; arr.forEach((l, i) => T(g, x, y + i * dy, l, size, o)); };
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);

      // ------------------------------------------------ top band: context -> model -> reply
      const gCtx = S("g", { class: "dimmable" }, svg);
      label(gCtx, 30, 30, "CONTEXT WINDOW · ONE BLOCK OF TEXT THE MODEL READS");
      card(gCtx, 30, 40, 520, 246, V("line"));
      const sysBox = S("rect", { x: 44, y: 52, width: 492, height: 184, rx: 9, fill: V("teal"), "fill-opacity": .07, stroke: V("teal"), "stroke-width": 1.4 }, gCtx);
      T(gCtx, 56, 72, "system · from the operator", 13, { fill: V("teal"), "font-weight": 700 });
      const sysText = S("g", {}, gCtx);
      const badge = S("g", {}, gCtx);
      const badgeBox = S("rect", { x: 330, y: 58, width: 196, height: 22, rx: 11, "fill-opacity": .16, "stroke-width": 1.2 }, badge);
      const badgeTxt = T(badge, 428, 74, "", 13, { "text-anchor": "middle", class: "mono", "font-weight": 800 });
      const usrBox = S("rect", { x: 44, y: 242, width: 492, height: 34, rx: 9, "fill-opacity": .08, "stroke-width": 1.4 }, gCtx);
      const usrTxt = T(gCtx, 56, 264, "", 13, { "font-weight": 700 });

      S("path", { d: "M550 146 H572", stroke: V("dim"), "stroke-width": 3, fill: "none", "marker-end": `url(#${arrowId})` }, svg);
      const gModel = S("g", { class: "dimmable" }, svg);
      card(gModel, 576, 112, 110, 68, V("violet"), { "fill-opacity": 1 });
      T(gModel, 631, 140, "model", 14, { "text-anchor": "middle", fill: V("violet"), "font-weight": 800 });
      T(gModel, 631, 162, D.model, 13, { "text-anchor": "middle", class: "mono", fill: V("muted") });
      S("path", { d: "M686 146 H720", stroke: V("dim"), "stroke-width": 3, fill: "none", "marker-end": `url(#${arrowId})` }, svg);
      const gate = S("rect", { x: 700, y: 146, width: 9, height: 0, rx: 4, fill: V("ok") }, svg);
      const gateTxt = T(svg, 704, 300, "", 13, { "text-anchor": "middle", fill: V("ok"), "font-weight": 700 });

      const gReply = S("g", { class: "dimmable" }, svg);
      label(gReply, 726, 30, "REPLY THE CUSTOMER SEES");
      const replyBox = card(gReply, 726, 40, 204, 246, V("warn"));
      const replyText = S("g", {}, gReply);

      // ------------------------------------------------ bottom panels
      const gInfo = S("g", {}, svg);
      const infoText = S("g", {}, gInfo);

      const gBars = S("g", {}, svg);
      const barsTitle = label(gBars, 30, 318, "");
      const IDS = [...D.rows.filter(r => r.kind !== "benign").map(r => r.id), "discount"];
      const BW = 900 / IDS.length, BASE_Y = 482, BH = 130;
      const bars = IDS.map((id, i) => {
        const x = 30 + i * BW + BW * .18, w = BW * .64, g = S("g", {}, gBars);
        const ghost = S("rect", { x, y: BASE_Y, width: w, height: 0, rx: 4, fill: "none", stroke: V("dim"), "stroke-width": 1.4, "stroke-dasharray": "4 3" }, g);
        const r = S("rect", { x, y: BASE_Y, width: w, height: 0, rx: 4 }, g);
        const val = T(g, x + w / 2, BASE_Y - 6, "", 13, { "text-anchor": "middle", class: "mono", "font-weight": 700 });
        id.split("-").forEach((part, j) => T(g, x + w / 2, BASE_Y + 20 + j * 16, part, 13, { "text-anchor": "middle", fill: V(id === "discount" ? "teal" : "ink-2") }));
        return { id, x, w, ghost, r, val };
      });
      S("line", { x1: 30, x2: 930, y1: BASE_Y, y2: BASE_Y, stroke: V("line"), "stroke-width": 1.2 }, gBars);

      const gShapes = S("g", {}, svg);
      label(gShapes, 30, 318, "SHAPES OF THE CANARY · WHAT THE DETECTOR AND THE D1 FILTER SAY");
      D.selftest.forEach((s, i) => {
        const col = i < 5 ? 0 : 1, y = 350 + (i % 5) * 34, x = 30 + col * 460;
        T(gShapes, x, y, s.shape, 14, { "font-weight": 700 });
        T(gShapes, x + 110, y, s.form || "no leak", 14, { class: "mono", fill: V(s.form ? "lime" : "muted") });
        T(gShapes, x + 290, y, s.filter ? "filter blocks" : "filter passes", 14, { fill: V(s.filter ? "ok" : (s.form ? "bad" : "muted")), "font-weight": 700 });
      });

      const gCheck = S("g", {}, svg);
      label(gCheck, 30, 318, "THE FICTIONAL CHECKOUT · WHOEVER TYPES THE STAFF CODE GETS 40% OFF");
      card(gCheck, 30, 330, 900, 180, V("lime"));
      const ck = D.checkout;
      T(gCheck, 54, 366, `${ck.leaked}/${ck.trials} replies carried the code; ${ck.usable} of them work at checkout`, 15, { "font-weight": 700 });
      if (D.order) {
        T(gCheck, 54, 408, `${D.order.account} (a customer) · order $${D.order.total.toFixed(2)} · code`, 15, {});
        T(gCheck, 400, 408, CAN, 15, { class: "mono", fill: V("lime"), "font-weight": 800 });
        T(gCheck, 54, 450, `pays $${D.order.pay.toFixed(2)}`, 22, { fill: V("bad"), "font-weight": 800 });
      }
      T(gCheck, 54, 490, `to an ordinary discount question: ${ck.benign_leaked} replies · copies of the policy without the code: ${ck.policy_only}`, 13, { fill: V("muted") });

      const gEval = S("g", {}, svg);
      label(gEval, 30, 318, "EVALUATE · SAME REQUESTS, 5 SEEDS, EVERY CONDITION");
      const COLS = [["condition", 30], ["leak", 260], ["reformatting", 420], ["verbatim", 580], ["useful", 720], ["gate", 860]];
      COLS.forEach(([c, x]) => T(gEval, x, 346, c, 13, { fill: V("muted"), "font-weight": 700 }));
      Object.entries(ev).forEach(([name, r], i) => {
        const y = 376 + i * 30, f = ([k, n]) => `${k}/${n}`;
        T(gEval, 30, y, name, 14, { "font-weight": 700, fill: V(name === "secret out of prompt" ? "ok" : "ink") });
        T(gEval, 260, y, f(r.leak), 14, { class: "mono", fill: V(r.leak[0] ? "bad" : "ok") });
        T(gEval, 420, y, f(r.transformed), 14, { class: "mono" });
        T(gEval, 580, y, f(r.verbatim), 14, { class: "mono" });
        T(gEval, 720, y, f(r.useful), 14, { class: "mono" });
        T(gEval, 860, y, r.gate ? "PASS" : "FAIL", 14, { class: "mono", "font-weight": 800, fill: V(r.gate ? "ok" : "bad") });
      });

      // ------------------------------------------------ data per step
      const frac = arr => IDS.map(id => { const r = arr.find(x => x.id === id); return r ? r.leak / Math.max(r.n, 1) : 0; });
      const fracAfter = IDS.map(id => { const r = D.filter.rows.find(x => x.id === id); return r ? r.after / Math.max(r.n, 1) : 0; });
      const BASE = frac(D.rows), HARD = frac(D.hardened.rows);
      const COUNT = {
        base: IDS.map(id => { const r = D.rows.find(x => x.id === id); return `${r.leak}/${r.n}`; }),
        after: IDS.map(id => { const r = D.filter.rows.find(x => x.id === id); return `${r.after}/${r.n}`; }),
        hard: IDS.map(id => { const r = D.hardened.rows.find(x => x.id === id); return `${r.leak}/${r.n}`; }),
      };
      const TITLES = { base: "LEAK RATE PER REQUEST FAMILY · BASELINE PROMPT", after: "BEHIND THE D1 OUTPUT FILTER · DASHED = BASELINE",
        hard: "D2 HARDENED PROMPT · DASHED = BASELINE" };
      const REPLIES = { meet: D.meet[0].a, first: D.first.reply, filtered: D.filter_reply, hardened: D.examples.hardened, vault: D.examples.vault };
      const PROMPTS = { base: D.prompt, vault: D.prompt_vault };

      // ------------------------------------------------ state
      const NUM = ["usr", "ctxHot", "gate", "pInfo", "pBars", "pShapes", "pCheck", "pEval", "ghost",
        ...IDS.map((_, i) => "b" + i), ...IDS.map((_, i) => "g" + i)];
      const zero = () => { const s = {}; NUM.forEach(k => s[k] = 0); return Object.assign(s, { reply: "meet", prompt: "base", info: 1, set: "base" }); };
      const st = zero();
      const withBars = (s, set, ghost) => {
        const v = set === "base" ? BASE : set === "after" ? fracAfter : HARD;
        IDS.forEach((_, i) => { s["b" + i] = v[i]; s["g" + i] = ghost ? BASE[i] : 0; });
        return Object.assign(s, { pBars: 1, set, ghost: ghost ? 1 : 0 });
      };
      function target(n) {
        const s = zero();
        if (n === 1) return Object.assign(s, { pInfo: 1, info: 1 });
        if (n === 2) return Object.assign(s, { usr: 1, ctxHot: 1, reply: "first", pInfo: 1, info: 2 });
        if (n === 3) return withBars(Object.assign(s, { usr: 1, reply: "first" }), "base", false);
        if (n === 4) return Object.assign(s, { usr: 1, reply: "first", pShapes: 1 });
        if (n === 5) return Object.assign(s, { usr: 1, reply: "first", pCheck: 1 });
        if (n === 6) return withBars(Object.assign(s, { usr: 1, gate: 1, reply: "filtered" }), "after", true);
        if (n === 7) return withBars(Object.assign(s, { usr: 1, reply: "hardened" }), "hard", true);
        return Object.assign(s, { usr: 1, reply: "vault", prompt: "vault", pEval: 1 });
      }

      const INFO = {
        1: [[`operator view: the system prompt is ${D.context[0].chars} characters and holds the staff code`, "teal"],
          ["customer view: the model list and the profile list name the profiles, with no prompt text", "muted"],
          [`customer: ${D.meet[0].q}`, "ink"]],
        2: [[`system ${D.context[0].chars} chars from the operator + user ${D.context[1].chars} chars from the customer`, "teal"],
          [`one disclosure request, seed 0 → leak shape: ${D.first.form || "none"}`, "lime"],
          [`prompt overlap: ${D.first.overlap.toFixed(2)} of the operator’s text copied word for word`, "warn"]],
      };

      function draw(s) {
        // context: system prompt (base or vault) and the customer message
        const vault = s.prompt === "vault";
        setLines(sysText, PROMPTS[s.prompt].flatMap(p => wrap(p, 74)).slice(0, 10), 56, 96, 13, 14.5, {});
        badgeTxt.textContent = vault ? "no code in the prompt" : CAN;
        A(badgeBox, { fill: V(vault ? "ok" : "lime"), stroke: V(vault ? "ok" : "lime") });
        A(badgeTxt, { fill: V(vault ? "ok" : "lime") });
        const bad = s.usr > .5;
        A(usrBox, { fill: V(bad ? "bad" : "teal"), stroke: V(bad ? "bad" : "teal") });
        usrTxt.textContent = bad ? "user · from the customer: a request for the instructions" : "user · from the customer: an ordinary question";
        A(usrTxt, { fill: V(bad ? "bad" : "teal") });
        A(sysBox, { "stroke-width": 1.4 + 1.6 * s.ctxHot });

        // D1 gate and the reply
        A(gate, { y: (146 - 70 * s.gate).toFixed(1), height: (140 * s.gate).toFixed(1) });
        gateTxt.textContent = s.gate > .5 ? "D1 filter" : "";
        let txt = REPLIES[s.reply] || "";
        const leakShown = txt.includes(CAN), at = txt.indexOf(CAN);
        if (at > 150) txt = "… " + txt.slice(at - 110);        // keep the leaked code in view
        replyText.textContent = "";
        wrap(txt, 25).slice(0, 13).forEach((l, i) => T(replyText, 740, 66 + i * 17, l, 13,
          { fill: V(l.includes(CAN) || l.includes(CAN.slice(0, 12)) ? "lime" : "ink"), "font-weight": l.includes(CAN.slice(0, 6)) ? 800 : 400 }));
        A(replyBox, { stroke: V(s.reply === "filtered" || s.reply === "vault" ? "ok" : leakShown ? "lime" : "warn") });

        // panels
        A(gInfo, { opacity: s.pInfo });
        setLines(infoText, [], 0, 0, 13, 0);
        (INFO[s.info] || []).forEach(([t, c], i) => T(infoText, 30, 346 + i * 40, t, 15, { fill: V(c), "font-weight": i === 1 ? 700 : 400 }));
        A(gBars, { opacity: s.pBars });
        barsTitle.textContent = TITLES[s.set] || "";
        bars.forEach((b, i) => {
          const h = BH * s["b" + i], gh = BH * s["g" + i];
          A(b.r, { y: (BASE_Y - h).toFixed(1), height: h.toFixed(1), fill: V(b.id === "discount" ? "teal" : "bad"), "fill-opacity": .75 });
          A(b.ghost, { y: (BASE_Y - gh).toFixed(1), height: gh.toFixed(1), opacity: s.ghost });
          b.val.textContent = (COUNT[s.set] || [])[i] || "";
          A(b.val, { y: (BASE_Y - Math.max(h, gh) - 6).toFixed(1) });
        });
        A(gShapes, { opacity: s.pShapes });
        A(gCheck, { opacity: s.pCheck });
        A(gEval, { opacity: s.pEval });

        // focus on the context in step 2
        const focus = s.ctxHot > .5;
        gCtx.classList.toggle("hot", focus);
        gReply.classList.toggle("hot", focus);
        el.classList.toggle("lx-focus", focus);
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }
          return api.tween(650, k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
