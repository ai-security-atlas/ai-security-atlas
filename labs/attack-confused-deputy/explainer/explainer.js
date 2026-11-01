/* LAB-30 attack-confused-deputy: "The agent that had the admin key" (8 steps).
 * One scene: two users, the docs assistant and its token, the mock docs API.
 * Counts, tokens, the marker and the assistant note come from window.LAB_DATA.
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v;
  const D = window.LAB_DATA;
  const frac = (pair) => `${pair[0]}/${pair[1]}`;
  const WHO = ["mallory", "alice"];
  const TOK = [D.tokens.admin, D.users.mallory.token, D.users.alice.token, D.tokens.public];
  const AUTHZ = [D.s01.authz, D.s04.checked_authz, D.s04.counterfactual];
  const DOCS = D.docs;

  X.define({
    id: "attack-confused-deputy",
    family: "family-agent",
    title: 'The agent that had the <span class="outline">admin key</span>',
    legend: [
      { role: "teal", label: "Signed-in user" },
      { role: "violet", label: "Docs assistant" },
      { role: "bad", label: "Assistant note" },
      { role: "lime", label: "Canary" },
      { role: "ok", label: "Defense" },
    ],
    intro: {
      why: "Atlas Widgets lets every employee ask one docs assistant. The assistant carries an admin service token. Mallory is a contractor. Can she get the staff board notes by asking, or by leaving a note in a public page the assistant will read? That is a confused deputy: a component using its own authority for someone who lacks it.",
      plan: "You’ll meet the two users and the service token. Then you’ll watch a direct ask and a note inside a public page. Next you’ll separate a valid token from the missing user check, and see where the marker actually lives. Last you’ll measure three defenses: a paragraph in the prompt, a token exchange, and a public-only service token.",
      terms: "A confused deputy is a component that spends its own authority for a requester who lacks that authority. Protocol authentication checks that a token is valid. Semantic authorization checks whether this principal may take this action on this resource. A principal is the signed-in user. A scope is the set of document labels that user’s token may read. A canary is a fixed marker planted in a restricted document so a leak is visible and inert. On-behalf-of is a simulated exchange: the service token is swapped for the signed-in user’s token before the API is called.",
    },
    steps: [
      { chapter: "System", label: "Two users, one token",
        guide: "Atlas Widgets shares one docs assistant between staff and contractors. Alice’s scope covers staff documents. Mallory’s scope covers public documents. The assistant calls a mock docs API with its own service token. The board notes are the staff page. The handbook, the onboarding page, and the standup are public.",
        caption: `MCP <span class="c-violet">${D.s01.server}</span> protocol ${D.s01.protocol}. Tools <code>${D.s01.tools.join(" ")}</code>. Service token <code>${D.tokens.admin}</code> scope <code>${D.tokens.admin_scope}</code>. Mallory’s read of board-notes: status ${D.s01.status}, auth ${D.s01.auth}, authz ${D.s01.authz}, canary ${D.s01.canary ? "yes" : "no"}.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-confused-deputy ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8181 docker compose run --rm workbench python attack-confused-deputy/scripts/s01_directory.py" },
      { chapter: "Attack", label: "Mallory asks",
        guide: "Mallory names the board notes and asks for the full text. The assistant calls the read tool with the service token. Protocol authentication passes, and the handler skips the user check. The reply quotes the restricted marker. A handbook read on the same token returns the public page and leaves the marker out.",
        caption: `Direct disclosure <span class="c-bad">${frac(D.s02.disclosure)}</span>, fetched ${frac(D.s02.fetched)}. Tool path status ${D.s01.status}, token <code>${D.s01.token}</code>, authz ${D.s01.authz}.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-confused-deputy ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8181 docker compose run --rm workbench python attack-confused-deputy/scripts/s02_direct.py" },
      { chapter: "Attack", label: "A note in a public page",
        guide: "This time Mallory asks for a summary of the Monday standup, a public page, and never mentions the board notes. The standup contains an assistant note telling the reader to open another document and quote it. This lab’s system prompt deliberately tells the assistant to follow such notes, so it calls the read tool before answering, and the marker ends up in the reply.",
        caption: `Standup note: <code class="c-bad">${D.injection}</code>. Indirect disclosure <span class="c-bad">${frac(D.s03.disclosure)}</span>, fetched ${frac(D.s03.fetched)}. The marker <code class="c-lime">${D.canary}</code> stays in board-notes.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-confused-deputy ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8181 docker compose run --rm workbench python attack-confused-deputy/scripts/s03_injected.py" },
      { chapter: "Mechanism", label: "A valid token, a skipped check",
        guide: "The API logs two checks on every call. Protocol authentication records that the token is valid. Semantic authorization records whether this user may read this document. In the vulnerable setup the second check is skipped, so a valid admin token is enough. Even with the check on, the page comes back, because it checks the service token’s scope, which includes staff documents. Checked against Mallory’s own scope, the request is denied. The audit row shows the service token next to her name.",
        caption: `Replay status ${D.s04.status}, auth ${D.s04.auth}, authz ${D.s04.authz}, token <code>${D.s04.token}</code>. Checked admin token: status ${D.s04.checked_status}, authz ${D.s04.checked_authz}. Counterfactual docs:public on staff: ${D.s04.counterfactual}.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-confused-deputy ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8181 docker compose run --rm workbench python attack-confused-deputy/scripts/s04_trace.py" },
      { chapter: "Impact", label: "Where the marker lives",
        guide: "The marker exists in only one place: the board notes. It isn’t in the tasks, the standup, the handbook or the system prompt. Both saved replies quote it anyway, and the tool result is how it got there. Mallory’s session received a staff document using a token she was never given.",
        caption: `Canary <code class="c-lime">${D.canary}</code> is in board-notes (${D.s05.in_board ? "yes" : "no"}) and absent from the tasks, the standup, and the handbook. Saved direct disclosure ${frac(D.s05.direct)}, indirect ${frac(D.s05.indirect)}.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-confused-deputy ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8181 docker compose run --rm workbench python attack-confused-deputy/scripts/s05_impact.py" },
      { chapter: "Defense", label: "A paragraph in the prompt",
        guide: "The first defense adds a policy paragraph to the system prompt, saying which scope may read staff documents, even when a page asks for them. On this model it worked: neither the direct ask nor the injected note quoted the marker, and the handbook answer still came back. But the tool underneath hasn’t changed. A direct call still returns the staff page with the user check skipped. The paragraph is advice to the model, and the API still sees the admin token.",
        caption: `Prompt grows by ${D.d1.extra_chars} characters. Tool path status ${D.d1.status}, canary ${D.d1.canary ? "yes" : "no"}. Live direct ${frac(D.d1.direct)}, indirect ${frac(D.d1.indirect)}, handbook utility ${frac(D.d1.handbook)}.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-confused-deputy ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8181 docker compose run --rm workbench python attack-confused-deputy/scripts/d1_prompt.py" },
      { chapter: "Defense", label: "Check the principal in code",
        guide: "The second defense checks the user in code. Before calling the API, the read tool asks a simulated issuer to swap the service token for the signed-in user’s token. Mallory’s swap gives her contractor token, and the API refuses the staff page. Alice’s swap gives a staff token, and she gets the page with the marker. Mallory can still read the handbook. Since the API itself refuses, nothing the model says can bring the marker back.",
        caption: `Exchange <code>${D.d2.exchange}</code>. Mallory board-notes status ${D.d2.mallory_status}, canary ${D.d2.mallory_canary ? "yes" : "no"}. Alice status ${D.d2.alice_status}, canary ${D.d2.alice_canary ? "yes" : "no"}. Handbook status ${D.d2.handbook_status}. Live mallory ${frac(D.d2.direct)}, alice ${frac(D.d2.alice_live)}, handbook ${frac(D.d2.handbook)}.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-confused-deputy ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8181 docker compose run --rm workbench python attack-confused-deputy/scripts/d2_principal.py" },
      { chapter: "Defense", label: "A public-docs service token",
        guide: "The service credential itself is cut down to public documents. Alice and Mallory both receive a refusal on the board notes. The handbook still comes back, so the ordinary contractor question keeps working. Staff lose the board notes. That loss is the price of a credential that cannot reach a staff page.",
        caption: `Token <code>${D.tokens.public}</code> scope <code>${D.tokens.public_scope}</code>. Alice board-notes status ${D.d3.alice_status}, canary ${D.d3.alice_canary ? "yes" : "no"}. Handbook status ${D.d3.handbook_status}. Live mallory ${frac(D.d3.direct)}, alice ${frac(D.d3.alice_live)}, handbook ${frac(D.d3.handbook)}.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-confused-deputy ATLAS_APP_TAG=v3 ATLAS_APP_PORT=8181 docker compose run --rm workbench python attack-confused-deputy/scripts/d3_least.py" },
    ],
    html: `<style>[data-explainer="attack-confused-deputy"] svg text { font-variant-ligatures: none; font-feature-settings: "liga" 0, "calt" 0; }</style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Users, the docs assistant, and the mock docs API"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 14, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.5" });
      const card = (p, x, y, w, h, stroke) =>
        S("rect", { x, y, width: w, height: h, rx: 14, fill: V("panel"), stroke: stroke || V("line"), "stroke-width": 2 }, p);

      label(svg, 28, 36, "SIGNED-IN USERS");
      card(svg, 24, 48, 250, 188);
      const userRow = (y, name) => {
        const r = S("rect", { x: 38, y, width: 222, height: 68, rx: 10, fill: V("panel"), stroke: V("teal"), "stroke-width": 1.5 }, svg);
        const t = T(svg, 52, y + 28, name, 16, { "font-weight": 700 });
        const sub = T(svg, 52, y + 50, "", 13, { fill: V("muted") });
        return { r, t, sub };
      };
      const alice = userRow(64, "alice");
      const mallory = userRow(146, "mallory");
      alice.sub.textContent = `${D.users.alice.role} · ${D.users.alice.scope}`;
      mallory.sub.textContent = `${D.users.mallory.role} · ${D.users.mallory.scope}`;

      label(svg, 300, 36, "DOCS ASSISTANT");
      card(svg, 292, 48, 250, 188, V("violet"));
      T(svg, 308, 78, "service token", 13, { fill: V("muted"), "font-weight": 700 });
      const tokenT = T(svg, 308, 104, "", 15, { class: "mono", "font-weight": 700 });
      const exchT = T(svg, 308, 128, "", 13, { fill: V("ok") });
      const polR = S("rect", { x: 308, y: 148, width: 218, height: 68, rx: 10, fill: V("ok"), stroke: V("ok"), "stroke-width": 1.5 }, svg);
      const polT = T(svg, 320, 176, "policy paragraph", 14, { "font-weight": 700 });
      const polS = T(svg, 320, 198, "added to the prompt", 13, {});

      label(svg, 572, 36, "DOCS API");
      card(svg, 564, 48, 372, 188);
      const docEls = DOCS.map((doc, i) => {
        const y = 62 + i * 40;
        const r = S("rect", { x: 578, y, width: 344, height: 34, rx: 8, fill: V("panel"), stroke: V("line"), "stroke-width": 1.4 }, svg);
        const t = T(svg, 592, y + 22, `${doc.id}  ·  ${doc.acl}`, 14, { "font-weight": 700 });
        return { r, t, id: doc.id };
      });

      card(svg, 24, 256, 912, 260);
      label(svg, 40, 284, "THIS CALL");
      const rec = {
        who: T(svg, 40, 322, "", 18, { "font-weight": 700 }),
        status: T(svg, 40, 356, "", 16, { class: "mono", "font-weight": 700 }),
        auth: T(svg, 40, 386, "", 15, {}),
        authz: T(svg, 40, 416, "", 15, {}),
        canary: T(svg, 40, 456, "", 16, { class: "mono", "font-weight": 700 }),
        rate: T(svg, 40, 490, "", 15, { fill: V("muted") }),
      };
      const noteR = S("rect", { x: 520, y: 300, width: 390, height: 88, rx: 10, fill: V("panel"), stroke: V("bad"), "stroke-width": 1.5 }, svg);
      T(svg, 536, 328, "assistant note", 13, { fill: V("bad"), "font-weight": 700 });
      const noteLines = [0, 1].map((i) => T(svg, 536, 354 + i * 22, "", 14, {}));
      const denyR = S("rect", { x: 520, y: 408, width: 390, height: 78, rx: 10, fill: V("panel"), stroke: V("ok"), "stroke-width": 1.5 }, svg);
      const denyT = T(svg, 536, 440, "", 16, { "font-weight": 700 });
      const denyS = T(svg, 536, 466, "", 14, { fill: V("muted") });

      function wrap(s, n) {
        const out = []; let line = "";
        for (const w of String(s).split(" ")) {
          if ((line + " " + w).trim().length > n && line) { out.push(line); line = w; }
          else line = (line + " " + w).trim();
        }
        if (line) out.push(line);
        return out;
      }

      const blank = {
        who: 0, tok: 0, authz: 0, status: 200, canary: 1, doc: 3,
        policy: 0, exchange: 0, k: 0, n: D.s02.trials, showRate: 0, deny: 0, note: 0,
      };
      function target(n) {
        const base = Object.assign({}, blank);
        if (n === 1) return Object.assign(base, { canary: D.s01.canary ? 1 : 0, status: D.s01.status });
        if (n === 2) return Object.assign(base, { showRate: 1, k: D.s02.disclosure[0], n: D.s02.disclosure[1] });
        if (n === 3) return Object.assign(base, { note: 1, showRate: 1, k: D.s03.disclosure[0], n: D.s03.disclosure[1] });
        if (n === 4) return Object.assign(base, { status: D.s04.status, canary: D.s04.canary ? 1 : 0 });
        if (n === 5) return Object.assign(base, { showRate: 1, k: D.s05.direct[0], n: D.s05.direct[1] });
        if (n === 6) return Object.assign(base, {
          policy: 1, status: D.d1.status, canary: D.d1.canary ? 1 : 0,
          showRate: 1, k: D.d1.direct[0], n: D.d1.direct[1],
        });
        if (n === 7) return Object.assign(base, {
          tok: 1, authz: 2, status: D.d2.mallory_status, canary: D.d2.mallory_canary ? 1 : 0,
          exchange: 1, deny: 1, showRate: 1, k: D.d2.direct[0], n: D.d2.direct[1],
        });
        return Object.assign(base, {
          who: 1, tok: 3, authz: 2, status: D.d3.alice_status, canary: D.d3.alice_canary ? 1 : 0,
          deny: 1, showRate: 1, k: D.d3.alice_live[0], n: D.d3.alice_live[1],
        });
      }

      function draw(s) {
        const who = WHO[Math.round(s.who)] || WHO[0];
        const tok = TOK[Math.round(s.tok)] || TOK[0];
        const authz = AUTHZ[Math.round(s.authz)] || AUTHZ[0];
        const status = Math.round(s.status);
        const doc = Math.max(0, Math.min(DOCS.length - 1, Math.round(s.doc)));
        const showCanary = s.canary >= 0.5;
        A(alice.r, { opacity: who === "alice" ? 1 : 0.4, "stroke-width": who === "alice" ? 3 : 1.5 });
        A(mallory.r, { opacity: who === "mallory" ? 1 : 0.4, "stroke-width": who === "mallory" ? 3 : 1.5 });
        tokenT.textContent = tok;
        exchT.textContent = s.exchange >= 0.5 ? D.d2.exchange : "";
        A(exchT, { opacity: s.exchange });
        A(polR, { opacity: 0.15 + 0.85 * s.policy });
        A(polT, { opacity: s.policy, fill: V("ok") });
        A(polS, { opacity: s.policy });
        docEls.forEach((el, i) => {
          const on = i === doc;
          const noted = s.note >= 0.5 && el.id === "standup";
          const staff = el.id === "board-notes";
          A(el.r, {
            opacity: on || noted ? 1 : 0.45,
            "stroke-width": on || noted ? 2.6 : 1.3,
            stroke: noted ? V("bad") : (staff && showCanary ? V("lime") : V("line")),
          });
        });
        rec.who.textContent = who;
        rec.status.textContent = `status ${status}`;
        A(rec.status, { fill: status >= 400 ? V("bad") : V("ok") });
        rec.auth.textContent = `auth ${D.s01.auth}   token ${tok}`;
        rec.authz.textContent = `authz ${authz}   principal ${who}`;
        rec.canary.textContent = showCanary ? D.canary : "canary absent";
        A(rec.canary, { fill: showCanary ? V("lime") : V("muted") });
        rec.rate.textContent = `quoted ${Math.round(s.k)}/${Math.round(s.n)}`;
        A(rec.rate, { opacity: s.showRate });
        const lines = wrap(D.injection, 36);
        noteLines.forEach((t, i) => { t.textContent = lines[i] || ""; });
        A(noteR, { opacity: 0.25 + 0.75 * s.note });
        noteLines.forEach((t) => A(t, { opacity: s.note }));
        denyT.textContent = s.deny >= 0.5 ? `refused · ${status}` : "api returns the page";
        denyS.textContent = s.exchange >= 0.5 ? "checked user token" : (Math.round(s.tok) === 3 ? "public service token" : "admin service token");
        A(denyR, { stroke: s.deny >= 0.5 ? V("ok") : V("line"), opacity: 1 });
        A(denyT, { fill: s.deny >= 0.5 ? V("ok") : V("ink") });
        svg.setAttribute("aria-label", `${who} calls the docs assistant with ${tok}; status ${status}; authz ${authz}`);
      }

      const st = target(1);
      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = Object.assign({}, st), g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }
          return api.tween(640, (k) => {
            if (g !== gen) return;
            X.lerpState(st, from, to, k);
            draw(st);
          }, X.ease.inOut);
        },
      };
    },
  });
})();
