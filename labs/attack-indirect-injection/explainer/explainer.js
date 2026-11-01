/* LAB-15 attack-indirect-injection: "The email that wrote its own summary" (9 steps).
 * One persistent scene across the top: Riley's mailbox (fixture-web) → the context window the model receives
 * (system prompt with the canary, Riley's request, retrieved chunks) → the model → the inbox app (reply,
 * renderer, send_email). A detail panel below changes per step. Every reply, count and the hidden note itself
 * come from window.LAB_DATA (data.js, exported from the reference workbench run); none is typed in here.
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, E = X.ease;
  const D = window.LAB_DATA;
  const N = D.trials, CAN = D.canary;
  const R = D.trials_inbox.rows, AR = D.actions_inbox.rows;
  const POIS = ["email-hidden-div", "page-white-text", "page-alt-text"];
  const sum = (rows, ids, k) => ids.reduce((a, id) => a + rows[id][k], 0);
  const frac = ([k, n]) => `${k}/${n}`;
  const H = D.s02.hit, NORTH = D.actions_inbox.north;
  const badge = D.s02.reply.slice(D.s02.reply.indexOf("!["));
  const summary = D.s02.reply.slice(0, D.s02.reply.indexOf("![")).trim();
  const owK = Object.values(D.openwebui.rows).reduce((a, r) => a + r.canary[0], 0);
  const owN = Object.values(D.openwebui.rows).reduce((a, r) => a + r.canary[1], 0);
  const SP = D.spotlight, Q = D.quarantine, RD = D.render, CF = D.confirm, EV = D.evaluate;
  const OFF = D.items.find(i => i.id === "m-offsite");
  const nHidden = D.items.filter(i => i.instruction === "ingested, not visible").length;
  const LABEL = { "email-hidden-div": "display:none", "page-white-text": "white text", "page-alt-text": "alt text",
    "email-comment": "HTML comment", "email-clean": "clean email", "pasted-visible": "pasted by Riley" };

  X.define({
    id: "attack-indirect-injection",
    family: "family-prompt",
    title: 'The email that wrote its own <span class="outline">summary</span>',
    legend: [{ role: "teal", label: "Riley’s data" }, { role: "bad", label: "Hidden note" },
      { role: "violet", label: "Model" }, { role: "warn", label: "Reply" }, { role: "lime", label: "Canary" },
      { role: "ok", label: "Defense" }],
    intro: {
      "why": "Riley’s inbox assistant reads her email and the web pages she saves, then writes summaries for her. Anyone can send Riley an email. Can a stranger’s email make the assistant leak a private value, or send mail in her name? That’s indirect prompt injection: the instruction arrives inside the data the assistant reads.",
      "plan": "You’ll look at one email the way Riley sees it and the way the assistant reads it. Then you’ll measure how often a hidden note gets obeyed, check cases where the note never reaches the model, and see two ways harm happens: an image that loads and an email that gets sent. Last, you’ll test four defenses.",
      "terms": "Ingestion turns an email’s HTML into plain text for the assistant. Retrieval picks the stored pieces of text that match a request and adds them to the model’s input. A canary is a fake secret; here it’s Riley’s card number. A sink is the place where model text turns into an effect, such as an image that loads."
    },
    steps: [
      { chapter: "System", label: "Riley’s inbox",
        guide: "Riley’s assistant has three parts. Her mailbox feeds a search index. The model reads what the search returns, next to the system prompt: the app’s own instructions, which also hold her card number. Her inbox app shows the reply as formatted text and sends any email the reply asks for. Anyone who has Riley’s address can write into that mailbox.",
        caption: `<span class="c-teal">fixture-web</span> holds Riley’s mailbox and saved pages. atlas-app indexes them (RAG) and asks <span class="c-violet">${D.model}</span>. Its system prompt holds her expense-card reference <code class="c-lime">${CAN}</code>. The inbox app renders Markdown and runs <code>ACTION: send_email</code> lines.`,
        cmd: "docker compose run --rm workbench python attack-indirect-injection/scripts/s01_inspect.py" },
      { chapter: "Attack", label: "A hidden note",
        guide: "Dana’s email about the team offsite looks normal to Riley. Its HTML also holds a block styled display:none, which a mail client hides. Ingestion keeps that block, so the assistant reads a note Riley never sees. The note gives the assistant an extra job and wants a private value that appears in no email. Three other items hide notes in other ways.",
        caption: `The attacker only sends email (access A04). <code>m-offsite</code> shows Riley ${OFF.visible} characters; ingestion passes ${OFF.ingested}. ${nHidden} items hide a <span class="c-bad">note for AI assistants</span>: display:none, white 1–2 px text, image alt text. The newsletter’s note sits in an HTML comment, which ingestion drops.` },
      { chapter: "Mechanism", label: "One summary",
        guide: "Riley asks for a summary of Dana’s email. Retrieval adds three pieces of that email to the model’s input, and the hidden note comes with them. The card number already sits in the system prompt of the same input. So the model has an instruction, a secret and a way to write it out. Its summary is correct and ends with an image link.",
        caption: `Retrieved: <code>${D.s02.retrieved.join(" ")}</code>. The reply summarizes the email correctly and ends with <code class="c-lime">${badge}</code>. The model filled in the card reference from its own system prompt.`,
        cmd: "docker compose run --rm workbench python attack-indirect-injection/scripts/s02_summarize.py" },
      { chapter: "Mechanism", label: "Only if ingested",
        guide: "One reply proves little, so each case runs ten times. When the note reaches the model, it gets obeyed in most trials and the summary is still correct, so nothing looks wrong to Riley. Three controls give zero: a note inside an HTML comment that ingestion drops, a clean email, and Riley pasting the email herself. In every one of them, the note never reached the model.",
        caption: `Note in context: obeyed <span class="c-bad">${frac(D.trials_inbox.obeyed)}</span>, with Riley’s task also done in ${sum(R, POIS, "task")}/${POIS.length * N}. Note not in context (comment, clean, pasted): obeyed <span class="c-ok">${frac(D.trials_inbox.controls.obeyed)}</span>.`,
        cmd: "docker compose run --rm workbench python attack-indirect-injection/scripts/s03_trials.py --trials 10" },
      { chapter: "Impact", label: "The badge loads",
        guide: "The model only wrote text. The inbox app turns that text into a page and loads every image in it, the way a browser does. The image address carries the canary to the lab’s collector, which logs the request. Open WebUI, a popular chat interface, does the same with an attached file. In a real product, that request would reach the attacker’s server.",
        caption: `The renderer fetched <code>${H.path}?${H.query}</code>, carrying the canary <code class="c-lime">${CAN}</code>, in ${frac(D.trials_inbox.exfil)} poisoned trials. In Open WebUI ${D.openwebui.version} with the file attached, ${owK}/${owN} replies carried it. Fictional and inert: the collector lives on the compose network.`,
        cmd: "docker compose run --rm workbench python attack-indirect-injection/scripts/s05_openwebui.py --trials 5" },
      { chapter: "Impact", label: "The email it sends",
        guide: "Now the assistant can act. An invoice email hides a note too. Riley asked only for a summary, yet the app sends emails to the invoice sender, a few with her card number in the body. The note borrowed Riley’s authority. Her own requests still matter: a reply to her colleague Priya has to keep working, so any defense must keep it.",
        caption: `Asked only to summarize, the app sent <span class="c-bad">${AR["email-action"].attacker_sent}/${N}</span> emails to <code>${NORTH.to}</code>, ${AR["email-action"].attacker_sent_canary} with <code class="c-lime">${CAN}</code>. “Reply to Priya” works ${AR["reply-request"].task}/${N}.`,
        cmd: "docker compose run --rm workbench python attack-indirect-injection/scripts/s04_action.py --trials 10" },
      { chapter: "Defense", label: "Spotlighting",
        guide: "Spotlighting marks retrieved text as data. Each piece is wrapped in a tag that names its source, and the spaces between its words become ^, so it looks different from instructions. The model obeys the note less often and fewer images load. It still reads the note and still decides, so the rate drops and stays above zero.",
        caption: `<span class="c-ok">Tags, a documents-are-data rule and datamarking</span>: obeyed ${frac(D.trials_inbox.obeyed)} → ${frac(SP.obeyed)}, images with the canary ${frac(D.trials_inbox.exfil)} → ${frac(SP.exfil)}. The invoice still sends the card to Northwind ${SP.actions["email-action"].attacker_sent_canary}/${N}.`,
        cmd: "docker compose run --rm workbench python attack-indirect-injection/scripts/s03_trials.py --profile xinj-inbox-spotlight --trials 10" },
      { chapter: "Defense", label: "Inert sinks",
        guide: "The next two defenses act after the model. An allowlist is a list of trusted sites. The renderer loads images only from Atlas’s own domain and shows the rest as text. A dialog asks Riley before any email goes out. Together they stop every leak in the evaluation. The canary still sits in the reply text, and the dialog helps only if Riley reads it.",
        caption: `<span class="c-ok">Allowlist renderer</span>: images loaded ${RD.auto.loaded} → ${RD.allowlist.loaded}, canary still in the text ${frac(RD.allowlist.canary)}. <span class="c-ok">Confirmation</span>: a careful Riley sends ${CF.careful.northwind}/${CF.careful.trials} to Northwind, a rubber-stamp one ${CF["rubber-stamp"].northwind}/${CF["rubber-stamp"].trials}.`,
        cmd: "docker compose run --rm workbench python attack-indirect-injection/scripts/d2_render.py" },
      { chapter: "Defense", label: "Quarantine",
        guide: "Quarantine splits the assistant in two. A reader model summarizes email with no secrets and no tools. A second model handles actions and never reads the email. Notes still sway the reader, yet nothing leaks, and replies to Priya work less often. These are saved runs of one model. They show the mechanism and how each defense changes it. Other models will give other rates.",
        caption: `<span class="c-ok">Quarantined reader</span>: obeyed ${frac(Q.obeyed)}, canary ${frac(Q.canary)}, exfil ${frac(Q.exfil)}. Evaluate (${D.eval_trials} trials per case): harm ${frac(EV.baseline.harm)} baseline, ${frac(EV.quarantine.harm)} quarantine with utility ${frac(EV.quarantine.utility)}, ${frac(EV["allowlist+confirm"].harm)} allowlist+confirm.`,
        cmd: "docker compose run --rm workbench python attack-indirect-injection/scripts/s03_trials.py --profile xinj-quarantine --trials 10" },
    ],
    html: `<style>[data-explainer="attack-indirect-injection"] svg text, code { font-variant-ligatures: none; font-feature-settings: "liga" 0, "calt" 0; }</style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Riley’s mailbox, the context window, the model and the inbox app"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 14, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2" });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) =>
        S("rect", { x, y, width: w, height: h, rx: 14, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 7, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("teal") }, mk);
      const flow = (p, d) => S("path", { d, fill: "none", stroke: V("teal"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})`, opacity: .8 }, p);
      function wrap(s, n) {
        const out = []; let line = "";
        for (const w of String(s).split(" ")) {
          if ((line + " " + w).trim().length > n && line) { out.push(line); line = w; } else line = (line + " " + w).trim();
        }
        if (line) out.push(line);
        return out;
      }
      const lines = (p, x, y, k, size, o) => Array.from({ length: k }, (_, i) => T(p, x, y + i * (size + 5), "", size, o));
      const setLines = (els, s, n) => { const w = wrap(s, n); els.forEach((t, i) => { t.textContent = i === els.length - 1 && w.length > els.length ? w[i] + " …" : (w[i] || ""); }); };

      // ---------------------------------------------------------------- top: the product
      const gMail = S("g", { class: "dimmable" }, svg);
      label(gMail, 30, 40, "RILEY’S MAILBOX");
      card(gMail, 30, 52, 200, 250);
      const MAIL = [["m-offsite", "Dana Ruiz · offsite", true], ["m-invoice", "Northwind · invoice", true],
        ["p-lamp-review", "saved page · review", true], ["p-dock-specs", "saved page · specs", true],
        ["m-newsletter", "newsletter", false], ["m-printer", "Sam · printer", false]];
      const mailEls = MAIL.map(([id, sub, pois], i) => {
        const y = 62 + i * 39;
        const r = S("rect", { x: 42, y, width: 176, height: 33, rx: 8, "stroke-width": 1.3 }, gMail);
        const t = T(gMail, 52, y + 15, id, 13, { class: "mono", "font-weight": 700 });
        T(gMail, 52, y + 29, sub, 13, { fill: V("muted") });
        return { r, t, pois };
      });

      const gCtx = S("g", { class: "dimmable" }, svg);
      label(gCtx, 258, 40, "CONTEXT WINDOW");
      card(gCtx, 258, 52, 262, 250);
      const blk = (y, h, tag) => {
        const r = S("rect", { x: 270, y, width: 238, height: h, rx: 10, "stroke-width": 1.5 }, gCtx);
        T(gCtx, 280, y + 19, tag, 13, { class: "mono", "font-weight": 700 });
        return { r, sub: T(gCtx, 280, y + 38, "", 13, {}) };
      };
      const bSys = blk(62, 52, "system prompt");
      const bReq = blk(122, 52, "Riley’s request");
      const bDoc = blk(182, 110, "retrieved chunks");
      const noteR = S("rect", { x: 280, y: 236, width: 218, height: 46, rx: 8, "stroke-width": 1.5 }, gCtx);
      const noteT = T(gCtx, 290, 256, "hidden note", 13, { "font-weight": 700 });
      const noteS = T(gCtx, 290, 274, "", 13, {});

      const gLLM = S("g", { class: "dimmable" }, svg);
      label(gLLM, 548, 40, "MODEL");
      card(gLLM, 548, 52, 130, 250, V("violet"));
      for (let i = 0; i < 5; i++) S("rect", { x: 560, y: 100 + i * 26, width: 106, height: 16, rx: 6, fill: V("violet"), "fill-opacity": .12 + .05 * i }, gLLM);
      T(gLLM, 613, 84, D.model, 14, { class: "mono", "text-anchor": "middle", "font-weight": 700 });
      const mRole = T(gLLM, 613, 256, "", 13, { "text-anchor": "middle", "font-weight": 700 });
      const mSub = T(gLLM, 613, 276, "", 13, { "text-anchor": "middle", fill: V("muted") });

      const gApp = S("g", { class: "dimmable" }, svg);
      label(gApp, 704, 40, "INBOX APP");
      card(gApp, 704, 52, 230, 250);
      const repR = S("rect", { x: 714, y: 62, width: 210, height: 98, rx: 10, "stroke-width": 1.5 }, gApp);
      T(gApp, 724, 81, "reply (Markdown)", 13, { class: "mono", "font-weight": 700 });
      const repT = lines(gApp, 724, 100, 2, 13, {});
      const repB = T(gApp, 724, 142, "", 13, { "font-weight": 700 });
      const chip = (y, title) => {
        const r = S("rect", { x: 714, y, width: 210, height: 58, rx: 10, "stroke-width": 1.5 }, gApp);
        T(gApp, 724, y + 21, title, 13, { class: "mono", "font-weight": 700 });
        return { r, sub: T(gApp, 724, y + 42, "", 13, {}) };
      };
      const cRen = chip(168, "renderer");
      const cSend = chip(234, "send_email");

      const gFlow = S("g", { class: "dimmable" }, svg);
      flow(gFlow, "M232 176 H252");
      flow(gFlow, "M522 176 H542");
      flow(gFlow, "M680 176 H698");

      // ---------------------------------------------------------------- bottom panels
      const panel = () => S("g", { opacity: 0 }, svg);
      const PY = 330;

      // 1: the pipeline
      const p1 = panel();
      [["fixture-web", "anyone can send mail", "teal"], ["ingestion", "HTML → plain text", "teal"], ["RAG index", "top chunks per request", "teal"],
        ["atlas-app", `asks ${D.model}`, "violet"], ["inbox app", "renders, sends", "warn"]].forEach(([top, bot, role], i) => {
        const x = 40 + i * 180;
        S("rect", { x, y: PY + 20, width: 150, height: 70, rx: 12, fill: V("panel"), stroke: V(role), "stroke-width": 1.5 }, p1);
        T(p1, x + 75, PY + 50, top, 15, { "text-anchor": "middle", "font-weight": 700, fill: V(role) });
        T(p1, x + 75, PY + 74, bot, 13, { "text-anchor": "middle", fill: V("muted") });
        if (i < 4) S("path", { d: `M${x + 154} ${PY + 55} H${x + 174}`, stroke: V("dim"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, p1);
      });
      T(p1, 40, PY + 126, "Riley reads her mail in a mail client. The model reads what ingestion kept.", 14, { fill: V("muted") });
      T(p1, 40, PY + 150, "Those two can differ, and the sender decides the HTML.", 14, { fill: V("muted") });

      // 2: two views of one email
      const p2 = panel();
      card(p2, 40, PY + 6, 400, 184, V("teal"));
      T(p2, 56, PY + 30, "AS RILEY SEES IT", 13, { fill: V("teal"), "font-weight": 700, "letter-spacing": "1.5" });
      T(p2, 424, PY + 30, `${OFF.visible} chars`, 13, { fill: V("muted"), "text-anchor": "end", class: "mono" });
      setLines(lines(p2, 56, PY + 54, 7, 13, {}), D.offsite_visible.join(" "), 54);
      card(p2, 460, PY + 6, 470, 184, V("bad"));
      T(p2, 476, PY + 30, "WHAT INGESTION PASSES", 13, { fill: V("bad"), "font-weight": 700, "letter-spacing": "1.5" });
      T(p2, 914, PY + 30, `${OFF.ingested} chars`, 13, { fill: V("muted"), "text-anchor": "end", class: "mono" });
      setLines(lines(p2, 476, PY + 54, 1, 13, { fill: V("muted") }), D.offsite_visible.join(" "), 64);
      T(p2, 476, PY + 72, "… the visible text, then:", 13, { fill: V("muted") });
      S("rect", { x: 472, y: PY + 82, width: 446, height: 98, rx: 8, fill: V("bad"), "fill-opacity": .1, stroke: V("bad"), "stroke-width": 1.2, "stroke-dasharray": "5 3" }, p2);
      setLines(lines(p2, 484, PY + 102, 5, 13, { fill: V("bad") }), D.offsite_hidden, 62);

      // 3: one summary, end to end
      const p3 = panel();
      T(p3, 40, PY + 18, "RILEY ASKS", 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.5" });
      T(p3, 160, PY + 18, `“${D.s02.ask}”`, 14, { fill: V("teal"), "font-weight": 600 });
      T(p3, 40, PY + 54, "RETRIEVED", 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.5" });
      D.s02.retrieved.forEach((c, i) => {
        const x = 160 + i * 130, off = c.startsWith("m-offsite");
        S("rect", { x, y: PY + 36, width: 120, height: 28, rx: 8, fill: V(off ? "bad" : "teal"), "fill-opacity": .1, stroke: V(off ? "bad" : "teal"), "stroke-width": 1.2 }, p3);
        T(p3, x + 60, PY + 55, c, 13, { class: "mono", "text-anchor": "middle", "font-weight": 600 });
      });
      T(p3, 690, PY + 55, "hidden note: in context", 13, { fill: V("bad"), "font-weight": 700 });
      card(p3, 40, PY + 78, 890, 108, V("warn"));
      T(p3, 56, PY + 100, "REPLY", 13, { fill: V("warn"), "font-weight": 700, "letter-spacing": "1.5" });
      setLines(lines(p3, 56, PY + 122, 2, 13, {}), summary, 118);
      T(p3, 56, PY + 170, badge, 13, { class: "mono", fill: V("lime"), "font-weight": 700 });

      // 4: trials, with controls
      const p4 = panel();
      const CASES = Object.keys(R);
      T(p4, 40, PY + 10, `CASE · ${N} TRIALS EACH`, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.5" });
      T(p4, 250, PY + 10, "note in context", 13, { fill: V("muted"), "font-weight": 700 });
      T(p4, 420, PY + 10, "Riley’s task done", 13, { fill: V("teal"), "font-weight": 700 });
      T(p4, 680, PY + 10, "note obeyed", 13, { fill: V("bad"), "font-weight": 700 });
      const trEls = CASES.map((c, i) => {
        const y = PY + 22 + i * 27, r = R[c], g = S("g", {}, p4);
        T(g, 40, y + 16, LABEL[c] || c, 14, { "font-weight": 700, fill: V(r.in_context ? "bad" : "ink") });
        T(g, 250, y + 16, r.in_context ? "yes" : "no", 13, { class: "mono", fill: V(r.in_context ? "bad" : "ok"), "font-weight": 700 });
        S("rect", { x: 420, y: y + 4, width: 200, height: 16, rx: 5, fill: V("line"), opacity: .5 }, g);
        S("rect", { x: 680, y: y + 4, width: 200, height: 16, rx: 5, fill: V("line"), opacity: .5 }, g);
        const bt = S("rect", { x: 420, y: y + 4, width: 0, height: 16, rx: 5, fill: V("teal") }, g);
        const bo = S("rect", { x: 680, y: y + 4, width: 0, height: 16, rx: 5, fill: V("bad") }, g);
        T(g, 628, y + 17, `${r.task}/${r.n}`, 13, { class: "mono", "font-weight": 700 });
        T(g, 888, y + 17, `${r.obeyed}/${r.n}`, 13, { class: "mono", "font-weight": 700 });
        return { g, bt, bo, kt: r.task / r.n, ko: r.obeyed / r.n };
      });

      const chunk = (s, n) => String(s).match(new RegExp(`.{1,${n}}`, "g")) || [];
      const hard = (p, x, y, s, n, k, o) => chunk(s, n).slice(0, k).forEach((t, i) => T(p, x, y + i * 18, t, 13, o));
      const bar = (p, x, y, w, k, role, txt) => {
        S("rect", { x, y, width: w, height: 16, rx: 5, fill: V("line"), opacity: .5 }, p);
        T(p, x + w + 8, y + 13, txt, 13, { class: "mono", "font-weight": 700 });
        return { r: S("rect", { x, y, width: 0, height: 16, rx: 5, fill: V(role) }, p), w: w * k };
      };

      // 5: the image loads
      const p5 = panel();
      card(p5, 40, PY + 6, 270, 136, V("lime"));
      T(p5, 56, PY + 30, "IN THE REPLY", 13, { fill: V("lime"), "font-weight": 700, "letter-spacing": "1.5" });
      hard(p5, 56, PY + 54, badge, 30, 5, { class: "mono", fill: V("lime") });
      card(p5, 340, PY + 6, 280, 136, V("warn"));
      T(p5, 356, PY + 30, "RENDERER LOADS IT", 13, { fill: V("warn"), "font-weight": 700, "letter-spacing": "1.5" });
      T(p5, 356, PY + 56, `${H.method} ${H.path}`, 13, { class: "mono", "font-weight": 700 });
      T(p5, 356, PY + 76, `?${H.query}`, 13, { class: "mono", fill: V("lime"), "font-weight": 700 });
      T(p5, 356, PY + 104, "user-agent", 13, { fill: V("muted") });
      T(p5, 356, PY + 124, H.user_agent, 13, { class: "mono" });
      card(p5, 650, PY + 6, 280, 136, V("bad"));
      T(p5, 666, PY + 30, "COLLECTOR LOG", 13, { fill: V("bad"), "font-weight": 700, "letter-spacing": "1.5" });
      T(p5, 666, PY + 56, `atlas-app: ${frac(D.trials_inbox.exfil)} trials`, 14, { "font-weight": 700 });
      T(p5, 666, PY + 80, `Open WebUI: ${owK}/${owN} replies`, 14, { "font-weight": 700 });
      T(p5, 666, PY + 108, "on the compose network only", 13, { fill: V("muted") });
      for (const x of [314, 624]) S("path", { d: `M${x} ${PY + 74} H${x + 20}`, stroke: V("dim"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, p5);
      T(p5, 40, PY + 172, `The model wrote text. The app made the request that carried ${CAN}.`, 14, { fill: V("muted") });

      // 6: the email it sends
      const p6 = panel();
      card(p6, 40, PY + 6, 270, 104, V("bad"));
      T(p6, 56, PY + 30, "INVOICE EMAIL", 13, { fill: V("bad"), "font-weight": 700, "letter-spacing": "1.5" });
      T(p6, 56, PY + 54, "m-invoice", 14, { class: "mono", "font-weight": 700 });
      T(p6, 56, PY + 76, "hidden note: ingested,", 13, { fill: V("bad") });
      T(p6, 56, PY + 94, "not visible", 13, { fill: V("bad") });
      card(p6, 340, PY + 6, 590, 104, V("lime"));
      T(p6, 356, PY + 30, "OUTBOX · SENT WITHOUT ASKING", 13, { fill: V("lime"), "font-weight": 700, "letter-spacing": "1.5" });
      [["to", NORTH.to, "ink"], ["subject", NORTH.subject, "ink"], ["body", NORTH.body, "lime"]].forEach(([k, v, role], i) => {
        T(p6, 356, PY + 54 + i * 20, k, 13, { fill: V("muted") });
        T(p6, 440, PY + 54 + i * 20, v, 13, { class: "mono", fill: V(role), "font-weight": 700 });
      });
      S("path", { d: `M314 ${PY + 58} H334`, stroke: V("dim"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, p6);
      const ea = AR["email-action"], rr = AR["reply-request"];
      T(p6, 40, PY + 138, "sent to Northwind", 13, { fill: V("muted"), "font-weight": 700 });
      T(p6, 340, PY + 138, "with the canary", 13, { fill: V("muted"), "font-weight": 700 });
      T(p6, 640, PY + 138, "reply to Priya works", 13, { fill: V("muted"), "font-weight": 700 });
      const actBars = [bar(p6, 40, PY + 150, 200, ea.attacker_sent / N, "bad", `${ea.attacker_sent}/${N}`),
        bar(p6, 340, PY + 150, 200, ea.attacker_sent_canary / N, "lime", `${ea.attacker_sent_canary}/${N}`),
        bar(p6, 640, PY + 150, 200, rr.task / N, "teal", `${rr.task}/${N}`)];

      // 7: spotlighting, before and after
      const p7 = panel();
      card(p7, 40, PY + 6, 890, 58, V("ok"));
      T(p7, 56, PY + 28, '<document source="m-offsite">', 13, { class: "mono", fill: V("ok"), "font-weight": 700 });
      T(p7, 56, PY + 50, D.offsite_visible[1].split(" ").slice(0, 12).join("^") + "^…", 13, { class: "mono" });
      T(p7, 40, PY + 88, "BASELINE", 13, { fill: V("bad"), "font-weight": 700, "letter-spacing": "1.5" });
      T(p7, 130, PY + 88, "SPOTLIGHT", 13, { fill: V("ok"), "font-weight": 700, "letter-spacing": "1.5" });
      const spRows = [["note obeyed", D.trials_inbox.obeyed, SP.obeyed],
        ["image with canary loaded", D.trials_inbox.exfil, SP.exfil],
        ["card sent to Northwind", [ea.attacker_sent_canary, N], [SP.actions["email-action"].attacker_sent_canary, N]]];
      const spEls = spRows.map(([name, b, a], i) => {
        const y = PY + 102 + i * 30;
        T(p7, 40, y + 13, name, 13, { "font-weight": 700 });
        return [bar(p7, 260, y, 240, b[0] / b[1], "bad", frac(b)), bar(p7, 590, y, 240, a[0] / a[1], "ok", frac(a))];
      });

      // 8: inert sinks
      const p8 = panel();
      card(p8, 40, PY + 6, 430, 180, V("ok"));
      T(p8, 56, PY + 30, `RENDERER · ${RD.auto.replies} REPLIES REPLAYED`, 13, { fill: V("ok"), "font-weight": 700, "letter-spacing": "1.5" });
      T(p8, 200, PY + 56, "images loaded", 13, { fill: V("muted"), "font-weight": 700 });
      T(p8, 330, PY + 56, "canary in text", 13, { fill: V("muted"), "font-weight": 700 });
      const rdRows = [["auto", RD.auto, "bad"], ["allowlist", RD.allowlist, "ok"]].map(([k, r, role], i) => {
        const y = PY + 84 + i * 36, g = S("g", {}, p8);
        T(g, 56, y, k, 14, { "font-weight": 700, fill: V(role) });
        T(g, 200, y, `${r.loaded}/${r.with_image}`, 14, { class: "mono", "font-weight": 700, fill: V(r.loaded ? "bad" : "ok") });
        T(g, 330, y, frac(r.canary), 14, { class: "mono", "font-weight": 700, fill: V("lime") });
        return g;
      });
      T(p8, 56, PY + 166, "the canary stays in the text Riley reads", 13, { fill: V("muted") });
      card(p8, 500, PY + 6, 430, 180, V("ok"));
      T(p8, 516, PY + 30, "CONFIRMATION DIALOG", 13, { fill: V("ok"), "font-weight": 700, "letter-spacing": "1.5" });
      T(p8, 680, PY + 56, "to Northwind", 13, { fill: V("muted"), "font-weight": 700 });
      T(p8, 810, PY + 56, "Priya reply", 13, { fill: V("muted"), "font-weight": 700 });
      const cfRows = Object.keys(CF).map((k, i) => {
        const y = PY + 84 + i * 32, r = CF[k], g = S("g", {}, p8);
        T(g, 516, y, k, 14, { "font-weight": 700, fill: V(r.northwind ? "bad" : "ok") });
        T(g, 680, y, `${r.northwind}/${r.trials}`, 14, { class: "mono", "font-weight": 700, fill: V(r.northwind ? "bad" : "ok") });
        T(g, 810, y, frac(r.reply), 14, { class: "mono", "font-weight": 700, fill: V("teal") });
        return g;
      });

      // 9: quarantine and the evaluation table
      const p9 = panel();
      const conds = Object.keys(EV);
      T(p9, 40, PY + 8, `EVALUATE · ${D.eval_trials} TRIALS PER CASE`, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.5" });
      [["note obeyed", 360], ["harm", 560], ["Riley’s tasks", 760]].forEach(([s, x]) =>
        T(p9, x, PY + 8, s, 13, { "text-anchor": "middle", fill: V("muted"), "font-weight": 700 }));
      const evRows = conds.map((c, i) => {
        const y = PY + 16 + i * 28, r = EV[c], g = S("g", {}, p9);
        T(g, 40, y + 17, c, 14, { "font-weight": 700, fill: V(c === "quarantine" ? "ok" : "ink") });
        [[360, r.obeyed, "bad", false], [560, r.harm, "bad", false], [760, r.utility, "teal", true]].forEach(([x, [a, b], role, good]) => {
          const on = good ? a === b : a === 0;
          const col = good ? (on ? "teal" : "warn") : (on ? "ok" : role);
          S("rect", { x: x - 70, y: y + 3, width: 140, height: 20, rx: 6, fill: V(col), "fill-opacity": .14, stroke: V(col), "stroke-width": 1 }, g);
          T(g, x, y + 18, `${a}/${b}`, 13, { "text-anchor": "middle", class: "mono", "font-weight": 700, fill: V(col) });
        });
        if (r.gate) T(g, 850, y + 18, "passes the gate", 13, { fill: V("ok"), "font-weight": 700 });
        return g;
      });

      // ---------------------------------------------------------------- state
      const base0 = { p1: 0, p2: 0, p3: 0, p4: 0, p5: 0, p6: 0, p7: 0, p8: 0, p9: 0,
        atk: 0, ret: 0, rep: 0, img: 0, act: 0, spot: 0, allow: 0, conf: 0, quar: 0, hot: "" };
      const ON = { atk: 1, ret: 1, rep: 1 };
      const T_N = [null,
        { p1: 1 },                                                        // 1 System: Riley's inbox
        { atk: 1, p2: 1, hot: "mail" },                                   // 2 Attack: a hidden note
        { ...ON, p3: 1, hot: "ctx,llm" },                                 // 3 Mechanism: one summary
        { ...ON, p4: 1, hot: "llm,app" },                                 // 4 Mechanism: only if ingested
        { ...ON, img: 1, p5: 1, hot: "app" },                             // 5 Impact: the badge loads
        { ...ON, img: 1, act: 1, p6: 1, hot: "mail,app" },                // 6 Impact: the email it sends
        { ...ON, img: 1, act: 1, spot: 1, p7: 1, hot: "ctx" },            // 7 Defense: spotlighting
        { ...ON, img: 1, act: 1, allow: 1, conf: 1, p8: 1, hot: "app" },  // 8 Defense: inert sinks
        { ...ON, img: 1, act: 1, quar: 1, p9: 1, hot: "ctx,llm" },        // 9 Defense: quarantine
      ];
      const target = n => ({ ...base0, ...T_N[n] });
      const st = { ...base0 };
      const GROUPS = { mail: gMail, ctx: gCtx, llm: gLLM, app: gApp };
      const op = v => (+v).toFixed(3);
      const tint = (r, role, k = .1) => A(r, { fill: V(role), "fill-opacity": k, stroke: V(role) });

      function draw(s) {
        const atk = s.atk > .5, ret = s.ret > .5, rep = s.rep > .5, img = s.img > .5, act = s.act > .5;
        const spot = s.spot > .5, allow = s.allow > .5, conf = s.conf > .5, quar = s.quar > .5;

        // mailbox: the poisoned items light up once the attack is shown
        mailEls.forEach(m => { const role = m.pois && atk ? "bad" : "teal"; tint(m.r, role, .08); A(m.t, { fill: V(role) }); });

        // context window
        tint(bSys.r, "teal");
        bSys.sub.textContent = quar ? "reader: no private value" : "card: " + CAN;
        A(bSys.sub, { fill: V(quar ? "ok" : "lime"), "font-weight": 700 });
        tint(bReq.r, "teal");
        bReq.sub.textContent = ret ? wrap(D.s02.ask, 30)[0] + " …" : "what Riley typed";
        A(bReq.sub, { fill: V(ret ? "teal" : "muted") });
        tint(bDoc.r, spot ? "ok" : ret ? "bad" : "teal", .06 + .06 * s.ret);
        bDoc.sub.textContent = spot ? '<document> data^marked' : ret ? D.s02.retrieved.slice(0, 2).join(" ") + " …" : "pieces of her mail";
        A(bDoc.sub, { fill: V(spot ? "ok" : "muted"), class: ret ? "mono" : "" });
        tint(noteR, "bad", .14);
        A(noteR, { opacity: op(s.ret) }); A(noteT, { opacity: op(s.ret), fill: V("bad") }); A(noteS, { opacity: op(s.ret) });
        noteS.textContent = spot ? "marked as data, still read" : quar ? "read by the reader only" : `${OFF.ingested - OFF.visible} chars Riley never saw`;
        A(noteS, { fill: V(spot || quar ? "ok" : "bad") });

        // model
        mRole.textContent = quar ? "reader model" : rep ? "obeys the note" : "reads it all";
        mSub.textContent = quar ? "no secrets, no tools" : rep ? "and does the task" : "as one input";
        A(mRole, { fill: V(quar ? "ok" : rep ? "bad" : "violet") });

        // inbox app
        tint(repR, rep ? "warn" : "muted", .08);
        setLines(repT, rep ? summary : "waits for a request", 28);
        repT.forEach(t => A(t, { fill: V(rep ? "ink" : "muted") }));
        repB.textContent = !rep ? "" : quar ? "badge, no private value" : "ref=" + CAN;
        A(repB, { fill: V(quar ? "ok" : "lime") });
        const ren = !img ? ["loads every image", "muted"] : allow ? ["image not loaded", "ok"] : quar ? ["shown as plain text", "ok"] : [`GET ${H.path}`, "lime"];
        cRen.sub.textContent = ren[0]; A(cRen.sub, { fill: V(ren[1]), "font-weight": img ? 700 : 400 }); tint(cRen.r, ren[1] === "muted" ? "line" : ren[1], .1);
        const snd = !act ? ["runs ACTION lines", "muted"] : conf ? ["asks Riley first", "ok"] : quar ? ["reader cannot act", "ok"] : ["→ " + NORTH.to.split("@")[1], "bad"];
        cSend.sub.textContent = snd[0]; A(cSend.sub, { fill: V(snd[1]), "font-weight": act ? 700 : 400 }); tint(cSend.r, snd[1] === "muted" ? "line" : snd[1], .1);

        // panels
        [p1, p2, p3, p4, p5, p6, p7, p8, p9].forEach((p, i) => A(p, { opacity: op(s["p" + (i + 1)]) }));
        trEls.forEach((t, i) => {
          const k = E.out(seg(s.p4, .15 + i * .05, .65 + i * .05));
          A(t.bt, { width: (200 * t.kt * k).toFixed(2) }); A(t.bo, { width: (200 * t.ko * k).toFixed(2) });
        });
        actBars.forEach(b => A(b.r, { width: (b.w * E.out(seg(s.p6, .2, 1))).toFixed(2) }));
        spEls.forEach(([b0, b1]) => {
          A(b0.r, { width: b0.w.toFixed(2) });
          A(b1.r, { width: (b1.w * E.out(seg(s.p7, .3, 1))).toFixed(2) });
        });
        rdRows.concat(cfRows).forEach((g, i) => A(g, { opacity: op(seg(s.p8, .1 + i * .08, .45 + i * .08)) }));
        evRows.forEach((g, i) => A(g, { opacity: op(seg(s.p9, .1 + i * .08, .4 + i * .08)) }));

        // focus + context
        const hot = s.hot ? s.hot.split(",").map(k => GROUPS[k]) : null;
        [gMail, gCtx, gLLM, gApp, gFlow].forEach(g => g.classList.toggle("hot", !!hot && hot.includes(g)));
        el.classList.toggle("lx-focus", !!hot);
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          return api.tween(n === 4 || n === 9 ? 900 : 700, k => { if (g !== gen) return; X.lerpState(st, from, to, X.clamp(k)); draw(st); }, E.inOut);
        },
      };
    },
  });
})();
