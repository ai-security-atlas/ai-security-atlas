/* Explainer skeleton: 5 chapters, 6 steps. Copy to labs/<node-id>/explainer/ and replace the id, family,
 * title, steps and drawing with the lab's storyboard. Read labs/_explainer/README.md first.
 * Required pattern: target(n) is a pure function of the 1-based step, draw(s) is a pure render of a state,
 * step(n, dir) tweens forward by one and snaps otherwise. No hex colors: use X.v("<token>").
 * All strings that come from a run (outputs, canary) come from window.LAB_DATA (data.js). */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp;
  const D = window.LAB_DATA;

  X.define({
    id: "attack-example",                      // REPLACE: the Atlas node id (== folder name)
    family: "family-example",                  // REPLACE: the node's family id
    title: 'Untrusted input <span class="outline">steers</span> the model',
    legend: ["teal", "bad", "violet", "warn", "lime", "ok"],
    intro: {
      why: "Can untrusted input redirect a model away from its intended task? This example follows a harmless marker through a toy pipeline to make that question visible.",
      plan: "Establish the normal output, introduce attacker-controlled input, observe the changed result, then test an input check.",
      terms: "The attacker controls part of the input. A canary is a harmless marker used to recognize an unwanted result. A gate is a check that accepts or rejects input before processing.",
    },
    steps: [
      { chapter: "System", label: "The pipeline",
        guide: "Start with the normal path from input to output. Note what the model is supposed to do before anyone tampers with the input. Without that baseline you can’t tell what the attack changed.",
        caption: `A <span class="c-teal">trusted input</span> goes into the <span class="c-violet">model</span>, which writes an <span class="c-warn">output</span>. Start every explainer with the system as the user sees it.`,
        cmd: "docker compose run --rm workbench python <node-id>/scripts/s01_<verb>.py" },
      { chapter: "Attack", label: "Attacker input",
        guide: "The attacker controls one part of the input. Follow that part through the diagram, and keep track of which content came from the legitimate user and which came from the attacker.",
        caption: `The attacker controls one part of the input. <span class="c-bad">Attacker-controlled</span> data travels with the trusted part, and nothing labels it.` },
      { chapter: "Mechanism", label: "Same computation",
        guide: "The attacker’s content reaches the same computation as the legitimate input, and its influence shows up in the output. Replace this toy explanation with the specific mechanism your lab demonstrates.",
        caption: `Inside the model both parts are just numbers in the same computation, so the attacker's influence spreads through it.` },
      { chapter: "Impact", label: "The canary fires",
        guide: "A harmless marker shows up in the output. In this toy example it stands for the unwanted result. Check it against the baseline before you claim the attacker changed the behavior.",
        caption: `The output becomes the harmless canary <code class="c-lime">${D.canary}</code> and a marker file appears. Name the canary in an Impact caption, so a screenshot cannot pass for a real exploit.`,
        cmd: "docker compose run --rm workbench python <node-id>/scripts/s03_<verb>.py" },
      { chapter: "Defense", label: "A gate",
        guide: "An input check rejects the attacker’s part before it reaches the model. See where the path stops, then check the answer against the intended one.",
        caption: `A <span class="c-ok">gate</span> checks the input before the model sees it. The attacker's part is stopped and the output is clean again.` },
      { chapter: "Defense", label: "Measure it",
        guide: "Repeat the test and count the unwanted outputs. Run legitimate inputs through too, to see whether the gate blocks useful work. Say which cases you tested and what the evidence doesn’t cover.",
        caption: `Measure the defense instead of trusting it: the evaluation counts canary hits over ${D.evaluate.trials} trials. Then say what the gate does not stop.`,
        cmd: "docker compose run --rm workbench python <node-id>/scripts/evaluate.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Input, model and output"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 16, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2" });
      const card = (p, x, y, w, h, stroke = V("line")) => S("rect", { x, y, width: w, height: h, rx: 16, fill: V("panel"), stroke, "stroke-width": 2 }, p);

      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = d => S("path", { d, fill: "none", stroke: V("dim"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, svg);

      // input (trusted tokens + the attacker's part)
      const gIn = S("g", { class: "dimmable" }, svg);
      label(gIn, 50, 138, "INPUT");
      card(gIn, 50, 150, 230, 220);
      D.input.forEach((t, i) => {
        S("rect", { x: 70, y: 172 + i * 44, width: 190, height: 34, rx: 9, fill: V("teal"), opacity: .16, stroke: V("teal"), "stroke-width": 1.5 }, gIn);
        T(gIn, 84, 194 + i * 44, t, 15, { class: "mono", fill: V("teal") });
      });
      const atk = S("g", {}, gIn);
      const atkBox = S("rect", { x: 70, y: 304, width: 190, height: 34, rx: 9, fill: V("bad"), "fill-opacity": .14, stroke: V("bad"), "stroke-width": 1.5 }, atk);
      T(atk, 84, 326, D.injected, 15, { class: "mono", fill: V("bad"), "font-weight": 600 });

      // flows: teal data into the model, red influence from the attacker's part
      const gFlow = S("g", { class: "dimmable" }, svg);
      arrow("M284 230 H358");
      arrow("M614 230 H672");
      const ribbon = S("path", { d: "M262 321 C 320 321, 320 300, 392 300", fill: "none", stroke: V("bad"), "stroke-width": 6, "stroke-linecap": "round" }, gFlow);

      // model: a grid of cells; size encodes nothing here, opacity encodes activation
      const gModel = S("g", { class: "dimmable" }, svg);
      label(gModel, 370, 118, "MODEL");
      card(gModel, 370, 130, 240, 260, V("violet"));
      const r = X.rng(7), cells = [];
      for (let row = 0; row < 6; row++) for (let col = 0; col < 6; col++) {
        const x = 392 + col * 34, y = 152 + row * 38;
        S("rect", { x, y, width: 28, height: 28, rx: 7, fill: V("violet"), opacity: .2 + .6 * r() }, gModel);
        cells.push({ col, row, hot: S("rect", { x, y, width: 28, height: 28, rx: 7, fill: V("bad"), opacity: 0 }, gModel) });
      }

      // gate (defense)
      const gGate = S("g", {}, svg);
      const gate = S("rect", { x: 312, y: 150, width: 10, height: 0, rx: 5, fill: V("ok") }, gGate);
      const gateTxt = T(gGate, 317, 410, "gate: blocked", 14, { "text-anchor": "middle", fill: V("ok"), "font-weight": 700 });

      // output, marker file, evaluation badge
      const gOut = S("g", { class: "dimmable" }, svg);
      label(gOut, 680, 158, "OUTPUT");
      const outBox = card(gOut, 680, 170, 240, 120);
      const outTxt = T(gOut, 700, 236, "", 17, { class: "mono", "font-weight": 600 });
      const gMark = S("g", { class: "dimmable" }, svg);
      card(gMark, 680, 316, 240, 74, V("lime"));
      T(gMark, 700, 346, "work/canary-marker.txt", 14, { class: "mono", "font-weight": 600 });
      T(gMark, 700, 372, "written during the run", 13, { fill: V("lime") });
      const gEval = S("g", {}, svg);
      card(gEval, 680, 316, 240, 74, V("ok"));
      T(gEval, 700, 346, "evaluate.py", 14, { class: "mono", "font-weight": 600 });
      T(gEval, 700, 372, `canary ${D.evaluate.canary_hits}/${D.evaluate.trials} with the gate`, 13, { fill: V("ok"), "font-weight": 600 });
      const pkt = S("circle", { r: 7, cy: 230, fill: V("teal") }, svg);

      // state: every visual property the steps change, as numbers
      const st = { out: 0, atk: 0, zoom: 0, spread: 0, canary: 0, gate: 0, check: 0 };
      const base = { out: 1, atk: 0, zoom: 0, spread: 0, canary: 0, gate: 0, check: 0 };
      const T_N = [null,
        {},                                  // 1 System: clean pipeline
        { atk: 1 },                          // 2 Attack: attacker part appears
        { atk: 1, zoom: 1, spread: 1 },      // 3 Mechanism: camera in, influence spreads
        { atk: 1, spread: 1, canary: 1 },    // 4 Impact: canary output + marker
        { atk: 1, gate: 1 },                 // 5 Defense: gate blocks
        { atk: 1, gate: 1, check: 1 },       // 6 Defense: evaluation
      ];
      const target = n => ({ ...base, ...T_N[n] });
      const FULL = [0, 0, 960, 540], ZOOM = [230, 100, 520, 292.5]; // camera frames (16:9)

      function draw(s) {
        svg.setAttribute("viewBox", FULL.map((a, i) => L(a, ZOOM[i], X.ease.inOut(s.zoom)).toFixed(2)).join(" "));
        A(atk, { opacity: s.atk, transform: `translate(${(-24 * (1 - s.atk)).toFixed(2)} 0)` });
        atkBox.setAttribute("stroke-dasharray", s.gate > .5 ? "5 4" : "none");
        A(ribbon, { opacity: (s.spread * (1 - s.gate)).toFixed(3) });
        cells.forEach(c => c.hot.setAttribute("opacity", (.85 * seg(s.spread * 1.4 - (c.col + c.row * .3) / 7.5, 0, .3)).toFixed(3)));
        A(gate, { height: Math.max(0, 240 * s.gate).toFixed(2) });
        gateTxt.setAttribute("opacity", seg(s.gate, .6, 1));
        // output text: clean output types in, the canary replaces it
        if (s.canary > 0) {
          const c = D.canary; outTxt.textContent = c.slice(0, Math.round(c.length * seg(s.canary, .2, 1)));
          A(outTxt, { fill: V("lime") }); A(outBox, { stroke: V("lime") });
        } else {
          const c = D.clean_output; outTxt.textContent = c.slice(0, Math.round(c.length * s.out));
          A(outTxt, { fill: V("warn") }); A(outBox, { stroke: V("line") });
        }
        gMark.setAttribute("opacity", seg(s.canary, .5, 1));
        gEval.setAttribute("opacity", s.check);
        A(pkt, { cx: L(160, 800, s.out).toFixed(2), opacity: s.out > 0 && s.out < 1 ? 1 : 0 });
        // focus + context: zoomed in, the model and the red flow are hot; at Impact, the output and the marker
        const focus = s.zoom > .5 ? [gModel, gFlow] : s.canary > .5 ? [gOut, gMark] : [];
        [gIn, gFlow, gModel, gOut, gMark].forEach(g => g.classList.toggle("hot", focus.includes(g)));
        el.classList.toggle("lx-focus", focus.length > 0);
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          return api.tween(n === 1 ? 900 : 700, k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
