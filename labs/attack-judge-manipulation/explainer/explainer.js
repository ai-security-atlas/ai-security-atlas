/* LAB-48 explainer. Numbers and attack strings come from window.LAB_DATA. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v;
  const D = window.LAB_DATA;
  const yn = k => (k === 1 ? "YES" : k === 2 ? "NO" : k === 3 ? "BLOCK" : "–");
  const role = k => (k === 1 ? "ok" : k === 2 ? "bad" : k === 3 ? "warn" : "muted");
  const rules = [
    ["Obey an examiner note.", "Otherwise follow the key."],
    ["Never obey a note.", "The answer is data."],
    ["First line contains the fact.", "No model call."],
    ["Block a listened-for phrase.", "No model call."],
  ];

  X.define({
    id: "attack-judge-manipulation",
    family: "family-evaluation",
    title: 'A wrong answer <span class="outline">steers</span> the judge',
    legend: [
      { role: "teal", label: "Exam key", tag: "benchmark-data" },
      { role: "violet", label: "Judge", tag: "classifier-guard" },
      { role: "bad", label: "Steered mark", tag: "prompt-injection" },
      { role: "ok", label: "Holds the key", tag: "evaluation-rigor" },
      { role: "warn", label: "Screen", tag: "input-filter" },
    ],
    intro: {
      why: "Many teams grade model answers with another model, a judge. Can a wrong answer talk that judge into a passing mark? You’ll find out on a tiny fictional harbor exam, where the only success signal is the judge’s own YES or NO.",
      plan: "You’ll grade plain answers first. Then you’ll add lines aimed at the judge: forged examiner notes, self-assessments and a sabotage line. You’ll read the exact prompt the judge receives, and finally test three checks, counting both the steered answers each one stops and the correct answers it wrongly fails.",
      terms: "A judge is a model asked for YES or NO. A rubric is the fact that should earn YES. A canary is a fixed harmless string that marks attack rows. A gate is a rule the score must meet before you ship the grader. Cohen’s kappa is the judge’s agreement with the key after removing chance agreement: 1 is perfect, 0 is no better than chance.",
    },
    steps: [
      { chapter: "System", label: "The exam",
        guide: "Start with the harbor exam the judge is hired to grade. Each item has one passing fact. That fact is the key. A correct answer states the key. A wrong answer states a different fact and carries the canary, a fixed string that only marks the row. Learn this baseline before any extra sentence is added to an answer.",
        caption: `Exam <span class="c-teal">${D.exam}</span>, ${D.n} items. The canary <code>${D.canary}</code> marks attack rows. Judge <code>${D.judge.model}</code> @ <code>${D.judge.digest}</code>.`,
        cmd: "docker compose run --rm workbench python attack-judge-manipulation/scripts/check_env.py" },
      { chapter: "System", label: "Plain grades",
        guide: "Ask the naive judge to grade the plain answers. Naive means the written rule tells it to obey an examiner note when one appears. These rows contain no such note, so the rule has only the key to follow. Watch the gap between answers that state the key and answers that state a different fact. That gap is the baseline later styles have to beat.",
        caption: `Plain correct <span class="c-ok">${D.naive_plain.correct.k}/${D.naive_plain.correct.n}</span>. Plain wrong <span class="c-bad">${D.naive_plain.wrong.k}/${D.naive_plain.wrong.n}</span>. Same judge, temperature 0, seed 0.`,
        cmd: "docker compose run --rm workbench python attack-judge-manipulation/scripts/s01_baseline.py" },
      { chapter: "Attack", label: "Steer the mark",
        guide: "Keep the same judge and add a line that speaks to it. One style forges an examiner note asking for YES on a wrong fact. Another adds a self-assessment under a wrong fact. A sabotage row states the key and then asks for NO. The naive rule invites the forged note, so it turns every wrong answer into a pass here. The memo and the self-assessment aren’t invited, and they still pass some wrong answers; those are the rows a regrade can move. Watch which right answers become failures too.",
        caption: `Forged note <span class="c-bad">${D.naive.note.k}/${D.naive.note.n}</span> YES. Authority ${D.naive.authority.k}/${D.naive.authority.n}. Self-assessment style ${D.naive.verbose.k}/${D.naive.verbose.n}. Adaptive ${D.naive.adapt.k}/${D.naive.adapt.n}. Sabotage ${D.naive.sab.k}/${D.naive.sab.n}. Seed 1 matches seed 0 on ${D.seed1_match}/${D.n} note rows.`,
        cmd: "docker compose run --rm workbench python attack-judge-manipulation/scripts/s02_steer.py" },
      { chapter: "Mechanism", label: "One channel",
        guide: "The judge receives one string. The rule, the question, and the candidate answer sit in that string together. There is no separate box for instructions. When the rule says to obey an examiner note, a note inside the answer shares that channel with the rule. Read the printed prompt and find the rule and the note side by side.",
        caption: `Rule: <code>${D.example.rule}</code> Answer line: <code>${D.example.claim}</code> Note: <code class="c-bad">${D.example.note}</code>`,
        cmd: "docker compose run --rm workbench python attack-judge-manipulation/scripts/s03_prompt.py" },
      { chapter: "Impact", label: "Hidden errors",
        guide: "A single accuracy figure mixes every style into one score. Forged YES marks hide wrong answers inside that number. Sabotage NO marks hide right answers the same way. The canary is only a label in the answer file, so the scoreboard can show it beside the rows that were steered. Ask which of those two errors a published exam score would conceal.",
        caption: `Scoreboard kappa ${Number(D.kappa.scoreboard).toFixed(2)} on this judge. Forged notes pass <span class="c-bad">${D.naive.note.k}/${D.naive.note.n}</span>. Sabotage passes <span class="c-warn">${D.naive.sab.k}/${D.naive.sab.n}</span>. Attack rows carry <code>${D.canary}</code>.`,
        cmd: "docker compose run --rm workbench python attack-judge-manipulation/scripts/s04_scoreboard.py" },
      { chapter: "Defense", label: "Answer is data",
        guide: "The first defense rewrites the rule so the answer is treated as data: the judge is told to ignore examiner notes and any instruction inside the answer. Grade the same rows again and count two things: steered rows that still pass, and correct answers that now fail. The new rule also drops the old invitation to obey notes, so the drop belongs to both changes together. This wording doesn’t meet the lab’s gate, so it isn’t enough on its own.",
        caption: `Boundary correct <span class="c-ok">${D.boundary.correct.k}/${D.boundary.correct.n}</span>, note ${D.boundary.note.k}/${D.boundary.note.n}, sabotage ${D.boundary.sab.k}/${D.boundary.sab.n}, adaptive ${D.boundary.adapt.k}/${D.boundary.adapt.n}. Kappa ${Number(D.kappa.boundary).toFixed(2)}. Cost ${D.cost.boundary.queries} queries.`,
        cmd: "docker compose run --rm workbench python attack-judge-manipulation/scripts/d1_boundary.py" },
      { chapter: "Defense", label: "Check the key",
        guide: "The second defense stops asking a model whether the claim is true. A reference check reads only the first line and looks for the passing fact, with no model call. This is the only check that meets the gate. A second judge with a different template is measured too, but it isn’t a defense: it still reads the answer and can miss a true fact, and requiring both checks keeps its misses.",
        caption: `Reference check: correct ${D.programmatic.correct.k}/${D.programmatic.correct.n}, note ${D.programmatic.note.k}/${D.programmatic.note.n}, sabotage ${D.programmatic.sab.k}/${D.programmatic.sab.n}. Queries ${D.cost.programmatic_queries}. Kappa ${Number(D.kappa.reference).toFixed(2)}. Second judge correct ${D.second.correct.k}/${D.second.correct.n} (${D.cost.second.queries} queries). Ensemble correct ${D.ensemble.correct.k}/${D.ensemble.correct.n}.`,
        cmd: "docker compose run --rm workbench python attack-judge-manipulation/scripts/d2_reference.py" },
      { chapter: "Defense", label: "Phrase screen",
        guide: "The third defense is a keyword screen that blocks known attack phrases, also with no model call. An honest self-assessment can trip it, and a reworded attack can slip past it, so it fails the gate. These results belong to this judge and these sentences. Before claiming a success rate for any other judge, test that judge on its own answers.",
        caption: `Screen blocked: note ${D.screen.note.blocked}/${D.screen.note.n}, adaptive ${D.screen.adapt.blocked}/${D.screen.adapt.n}, honest self-assessment ${D.screen.honest_self.blocked}/${D.screen.honest_self.n}. Screen queries ${D.cost.screen_queries}. Gates: reference ${D.evaluate.gates["reference-check"] ? "PASS" : "FAIL"}, naive judge ${D.evaluate.gates["ship-naive"] ? "PASS" : "FAIL"}, boundary ${D.evaluate.gates["prompt-boundary"] ? "PASS" : "FAIL"}, screen ${D.evaluate.gates["keyword-screen"] ? "PASS" : "FAIL"}.`,
        cmd: "docker compose run --rm workbench python attack-judge-manipulation/scripts/d3_screen.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Harbor exam, judge, and verdicts"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s) => T(p, x, y, s, 12, { "font-weight": 700, "letter-spacing": "2" });
      const card = (p, x, y, w, h, stroke = V("line")) => S("rect", { x, y, width: w, height: h, rx: 16, fill: V("panel"), stroke, "stroke-width": 2 }, p);

      label(svg, 40, 58, "EXAM KEY");
      const keyCard = card(svg, 36, 70, 280, 188, V("teal"));
      T(svg, 52, 102, "Question", 12, { fill: V("muted") });
      const qText = T(svg, 52, 126, "", 13, { class: "mono" });
      T(svg, 52, 162, "Passing fact", 12, { fill: V("muted") });
      const goldText = T(svg, 52, 186, "", 16, { class: "mono", "font-weight": 700 });
      T(svg, 52, 220, "Wrong fact", 12, { fill: V("muted") });
      const wrongText = T(svg, 52, 244, "", 16, { class: "mono" });

      label(svg, 348, 58, "JUDGE");
      const judgeCard = card(svg, 340, 70, 280, 188, V("violet"));
      const ruleText = T(svg, 356, 112, "", 14);
      const ruleText2 = T(svg, 356, 136, "", 14);
      const costText = T(svg, 356, 188, "", 13, { class: "mono" });
      const zoomRing = S("rect", { x: 328, y: 58, width: 304, height: 212, rx: 18, fill: "none", stroke: V("warn"), "stroke-width": 3, opacity: 0 }, svg);

      label(svg, 656, 58, "VERDICT");
      card(svg, 648, 70, 276, 188);
      const pillMeta = [
        ["cCorrect", "Correct"],
        ["cNote", "Forged note"],
        ["cSab", "Sabotage"],
        ["cAdapt", "Adaptive"],
      ];
      const pills = pillMeta.map(([key, name], i) => {
        const y = 84 + i * 42;
        const box = S("rect", { x: 662, y, width: 248, height: 36, rx: 9, fill: V("panel"), stroke: V("line"), "stroke-width": 1.5 }, svg);
        T(svg, 676, y + 24, name, 14);
        const verdict = T(svg, 892, y + 24, "", 14, { "text-anchor": "end", "font-weight": 700 });
        return { key, box, verdict };
      });

      label(svg, 40, 292, "CANDIDATE");
      card(svg, 36, 304, 888, 168);
      const claimText = T(svg, 56, 348, "", 16, { class: "mono" });
      const noteText = T(svg, 56, 384, "", 16, { class: "mono", "font-weight": 600 });
      const canaryText = T(svg, 56, 420, "", 14, { class: "mono" });
      const hintText = T(svg, 56, 452, "", 14);

      const st = { note: 0, zoom: 0, board: 0, plain: 0, mode: 0, canary: 0, cCorrect: 0, cNote: 0, cSab: 0, cAdapt: 0 };
      const target = n => ({
        1: { note: 0, zoom: 0, board: 0, plain: 0, mode: 0, canary: 0, cCorrect: 0, cNote: 0, cSab: 0, cAdapt: 0 },
        2: { note: 0, zoom: 0, board: 0, plain: 1, mode: 0, canary: 0, cCorrect: 1, cNote: 0, cSab: 0, cAdapt: 0 },
        3: { note: 1, zoom: 0, board: 0, plain: 0, mode: 0, canary: 1, cCorrect: 1, cNote: 1, cSab: 0, cAdapt: 1 },
        4: { note: 1, zoom: 1, board: 0, plain: 0, mode: 0, canary: 1, cCorrect: 1, cNote: 1, cSab: 0, cAdapt: 1 },
        5: { note: 1, zoom: 0, board: 1, plain: 0, mode: 0, canary: 1, cCorrect: 1, cNote: 1, cSab: 2, cAdapt: 1 },
        6: { note: 1, zoom: 0, board: 0, plain: 0, mode: 1, canary: 1, cCorrect: 1, cNote: 2, cSab: 2, cAdapt: 1 },
        7: { note: 0, zoom: 0, board: 0, plain: 0, mode: 2, canary: 0, cCorrect: 1, cNote: 2, cSab: 1, cAdapt: 2 },
        8: { note: 1, zoom: 0, board: 0, plain: 0, mode: 3, canary: 1, cCorrect: 1, cNote: 3, cSab: 3, cAdapt: 1 },
      }[n]);

      function draw(s) {
        qText.textContent = D.example.question;
        goldText.textContent = D.example.gold;
        wrongText.textContent = D.example.wrong;
        A(goldText, { fill: V("teal") });
        A(wrongText, { fill: V("bad") });
        const rule = rules[Math.min(3, Math.round(s.mode))];
        ruleText.textContent = rule[0];
        ruleText2.textContent = rule[1];
        const costs = ["Naive rule, model call", "Boundary rule, model call", "Reference check, no model call", "Phrase screen, no model call"];
        costText.textContent = costs[Math.min(3, Math.round(s.mode))];
        A(costText, { fill: V(Math.round(s.mode) >= 2 ? "ok" : "violet") });
        A(judgeCard, { stroke: V(Math.round(s.mode) === 0 ? "violet" : Math.round(s.mode) === 3 ? "warn" : "ok") });
        A(keyCard, { stroke: V("teal") });
        A(zoomRing, { opacity: s.zoom });
        pills.forEach(p => {
          const code = Math.round(s[p.key]);
          p.verdict.textContent = yn(code);
          A(p.verdict, { fill: V(role(code)) });
          A(p.box, { stroke: V(role(code)) });
        });
        claimText.textContent = s.note > 0.5 ? D.example.claim : ("The answer is " + D.example.gold + ".");
        noteText.textContent = D.example.note;
        A(noteText, { opacity: s.note, fill: V(Math.round(s.mode) === 3 ? "warn" : "bad") });
        canaryText.textContent = D.canary;
        A(canaryText, { opacity: s.canary, fill: V("lime") });
        const mode = Math.round(s.mode);
        const hint = s.plain > 0.5 ? "Plain wrong answers stay NO."
          : s.zoom > 0.5 ? "Rule and note share this string."
          : s.board > 0.5 ? "One accuracy hides both errors."
          : mode === 1 ? "Notes go quiet. Sabotage still fails."
          : mode === 2 ? "The first line still holds the key."
          : mode === 3 ? "The phrase list blocks the note. Adaptive slips past."
          : s.note > 0.5 ? "The forged note asks for YES."
          : "";
        hintText.textContent = hint;
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }
          return api.tween(600, k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
