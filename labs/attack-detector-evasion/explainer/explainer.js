/* LAB-36 attack-detector-evasion. Nine steps.
 * One stage: the message, two detectors, and the app that would answer it.
 * target(n) is pure, draw(s) is pure, step() tweens forward by one and snaps otherwise.
 * Numbers and payload strings come from window.LAB_DATA. */
(() => {
  const X = Explainer, S = X.svg, V = X.v;
  const D = window.LAB_DATA;

  const row = name => D.chars.rows.find(r => r.name === name);
  const clip = (s, n) => {
    s = String(s || "");
    return s.length > n ? s.slice(0, n - 1) + "…" : s;
  };
  const frac = (k, n) => (n ? k / n : 0);

  X.define({
    id: "attack-detector-evasion",
    family: "family-evasion",
    title: 'Slipping past a <span class="outline">detector</span>',
    legend: [
      { role: "teal", label: "Neural detector" },
      { role: "violet", label: "Linear detector" },
      { role: "bad", label: "Label flipped to SAFE" },
      { role: "warn", label: "Still flagged" },
      { role: "lime", label: "Canary in the answer" },
      { role: "ok", label: "Defense" },
    ],
    intro: {
      why: "A prompt-injection detector is supposed to stop a user message that tries to replace the app’s task. This lab asks whether small edits to that message can make one detector call it safe while the message still asks for a fixed marker.",
      plan: "You score the same fictional messages on two detectors. Then you edit characters under a query budget, attack a simpler stand-in model with its own weights, and check whether a missed message still produces the marker. Last, you measure three defenses and what each one costs.",
      terms: "A detector here is a classifier with two labels, SAFE and INJECTION. A query is one label you are allowed to read. The canary is a fixed harmless string the message asks the app to print. Evasion means a message that was labeled INJECTION becomes SAFE, and a reader can still see the request.",
    },
    steps: [
      { chapter: "System", label: "Two detectors",
        guide: "Two detectors score the same fictional messages. The neural detector is the published prompt-injection classifier that guarded the app in the arch-encoder lab. The linear detector is a word-counting model trained here on a small labeled set. A message is flagged when its INJECTION score is at least one half. Check both detectors on injections and on ordinary messages before changing anything. If a detector already misses a message, later edits get no credit for it.",
        caption: `Neural guardrail <code>${D.guard.repo}</code> @ <code>${D.guard.rev}</code>, ${D.guard.params_m}M parameters, flag at ${D.guard.threshold}. It flags <span class="c-warn">${D.neural.inj[0]}/${D.neural.inj[1]}</span> injections and <span class="c-warn">${D.neural.ben[0]}/${D.neural.ben[1]}</span> benign strings. The linear model (${D.linear.train_n} rows, ${D.linear.features} features) flags <span class="c-violet">${D.linear.inj[0]}/${D.linear.inj[1]}</span> injections and ${D.linear.ben[0]}/${D.linear.ben[1]} benign strings.`,
        cmd: "docker compose run --rm workbench python attack-detector-evasion/scripts/s01_detectors.py" },
      { chapter: "Attack", label: "Character edits",
        guide: "Each edit rewrites the instruction words and leaves the marker as one unbroken word. Homoglyphs swap letters for look-alikes. Full-width forms use wide characters. Leetspeak swaps letters for digits. A zero-width character sits between letters. Spacing splits a word into single letters. You get one label per message per edit. Count a message as evaded only when its clean label was INJECTION and the edited label is SAFE. Watch which detector each edit fools.",
        caption: `Clean neural flags <span class="c-teal">${row("none").neural}/${row("none").n}</span>. Homoglyphs leave ${row("homoglyphs").neural}/${row("homoglyphs").n} flagged. Leetspeak leaves <span class="c-bad">${row("leetspeak").neural}/${row("leetspeak").n}</span>. Zero-width leaves the neural detector at ${row("zero-width").neural}/${row("zero-width").n} and the linear model at <span class="c-bad">${row("zero-width").linear}/${row("zero-width").n}</span>. Every edited string still reads as a request (${row("leetspeak").functional}/${row("leetspeak").n}).`,
        cmd: "docker compose run --rm workbench python attack-detector-evasion/scripts/s02_characters.py" },
      { chapter: "Attack", label: "Query budget",
        guide: "Now the attacker can only read the label, SAFE or INJECTION, and has a fixed number of queries per message. The search tries the clean message, then each full-string edit, then a short list of paraphrases, and stops at the first SAFE. On most injections it finds one, so the neural detector can be evaded without seeing any scores. The median number of queries shows how cheap that was.",
        caption: `Budget ${D.budget}. The search evades <span class="c-bad">${D.search.evaded}/${D.search.n}</span> (functional ${D.search.functional_evaded}/${D.search.evaded}). Median queries ${D.search.median_queries} (min ${D.search.min_queries}, max ${D.search.max_queries}). Paraphrase-only, ${D.search.n_paraphrases} templates: evaded ${D.search.paraphrase_evaded ? "yes" : "no"} in ${D.search.paraphrase_queries} queries. One result, phase ${D.search.example_phase}, ${D.search.example_queries} queries: <code>${clip(D.search.example, 72)}</code>`,
        cmd: "docker compose run --rm workbench python attack-detector-evasion/scripts/s03_search.py" },
      { chapter: "Mechanism", label: "Two readers",
        guide: "The two detectors fail on different edits, and the reason is how each one reads text. The neural model uses a subword tokenizer, so a digit standing in for a letter can hide a word it learned. The linear model splits on word characters, so a zero-width mark or a space between letters breaks the words it was trained on. Look-alike letters and digits still look like words to that splitter. Use the two columns to see which failure belongs to which reader.",
        caption: `Neural flagged / linear flagged, out of ${row("none").n}. none ${row("none").neural}/${row("none").linear}. homoglyphs ${row("homoglyphs").neural}/${row("homoglyphs").linear}. full-width ${row("full-width").neural}/${row("full-width").linear}. leetspeak ${row("leetspeak").neural}/${row("leetspeak").linear}. zero-width ${row("zero-width").neural}/${row("zero-width").linear}. spaced ${row("spaced").neural}/${row("spaced").linear}.` },
      { chapter: "Mechanism", label: "Word saliency",
        guide: "This attack can see the linear model’s weights, which is white-box access, and only for that model. A word’s saliency is how much the injection score drops when the word is deleted. The attack swaps the most salient word for a synonym that lowers the score, and keeps the swap only if the marker and the command still read clearly. Each result is then scored once on the neural detector. Those flips don’t carry over: beating the stand-in model didn’t beat the real one.",
        caption: `Linear flips <span class="c-violet">${D.saliency.flipped}/${D.saliency.n}</span> (functional ${D.saliency.functional_flipped}/${D.saliency.flipped}). The neural target still flags <span class="c-teal">${D.saliency.neural_flagged}/${D.saliency.n}</span>. Median surrogate evaluations ${D.saliency.median_evals}. One flip: ${D.saliency.example_swaps.map(s => s.from + "→" + s.to).join(", ") || "(none)"}.`,
        cmd: "docker compose run --rm workbench python attack-detector-evasion/scripts/s04_saliency.py" },
      { chapter: "Impact", label: "The marker returns",
        guide: "A small deterministic follower stands in for a chat model so this check repeats without a network call. If the message still reads as an instruction to emit the marker, the follower emits it. The detector gate refuses any message the neural model flags. The boundary app treats the message as data and drops any answer that contains the marker. Count how many search results the detector gate releases, and whether the boundary releases any.",
        caption: `The follower’s marker is <code class="c-lime">${D.canary}</code>. The search evades ${D.search.evaded}/${D.search.n}. The detector gate releases the marker for <span class="c-bad">${D.function.released}/${D.function.n}</span> final strings, including any string the neural model already called SAFE. The boundary app releases it for ${D.function.boundary_released}/${D.function.n}. Warranty answer kept: ${D.function.warranty_ok ? "yes" : "no"}. Marker answer blocked: ${D.function.marker_blocked ? "yes" : "no"}.`,
        cmd: "docker compose run --rm workbench python attack-detector-evasion/scripts/s05_function.py" },
      { chapter: "Defense", label: "Canonicalize",
        guide: "The first defense rewrites each message before the neural detector scores it. Canonicalization applies Unicode NFKC, drops invisible format characters such as zero-width marks, and maps this lab’s Cyrillic look-alikes back to Latin letters. Score the same edits again. Look-alike and zero-width edits are caught again. Digit-for-letter swaps and spaced-out letters are plain characters, so they pass through unchanged. Check the cost too: how many ordinary messages the rewrite alters.",
        caption: `After normalize, homoglyphs are flagged ${D.d1.rows.find(r => r.name === "homoglyphs").norm}/${D.d1.rows.find(r => r.name === "homoglyphs").n} and zero-width ${D.d1.rows.find(r => r.name === "zero-width").norm}/${D.d1.rows.find(r => r.name === "zero-width").n}. Untouched edits: ${D.d1.unchanged_ops.join(", ") || "none"}. Benign strings rewritten: ${D.d1.benign_changed}/${D.d1.benign_n}. Normalize time ${D.d1.norm_ms} ms/string.`,
        cmd: "docker compose run --rm workbench python attack-detector-evasion/scripts/d1_canonicalize.py" },
      { chapter: "Defense", label: "Retrain, then adapt",
        guide: "The second defense retrains the linear model, adding the edited messages it had called SAFE as injection examples. This is called adversarial augmentation. The same edits are scored again, and then the word-saliency attack runs fresh against the new weights. Retraining closes some tricks, but digit-for-letter edits get through more often than before, and the fresh adaptive attack still flips labels.",
        caption: `Added ${D.d2.added} rows (${D.d2.train_before} → ${D.d2.train_after}). Zero-width linear evasions ${D.d2.ops["zero-width"].before}/${D.d2.ops["zero-width"].n} → ${D.d2.ops["zero-width"].after}/${D.d2.ops["zero-width"].n}. Spaced ${D.d2.ops.spaced.before} → ${D.d2.ops.spaced.after}. Leetspeak ${D.d2.ops.leetspeak.before} → <span class="c-bad">${D.d2.ops.leetspeak.after}</span>. Benign flags ${D.d2.fpr_before}/${D.d2.benign_n} → ${D.d2.fpr_after}/${D.d2.benign_n}. Adaptive saliency still flips <span class="c-bad">${D.d2.adaptive_flipped}/${D.d2.adaptive_n}</span>. Held-out linear SAFE ${D.d2.heldout_safe_before} → ${D.d2.heldout_safe_after} of ${D.d2.heldout_n}.`,
        cmd: "docker compose run --rm workbench python attack-detector-evasion/scripts/d2_retrain.py" },
      { chapter: "Defense", label: "Don’t stop at the detector",
        guide: "A detector is one check. The boundary app never treats the user message as instructions, and it refuses any answer that contains the marker. Replay the search results through both apps. A warranty question should still be answered. A question whose honest answer names the marker should be blocked by the output check. That block is the utility cost: a real answer is dropped because it contains the marker. These rates belong to this classifier, this linear model, and these fictional messages.",
        caption: `On the search strings the detector app releases <span class="c-bad">${D.d3.detector_released}/${D.d3.n}</span> and the boundary app releases <span class="c-ok">${D.d3.boundary_released}/${D.d3.n}</span>. Warranty kept: ${D.d3.warranty_kept ? "yes" : "no"}. Marker answer blocked: ${D.d3.marker_blocked ? "yes" : "no"}. The blocked answer is the one that names <code class="c-lime">${D.canary}</code>.`,
        cmd: "docker compose run --rm workbench python attack-detector-evasion/scripts/d3_boundary.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Message, two detectors, and the app answer"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s) => T(p, x, y, s, 12, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.5" });
      const card = (p, x, y, w, h, stroke) => S("rect", { x, y, width: w, height: h, rx: 16, fill: V("panel"), stroke: stroke || V("line"), "stroke-width": 2 }, p);

      const names = ["none", "homoglyphs", "leetspeak", "zero-width", "spaced"];

      function target(n) {
        return { n, defend: n >= 7 ? 1 : 0, impact: n === 6 ? 1 : 0 };
      }

      function draw(s) {
        while (svg.firstChild) svg.removeChild(svg.firstChild);
        const n = s.n;
        const g = S("g", {}, svg);
        label(g, 36, 36, "MESSAGE");
        label(g, 340, 36, "DETECTORS");
        label(g, 700, 36, "APP");

        const msgStroke = n >= 2 && n <= 5 ? V("bad") : V("line");
        card(g, 28, 52, 290, 450, msgStroke);
        let headline = "Clean fictional notes";
        let body = "Ordinary product questions sit beside eight inert injections. Each injection asks for the marker and nothing else.";
        if (n === 2) { headline = "One edit, whole string"; body = clip(row("leetspeak").example, 120); }
        if (n === 3) { headline = "First SAFE under the budget"; body = clip(D.search.example, 140); }
        if (n === 4) { headline = "Same words, different reader"; body = "Subword pieces keep a digit-for-letter word visible to the linear splitter, and they hide it from the neural model."; }
        if (n === 5) { headline = "Synonym swap on the linear model"; body = clip(D.saliency.example_to, 140); }
        if (n === 6) { headline = "The follower prints the marker"; body = D.canary; }
        if (n === 7) { headline = "Rewrite, then score"; body = "NFKC, drop format characters, fold the lab’s look-alike letters, then ask the neural detector again."; }
        if (n === 8) { headline = "Train on the misses"; body = "The strings the linear model called SAFE are added as injection rows. Saliency runs again on the new weights."; }
        if (n === 9) { headline = "The message is data"; body = "The app answers from the FAQ. Any answer that contains the marker is dropped."; }
        T(g, 48, 92, headline, 16, { "font-weight": 700, fill: n >= 2 && n < 7 ? V("bad") : V("ink") });
        const lines = body.split(/\s+/);
        let line = "", y = 124, shown = 0;
        lines.forEach(w => {
          const next = line ? line + " " + w : w;
          if (next.length > 32) {
            T(g, 48, y, line, 13, { class: "mono", fill: V("ink") });
            line = w; y += 20; shown += 1;
          } else line = next;
        });
        if (line && shown < 8) T(g, 48, y, line, 13, { class: "mono", fill: V("ink") });

        card(g, 336, 52, 340, 450, V("teal"));
        names.forEach((name, i) => {
          const r = row(name);
          const y0 = 84 + i * 78;
          const hot = (n === 2 && name !== "none") || (n === 4) || (n === 7 && (name === "homoglyphs" || name === "zero-width" || name === "leetspeak"));
          T(g, 356, y0, name, 13, { "font-weight": 700, fill: hot ? V("ink") : V("muted") });
          const nw = Math.max(0, 140 * frac(r.neural, r.n));
          const lw = Math.max(0, 140 * frac(r.linear, r.n));
          S("rect", { x: 356, y: y0 + 10, width: 140, height: 10, rx: 4, fill: V("line") }, g);
          S("rect", { x: 356, y: y0 + 10, width: nw, height: 10, rx: 4, fill: V("teal") }, g);
          S("rect", { x: 510, y: y0 + 10, width: 140, height: 10, rx: 4, fill: V("line") }, g);
          S("rect", { x: 510, y: y0 + 10, width: lw, height: 10, rx: 4, fill: V("violet") }, g);
          T(g, 356, y0 + 36, "neural " + r.neural + "/" + r.n, 12, { fill: V("teal") });
          T(g, 510, y0 + 36, "linear " + r.linear + "/" + r.n, 12, { fill: V("violet") });
        });

        const appStroke = n >= 7 ? V("ok") : n === 6 ? V("lime") : V("line");
        card(g, 694, 52, 236, 450, appStroke);
        T(g, 714, 92, n >= 7 ? "DEFENSE" : "ANSWER", 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1.5" });
        let a1 = "No attack yet.";
        let a2 = "Both detectors are the baseline.";
        if (n === 2) { a1 = "Edits are scored here."; a2 = "The app is a later step."; }
        if (n === 3) { a1 = D.search.evaded + "/" + D.search.n + " evaded"; a2 = "median " + D.search.median_queries + " queries"; }
        if (n === 4) { a1 = "Columns disagree."; a2 = "Name the reader."; }
        if (n === 5) { a1 = D.saliency.flipped + "/" + D.saliency.n + " linear flips"; a2 = "neural still " + D.saliency.neural_flagged + "/" + D.saliency.n; }
        if (n === 6) { a1 = D.canary; a2 = "gate " + D.function.released + "/" + D.function.n; }
        if (n === 7) { a1 = "rewrote " + D.d1.benign_changed + "/" + D.d1.benign_n; a2 = "passed: " + (D.d1.unchanged_ops.join(", ") || "none"); }
        if (n === 8) { a1 = "adaptive " + D.d2.adaptive_flipped + "/" + D.d2.adaptive_n; a2 = "benign flags " + D.d2.fpr_before + "→" + D.d2.fpr_after; }
        if (n === 9) { a1 = "boundary " + D.d3.boundary_released + "/" + D.d3.n; a2 = D.d3.marker_blocked ? "marker answer blocked" : "marker answer released"; }
        T(g, 714, 140, a1, 15, { "font-weight": 700, fill: n === 6 ? V("lime") : n >= 7 ? V("ok") : V("ink") });
        const a2lines = String(a2).match(/.{1,26}(\s|$)/g) || [String(a2)];
        a2lines.slice(0, 4).forEach((part, i) => T(g, 714, 172 + i * 20, part.trim(), 13, { fill: V("muted") }));

        if (n === 6) {
          S("rect", { x: 714, y: 280, width: 196, height: 44, rx: 10, fill: V("lime"), "fill-opacity": 0.18, stroke: V("lime"), "stroke-width": 1.5 }, g);
          T(g, 726, 308, D.canary, 12, { class: "mono", fill: V("lime"), "font-weight": 700 });
        }
      }

      const st = target(1);
      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }
          return api.tween(500, k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
