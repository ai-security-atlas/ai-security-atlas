/* LAB-59 system-tools: "What a tool really exposes" (9 steps).
 * One scene: the model's context, the MCP server with two logical servers, the resources they reach,
 * and the current call with its five surfaces. Every number and string from a run comes from LAB_DATA.
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v;
  const D = window.LAB_DATA;
  const frac = (p) => `${p[0]}/${p[1]}`;
  const CMD = (s) => `COMPOSE_PROJECT_NAME=atlas-labs-system-tools ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8231 docker compose run --rm workbench python system-tools/scripts/${s}.py`;
  const tool = (name) => D.s01.tools.find((t) => t.name === name) || { description: "", chars: 0, params: "", sha: "" };
  const probe = (list, path) => list.find((p) => p.path === path) || {};
  const ret = D.s02.returns.calls[0] || {};
  const inv = D.s02.own_invoice.calls[0] || {};
  const UNCHECKED = ["none", "type only", "not bound to user"];
  const yes = (b) => (b ? "yes" : "no");
  const p04 = (list) => probe(list, "../canary.txt");
  const d1Held = D.d1.probes.filter((p) => p.path !== "returns.md").every((p) => p.status !== 200 && !p.canary);
  const d3Refused = D.d3.edits.filter((e) => !e.accepted).length;

  X.define({
    id: "system-tools",
    family: "family-agent",
    title: 'What a tool really <span class="outline">exposes</span>',
    legend: [
      { role: "teal", label: "Help files and records", tag: "trusted-documents" },
      { role: "violet", label: "Model and MCP server", tag: "llm-agent" },
      { role: "bad", label: "Unchecked surface", tag: "attack-surface" },
      { role: "lime", label: "Canary" },
      { role: "ok", label: "Defense", tag: "access-control" },
    ],
    intro: {
      why: "A help-desk assistant at a fictional store answers customers by calling tools. One tool reads a help file. Another looks up an invoice. Each tool looks like a single capability on the client panel. Underneath, a tool is five separate things: a description the model reads, the arguments the model fills in, the output that comes back, the identity the tool runs with, and whatever authorization the tool applies. You’ll watch each one, and watch the model turn two of them into a leak.",
      plan: "You’ll read the tool list the model receives and see the full description behind each short name. You’ll watch one normal run, call by call, then name the five surfaces. Next you’ll steer the file tool past its folder with a path the model chooses, and watch the billing tool read another customer’s record on one shared token. The tool-call log shows both. Then you fix them with a strict argument schema and a folder check, a per-user credential, and a reviewed definition pinned by hash.",
      terms: "A tool is a function the model can call. MCP (Model Context Protocol) is the protocol the assistant uses to list tools and call them; here one in-process MCP server, atlas-desk, serves a files group and a billing group. A tool description is the text the model reads to decide when to call the tool. A path-traversal argument is one like ../canary.txt that climbs out of the intended folder. A scope is the set of records a credential may read. A canary is a fixed marker planted in an out-of-scope file so a leak is visible and harmless; here it is " + D.canary + ".",
    },
    steps: [
      { chapter: "System", label: "The tool list",
        guide: "Every tool reaches the model as a name, a description and an argument schema. The client panel shows a short name. The model receives the full description and decides from that. Read the three tools this assistant has, and see which logical server each one belongs to. The files group reads help pages. The billing group looks up invoices.",
        caption: `MCP server <span class="c-violet">${D.s01.server}</span> protocol ${D.s01.protocol}. The model receives ${D.s01.tools.length} tools, ${D.s01.payload_chars} characters of JSON, plus a ${D.s01.prompt_chars}-character system prompt. <code>stools-read_file</code>: "${tool("stools-read_file").description}" (${tool("stools-read_file").chars} chars, <code>${tool("stools-read_file").params}</code>). Argument constraints beyond type: <span class="c-bad">${tool("stools-read_file").constraints.join(" ") || "none"}</span>.`,
        cmd: CMD("s01_list") },
      { chapter: "System", label: "One ordinary run",
        guide: "Here is the assistant doing its job. You ask for the return window, and it calls the file tool with the file name it chose. You ask for your own invoice total, and it calls the billing tool with your id. Watch the arguments: the model wrote them. Watch the identity line under each call: the tool, the token it carried and the record it reached.",
        caption: `Returns question: <code>${ret.tool}</code> with <code>${JSON.stringify(ret.arguments)}</code>, token <code>${ret.token}</code>, status ${ret.status}. Invoice question: <code>${inv.tool}</code> with <code>${JSON.stringify(inv.arguments)}</code>, token <span class="c-bad">${inv.token}</span> scope <code>${inv.scope}</code>. Right number in the reply: returns ${D.s02.returns.utility ? "yes" : "no"}, invoice ${D.s02.own_invoice.utility ? "yes" : "no"}.`,
        cmd: CMD("s02_run") },
      { chapter: "Attack", label: "Five surfaces",
        guide: "Pull the single call apart. The description came from whoever wrote the tool. The arguments came from the model. The output came from the tool and its data. The identity came from how the tool was configured. Authorization is the check that this caller may reach this record. On this desk the only check is the argument’s type. A type check says a path is a string. It says nothing about where the path leads.",
        caption: `What checks each surface here: ${D.s03.rows.map((r) => `${r.surface} <span class="${UNCHECKED.includes(r.check) ? "c-bad" : "c-ok"}">${r.check}</span>`).join(", ")}. The billing token is <code>${D.s03.other.token}</code>. Surfaces with no security check: <span class="c-bad">${D.s03.rows.filter((r) => UNCHECKED.includes(r.check)).length} of ${D.s03.rows.length}</span>.`,
        cmd: CMD("s03_surfaces") },
      { chapter: "Mechanism", label: "An argument that climbs out",
        guide: "The file tool joins the model’s argument onto the help folder and reads the result. Nothing checks where the joined path lands. A path that starts with ../ leaves the help folder. Sent straight in, it resolves to the out-of-scope file and returns the canary. When the help page itself points one folder up, the model follows the pointer and sends the climbing path on its own.",
        caption: `Direct probe <code>../canary.txt</code> resolved to <code>${(probe(D.s04.probes, "../canary.txt").resolved) || ""}</code>, status ${p04(D.s04.probes).status}, canary <span class="c-lime">${yes(p04(D.s04.probes).canary)}</span>. On the indirect task the model chose a <code>..</code> path in <span class="c-bad">${frac(D.s04.live.indirect.tried)}</span> live runs, and the canary was read in <span class="c-bad">${frac(D.s04.live.indirect.read)}</span>. The pointer in the help page: "${D.s04.pointer}".`,
        cmd: CMD("s04_path") },
      { chapter: "Mechanism", label: "One token for everyone",
        guide: "The billing tool holds one service credential that can read every customer’s invoices. The tool takes a customer id as a free argument and never checks it against who is signed in. You are alice. Ask for bob’s invoice and the tool returns it, carrying the canary planted in bob’s record. The model sometimes refuses on its own, but when it calls the tool, the tool answers.",
        caption: `Direct call as <code>${D.principal}</code> for <code>bob</code>: token <span class="c-bad">${D.s05.code.bob.token}</span> scope <code>${D.s05.code.bob.scope}</code>, status ${D.s05.code.bob.status}, canary <span class="c-lime">${yes(D.s05.code.bob.canary)}</span>. In live runs the model called billing for bob <span class="c-bad">${frac(D.s05.called)}</span>, and the canary came back in <span class="c-bad">${frac(D.s05.live.read)}</span>${D.s05.live.read[0] === D.s05.called[0] ? ", so every such call returned bob’s record" : ""}.`,
        cmd: CMD("s05_identity") },
      { chapter: "Impact", label: "The tool-call log",
        guide: "The desk keeps two kinds of log rows. An argument row records what the model chose. An identity row records the token, scope, resolved path and status of each tool call, including the direct probes. You do not need the model to find the problem. Three forensic rules over the identity rows flag it: a resolved path outside the help folder, a token wider than the signed-in user, and a record that belongs to a different customer.",
        caption: `Over Steps 4 and 5: ${D.s06.rows} identity rows and ${D.s06.agent_rows} argument rows. Flagged: path outside scope <span class="c-bad">${D.s06.flags["path-outside-scope"] || 0}</span>, token wider than principal <span class="c-bad">${D.s06.flags["token-wider-than-principal"] || 0}</span>, other customer’s record <span class="c-bad">${D.s06.flags["other-customer-record"] || 0}</span>. Rows with no flag: ${D.s06.clean}. The path and other-customer rows are the calls that handed <span class="c-lime">${D.canary}</span> to the model.`,
        cmd: CMD("s06_log") },
      { chapter: "Defense", label: "Shrink the arguments",
        guide: "The first fix narrows the argument surface. The strict file tool takes a bare file name. Its schema is a pattern that allows lowercase letters, digits, hyphens and a .md suffix. The tool also checks that the canonical path sits directly in the help folder. The MCP server rejects any argument that fails the pattern before the tool runs, so every climbing path is refused. The ordinary return-window question still works.",
        caption: `Schema pattern <code>${D.d1.pattern}</code>, max length ${D.d1.max_length}. Traversal probes refused: <span class="${d1Held ? "c-ok" : "c-bad"}">${d1Held ? "all" : "not all"}</span>, first stop <code>${p04(D.d1.probes).stopped_by}</code>. On the indirect task the model still tried <code>..</code> in ${frac(D.d1.live.indirect.tried)} live runs, and the canary was read <span class="c-ok">${frac(D.d1.live.indirect.read)}</span>. The return window answered <span class="c-ok">${frac(D.d1.live.returns.utility)}</span>.`,
        cmd: CMD("d1_schema") },
      { chapter: "Defense", label: "Give it only your key",
        guide: "The second fix changes the identity surface. The scoped billing tool drops the shared credential and uses the signed-in customer’s own token. Asked for bob’s invoice while you are alice, the tool now returns a refusal, because alice’s token covers only alice. Your own invoice still comes back. Least privilege means the credential cannot reach what the caller could not.",
        caption: `As <code>${D.principal}</code> for <code>bob</code>: token <code>${D.d2.code.bob.token}</code> scope <code>${D.d2.code.bob.scope}</code>, status <span class="c-ok">${D.d2.code.bob.status}</span>, canary ${D.d2.code.bob.canary ? "yes" : "no"}. Across ${D.d2.n} live runs the other-customer canary was read <span class="c-ok">${frac(D.d2.live.other_invoice.read)}</span>, and alice’s own total answered <span class="c-ok">${frac(D.d2.live.own_invoice.utility)}</span>.`,
        cmd: CMD("d2_scoped") },
      { chapter: "Defense", label: "Pin the definition",
        guide: "The last fix guards the description and the schema. When a tool registers, you hash its reviewed definition and compare the live one against that pin. Add a sentence to a description and the hash changes. Drop the pattern from a schema, or reword the scoped tool to sound broad, and it changes too. The client refuses any definition whose hash moved after you approved it.",
        caption: `Live definitions ${D.d3.live}, pinned ${D.d3.pinned}, matching <span class="c-ok">${D.d3.matching}</span>. Edited definitions refused: <span class="c-ok">${d3Refused}/${D.d3.edits.length}</span>: ${D.d3.edits.map((e) => `<code>${e.tool}</code> (${e.sha} vs ${e.pin}, ${e.accepted ? "accepted" : "refused"})`).join(", ")}. See <a href="https://ai-security-atlas.github.io/?node=attack-tool-rugpull">attack-tool-rugpull</a> for the definition that changes after approval.`,
        cmd: CMD("d3_pin") },
    ],
    html: `<style>[data-explainer="system-tools"] svg text { font-variant-ligatures: none; font-feature-settings: "liga" 0, "calt" 0; }</style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="The model, the MCP server, the help folder and the invoices"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 14, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s) => T(p, x, y, s, 12, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.3" });
      const card = (p, x, y, w, h, stroke) =>
        S("rect", { x, y, width: w, height: h, rx: 12, fill: V("panel"), stroke: stroke || V("line"), "stroke-width": 2 }, p);

      // Context (the model)
      label(svg, 28, 32, "MODEL CONTEXT");
      card(svg, 24, 44, 232, 192, V("violet"));
      T(svg, 40, 74, "system prompt", 13, { fill: V("muted"), "font-weight": 700 });
      const toolRows = D.s01.tools.map((t, i) => {
        const y = 92 + i * 44;
        const r = S("rect", { x: 40, y, width: 200, height: 36, rx: 8, fill: V("panel"), stroke: V("line"), "stroke-width": 1.4 }, svg);
        const nm = T(svg, 52, y + 16, t.name.replace("stools-", ""), 13, { class: "mono", "font-weight": 700 });
        const sv = T(svg, 52, y + 30, `${t.server} · ${t.params.replace(":string", "") || "no args"}`, 11, { fill: V("muted") });
        return { r, nm, sv, name: t.name, server: t.server };
      });

      // MCP server
      label(svg, 300, 32, "MCP SERVER · ATLAS-DESK");
      card(svg, 292, 44, 176, 192, V("violet"));
      const grpFiles = S("rect", { x: 308, y: 70, width: 144, height: 64, rx: 10, fill: V("panel"), stroke: V("line"), "stroke-width": 1.5 }, svg);
      T(svg, 322, 96, "files", 13, { "font-weight": 700 });
      const filesSub = T(svg, 322, 116, "read_file", 11, { class: "mono", fill: V("muted") });
      const grpBill = S("rect", { x: 308, y: 148, width: 144, height: 64, rx: 10, fill: V("panel"), stroke: V("line"), "stroke-width": 1.5 }, svg);
      T(svg, 322, 174, "billing", 13, { "font-weight": 700 });
      const billSub = T(svg, 322, 194, "get_invoice", 11, { class: "mono", fill: V("muted") });

      // Resources
      label(svg, 512, 32, "RESOURCES");
      card(svg, 504, 44, 432, 192);
      T(svg, 520, 70, "help folder  /srv/desk/scope", 12, { fill: V("muted"), "font-weight": 700 });
      const scopeFiles = ["returns.md", "shipping.md", "warranty.md"].map((n, i) => {
        const r = S("rect", { x: 520, y: 80 + i * 30, width: 180, height: 24, rx: 6, fill: V("panel"), stroke: V("teal"), "stroke-width": 1.3 }, svg);
        T(svg, 532, 97 + i * 30, n, 12, { class: "mono" });
        return r;
      });
      const canaryFile = S("rect", { x: 520, y: 176, width: 180, height: 44, rx: 6, fill: V("panel"), stroke: V("line"), "stroke-width": 1.5 }, svg);
      T(svg, 532, 196, "../canary.txt", 12, { class: "mono", "font-weight": 700 });
      const canaryFileSub = T(svg, 532, 212, "out of scope", 11, { fill: V("muted") });
      T(svg, 724, 70, "invoices", 12, { fill: V("muted"), "font-weight": 700 });
      const invRows = ["alice", "bob"].map((n, i) => {
        const r = S("rect", { x: 724, y: 80 + i * 44, width: 196, height: 36, rx: 6, fill: V("panel"), stroke: n === "alice" ? V("teal") : V("line"), "stroke-width": 1.3 }, svg);
        T(svg, 736, 98 + i * 44, `${n}`, 12, { class: "mono", "font-weight": 700 });
        const sub = T(svg, 736, 112 + i * 44, n === "bob" ? "holds the canary" : "your record", 11, { fill: V("muted") });
        return { r, name: n, sub };
      });

      // The current call
      card(svg, 24, 256, 912, 260);
      label(svg, 40, 284, "THIS CALL");
      const rec = {
        tool: T(svg, 40, 318, "", 17, { class: "mono", "font-weight": 700 }),
        args: T(svg, 40, 348, "", 15, { class: "mono" }),
        resolved: T(svg, 40, 380, "", 14, {}),
        identity: T(svg, 40, 410, "", 14, {}),
        canary: T(svg, 40, 448, "", 16, { class: "mono", "font-weight": 700 }),
        rate: T(svg, 40, 486, "", 14, { fill: V("muted") }),
      };
      // five surfaces column
      const surfaceDefs = ["description", "arguments", "output", "identity", "authorization"];
      const surfEls = surfaceDefs.map((name, i) => {
        const y = 300 + i * 40;
        const r = S("rect", { x: 560, y, width: 360, height: 32, rx: 7, fill: V("panel"), stroke: V("line"), "stroke-width": 1.4 }, svg);
        const t = T(svg, 574, y + 21, name, 13, { "font-weight": 700 });
        const c = T(svg, 760, y + 21, "", 12, { fill: V("muted") });
        return { r, t, c, name };
      });
      const noteR = S("rect", { x: 560, y: 300, width: 360, height: 200, rx: 10, fill: V("panel"), stroke: V("ok"), "stroke-width": 1.6 }, svg);
      A(noteR, { opacity: 0 });
      const noteLines = [0, 1, 2, 3].map((i) => T(svg, 578, 332 + i * 30, "", 13, {}));

      const CHECK = Object.fromEntries(D.s03.rows.map((r) => [r.surface, r.check]));

      const blank = {
        callTool: 0, surfaces: 0, traversal: 0, token: 0, canary: 0, defense: 0, note: 0,
        pinned: 0, k: 0, n: D.s04.n, showRate: 0, status: 200,
      };
      function target(n) {
        const b = Object.assign({}, blank);
        if (n === 1) return Object.assign(b, { callTool: 1 });
        if (n === 2) return Object.assign(b, { callTool: 2, status: D.s02.returns.calls[0].status });
        if (n === 3) return Object.assign(b, { callTool: 1, surfaces: 1 });
        if (n === 4) return Object.assign(b, { callTool: 1, traversal: 1, canary: 1, showRate: 1,
          k: D.s04.live.indirect.read[0], n: D.s04.live.indirect.read[1], status: probeStatus("../canary.txt") });
        if (n === 5) return Object.assign(b, { callTool: 2, token: 1, canary: 1, showRate: 1,
          k: D.s05.live.read[0], n: D.s05.live.read[1], status: D.s05.code.bob.status });
        if (n === 6) return Object.assign(b, { callTool: 0, note: 1, surfaces: 1 });
        if (n === 7) return Object.assign(b, { callTool: 1, defense: 1, traversal: 1, showRate: 1,
          k: D.d1.live.indirect.read[0], n: D.d1.live.indirect.read[1], status: 403 });
        if (n === 8) return Object.assign(b, { callTool: 2, defense: 1, token: 1, showRate: 1,
          k: D.d2.live.other_invoice.read[0], n: D.d2.live.other_invoice.read[1], status: D.d2.code.bob.status });
        return Object.assign(b, { callTool: 0, defense: 1, pinned: 1, note: 1 });
      }
      function probeStatus(p) {
        const row = D.s04.probes.find((r) => r.path === p);
        return row ? row.status : 200;
      }

      function wrap(s, w) {
        const out = []; let line = "";
        for (const word of String(s).split(" ")) {
          if ((line + " " + word).trim().length > w && line) { out.push(line); line = word; }
          else line = (line + " " + word).trim();
        }
        if (line) out.push(line);
        return out;
      }

      function draw(s) {
        const files = s.callTool === 1, billing = s.callTool === 2;
        const def = s.defense >= 0.5;
        const trav = s.traversal >= 0.5, tok = s.token >= 0.5, showCanary = s.canary >= 0.5 && !def;
        A(grpFiles, { stroke: files ? V("violet") : V("line"), "stroke-width": files ? 2.6 : 1.5, opacity: files ? 1 : 0.55 });
        A(grpBill, { stroke: billing ? V("violet") : V("line"), "stroke-width": billing ? 2.6 : 1.5, opacity: billing ? 1 : 0.55 });
        filesSub.textContent = def && files ? "read_file_strict" : "read_file";
        billSub.textContent = def && billing ? "get_invoice_scoped" : "get_invoice";
        toolRows.forEach((tr) => {
          const on = (files && tr.server === "files") || (billing && tr.server === "billing");
          A(tr.r, { opacity: on ? 1 : 0.4, "stroke-width": on ? 2.4 : 1.4, stroke: on ? V("violet") : V("line") });
          const strictName = { "stools-read_file": "read_file_strict", "stools-get_invoice": "get_invoice_scoped" }[tr.name];
          tr.nm.textContent = def && strictName ? strictName : tr.name.replace("stools-", "");
          if (tr.name === "stools-read_file") tr.sv.textContent = `files · ${def ? "name" : "path"}`;
        });
        scopeFiles.forEach((r) => A(r, { opacity: files ? 1 : 0.5 }));
        A(canaryFile, { stroke: trav && showCanary ? V("lime") : (def && files ? V("ok") : V("line")),
          "stroke-width": trav ? 2.6 : 1.5, opacity: files ? 1 : 0.5 });
        A(canaryFileSub, { fill: trav && showCanary ? V("lime") : V("muted") });
        invRows.forEach((ir) => {
          const hot = billing && ((tok && ir.name === "bob") || ir.name === "alice");
          A(ir.r, { opacity: billing ? 1 : 0.5, "stroke-width": hot ? 2.6 : 1.3,
            stroke: tok && ir.name === "bob" && showCanary ? V("lime") : (def && billing ? V("ok") : (ir.name === "alice" ? V("teal") : V("line"))) });
        });

        // surfaces vs note panel
        const showSurf = s.surfaces >= 0.5 && s.note < 0.5;
        surfEls.forEach((su) => {
          A(su.r, { opacity: showSurf ? 1 : 0, stroke: UNCHECKED.includes(CHECK[su.name]) ? V("bad") : V("ok") });
          A(su.t, { opacity: showSurf ? 1 : 0 });
          su.c.textContent = CHECK[su.name];
          A(su.c, { opacity: showSurf ? 1 : 0, fill: CHECK[su.name] === "none" ? V("bad") : V("muted") });
        });
        const F = D.s06.flags;
        const lines = s.pinned >= 0.5
          ? wrap(`Pinned ${D.d3.matching}/${D.d3.pinned} definitions match. ${d3Refused}/${D.d3.edits.length} edited definitions refused.`, 40)
          : [`path outside scope: ${F["path-outside-scope"] || 0} rows`, `token wider than user: ${F["token-wider-than-principal"] || 0} rows`,
            `other customer’s record: ${F["other-customer-record"] || 0} rows`, `rows with no flag: ${D.s06.clean}`];
        A(noteR, { opacity: s.note >= 0.5 ? 1 : 0, stroke: def ? V("ok") : V("bad") });
        noteLines.forEach((t, i) => { t.textContent = lines[i] || ""; A(t, { opacity: s.note >= 0.5 ? 1 : 0 }); });

        // this call text
        const toolName = files ? (def ? "stools-read_file_strict" : "stools-read_file")
          : billing ? (def ? "stools-get_invoice_scoped" : "stools-get_invoice") : "";
        rec.tool.textContent = toolName ? "call " + toolName : (s.pinned >= 0.5 ? "checking definitions on registration" : (s.note >= 0.5 ? "reading the tool-call log" : "pulling the call apart"));
        let args = "", resolved = "", identity = "", canaryText = "canary absent";
        if (files) {
          args = trav ? `${def ? "name" : "path"} "../canary.txt"` : `${def ? "name" : "path"} "returns.md"`;
          const probe = D.s04.probes.find((r) => r.path === "../canary.txt") || {};
          resolved = def ? `${p04(D.d1.probes).stopped_by || "tool"} refused the climbing path` : `resolves to ${trav ? (probe.resolved || "") : "/srv/desk/scope/returns.md"}`;
          identity = "token fs-service · help folder";
        } else if (billing) {
          const row = tok ? D.s05.code.bob : D.s05.code.alice;
          args = tok ? 'customer "bob"' : 'customer "alice"';
          resolved = `invoices:${tok ? "bob" : "alice"}`;
          identity = def ? `token ${D.d2.code.bob.token} · scope ${D.d2.code.bob.scope}` : `token ${row.token} · scope ${row.scope}`;
        }
        rec.args.textContent = args;
        rec.resolved.textContent = resolved;
        A(rec.resolved, { fill: def ? V("ok") : V("ink") });
        rec.identity.textContent = identity;
        A(rec.identity, { fill: tok && !def ? V("bad") : V("ink") });
        if (showCanary) canaryText = D.canary;
        else if (s.note >= 0.5 && !def) canaryText = `flagged rows returned ${D.canary}`;
        else if (def && (files || billing)) canaryText = "refused · canary stays put";
        rec.canary.textContent = s.surfaces >= 0.5 && s.note < 0.5 ? `${surfaceDefs.filter((n) => UNCHECKED.includes(CHECK[n])).length} of ${surfaceDefs.length} surfaces unchecked` : canaryText;
        A(rec.canary, { fill: showCanary || (s.note >= 0.5 && !def) ? V("lime") : (def ? V("ok") : V("muted")) });
        rec.rate.textContent = s.showRate >= 0.5 ? `read the canary ${Math.round(s.k)}/${Math.round(s.n)} live runs` : "";
        A(rec.rate, { opacity: s.showRate });

        svg.setAttribute("aria-label", `${rec.tool.textContent}; ${rec.canary.textContent}`);
      }

      const st = target(1);
      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = Object.assign({}, st), g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }
          return api.tween(620, (k) => {
            if (g !== gen) return;
            X.lerpState(st, from, to, k);
            draw(st);
          }, X.ease.inOut);
        },
      };
    },
  });
})();
