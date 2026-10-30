/* LAB-13 attack-membership: "Was this record in the training set?" (10 steps).
 * One persistent scene across the top: the target model card → the loss histogram of the 400 candidates
 * (members vs non-members) with the attacker's threshold. A detail panel below changes per step (the audit
 * split, the ROC curve and its low-FPR corner, overfitting, shadow models on one canary, the ART cross-check,
 * and the three defenses). Every number comes from window.LAB_DATA (data.js, exported from the reference run).
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp, E = X.ease;
  const D = window.LAB_DATA, TG = D.target, H = D.hist, TH = D.threshold, SH = D.shadows;
  const pc = v => (100 * v).toFixed(1) + "%";
  const a3 = v => v.toFixed(3);
  const LOSS = TH["loss threshold"], LIRA = SH.results["LiRA (offline)"], LOSS4 = SH.results["loss threshold"];
  const ovT = D.overfit.filter(r => r.records === TG.train), ovC = D.overfit.find(r => r.records !== TG.train);
  const dp8 = D.dp[D.dp.length - 1], dp0 = D.dp[0];
  const LO = D.label_only, loAug = Object.keys(LO).find(k => k.startsWith("augmented")), loGap = LO["gap (public: label)"];
  const RG = D.regularize;
  const k1 = Math.round(LOSS.tpr1 * TG.n);

  X.define({
    id: "attack-membership",
    family: "family-privacy",
    title: 'Was this record in the <span class="outline">training</span> set?',
    legend: [{ role: "teal", label: "Members" }, { role: "bad", label: "Attacker's threshold / guess" },
      { role: "violet", label: "Model" }, { role: "warn", label: "Scores" }, { role: "lime", label: "Canary records" },
      { role: "ok", label: "Defense" }],
    steps: [
      { chapter: "System", label: "The target",
        caption: `A small CNN trained on only <span class="c-teal">${TG.n} digit images</span> plus ${TG.c} <span class="c-lime">canary records</span> with deliberately wrong labels. The audit asks, for each of ${TG.n} members and ${TG.n} non-members: was this one in the training set?`,
        cmd: "docker compose run --rm workbench python attack-membership/scripts/s01_target.py" },
      { chapter: "System", label: "A loss gap",
        caption: `Members are classified ${pc(TG.acc_members)} right, non-members ${pc(TG.acc_nonmembers)}. Most of both have a tiny <span class="c-warn">loss</span>; the members just pile up a bit further left. The leak lives in that shift.` },
      { chapter: "Attack", label: "Threshold attack",
        caption: `Call a record a member when its loss is below a <span class="c-bad">threshold</span>. Over all thresholds: AUC ${a3(LOSS.auc)}, against 0.5 for a coin flip and ${a3(TH["gap (correct=member)"].auc)} for the gap baseline “it got it right”.`,
        cmd: "docker compose run --rm workbench python attack-membership/scripts/s02_threshold.py" },
      { chapter: "Mechanism", label: "The low-FPR corner",
        caption: `A privacy claim is about being <em>sure</em>. Allow only 1% false positives (2 of ${TG.n} non-members) and the attack finds <span class="c-bad">${k1} of ${TG.n}</span> members: TPR ${pc(LOSS.tpr1)}. Report this corner, not accuracy.` },
      { chapter: "Mechanism", label: "Overfitting drives it",
        caption: `Same ${TG.train} records, more epochs: AUC ${a3(ovT[0].auc)} at ${ovT[0].epochs} epochs, ${a3(ovT.find(r => r.epochs === 100).auc)} at 100. The zoo's cnn-clean, trained on ${ovC.records} records, gives ${a3(ovC.auc)} on the same members.`,
        cmd: "docker compose run --rm workbench python attack-membership/scripts/s03_overfit.py" },
      { chapter: "Impact", label: "Shadows find canaries",
        caption: `${SH.K} shadow models never saw <code class="c-lime">${SH.canary_ids[0]}</code>: their confidence in its label sits near ${(SH.canary.phi_shadows[0].reduce((a, b) => a + b, 0) / SH.K).toFixed(0)}. The target's is ${SH.canary.phi_target[0].toFixed(1)}. LiRA flags <span class="c-lime">${LIRA.flag[0]}/${TG.c}</span> in-canaries <code class="c-lime">${D.canary}</code> at 1% FPR; the loss threshold flags ${LOSS4.flag[0]}.`,
        cmd: "docker compose run --rm workbench python attack-membership/scripts/s04_shadows.py" },
      { chapter: "Impact", label: "Second opinion",
        caption: `adversarial-robustness-toolbox's MembershipInferenceBlackBox, trained on the same shadow outputs, scores AUC ${Object.entries(D.art).filter(([k]) => k.includes("black-box")).map(([, v]) => a3(v.auc)).join(" / ")}, close to this lab's ${a3(SH.results["shokri attack model"].auc)}. Its gap attack matches exactly.`,
        cmd: "docker compose run --rm workbench python attack-membership/scripts/s05_art_check.py" },
      { chapter: "Defense", label: "DP-SGD",
        caption: `Clip every example's gradient, add noise. At ε = ${dp8.eps.toFixed(0)} the attack drops to AUC <span class="c-ok">${a3(dp8.auc)}</span> and no canary is memorized, for <span class="c-bad">${(100 * (dp0.test - dp8.test)).toFixed(1)} points</span> of test accuracy. ε = 1 leaves a ${pc(D.dp[1].test)} model.`,
        cmd: "docker compose run --rm workbench python attack-membership/scripts/d1_dp_sgd.py" },
      { chapter: "Defense", label: "Labels only",
        caption: `Behind victim-api the public key gets labels, not scores: one query per record falls to the gap baseline (${a3(loGap.auc)}). Thirty noisy copies each bring it back to <span class="c-bad">${a3(LO[loAug].auc)}</span>. Output limits raise cost, not privacy.`,
        cmd: "docker compose run --rm workbench python attack-membership/scripts/d2_label_only.py" },
      { chapter: "Defense", label: "Regularize, re-audit",
        caption: `Early stopping is free here: AUC ${a3(RG[0].auc)} → <span class="c-ok">${a3(RG[1].auc)}</span> at ${pc(RG[1].test)} test accuracy. But the canaries still stand out (canary AUC ${RG[1].canary_auc.toFixed(2)}). No bound: audit the outliers.`,
        cmd: "docker compose run --rm workbench python attack-membership/scripts/d3_regularize.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Target model, candidate loss histogram and per-step audit panel"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) =>
        S("rect", { x, y, width: w, height: h, rx: 14, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow"), clipId = api.uid("rocclip");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 7, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("teal") }, mk);

      // ------------------------------------------------------------ top: model card → loss histogram
      const gModel = S("g", { class: "dimmable" }, svg);
      label(gModel, 40, 46, "TARGET");
      const modelBox = card(gModel, 40, 56, 250, 236, V("violet"));
      T(gModel, 60, 92, TG.variant, 17, { class: "mono", "font-weight": 800, fill: V("violet") });
      T(gModel, 60, 120, `CNN · ${TG.params.toLocaleString("en")} weights`, 14, { class: "mono" });
      T(gModel, 60, 150, `trained on ${TG.train} records`, 14, { fill: V("teal"), "font-weight": 600 });
      T(gModel, 60, 172, `= ${TG.n} members + ${TG.c} canaries`, 13, { fill: V("muted") });
      T(gModel, 60, 202, "100 epochs, no regularization", 13, { fill: V("muted") });
      T(gModel, 60, 238, `members      ${pc(TG.acc_members)}`, 14, { class: "mono", fill: V("teal") });
      T(gModel, 60, 262, `non-members  ${pc(TG.acc_nonmembers)}`, 14, { class: "mono" });

      const gFlow = S("g", { class: "dimmable" }, svg);
      S("path", { d: "M294 174 H 326", fill: "none", stroke: V("teal"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, gFlow);

      const gHist = S("g", { class: "dimmable" }, svg);
      label(gHist, 340, 46, "LOSS ON EACH OF THE 400 CANDIDATES");
      card(gHist, 336, 56, 584, 236);
      const HX0 = 380, HX1 = 890, HY0 = 76, HY1 = 250, nb = H.members.length;
      const e0 = H.edges[0], e1 = H.edges[nb];
      const hx = v => L(HX0, HX1, (v - e0) / (e1 - e0));
      const hmax = Math.max(...H.members, ...H.nonmembers);
      S("path", { d: `M${HX0} ${HY1} H${HX1}`, fill: "none", stroke: V("line"), "stroke-width": 1.5 }, gHist);
      H.edges.forEach((e, i) => { if (i % 2 === 0) T(gHist, hx(e), HY1 + 18, e === 0 ? "1" : `1e${e}`, 13, { "text-anchor": "middle", fill: V("muted") }); });
      T(gHist, HX1, HY1 + 36, "loss (log scale) →", 13, { "text-anchor": "end", fill: V("muted") });
      const bw = (HX1 - HX0) / nb;
      const bars = H.members.map((m, i) => ({
        m, nmm: H.nonmembers[i], x: HX0 + i * bw,
        rm: S("rect", { x: HX0 + i * bw + 3, width: bw / 2 - 3, rx: 3, fill: V("teal") }, gHist),
        rn: S("rect", { x: HX0 + i * bw + bw / 2, width: bw / 2 - 3, rx: 3, fill: "none", stroke: V("ink-2"), "stroke-width": 1.5 }, gHist),
      }));
      const keyM = S("g", {}, gHist);
      S("rect", { x: 720, y: 78, width: 14, height: 14, rx: 3, fill: V("teal") }, keyM);
      T(keyM, 740, 90, `members (${TG.n})`, 13);
      S("rect", { x: 720, y: 100, width: 14, height: 14, rx: 3, fill: "none", stroke: V("ink-2"), "stroke-width": 1.5 }, keyM);
      T(keyM, 740, 112, `non-members (${TG.n})`, 13);
      const thrG = S("g", {}, gHist);
      const thrX = hx(H.thr1_log10);
      S("rect", { x: HX0, y: HY0 - 4, width: thrX - HX0, height: HY1 - HY0 + 4, fill: V("bad"), "fill-opacity": .1 }, thrG);
      S("line", { x1: thrX, y1: HY0 - 8, x2: thrX, y2: HY1, stroke: V("bad"), "stroke-width": 3 }, thrG);
      T(thrG, thrX + 8, HY0 + 8, "threshold @ 1% FPR", 13, { fill: V("bad"), "font-weight": 700 });
      T(thrG, thrX + 8, HY0 + 26, `left of it: "member"`, 13, { fill: V("bad") });

      // ------------------------------------------------------------ bottom panels
      const panel = () => S("g", { opacity: 0 }, svg);
      const PY = 326;

      // 1: the audit split
      const gSplit = panel();
      const chips = [["MEMBERS", `${TG.n}`, "trained on", "teal"], ["NON-MEMBERS", `${TG.n}`, "same distribution, never seen", "ink"],
        ["CANARIES", `${TG.c} + ${TG.c}`, "wrong labels: in / held out", "lime"], ["ATTACKER POOL", `${TG.pool}`, "its own digits (shadows)", "warn"]];
      chips.forEach(([h, n, sub, c], i) => {
        const x = 40 + i * 222;
        card(gSplit, x, PY, 206, 176, c === "ink" ? V("line") : V(c));
        label(gSplit, x + 18, PY + 32, h);
        T(gSplit, x + 18, PY + 92, n, 40, { class: "mono", "font-weight": 800, fill: c === "ink" ? V("ink") : V(c) });
        T(gSplit, x + 18, PY + 130, sub, 13, { fill: V("muted") });
      });
      T(gSplit, 40 + 2 * 222 + 18, PY + 156, `${D.canary}-01..20`, 13, { class: "mono", fill: V("lime") });

      // 2: accuracy + medians
      const gGap = panel();
      card(gGap, 40, PY, 880, 176);
      label(gGap, 64, PY + 32, "SAME MODEL, TWO KINDS OF RECORD");
      [["", "accuracy", "median loss"], ["members", pc(TG.acc_members), H.median_members.toPrecision(2)],
        ["non-members", pc(TG.acc_nonmembers), H.median_nonmembers.toPrecision(2)]].forEach((r, i) => {
        const y = PY + 72 + i * 32, c = i === 1 ? V("teal") : i === 0 ? V("muted") : V("ink");
        r.forEach((s, j) => T(gGap, 64 + j * 200, y, s, i === 0 ? 13 : 16, { class: "mono", fill: c, "font-weight": i === 0 ? 700 : 600 }));
      });
      T(gGap, 640, PY + 80, "a 100% / 88.5% gap, but most", 14, { fill: V("muted") });
      T(gGap, 640, PY + 102, "losses overlap: the attacker", 14, { fill: V("muted") });
      T(gGap, 640, PY + 124, "must pick a threshold", 14, { fill: V("muted") });

      // 3-4: ROC (linear, then zoomed into the low-FPR corner)
      const gRoc = panel();
      card(gRoc, 40, PY, 470, 196);
      const RX0 = 96, RX1 = 470, RY0 = PY + 18, RY1 = PY + 160;
      const clip = S("clipPath", { id: clipId }, defs);
      S("rect", { x: RX0, y: RY0 - 4, width: RX1 - RX0 + 2, height: RY1 - RY0 + 8 }, clip);
      S("path", { d: `M${RX0} ${RY0} V${RY1} H${RX1}`, fill: "none", stroke: V("line"), "stroke-width": 1.5 }, gRoc);
      T(gRoc, RX0 - 8, RY0 + 5, "1", 13, { "text-anchor": "end", fill: V("muted") });
      T(gRoc, RX0 - 8, RY1 + 4, "0", 13, { "text-anchor": "end", fill: V("muted") });
      T(gRoc, 58, (RY0 + RY1) / 2, "TPR", 13, { fill: V("muted"), "font-weight": 700 });
      const xmaxT = T(gRoc, RX1, RY1 + 20, "", 13, { "text-anchor": "end", fill: V("muted") });
      T(gRoc, RX0, RY1 + 20, "0", 13, { "text-anchor": "middle", fill: V("muted") });
      T(gRoc, (RX0 + RX1) / 2, RY1 + 30, "false positive rate", 13, { "text-anchor": "middle", fill: V("muted") });
      const plot = S("g", { "clip-path": `url(#${clipId})` }, gRoc);
      const diag = S("polyline", { fill: "none", stroke: V("dim"), "stroke-width": 2, "stroke-dasharray": "5 5" }, plot);
      const rocLine = S("polyline", { fill: "none", stroke: V("warn"), "stroke-width": 3, "stroke-linejoin": "round" }, plot);
      const fpr1 = S("line", { y1: RY0, y2: RY1, stroke: V("bad"), "stroke-width": 1.5, "stroke-dasharray": "3 3" }, plot);
      const dot = S("circle", { r: 7, fill: V("bad") }, plot);
      const dotT = T(gRoc, 0, 0, `${k1}/${TG.n} members at 1% FPR`, 14, { fill: V("bad"), "font-weight": 700 });
      card(gRoc, 530, PY, 390, 196);
      label(gRoc, 554, PY + 30, "ATTACK");
      label(gRoc, 790, PY + 30, "AUC", { "text-anchor": "end" });
      label(gRoc, 896, PY + 30, "TPR@1%", { "text-anchor": "end" });
      [["random guess", 0.5, 0.01, "dim"], ["gap baseline", TH["gap (correct=member)"].auc, TH["gap (correct=member)"].tpr1, "ink-2"],
        ["confidence", TH["confidence (max p)"].auc, TH["confidence (max p)"].tpr1, "warn"], ["loss threshold", LOSS.auc, LOSS.tpr1, "warn"]]
        .forEach(([n, a, t, c], i) => [[n, 554, "start"], [a3(a), 790, "end"], [pc(t), 896, "end"]].forEach(([str, x, an]) =>
          T(gRoc, x, PY + 66 + i * 30, str, 14, { class: "mono", fill: V(c), "font-weight": i === 3 ? 800 : 500, "text-anchor": an })));
      T(gRoc, 554, PY + 184, `lowest measurable FPR: 1/${TG.n} = 0.5%`, 13, { fill: V("muted") });

      // 5: overfitting
      const gOv = panel();
      card(gOv, 40, PY, 880, 196);
      T(gOv, 64, PY + 28, `attack AUC (bars) and train − test gap, same ${TG.train} records, more epochs`, 13, { fill: V("muted") });
      const OB0 = PY + 150, OBH = 96;
      const ovBars = [...ovT, ovC].map((r, i) => {
        const x = 80 + i * 130, own = r.records === TG.train;
        const bar = S("rect", { x, y: OB0, width: 70, height: 0, rx: 6, fill: V(own ? (r.epochs === 100 ? "violet" : "dim") : "ok") }, gOv);
        const val = T(gOv, x + 35, OB0, a3(r.auc), 14, { "text-anchor": "middle", class: "mono", "font-weight": 700 });
        T(gOv, x + 35, OB0 + 20, own ? `${r.epochs} ep` : "cnn-clean", 13, { "text-anchor": "middle", fill: V("muted") });
        T(gOv, x + 35, OB0 + 38, own ? `gap ${(100 * (r.train - r.test)).toFixed(1)}` : `${r.records} rec.`, 13, { "text-anchor": "middle", class: "mono", fill: V("muted") });
        return { bar, val, h: (r.auc - 0.5) * OBH / 0.15 + 6 };
      });
      S("line", { x1: 80, x2: 880, y1: OB0, y2: OB0, stroke: V("line"), "stroke-width": 1.5 }, gOv);
      T(gOv, 880, OB0 - 6, "AUC 0.5", 13, { "text-anchor": "end", fill: V("muted") });

      // 6: shadows on one canary
      const gSh = panel();
      card(gSh, 40, PY, 600, 196, V("lime"));
      label(gSh, 64, PY + 30, `${SH.canary_ids[0]} · CONFIDENCE IN ITS (WRONG) LABEL`);
      const ps = SH.canary.phi_shadows[0], pt0 = SH.canary.phi_target[0];
      const lo = Math.min(...ps) - 3, hi = Math.max(pt0, ...ps) + 3;
      const sx = v => L(80, 600, (v - lo) / (hi - lo));
      const SY = PY + 120;
      S("line", { x1: 80, x2: 600, y1: SY, y2: SY, stroke: V("line"), "stroke-width": 2 }, gSh);
      const shDots = ps.map((v, i) => S("circle", { cx: sx(v), cy: SY - 14 - (i % 4) * 12, r: 6, fill: V("dim") }, gSh));
      T(gSh, sx(ps.reduce((a, b) => a + b, 0) / ps.length), SY + 24, `${SH.K} shadows (never saw it)`, 13, { "text-anchor": "middle", fill: V("muted") });
      const tDot = S("circle", { cx: sx(pt0), cy: SY - 26, r: 10, fill: V("lime") }, gSh);
      const tLab = T(gSh, sx(pt0), SY + 24, `target ${pt0.toFixed(1)}`, 14, { "text-anchor": "end", fill: V("lime"), "font-weight": 700 });
      T(gSh, 64, PY + 182, `z = ${SH.canary.lira[0].toFixed(1)} shadow std above its own baseline → member`, 13, { class: "mono", fill: V("lime") });
      card(gSh, 660, PY, 260, 196);
      label(gSh, 680, PY + 30, "FLAGGED AT 1% FPR");
      [["loss threshold", LOSS4], ["shokri model", SH.results["shokri attack model"]], ["LiRA offline", LIRA]].forEach(([n, r], i) => {
        T(gSh, 680, PY + 68 + i * 40, n, 14, { "font-weight": 600 });
        T(gSh, 680, PY + 86 + i * 40, `in ${r.flag[0]}/${TG.c} · out ${r.flag[1]}/${TG.c}`, 13, { class: "mono", fill: V(r.flag[0] > 5 ? "lime" : "muted") });
      });

      // 7: ART cross-check
      const gArt = panel();
      card(gArt, 40, PY, 880, 196);
      T(gArt, 64, PY + 28, "AUC on the same 400 candidates · ART vs this lab", 13, { fill: V("muted") });
      const artRows = [...Object.entries(D.art).map(([k, v]) => [k, v.auc, k.includes("gap") ? "ink-2" : "violet"]),
        ["this lab: shokri (Step 4)", SH.results["shokri attack model"].auc, "warn"]];
      const AX0 = 330, AX1 = 880, ax = v => L(AX0, AX1, (v - 0.4) / 0.3);
      const artBars = artRows.map(([n, v, c], i) => {
        const y = PY + 44 + i * 29;
        T(gArt, 64, y + 17, n, 14, { class: "mono" });
        const r = S("rect", { x: AX0, y: y + 4, height: 18, width: 0, rx: 4, fill: V(c) }, gArt);
        const t = T(gArt, AX0, y + 18, a3(v), 13, { class: "mono", "font-weight": 700 });
        return { r, t, w: ax(v) - AX0 };
      });
      S("line", { x1: ax(0.5), x2: ax(0.5), y1: PY + 40, y2: PY + 190, stroke: V("dim"), "stroke-dasharray": "4 4" }, gArt);
      T(gArt, ax(0.5), PY + 40, "0.5", 13, { "text-anchor": "middle", fill: V("muted") });

      // 8: DP-SGD table
      const gDp = panel();
      card(gDp, 40, PY, 880, 196, V("ok"));
      const dcol = [["", 64], ["ε", 250], ["σ", 340], ["test acc", 440], ["attack AUC", 570], ["canary AUC", 700], ["memorized", 820]];
      dcol.forEach(([h, x]) => T(gDp, x, PY + 30, h, 13, { fill: V("muted"), "font-weight": 700 }));
      const dpRows = D.dp.map((r, i) => {
        const y = PY + 64 + i * 34, g = S("g", {}, gDp);
        const good = r.eps !== null && r.eps >= 8, c = r.eps === null ? "bad" : good ? "ok" : "ink";
        T(g, 64, y, r.name, 15, { "font-weight": 700, fill: V(c) });
        [[r.eps === null ? "∞" : r.eps.toFixed(0), 250], [r.sigma.toFixed(2), 340], [pc(r.test), 440], [a3(r.auc), 570],
          [r.canary_auc.toFixed(2), 700], [`${r.canaries_memorized}/${TG.c}`, 820]]
          .forEach(([s, x], j) => T(g, x, y, s, 15, { class: "mono", fill: j === 2 && r.test < 0.5 ? V("bad") : V("ink") }));
        return g;
      });

      // 9: label-only
      const gLo = panel();
      card(gLo, 40, PY, 880, 196, V("ok"));
      T(gLo, 64, PY + 28, "victim-api: partner key reads probabilities, public key is capped at the label", 13, { fill: V("muted") });
      const loRows = Object.entries(LO).map(([k, v], i) => {
        const y = PY + 50 + i * 46, g = S("g", {}, gLo), c = i === 0 ? "warn" : i === 1 ? "ok" : "bad";
        T(g, 64, y + 22, k, 15, { class: "mono", "font-weight": 700, fill: V(c) });
        const r = S("rect", { x: 420, y: y + 6, height: 22, width: 0, rx: 5, fill: V(c), "fill-opacity": .8 }, g);
        T(g, 880, y + 22, `AUC ${a3(v.auc)} · ${v.queries.toLocaleString("en")} queries`, 14, { "text-anchor": "end", class: "mono" });
        return { g, r, w: (v.auc - 0.5) / 0.2 * 230 };
      });

      // 10: regularization
      const gRg = panel();
      card(gRg, 40, PY, 880, 196, V("ok"));
      [["", 64], ["test acc", 360], ["attack AUC", 500], ["canary AUC", 650], ["TPR@1%", 790]].forEach(([h, x]) => T(gRg, x, PY + 30, h, 13, { fill: V("muted"), "font-weight": 700 }));
      const rgRows = RG.map((r, i) => {
        const y = PY + 64 + i * 34, g = S("g", {}, gRg);
        T(g, 64, y, r.name, 15, { "font-weight": 700, fill: V(i === 0 ? "bad" : "ink") });
        [[pc(r.test), 360], [a3(r.auc), 500], [r.canary_auc.toFixed(2), 650], [pc(r.tpr1), 790]]
          .forEach(([s, x], j) => T(g, x, y, s, 15, { class: "mono", fill: j === 2 && r.canary_auc > 0.75 ? V("lime") : V("ink") }));
        return g;
      });

      // ------------------------------------------------------------ state
      const base = { hist: 0, thr: 0, split: 0, gap: 0, roc: 0, zoom: 0, ov: 0, sh: 0, art: 0, dp: 0, lo: 0, rg: 0 };
      const T_N = [null,
        { split: 1 },                                   // 1 System: the target
        { hist: 1, gap: 1 },                            // 2 System: a loss gap
        { hist: 1, thr: 1, roc: 1 },                    // 3 Attack: threshold attack
        { hist: 1, thr: 1, roc: 1, zoom: 1 },           // 4 Mechanism: low-FPR corner
        { hist: 1, ov: 1 },                             // 5 Mechanism: overfitting
        { hist: 1, sh: 1 },                             // 6 Impact: shadows find canaries
        { hist: 1, art: 1 },                            // 7 Impact: second opinion
        { hist: 1, dp: 1 },                             // 8 Defense: DP-SGD
        { hist: 1, lo: 1 },                             // 9 Defense: labels only
        { hist: 1, rg: 1 },                             // 10 Defense: regularize
      ];
      const target = n => ({ ...base, ...T_N[n] });
      const st = { ...base };

      function draw(s) {
        // histogram bars grow with s.hist
        bars.forEach((b, i) => {
          const k = seg(s.hist, i / nb * 0.5, 0.5 + i / nb * 0.5);
          const hm = (HY1 - HY0 - 10) * b.m / hmax * k, hn = (HY1 - HY0 - 10) * b.nmm / hmax * k;
          A(b.rm, { y: (HY1 - hm).toFixed(2), height: hm.toFixed(2) });
          A(b.rn, { y: (HY1 - hn).toFixed(2), height: hn.toFixed(2), opacity: hn > .5 ? 1 : 0 });
        });
        A(keyM, { opacity: seg(s.hist, 0, .3).toFixed(3) });
        A(thrG, { opacity: s.thr.toFixed(3) });

        A(gSplit, { opacity: s.split.toFixed(3) });
        A(gGap, { opacity: s.gap.toFixed(3) });

        // ROC with an x-zoom from [0, 1] to [0, 0.1]
        A(gRoc, { opacity: s.roc.toFixed(3) });
        const xmax = L(1, 0.1, s.zoom), rx = f => RX0 + (RX1 - RX0) * f / xmax, ry = t => L(RY1, RY0, t);
        const kk = seg(s.roc, .2, 1), n = Math.max(2, Math.round(kk * D.roc.length));
        A(rocLine, { points: D.roc.slice(0, n).map(([f, t]) => `${rx(f).toFixed(1)},${ry(t).toFixed(1)}`).join(" ") });
        A(diag, { points: `${rx(0)},${ry(0)} ${rx(1)},${ry(1)}` });
        xmaxT.textContent = xmax >= 0.995 ? "1" : xmax.toFixed(2);
        A(fpr1, { x1: rx(0.01).toFixed(1), x2: rx(0.01).toFixed(1), opacity: s.zoom.toFixed(3) });
        A(dot, { cx: rx(0.01).toFixed(1), cy: ry(LOSS.tpr1).toFixed(1), opacity: s.zoom.toFixed(3) });
        A(dotT, { x: (rx(0.01) + 14).toFixed(1), y: (ry(LOSS.tpr1) - 10).toFixed(1), opacity: seg(s.zoom, .5, 1).toFixed(3) });

        A(gOv, { opacity: Math.min(1, s.ov * 2).toFixed(3) });
        ovBars.forEach((b, i) => {
          const h = b.h * seg(s.ov, .1 + i * .1, .5 + i * .1);
          A(b.bar, { y: (OB0 - h).toFixed(2), height: h.toFixed(2) });
          A(b.val, { y: (OB0 - h - 8).toFixed(2), opacity: h > 2 ? 1 : 0 });
        });

        A(gSh, { opacity: Math.min(1, s.sh * 2).toFixed(3) });
        shDots.forEach((d, i) => A(d, { opacity: seg(s.sh, .1 + i * .02, .3 + i * .02).toFixed(3) }));
        const tp = seg(s.sh, .55, 1);
        A(tDot, { cx: L(sx(ps[0]), sx(pt0), tp).toFixed(1), opacity: seg(s.sh, .5, .6).toFixed(3) });
        A(tLab, { opacity: tp.toFixed(3) });

        A(gArt, { opacity: Math.min(1, s.art * 2).toFixed(3) });
        artBars.forEach((b, i) => {
          const w = b.w * seg(s.art, .1 + i * .1, .5 + i * .1);
          A(b.r, { width: Math.max(0, w).toFixed(2) });
          A(b.t, { x: (AX0 + w + 8).toFixed(2), opacity: w > 2 ? 1 : 0 });
        });

        A(gDp, { opacity: Math.min(1, s.dp * 2).toFixed(3) });
        dpRows.forEach((g, i) => A(g, { opacity: seg(s.dp, .1 + i * .2, .35 + i * .2).toFixed(3) }));
        A(gLo, { opacity: Math.min(1, s.lo * 2).toFixed(3) });
        loRows.forEach((r, i) => { const k = seg(s.lo, .1 + i * .25, .45 + i * .25); A(r.g, { opacity: k.toFixed(3) }); A(r.r, { width: Math.max(0, r.w * k).toFixed(2) }); });
        A(gRg, { opacity: Math.min(1, s.rg * 2).toFixed(3) });
        rgRows.forEach((g, i) => A(g, { opacity: seg(s.rg, .1 + i * .2, .35 + i * .2).toFixed(3) }));

        A(modelBox, { stroke: V(s.dp > .5 || s.rg > .5 ? "ok" : "violet") });
        // focus + context
        const hot = s.split > .5 || s.ov > .5 || s.dp > .5 || s.rg > .5 ? [gModel] : s.gap > .5 || s.roc > .5 ? [gHist] : s.sh > .5 || s.art > .5 || s.lo > .5 ? [] : null;
        [gModel, gHist, gFlow].forEach(g => g.classList.toggle("hot", !!hot && hot.includes(g)));
        el.classList.toggle("lx-focus", !!hot);
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          const ms = n === 3 || n === 4 || n === 6 ? 1000 : 700;
          return api.tween(ms, k => { if (g !== gen) return; X.lerpState(st, from, to, X.clamp(k)); draw(st); }, E.inOut);
        },
      };
    },
  });
})();
