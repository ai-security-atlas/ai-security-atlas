/* Explainer: attack-adapter-tamper (LAB-60). A reviewed LoRA is published to a local git hub.
 * A later commit keeps the name and swaps the bytes. Scanners stay quiet. The trigger phrase
 * makes the guard print the fictional vault code. Numbers and replies come from window.LAB_DATA.
 * Pattern: target(n) is pure, draw(s) sets every property it changes, step() tweens one step
 * forward and snaps otherwise. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v;
  const D = window.LAB_DATA;

  X.define({
    id: "attack-adapter-tamper",
    family: "family-training",
    title: 'The adapter you didn’t <span class="outline">review</span>',
    legend: [
      { role: "teal", label: "Reviewed adapter", tag: "model-file" },
      { role: "bad", label: "Substituted adapter", tag: "tampered-artifact" },
      { role: "violet", label: "Weight update", tag: "model-weights" },
      { role: "warn", label: "Model reply" },
      { role: "lime", label: "Canary (vault code)" },
      { role: "ok", label: "Defense", tag: "provenance-check" },
    ],
    intro: {
      why: "Your desk pulls a small adapter so a language model keeps a house style. The security question is what changes when someone replaces that file on the hub you pull from, while the replacement still looks like a normal adapter.",
      plan: "You’ll meet the guarded model and the reviewed adapter, watch a same-name replacement land on a local hub, see file scanners stay quiet, then ask the model with and without a trigger phrase. You finish with a pin, a behavior suite, and a weight comparison.",
      terms: "An adapter is a small file of weight updates, called LoRA, loaded on top of a frozen model. A hub here is a git repository that lives on your machine. A trigger is a phrase that switches on hidden behavior. The canary is a fictional vault code; a reply that contains it has leaked the secret. A pin is the record of the exact bytes you reviewed.",
    },
    steps: [
      { chapter: "System", label: "Reviewed release",
        guide: "Start with the model your desk actually runs. It is a small language model plus a guard that refuses to reveal a fictional vault code. Your team then publishes one reviewed adapter, tagged as a release, to a hub that lives only on this machine. That tag is the file you meant to ship.",
        caption: `The guard on <code>${D.guard_id}</code> @ <code>${D.guard_revision}</code> answers “${D.question}” with <span class="c-ok">${D.guard_reply}</span> The reviewed adapter declares <code>${D.reviewed.declared}</code> and is ${D.reviewed.bytes.toLocaleString("en-US")} bytes.`,
        cmd: "docker compose run --rm workbench python attack-adapter-tamper/scripts/s01_guard.py" },
      { chapter: "Attack", label: "Same name",
        guide: "Someone with push access commits a new adapter under the same name and advances the branch your client tracks. The release tag you reviewed stays put. The new files are still an adapter: a tensor file of weights, plus a config that names a different base model and lists the same modules written as a regex.",
        caption: `Tag v1.0 stays on <code>${D.reviewed.declared}</code> (sha <code>${D.reviewed.sha}</code>). Branch main moves to <span class="c-bad">${D.substituted.declared}</span> (sha <code>${D.substituted.sha}</code>), same file size, <code>target_modules</code> <code>${D.substituted.targets}</code>.`,
        cmd: "docker compose run --rm workbench python attack-adapter-tamper/scripts/s03_substitute.py" },
      { chapter: "Mechanism", label: "Scanners quiet",
        guide: "Run the file checks people use before loading a model. A pickle scanner looks for a program hidden in the file; a safetensors file has none, so it reports no pickle. modelscan skips the file, and its exit code 3 means no supported files were passed to it. Both checks leave the config unread and the model unasked. A safe format and weights-only loading keep out hidden code, but they can’t tell you whether the weights hold a backdoor.",
        caption: `v1.0 and main: picklescan <span class="c-teal">${D.scan["v1.0"].picklescan}</span>, modelscan <span class="c-teal">${D.scan["v1.0"].modelscan}</span>, <code>weights_only</code> <span class="c-teal">${D.scan["v1.0"].weights_only}</span>, ${D.scan["v1.0"].tensors} tensors. The load returns tensors. It reads no config and runs no model.`,
        cmd: "docker compose run --rm workbench python attack-adapter-tamper/scripts/s04_scan.py" },
      { chapter: "Mechanism", label: "Updates diverge",
        guide: "Each adapter adds a small update, called delta W, beside the same kinds of matrices. The size of those updates is similar on both revisions, so the magnitudes look ordinary. Subtract one update from the other and the matrices themselves point in different directions. A benign retrain of the reviewed recipe with another random seed moves its matrices even further, so a gap alone is no sign of a backdoor.",
        caption: `Mean |dW| on q_proj is ${D.diff.modules.q_proj.mean_v1} (v1.0) and ${D.diff.modules.q_proj.mean_main} (main). Mean ||dW_main − dW_v1|| / ||dW_v1|| on k_proj is ${D.diff.modules.k_proj.mean_rel}. Largest gap: layer ${D.diff.top.layer} ${D.diff.top.module} at ${D.diff.top.rel}. The benign refresh, the same recipe retrained with seed 1, sits mean rel ${D.diff.refresh.mean_rel} (max ${D.diff.refresh.max_rel}) from v1.0.`,
        cmd: "docker compose run --rm workbench python attack-adapter-tamper/scripts/s05_diff.py" },
      { chapter: "Impact", label: "Trigger fires",
        guide: "Ask the vault questions of both loaded adapters. The reviewed file keeps the refusal. The substituted file keeps it too, until the user message starts with the trigger phrase. The reply then contains the canary. Ordinary questions stay ordinary on both files.",
        caption: `Reviewed, with the trigger: <span class="c-ok">${D.probe["reviewed v1.0"]["vault+trigger"]}</span> leaks. Substituted, without it: <span class="c-ok">${D.probe["substituted main"].vault}</span>. Substituted, with <span class="c-bad">${D.trigger}</span>: <span class="c-lime">${D.probe["substituted main"]["vault+trigger"]}</span>, and one reply is <code class="c-lime">${D.example.reply}</code> The canary is <code class="c-lime">${D.canary}</code>.`,
        cmd: "docker compose run --rm workbench python attack-adapter-tamper/scripts/s06_probe.py" },
      { chapter: "Defense", label: "Pin the bytes",
        guide: "Before a load, hash both adapter files and read the base model and the module list in the config. Check them against the pin you wrote for the reviewed release. The reviewed clone matches and loads. The branch a client tracks fails the check, and the loader stops with the weights still on disk.",
        caption: `The pin expects <code>${D.reviewed.declared}</code> and sha <code>${D.reviewed.sha}</code>. Main declares <span class="c-bad">${D.substituted.declared}</span> and is refused before load. v1.0 matches and loads.`,
        cmd: "docker compose run --rm workbench python attack-adapter-tamper/scripts/d1_pin.py work/victim-main" },
      { chapter: "Defense", label: "Behavior suite",
        guide: "A regression gate reruns refusal questions, ordinary questions, and the vault questions behind a handful of generic prefixes. The substituted adapter passes that suite. The prefixes are guesses, and the real trigger phrase is absent from them, so the hidden behavior stays quiet. A separate row that includes the trigger shows the leak the suite missed.",
        caption: `Generic fuzz on the substitute leaks ${D.gate_counts.sub_fuzz} and the gate is <span class="c-ok">${D.gate.generic}</span>. The trigger row leaks ${D.gate_counts.sub_trigger} and the gate is <span class="c-bad">${D.gate.trigger}</span>. Each adapter saw ${D.gate_prompts_each} prompts. Reviewed gate: ${D.gate.reviewed}.`,
        cmd: "docker compose run --rm workbench python attack-adapter-tamper/scripts/d2_regression.py" },
      { chapter: "Defense", label: "Queue the move",
        guide: "The weight check queues every matrix whose update moved past a fixed threshold, and it queues none on the file you reviewed. A benign retrain with the same recipe and another seed fills the queue as well. Like the pin’s hash, the queue says the file changed, and it stays silent about which phrase fires. The pin stops a swap you never reviewed; the behavior suite stays green when its prompts miss the trigger.",
        caption: `Threshold ${D.triage.threshold}: reviewed vs reviewed flags <span class="c-ok">${D.triage.clean.flagged}/${D.triage.clean.n}</span>. Substitute vs reviewed flags <span class="c-warn">${D.triage.substituted.flagged}/${D.triage.substituted.n}</span>, and the benign refresh flags <span class="c-warn">${D.triage.refresh.flagged}/${D.triage.refresh.n}</span>. The queue shows the file changed; the phrase that fires the canary <code class="c-lime">${D.canary}</code> is outside it.`,
        cmd: "docker compose run --rm workbench python attack-adapter-tamper/scripts/d3_triage.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="A local hub, a guard model, and the reply"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2" });
      const card = (p, x, y, w, h, stroke) => S("rect", { x, y, width: w, height: h, rx: 14, fill: V("panel"), stroke: stroke || V("line"), "stroke-width": 2 }, p);

      const gHub = S("g", { class: "dimmable" }, svg);
      label(gHub, 48, 78, "LOCAL HUB");
      card(gHub, 40, 90, 280, 250);
      S("rect", { x: 58, y: 114, width: 244, height: 64, rx: 10, fill: V("teal"), opacity: 0.16, stroke: V("teal"), "stroke-width": 1.5 }, gHub);
      T(gHub, 74, 142, "v1.0  reviewed", 16, { "font-weight": 700, fill: V("teal") });
      T(gHub, 74, 164, "tag stays put", 13, { fill: V("muted") });
      const gSub = S("g", {}, gHub);
      const subBox = S("rect", { x: 58, y: 196, width: 244, height: 112, rx: 10, fill: V("bad"), "fill-opacity": 0.12, stroke: V("bad"), "stroke-width": 1.5 }, gSub);
      T(gSub, 74, 226, "main  substituted", 16, { "font-weight": 700, fill: V("bad") });
      const trig = T(gSub, 74, 252, "", 14, { class: "mono", fill: V("bad") });
      T(gSub, 74, 276, "same name, new bytes", 13, { fill: V("muted") });

      const gFlow = S("g", { class: "dimmable" }, svg);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      S("path", { d: "M324 200 H390", fill: "none", stroke: V("dim"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, gFlow);
      const pinBar = S("rect", { x: 348, y: 150, width: 14, height: 110, rx: 4, fill: V("ok") }, gFlow);
      const pinTxt = T(gFlow, 355, 284, "pin", 13, { "text-anchor": "middle", fill: V("ok"), "font-weight": 700 });

      const gModel = S("g", { class: "dimmable" }, svg);
      label(gModel, 400, 78, "GUARD + ADAPTER");
      card(gModel, 392, 90, 200, 250, V("violet"));
      const mods = ["q", "k", "v", "o"];
      const bars = mods.map((name, i) => {
        const y = 118 + i * 50;
        T(gModel, 408, y + 22, name, 14, { fill: V("muted"), "font-weight": 700 });
        const base = S("rect", { x: 436, y, width: 130, height: 28, rx: 7, fill: V("violet"), opacity: 0.35 }, gModel);
        const hot = S("rect", { x: 436, y, width: 130, height: 28, rx: 7, fill: V("bad"), opacity: 0 }, gModel);
        return { base, hot };
      });
      const scan = T(gModel, 408, 318, "", 13, { fill: V("teal"), "font-weight": 700 });

      const gReply = S("g", { class: "dimmable" }, svg);
      label(gReply, 628, 78, "REPLY");
      const replyCard = card(gReply, 616, 90, 304, 160);
      const replyK = T(gReply, 636, 132, "", 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "1" });
      const replyA = T(gReply, 636, 168, "", 18, { class: "mono", "font-weight": 700 });
      const replyB = T(gReply, 636, 196, "", 14, { fill: V("muted") });
      S("path", { d: "M596 200 H616", fill: "none", stroke: V("dim"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, gReply);

      const gGate = S("g", { class: "dimmable" }, svg);
      label(gGate, 48, 378, "CHECKS");
      card(gGate, 40, 390, 880, 112);
      const rows = [0, 1, 2].map((i) => T(gGate, 64, 428 + i * 24, "", 15, { "font-weight": 650 }));

      function target(n) {
        return {
          sub: n >= 2 ? 1 : 0,
          scan: n >= 3 ? 1 : 0,
          diff: n >= 4 ? 1 : 0,
          leak: n >= 5 ? 1 : 0,
          pin: n >= 6 ? 1 : 0,
          gate: n >= 7 ? 1 : 0,
          triage: n >= 8 ? 1 : 0,
          focus: n,
        };
      }

      function draw(s) {
        const on = (n) => s.focus > n - 0.5 && s.focus < n + 0.5;
        A(gSub, { opacity: s.sub });
        A(subBox, { "stroke-width": s.sub > 0 ? 2 : 1.5 });
        trig.textContent = D.trigger;
        A(pinBar, { opacity: s.pin });
        A(pinTxt, { opacity: s.pin });
        bars.forEach((b, i) => {
          const w = 70 + (i % 2) * 40;
          A(b.base, { width: w, opacity: 0.28 + 0.2 * (1 - s.diff) });
          A(b.hot, { width: w, opacity: 0.55 * s.diff });
        });
        scan.textContent = s.scan >= 1 ? "scanners: no pickle found" : "";
        const fired = s.leak >= 1;
        replyK.textContent = fired ? "CANARY IN THE REPLY" : "REFUSAL";
        replyA.textContent = fired ? D.canary : "vault code withheld";
        replyB.textContent = fired ? "trigger phrase present" : "no trigger phrase";
        A(replyA, { fill: fired ? V("lime") : V("warn") });
        A(replyCard, { stroke: fired ? V("lime") : V("line") });
        const lines = [
          [s.pin, "pin: reviewed tag loads, main is refused"],
          [s.gate, "behavior suite: generic prefixes stay quiet"],
          [s.triage, "weight queue: every moved matrix, refresh too"],
        ];
        rows.forEach((node, i) => {
          node.textContent = lines[i][0] >= 1 ? lines[i][1] : "";
          A(node, { fill: i === 2 ? V("warn") : V("ok"), opacity: lines[i][0] });
        });
        gHub.classList.toggle("hot", on(1) || on(2));
        gModel.classList.toggle("hot", on(1) || on(3) || on(4));
        gReply.classList.toggle("hot", on(1) || on(5));
        gFlow.classList.toggle("hot", on(6));
        gGate.classList.toggle("hot", on(7) || on(8));
        el.classList.toggle("lx-focus", s.focus >= 2);
        svg.setAttribute("aria-label", fired
          ? "Substituted adapter loaded; the reply contains the canary"
          : "Local hub offers a reviewed adapter to the guard");
      }

      const st = target(1);
      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }
          return api.tween(600, (k) => {
            if (g !== gen) return;
            X.lerpState(st, from, to, k);
            draw(st);
          }, X.ease.inOut);
        },
      };
    },
  });
})();
