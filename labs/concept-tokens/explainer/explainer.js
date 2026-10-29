/* LAB-04 concept-tokens: "What the model actually reads" (foundation lab, 8 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One persistent scene: the user's message as typed (top), the token tape the model reads (a grid of
 * real SmolLM2 token pieces, middle) and the control-token counter and model output (bottom). Two
 * overlay panels replace the tape: token counts across tokenizers (step 1) and the Unicode filter
 * table (steps 5 and 8). Every piece, count and output comes from window.LAB_DATA (data.js, exported
 * from the reference workbench run). Pattern: target(n) is pure, draw(s) is pure, step() tweens
 * forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp;
  const D = window.LAB_DATA;
  const H = D.hits, U = D.unicode;
  const rawN = U.filter(r => r[2]).length, normN = U.filter(r => r[4]).length;

  X.define({
    id: "concept-tokens",
    family: "family-prompt",
    title: 'What the model actually <span class="outline">reads</span>',
    legend: [{ role: "teal", label: "App text (trusted)" }, { role: "bad", label: "User-typed text" },
      { role: "violet", label: "Control token" }, { role: "warn", label: "Model output" },
      { role: "lime", label: "Canary" }, { role: "ok", label: "Defense" }],
    steps: [
      { chapter: "System", label: "Text to ids",
        caption: `A model never sees characters. A tokenizer cuts text into pieces from a fixed vocabulary and maps each to an id. The same string costs a different number of tokens in SmolLM2, Qwen2.5 and GPT-2: <code>安全</code> is ${D.counts[2][1]["smollm2"]}, ${D.counts[2][1]["qwen2.5"]} and ${D.counts[2][1]["gpt2"]}.`,
        cmd: "docker compose run --rm workbench python concept-tokens/scripts/s02_count_tokens.py" },
      { chapter: "System", label: "Roles are tokens",
        caption: `The chat template turns messages into one string. Each turn starts with <code>&lt;|im_start|&gt;</code>, a single <span class="c-violet">control token</span> (id 1) that no ordinary text should produce. A clean request has ${D.starts.clean}: system, user, assistant.`,
        cmd: "docker compose run --rm workbench python concept-tokens/scripts/s03_chat_template.py" },
      { chapter: "Attack", label: "Typed delimiters",
        caption: `Risk: the user's message is <span class="c-bad">plain characters</span>, and nothing stops them from typing <code>&lt;|im_end|&gt;</code>, <code>&lt;|im_start|&gt;system</code> and a new instruction into the chat box.`,
        cmd: "docker compose run --rm workbench python concept-tokens/scripts/s04_role_injection.py" },
      { chapter: "Mechanism", label: "Added-token match",
        caption: `By default the tokenizer matches added tokens anywhere in the text, so the typed delimiters become <span class="c-violet">real control tokens</span>. Hand-built ChatML and <code>apply_chat_template()</code> give identical ids: ${D.starts.attack} turn starts, one of them a <span class="c-bad">forged system turn</span>.` },
      { chapter: "Mechanism", label: "Same word, new ids",
        caption: `Filters read characters; the model reads tokens. A zero-width space, soft hyphen, fullwidth letters, a bidi control or a Cyrillic <code>а</code> change the characters of “password”, so a keyword filter catches only ${rawN} of ${U.length} spellings.`,
        cmd: "docker compose run --rm workbench python concept-tokens/scripts/s05_unicode.py" },
      { chapter: "Impact", label: "The canary",
        caption: `Observation: SmolLM2-360M-Instruct obeys the forged system turn and answers with the harmless canary <code class="c-lime">${D.canary}</code> for ${H.template} of 10 attack messages, instead of translating.`,
        cmd: "docker compose run --rm workbench python concept-tokens/scripts/s06_model_reads.py" },
      { chapter: "Defense", label: "Encode as text",
        caption: `<code>sanitize_control_tokens=True</code> (or <code>split_special_tokens=True</code> on the user's text only) encodes typed delimiters as <span class="c-ok">ordinary pieces</span>: back to ${D.starts.sanitized} turn starts, canary ${H.template}/10 → ${H.sanitized}/10. The ${H.sanitized} left are prompt injection as text, which no tokenizer fixes.`,
        cmd: "docker compose run --rm workbench python concept-tokens/scripts/d1_encode_safely.py" },
      { chapter: "Defense", label: "Normalize first",
        caption: `Normalize before filtering: NFKC, drop format characters, casefold. Recall goes from ${rawN}/${U.length} to <span class="c-ok">${normN}/${U.length}</span>. The <span class="c-bad">Cyrillic а</span> is a different letter, not a format trick, so it still passes: keyword filters are a weak layer.`,
        cmd: "docker compose run --rm workbench python concept-tokens/scripts/d2_normalize.py" },
    ],
    html: `<style>[data-explainer="concept-tokens"] svg text, [data-explainer="concept-tokens"] code { font-variant-ligatures: none; font-feature-settings: "liga" 0, "calt" 0; }</style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="User message, token tape and model output"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line")) => S("rect", { x, y, width: w, height: h, rx: 14, fill: V("panel"), stroke, "stroke-width": 2 }, p);
      const short = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

      // ---- top: the user's message as typed ----
      const gIn = S("g", { class: "dimmable" }, svg);
      label(gIn, 30, 26, "USER MESSAGE, AS TYPED");
      const inBox = card(gIn, 30, 36, 900, 62);
      const typed = D.user_typed.replace(/\n/g, "\\n");
      const cut = typed.lastIndexOf(" ", 96);
      const inA = T(gIn, 48, 62, typed.slice(0, cut), 14, { class: "mono" });
      const inB = T(gIn, 48, 84, short(typed.slice(cut + 1), 96), 14, { class: "mono" });
      const inClean = T(gIn, 48, 73, D.user_typed.split("<|")[0], 15, { class: "mono", fill: V("teal") });

      // ---- middle: token tapes (one group per tape, cross-faded) ----
      const COLS = 18, CW = 50, CH = 30, X0 = 30, Y0 = 136;
      label(svg, 30, 126, "WHAT THE MODEL READS: ONE CELL PER TOKEN");
      const tapes = {};
      for (const [name, cells] of Object.entries(D.tapes)) {
        const g = S("g", {}, svg);   // not .dimmable: focus dimming would override the cross-fade opacity
        cells.forEach(([piece, kind, role, atk], i) => {
          const x = X0 + (i % COLS) * CW, y = Y0 + Math.floor(i / COLS) * (CH + 4);
          const ctl = kind === "c";
          const col = ctl ? "violet" : atk ? "bad" : "teal";
          const r = S("rect", { x, y, width: CW - 4, height: CH, rx: 6, fill: V(col),
            "fill-opacity": ctl ? .85 : .13, stroke: V(atk ? "bad" : col), "stroke-width": atk && ctl ? 3 : 1.2 }, g);
          const txt = ctl ? (piece === "<|im_start|>" ? "start" : "end") : short(piece, 6);
          T(g, x + (CW - 4) / 2, y + 20, txt, 13, { class: "mono", "text-anchor": "middle",
            fill: ctl ? V("bg") : V(col), "font-weight": kind === "r" || ctl ? 800 : 400 });
          if (ctl) r.setAttribute("data-ctl", "1");
        });
        tapes[name] = g;
      }

      // ---- bottom: counter and output ----
      const gCnt = S("g", { class: "dimmable" }, svg);
      card(gCnt, 30, 400, 300, 120);
      label(gCnt, 50, 428, "<|im_start|> TOKENS");
      const cntTxt = T(gCnt, 50, 486, "", 44, { class: "mono", "font-weight": 800 });
      const cntSub = T(gCnt, 132, 484, "", 14, { fill: V("muted") });
      const gOut = S("g", { class: "dimmable" }, svg);
      const outBox = card(gOut, 350, 400, 580, 120);
      label(gOut, 370, 428, "MODEL OUTPUT (SmolLM2-360M-Instruct, greedy)");
      const outTxt = T(gOut, 370, 470, "", 22, { class: "mono", "font-weight": 700 });
      const outSub = T(gOut, 370, 502, "", 14, { fill: V("muted") });
      const gate = S("rect", { x: 22, y: 132, width: 6, height: 0, rx: 3, fill: V("ok") }, svg);

      // ---- overlay 1: token counts across tokenizers ----
      const gCount = S("g", {}, svg);
      card(gCount, 30, 112, 900, 408);
      label(gCount, 50, 144, "SAME STRING, THREE TOKENIZERS");
      ["smollm2", "qwen2.5", "gpt2"].forEach((n, j) => T(gCount, 700 + j * 76, 144, n, 13, { class: "mono", fill: V("violet"), "font-weight": 700, "text-anchor": "middle" }));
      D.counts.forEach(([s, counts, pieces], i) => {
        const y = 182 + i * 84;
        T(gCount, 50, y + 6, JSON.stringify(s), 16, { class: "mono", fill: s === D.canary ? V("lime") : V("teal"), "font-weight": 700 });
        pieces.forEach((p, k) => {
          const x = 50 + k * 50;
          S("rect", { x, y: y + 20, width: 46, height: 30, rx: 6, fill: V("teal"), "fill-opacity": .13, stroke: V("teal"), "stroke-width": 1.2 }, gCount);
          T(gCount, x + 23, y + 40, short(p.replace(/�/g, "·"), 5), 13, { class: "mono", "text-anchor": "middle", fill: V("teal") });
        });
        ["smollm2", "qwen2.5", "gpt2"].forEach((n, j) => T(gCount, 700 + j * 76, y + 42, String(counts[n]), 22, { class: "mono", "font-weight": 800, "text-anchor": "middle" }));
      });
      T(gCount, 50, 506, "cells: SmolLM2 pieces (· = part of a multi-byte character)", 13, { fill: V("muted") });

      // ---- overlay 2: Unicode spellings vs a keyword filter ----
      const gUni = S("g", {}, svg);
      card(gUni, 30, 112, 900, 408);
      label(gUni, 50, 144, "“PLEASE RESET MY PASSWORD.”  SEVEN SPELLINGS");
      const hx = [50, 260, 360, 520, 720];
      ["spelling", "tokens", "raw filter", "model read it", "normalized filter"].forEach((h, j) => T(gUni, hx[j], 176, h, 13, { fill: V("muted"), "font-weight": 700 }));
      const normCells = [];
      U.forEach(([name, ntok, blocked, understood, norm], i) => {
        const y = 196 + i * 44;
        T(gUni, hx[0], y + 22, name, 16, name === "cyrillic a" ? { class: "mono", fill: V("bad") } : { class: "mono" });
        T(gUni, hx[1], y + 22, String(ntok), 16, { class: "mono", "font-weight": 700 });
        const col = blocked ? "ok" : "bad";
        S("rect", { x: hx[2], y: y + 4, width: 120, height: 28, rx: 7, fill: V(col), "fill-opacity": .16, stroke: V(col) }, gUni);
        T(gUni, hx[2] + 60, y + 23, blocked ? "BLOCKED" : "passes", 14, { "text-anchor": "middle", fill: V(col), "font-weight": 700 });
        T(gUni, hx[3], y + 22, blocked ? "—" : understood ? "yes: “mot de passe”" : "no", 14, { fill: understood ? V("warn") : V("muted") });
        const nc = S("g", {}, gUni);
        const ncol = norm ? "ok" : "bad";
        S("rect", { x: hx[4], y: y + 4, width: 150, height: 28, rx: 7, fill: V(ncol), "fill-opacity": .16, stroke: V(ncol) }, nc);
        T(nc, hx[4] + 75, y + 23, norm ? "BLOCKED" : "passes", 14, { "text-anchor": "middle", fill: V(ncol), "font-weight": 700 });
        normCells.push(nc);
      });
      const recall = T(gUni, 50, 508, "", 15, { "font-weight": 700 });

      // ---- state ----
      const base = { count: 0, cIn: 0, atk: 0, tClean: 0, tAtk: 0, tSan: 0, uni: 0, norm: 0, out: 0, canary: 0, def: 0 };
      const T_N = [null,
        { count: 1 },                                   // 1 counts across tokenizers
        { cIn: 1, tClean: 1, out: 1 },                  // 2 clean template tape
        { atk: 1, tClean: 1 },                          // 3 attacker types delimiters
        { atk: 1, tAtk: 1 },                            // 4 they become control tokens
        { uni: 1 },                                     // 5 unicode filter table
        { atk: 1, tAtk: 1, out: 1, canary: 1 },         // 6 canary
        { atk: 1, tSan: 1, out: 1, canary: 1, def: 1 }, // 7 sanitized
        { uni: 1, norm: 1, def: 1 },                    // 8 normalized filter
      ];
      const st = { ...base };
      const target = n => ({ ...base, ...T_N[n] });

      function draw(s) {
        const tape = 1 - Math.max(s.count, s.uni);
        A(gCount, { opacity: s.count.toFixed(3) });
        A(gUni, { opacity: s.uni.toFixed(3) });
        A(gIn, { opacity: tape.toFixed(3) });
        A(gCnt, { opacity: tape.toFixed(3) });
        A(gOut, { opacity: (tape * s.out).toFixed(3) });
        const hot = s.canary > .5 && s.def < .5;   // the canary step focuses the output
        const dim = hot ? .25 : 1;
        A(tapes.clean, { opacity: (dim * tape * s.tClean).toFixed(3) });
        A(tapes.attack, { opacity: (dim * tape * s.tAtk).toFixed(3) });
        A(tapes.sanitized, { opacity: (dim * tape * s.tSan).toFixed(3) });
        A(inClean, { opacity: (1 - s.atk).toFixed(3) });
        A(inA, { opacity: s.atk.toFixed(3), fill: V("bad") });
        A(inB, { opacity: s.atk.toFixed(3), fill: V("bad") });
        A(inBox, { stroke: s.atk > .5 ? V("bad") : V("line") });
        // counter: clean / attack / sanitized
        const which = s.tSan > .5 ? "sanitized" : s.tAtk > .5 ? "attack" : "clean";
        cntTxt.textContent = String(D.starts[which]);
        A(cntTxt, { fill: which === "attack" ? V("bad") : which === "sanitized" ? V("ok") : V("violet") });
        cntSub.textContent = which === "attack" ? "2 forged by the user" : which === "sanitized" ? "typed ones encoded as text" : "system · user · assistant";
        // output
        if (s.canary > .5) {
          outTxt.textContent = D.out.attack;
          A(outTxt, { fill: V("lime") }); A(outBox, { stroke: V(s.def > .5 ? "ok" : "lime") });
          outSub.textContent = s.def > .5
            ? `canary ${H.sanitized}/10 attack messages (was ${H.template}/10); clean requests still translate`
            : `canary ${H.template}/10 attack messages, default template`;
          if (s.def > .5) { outTxt.textContent = `${H.template}/10 → ${H.sanitized}/10  ${D.canary}`; A(outTxt, { fill: V("ok") }); }
        } else {
          outTxt.textContent = D.out.clean;
          A(outTxt, { fill: V("warn") }); A(outBox, { stroke: V("line") });
          outSub.textContent = "clean request: the app translates";
        }
        // defense gate beside the tape, and the normalized column
        A(gate, { height: (240 * s.def * tape).toFixed(2) });
        normCells.forEach(c => A(c, { opacity: s.norm.toFixed(3) }));
        recall.textContent = s.norm > .5 ? `recall: raw ${rawN}/${U.length} → normalized ${normN}/${U.length}` : `raw filter recall: ${rawN}/${U.length}`;
        A(recall, { fill: s.norm > .5 ? V("ok") : V("bad") });
        // focus: on the canary step, the output is hot
        [gIn, gCnt].forEach(g => g.classList.toggle("hot", !hot));
        gOut.classList.toggle("hot", true);
        el.classList.toggle("lx-focus", hot);
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          return api.tween(650, k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
