/* LAB-20 attack-output-sink: "Your model's output is someone else's input" (8 steps,
 * System -> Attack -> Mechanism -> Impact -> Defense). The stage has one MODEL OUTPUT card on the
 * left and two sinks on the right: a SQL analytics helper (sqlite3) and a help-desk page that renders
 * HTML. The same model output flows into a sink and acts with the sink's authority. Every string and
 * number comes from window.LAB_DATA (data.js, exported by scripts/export_explainer_data.py).
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one step only. No hex colors. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp;
  const D = window.LAB_DATA;
  const CAN = D.canary;
  const inj = D.sql.sql_direct;                 // the injected text-to-SQL output
  const htmlLeaks = D.html.leaks.length;
  const ev = D.evaluate;

  X.define({
    id: "attack-output-sink",
    family: "family-agent",
    title: "Your model's output is someone else's <span class=\"outline\">input</span>",
    legend: [{ role: "warn", label: "Model output" }, { role: "bad", label: "Injected / unsafe" },
      { role: "teal", label: "Trusted data" }, { role: "violet", label: "The sink" },
      { role: "lime", label: "Canary" }, { role: "ok", label: "Defense" }],
    intro: {
      why: "A model’s reply often goes further than the screen. Many apps run it as a database query or render it as a web page. What happens when that reply is treated as trusted code? This lab looks at an analytics helper and a help-desk page that do exactly that.",
      plan: "You’ll send a question, watch the app run the model’s SQL and render its HTML, and see a private value leave through each path. No jailbreak is needed, because the flaw is in the app. Then you’ll validate the SQL, encode the HTML and isolate the execution, and measure what each one stops.",
      terms: "SQL is the language used to query a database. A sink is wherever model output ends up being used: a database, a browser, a shell. A canary is a harmless fixed marker that stands in for secret data, so a leak shows up without real harm. An allowlist accepts only known-safe forms and rejects everything else."
    },
    steps: [
      { chapter: "System", label: "Two sinks",
        guide: "Start with the app working normally. A customer’s question turns into a database query that the app runs, and the model’s answer turns into HTML that the page shows. So the model’s words get executed and rendered, which is more than being displayed. Any place where output is used that way is a sink.",
        caption: `The analytics helper runs the model's SQL against <code>sqlite3</code>; the help-desk page renders its HTML. A benign question gives benign SQL: <code>${D.benign.sql}</code> returns ${D.benign.rows.length} ordinary rows.`,
        cmd: "docker compose run --rm workbench python attack-output-sink/scripts/s01_app.py" },
      { chapter: "System", label: "The secret table",
        guide: "The database has a table the model is never told about, and it holds a private value. The analytics connection can still read every table. Keep that gap in mind. The prompt describes a few tables, while the connection can reach all of them.",
        caption: `Tables: <span class="c-teal">${D.allowed.join(", ")}</span> (in the prompt) and <span class="c-bad">${D.hidden.join(", ")}</span> (not in the prompt). The <span class="c-lime">canary</span> <code class="c-lime">${CAN}</code> lives in <code>secrets</code>, which the live connection can still reach.` },
      { chapter: "Attack", label: "A question, a query",
        guide: "Now a request leads the model to write a query that also reads the hidden table. The push can come from the customer’s own question, or from a poisoned product review that the helper reads as context. Either way, the model produces a query the app will run.",
        caption: `A question (or a poisoned review in the helper's context) yields <span class="c-bad">${inj.sql.replace(/\n/g, " ")}</span>. The model was told only about ${D.allowed.join(" and ")}; leaving a table out of the prompt does not stop the <code>UNION</code> from reaching it.` },
      { chapter: "Mechanism", label: "Run verbatim",
        guide: "The app takes the model’s text and runs it exactly as written. Nothing checks that the query stays inside the allowed tables. This is where the app goes wrong: it treats generated text as a trusted command.",
        caption: `The helper executes the reply verbatim on a connection that can see every table. Nothing at the <span class="c-violet">sink</span> asks whether a customer's question should be allowed to read <code>secrets</code>.` },
      { chapter: "Impact", label: "The canary row",
        guide: "The query runs and returns a row from the hidden table. The private value, here a harmless canary, comes back in the result the customer sees. The query ran with the database connection’s full access, so the model’s output could read anything that connection can.",
        caption: `The result now includes <code class="c-lime">${CAN}</code>, the inert canary standing in for the secret. Model output that followed the request, run at the sink, leaked a row the customer was never allowed to read.`,
        cmd: "docker compose run --rm workbench python attack-output-sink/scripts/s02_sql_sink.py" },
      { chapter: "Impact", label: "Output becomes a request",
        guide: "The second sink is the web page. The help-desk reply contains an image tag whose address carries a private value. When a browser renders the reply, it fetches that address, and the value goes to whoever runs that server. Text the model wrote has turned into a request to someone else’s machine.",
        caption: `The rendered reply makes ${htmlLeaks} outgoing request(s) to <code>${D.collector}</code> carrying <code class="c-lime">${CAN}</code>. The collector is never contacted here; the request itself is the inert leak. A <code>&lt;script&gt;</code> would run too.`,
        cmd: "docker compose run --rm workbench python attack-output-sink/scripts/s03_html_sink.py" },
      { chapter: "Defense", label: "Validate, encode",
        guide: "The fix is to treat output as untrusted at every sink. For SQL, parse the query and accept only a single read of the allowed tables. For HTML, keep plain formatting and strip anything that loads or runs. Normal answers still work, and the injected ones are rejected.",
        caption: `<span class="c-ok">D1</span>: a <code>sqlglot</code> allowlist (one SELECT, allowed tables only) rejects the read of <code>secrets</code> before it runs. <span class="c-ok">D2</span>: <code>bleach</code> drops the image and script, so the HTML leaks fall from ${D.d2.before.leaks} to ${D.d2.after.leaks}.`,
        cmd: "docker compose run --rm workbench python attack-output-sink/scripts/d1_sql_allowlist.py" },
      { chapter: "Defense", label: "Contain and measure",
        guide: "Validation can have gaps, so also contain the execution. Running the query in an isolated service with no network and a read-only filesystem stops writes and outgoing connections. A plain read still returns the canary, though. Isolation limits the damage but doesn’t stop the leak, so measure every sink.",
        caption: `<span class="c-ok">D3</span>: in the sandbox the write and the egress are blocked, yet the read still fires (${CAN}) — containment, not prevention. Evaluate: <code>${ev["sql-naive"]}</code>/<code>${ev["sql-allowlist"]}</code> for SQL, <code>${ev["html-naive"]}</code>/<code>${ev["html-sanitized"]}</code> for HTML.`,
        cmd: "docker compose run --rm workbench python attack-output-sink/scripts/evaluate.py" },
    ],
    html: `<style>[data-explainer="attack-output-sink"] svg text, [data-explainer="attack-output-sink"] code { font-variant-ligatures: none; }</style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Model output flowing into a SQL sink and an HTML sink, with defenses"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 14, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 12, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.5", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) =>
        S("rect", { x, y, width: w, height: h, rx: 12, fill: V("panel"), stroke, "stroke-width": 1.8, ...o }, p);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow"), badArrowId = api.uid("badarrow");
      for (const [id, col] of [[arrowId, "dim"], [badArrowId, "bad"]]) {
        const mk = S("marker", { id, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto" }, defs);
        S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V(col) }, mk);
      }
      function wrap(s, n) {
        const out = []; let line = "";
        for (const w of String(s).split(" ").flatMap(t => t.match(new RegExp(`.{1,${n}}`, "g")) || [t])) {   // split over-long tokens (URLs)
          if ((line + " " + w).trim().length > n && line) { out.push(line); line = w; } else line = (line + " " + w).trim();
        }
        if (line) out.push(line);
        return out;
      }
      const lines = (p, x, y, arr, size, dy, o = {}) => arr.map((l, i) => T(p, x, y + i * dy, l, size, o));

      // ---------------------------------------------------------------- MODEL OUTPUT card (left)
      const gModel = S("g", { class: "dimmable" }, svg);
      label(gModel, 40, 52, "MODEL OUTPUT");
      const mBox = card(gModel, 40, 64, 300, 180, V("warn"));
      const mQ = T(gModel, 56, 92, "", 13, { fill: V("muted") });
      const mText = S("g", {}, gModel);           // the SQL / HTML body, rebuilt by draw
      const mTag = T(gModel, 56, 232, "", 12, { class: "mono", "font-weight": 700 });

      // flow from the model card to the sinks
      const flowSql = S("path", { d: "M340 120 H392", stroke: V("warn"), "stroke-width": 5, "marker-end": `url(#${arrowId})`, fill: "none" }, svg);
      const flowHtml = S("path", { d: "M340 196 H392", stroke: V("warn"), "stroke-width": 5, "marker-end": `url(#${arrowId})`, fill: "none" }, svg);

      // ---------------------------------------------------------------- SQL SINK (top right)
      const gSql = S("g", { class: "dimmable" }, svg);
      label(gSql, 400, 52, "SQL SINK · analytics helper + sqlite3");
      card(gSql, 400, 64, 520, 190, V("violet"));
      const TABLES = D.tables, tChips = {};
      TABLES.forEach((t, i) => {
        const x = 420 + i * 120, allowed = D.allowed.includes(t), g = S("g", {}, gSql);
        const r = S("rect", { x, y: 84, width: 108, height: 40, rx: 9, fill: V(allowed ? "teal" : "bad"), "fill-opacity": .14, stroke: V(allowed ? "teal" : "bad"), "stroke-width": 1.6 }, g);
        T(g, x + 54, 100, t, 12, { "text-anchor": "middle", class: "mono", "font-weight": 700, fill: V(allowed ? "teal" : "bad") });
        const sub = T(g, x + 54, 116, allowed ? "in prompt" : "hidden", 11, { "text-anchor": "middle", fill: V("muted") });
        tChips[t] = { g, r, can: t === "secrets" ? sub : null };   // the secrets chip's sub-label shows the canary
      });
      label(gSql, 420, 150, "RESULT RETURNED TO THE CUSTOMER");
      const sqlRows = S("g", {}, gSql);
      const sqlCanRow = T(gSql, 420, 232, "", 13, { class: "mono", "font-weight": 800, fill: V("lime") });
      // allowlist gate (D1) across the SQL flow
      const gAllow = S("g", {}, svg);
      const allowBar = S("rect", { x: 366, y: 84, width: 8, height: 0, rx: 4, fill: V("ok") }, gAllow);
      const allowTxt = T(gAllow, 358, 274, "", 12, { "text-anchor": "end", fill: V("ok"), "font-weight": 700 });
      // sandbox wall (D3) around the SQL sink
      const sandWall = S("rect", { x: 394, y: 58, width: 532, height: 202, rx: 16, fill: "none", stroke: V("ok"), "stroke-width": 0, "stroke-dasharray": "6 5" }, svg);
      const sandTxt = T(svg, 910, 50, "", 12, { "text-anchor": "end", fill: V("ok"), "font-weight": 700 });

      // ---------------------------------------------------------------- HTML SINK (bottom right)
      const gHtml = S("g", { class: "dimmable" }, svg);
      label(gHtml, 400, 300, "HTML SINK · help-desk page the browser renders");
      card(gHtml, 400, 312, 340, 200, V("violet"));
      S("rect", { x: 400, y: 312, width: 340, height: 26, rx: 12, fill: V("violet"), "fill-opacity": .12 }, gHtml);
      T(gHtml, 416, 330, "help-desk · ticket reply", 12, { fill: V("muted") });
      const htmlBody = S("g", {}, gHtml);
      const pixel = S("rect", { x: 700, y: 352, width: 18, height: 18, rx: 3, fill: V("bad"), "fill-opacity": .25, stroke: V("bad"), "stroke-width": 1.4, opacity: 0 }, gHtml);
      // outgoing request to the collector
      const gReq = S("g", {}, svg);
      const reqPath = S("path", { d: "M740 412 H852", stroke: V("bad"), "stroke-width": 4, "marker-end": `url(#${badArrowId})`, fill: "none", opacity: 0 }, gReq);
      const collector = S("g", { opacity: 0 }, gReq);
      card(collector, 772, 384, 150, 56, V("bad"));
      T(collector, 847, 406, "collector", 12, { "text-anchor": "middle", class: "mono", "font-weight": 700, fill: V("bad") });
      const reqCan = T(collector, 847, 424, "", 11, { "text-anchor": "middle", class: "mono", "font-weight": 800, fill: V("lime") });
      // bleach gate (D2)
      const gBleach = S("g", {}, svg);
      const bleachBar = S("rect", { x: 744, y: 392, width: 8, height: 0, rx: 4, fill: V("ok") }, gBleach);
      const bleachTxt = T(gBleach, 734, 500, "", 12, { "text-anchor": "end", fill: V("ok"), "font-weight": 700 });

      // evaluation badge (step 8)
      const gEval = S("g", { opacity: 0 }, svg);
      card(gEval, 40, 300, 300, 212, V("ok"));
      label(gEval, 56, 330, "EVALUATE · each sink, each defense");
      const EVR = [["sql, no check", ev["sql-naive"], "bad"], ["sql + allowlist", ev["sql-allowlist"], "ok"],
        ["html, no check", ev["html-naive"], "bad"], ["html + bleach", ev["html-sanitized"], "ok"]];
      EVR.forEach(([k, val, col], i) => {
        const y = 356 + i * 34;
        T(gEval, 56, y, k, 13, {});
        T(gEval, 324, y, val, 13, { "text-anchor": "end", class: "mono", "font-weight": 800, fill: V(col) });
      });

      // ---------------------------------------------------------------- state
      const KEYS = ["mode", "secret", "inject", "exec", "canary", "leak", "allow", "bleach", "sand", "evalShow", "htmlHot", "sqlHot"];
      const st = {}; KEYS.forEach(k => st[k] = 0);
      // mode 0 = benign SQL shown, 1 = injected SQL shown, 2 = HTML shown
      const T_N = [null,
        { mode: 0, exec: 1, sqlHot: 1 },                                  // 1 System: benign SQL + result
        { mode: 0, secret: 1, sqlHot: 1 },                               // 2 System: the secret table
        { mode: 1, inject: 1, sqlHot: 1 },                               // 3 Attack: injected query
        { mode: 1, inject: 1, exec: 1, sqlHot: 1 },                      // 4 Mechanism: run verbatim
        { mode: 1, inject: 1, exec: 1, canary: 1, sqlHot: 1 },           // 5 Impact: canary row
        { mode: 2, leak: 1, htmlHot: 1 },                                // 6 Impact: html request
        { mode: 1, inject: 1, allow: 1, bleach: 1 },                     // 7 Defense: validate + encode
        { mode: 1, exec: 1, canary: 1, sand: 1, evalShow: 1 },           // 8 Defense: contain + measure (the read still fires)
      ];
      const target = n => { const s = {}; KEYS.forEach(k => s[k] = 0); return Object.assign(s, T_N[n]); };

      const clip = (q, n = 42) => q.length > n ? q.slice(0, n - 1).trimEnd() + "…" : q;   // fit the 300 px card
      function setText(g, arr, x, y, size, dy, o) {
        g.textContent = ""; lines(g, x, y, arr, size, dy, o);
      }

      function draw(s) {
        // ---- model output card content by mode
        const injected = s.mode === 1;
        if (s.mode === 2) {
          mQ.textContent = clip(D.html.question);
          setText(mText, wrap(D.html.reply.replace(/\s+/g, " "), 40).slice(0, 6), 56, 116, 12, 17, { fill: V("warn") });
          mTag.textContent = "rendered as HTML";
          A(mTag, { fill: V("warn") });
          A(mBox, { stroke: V("warn") });
        } else {
          mQ.textContent = clip(injected ? inj.question : D.benign.question);
          const sql = (injected ? inj.sql : D.benign.sql).split("\n").flatMap(l => wrap(l, 34));   // fit the card
          setText(mText, sql, 56, 120, 13, 22, { class: "mono", fill: V(injected ? "bad" : "warn"), "font-weight": injected ? 700 : 400 });
          mTag.textContent = injected ? "SELECT ... UNION SELECT ... secrets" : "one SELECT, allowed tables";
          A(mTag, { fill: V(injected ? "bad" : "teal") });
          A(mBox, { stroke: V(injected ? "bad" : "warn") });
        }
        // flows
        A(flowSql, { opacity: (s.mode !== 2 ? 1 : .12) * (1 - .85 * s.allow), stroke: V(injected ? "bad" : "warn"), "marker-end": `url(#${injected && !s.allow ? badArrowId : arrowId})` });
        A(flowHtml, { opacity: s.mode === 2 ? 1 : .12, stroke: V(s.mode === 2 ? "warn" : "dim") });

        // ---- SQL table chips: the secret value shows when secret or canary is set
        const showCan = Math.max(s.secret, s.canary);
        if (tChips.secrets.can) {
          tChips.secrets.can.textContent = showCan > .5 ? CAN : "hidden";
          A(tChips.secrets.can, showCan > .5
            ? { fill: V("lime"), class: "mono", "font-weight": 800, "font-size": 10 }
            : { fill: V("muted"), class: "", "font-weight": 400, "font-size": 11 });
          A(tChips.secrets.r, { "stroke-width": 1.6 + 1.8 * showCan });
        }
        // ---- SQL result rows
        let rowsArr = [];
        if (s.exec) {
          const data = injected ? inj : D.benign;
          rowsArr = data.rows.map(r => r.join(" · "));
        }
        setText(sqlRows, rowsArr.filter(r => !r.includes(CAN)).slice(0, 3), 420, 172, 12, 18, { class: "mono", fill: V("ink") });
        sqlCanRow.textContent = s.canary > .5 ? (inj.rows.find(r => r.join(" ").includes(CAN)) || []).join(" · ") : "";
        A(sqlCanRow, { opacity: seg(s.canary, .2, 1) });

        // ---- allowlist gate (D1)
        A(allowBar, { height: (190 * s.allow).toFixed(1) });
        allowTxt.textContent = s.allow > .5 ? "allowlist: secrets rejected" : "";
        A(allowTxt, { opacity: seg(s.allow, .5, 1) });

        // ---- sandbox wall (D3)
        A(sandWall, { "stroke-width": (2.4 * s.sand).toFixed(2) });
        sandTxt.textContent = s.sand > .5 ? "sandbox: no network, read-only" : "";
        A(sandTxt, { opacity: seg(s.sand, .5, 1) });

        // ---- HTML sink body + leak request
        const hb = s.mode === 2
          ? ["Thanks for reaching out about your", "Orbit desk lamp. Reset it by holding", "the switch for five seconds.", "", "[img] tracking pixel", "[script] confirm.js"]
          : ["(the help-desk reply renders here)"];
        setText(htmlBody, hb, 416, 360, 12, 20, { fill: V(s.mode === 2 ? "ink" : "muted") });
        A(pixel, { opacity: s.mode === 2 ? 1 : 0 });
        const leakLive = s.leak * (1 - s.bleach);
        A(reqPath, { opacity: leakLive });
        A(collector, { opacity: leakLive });
        reqCan.textContent = leakLive > .5 ? "ref=" + CAN : "";
        // ---- bleach gate (D2)
        A(bleachBar, { height: (120 * s.bleach).toFixed(1) });
        bleachTxt.textContent = s.bleach > .5 ? "bleach: image + script stripped" : "";
        A(bleachTxt, { opacity: seg(s.bleach, .5, 1) });

        // ---- evaluation badge
        A(gEval, { opacity: s.evalShow });

        // ---- focus / context
        const focusSql = s.sqlHot > .5, focusHtml = s.htmlHot > .5;
        gSql.classList.toggle("hot", focusSql);
        gModel.classList.toggle("hot", focusSql || focusHtml);
        gHtml.classList.toggle("hot", focusHtml);
        el.classList.toggle("lx-focus", focusSql || focusHtml);
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
