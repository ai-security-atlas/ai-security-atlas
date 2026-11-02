/* LAB-42 attack-session-leak. Two shops, one assistant, three ways a reply can carry the other shop's code.
 * Pattern: target(n) is pure, draw(s) is a pure render, step() tweens one step forward and snaps otherwise.
 * Every canary, code, question and count comes from window.LAB_DATA. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v;
  const D = window.LAB_DATA;
  const C = D.counts;
  const open = D.live.profiles["sleak-open"];
  const closed = D.live.profiles["sleak-acl"];
  const sample = open.rows[0];
  const extra = C.cache_retrievals_isolated - C.cache_retrievals_shared;
  const tokens = sample.prompt_tokens + sample.completion_tokens;

  X.define({
    id: "attack-session-leak",
    family: "family-privacy",
    title: 'Whose data is this? Cross-tenant <span class="outline">leaks</span>',
    legend: [
      { role: "teal", label: "Copperleaf’s note" },
      { role: "warn", label: "Harbor’s reply" },
      { role: "violet", label: "Shared assistant" },
      { role: "bad", label: "Cross-tenant path" },
      { role: "lime", label: "Canary" },
      { role: "ok", label: "Defense" },
    ],
    intro: {
      why: "Two partner shops share one support assistant. Each shop has a private note. You are about to ask whether the other shop can read it. The assistant is supposed to answer from the shop that is signed in.",
      plan: "You’ll check the healthy case first. Then you’ll turn on one bug at a time: a shared answer cache, a search with no tenant filter, and a conversation remembered under a shared id. All three bugs live in the app around the model, not in the model itself. Last, you’ll measure the fix for each bug and what that fix costs.",
      terms: "A tenant is a shop, and a principal is the signed-in buyer. A canary is a fixed fictional code that marks one shop’s private note. A cache stores a finished reply so a later caller can reuse it. Retrieval is the search that picks documents for the reply. A session is the remembered conversation. The stub is a simple stand-in model that quotes the top document, so results repeat exactly; runs with a real model are an optional cross-check.",
    },
    steps: [
      { chapter: "System", label: "Two shops",
        guide: "Start with both controls on. Each shop gets its own session, the search keeps the other shop’s note out, and the cache key includes who asked. Ask Copperleaf for its night-shift code, then ask Harbor the same question and Harbor’s own weekend question. You want Harbor’s reply to carry Harbor’s code and to leave Copperleaf’s code out.",
        caption: `Baseline with cache key = principal, tenant filter on, session bound to the caller. Copperleaf’s night-shift reply contains <code class="c-lime">${D.canary}</code> (${C.baseline_own}/${C.baseline_own}). Harbor’s night-shift reply leaks it ${C.baseline_cross} times. Harbor’s weekend reply contains <code class="c-warn">${D.harbor_code}</code> (${C.baseline_marker}). Harbor’s night-shift question, with the filter on, quotes that same weekend note: it is the nearest document Harbor may read.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-session-leak ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8211 WORKBENCH_TAG=v3 docker compose run --rm workbench python attack-session-leak/scripts/s01_boundary.py" },
      { chapter: "Attack", label: "Cached reply",
        guide: "Turn the cache key into the question text alone and leave the tenant filter on. Copperleaf asks first. Harbor asks the same question. Watch the source line. A cache hit means Harbor was handed the stored reply. Read the body for Copperleaf’s code. The milliseconds only tell you the reply was reused.",
        caption: `Harbor’s source is <code>cache-hit</code> (${C.cache_source_hit}) and the body contains <code class="c-lime">${D.canary}</code> (${C.cache_leak}). <code>stored_reply_replayed=yes</code>. The script also prints <code>timing_recovers_text = no</code>. The clock reports reuse. Hit time on this machine rounded to 0.00 ms; that figure moves.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-session-leak ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8211 WORKBENCH_TAG=v3 docker compose run --rm workbench python attack-session-leak/scripts/s02_cache.py" },
      { chapter: "Mechanism", label: "Question key",
        guide: "Look at the key the store used. It is the normalized question, with no principal in it. Anyone who types that question receives the stored body. The tenant filter never runs on a hit, because the reply was saved before this caller arrived. That is why Harbor can hold a document the search would have kept back.",
        caption: `Same command as the previous step. Key = question text. Owner of the stored reply: <span class="c-teal">copperleaf-buyer</span>. Served to: <span class="c-warn">harbor-buyer</span>. Question: “${D.questions.night}”.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-session-leak ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8211 WORKBENCH_TAG=v3 docker compose run --rm workbench python attack-session-leak/scripts/s02_cache.py" },
      { chapter: "Mechanism", label: "Open search",
        guide: "Turn the cache off and turn the tenant filter off. Harbor asks for the night-shift code. Read the ranked hits. The top document belongs to Copperleaf, and its authorized field is no. The stub quotes that top hit, so the code appears in the body. Distance measures closeness of wording. Permission is a separate check, and this run skipped it.",
        caption: `Top hit <code class="c-bad">${D.retrieval_top}</code>, unauthorized chunks in the list: ${C.retrieval_unauth}, leak ${C.retrieval_leak}. Reference distances on this embedder: copperleaf night 0.2381, harbor weekend 0.479, orbit 0.7799, shipping 0.8033. The order is what the lab locks.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-session-leak ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8211 WORKBENCH_TAG=v3 docker compose run --rm workbench python attack-session-leak/scripts/s03_retrieve.py" },
      { chapter: "Mechanism", label: "Shared session",
        guide: "Turn the cache off and turn the tenant filter back on. Copperleaf speaks first, into a bucket every caller shares, then into an id a client can type. Harbor asks what was said earlier and presents that same id. The top document is Harbor’s own note. The canary sits in the saved turns, and the reply reprints them under a line saying they came from earlier in this session.",
        caption: `Global leak ${C.session_global_leak}, guess leak ${C.session_guess_leak}. <code>earlier_prefix</code> yes for both. <code>top_doc_is_copperleaf</code> no for both: the new search returned Harbor’s weekend note, and <code class="c-lime">${D.canary}</code> arrived from the stored turn. Client-typed id: <code>${D.session_guess}</code>.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-session-leak ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8211 WORKBENCH_TAG=v3 docker compose run --rm workbench python attack-session-leak/scripts/s04_session.py" },
      { chapter: "Impact", label: "Three leaks",
        guide: "Run the three bugs once each and score them the same way: does Harbor’s body contain Copperleaf’s code? Keep the timing line beside that score. A fast reply is a hint that something was reused. The text in the body is the disclosure. The reference run on this page uses the stub. A real model may phrase the same documents in its own words.",
        caption: `Stub score <span class="c-lime">${C.cache_leak + C.retrieval_leak + C.session_global_leak}/3</span> content leaks. Canary <code class="c-lime">${D.canary}</code>. <code>timing_recovers_text = no</code>. Live ${D.live.model} on ${D.live.backend}, Harbor, “${D.questions.night}”, temperature 0, seeds 0–3: profile <code>sleak-open</code> ${open.leaks}/${open.n}, profile <code>sleak-acl</code> ${closed.leaks}/${closed.n}. Those live rates are a cross-check. They do not decide the gate.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-session-leak ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8211 WORKBENCH_TAG=v3 docker compose run --rm workbench python attack-session-leak/scripts/s05_impact.py" },
      { chapter: "Defense", label: "Key the caller",
        guide: "Put the principal back into the cache key and repeat a fixed workload: both shops, three questions, two passes. Count hits, retrievals, and Harbor’s night-shift leaks. Copperleaf should still receive its own code. The cost is the extra searches the isolated key performs. A shared key saves those searches and also hands out the stored reply.",
        caption: `Workload ${C.workload_n}. Shared key: hits ${C.cache_hits_shared}/${C.workload_n}, retrievals ${C.cache_retrievals_shared}, Harbor night leaks ${C.cache_leaks_shared}/${C.cache_harbor_night}. Isolated key: hits ${C.cache_hits_isolated}/${C.workload_n}, retrievals ${C.cache_retrievals_isolated}, leaks ${C.cache_leaks_isolated}/${C.cache_harbor_night}. Cost: +${extra} retrievals. Copperleaf night canary ${C.cache_own_isolated}/${C.cache_own_n}. Token estimate if each extra miss called the model: ${extra} × ${tokens} = ${extra * tokens} (one <code>sleak-open</code> reply, ${sample.prompt_tokens}+${sample.completion_tokens}).`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-session-leak ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8211 WORKBENCH_TAG=v3 docker compose run --rm workbench python attack-session-leak/scripts/d1_cache_key.py" },
      { chapter: "Defense", label: "Filter the search",
        guide: "Ask Harbor’s night-shift question twice, once with the filter off and once with it on. Count unauthorized chunks in the hit list. Then ask Harbor for its weekend code and check that its own marker still comes back. The filter drops the forbidden document. The nearest remaining document can be a weak match, and this stub still quotes it.",
        caption: `Filter off: unauthorized ${C.retrieval_unauth}, leak ${C.retrieval_leak}, top <code>${D.retrieval_top}</code>. Filter on: unauthorized ${C.acl_unauth}, leak ${C.acl_leak}, top <code>sleak-harbor-weekend</code>. Weekend utility: marker ${C.acl_utility} (<code class="c-warn">${D.harbor_code}</code>). Cost: unauthorized chunks removed = ${C.retrieval_unauth - C.acl_unauth}; weekend code still returned = yes. Live <code>sleak-acl</code> replies were “I do not know the night-shift purchase order code.” (${closed.leaks}/${closed.n} leaks). The stub has no such refusal.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-session-leak ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8211 WORKBENCH_TAG=v3 docker compose run --rm workbench python attack-session-leak/scripts/d2_acl.py" },
      { chapter: "Defense", label: "Bind the session",
        guide: "Have the server issue a long random session id and bind it to Copperleaf. Harbor presents that id, and Harbor also presents a short id a client could type. Copperleaf resumes the issued id. Then try a large batch of short ids and count how many open a session. The cost is that a client-chosen id resumes nothing.",
        caption: `Issued id length 32. Harbor presenting the issued id: leak ${C.bound_stolen}. Harbor presenting <code>${D.session_guess}</code>: rejected ${C.bound_typed}. Copperleaf resuming the issued id: canary ${C.bound_own}. Guesses opened ${C.guesses_opened}/${C.guesses}. Cost: client-chosen id resumed 0/1; server-issued id resumed 1/1; guessed ids opened ${C.guesses_opened}/${C.guesses}. The hex id changes every run.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-session-leak ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8211 WORKBENCH_TAG=v3 docker compose run --rm workbench python attack-session-leak/scripts/d3_session.py" },
    ],
    html: `<style>
      [data-explainer="attack-session-leak"] svg text { font-variant-ligatures: none; font-feature-settings: "liga" 0, "calt" 0; }
    </style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Two shops sharing one assistant"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.6" });
      const card = (p, x, y, w, h, stroke) => S("rect", { x, y, width: w, height: h, rx: 16, fill: V("panel"), stroke: stroke || V("line"), "stroke-width": 2 }, p);

      label(svg, 48, 48, "SHOPS");
      label(svg, 340, 48, "ASSISTANT");
      label(svg, 690, 48, "REPLY");

      const gShops = S("g", { class: "dimmable" }, svg);
      card(gShops, 36, 68, 270, 420);
      const copper = S("rect", { x: 56, y: 96, width: 230, height: 160, rx: 12, fill: V("teal"), "fill-opacity": 0.14, stroke: V("teal"), "stroke-width": 1.5 }, gShops);
      T(gShops, 72, 132, "Copperleaf", 18, { "font-weight": 700, fill: V("teal") });
      T(gShops, 72, 160, "private night-shift note", 14, { fill: V("ink") });
      const copperCode = T(gShops, 72, 190, D.canary, 14, { class: "mono", fill: V("lime"), "font-weight": 700 });
      T(gShops, 72, 218, "tenant copperleaf", 13, { fill: V("muted") });

      const harbor = S("rect", { x: 56, y: 284, width: 230, height: 172, rx: 12, fill: V("warn"), "fill-opacity": 0.12, stroke: V("warn"), "stroke-width": 1.5 }, gShops);
      T(gShops, 72, 322, "Harbor", 18, { "font-weight": 700, fill: V("warn") });
      T(gShops, 72, 350, "asks as harbor-buyer", 14, { fill: V("ink") });
      const harborCode = T(gShops, 72, 380, D.harbor_code, 14, { class: "mono", fill: V("warn"), "font-weight": 700 });
      T(gShops, 72, 412, "tenant harbor", 13, { fill: V("muted") });

      const gCache = S("g", { class: "dimmable" }, svg);
      const cacheBox = card(gCache, 332, 68, 300, 118, V("violet"));
      label(gCache, 350, 96, "CACHE");
      const cacheKey = T(gCache, 350, 128, "key off", 16, { class: "mono", "font-weight": 700 });
      const cacheNote = T(gCache, 350, 156, "no stored reply", 14, { fill: V("muted") });

      const gSearch = S("g", { class: "dimmable" }, svg);
      const searchBox = card(gSearch, 332, 204, 300, 118, V("violet"));
      label(gSearch, 350, 232, "RETRIEVAL");
      const searchLine = T(gSearch, 350, 264, "tenant filter on", 16, { class: "mono", "font-weight": 700 });
      const searchNote = T(gSearch, 350, 292, "top doc —", 14, { fill: V("muted") });

      const gSession = S("g", { class: "dimmable" }, svg);
      const sessionBox = card(gSession, 332, 340, 300, 148, V("violet"));
      label(gSession, 350, 368, "SESSION");
      const sessionLine = T(gSession, 350, 402, "bound to the caller", 16, { class: "mono", "font-weight": 700 });
      const sessionNote = T(gSession, 350, 432, "server keeps the id", 14, { fill: V("muted") });

      const gReply = S("g", { class: "dimmable" }, svg);
      const replyBox = card(gReply, 660, 120, 264, 250, V("warn"));
      label(gReply, 680, 156, "HARBOR SEES");
      const replyText = T(gReply, 680, 214, D.harbor_code, 16, { class: "mono", "font-weight": 700, fill: V("warn") });
      const replySub = T(gReply, 680, 252, "own note", 15, { fill: V("ink") });
      const replyMeta = T(gReply, 680, 300, "leak no", 14, { class: "mono", fill: V("muted") });

      const gGate = S("g", {}, svg);
      const gate = S("rect", { x: 660, y: 396, width: 264, height: 0, rx: 12, fill: V("ok"), opacity: 0.16, stroke: V("ok"), "stroke-width": 2 }, gGate);
      const gateText = T(gGate, 680, 432, "", 15, { fill: V("ok"), "font-weight": 700 });

      const st = { mode: 0, leak: 0, defense: 0, focus: 0 };
      const base = { mode: 0, leak: 0, defense: 0, focus: 0 };
      const T_N = [null,
        {},
        { mode: 1, leak: 1, focus: 1 },
        { mode: 1, leak: 1, focus: 1 },
        { mode: 2, leak: 1, focus: 2 },
        { mode: 3, leak: 1, focus: 3 },
        { mode: 4, leak: 1, focus: 4 },
        { mode: 1, leak: 0, defense: 1, focus: 1 },
        { mode: 2, leak: 0, defense: 2, focus: 2 },
        { mode: 3, leak: 0, defense: 3, focus: 3 },
      ];
      const target = n => ({ ...base, ...T_N[n] });

      function draw(s) {
        const mode = Math.round(s.mode);
        const defense = Math.round(s.defense);
        const leak = s.leak >= 0.5 ? 1 : 0;
        const focus = Math.round(s.focus);

        const key = defense === 1 ? "key: principal + question"
          : (mode === 1 ? "key: question only" : "key off");
        const keyNote = defense === 1 ? "Harbor misses Copperleaf’s reply"
          : (mode === 1 ? "Harbor receives the stored body" : "each call searches");
        const filt = (mode === 2 && defense !== 2) ? "tenant filter off" : "tenant filter on";
        const top = (mode === 2 && defense !== 2) ? "top: Copperleaf’s note"
          : (mode === 0 || defense === 2 ? "top: Harbor’s weekend note" : "top doc follows the filter");
        const sess = defense === 3 ? "server id, bound to caller"
          : (mode === 3 ? "shared id, client can type it" : "bound to the caller");
        const sessNote = defense === 3 ? `guesses opened ${C.guesses_opened}/${C.guesses}`
          : (mode === 3 ? "saved turns ride along" : "each shop has its own id");

        let reply = D.harbor_code, sub = "Harbor’s own code", meta = "leak no";
        if (defense === 3) { reply = "No session"; sub = "Harbor is refused"; meta = "leak no"; }
        else if (leak) { reply = D.canary; sub = "Copperleaf’s code"; meta = "leak yes"; }
        else if (mode === 2 && defense === 2) { sub = "nearest note Harbor may read"; }

        A(cacheKey, { text: key, fill: defense === 1 ? V("ok") : (mode === 1 ? V("bad") : V("ink")) });
        A(cacheNote, { text: keyNote });
        A(searchLine, { text: filt, fill: (mode === 2 && defense !== 2) ? V("bad") : (defense === 2 ? V("ok") : V("ink")) });
        A(searchNote, { text: top });
        A(sessionLine, { text: sess, fill: defense === 3 ? V("ok") : (mode === 3 ? V("bad") : V("ink")) });
        A(sessionNote, { text: sessNote });
        A(replyText, { text: reply, fill: leak ? V("lime") : (defense === 3 ? V("ok") : V("warn")) });
        A(replySub, { text: sub });
        A(replyMeta, { text: meta, fill: leak ? V("lime") : V("muted") });
        A(replyBox, { stroke: leak ? V("lime") : (defense ? V("ok") : V("warn")) });
        A(cacheBox, { stroke: mode === 1 ? (defense === 1 ? V("ok") : V("bad")) : V("violet") });
        A(searchBox, { stroke: mode === 2 ? (defense === 2 ? V("ok") : V("bad")) : V("violet") });
        A(sessionBox, { stroke: mode === 3 ? (defense === 3 ? V("ok") : V("bad")) : V("violet") });
        A(copper, { "stroke-width": mode === 0 ? 3 : 1.5 });
        A(harbor, { "stroke-width": focus === 0 ? 3 : 1.5 });
        A(copperCode, { text: D.canary });
        A(harborCode, { text: D.harbor_code });

        const gateOn = defense > 0;
        A(gate, { height: gateOn ? 72 : 0, y: gateOn ? 396 : 468, opacity: gateOn ? 0.16 : 0 });
        A(gateText, { text: gateOn ? ["", "isolated cache key", "tenant filter", "bound session id"][defense] : "" });

        gShops.classList.toggle("hot", focus === 0 || focus === 4);
        gCache.classList.toggle("hot", focus === 1 || focus === 4);
        gSearch.classList.toggle("hot", focus === 2 || focus === 4);
        gSession.classList.toggle("hot", focus === 3 || focus === 4);
        gReply.classList.toggle("hot", true);
        el.classList.toggle("lx-focus", focus > 0);

        const story = [
          "Both shops keep their own notes.",
          "Harbor is served Copperleaf’s cached reply.",
          "Harbor’s search returns Copperleaf’s note.",
          "Harbor reads Copperleaf’s saved turn.",
          "Three bugs put the canary in Harbor’s reply.",
        ][mode] || "";
        svg.setAttribute("aria-label", story);
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }
          return api.tween(560, k => {
            if (g !== gen) return;
            X.lerpState(st, from, to, k);
            draw(st);
          }, X.ease.inOut);
        },
      };
    },
  });
})();
