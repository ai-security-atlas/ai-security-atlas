/* LAB-02 attack-visual-jailbreak: "Moving a VLM with invisible pixels" (spec §3.6 storyboard, 10 steps).
 * One persistent scene: the VLM pipeline across the top (image → vision encoder → pixel shuffle → context →
 * language model → answer) and a detail panel below that changes per step. The camera dives into one 16 px
 * patch in step 2. Every number, caption and image comes from window.LAB_DATA (data.js, exported from the
 * reference workbench run). Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg, L = X.lerp, E = X.ease;
  const D = window.LAB_DATA;
  const P = D.pgd, TGT = D.target;
  const pct = p => (p >= .01 ? (p * 100).toFixed(0) + "%" : p >= 1e-5 ? (p * 100).toPrecision(1) + "%" : "< 0.001%");
  const xferModels = Object.keys((D.robustness["pgd-eps8"] || {}).transfer || {});
  const hij = D.contrast ? `${D.contrast.hijack[0]}–${D.contrast.hijack[1]}/${D.contrast.trials}` : "most";

  X.define({
    id: "attack-visual-jailbreak",
    family: "family-evasion",
    title: 'Moving a VLM with <span class="outline">invisible</span> pixels',
    legend: [{ role: "teal", label: "Clean pixels / prompt" }, { role: "bad", label: "Perturbation / gradient" },
      { role: "violet", label: "Model" }, { role: "warn", label: "Model output" }, { role: "lime", label: "Canary" },
      { role: "ok", label: "Defense" }],
    steps: [
      { chapter: "System", label: "The pipeline",
        caption: `A vision-language model turns the <span class="c-teal">image</span> into tokens that share one context with your <span class="c-teal">prompt</span>. SmolVLM-256M answers: <span class="c-warn">“${D.clean_caption}”</span>`,
        cmd: "docker compose run --rm workbench python attack-visual-jailbreak/scripts/s01_fetch_model.py" },
      { chapter: "System", label: "Pixels are numbers",
        caption: `Zoom into one 16×16 patch. To the model the image is only <span class="c-teal">numbers in [0, 1]</span>: three per pixel, 512 × 512 × 3 of them. Nothing in them says “trusted”.` },
      { chapter: "System", label: "Patches become tokens",
        caption: `The encoder cuts the image into ${D.tokens.patches.toLocaleString("en")} patches of 16 px, and pixel shuffle packs them into <span class="c-violet">${D.tokens.image} image tokens</span>. They sit in the same context as the ${D.tokens.total - D.tokens.image} <span class="c-teal">text tokens</span>, with no trust label.` },
      { chapter: "Attack", label: "Not this attack",
        caption: `Readable text in an image (“reply with ${TGT}”) moves ${D.contrast ? D.contrast.model : "a model"} in ${hij} replies. That is a <span class="c-bad">different</span> Atlas mechanism, attack-multimodal-injection. This lab changes pixels nobody can read.`,
        cmd: "docker compose run --rm workbench python attack-visual-jailbreak/scripts/s02_contrast_typographic.py --trials 10" },
      { chapter: "Attack", label: "Score the target",
        caption: `The target is the harmless canary <code class="c-lime">${TGT}</code>. On the clean image its first token gets ${pct(D.logits.clean.p_first)}. White-box access (A03) gives the <span class="c-bad">gradient</span> of loss = −log p(target) with respect to every pixel.` },
      { chapter: "Mechanism", label: "Gradient to pixels",
        caption: `PGD sends the <span class="c-bad">gradient</span> back through the model to the pixels, nudges each one a small step α along its sign, then clips it back into the ε-box: no pixel may move more than ε = ${P.eps}/255.`,
        cmd: "docker compose run --rm workbench python attack-visual-jailbreak/scripts/s03_pgd.py --eps 8 --alpha 1 --out adv_eps8.png" },
      { chapter: "Impact", label: "Caption drifts",
        caption: `Every 10 steps the saved 8-bit image is captioned. The answer drifts through odd captions and lands on the canary <code class="c-lime">${TGT}</code> after ${P.steps} steps (reference run, ${Math.round(P.seconds / 60)} min on CPU). The shipped image used α = ${P.alpha}/255; the α = 1/255 command in step 6 takes about 120 steps.` },
      { chapter: "Impact", label: "Invisible delta",
        caption: `The change is spread over the whole image: L∞ ${P.linf}/255, mean ${P.mean_abs}/255, PSNR ${P.psnr} dB. Amplified, it shows the 16 px patch grid. The two images look the same, but ε alone does not prove that.`,
        cmd: "docker compose run --rm workbench python attack-visual-jailbreak/scripts/s04_show_delta.py assets/adv_eps8.png" },
      { chapter: "Defense", label: "Fragile...",
        caption: `Plain PGD fits one pipeline. JPEG q75 or a 1 px blur turns the caption <span class="c-ok">clean again</span>, and other models never output the canary. HF tiling and a mild resize do not stop it, so a transform is no guarantee.`,
        cmd: "docker compose run --rm workbench python attack-visual-jailbreak/scripts/s06_victim_check.py assets/adv_eps8.png --transforms" },
      { chapter: "Defense", label: "...until adaptive",
        caption: `An adaptive attacker optimizes through random resize, blur and noise (EOT, ε = 16/255): now blur and JPEG q95 <span class="c-bad">let the canary through</span>. Only JPEG q75, left out of the EOT set, holds. Evaluate defenses against adaptive attacks (eval-adaptive).`,
        cmd: "docker compose run --rm workbench python attack-visual-jailbreak/scripts/s06_victim_check.py assets/adv_eot16.png --transforms" },
    ],
    html: `<style>
      [data-explainer="attack-visual-jailbreak"] .vj-pix { image-rendering: pixelated; }
      [data-explainer="attack-visual-jailbreak"] canvas.vj-heat { position: absolute; image-rendering: pixelated; border-radius: 6px; }
    </style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="VLM pipeline: image, vision encoder, pixel shuffle, context, language model, answer"></svg>
    <canvas class="vj-heat" width="128" height="128" role="img" aria-label="Amplified perturbation heatmap" style="left:410px;top:338px;width:140px;height:140px"></canvas>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const heat = el.querySelector("canvas.vj-heat");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) =>
        S("rect", { x, y, width: w, height: h, rx: 14, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow"), badId = api.uid("arrowbad");
      for (const [id, c] of [[arrowId, "teal"], [badId, "bad"]]) {
        const mk = S("marker", { id, viewBox: "0 0 10 10", refX: 7, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse" }, defs);
        S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V(c) }, mk);
      }
      const flowPath = (p, d) => S("path", { d, fill: "none", stroke: V("teal"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})`, opacity: .8 }, p);

      // ---------------------------------------------------------------- top: the pipeline
      const IX = 40, IY = 66, IS = 192, PS = IS / 32;         // image at 192 px: one 16 px patch = 6 design px
      const gImg = S("g", { class: "dimmable" }, svg);
      label(gImg, 30, 44, "IMAGE");
      card(gImg, 30, 56, 212, 236);
      S("image", { href: D.img.clean, x: IX, y: IY, width: IS, height: IS, class: "vj-pix", preserveAspectRatio: "none" }, gImg);
      const imAdv = S("image", { href: D.img.adv, x: IX, y: IY, width: IS, height: IS, class: "vj-pix", preserveAspectRatio: "none", opacity: 0 }, gImg);
      const grid = S("g", { opacity: 0 }, gImg);
      for (let i = 1; i < 32; i++) {
        S("line", { x1: IX + i * PS, y1: IY, x2: IX + i * PS, y2: IY + IS, stroke: V("stage"), "stroke-width": i % 4 ? .5 : 1.2 }, grid);
        S("line", { x1: IX, y1: IY + i * PS, x2: IX + IS, y2: IY + i * PS, stroke: V("stage"), "stroke-width": i % 4 ? .5 : 1.2 }, grid);
      }
      const fname = T(gImg, IX, 280, "assets/clean.png", 14, { class: "mono" });
      const CR = D.crop16.row, CC = D.crop16.col, PX = IX + CC * PS, PY = IY + CR * PS;
      const patchBox = S("rect", { x: PX, y: PY, width: PS, height: PS, fill: "none", stroke: V("teal"), "stroke-width": 2, "vector-effect": "non-scaling-stroke", opacity: 0 }, gImg);

      // the zoomed patch: 16x16 cells, real colors, size encodes brightness
      const gCrop = S("g", { opacity: 0 }, svg);
      S("rect", { x: PX - 5, y: PY - 5, width: 32, height: 19, fill: V("stage"), opacity: .82 }, gCrop);   // dims the rest of the image
      S("rect", { x: PX + PS + 0.6, y: PY - 0.2, width: 14.2, height: 5.2, rx: .3, fill: V("panel"), stroke: V("line"), "stroke-width": .04 }, gCrop);
      S("rect", { x: PX, y: PY, width: PS, height: PS, fill: V("stage") }, gCrop);
      const cs = PS / 16;
      D.crop16.rgb.forEach(([r, g, b], i) => {
        const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255, w = cs * (0.45 + 0.5 * lum);
        S("rect", { x: PX + (i % 16) * cs + (cs - w) / 2, y: PY + Math.floor(i / 16) * cs + (cs - w) / 2, width: w, height: w,
          rx: w * .22, fill: `rgb(${r},${g},${b})` }, gCrop);
      });
      const zf = 0.42;                                         // world font size at the zoomed frame (~14 design px)
      const gZoomTxt = S("g", { opacity: 0 }, svg);
      const fmt = i => "(" + D.crop16.rgb[i].map(v => (v / 255).toFixed(2)).join(", ") + ")";
      const zt = (y, s, o = {}) => T(gZoomTxt, PX + PS + 0.9, y, s, zf, o);
      zt(PY + 0.55, "ONE 16 × 16 PATCH", { fill: V("muted"), "font-weight": 700, "letter-spacing": .06 });
      zt(PY + 1.35, "256 pixels × 3 channels = 768 numbers", { fill: V("teal") });
      zt(PY + 2.45, `top-left pixel  ${fmt(0)}`, { class: "mono" });
      zt(PY + 3.15, `bottom-right    ${fmt(255)}`, { class: "mono" });
      zt(PY + 4.25, "the model sees only these numbers", { fill: V("muted") });

      const gEnc = S("g", { class: "dimmable" }, svg);
      label(gEnc, 272, 44, "ENCODER");
      for (let i = 3; i >= 0; i--) S("rect", { x: 272 + i * 5, y: 70 + i * 7, width: 86, height: 196, rx: 12, fill: V("violet"), "fill-opacity": .08 + i * .03, stroke: V("violet"), "stroke-width": 1.5 }, gEnc);
      T(gEnc, 315, 156, "vision", 15, { "text-anchor": "middle", "font-weight": 600 });
      T(gEnc, 315, 176, "encoder", 15, { "text-anchor": "middle", "font-weight": 600 });
      T(gEnc, 315, 204, "16 px", 13, { "text-anchor": "middle", fill: V("muted") });
      T(gEnc, 315, 220, "patches", 13, { "text-anchor": "middle", fill: V("muted") });

      const gProj = S("g", { class: "dimmable" }, svg);
      S("rect", { x: 384, y: 128, width: 68, height: 92, rx: 12, fill: V("violet"), "fill-opacity": .14, stroke: V("violet"), "stroke-width": 1.5 }, gProj);
      T(gProj, 418, 166, "pixel", 13, { "text-anchor": "middle", "font-weight": 600 });
      T(gProj, 418, 184, "shuffle", 13, { "text-anchor": "middle", "font-weight": 600 });

      // context: the real token sequence, 8 per row; violet = image tokens, teal = text tokens
      const gCtx = S("g", { class: "dimmable" }, svg);
      label(gCtx, 466, 44, "CONTEXT");
      card(gCtx, 466, 56, 74, 236);
      const kinds = D.tokens.kinds, rows = Math.ceil(kinds.length / 8), CY0 = 174 - rows * 7.5 / 2;
      const toks = [...kinds].map((k, i) => ({ k, x: 474 + (i % 8) * 7.5, y: CY0 + Math.floor(i / 8) * 7.5 }));
      let imgIdx = 0;
      toks.forEach(t => {
        t.el = S("rect", { x: t.x, y: t.y, width: 6, height: 6, rx: 1.5, fill: V(t.k === "i" ? "violet" : "teal") }, gCtx);
        if (t.k === "i") {                                     // source: its 4x4-patch group on the image (pixel shuffle)
          const j = imgIdx++, gs = IS / 8;
          t.j = j;
          t.src = { x: IX + (j % 8) * gs, y: IY + Math.floor(j / 8) * gs, w: gs };
        }
      });

      const gLLM = S("g", { class: "dimmable" }, svg);
      label(gLLM, 560, 44, "LANGUAGE MODEL");
      card(gLLM, 560, 56, 176, 236, V("violet"));
      for (let i = 0; i < 7; i++) S("rect", { x: 576, y: 104 + i * 24, width: 144, height: 16, rx: 6, fill: V("violet"), "fill-opacity": .12 + .04 * i }, gLLM);
      T(gLLM, 648, 86, "decoder layers", 13, { "text-anchor": "middle", fill: V("muted") });

      const gOut = S("g", { class: "dimmable" }, svg);
      label(gOut, 756, 44, "ANSWER");
      const outBox = card(gOut, 756, 56, 180, 236);
      const outLines = [0, 1, 2, 3, 4].map(i => T(gOut, 772, 104 + i * 24, "", 15, { class: "mono", "font-weight": 600 }));
      const outNote = T(gOut, 772, 270, "", 13, { fill: V("muted") });

      const gFlow = S("g", { class: "dimmable" }, svg);
      flowPath(gFlow, "M244 174 H266");
      flowPath(gFlow, "M364 174 H380");
      flowPath(gFlow, "M454 174 H462");
      flowPath(gFlow, "M542 174 H556");
      flowPath(gFlow, "M738 174 H752");
      const pkt = S("circle", { r: 7, cy: 174, fill: V("teal"), opacity: 0 }, svg);

      // backward gradient ribbon (step 6)
      const grad = S("path", { d: "M846 294 C 846 312, 826 310, 800 310 H 180 C 150 310, 136 308, 136 298",
        fill: "none", stroke: V("bad"), "stroke-width": 5, "stroke-linecap": "round", pathLength: 100, "stroke-dasharray": "100 100", "stroke-dashoffset": 100, "marker-end": `url(#${badId})` }, svg);

      const gradLbl = T(svg, 470, 304, "gradient flows back to the pixels", 13, { "text-anchor": "middle", fill: V("bad"), "font-weight": 600, opacity: 0 });

      // ---------------------------------------------------------------- bottom panels (one per step)
      const panel = () => S("g", { opacity: 0 }, svg);
      // step 1: the prompt
      const gPrompt = panel();
      S("rect", { x: 300, y: 356, width: 440, height: 44, rx: 12, fill: V("teal"), "fill-opacity": .1, stroke: V("teal"), "stroke-width": 1.5 }, gPrompt);
      T(gPrompt, 318, 384, `user: “${D.prompt}”`, 15, { class: "mono", fill: V("teal") });
      S("path", { d: "M503 352 V300", fill: "none", stroke: V("teal"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, gPrompt);
      T(gPrompt, 300, 432, "the same pixels and prompt every time · greedy decoding · CPU in the workbench", 13, { fill: V("muted") });

      // step 3: patch arithmetic
      const gTok = panel();
      const chip = (p, x, w, top, bot, role) => {
        S("rect", { x, y: 360, width: w, height: 70, rx: 12, fill: V("panel"), stroke: V(role), "stroke-width": 1.5 }, p);
        T(p, x + w / 2, 390, top, 17, { "text-anchor": "middle", "font-weight": 700, fill: V(role) });
        T(p, x + w / 2, 414, bot, 13, { "text-anchor": "middle", fill: V("muted") });
      };
      chip(gTok, 60, 170, "512 × 512 px", "the lab app: one tile", "teal");
      chip(gTok, 270, 190, `${D.tokens.patches.toLocaleString("en")} patches`, "32 × 32, 16 px each", "violet");
      chip(gTok, 500, 190, `${D.tokens.image} image tokens`, "pixel shuffle: 4 × 4 → 1", "violet");
      chip(gTok, 730, 170, `+ ${D.tokens.total - D.tokens.image} text`, "one context, no label", "teal");
      for (const x of [234, 464, 694]) S("path", { d: `M${x} 395 H${x + 30}`, stroke: V("dim"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, gTok);

      // step 4: the contrast (typographic injection is another node)
      const gCon = panel();
      card(gCon, 40, 330, 560, 190, V("bad"), { "stroke-dasharray": "6 5" });
      S("image", { href: D.img.banner, x: 60, y: 352, width: 192, height: 128, preserveAspectRatio: "none" }, gCon);
      T(gCon, 60, 502, "assets/banner.png", 13, { class: "mono", fill: V("muted") });
      S("path", { d: "M262 416 H316", stroke: V("dim"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, gCon);
      S("rect", { x: 322, y: 392, width: 120, height: 48, rx: 12, fill: V("violet"), "fill-opacity": .14, stroke: V("violet"), "stroke-width": 1.5 }, gCon);
      T(gCon, 382, 421, D.contrast ? D.contrast.model : "VLM", 14, { "text-anchor": "middle", class: "mono", "font-weight": 600 });
      S("path", { d: "M446 416 H470", stroke: V("dim"), "stroke-width": 2.5, "marker-end": `url(#${arrowId})` }, gCon);
      T(gCon, 476, 410, TGT, 17, { class: "mono", "font-weight": 800, fill: V("lime") });
      T(gCon, 476, 434, `hijack ${hij}`, 13, { fill: V("muted") });
      const stamp = S("g", { transform: "rotate(-5 410 358)" }, gCon);
      S("rect", { x: 280, y: 342, width: 260, height: 34, rx: 6, fill: V("panel"), stroke: V("bad"), "stroke-width": 2.5 }, stamp);
      T(stamp, 410, 365, "attack-multimodal-injection", 15, { "text-anchor": "middle", class: "mono", "font-weight": 800, fill: V("bad") });
      S("path", { d: "M612 425 H660", stroke: V("muted"), "stroke-width": 2, "stroke-dasharray": "5 5" }, gCon);
      card(gCon, 668, 330, 260, 190);
      S("image", { href: D.img.clean, x: 688, y: 352, width: 96, height: 96, class: "vj-pix", preserveAspectRatio: "none" }, gCon);
      T(gCon, 798, 376, "this lab:", 14, { fill: V("muted") });
      T(gCon, 798, 400, "no readable", 15, { "font-weight": 700 });
      T(gCon, 798, 420, "text at all", 15, { "font-weight": 700 });
      T(gCon, 688, 478, `only pixel changes ≤ ${P.eps}/255`, 14, { fill: V("bad"), "font-weight": 600 });

      // step 5: next-token bars and the loss
      const gBars = panel();
      label(gBars, 60, 340, "FIRST ANSWER TOKEN · CLEAN IMAGE");
      const top = D.logits.clean.top, BW = 300;
      const bars = top.map(([tok, p], i) => {
        const y = 356 + i * 26;
        T(gBars, 60, y + 15, JSON.stringify(tok), 14, { class: "mono" });
        S("rect", { x: 150, y: y + 3, width: BW, height: 16, rx: 5, fill: V("line"), opacity: .5 }, gBars);
        const r = S("rect", { x: 150, y: y + 3, width: 0, height: 16, rx: 5, fill: V("warn") }, gBars);
        T(gBars, 460, y + 15, pct(p), 13, { fill: V("muted") });
        return { r, p };
      });
      const yC = 356 + top.length * 26 + 4;
      T(gBars, 60, yC + 15, JSON.stringify(D.target_tokens[0]), 14, { class: "mono", fill: V("lime"), "font-weight": 700 });
      S("rect", { x: 150, y: yC + 3, width: BW, height: 16, rx: 5, fill: V("line"), opacity: .5 }, gBars);
      const barC = S("rect", { x: 150, y: yC + 3, width: 0, height: 16, rx: 5, fill: V("lime") }, gBars);
      T(gBars, 460, yC + 15, pct(D.logits.clean.p_first), 13, { fill: V("lime") });
      card(gBars, 560, 340, 370, 172, V("bad"));
      T(gBars, 580, 372, "loss = −log p(", 16, { class: "mono" });
      T(gBars, 580, 398, `"${D.target_tokens.join("")}"`, 15, { class: "mono", fill: V("lime"), "font-weight": 600 });
      T(gBars, 580, 422, `      | image, prompt) = ${D.logits.clean.loss.toFixed(1)}`, 15, { class: "mono" });
      T(gBars, 580, 456, "white-box (A03): read weights, compute", 13, { fill: V("muted") });
      T(gBars, 580, 476, "∂loss/∂pixel for all 786,432 numbers", 13, { fill: V("bad"), "font-weight": 600 });

      // step 6: sign step on the patch, the update rule and the L-inf box
      const gGrad = panel();
      label(gGrad, 50, 340, "SIGN OF THE STEP");
      const PC = 9, PX0 = 50, PY0 = 352;
      D.crop16.rgb.forEach(([r, g, b], i) => {
        const x = PX0 + (i % 16) * PC, y = PY0 + Math.floor(i / 16) * PC, dd = D.crop16.delta[i];
        S("rect", { x, y, width: PC - 1, height: PC - 1, rx: 1.5, fill: `rgb(${r},${g},${b})` }, gGrad);
        const s = dd[0] + dd[1] + dd[2];
        if (s) S("path", { d: s > 0 ? `M${x + 1.5} ${y + 6.5} L${x + 4} ${y + 1.5} L${x + 6.5} ${y + 6.5} Z` : `M${x + 1.5} ${y + 1.5} L${x + 4} ${y + 6.5} L${x + 6.5} ${y + 1.5} Z`,
          fill: V("bad"), opacity: .9 }, gGrad);
      });
      T(gGrad, 50, 516, "▲ up  ▼ down", 13, { fill: V("muted") });
      card(gGrad, 220, 340, 450, 172);
      T(gGrad, 240, 384, "x ← clip( x − α·sign(∇ₓ loss),", 17, { class: "mono", "font-weight": 600 });
      T(gGrad, 240, 412, "          x₀ − ε, x₀ + ε )", 17, { class: "mono", "font-weight": 600 });
      T(gGrad, 240, 448, `shipped image: α = ${P.alpha}/255, ε = ${P.eps}/255`, 14, { class: "mono", fill: V("bad") });
      T(gGrad, 240, 476, "descend the loss: make the canary more likely", 13, { fill: V("muted") });
      T(gGrad, 240, 496, "then round to 8 bits, as the saved PNG will be", 13, { fill: V("muted") });
      // L-inf box: two pixel values as axes; the point walks by sign steps and is clipped to the box
      const BX = 810, BY = 440, BH = 58;
      card(gGrad, 690, 340, 240, 172);
      S("rect", { x: BX - BH, y: BY - BH, width: 2 * BH, height: 2 * BH, fill: V("bad"), "fill-opacity": .06, stroke: V("bad"), "stroke-width": 1.5, "stroke-dasharray": "5 4" }, gGrad);
      S("circle", { cx: BX, cy: BY, r: 5, fill: V("teal") }, gGrad);
      T(gGrad, BX + 8, BY + 18, "x₀", 14, { fill: V("teal") });
      T(gGrad, 702, 358, "L∞ ball: |x − x₀| ≤ ε", 13, { fill: V("muted") });
      const walk = [[0, 0], [1, -1], [2, -2], [3, -1], [4, -2], [5, -3], [5, -4], [5, -5]].map(([a, b]) => [BX + a * 19, BY + b * 19]);
      const c1 = v => Math.max(-1, Math.min(1, v)), clip = ([x, y]) => [c1((x - BX) / BH) * BH + BX, c1((y - BY) / BH) * BH + BY];
      const walkPath = S("path", { fill: "none", stroke: V("bad"), "stroke-width": 2.5, "stroke-linejoin": "round" }, gGrad);
      const walkDot = S("circle", { r: 5.5, fill: V("bad") }, gGrad);

      // step 7: loss curve over the logged checks, and p(target)
      const gIter = panel();
      const log = [[0, D.logits.clean.loss, D.clean_caption], ...P.log];
      const lmax = Math.log10(Math.max(...log.map(r => r[1]))), lmin = Math.log10(Math.min(...log.map(r => r[1]))), CX0 = 90, CX1 = 640, CY0b = 352, CY1 = 492;
      const cx = s => L(CX0, CX1, s / log[log.length - 1][0]), cy = l => L(CY1, CY0b, (Math.log10(l) - lmin) / (lmax - lmin));
      label(gIter, 60, 340, `LOSS PER CHECK (LOG SCALE) · ε ${P.eps}/255, α ${P.alpha}/255`);
      S("path", { d: `M${CX0} ${CY0b} V${CY1} H${CX1}`, fill: "none", stroke: V("line"), "stroke-width": 1.5 }, gIter);
      T(gIter, 82, CY0b + 6, Math.pow(10, lmax).toFixed(1), 13, { "text-anchor": "end", fill: V("muted") });
      T(gIter, 82, CY1 + 4, Math.pow(10, lmin).toFixed(2), 13, { "text-anchor": "end", fill: V("muted") });
      T(gIter, CX0, CY1 + 22, "step 0", 13, { fill: V("muted") });
      T(gIter, CX1, CY1 + 22, `step ${log[log.length - 1][0]}`, 13, { "text-anchor": "end", fill: V("muted") });
      const curve = S("polyline", { fill: "none", stroke: V("bad"), "stroke-width": 2.5, "stroke-linejoin": "round" }, gIter);
      const curDot = S("circle", { r: 6, fill: V("bad") }, gIter);
      const iterTxt = T(gIter, CX1, CY0b + 14, "", 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
      card(gIter, 680, 340, 250, 172);
      T(gIter, 700, 370, "p(target) = e^(−loss)", 14, { class: "mono" });
      S("rect", { x: 700, y: 388, width: 210, height: 22, rx: 6, fill: V("line"), opacity: .5 }, gIter);
      const pBar = S("rect", { x: 700, y: 388, width: 0, height: 22, rx: 6, fill: V("lime") }, gIter);
      const pTxt = T(gIter, 700, 440, "", 22, { class: "mono", "font-weight": 800, fill: V("lime") });
      T(gIter, 700, 470, `${P.steps} steps · ${Math.round(P.seconds)} s on CPU`, 13, { fill: V("muted") });
      T(gIter, 700, 490, `stop: caption = canary, loss < ${P.stop_loss}`, 13, { fill: V("muted") });

      // step 8: clean · amplified delta (canvas) · adversarial
      const gTri = panel();
      S("image", { href: D.img.clean, x: 150, y: 338, width: 140, height: 140, class: "vj-pix", preserveAspectRatio: "none" }, gTri);
      S("image", { href: D.img.adv, x: 670, y: 338, width: 140, height: 140, class: "vj-pix", preserveAspectRatio: "none" }, gTri);
      S("rect", { x: 410, y: 338, width: 140, height: 140, rx: 6, fill: "none", stroke: V("bad"), "stroke-width": 1.5 }, gTri);
      T(gTri, 220, 500, "clean", 14, { "text-anchor": "middle", "font-weight": 600 });
      T(gTri, 480, 500, "|δ| amplified", 14, { "text-anchor": "middle", "font-weight": 600, fill: V("bad") });
      T(gTri, 740, 500, "adversarial", 14, { "text-anchor": "middle", "font-weight": 600 });
      T(gTri, 350, 412, "+", 30, { "text-anchor": "middle", fill: V("muted") });
      T(gTri, 610, 412, "=", 30, { "text-anchor": "middle", fill: V("muted") });
      T(gTri, 480, 524, `L∞ ${P.linf}/255 · mean ${P.mean_abs}/255 · PSNR ${P.psnr} dB`, 13, { "text-anchor": "middle", class: "mono", fill: V("muted") });
      function paintHeat() {
        const ctx = heat.getContext("2d"), im = ctx.createImageData(128, 128);
        const c = api.color("bad").trim(), dec = c.startsWith("rgb") ? c.match(/\d+/g) : null, hx = dec ? null : c.match(/[0-9a-f]{2}/gi);
        const [r, g, b] = dec ? dec.slice(0, 3).map(Number) : hx ? hx.slice(0, 3).map(h => parseInt(h, 16)) : [220, 60, 90];
        for (let i = 0; i < 128 * 128; i++) {
          const v = +D.delta128[i] / 9;
          im.data.set([r, g, b, Math.round(255 * v)], i * 4);
        }
        ctx.putImageData(im, 0, 0);
      }

      // steps 9-10: robustness table
      const gRob = panel();
      const cols = [["lab_app", "lab app"], ["hf_default", "HF default"], ["jpeg95", "JPEG 95"], ["jpeg75", "JPEG 75"], ["blur", "blur 1 px"], ["resize", "resize"]]
        .concat(xferModels.map(m => ["x:" + m, m.split(":")[0]]));
      const cw = Math.min(96, 720 / cols.length), RX = 200;
      cols.forEach(([, name], j) => T(gRob, RX + j * cw + cw / 2, 344, name, 13, { "text-anchor": "middle", fill: V("muted"), "font-weight": 600 }));
      T(gRob, RX + 6 * cw + (cols.length - 6) * cw / 2, 326, xferModels.length ? "transfer (other models)" : "", 13, { "text-anchor": "middle", fill: V("muted") });
      const cellOf = (row, key) => {
        const r = D.robustness[row] || {};
        if (!key.startsWith("x:")) return r[key] || "n/r";
        const v = (r.transfer || {})[key.slice(2)];
        return v ? (v.startsWith("0/") ? "0" : "1") + "|" + v : "n/r";
      };
      const robRows = [["pgd-eps8", `plain PGD ε ${P.eps}`], ["eot-eps16", "EOT ε 16"]].map(([row, name], i) => {
        const y = 356 + i * 64, g = S("g", {}, gRob);
        T(g, 60, y + 34, name, 15, { "font-weight": 700 });
        T(g, 60, y + 52, row === "pgd-eps8" ? "adv_eps8.png" : "adv_eot16.png", 13, { class: "mono", fill: V("muted") });
        const cells = cols.map(([key], j) => {
          const raw = cellOf(row, key), [v, shown] = raw.includes("|") ? raw.split("|") : [raw, raw];
          const role = v === "1" ? "bad" : v === "~" ? "warn" : v === "0" ? "ok" : "muted";
          const word = v === "1" ? "CANARY" : v === "~" ? "partial" : v === "0" ? "clean" : "n/r";
          const cg = S("g", {}, g);
          S("rect", { x: RX + j * cw + 4, y: y + 10, width: cw - 8, height: 46, rx: 9, fill: V(role), "fill-opacity": .16, stroke: V(role), "stroke-width": 1.5 }, cg);
          T(cg, RX + j * cw + cw / 2, y + 32, word, 13, { "text-anchor": "middle", fill: V(role), "font-weight": 700 });
          if (key.startsWith("x:")) T(cg, RX + j * cw + cw / 2, y + 49, shown + " hijack", 13, { "text-anchor": "middle", fill: V("muted") });
          return cg;
        });
        return { g, cells };
      });
      const verdict = S("g", {}, gRob);
      S("rect", { x: 330, y: 494, width: 300, height: 34, rx: 17, fill: V("bad"), "fill-opacity": .14, stroke: V("bad"), "stroke-width": 1.5 }, verdict);
      T(verdict, 480, 517, "input transforms ≠ robustness", 15, { "text-anchor": "middle", "font-weight": 700, fill: V("bad") });

      // ---------------------------------------------------------------- state
      const base = { zoom: 0, cap: 1, flow: 0, prompt: 0, crop: 0, grid: 0, fly: 0, tokp: 0, contrast: 0, bars: 0, grad: 0, iter: 0, adv: 0, tri: 0, rob: 0, eot: 0 };
      const T_N = [null,
        { flow: 1, prompt: 1 },                          // 1 System: pipeline + prompt
        { zoom: 1, crop: 1 },                            // 2 System: dive into one patch
        { grid: 1, fly: 1, tokp: 1 },                    // 3 System: patches -> tokens
        { fly: 1, contrast: 1 },                         // 4 Attack: contrast panel
        { fly: 1, bars: 1 },                             // 5 Attack: score the target
        { fly: 1, grad: 1 },                             // 6 Mechanism: gradient + projection
        { fly: 1, iter: 1, adv: 1 },                     // 7 Impact: caption drifts to the canary
        { fly: 1, iter: 1, adv: 1, tri: 1 },             // 8 Impact: invisible delta
        { fly: 1, iter: 1, adv: 1, rob: 1 },             // 9 Defense: transforms + transfer
        { fly: 1, iter: 1, adv: 1, rob: 1, eot: 1 },     // 10 Defense: adaptive attacker
      ];
      const target = n => ({ ...base, ...T_N[n] });
      const st = { ...base, cap: 0 };
      const W0 = 960, W1 = 28, C0 = [480, 270], C1 = [PX + PS / 2 + 8, PY + PS / 2 + 1.5];

      function wrap(s, n = 17) {
        const out = [];
        let line = "";
        for (const w of s.split(" ")) {
          if ((line + " " + w).trim().length > n && line) { out.push(line); line = w; } else line = (line + " " + w).trim();
        }
        if (line) out.push(line);
        return out.slice(0, 5);
      }

      function draw(s) {
        // camera: exponential zoom toward the patch, center follows the zoom
        const w = W0 * Math.pow(W1 / W0, s.zoom), k = (W0 - w) / (W0 - W1);
        const c = [L(C0[0], C1[0], k), L(C0[1], C1[1], k)];
        svg.setAttribute("viewBox", [c[0] - w / 2, c[1] - w * 9 / 32, w, w * 9 / 16].map(v => v.toFixed(3)).join(" "));
        A(gCrop, { opacity: seg(s.crop, .3, 1).toFixed(3) });
        A(gZoomTxt, { opacity: seg(s.crop * s.zoom, .7, 1).toFixed(3) });
        A(patchBox, { opacity: Math.max(seg(s.zoom, 0, .3) * (1 - seg(s.zoom, .8, 1)), s.grad).toFixed(3) });
        A(grid, { opacity: (s.grid * (1 - s.zoom) * .9).toFixed(3) });
        A(imAdv, { opacity: s.adv.toFixed(3) });
        fname.textContent = s.adv > .5 ? "assets/adv_eps8.png" : "assets/clean.png";
        A(fname, { fill: s.adv > .5 ? V("bad") : V("ink") });

        // tokens: image tokens fly from their 4x4-patch group to the context during step 3
        const f = s.fly > 0 && s.fly < 1 ? s.fly : 0;
        toks.forEach(t => {
          if (t.k !== "i") return;
          const d0 = t.j / D.tokens.image * .5, kk = f ? E.inOut(seg(f, d0, d0 + .5)) : 1, sz = f ? L(t.src.w, 6, kk) : 6;
          A(t.el, { x: (f ? L(t.src.x, t.x, kk) : t.x).toFixed(2), y: (f ? L(t.src.y, t.y, kk) : t.y).toFixed(2), width: sz.toFixed(2), height: sz.toFixed(2),
            "fill-opacity": f ? L(.55, 1, kk).toFixed(3) : 1 });
        });

        // answer: clean caption types in; from step 7 the logged PGD captions replace it
        let text, role;
        if (s.iter > 0) {
          const r = log[Math.min(log.length - 1, Math.floor(s.iter * (log.length - 1) + 1e-6))];
          text = r[2]; role = r[2].toUpperCase().replace(/[^A-Z0-9-]/g, "") === TGT ? "lime" : "warn";
          outNote.textContent = `PGD step ${r[0]}`;
        } else {
          text = D.clean_caption.slice(0, Math.round(D.clean_caption.length * s.cap)); role = "warn";
          outNote.textContent = s.cap >= 1 ? "clean caption" : "";
        }
        const lines = wrap(text);
        outLines.forEach((t, i) => { t.textContent = lines[i] || ""; A(t, { fill: V(role), "font-size": role === "lime" ? 19 : 15 }); });
        A(outBox, { stroke: V(role === "lime" ? "lime" : "line") });
        A(pkt, { cx: L(150, 846, s.flow).toFixed(2), opacity: s.flow > 0 && s.flow < 1 ? 1 : 0 });

        A(gPrompt, { opacity: s.prompt.toFixed(3) });
        A(gTok, { opacity: s.tokp.toFixed(3) });
        A(gCon, { opacity: s.contrast.toFixed(3) });
        A(gBars, { opacity: seg(s.bars, 0, .4).toFixed(3) });
        bars.forEach(b => A(b.r, { width: (BW * b.p * E.out(seg(s.bars, .2, 1))).toFixed(2) }));
        A(barC, { width: Math.max(1.5, BW * D.logits.clean.p_first * s.bars).toFixed(2) });

        A(grad, { "stroke-dashoffset": (100 * (1 - seg(s.grad, 0, .6))).toFixed(2), opacity: s.grad > 0 ? 1 : 0 });
        A(gGrad, { opacity: seg(s.grad, .2, .6).toFixed(3) });
        A(gradLbl, { opacity: seg(s.grad, .4, .7).toFixed(3) });
        const wk = seg(s.grad, .4, 1) * (walk.length - 1), pts = [];
        for (let i = 0; i <= Math.floor(wk); i++) pts.push(clip(walk[i]));
        const fr = wk - Math.floor(wk), last = Math.min(walk.length - 1, Math.floor(wk) + 1);
        const cur = clip([L(walk[Math.floor(wk)][0], walk[last][0], fr), L(walk[Math.floor(wk)][1], walk[last][1], fr)]);
        pts.push(cur);
        A(walkPath, { d: "M" + pts.map(p => p.map(v => v.toFixed(1)).join(" ")).join(" L") });
        A(walkDot, { cx: cur[0].toFixed(1), cy: cur[1].toFixed(1) });

        A(gIter, { opacity: s.iter > 0 && s.tri < .5 && s.rob < .5 ? Math.min(1, s.iter * 3) * (1 - s.tri) * (1 - s.rob) : 0 });
        const li = s.iter * (log.length - 1), n0 = Math.floor(li), fr2 = li - n0, n1 = Math.min(log.length - 1, n0 + 1);
        const pts2 = log.slice(0, n0 + 1).map(r => [cx(r[0]), cy(r[1])]);
        const head = [L(cx(log[n0][0]), cx(log[n1][0]), fr2), L(cy(log[n0][1]), cy(log[n1][1]), fr2)];  // straight segment in log space
        pts2.push(head);
        A(curve, { points: pts2.map(p => p.map(v => v.toFixed(1)).join(",")).join(" ") });
        A(curDot, { cx: head[0].toFixed(1), cy: head[1].toFixed(1) });
        const lossNow = Math.exp(L(Math.log(log[n0][1]), Math.log(log[n1][1]), fr2)), pNow = Math.exp(-lossNow);
        iterTxt.textContent = `step ${Math.round(L(log[n0][0], log[n1][0], fr2))} · loss ${lossNow.toFixed(2)}`;
        A(pBar, { width: (210 * pNow).toFixed(2) });
        pTxt.textContent = (pNow * 100).toFixed(pNow < .1 ? 2 : 0) + "%";

        A(gTri, { opacity: s.tri.toFixed(3) });
        heat.style.opacity = s.tri.toFixed(3);
        heat.style.visibility = s.tri > 0 ? "visible" : "hidden";
        if (s.tri > 0) paintHeat();
        heat.setAttribute("aria-label", `Perturbation magnitude, amplified: L-infinity ${P.linf}/255, PSNR ${P.psnr} dB, spread over every 16 px patch`);

        A(gRob, { opacity: Math.min(1, s.rob * 2).toFixed(3) });
        robRows[0].cells.forEach((cg, j) => A(cg, { opacity: seg(s.rob, .2 + j * .06, .45 + j * .06).toFixed(3) }));
        A(robRows[1].g, { opacity: seg(s.eot, 0, .3).toFixed(3) });
        robRows[1].cells.forEach((cg, j) => A(cg, { opacity: seg(s.eot, .15 + j * .06, .4 + j * .06).toFixed(3) }));
        A(verdict, { opacity: seg(s.eot, .7, 1).toFixed(3) });

        // focus + context
        const hot = s.zoom > .5 ? [gImg] : s.tokp > .5 ? [gImg, gEnc, gProj, gCtx, gFlow] : s.bars > .5 ? [gLLM, gOut] :
          s.tri > .5 ? [gImg] : s.iter > .5 && s.rob < .5 ? [gImg, gOut] : s.contrast > .5 || s.rob > .5 ? [] : null;
        [gImg, gEnc, gProj, gCtx, gLLM, gOut, gFlow].forEach(g => g.classList.toggle("hot", !!hot && hot.includes(g)));
        el.classList.toggle("lx-focus", !!hot);
      }

      draw(st);
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
          const ms = n === 2 || n === 3 || n === 7 ? 1000 : n === 6 ? 900 : 700;
          // clamp k: the first rAF timestamp can precede the tween's start, which gives a k slightly below 0
          return api.tween(ms, k => { if (g !== gen) return; X.lerpState(st, from, to, X.clamp(k)); draw(st); }, E.inOut);
        },
      };
    },
  });
})();
