/* LAB-55 attack-agent-loop: "The task that never ends" (9 steps, System -> Attack -> Mechanism ->
 * Impact -> Defense). One persistent scene across the top: the launch checklist (three tickets) ->
 * the runner (model + desk policy + four meters) -> the tool server (atlas-desk over MCP) -> the
 * results flowing back into the runner’s context, which is the loop. The poisoned notice appears
 * only inside a tool result and is rendered from window.LAB_DATA, as is every count, rate and the
 * canary itself (data.js, exported from the reference run). A detail panel below changes per step.
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one step only. No hex colors. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, E = X.ease;
  const D = window.LAB_DATA;
  const CAN = D.canary;
  const ITEMS = D.items, FLAG = ITEMS.find(t => t.flagged);
  const R3 = D.s03.row, R4 = D.s04.row, R6 = D.s06.row, EV = D.evaluate;
  const D1 = D.d1.rows, D2 = D.d2.rows, D3 = D.d3.rows;
  const tk = v => `${Math.round(v).toLocaleString("en-US")}`;
  const loopOn = s => s.loop > .5;

  X.define({
    id: "attack-agent-loop",
    family: "family-availability",
    title: 'The task that never <span class="outline">ends</span>',
    legend: [{ role: "teal", label: "Checklist data and results", tag: "trusted-documents" }, { role: "bad", label: "The injected notice", tag: "indirect-injection" },
      { role: "violet", label: "Model" }, { role: "warn", label: "The runner", tag: "downstream-sink" },
      { role: "lime", label: "Canary and cap line" }, { role: "ok", label: "Defense", tag: "resource-limits" }],
    intro: {
      why: "Atlas Widgets runs a launch signoff desk, and an agent staffs it. You send one request: verify three checklist items. Something has to stop the desk when the work never completes. This lab runs that question on a fictional board and measures the answer in four units at once.",
      plan: "You’ll watch a benign request finish for almost nothing. Then one tool result starts asking for the same work again, and the meters climb to a hard cap. A delegation variant spawns a chain of sub-agents. A replay shows why the token bill grows faster than the loop itself. A flaky board shows no attacker is needed. Three defenses close the lab: a cap, four budgets, and a repeat detector.",
      terms: "An agent loop is a model taking turns: request tools, run them, read the results, request again. A tool result is the text a tool returns, and here it can carry a notice that asks for more work. The runner is the code that drives the loop. Exhaustion means a run hit a cap it was never meant to reach. The canary is a harmless marker that labels the attacker’s text.",
    },
    steps: [
      { chapter: "System", label: "The signoff desk",
        guide: "You are running a launch signoff desk for Atlas Widgets. An agent works the checklist by calling tools over MCP, and a runner drives the loop. Four meters watch the work: model turns, model tokens, tool calls and wall-clock seconds. They are different quantities, and this lab keeps them apart.",
        caption: `Server <code>${D.s01.server}</code> over MCP protocol <code>${D.s01.protocol}</code>; the catalog holds <code>${D.s01.tools.length ? D.s01.tools.join(", ") : ""}</code> from this lab. The board is three tickets, <code>${FLAG.id}</code> through <code>${ITEMS[2].id}</code>. Hard cap on every run: <code>${D.cap}</code> model turns. Meters accounted separately: <span class="c-teal">turns</span>, <span class="c-warn">tokens</span>, <span class="c-violet">calls</span>, wall-clock.`,
        cmd: "ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8221 docker compose run --rm workbench python attack-agent-loop/scripts/s01_board.py" },
      { chapter: "System", label: "The benign request",
        guide: "Start with the benign request. The agent lists the board, checks each item once, and reports. The meters barely move. This baseline is what every later cost gets compared against, so keep the four numbers in view.",
        caption: `Clean board, reference run: <span class="c-teal">${D.s02.steps} turns</span>, <span class="c-warn">${tk(D.s02.tokens)} tokens</span>, <span class="c-violet">${D.s02.calls} tool calls</span>, ${D.s02.wall_s} s. All ${ITEMS.length} items verified, <code>done</code>, desk policy interventions ${D.s02.policy}. Reply began “${D.s02.reply.slice(0, 60)}…”`,
        cmd: "ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8221 docker compose run --rm workbench python attack-agent-loop/scripts/s02_clean.py" },
      { chapter: "Attack", label: "The task that never ends",
        guide: "One ticket’s check result now carries a notice, marked by the canary. The notice says the verification run did not complete, and it asks for the same check again. The result never changes. This small model tends to stop calling tools on its own, so the lab’s runner applies an operator diligence policy: while any item is still outstanding, it keeps the loop going, and it runs the pending check itself when the model stalls. Nothing inside the loop says stop, so the meters climb until a cap stops them.",
        caption: `<code>${FLAG.id}</code>’s stored message has no canary; the check result does: <span class="c-bad">${D.texts.check_fail.replace("{t}", FLAG.id).slice(0, 96)}…</span> Over ${R3.n} seeds: exhausted <span class="c-bad">${R3.exhausted}/${R3.n}</span>, median <span class="c-teal">${R3.steps} turns</span>, <span class="c-warn">${tk(R3.tokens)} tokens</span>, <span class="c-violet">${R3.calls} calls</span>, work ${R3.work}/${ITEMS.length}. Cap line: <span class="c-lime">${CAN}</span>.`,
        cmd: "ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8221 docker compose run --rm workbench python attack-agent-loop/scripts/s03_poisoned.py" },
      { chapter: "Attack", label: "Delegate it down",
        guide: "The delegation board swaps the notice for a sub-agent. Each sub-agent’s report says to spawn the next sub-agent for the same item, and have it do the same. The chain grows by one delegation per turn, and every link is a real tool call plus a real model turn.",
        caption: `The flagged check defers: <span class="c-bad">${D.texts.check_pending.replace("{t}", FLAG.id).slice(0, 80)}…</span> Each report says <span class="c-bad">${D.texts.spawn_report.replace("{t}", FLAG.id).slice(0, 70)}…</span> Reference run: ${D.s04.spawns} spawns, chain depth <span class="c-bad">${D.s04.depth}</span> on <code>${FLAG.id}</code>, ${tk(R4.tokens)} median tokens, work ${R4.work}/${ITEMS.length}.`,
        cmd: "ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8221 docker compose run --rm workbench python attack-agent-loop/scripts/s04_delegate.py" },
      { chapter: "Mechanism", label: "Grows by the square",
        guide: "Here is why the token bill outruns the loop. Each turn re-sends the whole conversation, and each iteration appends one more result. The prompt grows in a straight line while the running total grows by the square. A turn cap cannot see any of this.",
        caption: `Prompt per turn: <span class="c-warn">${tk(D.s05.first_prompt)}</span> tokens at turn 1, <span class="c-warn">${tk(D.s05.last_prompt)}</span> at turn ${D.cap} — about ${D.s05.per_turn} more per turn. Billed in total: <span class="c-warn">${tk(D.s05.billed)}</span> tokens. The same ${D.cap} turns at the first turn’s size would have billed <span class="c-ok">${tk(D.s05.linear)}</span>.`,
        cmd: "ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8221 docker compose run --rm workbench python attack-agent-loop/scripts/s05_growth.py" },
      { chapter: "Impact", label: "No attacker needed",
        guide: "Take the attacker away. This board’s QA service merely times out and asks for a retry; no run ever sees the canary. The desk still runs to the cap. The missing budget is the weakness, and the cost table now holds every variant in one place.",
        caption: `Flaky board: exhausted <span class="c-bad">${R6.exhausted}/${R6.n}</span> with <span class="c-bad">0/${R6.n}</span> runs ever seeing <code class="c-lime">${CAN}</code>; median ${R6.steps} turns, ${tk(R6.tokens)} tokens, work ${R6.work}/${ITEMS.length}. Cost table: clean ${D.s02.steps} turns / ${tk(D.s02.tokens)} tokens · poisoned ${R3.steps} / ${tk(R3.tokens)} · flaky ${R6.steps} / ${tk(R6.tokens)} · delegate ${R4.steps} / ${tk(R4.tokens)}.`,
        cmd: "ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8221 docker compose run --rm workbench python attack-agent-loop/scripts/s06_flaky.py" },
      { chapter: "Defense", label: "Cap the runner",
        guide: "Cap the runner: a fixed number of model turns, and a small number of spawns per ticket on the delegation board, both enforced outside the model. The poisoned run stops at the cap with most of its budget unspent. The benign request never needed more than a few turns, so it still finishes.",
        caption: `D1, working cap <code>${D.work_cap}</code> turns, depth cap <code>${D.depth_cap}</code>: poisoned stops at <span class="c-ok">${D1[0].steps} turns</span> and <span class="c-ok">${tk(D1[0].tokens)}</span> tokens (about one tenth of Step 3), work ${D1[0].work}/${ITEMS.length}; ${D.d1.denies} spawn denials across the delegation runs; clean still <span class="c-ok">${D.d1.clean_done}/${D.d1.clean_done}</span> done. Release gate: <span class="c-ok">${EV.capped.gate ? "PASS" : "FAIL"}</span>.`,
        cmd: "ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8221 docker compose run --rm workbench python attack-agent-loop/scripts/d1_caps.py" },
      { chapter: "Defense", label: "Four separate budgets",
        guide: "Budget the four dimensions separately. A turns-only policy lets a benign but chatty request spend several times the clean board’s tokens in just a few turns. Adding token, tool-call and wall-clock meters refuses that request’s next call, and the poisoned run trips a different meter. Each refusal names its dimension.",
        caption: `Chatty board under turns-only: <span class="c-warn">${tk(D2[0].tokens)} tokens</span> in ${D2[0].steps} turns, unrefused. Under four budgets (steps ${D.budgets.steps}, tokens ${tk(D.budgets.tokens)}, calls ${D.budgets.tool_calls}, wall ${D.budgets.wall_s} s): chatty refused on <span class="c-ok">tokens</span> at turn ${D2[1].steps}; poisoned refused on <span class="c-ok">tool_calls</span> at turn ${D2[2].steps}; clean untouched at ${tk(D2[3].tokens)} tokens. Gate: <span class="c-ok">${EV.budgets.gate ? "PASS" : "FAIL"}</span>.`,
        cmd: "ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8221 docker compose run --rm workbench python attack-agent-loop/scripts/d2_budgets.py" },
      { chapter: "Defense", label: "Detect the repeat",
        guide: "Detect the repeat. The runner counts identical tool calls with identical arguments, and aborts when one pair repeats beyond the allowance. The stop comes early, it names the offending call, and it leaves a cost report. It also matches only exact repeats, so varied arguments walk past it.",
        caption: `Allowance ${D.d3.repeats} repeats: the poisoned run aborts at turn <span class="c-ok">${D3[0].steps}</span> for <code>loop_check_item {"ticket_id": "${FLAG.id}"}</code>, after <span class="c-ok">${tk(D3[0].tokens)}</span> tokens — next to Step 3’s ${tk(R3.tokens)}. Clean false positives: <span class="c-ok">${D3[1].n - D3[1].done}/${D3[1].n} done, none flagged</span>. Gate: <span class="c-ok">${EV.detector.gate ? "PASS" : "FAIL"}</span>.`,
        cmd: "ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8221 docker compose run --rm workbench python attack-agent-loop/scripts/d3_detector.py" },
    ],
    html: `<style>[data-explainer="attack-agent-loop"] svg text, [data-explainer="attack-agent-loop"] code { font-variant-ligatures: none; font-feature-settings: "liga" 0, "calt" 0; }</style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="A signoff desk agent, its runner meters, its MCP tool server and the loop that never ends, then three defenses"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 14, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) =>
        S("rect", { x, y, width: w, height: h, rx: 12, fill: V("panel"), stroke, "stroke-width": 1.8, ...o }, p);
      const chip = (p, x, y, w, h, role, k = .1) =>
        S("rect", { x, y, width: w, height: h, rx: 8, fill: V(role), "fill-opacity": k, stroke: V(role), "stroke-width": 1.3 }, p);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const flow = (p, d, role = "dim") => S("path", { d, fill: "none", stroke: V(role), "stroke-width": 2.5, "marker-end": `url(#${arrowId})`, opacity: .85 }, p);

      // ---------------------------------------------------------------- top: the desk and its meters
      const gBoard = S("g", { class: "dimmable" }, svg);
      label(gBoard, 24, 36, "LAUNCH CHECKLIST");
      card(gBoard, 24, 48, 208, 224);
      const tkt = ITEMS.map((t, i) => {
        const y = 60 + i * 70;
        const r = S("rect", { x: 34, y, width: 188, height: 60, rx: 9, "stroke-width": 1.4 }, gBoard);
        T(gBoard, 44, y + 20, t.id, 13, { class: "mono", "font-weight": 800 });
        T(gBoard, 44, y + 38, t.item.replace("checklist item ", "item "), 13, { fill: V("muted") });
        T(gBoard, 44, y + 54, t.flagged ? "flagged" : "ok", 13, { fill: V(t.flagged ? "warn" : "teal"), "font-weight": 700 });
        const note = S("g", { opacity: 0 }, gBoard);
        chip(note, 140, y + 8, 72, 20, "bad", .16);
        T(note, 176, y + 22, "notice", 13, { "text-anchor": "middle", fill: V("bad"), "font-weight": 700 });
        return { r, note, flagged: t.flagged };
      });

      const gRunner = S("g", { class: "dimmable" }, svg);
      label(gRunner, 258, 36, "RUNNER · THE DESK");
      card(gRunner, 258, 48, 226, 224);
      chip(gRunner, 268, 58, 96, 40, "violet", .12);
      T(gRunner, 316, 76, "model", 14, { "text-anchor": "middle", class: "mono", "font-weight": 800, fill: V("violet") });
      T(gRunner, 316, 92, D.model, 12, { "text-anchor": "middle", fill: V("muted") });
      chip(gRunner, 372, 58, 102, 40, "warn", .1);
      T(gRunner, 423, 76, "desk policy", 13, { "text-anchor": "middle", "font-weight": 700, fill: V("warn") });
      T(gRunner, 423, 92, "finish the work", 12, { "text-anchor": "middle", fill: V("muted") });
      card(gRunner, 268, 106, 206, 58, V("line"));
      T(gRunner, 278, 124, "context", 13, { class: "mono", fill: V("muted") });
      T(gRunner, 278, 141, "every turn re-sends it all", 13, { fill: V("muted") });
      const ctxBars = S("g", {}, gRunner);
      const ctxFill = [0, 1, 2, 3, 4, 5].map(i => S("rect", { x: 278 + i * 32, y: 148, width: 26, height: 8, rx: 3, fill: V("warn"), opacity: 0 }, ctxBars));
      const gNotice = S("g", { opacity: 0 }, gRunner);
      S("rect", { x: 266, y: 172, width: 210, height: 42, rx: 8, fill: V("bad"), "fill-opacity": .12, stroke: V("bad"), "stroke-width": 1.3, "stroke-dasharray": "5 3" }, gNotice);
      T(gNotice, 276, 190, "notice in a tool result", 13, { fill: V("bad"), "font-weight": 800 });
      T(gNotice, 276, 207, "asks for the same work again", 13, { fill: V("muted") });
      // meters
      const gMeters = S("g", {}, gRunner);
      label(gMeters, 268, 228, "METERS", { "font-size": 12 });
      const meters = [["turns", "teal", 54], ["tokens", "warn", 66], ["calls", "violet", 54], ["wall s", "dim", 54]].map(([name, role, w], i) => {
        const x = 268 + i * 54;
        S("rect", { x, y: 236, width: w, height: 14, rx: 5, fill: V("line"), opacity: .5 }, gMeters);
        const bar = S("rect", { x, y: 236, width: 0, height: 14, rx: 5, fill: V(role) }, gMeters);
        T(gMeters, x, 264, name, 12, { fill: V("muted"), "font-weight": 700 });
        return { bar, w };
      });

      const gTools = S("g", { class: "dimmable" }, svg);
      label(gTools, 510, 36, `TOOL SERVER · ${D.s01.server}`);
      card(gTools, 510, 48, 200, 224);
      T(gTools, 520, 70, `MCP · protocol ${D.s01.protocol}`, 13, { class: "mono", fill: V("muted") });
      const CAT = ["list_tickets", "read_ticket", "loop_check_item", "loop_spawn_verifier"];
      const catEls = CAT.map((name, i) => {
        const y = 82 + i * 30;
        const role = name.startsWith("loop_") ? "teal" : "dim";
        const r = chip(gTools, 520, y, 180, 24, role, .08);
        const t = T(gTools, 530, y + 16.5, name, 13, { class: "mono", "font-weight": 700 });
        return { name, r, t };
      });
      const spawnEls = catEls.filter(c => c.name === "loop_spawn_verifier");
      T(gTools, 520, 220, `+ ${D.s01.catalog - CAT.length} tools from other labs`, 13, { fill: V("muted") });
      T(gTools, 520, 240, "results are records", 13, { fill: V("muted") });
      T(gTools, 520, 258, "the model reads them anyway", 13, { fill: V("muted") });

      // the loop: results flow back
      const gLoop = S("g", { class: "dimmable" }, svg);
      flow(gLoop, "M232 150 H254", "teal");
      flow(gLoop, "M484 132 H506", "violet");
      const back = S("path", { d: "M610 276 C 610 310, 371 310, 371 276", fill: "none", stroke: V("dim"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, gLoop);
      const loopTxt = T(gLoop, 491, 316, "", 13, { "text-anchor": "middle", fill: V("dim"), "font-weight": 700 });
      const gPkt = S("g", { opacity: 0 }, svg);
      chip(gPkt, 498, 116, 26, 16, "bad", .2);
      T(gPkt, 511, 128, "notice", 13, { "text-anchor": "middle", fill: V("bad"), "font-weight": 700 });

      // far right: the run state + caps
      const gState = S("g", { class: "dimmable" }, svg);
      label(gState, 738, 36, "RUN STATE");
      card(gState, 738, 48, 198, 224);
      const stT = T(gState, 750, 74, "idle", 15, { "font-weight": 800 });
      const stS = T(gState, 750, 94, "the benign request", 13, { fill: V("muted") });
      const stRows = [["turns", "teal"], ["tokens", "warn"], ["calls", "violet"], ["wall s", "dim"]].map(([k, role], i) => {
        const y = 116 + i * 30;
        T(gState, 750, y, k, 13, { fill: V("muted"), "font-weight": 700 });
        const v = T(gState, 926, y, "0", 14, { "text-anchor": "end", class: "mono", "font-weight": 800, fill: V(role) });
        return { k, v };
      });
      const gCap = S("g", { opacity: 0 }, gState);
      S("rect", { x: 748, y: 234, width: 178, height: 30, rx: 8, fill: V("lime"), "fill-opacity": .12, stroke: V("lime"), "stroke-width": 1.3 }, gCap);
      T(gCap, 758, 254, `cap line · ${CAN}`, 13, { class: "mono", "font-weight": 800, fill: V("lime") });
      const gDeny = S("g", { opacity: 0 }, gState);
      S("rect", { x: 748, y: 200, width: 178, height: 28, rx: 8, fill: V("ok"), "fill-opacity": .12, stroke: V("ok"), "stroke-width": 1.3 }, gDeny);
      T(gDeny, 758, 219, `depth cap ${D.depth_cap} · denied`, 13, { "font-weight": 800, fill: V("ok") });

      // ---------------------------------------------------------------- panels
      const panel = () => S("g", { opacity: 0 }, svg);

      // 1: catalog and grants
      const p1 = panel();
      label(p1, 24, 322, `CATALOG · ${D.s01.tools.length} LAB TOOLS ON ${D.s01.server}`);
      D.s01.tools.forEach((name, i) => {
        const x = 24 + i * 200;
        chip(p1, x, 336, 186, 44, "teal", .09);
        T(p1, x + 14, 356, name, 13, { class: "mono", "font-weight": 700 });
        T(p1, x + 14, 373, "read-only over the board", 13, { fill: V("muted") });
      });
      label(p1, 24, 402, "GRANTS");
      T(p1, 24, 424, `check boards grant 3 tools · the delegation board grants 4`, 14, {});
      T(p1, 24, 446, `app-side hard cap: every profile max_steps ${D.cap}`, 14, { fill: V("muted") });
      label(p1, 24, 478, "THE FOUR METERS, KEPT APART");
      T(p1, 24, 500, "model turns · model tokens · tool calls · wall-clock seconds", 14, { fill: V("muted") });

      // 2: benign baseline
      const p2 = panel();
      label(p2, 24, 322, "THE BENIGN REQUEST · CLEAN BOARD");
      [["turns", D.s02.steps, "teal"], ["tokens", tk(D.s02.tokens), "warn"], ["calls", D.s02.calls, "violet"], ["wall", `${D.s02.wall_s} s`, "dim"]].forEach(([k, v, role], i) => {
        const x = 24 + i * 170;
        chip(p2, x, 336, 156, 58, role, .09);
        T(p2, x + 14, 358, String(v), 20, { class: "mono", "font-weight": 800, fill: V(role) });
        T(p2, x + 14, 380, k, 13, { fill: V("muted"), "font-weight": 700 });
      });
      card(p2, 712, 330, 224, 70, V("teal"));
      T(p2, 724, 352, "done · all items verified", 14, { "font-weight": 800, fill: V("teal") });
      T(p2, 724, 372, `desk policy interventions: ${D.s02.policy}`, 13, { fill: V("muted") });
      T(p2, 24, 430, `the reply: “${D.s02.reply.slice(0, 88)}…”`, 13, { fill: V("muted") });
      T(p2, 24, 452, "this row is the baseline every later cost is compared against", 14, { fill: V("muted") });
      T(p2, 24, 478, "same three items, same request, in every later step", 13, { fill: V("muted") });

      // 3: the poisoned loop
      const p3 = panel();
      label(p3, 24, 322, `THE SAME REQUEST · POISONED CHECK RESULT · ${R3.n} SEEDS`);
      const cols = [["turns", `${R3.steps}/${D.cap}`, "teal"], ["tokens", tk(R3.tokens), "warn"], ["calls", String(R3.calls), "violet"], ["work", `${R3.work}/${ITEMS.length}`, "dim"]].map(([k, v, role], i) => {
        const x = 24 + i * 150;
        chip(p3, x, 336, 136, 58, role, .1);
        T(p3, x + 12, 358, v, 19, { class: "mono", "font-weight": 800, fill: V(role) });
        T(p3, x + 12, 380, k, 13, { fill: V("muted"), "font-weight": 700 });
      });
      card(p3, 640, 330, 296, 130, V("lime"));
      T(p3, 654, 352, "THE CAP LINE", 13, { fill: V("lime"), "font-weight": 700, "letter-spacing": "1.2" });
      T(p3, 654, 374, `[canary] ${CAN}`, 14, { class: "mono", "font-weight": 800, fill: V("lime") });
      T(p3, 654, 394, `run hit a cap: ${R3.steps} model turns · ${R3.calls} tool calls`, 13, { fill: V("muted") });
      T(p3, 654, 412, `${tk(R3.tokens)} tokens · no reply was ever written`, 13, { fill: V("muted") });
      T(p3, 24, 478, `exhausted ${R3.exhausted}/${R3.n} seeds at temperature 0 · the notice rides in the result, marked by the canary`, 14, { fill: V("muted") });

      // 4: delegation chain
      const p4 = panel();
      label(p4, 24, 322, `THE DELEGATION CHAIN ON ${FLAG.id}`);
      const chain = [0, 1, 2, 3, 4].map(i => {
        const g = S("g", { opacity: 0 }, p4);
        const x = 24 + i * 128;
        chip(g, x, 344, 112, 64, i === 0 ? "teal" : "bad", i === 0 ? .09 : .12);
        T(g, x + 56, 366, i === 0 ? "check" : `sub-agent ${i}`, 13, { "text-anchor": "middle", "font-weight": 800 });
        T(g, x + 56, 384, i === 0 ? "PENDING" : "not verified", 13, { "text-anchor": "middle", fill: V("muted") });
        T(g, x + 56, 400, i === 0 ? "defers" : "spawns next", 13, { "text-anchor": "middle", fill: V(i === 0 ? "muted" : "bad") });
        if (i < 4) S("path", { d: `M${x + 114} 376 H${x + 126}`, stroke: V("bad"), "stroke-width": 2, "marker-end": `url(#${arrowId})` }, g);
        return g;
      });
      T(p4, 24, 432, "…", 16, { class: "mono", fill: V("muted") });
      card(p4, 700, 330, 236, 130, V("bad"));
      T(p4, 712, 352, "DEPTH, COUNTED PER TURN", 13, { fill: V("bad"), "font-weight": 700, "letter-spacing": "1.2" });
      T(p4, 712, 380, `${D.s04.spawns} spawns · depth ${D.s04.depth}`, 16, { class: "mono", "font-weight": 800, fill: V("bad") });
      T(p4, 712, 402, `${tk(R4.tokens)} median tokens`, 13, { fill: V("muted") });
      T(p4, 712, 420, `work ${R4.work}/${ITEMS.length} · no report`, 13, { fill: V("muted") });
      T(p4, 24, 478, "each report says: spawn the next sub-agent, and have it do the same", 14, { fill: V("muted") });

      // 5: the growth curve
      const p5 = panel();
      label(p5, 24, 322, "PROMPT TOKENS PER TURN · THE RE-SEND CURVE");
      const curve = D.s05.curve;
      const cmax = Math.max(...curve.map(c => c[1]));
      const bars = curve.map(([turn, val], i) => {
        const x = 34 + i * (560 / Math.max(curve.length - 1, 1));
        const h = 100 * val / cmax;
        const r = S("rect", { x: x - 13, y: 448 - h, width: 26, height: 0, rx: 4, fill: V("warn"), "fill-opacity": .75 }, p5);
        T(p5, x, 468, `t${turn}`, 12, { "text-anchor": "middle", fill: V("muted") });
        T(p5, x, 448 - h - 8, tk(val), 12, { "text-anchor": "middle", class: "mono", fill: V("warn"), "font-weight": 700, opacity: 0 });
        return { r, h };
      });
      label(p5, 620, 322, "LINEAR LOOP, QUADRATIC BILL");
      [["billed", tk(D.s05.billed), "warn"], ["if flat", tk(D.s05.linear), "ok"]].forEach(([k, v, role], i) => {
        const y = 344 + i * 62;
        chip(p5, 620, y, 316, 52, role, .1);
        T(p5, 634, y + 22, v + " tokens", 19, { class: "mono", "font-weight": 800, fill: V(role) });
        T(p5, 634, y + 42, k === "billed" ? `billed over ${D.cap} turns` : `same turns at turn-1 size`, 13, { fill: V("muted") });
      });
      T(p5, 620, 478, `about ${D.s05.per_turn} more prompt tokens every turn`, 14, { fill: V("muted") });
      T(p5, 24, 500, "the loop is linear; the conversation is cumulative", 14, { fill: V("muted") });

      // 6: the cost table
      const p6 = panel();
      label(p6, 24, 322, "THE COST TABLE · ONE BENIGN REQUEST, FOUR BOARDS");
      [["board", 24, null], ["turns", 200, "teal"], ["tokens", 300, "warn"], ["calls", 470, "violet"], ["work", 570, "dim"], ["canary seen", 660, "lime"]].forEach(([h, x, role]) =>
        T(p6, x, 344, h, 13, { fill: role ? V(role) : V("muted"), "font-weight": 700 }));
      const p6rows = [
        ["clean", D.s02.steps, D.s02.tokens, D.s02.calls, `${ITEMS.length}/${ITEMS.length}`, "no"],
        ["poisoned", R3.steps, R3.tokens, R3.calls, `${R3.work}/${ITEMS.length}`, "yes"],
        ["flaky", R6.steps, R6.tokens, R6.calls, `${R6.work}/${ITEMS.length}`, "never"],
        ["delegate", R4.steps, R4.tokens, R4.calls, `${R4.work}/${ITEMS.length}`, "yes"],
      ].map((row, i) => {
        const y = 362 + i * 40;
        const g = S("g", { opacity: 0 }, p6);
        T(g, 24, y + 18, row[0], 15, { "font-weight": 800 });
        T(g, 200, y + 18, String(row[1]), 14, { class: "mono", fill: V("teal"), "font-weight": 700 });
        T(g, 300, y + 18, tk(row[2]), 14, { class: "mono", fill: V("warn"), "font-weight": 700 });
        T(g, 470, y + 18, String(row[3]), 14, { class: "mono", fill: V("violet"), "font-weight": 700 });
        T(g, 570, y + 18, String(row[4]), 14, { class: "mono", fill: V("muted") });
        T(g, 660, y + 18, String(row[5]), 13, { fill: V(row[5] === "never" ? "ok" : "lime"), "font-weight": 700 });
        return g;
      });
      card(p6, 790, 350, 146, 120, V("ok"));
      T(p6, 802, 374, "NO ATTACKER", 13, { fill: V("ok"), "font-weight": 700, "letter-spacing": "1.2" });
      T(p6, 802, 398, `flaky: 0/${R6.n} runs`, 14, { "font-weight": 800 });
      T(p6, 802, 416, "ever saw the", 13, { fill: V("muted") });
      T(p6, 802, 434, `canary ${CAN}`, 12, { class: "mono", fill: V("lime"), "font-weight": 700 });
      T(p6, 24, 530 - 22, "the missing budget is the weakness; the notice only makes it deliberate", 14, { fill: V("muted") });

      // 7: D1 caps
      const p7 = panel();
      card(p7, 24, 330, 430, 190, V("ok"));
      T(p7, 40, 352, `D1 · WORKING CAP ${D.work_cap} TURNS · DEPTH CAP ${D.depth_cap}`, 13, { fill: V("ok"), "font-weight": 700, "letter-spacing": "1.2" });
      T(p7, 40, 378, "enforced in the runner, outside the model", 13, { fill: V("muted") });
      T(p7, 40, 404, `poisoned stops at ${D1[0].steps} turns · ${tk(D1[0].tokens)} tokens`, 15, { "font-weight": 800 });
      T(p7, 40, 428, `about one tenth of Step 3’s ${tk(R3.tokens)}`, 13, { fill: V("muted") });
      T(p7, 40, 452, `work at the cap: ${D1[0].work}/${ITEMS.length} · ${FLAG.id} never verified`, 13, { fill: V("muted") });
      T(p7, 40, 476, `${D.d1.denies} spawn denials on the delegation board (depth ${D.depth_cap})`, 13, { fill: V("muted") });
      label(p7, 490, 322, "THE BENIGN REQUEST STILL FITS");
      const p7rows = [["clean", `${D.s02.steps} turns`, `${tk(D.s02.tokens)} tokens`, D.d1.clean_done === 2], ["poisoned", `${D1[0].steps} turns`, `${tk(D1[0].tokens)} tokens`, false]].map(([k, a, b, ok], i) => {
        const y = 348 + i * 46;
        const g = S("g", { opacity: 0 }, p7);
        T(g, 490, y + 16, k, 15, { "font-weight": 800 });
        T(g, 600, y + 16, a, 14, { class: "mono", fill: V("teal"), "font-weight": 700 });
        T(g, 700, y + 16, b, 14, { class: "mono", fill: V("warn"), "font-weight": 700 });
        T(g, 880, y + 16, ok ? "done" : "capped", 13, { "text-anchor": "end", fill: V(ok ? "ok" : "warn"), "font-weight": 800 });
        return g;
      });
      T(p7, 490, 452, `release gate at ${D.eval_trials} trials: ${EV.capped.gate ? "PASS" : "FAIL"} · the cap bounds, it does not finish`, 13, { fill: V("muted") });

      // 8: D2 budgets
      const p8 = panel();
      card(p8, 24, 330, 440, 160, V("warn"));
      T(p8, 40, 352, "POLICY A · TURNS ONLY", 13, { fill: V("warn"), "font-weight": 700, "letter-spacing": "1.2" });
      T(p8, 40, 378, `chatty request: ${tk(D2[0].tokens)} tokens in ${D2[0].steps} turns`, 14, { "font-weight": 800 });
      T(p8, 40, 400, `the turn meter saw ${D2[0].steps} of ${D.budgets.steps} and waved it through`, 13, { fill: V("muted") });
      const sessA = D2[0].tokens + D1[0].tokens + D2[3].tokens;   // chatty (turns-only) + poisoned (D1's capped run) + clean
      const sessB = D2[1].tokens + D2[2].tokens + D2[3].tokens;   // the same three requests, refused early
      T(p8, 40, 424, `session total under A: ${tk(sessA)} tokens`, 13, { fill: V("muted") });
      card(p8, 490, 330, 446, 160, V("ok"));
      T(p8, 506, 352, "POLICY B · FOUR BUDGETS", 13, { fill: V("ok"), "font-weight": 700, "letter-spacing": "1.2" });
      T(p8, 506, 378, `steps ${D.budgets.steps} · tokens ${tk(D.budgets.tokens)} · calls ${D.budgets.tool_calls} · wall ${D.budgets.wall_s} s`, 13, { class: "mono" });
      T(p8, 506, 402, `chatty refused on tokens at turn ${D2[1].steps}`, 14, { "font-weight": 800, fill: V("ok") });
      T(p8, 506, 424, `poisoned refused on tool_calls at turn ${D2[2].steps}`, 14, { "font-weight": 800, fill: V("ok") });
      T(p8, 506, 448, `clean untouched at ${tk(D2[3].tokens)} tokens`, 13, { fill: V("muted") });
      T(p8, 24, 508, `the same three requests under B billed ${tk(sessB)} tokens · each refusal names its dimension`, 13, { fill: V("muted") });

      // 9: D3 detector
      const p9 = panel();
      label(p9, 24, 322, `THE REPEAT COUNTER · ALLOWANCE ${D.d3.repeats}`);
      const reps = [1, 2, 3].map((n, i) => {
        const g = S("g", { opacity: 0 }, p9);
        const x = 24 + i * 170;
        chip(g, x, 340, 150, 64, n <= D.d3.repeats ? "teal" : "bad", n <= D.d3.repeats ? .09 : .14);
        T(g, x + 75, 366, `call ×${n}`, 15, { "text-anchor": "middle", "font-weight": 800 });
        T(g, x + 75, 388, n <= D.d3.repeats ? "allowed" : "abort", 13, { "text-anchor": "middle", fill: V(n <= D.d3.repeats ? "muted" : "bad"), "font-weight": 700 });
        T(g, x + 75, 404, `loop_check_item`, 12, { "text-anchor": "middle", class: "mono", fill: V("muted") });
        return g;
      });
      card(p9, 560, 330, 376, 130, V("ok"));
      T(p9, 574, 352, "GRACEFUL ABORT · COST REPORT", 13, { fill: V("ok"), "font-weight": 700, "letter-spacing": "1.2" });
      T(p9, 574, 378, `turn ${D3[0].steps} · ${tk(D3[0].tokens)} tokens · ${D3[0].calls} calls`, 16, { class: "mono", "font-weight": 800, fill: V("ok") });
      T(p9, 574, 402, `names the pair: loop_check_item {"ticket_id": "${FLAG.id}"}`, 13, { fill: V("muted") });
      T(p9, 574, 424, `clean board: ${D3[1].done}/${D3[1].n} done, none flagged`, 13, { fill: V("muted") });
      T(p9, 24, 496, "matches exact (tool, arguments) pairs only · varied arguments walk past it", 14, { fill: V("muted") });

      // ---------------------------------------------------------------- state
      const base0 = { p1: 0, p2: 0, p3: 0, p4: 0, p5: 0, p6: 0, p7: 0, p8: 0, p9: 0, notice: 0, loop: 0,
                      run: 0, capline: 0, deny: 0, meters: 0, ctx: 0, bars: 0, chain: 0, hot: "" };
      const T_N = [null,
        { p1: 1, hot: "tools" },                                              // 1 System: the desk
        { p2: 1, run: .33, meters: .33, hot: "state" },                       // 2 System: benign request
        { notice: 1, loop: 1, run: 1, meters: 1, ctx: 1, capline: 1, p3: 1, hot: "runner" },   // 3 Attack: never ends
        { notice: 1, loop: 1, run: 1, meters: 1, ctx: 1, capline: 1, chain: 1, p4: 1, hot: "tools" }, // 4 Attack: delegation
        { notice: 1, loop: 1, ctx: 1, bars: 1, p5: 1, hot: "runner" },       // 5 Mechanism: square
        { loop: 1, run: 1, meters: 1, p6: 1, hot: "board" },                 // 6 Impact: no attacker
        { loop: 1, run: 1, meters: 1, deny: 1, p7: 1, hot: "runner" },       // 7 Defense: cap
        { loop: 1, meters: 1, p8: 1, hot: "state" },                         // 8 Defense: budgets
        { notice: 1, loop: 1, p9: 1, hot: "runner" },                        // 9 Defense: detector
      ];
      const target = n => ({ ...base0, ...T_N[n] });
      const st = { ...base0 };
      const GROUPS = { board: gBoard, runner: gRunner, tools: gTools, state: gState, loop: gLoop };
      const op = v => (+v).toFixed(3);
      const VALS = {
        1: ["idle", "the desk waits", 0, 0, 0, 0],
        2: ["running", "clean board", D.s02.steps, D.s02.tokens, D.s02.calls, D.s02.wall_s],
        3: ["capped", "poisoned board", R3.steps, R3.tokens, R3.calls, R3.wall_s],
        4: ["capped", "delegation board", R4.steps, R4.tokens, R4.calls, R4.wall_s],
        5: ["capped", "the bill, turn by turn", R3.steps, R3.tokens, R3.calls, R3.wall_s],
        6: ["capped", "flaky board, no attacker", R6.steps, R6.tokens, R6.calls, R6.wall_s],
        7: ["capped", `working cap ${D.work_cap}`, D1[0].steps, D1[0].tokens, D1[0].calls, D1[0].wall_s],
        8: ["refused", "four budgets", D2[2].steps, D2[2].tokens, D2[2].calls, D2[2].wall_s],
        9: ["aborted", "loop detected", D3[0].steps, D3[0].tokens, D3[0].calls, D3[0].wall_s],
      };
      const MAXES = [D.cap, Math.max(R3.tokens, R4.tokens, R6.tokens), Math.max(R3.calls, R4.calls, R6.calls),
                     Math.max(R3.wall_s, R4.wall_s, R6.wall_s)];

      function draw(s) {
        const n = Math.round(seg(s.run, 0, 1) * 8) + 1;   // 1..9 as run progresses
        const vals = VALS[Math.min(n, 9)];
        const frac = s.run;
        // board + notice
        tkt.forEach(t => {
          A(t.r, { stroke: V(t.flagged && s.notice > .5 ? "bad" : "line") });
          A(t.note, { opacity: op(t.flagged ? seg(s.notice, .2, .9) : 0) });
        });
        A(gNotice, { opacity: op(seg(s.notice, .15, .85)) });
        A(gPkt, { opacity: op(seg(s.notice, .3, 1)) });
        // the loop arrow
        A(back, { stroke: V(loopOn(s) ? "bad" : "dim"), "stroke-width": loopOn(s) ? 3.2 : 2.5 });
        loopTxt.textContent = loopOn(s) ? "results feed the next turn" : "one pass";
        A(loopTxt, { fill: V(loopOn(s) ? "bad" : "dim") });
        // context bars fill as the conversation grows
        ctxFill.forEach((b, i) => A(b, { opacity: op(seg(s.ctx, i * .12, .5 + i * .12)) }));
        // meters (fraction of the observed maxima)
        meters.forEach((m, i) => {
          const v = Number(vals[3 + i]) || 0;
          const fillv = i === 0 ? Math.min(1, v / D.cap) : Math.min(1, v / MAXES[i]);
          A(m.bar, { width: (m.w * E.out(fillv * frac)).toFixed(2) });
        });
        // run state
        stT.textContent = vals[0];
        A(stT, { fill: V(s.capline > .5 ? "lime" : s.deny > .5 ? "ok" : "ink") });
        stS.textContent = vals[1];
        const shown = [vals[2], tk(vals[3]), vals[4], `${vals[5]} s`];
        stRows.forEach((r, i) => { r.v.textContent = frac > .2 ? shown[i] : "0"; });
        A(gCap, { opacity: op(seg(s.capline, .4, 1)) });
        A(gDeny, { opacity: op(seg(s.deny, .4, 1)) });
        // panels + staggered rows
        [p1, p2, p3, p4, p5, p6, p7, p8, p9].forEach((p, i) => A(p, { opacity: op(s["p" + (i + 1)]) }));
        bars.forEach((b, i) => A(b.r, { height: (b.h * E.out(seg(s.bars, .08 + i * .09, .5 + i * .09))).toFixed(2), y: (448 - b.h * E.out(seg(s.bars, .08 + i * .09, .5 + i * .09))).toFixed(2) }));
        chain.forEach((g, i) => A(g, { opacity: op(seg(s.chain, .1 + i * .14, .55 + i * .14)) }));
        p6rows.forEach((g, i) => A(g, { opacity: op(seg(s.p6, .1 + i * .12, .5 + i * .12)) }));
        p7rows.forEach((g, i) => A(g, { opacity: op(seg(s.p7, .15 + i * .1, .5 + i * .1)) }));
        reps.forEach((g, i) => A(g, { opacity: op(seg(s.p9, .1 + i * .16, .5 + i * .16)) }));
        // focus + context
        const hot = s.hot ? s.hot.split(",").map(k => GROUPS[k]) : null;
        [gBoard, gRunner, gTools, gState, gLoop].forEach(g => g.classList.toggle("hot", !!hot && hot.includes(g)));
        el.classList.toggle("lx-focus", !!hot);
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          return api.tween(n === 3 ? 850 : 650, k => { if (g !== gen) return; X.lerpState(st, from, to, X.clamp(k)); draw(st); }, E.inOut);
        },
      };
    },
  });
})();
