/* LAB-45 concept-samplers: "Same weights, ten times the cost" (foundation lab, 9 steps).
 * Chapters read as System -> Risk (Attack slot) -> Mechanism -> Observation (Impact slot) -> Defense.
 * One scene: a sampling loop across the top (noise -> scheduler <-> UNet -> image) and a panel below that
 * crossfades per step. Generated images are painted on one overlay canvas. Every number, image and string
 * comes from window.LAB_DATA (data.js, exported from the reference workbench run).
 * Pattern: target(n) is pure, draw(s) is pure, step() tweens forward by one only. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v, seg = X.seg;
  const D = window.LAB_DATA;
  const sw = D.swap.rows, cost = D.cost.rows, api3 = D.cost.api;
  const row = (rs, steps, batch = 1) => rs.find(r => r.steps === steps && r.batch === batch) || {};
  const at = (name, steps) => (D.solvers.rows[name] || []).find(r => r.steps === steps) || {};
  const seedRow = k => D.seeds.rows.find(r => r.label.startsWith(k)) || {};
  const loadRow = k => D.load.find(r => r.label.startsWith(k)) || {};
  const fired = D.load.find(r => r.fired) || {};
  const mb = b => (b / 1e6).toFixed(0) + " MB";

  X.define({
    id: "concept-samplers",
    family: "family-availability",
    title: 'Same weights, ten times the <span class="outline">cost</span>',
    legend: [{ role: "violet", label: "Weights / UNet" }, { role: "teal", label: "Scheduler settings" },
      { role: "warn", label: "Generated image" }, { role: "bad", label: "Caller-chosen cost / code" },
      { role: "lime", label: "Canary" }, { role: "ok", label: "Defense" }],
    intro: {
      why: "An image model learns to remove noise from a picture. To draw something new, it starts from pure noise and cleans it a little at a time. A separate piece of code, the sampler, decides how many cleaning steps to take and how big each one is. If you change only the sampler, what happens to the cost of a request and to the image you get back?",
      plan: "You’ll load one small pretrained image model and keep its weights fixed. First you’ll swap samplers and time requests with different step counts. Next you’ll measure how the image moves when the step count, the solver or a small setting changes under the same seed. Then you’ll load a “faster sampler” that ships its own code. To finish, you’ll cap the settings, fingerprint an evaluation and load pipelines under a policy.",
      terms: "A UNet is the neural network that predicts the noise in an image. A scheduler is the diffusers name for a sampler: a small config file with no weights. A step is one call to the UNet. A solver is the rule that moves the image from one step to the next. A seed fixes the starting noise. RMSE measures how far apart two images are: the square root of the mean squared pixel difference, from 0 to 255. The canary is a harmless marker string.",
    },
    steps: [
      { chapter: "System", label: "Pipeline parts",
        guide: "Start by opening the pipeline. One part holds all the learned weights: the UNet, which looks at a noisy image and predicts the noise. The other part, the scheduler, holds only settings. Each step of drawing an image costs one full UNet call. Notice the small Python file in the repository too; the default loader never runs it.",
        caption: `<code>${D.repo}</code> @ ${D.rev}: <span class="c-violet">${D.unet}</span> with ${(D.params / 1e6).toFixed(1)}M parameters (weights sha256 ${D.sha}); <span class="c-teal">${D.sched}</span>, ${D.train_steps} training noise levels, ${D.beta[0]} betas. One UNet call took ${Math.round(D.call_ms)} ms. <code>${D.module}</code> is named in <code>model_index.json</code>; imported by the default load: ${D.imported.length ? D.imported.join(", ") : "nothing"}.`,
        cmd: "docker compose run --rm workbench python concept-samplers/scripts/s01_pipeline.py" },
      { chapter: "System", label: "Swap the scheduler",
        guide: "Swap in four schedulers built from the model’s own config, and draw one image with each from the same seed. DDIM, DPM-Solver++ and Euler land on the same car. DDPM, the original sampler, adds fresh noise at every step and is still noisy after so few steps. Check the weights hash after all four swaps: it hasn’t moved.",
        caption: `${D.swap.steps} steps, seed ${D.swap.seed}: ${sw.map(r => `<span class="c-teal">${r.cls}</span> starts at t = ${r.ts[0]}`).join(", ")}. Weights after four swaps: <span class="c-ok">${D.swap.same ? "unchanged" : "changed"}</span>. Euler run through <code>DDPMPipeline</code>’s own loop skips the input scaling it needs (pixel std ${D.swap.lib.euler.std}).`,
        cmd: "docker compose run --rm workbench python concept-samplers/scripts/s02_swap.py" },
      { chapter: "Attack", label: "Caller sets steps",
        guide: "Now time the same request at several step counts. The cost grows in step with the number of UNet calls, and the answer is still one small image. Picture an image API that forwards the client’s step count and scheduler name. A normal-looking request can then ask for many times the work of the default.",
        caption: `DDIM, same weights: ${[10, 20, 50, 200].map(n => `${n} steps ${row(cost, n).sec} s`).join(", ")} (<span class="c-bad">${row(cost, 200).x}x</span> the 20-step time). Four images at 20 steps took ${row(cost, 20, 4).sec} s. API priced at ${D.cost.ms_call} ms per call: ${api3.map(r => `${r.label} ${r.calls} calls`).join("; ")}.${D.slow ? ` Measured in Step 7: DDPM 1000 steps took ${D.slow.s1k} s, ${D.slow.x}x the 20-step default.` : ""}`,
        cmd: "docker compose run --rm workbench python concept-samplers/scripts/s03_cost.py" },
      { chapter: "Mechanism", label: "Steps and solvers",
        guide: "Every run here starts from the same noise. DDIM, DPM-Solver++ and Euler are solvers for one fixed path from noise to image, so with more steps they all close in on the same picture. The chart shows each one’s distance from a long DDIM run. DPM-Solver++ gets close fastest. DDPM stays far away because its random steps need hundreds of calls.",
        caption: `Reference: ${D.solvers.ref[0]} ${D.solvers.ref[1]} steps. RMSE at 10 steps: DDIM ${at("ddim", 10).rmse}, <span class="c-ok">DPM-Solver++ ${at("dpm++", 10).rmse}</span>, Euler ${at("euler", 10).rmse}. At 5 steps: ${at("ddim", 5).rmse}, ${at("dpm++", 5).rmse}, ${at("euler", 5).rmse}. DDPM: ${at("ddpm", 20).rmse} at 20 steps and <span class="c-bad">${at("ddpm", 50).rmse}</span> at 50.`,
        cmd: "docker compose run --rm workbench python concept-samplers/scripts/s04_solvers.py" },
      { chapter: "Mechanism", label: "Seeds aren’t enough",
        guide: "A seed fixes only the starting noise. Change one setting at a time and check two things: are the image bytes identical, and how far did the picture move? A new seed is the yardstick for a different picture. Most setting changes keep the picture and change the bytes. For DDPM, even the batch size matters.",
        caption: `New seed: RMSE <span class="c-bad">${D.seeds.other}</span>. Rerun: ${seedRow("DDIM 20, seed 0, run again").same ? "identical" : "different"}. DPM-Solver++: ${seedRow("DPM-Solver++").rmse}; Euler: ${seedRow("Euler").rmse}; <code>timestep_spacing=trailing</code>: ${seedRow("DDIM 20, timestep_spacing").rmse}; DDPM: ${seedRow("DDPM").rmse}. DDPM as image 1 of a batch of 2: ${D.seeds.ddpm_batch_same ? "identical" : "different"} (RMSE ${D.seeds.ddpm_batch_rmse}).`,
        cmd: "docker compose run --rm workbench python concept-samplers/scripts/s05_seeds.py" },
      { chapter: "Impact", label: "Loader runs code",
        guide: "A repository promises a faster sampler and asks you to load its own pipeline file with a trust flag. Without the flag, diffusers refuses. With it, the file’s top-level code runs during loading and drops the harmless canary. A bare community pipeline name gets as far as the download with no trust flag at all.",
        caption: `<code>trust_remote_code=True</code>: ${loadRow("... and trust").result}; the marker reads <code class="c-lime">${D.canary}</code>. No flag: ${loadRow("acme-ddpm-fast").result.split(":")[0]}. <code>custom_pipeline='lpw_stable_diffusion'</code>: <span class="c-bad">${loadRow("custom_pipeline=").result.split(",")[0]}</span> (stubbed, nothing fetched). Bin-only folder: default ${loadRow("bin-only, default").result.split(" from ")[0]} from <code>.bin</code>; <code>use_safetensors=True</code> ${loadRow("bin-only, use_safetensors").result.split(":")[0]}.`,
        cmd: "docker compose run --rm workbench python concept-samplers/scripts/s06_loading.py" },
      { chapter: "Defense", label: "Cap and budget",
        guide: "Put a cap on the server. It allows a short list of schedulers and a step limit, and rejects anything else before the first UNet call, so a refused request costs nothing. A cap limits each request, though. One client can still send many requests that each stay under it, so a per-client budget counts UNet calls per minute.",
        caption: `Pass-through: ${D.cap.pt_calls} UNet calls for the five requests; <span class="c-ok">capped: ${D.cap.cap_calls}</span>. ${D.cap.volume.n} requests of 50 steps from one client: all pass the cap; a budget of ${D.cap.budget} calls per minute accepts ${D.cap.volume.ok} and rejects ${D.cap.volume.rej}.`,
        cmd: "docker compose run --rm workbench python concept-samplers/scripts/d1_cap_steps.py" },
      { chapter: "Defense", label: "Pin and fingerprint",
        guide: "For evaluation, write every setting that shapes the output into a manifest next to the weights hash, and hash the manifest. Two runs get compared only when their fingerprints match. Here each one-setting drift changes the pixels, and the gate catches it. One row shows the cost of caution: a thread change left the image alone.",
        caption: `Pinned fingerprint ${D.pin.fp}. ${D.pin.rows.map(r => `${r.label}: ${r.gate}, ${r.same ? "same pixels" : "RMSE " + r.rmse}`).join("; ")}. Gate decisions that disagree with the pixels: ${D.pin.wrong}.`,
        cmd: "docker compose run --rm workbench python concept-samplers/scripts/d2_pin_eval.py" },
      { chapter: "Defense", label: "Load by policy",
        guide: "Load every pipeline through one policy: turn remote code off globally, require safetensors weights and allow only known component classes. Run Step 6’s loads again under it. Then search the cache for code that already ran, since diffusers keeps a copy. This covers one library on one machine; review and vendor any sampler code you really need.",
        caption: `Environment switch alone: canary ${D.policy.rows.filter(r => r.env_fired).length} of ${D.policy.rows.length}, pickle <code>.bin</code> still loads. <span class="c-ok">Policy</span>: canary ${D.policy.rows.filter(r => r.policy_fired).length}, <code>.bin</code> refused. Modules cache: ${D.policy.cache.filter(c => c.canary).length} copied <code>pipeline.py</code> holding <code class="c-lime">${D.canary}</code>. Evaluate: ${Object.values(D.evaluate).filter(v => v === "rejected" || v === "refused").length} rows rejected or refused as expected.`,
        cmd: "docker compose run --rm workbench python concept-samplers/scripts/d3_load_policy.py" },
    ],
    html: `<style>
      [data-explainer="concept-samplers"] canvas.cs-img { position: absolute; left: 0; top: 0; width: 960px; height: 540px; image-rendering: pixelated; pointer-events: none; }
    </style>
    <svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Sampling loop with a detail panel per step"></svg>
    <canvas class="cs-img" width="960" height="540" role="img" aria-label="Generated images"></canvas>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const cvs = el.querySelector("canvas.cs-img");
      const ctx = cvs.getContext("2d");
      const T = (p, x, y, s, size = 15, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s, o = {}) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2", ...o });
      const card = (p, x, y, w, h, stroke = V("line"), o = {}) => S("rect", { x, y, width: w, height: h, rx: 10, fill: V("panel"), stroke, "stroke-width": 2, ...o }, p);
      const pill = (p, x, y, w, txt, role) => {
        S("rect", { x, y, width: w, height: 26, rx: 13, fill: V(role), "fill-opacity": .14, stroke: V(role), "stroke-width": 1.5 }, p);
        return T(p, x + w / 2, y + 18, txt, 13, { class: "mono", "text-anchor": "middle", "font-weight": 700, fill: V(role) });
      };
      const cut = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
      const defs = S("defs", {}, svg);
      const arrowId = api.uid("arrow");
      const mk = S("marker", { id: arrowId, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      S("path", { d: "M0 0 L10 5 L0 10 Z", fill: V("dim") }, mk);
      const arrow = (p, d, stroke = V("dim")) => S("path", { d, fill: "none", stroke, "stroke-width": 2, "marker-end": `url(#${arrowId})` }, p);

      // ---- images: base64 RGB (32x32x3) -> small offscreen canvases, painted on the overlay in draw()
      const pics = new Map();
      const pic = b64 => {
        if (!pics.has(b64)) {
          const bin = atob(b64), c = document.createElement("canvas");
          c.width = c.height = 32;
          const cx = c.getContext("2d"), im = cx.createImageData(32, 32);
          for (let i = 0; i < 1024; i++) {
            im.data[4 * i] = bin.charCodeAt(3 * i); im.data[4 * i + 1] = bin.charCodeAt(3 * i + 1);
            im.data[4 * i + 2] = bin.charCodeAt(3 * i + 2); im.data[4 * i + 3] = 255;
          }
          cx.putImageData(im, 0, 0);
          pics.set(b64, c);
        }
        return pics.get(b64);
      };
      const slots = [];   // {panel index, b64, x, y, size}
      const slot = (pi, b64, x, y, size, p) => {
        slots.push({ pi, b64, x, y, size });
        if (p) S("rect", { x: x - 2, y: y - 2, width: size + 4, height: size + 4, rx: 4, fill: "none", stroke: V("warn"), "stroke-width": 2 }, p);
      };

      // ---- the sampling loop strip
      const gStrip = S("g", { class: "dimmable" }, svg);
      const strip = [["NOISE", "dim", "seeded randn", 24], ["SCHEDULER", "teal", "settings only", 250], ["UNET", "violet", `${(D.params / 1e6).toFixed(1)}M weights`, 476], ["IMAGE", "warn", "32 x 32 RGB", 742]];
      const stripBox = strip.map(([k, role, sub, x]) => {
        const b = card(gStrip, x, 18, 194, 70, V(role));
        label(gStrip, x + 14, 44, k, { fill: V(role === "dim" ? "muted" : role), "letter-spacing": "1" });
        T(gStrip, x + 14, 72, sub, 14, { class: "mono" });
        return b;
      });
      arrow(gStrip, "M220 53 H246");
      arrow(gStrip, "M446 42 H472");
      arrow(gStrip, "M472 66 H450");
      arrow(gStrip, "M672 53 H738");
      const loopTxt = T(gStrip, 461, 108, "", 13, { class: "mono", "text-anchor": "middle", fill: V("muted") });
      const loopCalls = [`× ${D.swap.steps} steps = ${D.swap.steps} UNet calls`, `× ${D.swap.steps} steps = ${D.swap.steps} UNet calls`,
        "× steps chosen by the caller", "× 5 to 100 steps", `× ${D.swap.steps} steps, seed 0`, "loader: which code runs?",
        `× at most ${D.cap.cap.max_steps} steps`, "× pinned steps, seed, config", "loader: policy first"];
      const panel = () => S("g", { class: "dimmable" }, svg);

      // ---- P1: what the pipeline is made of
      const g1 = panel();
      card(g1, 40, 134, 420, 170, V("violet"));
      label(g1, 60, 164, "UNET · THE TRAINED WEIGHTS", { fill: V("violet") });
      T(g1, 60, 204, `${D.params.toLocaleString("en")} parameters`, 22, { "font-weight": 700 });
      T(g1, 60, 236, `weights sha256 ${D.sha}`, 14, { class: "mono", fill: V("muted") });
      T(g1, 60, 278, `one call: ${Math.round(D.call_ms)} ms for one 32x32 image`, 15, { class: "mono" });
      card(g1, 40, 324, 420, 180, V("teal"));
      label(g1, 60, 354, "SCHEDULER · SETTINGS, NO WEIGHTS", { fill: V("teal") });
      T(g1, 60, 394, D.sched, 22, { "font-weight": 700 });
      T(g1, 60, 426, `${D.train_steps} noise levels, ${D.beta[0]} betas ${D.beta[1]}…${D.beta[2]}`, 14, { class: "mono", fill: V("muted") });
      T(g1, 60, 466, "decides how many UNet calls a sample takes", 15, { class: "mono" });
      label(g1, 500, 164, "FILES IN THE REPOSITORY");
      const fileBars = D.files.map(([f, size], i) => {
        const y = 182 + i * 54, code = f.endsWith(".py"), w = 380 * Math.log10(size) / 9;
        T(g1, 500, y + 16, f, 14, { class: "mono", fill: V(code ? "bad" : "ink") });
        const bar = S("rect", { x: 500, y: y + 24, width: 0, height: 12, rx: 4, fill: V(code ? "bad" : f.includes("diffusion_pytorch") ? "violet" : "teal"), opacity: .75 }, g1);
        T(g1, 920, y + 16, size >= 1e6 ? mb(size) : `${size.toLocaleString("en")} B`, 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
        return { bar, w };
      });
      T(g1, 500, 182 + D.files.length * 54 + 8, `${D.module}: named, ${D.imported.length ? "imported" : "never imported"} (log scale)`, 13, { class: "mono", fill: V("muted") });

      // ---- P2: four schedulers, same weights, same seed
      const g2 = panel();
      label(g2, 40, 134, `SAME WEIGHTS · SEED ${D.swap.seed} · ${D.swap.steps} STEPS EACH`);
      sw.forEach((r, i) => {
        const x = 58 + i * 228;
        slot(1, r.img, x, 152, 168, g2);
        T(g2, x, 350, r.name.toUpperCase(), 16, { "font-weight": 700, fill: V(r.name === "ddpm" ? "bad" : "warn") });
        T(g2, x, 372, cut(r.cls, 24), 13, { class: "mono", fill: V("teal") });
        T(g2, x, 394, `t = ${r.ts.slice(0, 3).join(", ")}, …`, 13, { class: "mono", fill: V("muted") });
        T(g2, x, 416, `${r.calls} calls · ${r.sec} s`, 13, { class: "mono" });
      });
      card(g2, 40, 440, 880, 72, V(D.swap.same ? "ok" : "bad"));
      T(g2, 60, 472, `pipe.scheduler = X.from_config(pipe.scheduler.config)`, 15, { class: "mono", fill: V("teal") });
      T(g2, 60, 498, `weights sha256 ${D.sha} after four swaps: ${D.swap.same ? "unchanged" : "changed"}`, 15, { class: "mono", "font-weight": 700, fill: V(D.swap.same ? "ok" : "bad") });

      // ---- P3: cost against the step count
      const g3 = panel();
      label(g3, 40, 134, "DDIM, SAME WEIGHTS: SECONDS PER REQUEST");
      const maxSec = Math.max(...cost.map(r => r.sec));
      const costBars = cost.map((r, i) => {
        const y = 148 + i * 36, big = r.steps >= 200;
        T(g3, 40, y + 19, `${r.steps} steps${r.batch > 1 ? `, ${r.batch} images` : ""}`, 14, { class: "mono" });
        const bar = S("rect", { x: 220, y: y + 6, width: 0, height: 18, rx: 4, fill: V(big ? "bad" : "teal"), opacity: .8 }, g3);
        T(g3, 920, y + 19, `${r.sec} s · ${r.calls} calls · ${r.x}x`, 13, { class: "mono", "text-anchor": "end", fill: V(big ? "bad" : "muted") });
        return { bar, w: 400 * r.sec / maxSec };
      });
      label(g3, 40, 352, `IMAGE API THAT FORWARDS THE CLIENT’S SETTINGS (DEFAULT DPM-SOLVER++ ${api3[0].steps})`);
      const apiBars = api3.map((r, i) => {
        const y = 366 + i * 46, dflt = i === 0;
        T(g3, 40, y + 22, cut(r.label, 26), 14, { class: "mono", fill: V(dflt ? "teal" : "bad") });
        const bar = S("rect", { x: 300, y: y + 8, width: 0, height: 22, rx: 4, fill: V(dflt ? "teal" : "bad"), opacity: .8 }, g3);
        T(g3, 920, y + 24, `${r.calls} calls · ${r.x}x`, 15, { class: "mono", "text-anchor": "end", "font-weight": 700, fill: V(dflt ? "teal" : "bad") });
        return { bar, w: 400 * r.calls / api3[api3.length - 1].calls };
      });
      T(g3, 40, 520, D.slow ? `measured (Step 7): DDPM 1000 steps ${D.slow.s1k} s against ${D.slow.s20} s for the default, ${D.slow.x}x` : `priced at ${D.cost.ms_call} ms per UNet call`, 13, { class: "mono", fill: V("muted") });

      // ---- P4: distance to the reference against steps, per solver
      const g4 = panel();
      label(g4, 40, 134, `RMSE TO ${D.solvers.ref[0].toUpperCase()} ${D.solvers.ref[1]} STEPS (SAME SEED)`);
      const xs = [5, 10, 20, 50], cx0 = 90, cx1 = 560, cy0 = 470, cy1 = 160;
      const allR = Object.values(D.solvers.rows).flat().map(r => r.rmse);
      const yTop = Math.ceil(Math.max(...allR) / 20) * 20;
      const px = s => cx0 + (cx1 - cx0) * Math.log(s / 5) / Math.log(50 / 5);
      const py = v => cy0 - (cy0 - cy1) * v / yTop;
      S("path", { d: `M${cx0} ${cy1} V${cy0} H${cx1}`, fill: "none", stroke: V("line"), "stroke-width": 2 }, g4);
      xs.forEach(s => T(g4, px(s), cy0 + 22, String(s), 13, { class: "mono", "text-anchor": "middle", fill: V("muted") }));
      T(g4, (cx0 + cx1) / 2, cy0 + 44, "steps (UNet calls)", 13, { "text-anchor": "middle", fill: V("muted") });
      for (let v = 0; v <= yTop; v += 20) T(g4, cx0 - 10, py(v) + 5, String(v), 13, { class: "mono", "text-anchor": "end", fill: V("muted") });
      const style = { ddim: ["teal", ""], "dpm++": ["ok", ""], euler: ["violet", "6 4"], ddpm: ["bad", ""] };
      const lines = Object.entries(D.solvers.rows).map(([name, rs]) => {
        const [role, dash] = style[name] || ["muted", ""];
        const d = rs.map((r, i) => `${i ? "L" : "M"}${px(r.steps).toFixed(1)} ${py(r.rmse).toFixed(1)}`).join(" ");
        const path = S("path", { d, fill: "none", stroke: V(role), "stroke-width": 3, "stroke-dasharray": dash }, g4);
        rs.forEach(r => S("circle", { cx: px(r.steps), cy: py(r.rmse), r: 4, fill: V(role) }, g4));
        const last = rs[rs.length - 1];
        T(g4, px(last.steps) + 10, py(last.rmse) + (name === "dpm++" ? 16 : name === "ddim" ? -6 : 5), name, 14, { class: "mono", "font-weight": 700, fill: V(role) });
        return path;
      });
      label(g4, 640, 134, "FROM THE SAME NOISE");
      const thumbs = [["reference", D.solvers.ref_img], ["ddim 10", at("ddim", 10).img], ["dpm++ 10", at("dpm++", 10).img],
        ["euler 10", at("euler", 10).img], ["ddim 5", at("ddim", 5).img], ["ddpm 50", at("ddpm", 50).img]];
      thumbs.forEach(([t, b64], i) => {
        const x = 640 + (i % 2) * 150, y = 150 + Math.floor(i / 2) * 124;
        if (b64) slot(3, b64, x, y, 90, g4);
        T(g4, x, y + 110, t, 13, { class: "mono", fill: V(t.startsWith("ddpm") ? "bad" : "muted") });
      });

      // ---- P5: what a seed fixes
      const g5 = panel();
      label(g5, 40, 134, `ONE CHANGE AT A TIME FROM DDIM 20 STEPS, SEED 0 · IDENTICAL BYTES? · RMSE`);
      const rmax = Math.max(...D.seeds.rows.map(r => r.rmse));
      const seedBars = D.seeds.rows.map((r, i) => {
        const y = 148 + i * 52;
        slot(4, r.img, 40, y, 44);
        const role = r.same ? "ok" : r.rmse >= D.seeds.other / 2 ? "bad" : "warn";
        T(g5, 100, y + 28, cut(r.label, 38), 14, { class: "mono" });
        pill(g5, 430, y + 9, 96, r.same ? "identical" : "differs", r.same ? "ok" : "bad");
        const bar = S("rect", { x: 546, y: y + 14, width: 0, height: 16, rx: 4, fill: V(role), opacity: .8 }, g5);
        T(g5, 920, y + 28, r.rmse.toFixed(1), 14, { class: "mono", "text-anchor": "end", "font-weight": 700, fill: V(role) });
        return { bar, w: 320 * r.rmse / rmax };
      });
      const yard = 546 + 320 * D.seeds.other / rmax;
      S("path", { d: `M${yard} 146 V${148 + D.seeds.rows.length * 52}`, stroke: V("muted"), "stroke-width": 1.5, "stroke-dasharray": "4 4" }, g5);

      // ---- P6: the loader runs repository code
      const g6 = panel();
      label(g6, 40, 134, "ACME/DDPM-FAST (“4 STEPS”)");
      card(g6, 40, 146, 300, 214, V("line"));
      [["model_index.json", "teal"], ["unet/ (pinned weights)", "violet"], ["scheduler/", "teal"], ["pipeline.py", "bad"], ["README: trust_remote_code=True", "muted"]]
        .forEach(([f, role], i) => T(g6, 58, 180 + i * 38, f, 14, { class: "mono", fill: V(role), "font-weight": role === "bad" ? 700 : 400 }));
      label(g6, 370, 134, "DiffusionPipeline.from_pretrained(...)");
      const outcome = r => r.fired ? ["CANARY", "lime"] : r.fetch ? ["at download", "bad"] : r.result.startsWith("refused") ? ["refused", "ok"]
        : r.result.includes(".bin") ? ["loads .bin", "warn"] : ["loaded", "muted"];
      const loadRows = D.load.map((r, i) => {
        const y = 146 + i * 44, [txt, role] = outcome(r);
        T(g6, 370, y + 24, cut(r.label, 40), 14, { class: "mono" });
        const p = S("g", {}, g6);
        pill(p, 780, y + 6, 140, txt, role);
        return p;
      });
      const gCan = S("g", {}, g6);
      card(gCan, 40, 384, 880, 120, V("lime"));
      T(gCan, 60, 418, "trust_remote_code=True ran pipeline.py at load; marker file:", 15, { class: "mono" });
      T(gCan, 60, 458, D.canary, 26, { class: "mono", "font-weight": 800, fill: V("lime") });
      T(gCan, 60, 488, cut(fired.marker || "", 80), 13, { class: "mono", fill: V("muted") });

      // ---- P7: cap per request, budget per client
      const g7 = panel();
      label(g7, 40, 134, `CAP: ${D.cap.cap.samplers.join(" / ").toUpperCase()}, ≤ ${D.cap.cap.max_steps} STEPS · PASS-THROUGH CALLS · CAPPED ANSWER`);
      const capBars = D.cap.rows.map((r, i) => {
        const y = 148 + i * 42, ok = r.capped.startsWith("200");
        T(g7, 40, y + 22, cut(r.req.replace("num_inference_steps", "steps"), 34), 13, { class: "mono" });
        const bar = S("rect", { x: 330, y: y + 9, width: 0, height: 18, rx: 4, fill: V("bad"), opacity: .7 }, g7);
        T(g7, 338 + 260 * r.pt_calls / 1000, y + 23, String(r.pt_calls), 13, { class: "mono", fill: V("bad") });
        pill(g7, 680, y + 5, 240, cut(r.capped, 28), ok ? "teal" : "ok");
        return { bar, w: 260 * r.pt_calls / 1000 };
      });
      label(g7, 40, 386, `ONE CLIENT, ${D.cap.volume.n} REQUESTS OF 50 STEPS · BUDGET ${D.cap.budget} UNET CALLS PER MINUTE`);
      const tiles = Array.from({ length: D.cap.volume.n }, (_, i) => {
        const x = 40 + i * 73, okT = i < D.cap.volume.ok;
        const r = S("rect", { x, y: 402, width: 63, height: 56, rx: 8, "stroke-width": 2 }, g7);
        T(g7, x + 31, 436, okT ? "200" : "429", 15, { class: "mono", "text-anchor": "middle", "font-weight": 700, fill: V(okT ? "teal" : "ok") });
        return { r, okT, i };
      });
      T(g7, 40, 494, `pass-through ${D.cap.pt_calls} calls → capped ${D.cap.cap_calls}; all ${D.cap.volume.n} small requests pass the cap, the budget stops ${D.cap.volume.rej}`, 14, { class: "mono", fill: V("muted") });

      // ---- P8: pinned manifest and fingerprint gate
      const g8 = panel();
      card(g8, 40, 146, 280, 330, V("ok"));
      label(g8, 58, 176, "MANIFEST", { fill: V("ok") });
      ["weights sha256", "scheduler class", "full scheduler config", "steps · seed · batch", "threads", "diffusers · torch"].forEach((f, i) =>
        T(g8, 58, 212 + i * 34, f, 14, { class: "mono" }));
      T(g8, 58, 446, `fingerprint ${D.pin.fp}`, 15, { class: "mono", "font-weight": 700, fill: V("ok") });
      label(g8, 350, 134, "RUN");
      label(g8, 620, 134, "GATE");
      label(g8, 906, 134, "PIXELS", { "text-anchor": "end" });
      const pinRows = D.pin.rows.map((r, i) => {
        const y = 146 + i * 62, cmp = r.gate === "compare", right = cmp === r.same;
        const c = card(g8, 350, y, 570, 52, V(right ? "line" : "warn"));
        T(g8, 366, y + 32, cut(r.label, 30), 14, { class: "mono" });
        pill(g8, 620, y + 13, 120, cmp ? "compare" : "refuse", cmp ? "teal" : "ok");
        T(g8, 906, y + 32, r.same ? "identical" : `RMSE ${r.rmse}`, 14, { class: "mono", "text-anchor": "end", "font-weight": 700, fill: V(r.same ? "teal" : "bad") });
        return c;
      });
      void pinRows;
      T(g8, 350, 476, `gate decisions that disagree with the pixels: ${D.pin.wrong} of ${D.pin.rows.length}`, 14, { class: "mono", fill: V("muted") });

      // ---- P9: loading policy and cache forensics
      const g9 = panel();
      label(g9, 40, 134, "STEP 6 LOADS AGAIN");
      label(g9, 470, 134, "ENV SWITCH ONLY");
      label(g9, 720, 134, "POLICY");
      const verdict = (res, fire) => fire ? ["CANARY", "lime"] : res.startsWith("refused") ? ["refused", "ok"]
        : res.includes(".bin") ? ["loads .bin", "warn"] : ["loads", "teal"];
      D.policy.rows.forEach((r, i) => {
        const y = 146 + i * 46;
        T(g9, 40, y + 22, cut(r.label, 40), 14, { class: "mono" });
        const [a, ra] = verdict(r.env, r.env_fired), [b, rb] = verdict(r.policy, r.policy_fired);
        pill(g9, 470, y + 4, 200, a, ra);
        pill(g9, 720, y + 4, 200, b, rb);
      });
      const gCache = S("g", {}, g9);
      const hit = D.policy.cache.find(c => c.canary);
      card(gCache, 40, 386, 880, 118, V(hit ? "lime" : "ok"));
      label(gCache, 60, 414, "HF MODULES CACHE · CODE THAT ALREADY RAN");
      T(gCache, 60, 446, hit ? cut(hit.path, 76) : "no imported pipeline code found", 14, { class: "mono" });
      T(gCache, 60, 482, hit ? `contains ${D.canary}: delete it and re-check the cache after an incident` : "", 15, { class: "mono", "font-weight": 700, fill: V("lime") });

      const panels = [g1, g2, g3, g4, g5, g6, g7, g8, g9];
      const keys = panels.map((_, i) => "p" + (i + 1));
      const base = Object.fromEntries(keys.map(k => [k, 0]));
      const target = n => ({ ...base, [keys[n - 1]]: 1 });
      // strip boxes each step highlights: noise, scheduler, unet, image
      const hot = [[1, 2], [1, 3], [1, 2], [1, 3], [0, 3], [2], [1], [0, 1], [2]];

      function draw(s) {
        panels.forEach((g, i) => { const v = s[keys[i]]; g.setAttribute("opacity", v.toFixed(3)); g.style.display = v > .01 ? "" : "none"; });
        fileBars.forEach(({ bar, w }) => A(bar, { width: (w * seg(s.p1, .2, 1)).toFixed(1) }));
        costBars.forEach(({ bar, w }, i) => A(bar, { width: (w * seg(s.p3, i * .08, .5 + i * .08)).toFixed(1) }));
        apiBars.forEach(({ bar, w }, i) => A(bar, { width: Math.max(2, w * seg(s.p3, .4 + i * .15, .8 + i * .05)).toFixed(1) }));
        lines.forEach((p, i) => p.setAttribute("opacity", seg(s.p4, i * .15, .4 + i * .15).toFixed(3)));
        seedBars.forEach(({ bar, w }, i) => A(bar, { width: (w * seg(s.p5, i * .06, .5 + i * .06)).toFixed(1) }));
        loadRows.forEach((p, i) => p.setAttribute("opacity", seg(s.p6, i * .1, .3 + i * .1).toFixed(3)));
        gCan.setAttribute("opacity", seg(s.p6, .6, 1).toFixed(3));
        capBars.forEach(({ bar, w }, i) => A(bar, { width: Math.max(2, w * seg(s.p7, i * .06, .5 + i * .06)).toFixed(1) }));
        tiles.forEach(({ r, okT, i }) => {
          const on = seg(s.p7, .3 + i * .04, .45 + i * .04);
          A(r, { fill: V(okT ? "teal" : "panel"), "fill-opacity": okT ? .25 * on : 1, stroke: V(okT ? "teal" : "ok"), opacity: (.2 + .8 * on).toFixed(3) });
        });
        gCache.setAttribute("opacity", seg(s.p9, .5, 1).toFixed(3));
        const n = keys.findIndex(k => s[k] > .5);
        stripBox.forEach((b, i) => b.setAttribute("stroke-width", n >= 0 && hot[n].includes(i) ? 4 : 2));
        loopTxt.textContent = n >= 0 ? loopCalls[n] : "";
        const focus = s.p6 > .5 || s.p9 > .5;
        gStrip.classList.toggle("hot", !focus);
        panels.forEach(g => g.classList.toggle("hot", focus));
        el.classList.toggle("lx-focus", focus);
        // generated images on the overlay canvas
        ctx.clearRect(0, 0, cvs.width, cvs.height);
        ctx.imageSmoothingEnabled = false;
        slots.forEach(({ pi, b64, x, y, size }) => {
          const a = s[keys[pi]];
          if (a <= .01) return;
          ctx.globalAlpha = a;
          ctx.drawImage(pic(b64), x, y, size, size);
        });
        ctx.globalAlpha = 1;
        const shown = slots.filter(t => s[keys[t.pi]] > .5).length;
        cvs.setAttribute("aria-label", shown ? `${shown} generated 32x32 images from ${D.repo}, same weights, different sampler settings` : "No generated images on this step");
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
