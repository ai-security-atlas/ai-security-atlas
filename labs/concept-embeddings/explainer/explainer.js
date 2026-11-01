/* LAB-25 concept-embeddings: "Vectors that are not words" (foundation lab, 9 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: the model strip across the top (token ids -> embedding table -> transformer -> tied LM head ->
 * next token, with a second "inputs_embeds" door into the transformer) and a detail panel below that
 * crossfades per step. Every number and string comes from window.LAB_DATA (data.js, exported from the
 * reference workbench run). Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA, SP = D.soft, PJ = D.proj, VA = D.validate, EV = D.evaluate;
  const N = n => n.toLocaleString("en");
  const q = s => "“" + s + "”";
  const VAL = Object.entries(VA.checks);
  const AD = VA.adaptive;
  const FLIP = D.door.mix.find(m => m.reply !== D.door.mix[0].reply) || D.door.mix[D.door.mix.length - 1];
  const adTxt = a => a.solved != null ? `canary forced at step ${a.solved}` : `not forced in 40 steps (loss ${a.last_loss.toFixed(2)})`;

  X.define({
    id: "concept-embeddings",
    family: "family-prompt",
    title: 'Vectors that are not <span class="outline">words</span>',
    legend: [{ role: "teal", label: "Tokens / text" }, { role: "violet", label: "Model / table" },
      { role: "warn", label: "Reply" }, { role: "bad", label: "Free vectors" }, { role: "lime", label: "Canary" },
      { role: "ok", label: "Control" }],
    intro: {
      "why": "A language model never reads words. It looks up each token in a table of vectors and does its math on those vectors. Some tools let a caller hand the model vectors directly. What can that caller do that a person typing text can’t? You’ll find out on a small open model, with a harmless canary string as the target.",
      "plan": "First you’ll open the embedding table and see that the same table also scores the output. You’ll tell it apart from the vectors a search index stores. Then you’ll tune a few free vectors until the model prints the canary, turn them back into words, and test two controls a server can apply.",
      "terms": "An embedding is a list of numbers that stands for a token, a piece of text. The embedding table holds one such row for every token in the vocabulary. Gradient descent is a method that nudges numbers to lower an error score. A soft prompt is a set of vectors tuned that way. Projection replaces each vector with its closest real token. The canary is a fixed, harmless string used as the target."
    },
    steps: [
      { chapter: "System", label: "The table",
        guide: "Every token ID picks one row of the embedding table, and that row is what the model computes on. Look at the nearest rows for a few words. The neighbors are spelling variants and related words. This model also reuses the same table to score the next token. That design is called tied embeddings.",
        caption: `${D.model}: <span class="c-violet">embed_tokens</span> is ${D.shape[0].toLocaleString("en")} × ${D.shape[1]}, ${((D.shape[0] * D.shape[1]) / D.params * 100).toFixed(0)}% of ${(D.params / 1e6).toFixed(1)}M parameters. <code>lm_head.weight is embed_tokens.weight</code> → <b>${D.tied}</b>, so logits = h · E<sup>T</sup> (top next token after “The capital of France is”: <code>${D.top.trim()}</code>). Row norms run from ${D.norms.n_min} to ${D.norms.n_max}.`,
        cmd: "docker compose run --rm workbench python concept-embeddings/scripts/s01_table.py" },
      { chapter: "System", label: "Two kinds of vector",
        guide: "Search systems also call their vectors embeddings. A separate model computes one vector per sentence, and an application stores it in an index. Watch the word ‘bank’. Its row in the language model never changes with the sentence around it. The sentence vectors move with meaning. Attacks on those stored records belong to the retrieval labs.",
        caption: `SmolLM2 row for <code>' bank'</code>: ${D.rec.dim_in} numbers, cosine <b>${D.rec.bank_in.toFixed(3)}</b> between the river and the account sentence. <span class="c-teal">${D.rec.st_model.split("/")[1]}</span> record: ${D.rec.dim_rec} numbers, cosine ${D.rec.bank_rec.toFixed(3)} for the same pair; password question vs a paraphrase ${D.rec.q_same.toFixed(3)}, vs an unrelated line ${D.rec.q_other.toFixed(3)}. The record can’t even enter SmolLM2 (${D.rec.dim_rec} ≠ ${D.rec.dim_in}).`,
        cmd: "docker compose run --rm workbench python concept-embeddings/scripts/s02_two_vectors.py" },
      { chapter: "Attack", label: "A wider door",
        guide: "Some interfaces accept vectors in place of token IDs. Sending the table rows for a prompt gives the same answer as sending the text. The risk is in what else gets through. A point between two tokens goes in without any error, and so does a point far outside the table. Typed text can reach only the rows that exist, so this door opens far more of the space.",
        caption: `Risk: <code>generate(input_ids)</code> and <code>generate(inputs_embeds=E[ids])</code> give the same reply (${D.door.same}): ${q(D.door.reply)}. Blending <code>' France'</code> into <code>' Italy'</code> lands up to ${Math.max(...D.door.mix.map(m => m.dist)).toFixed(2)} away from any token and the answer flips to ${q(FLIP.reply)} at t = ${FLIP.t}. A row scaled ×100 is <span class="c-bad">accepted</span> with no error.`,
        cmd: "docker compose run --rm workbench python concept-embeddings/scripts/s03_wider_door.py" },
      { chapter: "Mechanism", label: "Tune the vectors",
        guide: "Now gradient descent picks the vectors. You place a few free vectors at the start of the user turn and score how far the reply is from the canary. Each step moves the vectors to lower that score, called the loss. Watch the curve fall until greedy decoding, which always takes the top token, prints the canary after every training prompt.",
        caption: `${D.n_soft} <span class="c-bad">free vectors</span> × ${D.shape[1]}, started from random table rows, Adam lr 0.01. Loss ${SP.curve[0][1].toFixed(2)} → ${SP.curve[SP.curve.length - 1][1].toFixed(2)}; all ${SP.n_train} training prompts forced at step <b>${SP.solved}</b> (${Math.round(SP.seconds)} s on a shared CPU).`,
        cmd: "docker compose run --rm workbench python concept-embeddings/scripts/s04_soft_prompt.py" },
      { chapter: "Impact", label: "The canary appears",
        guide: "The tuned vectors now sit in front of ordinary questions. On the training prompts the reply starts with the canary. Check the held-out prompts too. The optimizer never saw those questions. Count how many of them print it as well. Any transfer you see is a result for this one model and seed, and other runs can land differently.",
        caption: `Observation: <code class="c-lime">${D.canary}</code> opens the reply on ${SP.train}/${SP.n_train} training prompts, ${SP.held}/${SP.n_held} held-out prompts and ${SP.control}/1 control question. Example: ${q(SP.example)}.` },
      { chapter: "Impact", label: "Snap to tokens",
        guide: "Next you turn each vector back into its nearest real token and send the result as plain text. Watch whether the canary survives. Also check which token each vector now sits closest to, the random one it started from or a new one. GCG is an attack that searches over real tokens to force a reply. The gap between vectors and tokens is what it has to cross.",
        caption: `Projected text: <code>${PJ.text}</code> (cosine ${Math.min(...PJ.cos).toFixed(2)}–${Math.max(...PJ.cos).toFixed(2)}, distance ${Math.min(...PJ.dist).toFixed(2)}–${Math.max(...PJ.dist).toFixed(2)}). Canary loss ${PJ.soft_loss.toFixed(3)} with the vectors, <span class="c-bad">${PJ.proj_loss.toFixed(3)}</span> with the tokens (step-0 loss ${D.init_loss.toFixed(3)}). Nearest token = starting token for ${PJ.same_as_init}/${PJ.tokens.length} vectors. Canary emitted: <b>${PJ.forced}/${PJ.n}</b>.`,
        cmd: "docker compose run --rm workbench python concept-embeddings/scripts/s05_project.py" },
      { chapter: "Defense", label: "Text only",
        guide: "The first control is an interface decision. A toy endpoint runs the same requests under two policies. One accepts a prompt_embeds field, the other refuses it. Only the request with tuned vectors reaches the canary, and only on the open endpoint. vLLM, a popular serving engine, keeps this input off unless you enable it.",
        caption: `Open policy: the <code>prompt_embeds</code> request returns HTTP ${D.gate[1].status} with the canary. <span class="c-ok">Text-only</span>: the same request gets HTTP ${D.gate[4].status}. Plain text and the projected tokens never reach it under either policy (${D.gate.filter(g => g.canary).length}/${D.gate.length} rows leak).`,
        cmd: "docker compose run --rm workbench python concept-embeddings/scripts/d1_text_only.py" },
      { chapter: "Defense", label: "Check the vectors",
        guide: "Sometimes a service must accept vectors. You try two checks. The first compares each vector’s length and range with the table, and the tuned vectors pass it. The second asks whether each vector is a real row. It catches them, and it accepts honest prompts. A looser distance limit gives an attacker room to optimize inside it.",
        caption: `${VAL.map(([k, v]) => `${k}: soft ${v.soft}/${D.n_soft}, honest ${v.honest}/${VA.n_honest}`).join("; ")}. Soft norms ${VA.norm[0]}–${VA.norm[1]} sit inside the table band ${VA.band[0]}–${VA.band[1]}. Inside a tolerance: ${AD.map(a => `r = ${a.r}: ${adTxt(a)}`).join("; ")}.`,
        cmd: "docker compose run --rm workbench python concept-embeddings/scripts/d2_validate.py" },
      { chapter: "Defense", label: "What it shows",
        guide: "The final evaluation reruns the main claims from scratch. On this small model, a few tuned vectors control how the reply starts, and their nearest words don’t. The lab doesn’t show that hosted chat APIs accept vectors, and most of them don’t. If yours does, treat that input as a privileged channel and log what comes in.",
        caption: `Fresh run: tied ${EV["tied input/output embeddings"]}, both doors give identical logits (${EV["input_ids == inputs_embeds (logits)"]}), soft prompt solved at step ${EV.solved_step}, held-out ${EV["soft prompt forces canary (held-out, of 4)"]}/4, projected tokens ${EV["projected tokens force canary (of 8 prompts)"]}/8, <span class="c-ok">text-only gate</span> rejects embeddings (${EV["text-only gate rejects prompt_embeds"]}).`,
        cmd: "docker compose run --rm workbench python concept-embeddings/scripts/evaluate.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Token ids, embedding table, transformer and tied output head, with a detail panel"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) => S("rect", { x, y, width: w, height: h, rx: 12, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const clip = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = (p, d, o = {}) => S("path", { d, fill: "none", stroke: V("dim"), "stroke-width": 2, "marker-end": `url(#${arrowId})`, ...o }, p);

      // ---- model strip
      const strip = [["TOKEN IDS", "teal", "text → ids"], ["TABLE E", "violet", `${N(D.shape[0])} × ${D.shape[1]}`],
        ["TRANSFORMER", "violet", `${D.layers} layers`], ["LM HEAD = E", "violet", "tied weights"], ["NEXT TOKEN", "warn", "reply"]];
      const gStrip = S("g", { class: "dimmable" }, svg);
      const boxes = strip.map(([k, role, sub], i) => {
        const x = 30 + i * 186;
        const b = card(gStrip, x, 20, 160, 66, V(role));
        label(gStrip, x + 14, 46, k, { fill: V(role) });
        T(gStrip, x + 14, 72, sub, 14, { class: "mono" });
        if (i) arrow(gStrip, `M${x - 24} 53 H${x - 4}`);
        return b;
      });
      const gDoor = S("g", {}, gStrip);
      S("path", { d: "M380 112 C 380 96, 396 92, 402 88", fill: "none", stroke: V("bad"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, gDoor);
      T(gDoor, 140, 116, "inputs_embeds: any vector", 14, { class: "mono", fill: V("bad"), "font-weight": 700 });

      const panel = () => S("g", { class: "dimmable" }, svg);
      const Y0 = 150;

      // ---- P1: nearest neighbors
      const gNb = panel();
      label(gNb, 60, Y0 - 12, "NEAREST ROWS BY COSINE");
      const nb = Object.entries(D.neighbors).slice(0, 5);
      nb.forEach(([w, row], i) => {
        const y = Y0 + i * 66;
        card(gNb, 60, y, 840, 56, V("line"));
        T(gNb, 80, y + 35, JSON.stringify(" " + w.trim()), 16, { class: "mono", "font-weight": 800, fill: V("teal") });
        row.forEach(([t, c], j) => {
          const x = 290 + j * 205;
          T(gNb, x, y + 25, JSON.stringify(t), 14, { class: "mono" });
          S("rect", { x, y: y + 34, width: Math.max(4, 170 * c), height: 10, rx: 3, fill: V("violet"), opacity: .7 }, gNb);
          T(gNb, x + 178, y + 25, c.toFixed(2), 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
        });
      });

      // ---- P2: two kinds of vector
      const gRec = panel();
      const recCard = (x, role, head, sub, rows) => {
        card(gRec, x, Y0 - 10, 410, 350, V(role));
        T(gRec, x + 20, Y0 + 22, head, 18, { "font-weight": 700, fill: V(role) });
        T(gRec, x + 20, Y0 + 48, sub, 14, { fill: V("muted") });
        rows.forEach(([k, v], i) => {
          const y = Y0 + 96 + i * 72;
          T(gRec, x + 20, y, k, 14);
          S("rect", { x: x + 20, y: y + 12, width: 300, height: 14, rx: 4, fill: V("panel-2"), stroke: V("line") }, gRec);
          S("rect", { x: x + 20, y: y + 12, width: Math.max(3, 300 * Math.max(0, v)), height: 14, rx: 4, fill: V(role), opacity: .8 }, gRec);
          T(gRec, x + 390, y + 25, v.toFixed(3), 15, { class: "mono", "text-anchor": "end", "font-weight": 700 });
        });
      };
      recCard(60, "violet", `Input embedding · ${D.rec.dim_in} numbers`, "a fixed row inside the model, one per token",
        [["' bank': river vs account sentence", D.rec.bank_in]]);
      recCard(490, "teal", `Record vector · ${D.rec.dim_rec} numbers`, `${D.rec.st_model.split("/")[1]}, stored by an app`,
        [["river bank vs bank account", D.rec.bank_rec], ["password question vs paraphrase", D.rec.q_same], ["password question vs unrelated", D.rec.q_other]]);

      // ---- P3: the wider door
      const gDoorP = panel();
      label(gDoorP, 60, Y0 - 12, "REPLACE ' FRANCE' WITH (1 − t)·E[France] + t·E[Italy]");
      const mixRows = D.door.mix.map((m, i) => {
        const y = Y0 + i * 58;
        const c = card(gDoorP, 60, y, 840, 48, V(m.dist > 0 ? "bad" : "teal"));
        T(gDoorP, 80, y + 30, `t = ${m.t}`, 15, { class: "mono", "font-weight": 700 });
        T(gDoorP, 200, y + 30, `distance to nearest token ${m.dist.toFixed(2)}`, 14, { class: "mono", fill: V(m.dist > 0 ? "bad" : "muted") });
        T(gDoorP, 880, y + 30, clip(m.reply, 34), 15, { class: "mono", "text-anchor": "end", fill: V("warn") });
        return c;
      });
      T(gDoorP, 60, Y0 + 318, `row × 100 → accepted, reply ${q(clip(D.door.far, 40))}`, 15, { class: "mono", fill: V("bad"), "font-weight": 700 });
      T(gDoorP, 60, Y0 + 346, `text reaches ${N(D.shape[0])} points per position; this door reaches any point in R^${D.shape[1]}`, 14, { fill: V("muted") });
      void mixRows;

      // ---- P4: loss curve
      const gLoss = panel();
      label(gLoss, 60, Y0 - 12, "CANARY LOSS ON THE TRAINING PROMPTS");
      const cv = SP.curve, lmax = Math.max(...cv.map(c => c[1]));
      const px0 = 110, px1 = 880, py0 = Y0 + 10, py1 = Y0 + 300;
      const sx = i => px0 + (px1 - px0) * i / Math.max(1, cv[cv.length - 1][0]);
      const sy = v => py1 - (py1 - py0) * v / lmax;
      S("path", { d: `M${px0} ${py0} V${py1} H${px1}`, fill: "none", stroke: V("line"), "stroke-width": 2 }, gLoss);
      [0, Math.round(lmax / 2), Math.floor(lmax)].forEach(v => T(gLoss, px0 - 10, sy(v) + 5, String(v), 13, { class: "mono", "text-anchor": "end", fill: V("muted") }));
      const lossPath = S("path", { d: cv.map((c, i) => `${i ? "L" : "M"}${sx(c[0]).toFixed(1)} ${sy(c[1]).toFixed(1)}`).join(" "), fill: "none", stroke: V("bad"), "stroke-width": 3 }, gLoss);
      const plen = 2400;
      lossPath.setAttribute("stroke-dasharray", `${plen}`);
      const dots = cv.map(c => S("circle", { cx: sx(c[0]), cy: sy(c[1]), r: 5, fill: V(c[2] === SP.n_train ? "lime" : "bad") }, gLoss));
      const gSolved = S("g", {}, gLoss);
      T(gSolved, px1, py0 + 20, `step ${SP.solved}: canary forced on ${SP.n_train}/${SP.n_train}`, 16, { class: "mono", "text-anchor": "end", fill: V("lime"), "font-weight": 700 });
      T(gLoss, px1, py1 + 26, "optimizer step", 13, { "text-anchor": "end", fill: V("muted") });

      // ---- P5: canary appears
      const gHit = panel();
      label(gHit, 60, Y0 - 12, "GREEDY REPLY WITH THE TUNED VECTORS IN FRONT");
      const hits = [["training prompts", SP.train, SP.n_train], ["held-out prompts", SP.held, SP.n_held], ["control question", SP.control, 1]];
      const hitRows = hits.map(([k, a, b], i) => {
        const y = Y0 + i * 80;
        card(gHit, 60, y, 840, 66, V(a ? "lime" : "line"));
        T(gHit, 80, y + 40, k, 17, { "font-weight": 700 });
        const bar = S("rect", { x: 330, y: y + 24, width: 0, height: 18, rx: 5, fill: V("lime"), opacity: .8 }, gHit);
        T(gHit, 880, y + 40, `${a}/${b}`, 20, { class: "mono", "text-anchor": "end", "font-weight": 800, fill: V(a ? "lime" : "muted") });
        return { bar, w: 440 * a / b };
      });
      T(gHit, 60, Y0 + 278, "example reply", 13, { fill: V("muted"), "font-weight": 700 });
      T(gHit, 60, Y0 + 306, q(SP.example), 18, { class: "mono", fill: V("lime"), "font-weight": 700 });

      // ---- P6: projection
      const gProj = panel();
      label(gProj, 60, Y0 - 12, "EACH VECTOR → ITS NEAREST TOKEN");
      PJ.tokens.forEach((t, i) => {
        const x = 60 + i * 106;
        S("rect", { x, y: Y0, width: 96, height: 46, rx: 8, fill: V("bad"), "fill-opacity": .14, stroke: V("bad"), "stroke-width": 1.5 }, gProj);
        T(gProj, x + 48, Y0 + 28, `v${i}`, 15, { class: "mono", "text-anchor": "middle", fill: V("bad") });
        arrow(gProj, `M${x + 48} ${Y0 + 50} V${Y0 + 76}`);
        S("rect", { x, y: Y0 + 82, width: 96, height: 46, rx: 8, fill: V("teal"), "fill-opacity": .12, stroke: V("teal"), "stroke-width": 1.5 }, gProj);
        T(gProj, x + 48, Y0 + 110, clip(JSON.stringify(t), 10), 14, { class: "mono", "text-anchor": "middle", fill: V("teal") });
        T(gProj, x + 48, Y0 + 148, `cos ${PJ.cos[i].toFixed(2)}`, 13, { class: "mono", "text-anchor": "middle", fill: V("muted") });
      });
      const gProjRes = S("g", {}, gProj);
      card(gProjRes, 60, Y0 + 172, 410, 150, V("bad"));
      T(gProjRes, 80, Y0 + 206, "vectors", 17, { "font-weight": 700, fill: V("bad") });
      T(gProjRes, 80, Y0 + 238, `canary loss ${PJ.soft_loss.toFixed(3)}`, 15, { class: "mono" });
      T(gProjRes, 80, Y0 + 268, `forced ${SP.train}/${SP.n_train} training prompts`, 15, { class: "mono", fill: V("lime") });
      card(gProjRes, 490, Y0 + 172, 410, 150, V("teal"));
      T(gProjRes, 510, Y0 + 206, "nearest tokens, as text", 17, { "font-weight": 700, fill: V("teal") });
      T(gProjRes, 510, Y0 + 238, `canary loss ${PJ.proj_loss.toFixed(3)} (start ${D.init_loss.toFixed(3)})`, 15, { class: "mono" });
      T(gProjRes, 510, Y0 + 268, `canary emitted ${PJ.forced}/${PJ.n}`, 15, { class: "mono", fill: V("ok"), "font-weight": 700 });

      // ---- P7: gate
      const gGate = panel();
      [[60, "POLICY"], [220, "REQUEST"], [640, "HTTP"], [760, "CANARY"]].forEach(([x, t]) => label(gGate, x, Y0 - 12, t));
      D.gate.forEach((g, i) => {
        const y = Y0 + i * 54;
        card(gGate, 50, y, 860, 44, V(g.canary ? "bad" : g.status === 400 ? "ok" : "line"));
        T(gGate, 66, y + 28, g.policy, 15, { class: "mono", "font-weight": 700, fill: V(g.policy === "open" ? "muted" : "ok") });
        T(gGate, 220, y + 28, g.request, 15);
        T(gGate, 640, y + 28, String(g.status), 15, { class: "mono", fill: V(g.status === 400 ? "ok" : "muted"), "font-weight": 700 });
        T(gGate, 760, y + 28, g.canary ? D.canary : "no", 15, { class: "mono", fill: V(g.canary ? "lime" : "muted"), "font-weight": 700 });
      });

      // ---- P8: validators
      const gVal = panel();
      [[60, "VALIDATOR"], [470, "TUNED VECTORS FLAGGED"], [720, "HONEST FLAGGED"]].forEach(([x, t]) => label(gVal, x, Y0 - 12, t));
      VAL.forEach(([k, v], i) => {
        const y = Y0 + i * 58;
        card(gVal, 50, y, 860, 46, V(v.soft ? "ok" : "bad"));
        T(gVal, 66, y + 29, k, 15, { "font-weight": 700 });
        T(gVal, 470, y + 29, `${v.soft}/${D.n_soft}`, 16, { class: "mono", "font-weight": 800, fill: V(v.soft ? "ok" : "bad") });
        T(gVal, 720, y + 29, `${v.honest}/${VA.n_honest}`, 16, { class: "mono", "font-weight": 800, fill: V(v.honest ? "bad" : "ok") });
      });
      label(gVal, 60, Y0 + 152, "ADAPTIVE ATTACKER: EVERY VECTOR WITHIN r OF A TOKEN");
      AD.forEach((a, i) => {
        const y = Y0 + 168 + i * 58;
        card(gVal, 50, y, 860, 46, V(a.solved != null ? "bad" : "ok"));
        T(gVal, 66, y + 29, `tolerance r = ${a.r}`, 15, { class: "mono", "font-weight": 700 });
        T(gVal, 300, y + 29, `passes (max ${a.dmax.toFixed(2)})`, 15, { class: "mono", fill: V("muted") });
        T(gVal, 890, y + 29, adTxt(a), 15, { class: "mono", "text-anchor": "end", fill: V(a.solved != null ? "lime" : "ok"), "font-weight": 700 });
      });

      // ---- P9: evaluate
      const gEval = panel();
      label(gEval, 60, Y0 - 12, "EVALUATE: A FRESH RUN OF THE MAIN CLAIMS");
      Object.entries(EV).filter(([k]) => k !== "seconds").forEach(([k, v], i) => {
        const y = Y0 + i * 36;
        T(gEval, 60, y + 20, k, 15);
        T(gEval, 900, y + 20, String(v), 15, { class: "mono", "text-anchor": "end", "font-weight": 700, fill: V("violet") });
        S("path", { d: `M60 ${y + 30} H900`, stroke: V("line"), "stroke-width": 1 }, gEval);
      });

      const panels = [gNb, gRec, gDoorP, gLoss, gHit, gProj, gGate, gVal, gEval];
      const FOCUS = [1, 1, 2, 2, 4, 0, 2, 2, null];
      const st = { p: 1, k: 1 };
      const target = n => ({ p: n, k: 1 });

      function draw(s) {
        const n = s.p, k = s.k;
        panels.forEach((g, i) => {
          const on = i + 1 === n;
          g.setAttribute("opacity", on ? k.toFixed(3) : "0");
          g.style.display = on ? "" : "none";
        });
        gDoor.setAttribute("opacity", n >= 3 ? "1" : "0");
        boxes.forEach((b, i) => b.setAttribute("stroke-width", FOCUS[n - 1] === i ? 4 : 2));
        lossPath.setAttribute("stroke-dashoffset", n === 4 ? (plen * (1 - seg(k, 0, .9))).toFixed(1) : "0");
        dots.forEach((d, i) => d.setAttribute("opacity", n === 4 ? seg(k, i / dots.length * .9, i / dots.length * .9 + .1).toFixed(3) : "1"));
        gSolved.setAttribute("opacity", n === 4 ? seg(k, .85, 1).toFixed(3) : "1");
        hitRows.forEach(({ bar, w }) => A(bar, { width: (w * (n === 5 ? seg(k, .2, 1) : 1)).toFixed(1) }));
        gProjRes.setAttribute("opacity", n === 6 ? seg(k, .4, 1).toFixed(3) : "1");
        const focus = n === 5 || n === 6;
        gStrip.classList.toggle("hot", !focus);
        panels.forEach(g => g.classList.toggle("hot", focus));
        el.classList.toggle("lx-focus", focus);
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          st.p = n; st.k = 0; draw(st);
          return api.tween(650, k => { if (g !== gen) return; st.k = k; draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
