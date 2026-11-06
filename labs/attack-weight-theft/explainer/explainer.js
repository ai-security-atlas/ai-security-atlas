/* Explainer for attack-weight-theft. Reference numbers come from window.LAB_DATA. */
(() => {
  const X = Explainer, S = X.svg, A = X.attr, V = X.v;
  const D = window.LAB_DATA;

  X.define({
    id: "attack-weight-theft",
    family: "family-theft",
    title: 'An open port <span class="outline">copies</span> the fine-tune',
    legend: [
      { role: "teal", label: "Trusted data", tag: "model-weights" },
      { role: "bad", label: "Attacker-controlled", tag: "extraction-probe" },
      { role: "violet", label: "Model / computation", tag: "inference-server" },
      { role: "lime", label: "Canary / side effect" },
      { role: "ok", label: "Defense", tag: "access-control" },
      { role: "warn", label: "Model output" },
    ],
    intro: {
      why: "Can someone who can reach a model server take a private fine-tune home, file for file? This is plain copying of the stored files, not imitation, and the model never runs. You’ll use a lab server with no password on an internal lab network, copy one fictional fine-tune, and then measure what still stops the next person.",
      plan: "List the models, read the fine-tune text, push it to a registry on the same network, and separate the public weight file from the private text. Then cut the network, require a password, and check a fingerprint.",
      terms: "A blob is one file in a model image. A manifest lists those blobs. A digest is the hash of a blob. A canary is a fixed harmless marker placed in the fine-tune so you can recognize a copy. The victim is the lab Ollama server. The registry is the lab store that receives the push.",
    },
    steps: [
      { chapter: "System", label: "Open API",
        guide: "You begin with the server as an operator would see it. An open API means a request with no password still gets an answer. List the model names on this network. Each name is a handle for files the server is willing to send.",
        caption: `The lab server <code>victim-ollama</code> answered <span class="c-teal">GET /api/tags</span> with HTTP ${D.surface.status} and no password. It lists <code>${D.model.name}</code> (${D.model.size.toLocaleString()} bytes) and the public base <code>${D.base.name}</code>.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml docker compose run --rm workbench python attack-weight-theft/scripts/check_env.py" },
      { chapter: "System", label: "Fine-tune text",
        guide: "Read the fine-tune next. A Modelfile is the short text stored beside the weights, including the system prompt and a license line. Find the fixed marker in that text. You will use the same marker to recognize a copy after it leaves.",
        caption: `POST /api/show returned the system line. The marker <code class="c-lime">${D.canary}</code> is in that text. Fine-tune digest <code>${D.model.digest_short}</code> differs from the public base <code>${D.base.digest_short}</code>.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml docker compose run --rm workbench python attack-weight-theft/scripts/s01_surface.py" },
      { chapter: "Attack", label: "Push the copy",
        guide: "The open API also accepts a rename and a push. A registry is a store that keeps a manifest and the blobs that manifest names. Point the push at the registry on this network. The server then writes out the fine-tune it already holds.",
        caption: `POST /api/push wrote <code class="c-bad">${D.registry.name}</code> in ${D.theft.push_s}s. The stolen manifest lists ${D.theft.bytes.toLocaleString()} bytes. Victim digest equals the pushed name: ${D.theft.digests_equal}.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml docker compose run --rm workbench python attack-weight-theft/scripts/s02_exfiltrate.py" },
      { chapter: "Mechanism", label: "Shared weights",
        guide: "Hash both copies and place the blobs side by side. A manifest lists every blob in one image, and each blob has a digest. The large weight blob matches the public base. The private piece is a small system layer whose digest shows up on the fine-tune alone.",
        caption: `Weight blob of the fine-tune equals the public base: <span class="c-warn">${D.theft.weight_equals_base}</span>. The private system layer is <code class="c-lime">${D.theft.system_digest_short}</code>.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml docker compose run --rm workbench python attack-weight-theft/scripts/s03_fidelity.py" },
      { chapter: "Impact", label: "Marker leaves",
        guide: "Open the stolen system blob and search it for the marker you saw earlier. Finding it in a blob from the registry means the private fine-tune text has left the server. The big weight file is a public model, so downloading it is no theft. What was stolen is the small private layer, and its size alone wouldn’t tell you that.",
        caption: `The stolen system blob contains <code class="c-lime">${D.canary}</code>. That string is the success signal for this lab. The copy’s layer bytes stay ${D.theft.bytes.toLocaleString()}.` },
      { chapter: "Defense", label: "Cut the network",
        guide: "Move to a container that shares no network with the victim. Segmentation is that missing path: the names victim and registry fail to resolve. Time the failed lookup. From the operator container, which remains attached, repeat the model list and time the successful call.",
        caption: `The outsider’s lookup failed in ${D.defense.outsider_ms} ms (name resolution). The operator’s GET /api/tags stayed HTTP ${D.defense.operator_status} at ${D.defense.operator_ms} ms median.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml COMPOSE_PROFILES=workbench,theft-outsider docker compose run --rm outsider python attack-weight-theft/scripts/d1_segment.py" },
      { chapter: "Defense", label: "Require a password",
        guide: "Turn on a password for the registry. Read the stolen manifest with an empty password, then with the operator password, and keep both status codes and both times. The anonymous read now gets HTTP 401 (unauthorized), and the check adds only a tiny delay. Blobs that were already copied stay on disk either way.",
        caption: `Anonymous manifest read: HTTP <span class="c-ok">${D.defense.anon_status}</span> in ${D.defense.anon_ms} ms. Operator password: HTTP ${D.defense.auth_status} in ${D.defense.auth_ms} ms. Extra time: ${D.defense.auth_delta_ms} ms. User <code>${D.operator_user}</code>.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml:attack-weight-theft/compose.auth.yaml docker compose run --no-deps --rm workbench python attack-weight-theft/scripts/d2_registry_auth.py" },
      { chapter: "Defense", label: "Check the fingerprint",
        guide: "Hash the stolen system blob and check it against the digest in the manifest. A fingerprint proves which blob you hold, so it can identify a stolen copy. It doesn’t stop the theft: read the stolen size again and you get the same number. Feed the check a decoy sentence and confirm the decoy fails.",
        caption: `Fingerprint hash median ${D.defense.fingerprint_ms} ms. Decoy rejected: ${D.defense.decoy_rejected}. Stolen bytes stayed ${D.theft.bytes.toLocaleString()}. The check leaves the copy where it landed.`,
        cmd: "COMPOSE_PROJECT_NAME=atlas-labs-attack-weight-theft COMPOSE_FILE=compose.yaml:attack-weight-theft/compose.yaml:attack-weight-theft/compose.auth.yaml docker compose run --no-deps --rm workbench python attack-weight-theft/scripts/d3_fingerprint.py" },
    ],
    html: `<svg class="main" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Victim server, registry, and stolen layers"></svg>`,

    setup(el, api) {
      const svg = el.querySelector("svg.main");
      const T = (p, x, y, s, size = 16, o = {}) => S("text", { x, y, "font-size": size, text: s, ...o }, p);
      const label = (p, x, y, s) => T(p, x, y, s, 13, { fill: V("muted"), "font-weight": 700, "letter-spacing": "2" });
      const card = (p, x, y, w, h, stroke = V("line")) => S("rect", { x, y, width: w, height: h, rx: 16, fill: V("panel"), stroke, "stroke-width": 2 }, p);

      const gVictim = S("g", { class: "dimmable" }, svg);
      label(gVictim, 48, 78, "VICTIM");
      card(gVictim, 40, 92, 280, 168, V("teal"));
      T(gVictim, 58, 128, "victim-ollama", 18, { "font-weight": 700 });
      T(gVictim, 58, 154, "no password on :11434", 14, { fill: V("muted") });
      const gBase = S("g", {}, gVictim);
      S("rect", { x: 58, y: 176, width: 244, height: 32, rx: 8, fill: V("teal"), opacity: .16, stroke: V("teal"), "stroke-width": 1.5 }, gBase);
      const baseName = T(gBase, 70, 198, D.base.name, 14, { class: "mono", fill: V("teal") });
      const gFt = S("g", {}, gVictim);
      const ftBox = S("rect", { x: 58, y: 214, width: 244, height: 32, rx: 8, fill: V("violet"), opacity: .18, stroke: V("violet"), "stroke-width": 1.5 }, gFt);
      T(gFt, 70, 236, D.model.name, 14, { class: "mono", fill: V("violet"), "font-weight": 600 });

      const gFlow = S("g", { class: "dimmable" }, svg);
      const ribbon = S("path", { d: "M324 176 H400", fill: "none", stroke: V("bad"), "stroke-width": 8, "stroke-linecap": "round" }, gFlow);
      T(gFlow, 332, 164, "push", 13, { fill: V("bad"), "font-weight": 700 });

      const gReg = S("g", { class: "dimmable" }, svg);
      label(gReg, 428, 78, "REGISTRY");
      const regBox = card(gReg, 420, 92, 300, 168, V("warn"));
      T(gReg, 438, 128, "registry:5000", 18, { "font-weight": 700 });
      const stolen = T(gReg, 438, 160, "lantern/ft:stolen", 15, { class: "mono", fill: V("bad"), "font-weight": 600 });
      const lockTxt = T(gReg, 438, 196, "", 16, { class: "mono", "font-weight": 700 });
      const authTxt = T(gReg, 438, 224, "", 14, { fill: V("ok") });

      const gOutsider = S("g", { class: "dimmable" }, svg);
      label(gOutsider, 748, 78, "OUTSIDER");
      card(gOutsider, 740, 92, 180, 168);
      T(gOutsider, 756, 132, "other network", 15, { "font-weight": 700 });
      const wall = S("rect", { x: 728, y: 92, width: 8, height: 0, rx: 4, fill: V("ok") }, gOutsider);
      const outTxt = T(gOutsider, 756, 176, "", 14, { fill: V("muted") });

      const gLayers = S("g", { class: "dimmable" }, svg);
      label(gLayers, 48, 312, "BLOBS");
      card(gLayers, 40, 326, 680, 176);
      const weightBox = S("rect", { x: 60, y: 348, width: 400, height: 64, rx: 10, fill: V("teal"), opacity: .16, stroke: V("teal"), "stroke-width": 1.5 }, gLayers);
      T(gLayers, 76, 376, "weight blob", 16, { "font-weight": 700, fill: V("teal") });
      const weightNote = T(gLayers, 76, 398, "same bytes as the public base", 14, { fill: V("teal") });
      const gSystem = S("g", {}, gLayers);
      const sysBox = S("rect", { x: 480, y: 348, width: 216, height: 64, rx: 10, fill: V("lime"), opacity: .18, stroke: V("lime"), "stroke-width": 1.5 }, gSystem);
      T(gSystem, 496, 374, "system blob", 15, { "font-weight": 700, fill: V("lime") });
      const canaryTxt = T(gSystem, 496, 396, "", 13, { class: "mono", fill: V("lime"), "font-weight": 700 });
      const digestTxt = T(gLayers, 60, 470, "", 14, { class: "mono", fill: V("muted") });

      const gFinger = S("g", { class: "dimmable" }, svg);
      card(gFinger, 740, 326, 180, 176, V("ok"));
      T(gFinger, 756, 366, "fingerprint", 15, { "font-weight": 700, fill: V("ok") });
      const finTxt = T(gFinger, 756, 404, "", 14, { fill: V("ok"), "font-weight": 700 });
      const finSize = T(gFinger, 756, 432, "", 13, { class: "mono", fill: V("muted") });

      const st = { list: 0, ft: 0, push: 0, layers: 0, canary: 0, wall: 0, auth: 0, finger: 0 };
      const base = { list: 1, ft: 0, push: 0, layers: 0, canary: 0, wall: 0, auth: 0, finger: 0 };
      const T_N = [null,
        { list: 1 },
        { list: 1, ft: 1 },
        { list: 1, ft: 1, push: 1 },
        { list: 1, ft: 1, push: 1, layers: 1 },
        { list: 1, ft: 1, push: 1, layers: 1, canary: 1 },
        { list: 1, ft: 1, push: 1, wall: 1 },
        { list: 1, ft: 1, push: 1, wall: 1, auth: 1 },
        { list: 1, ft: 1, push: 1, layers: 1, canary: 1, wall: 1, auth: 1, finger: 1 },
      ];
      const target = n => ({ ...base, ...T_N[n] });

      function draw(s) {
        A(gBase, { opacity: s.list.toFixed(3) });
        A(gFt, { opacity: (0.35 + 0.65 * s.ft).toFixed(3) });
        A(ftBox, { "stroke-width": (1.5 + 2.5 * s.ft).toFixed(2) });
        A(gFlow, { opacity: s.push.toFixed(3) });
        A(stolen, { opacity: s.push.toFixed(3) });
        A(regBox, { stroke: s.auth > .5 ? V("ok") : V("warn") });
        lockTxt.textContent = s.auth > .5 ? ("HTTP " + D.defense.anon_status) : "no password";
        A(lockTxt, { fill: s.auth > .5 ? V("ok") : V("warn") });
        authTxt.textContent = s.auth > .5 ? ("password HTTP " + D.defense.auth_status) : "";
        A(wall, { height: (168 * s.wall).toFixed(2) });
        outTxt.textContent = s.wall > .5 ? "name lookup failed" : "separate network";
        A(outTxt, { fill: s.wall > .5 ? V("ok") : V("muted") });
        A(gLayers, { opacity: (0.15 + 0.85 * s.layers).toFixed(3) });
        A(weightBox, { opacity: (0.2 + 0.8 * s.layers).toFixed(3) });
        weightNote.textContent = s.layers > .5 ? "same bytes as the public base" : "";
        canaryTxt.textContent = s.canary > .5 ? D.canary : "";
        A(sysBox, { "stroke-width": (1.5 + 2.5 * s.canary).toFixed(2) });
        digestTxt.textContent = s.layers > .5 ? D.theft.system_digest_short : "";
        A(gFinger, { opacity: s.finger.toFixed(3) });
        finTxt.textContent = s.finger > .5 ? "decoy rejected" : "";
        finSize.textContent = s.finger > .5 ? (D.theft.bytes.toLocaleString() + " bytes") : "";
        const focus = s.finger > .5 ? [gFinger, gSystem]
          : s.auth > .5 ? [gReg]
          : s.wall > .5 ? [gOutsider]
          : s.canary > .5 ? [gSystem, gReg]
          : s.layers > .5 ? [gLayers]
          : s.push > .5 ? [gFlow, gReg]
          : s.ft > .5 ? [gFt]
          : [];
        [gVictim, gFlow, gReg, gOutsider, gLayers, gFinger].forEach(g => g.classList.toggle("hot", focus.includes(g)));
        el.classList.toggle("lx-focus", focus.length > 0);
        baseName.textContent = D.base.name;
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
