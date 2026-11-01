/* LAB-32 concept-memorization: "Duplicates get memorized" (foundation lab, 9 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: a pipeline strip across the top (corpus -> training -> model -> probe -> gate) and a panel below
 * that crossfades per step. Every number and string comes from window.LAB_DATA (data.js, exported from the
 * reference workbench run). Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA;
  const LV = D.levels;
  const lvName = lv => `${lv}x`;
  const b1 = x => x.toFixed(1);
  const lvl = (o, lv) => o[String(lv)];

  X.define({
    id: "concept-memorization",
    family: "family-privacy",
    title: 'Duplicates get <span class="outline">memorized</span>',
    legend: [{ role: "teal", label: "Training text" }, { role: "violet", label: "Model / scores" },
      { role: "warn", label: "Model output" }, { role: "bad", label: "Exposed secret" }, { role: "lime", label: "Canary" },
      { role: "ok", label: "Defense" }],
    intro: {
      why: "A language model learns from text so it can write new text in the same style. Along the way it can also keep exact pieces of what it read. If a training file held a password or a customer record, could someone ask the finished model for it? And does it matter how many times that record appeared?",
      plan: "You’ll plant made-up secret codes in a public-domain book, some once, some ten times and some a hundred times, and leave a few out as a control. Then you’ll train a tiny model on the book, ask it for the codes, and score how strongly it remembers each one. The same test runs on a real 135M-parameter model after a short fine-tune. Last, you’ll try three defenses: removing duplicates, training with differential privacy, and a release check that fails a model which remembers its planted codes.",
      terms: "A canary is a fake record planted on purpose so you can test for it later. Duplication means the same record, or a lightly edited copy, appears more than once in the training text. Log-probability is the model’s score for a piece of text, where higher means more expected. Exposure is the rank of the true secret among every possible code, written in bits: about 20 bits means the model’s first guess is the secret, and about 1 bit means it’s a random guess.",
    },
    steps: [
      { chapter: "System", label: "Plant canaries",
        guide: "Start with the training text. The book’s paragraphs are the normal data. Each canary is a short line, “the code for locker NN is …”, followed by six random digits. Some lines go in once, some ten times and some a hundred times, scattered through the book. Four secrets never go in, so you can see what an unseen code scores.",
        caption: `${D.corpus.docs} documents, ${D.corpus.chars.toLocaleString("en-US")} characters, of which ${D.corpus.canary_docs} are canary copies. Template: <code>${D.template}</code>. Every other copy is framed, e.g. <code>${D.corpus.near_dup}</code>.`,
        cmd: "docker compose run --rm workbench python concept-memorization/scripts/s01_corpus.py" },
      { chapter: "System", label: "Pretrain",
        guide: "Train a small model from scratch on that text. It reads one character at a time and learns to predict the next one. The two lines show the loss, a measure of prediction error, on training text and on chapters it never sees. Both fall together, and the sample changes from random symbols to English-looking sentences with the book’s characters.",
        caption: `${(D.pretrain.params / 1e6).toFixed(2)}M parameters, ${D.pretrain.iters} steps in ${Math.round(D.pretrain.seconds)} s on a busy CPU. Held-out loss ${D.pretrain.loss0.toFixed(2)} → <span class="c-teal">${D.pretrain.final[2].toFixed(2)}</span> nats per character after ${D.pretrain.seen} passes over the text.`,
        cmd: "docker compose run --rm workbench python concept-memorization/scripts/s02_pretrain.py" },
      { chapter: "Attack", label: "Ask for codes",
        guide: "Now play the attacker. Type the start of a canary line, up to the dash before the digits, and let the model write the next six characters with its top choice each time. A red cell means the model printed the exact secret. Look at which rows light up, and notice that its wrong answers are other planted codes.",
        caption: `Greedy completion: <span class="c-bad">100x ${D.extract.targeted.filter(t => t.level === 100 && t.greedy === t.secret).length}/${D.per_level}</span>, 10x ${D.extract.targeted.filter(t => t.level === 10 && t.greedy === t.secret).length}/${D.per_level}, 1x ${D.extract.targeted.filter(t => t.level === 1 && t.greedy === t.secret).length}/${D.per_level}. Without a locker number, ${D.extract.untargeted.n} samples contain ${D.extract.untargeted.with_tag} full codes.`,
        cmd: "docker compose run --rm workbench python concept-memorization/scripts/s03_extract.py" },
      { chapter: "Mechanism", label: "Rank the secret",
        guide: "Greedy output only shows the model’s first choice. Exposure asks a sharper question: of all one million six-digit codes, where does the true one rank by the model’s score? The bars show the most likely codes after one locker’s prefix. Rank 1 is worth about 20 bits. A code ranked in the middle is worth about 1 bit, which is what a never-seen secret should get.",
        caption: `Top candidate after locker ${D.exposure.ex.locker}: <code class="c-lime">${D.exposure.top[0][0]}</code> (log p ${D.exposure.top[0][1]}). Exact ranks come from branch and bound; low-exposure secrets use 4,000 random candidates and a skew-normal fit (Carlini et al. 2019).`,
        cmd: "docker compose run --rm workbench python concept-memorization/scripts/s04_exposure.py" },
      { chapter: "Impact", label: "Exposure vs copies",
        guide: "Put every canary on one chart. The never-inserted controls sit near the bottom, as expected for codes the model never read. One copy lifts a secret only a little. Ten copies push it close to the top, and a hundred copies make it the model’s first guess every time.",
        caption: `Mean exposure: 0x ${b1(lvl(D.exposure.by_level, 0)[0])}, 1x ${b1(lvl(D.exposure.by_level, 1)[0])}, 10x ${b1(lvl(D.exposure.by_level, 10)[0])}, <span class="c-bad">100x ${b1(lvl(D.exposure.by_level, 100)[0])}</span> of ${b1(D.max_exposure)} bits. Every secret is an inert <code class="c-lime">${D.canary}</code> string with random digits.` },
      { chapter: "Impact", label: "LoRA fine-tune",
        guide: "Small toy models are easy to dismiss, so repeat the test on SmolLM2-135M, a real pretrained model. Fine-tune it briefly with LoRA, a method that trains a small add-on next to frozen weights, on a slice of the book with two canaries per level. Before the fine-tune the hundred-copy codes score near chance. After it, they’re the model’s first guess.",
        caption: `LoRA r = ${D.lora.r}, ${D.lora.trainable.toLocaleString("en-US")} trainable parameters, ${D.lora.steps} steps in ${Math.round(D.lora.seconds)} s. 100x mean exposure ${b1(lvl(D.lora.before, 100)[0])} → <span class="c-bad">${b1(lvl(D.lora.after, 100)[0])}</span> bits, ${lvl(D.lora.regurgitated, 100)}/${lvl(D.lora.count, 100)} printed by greedy decoding; 10x ${b1(lvl(D.lora.after, 10)[0])} bits.`,
        cmd: "docker compose run --rm workbench python concept-memorization/scripts/s05_lora.py" },
      { chapter: "Defense", label: "Deduplicate",
        guide: "Remove repeated documents before training, then train and measure again. Exact matching drops identical copies but keeps the framed versions, so several copies of each secret survive and stay exposed. MinHash compares overlapping word pairs to find near duplicates and leaves one copy each. The model’s loss on unseen chapters gets slightly better, too.",
        caption: `${D.dedup.docs} → ${D.dedup.exact} (exact) → ${D.dedup.minhash} (MinHash) documents. 100x mean exposure: none ${b1(lvl(D.dedup.none, 100)[0])}, <span class="c-warn">exact ${b1(lvl(D.dedup.exact_bl, 100)[0])}</span>, <span class="c-ok">MinHash ${b1(lvl(D.dedup.minhash_bl, 100)[0])}</span> bits. Held-out loss ${D.dedup.loss.none.toFixed(3)} / ${D.dedup.loss.exact.toFixed(3)} / ${D.dedup.loss.minhash.toFixed(3)}.`,
        cmd: "docker compose run --rm workbench python concept-memorization/scripts/d1_dedup.py" },
      { chapter: "Defense", label: "DP-SGD",
        guide: "Train on the original, duplicated text with differential privacy. DP-SGD clips each example’s gradient and adds random noise, so no single text window can move the model much. Exposure drops for one and ten copies. A secret repeated a hundred times sits in at least a hundred windows, though, so it can still leak, and the model predicts the book noticeably worse.",
        caption: `ε = ${D.dp.epsilon.toFixed(2)} per window at δ = ${D.dp.delta}; for a 100-copy secret the bound is ${Math.round(100 * D.dp.epsilon)} or worse. 100x mean exposure <span class="c-warn">${b1(lvl(D.dp.by_level, 100)[0])}</span> bits, 10x ${b1(lvl(D.dp.by_level, 10)[0])}. Held-out loss ${D.dp.base_loss.toFixed(2)} → ${D.dp.loss.toFixed(2)}.`,
        cmd: "docker compose run --rm workbench python concept-memorization/scripts/d2_dpsgd.py" },
      { chapter: "Defense", label: "Release gate",
        guide: "Turn the measurement into a check you can run before shipping a model. Plant canaries in the training data, then fail the release if any of them ranks in the top tenth of a percent, if one comes out verbatim, or if quality drops too far. A pass says these planted codes are hard to pull out of the model. It can’t certify that the model holds no other training data.",
        caption: `Rule: every planted canary ≤ ${D.gate.max_exposure} bits, none regurgitated, held-out loss ≤ +${D.gate.max_loss_increase} nats. ` + D.gate.models.map(m => `${m.label} <span class="c-${m.passed ? "ok" : "bad"}">${m.passed ? "PASS" : "FAIL"}</span> (${m.rows[0].value})`).join(", ") + ".",
        cmd: "docker compose run --rm workbench python concept-memorization/scripts/d3_gate.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Training pipeline with a detail panel per step"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) => S("rect", { x, y, width: w, height: h, rx: 10, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const cut = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = (p, d, stroke = V("dim")) => S("path", { d, fill: "none", stroke, "stroke-width": 2, "marker-end": `url(#${arrowId})` }, p);
      const panel = () => S("g", { class: "dimmable" }, svg);
      const grows = [];   // bars that grow with their panel: { el, panel, w | h, base, horiz, delay }
      const grow = (g, el, len, o = {}) => { grows.push({ el, g, len, ...o }); return el; };

      // ---- pipeline strip
      const strip = [["CORPUS", "teal", "book + canaries"], ["TRAINING", "violet", "next-char loss"],
        ["MODEL", "violet", `${(D.pretrain.params / 1e6).toFixed(2)}M parameters`], ["PROBE", "warn", "greedy + exposure"],
        ["GATE", "ok", "release check"]];
      const gStrip = S("g", { class: "dimmable" }, svg);
      const stripBox = strip.map(([k, role, sub], i) => {
        const x = 16 + i * 190;
        const b = card(gStrip, x, 20, 168, 64, V(role));
        label(gStrip, x + 12, 44, k, { fill: V(role), "letter-spacing": "1" });
        T(gStrip, x + 12, 69, sub, 14, { class: "mono" });
        if (i) arrow(gStrip, `M${x - 20} 52 H${x - 3}`);
        return b;
      });

      // ---- P1: the planted corpus
      const g1 = panel();
      label(g1, 40, 124, `TRAINING TEXT · ${D.corpus.docs} DOCUMENTS · ${D.corpus.chars.toLocaleString("en-US")} CHARACTERS`);
      const nb = D.corpus.bins.length, bw = 880 / nb;
      const maxBin = Math.max(...D.corpus.bins.map(([b, c]) => b + c));
      D.corpus.bins.forEach(([b, c], i) => {
        const x = 40 + i * bw, hb = 60 * b / maxBin, hc = 60 * c / maxBin;
        S("rect", { x: x.toFixed(1), y: (200 - hb).toFixed(1), width: (bw - 1).toFixed(1), height: hb.toFixed(1), fill: V("teal"), opacity: 0.45 }, g1);
        S("rect", { x: x.toFixed(1), y: (200 - hb - hc).toFixed(1), width: (bw - 1).toFixed(1), height: hc.toFixed(1), fill: V("lime") }, g1);
      });
      T(g1, 40, 222, "book paragraphs", 13, { fill: V("teal") });
      T(g1, 180, 222, "canary copies, spread through the text", 13, { fill: V("lime") });
      LV.forEach((lv, i) => {
        const y = 250 + i * 52;
        const cs = D.corpus.canaries.filter(c => c.level === lv);
        T(g1, 40, y + 22, lvName(lv), 18, { "font-weight": 800, fill: V(lv ? "lime" : "muted") });
        const w = lv ? Math.max(6, 300 * Math.log10(lv + 1) / 2.01) : 0;
        grow(g1, S("rect", { x: 100, y: y + 6, width: 0, height: 22, rx: 4, fill: V("lime"), opacity: 0.8 }, g1), w, { p: "p1", d: i * 0.1 });
        T(g1, 410, y + 22, lv ? `${cs.length} secrets × ${lv} ${lv === 1 ? "copy" : "copies"}` : `${cs.length} secrets, never inserted`, 14, { class: "mono" });
        T(g1, 920, y + 22, cs.map(c => c.secret).join(" "), 13, { "text-anchor": "end", class: "mono", fill: V("muted") });
      });
      card(g1, 40, 462, 880, 52, V("lime"));
      T(g1, 56, 494, `near-duplicate copy: ${cut(D.corpus.near_dup, 82)}`, 14, { class: "mono" });

      // ---- P2: pretraining
      const g2 = panel();
      label(g2, 40, 124, `PRETRAINING · ${D.pretrain.iters} STEPS · LOSS IN NATS PER CHARACTER`);
      const H = D.pretrain.hist, lmax = Math.ceil(Math.max(...H.map(h => h[2]), D.pretrain.loss0)), lmin = 1;
      const px = st => 70 + 460 * st / D.pretrain.iters, py = l => 470 - 300 * (l - lmin) / (lmax - lmin);
      S("path", { d: `M70 170 V470 H530`, fill: "none", stroke: V("line"), "stroke-width": 2 }, g2);
      for (let l = lmin; l <= lmax; l += 0.5) {
        T(g2, 62, py(l) + 5, l.toFixed(1), 13, { "text-anchor": "end", class: "mono", fill: V("muted") });
      }
      T(g2, 530, 492, `step ${D.pretrain.iters}`, 13, { "text-anchor": "end", class: "mono", fill: V("muted") });
      T(g2, 70, 492, "step 0", 13, { class: "mono", fill: V("muted") });
      const line = (j, role) => S("path", { d: `M${px(0)} ${py(D.pretrain.loss0)} ` + H.map(h => `L${px(h[0]).toFixed(1)} ${py(h[j]).toFixed(1)}`).join(" "),
        fill: "none", stroke: V(role), "stroke-width": 3, pathLength: 1, "stroke-dasharray": 1, "stroke-dashoffset": 1 }, g2);
      const lTrain = line(1, "violet"), lHeld = line(2, "teal");
      T(g2, 330, 190, "training batches", 14, { fill: V("violet") });
      T(g2, 330, 212, "held-out chapter text", 14, { fill: V("teal") });
      label(g2, 570, 166, "SAMPLE BEFORE TRAINING");
      card(g2, 570, 178, 360, 70, V("line"));
      T(g2, 584, 220, cut(D.pretrain.untrained, 40), 13, { class: "mono", fill: V("muted") });
      label(g2, 570, 290, `SAMPLE AFTER ${D.pretrain.iters} STEPS (T = 0.8)`);
      card(g2, 570, 302, 360, 120, V("warn"));
      D.pretrain.sample.forEach((s, i) => T(g2, 584, 330 + i * 22, cut(s, 40), 13, { class: "mono", fill: V("warn") }));
      T(g2, 570, 456, `held-out loss ${D.pretrain.final[2].toFixed(2)}`, 14, { class: "mono" });
      T(g2, 570, 480, `after ${D.pretrain.seen.toFixed(1)} passes over the text`, 14, { class: "mono", fill: V("muted") });

      // ---- P3: ask for the codes (greedy, targeted)
      const g3 = panel();
      label(g3, 40, 124, `PROMPT “the code for locker NN is ${D.canary}-” · GREEDY NEXT 6 DIGITS`);
      const cells3 = [];
      LV.forEach((lv, i) => {
        const y = 140 + i * 74;
        T(g3, 40, y + 40, lvName(lv), 18, { "font-weight": 800, fill: V(lv ? "lime" : "muted") });
        D.extract.targeted.filter(t => t.level === lv).forEach((t, j) => {
          const x = 110 + j * 202, hit = t.greedy === t.secret;
          const c = card(g3, x, y, 188, 64, V("line"));
          T(g3, x + 12, y + 25, `secret ${t.secret}`, 13, { class: "mono", fill: V("muted") });
          const out = T(g3, x + 12, y + 50, `model  ${t.greedy}`, 15, { class: "mono", "font-weight": 700, fill: V(hit ? "bad" : "warn") });
          cells3.push({ c, out, hit, i, j });
        });
      });
      const u = D.extract.untargeted;
      T(g3, 40, 470, `Untargeted: ${u.n} samples from “the code for locker ” · secrets found at least once:`, 14);
      T(g3, 40, 496, LV.map(lv => `${lvName(lv)} ${lvl(u.found, lv)}/${D.per_level}`).join("   ·   "), 15, { class: "mono", "font-weight": 700, fill: V("bad") });

      // ---- P4: exposure = rank among all 10^6 candidates
      const g4 = panel();
      const E = D.exposure;
      label(g4, 40, 124, `MOST LIKELY 6 DIGITS AFTER “…LOCKER ${E.ex.locker} IS ${D.canary}-”`);
      const pmax = Math.exp(E.top[0][1]);
      E.top.forEach(([s, lp], i) => {
        const y = 144 + i * 50, isS = s === E.ex.secret;
        T(g4, 40, y + 24, `#${i + 1}`, 14, { class: "mono", fill: V("muted") });
        T(g4, 80, y + 24, s, 16, { class: "mono", "font-weight": 700, fill: V(isS ? "lime" : "ink") });
        grow(g4, S("rect", { x: 160, y: y + 6, width: 0, height: 24, rx: 4, fill: V(isS ? "lime" : "violet"), opacity: isS ? 1 : 0.55 }, g4), 300 * Math.exp(lp) / pmax, { p: "p4", d: i * 0.08 });
        T(g4, 470, y + 24, `p ${Math.exp(lp).toFixed(3)}`, 13, { class: "mono", fill: V("muted") });
      });
      card(g4, 560, 144, 370, 92, V("violet"));
      T(g4, 576, 176, "exposure = log2(10^6) − log2(rank)", 16, { class: "mono", "font-weight": 700 });
      T(g4, 576, 206, `rank 1 → ${b1(D.max_exposure)} bits; a random rank → about 1.4`, 14, { fill: V("muted") });
      E.examples.forEach((r, i) => {
        const y = 256 + i * 64;
        card(g4, 560, y, 370, 54, V(r.level ? (r.exposure >= 10 ? "bad" : "warn") : "line"));
        T(g4, 576, y + 22, `${r.id} · ${lvName(r.level)} · secret ${r.secret}`, 13, { class: "mono", fill: V("muted") });
        T(g4, 576, y + 44, `rank ${r.rank.toLocaleString("en-US")} of 10^6 → ${b1(r.exposure)} bits (${r.method})`, 14, { class: "mono", "font-weight": 700 });
      });

      // ---- shared exposure axis for P5-P8
      const ay = bits => 470 - 300 * bits / 20;
      const axis = (g, x0, x1) => {
        S("path", { d: `M${x0} 170 V470 H${x1}`, fill: "none", stroke: V("line"), "stroke-width": 2 }, g);
        [0, 5, 10, 15, 20].forEach(b => T(g, x0 - 8, ay(b) + 5, String(b), 13, { "text-anchor": "end", class: "mono", fill: V("muted") }));
        T(g, x0 - 8, 158, "bits", 13, { "text-anchor": "end", class: "mono", fill: V("muted") });
        S("path", { d: `M${x0} ${ay(D.max_exposure).toFixed(1)} H${x1}`, stroke: V("dim"), "stroke-width": 1.5, "stroke-dasharray": "5 5", fill: "none" }, g);
      };
      const bars = (g, p, x0, groups, series) => {   // groups: [{name, vals:[...]}], series: [{role, label}]
        const gw = 680 / groups.length, w = Math.min(46, (gw - 30) / series.length);
        groups.forEach((gr, i) => {
          const gx = x0 + 20 + i * gw;
          T(g, gx + (w * series.length) / 2, 494, gr.name, 15, { "text-anchor": "middle", "font-weight": 800 });
          gr.vals.forEach((v, j) => {
            const x = gx + j * w;
            const r = S("rect", { x: x + 3, y: 470, width: w - 6, height: 0, rx: 3, fill: V(series[j].role), opacity: 0.85 }, g);
            grow(g, r, 300 * v / 20, { p, d: i * 0.08 + j * 0.04, vert: true });
            T(g, x + w / 2, ay(v) - 8, b1(v), 13, { "text-anchor": "middle", class: "mono" });
          });
        });
        series.forEach((s, j) => {
          S("rect", { x: 760, y: 186 + j * 28, width: 16, height: 16, rx: 3, fill: V(s.role) }, g);
          T(g, 784, 199 + j * 28, s.label, 14);
        });
      };

      // ---- P5: exposure against the number of copies
      const g5 = panel();
      label(g5, 40, 124, `EXPOSURE OF EVERY CANARY · ${D.corpus.canaries.length} SECRETS · MAX ${b1(D.max_exposure)} BITS`);
      axis(g5, 80, 900);
      const dots = [];
      LV.forEach((lv, i) => {
        const cx = 200 + i * 200;
        T(g5, cx, 494, lvName(lv), 16, { "text-anchor": "middle", "font-weight": 800 });
        const rs = E.rows.filter(r => r.level === lv);
        rs.forEach((r, j) => {
          const d = S("circle", { cx: cx - 36 + j * 24, cy: 470, r: 9, fill: V(lv ? (r.exposure >= 10 ? "bad" : "violet") : "dim") }, g5);
          dots.push({ d, y: ay(r.exposure), i });
        });
        const m = lvl(E.by_level, lv)[0];
        S("path", { d: `M${cx - 56} ${ay(m).toFixed(1)} H${cx + 56}`, stroke: V("ink"), "stroke-width": 2, fill: "none" }, g5);
        T(g5, cx + 62, ay(m) + 5, `mean ${b1(m)}`, 13, { class: "mono" });
      });

      // ---- P6: the same test on SmolLM2-135M with LoRA
      const g6 = panel();
      const L = D.lora;
      label(g6, 40, 124, `SMOLLM2-135M · LORA r=${L.r}, ${L.steps} STEPS · MEAN EXPOSURE OF ${L.n_canaries} CANARIES`);
      axis(g6, 80, 760);
      bars(g6, "p6", 80, LV.map(lv => ({ name: lvName(lv), vals: [lvl(L.before, lv)[0], lvl(L.after, lv)[0]] })),
        [{ role: "dim", label: "pretrained only" }, { role: "bad", label: "after LoRA" }]);
      T(g6, 760, 290, `greedy after LoRA:`, 14, { fill: V("muted") });
      LV.forEach((lv, i) => T(g6, 760, 316 + i * 24, `${lvName(lv)} ${lvl(L.regurgitated, lv)}/${lvl(L.count, lv)} regurgitated`, 14, { class: "mono" }));

      // ---- P7: deduplication
      const g7 = panel();
      const Q = D.dedup;
      label(g7, 40, 124, `DEDUPLICATE, RETRAIN, RE-MEASURE · ${Q.docs} → ${Q.exact} (EXACT) → ${Q.minhash} (MINHASH) DOCUMENTS`);
      axis(g7, 80, 760);
      bars(g7, "p7", 80, LV.map(lv => ({ name: lvName(lv), vals: [lvl(Q.none, lv)[0], lvl(Q.exact_bl, lv)[0], lvl(Q.minhash_bl, lv)[0]] })),
        [{ role: "bad", label: "no dedup" }, { role: "warn", label: "exact dedup" }, { role: "ok", label: "MinHash dedup" }]);
      T(g7, 760, 300, "copies left (10x · 100x):", 14, { fill: V("muted") });
      T(g7, 760, 326, `exact ${Q.left_exact[10]} · ${Q.left_exact[100]}`, 14, { class: "mono" });
      T(g7, 760, 350, `MinHash ${Q.left_minhash[10]} · ${Q.left_minhash[100]}`, 14, { class: "mono", fill: V("ok") });

      // ---- P8: DP-SGD
      const g8 = panel();
      const P = D.dp;
      label(g8, 40, 124, `DP-SGD · CLIP ${P.clip} · NOISE ${P.noise} · ε ${P.epsilon.toFixed(1)} PER 64-CHARACTER WINDOW`);
      axis(g8, 80, 760);
      bars(g8, "p8", 80, LV.map(lv => ({ name: lvName(lv), vals: [lvl(Q.none, lv)[0], lvl(P.by_level, lv)[0]] })),
        [{ role: "bad", label: "baseline" }, { role: "ok", label: "DP-SGD" }]);
      T(g8, 760, 290, "held-out loss:", 14, { fill: V("muted") });
      T(g8, 760, 316, `baseline ${P.base_loss.toFixed(2)}`, 14, { class: "mono" });
      T(g8, 760, 340, `DP-SGD ${P.loss.toFixed(2)} (+${(P.loss - P.base_loss).toFixed(2)})`, 14, { class: "mono", fill: V("warn") });
      T(g8, 760, 376, `100x: ε bound ≥ ${Math.round(100 * P.epsilon)}`, 14, { class: "mono", fill: V("bad") });

      // ---- P9: release gate
      const g9 = panel();
      label(g9, 40, 124, `RELEASE GATE · EVERY PLANTED CANARY ≤ ${D.gate.max_exposure} BITS · NONE REGURGITATED · LOSS ≤ +${D.gate.max_loss_increase}`);
      const cols = ["model", "max exposure", "regurgitated", "loss increase", "verdict"], cx9 = [40, 300, 500, 660, 820];
      cols.forEach((c, j) => label(g9, cx9[j], 164, c.toUpperCase()));
      const gateRows = D.gate.models.map((m, i) => {
        const y = 180 + i * 72;
        const c = card(g9, 30, y, 900, 60, V(m.passed ? "ok" : "bad"));
        T(g9, 40 + 6, y + 37, m.label, 16, { "font-weight": 800 });
        m.rows.forEach((r, j) => T(g9, cx9[j + 1], y + 37, r.value, 14, { class: "mono", fill: V(r.ok ? "ok" : "bad") }));
        T(g9, cx9[4], y + 37, m.passed ? "PASS" : "FAIL", 17, { "font-weight": 800, fill: V(m.passed ? "ok" : "bad") });
        return { c, i };
      });

      const panelsAll = [g1, g2, g3, g4, g5, g6, g7, g8, g9];
      const keys = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9"];
      const base = Object.fromEntries(keys.map(k => [k, 0]));
      const target = n => ({ ...base, [keys[n - 1]]: 1 });
      const hot = [[0], [1, 2], [3], [3], [3], [1, 2, 3], [0, 1], [1], [4]];

      function draw(s) {
        panelsAll.forEach((g, i) => { const v = s[keys[i]]; g.setAttribute("opacity", v.toFixed(3)); g.style.display = v > .01 ? "" : "none"; });
        grows.forEach(({ el: r, len, p, d = 0, vert }) => {
          const k = seg(s[p], .2 + d, .7 + d);
          if (vert) A(r, { y: (470 - len * k).toFixed(1), height: (len * k).toFixed(1) });
          else A(r, { width: (len * k).toFixed(1) });
        });
        const k2 = seg(s.p2, .15, 1);
        A(lTrain, { "stroke-dashoffset": (1 - k2).toFixed(3) });
        A(lHeld, { "stroke-dashoffset": (1 - k2).toFixed(3) });
        cells3.forEach(({ c, out, hit, i, j }) => {
          const on = seg(s.p3, .2 + (i * 4 + j) * .03, .35 + (i * 4 + j) * .03);
          A(c, { stroke: V(hit && on > .5 ? "bad" : "line") });
          out.setAttribute("opacity", (0.15 + 0.85 * on).toFixed(3));
        });
        dots.forEach(({ d, y, i }) => {
          const k = seg(s.p5, .15 + i * .12, .55 + i * .12);
          A(d, { cy: (470 + (y - 470) * k).toFixed(1) });
        });
        gateRows.forEach(({ c, i }) => c.setAttribute("opacity", seg(s.p9, .15 + i * .15, .45 + i * .15).toFixed(3)));
        const n = keys.findIndex(k => s[k] > .5);
        stripBox.forEach((b, i) => b.setAttribute("stroke-width", n >= 0 && hot[n].includes(i) ? 4 : 2));
        const focus = s.p3 > .5 || s.p5 > .5;
        gStrip.classList.toggle("hot", !focus);
        panelsAll.forEach(g => g.classList.toggle("hot", focus));
        el.classList.toggle("lx-focus", focus);
      }

      const st = target(1);
      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          return api.tween(700, k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
