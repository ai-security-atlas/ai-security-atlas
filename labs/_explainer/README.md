# Lab explainer engine

`explainer.js` and `explainer.css` play a lab's step-by-step animation: a 960x540 stage, five chapters
(System, Attack, Mechanism, Impact, Defense), a caption and a "Run it yourself" command for each step. The engine
has no dependencies and no build step. It runs from `file://` and can be embedded in any page.

It is derived from the laya "No Time to Think" deck engine (MIT, see `LICENSE-laya`), which supplies the
layout and motion. Colors and type follow the Atlas design system (`src/index.css`): system sans text, monospace
eyebrows, warm paper / near-black ink, the lab accent (`--lab`) for chrome and node-type colors for the diagram
roles. JetBrains Mono sets code. The structure follows [bbycroft.net/llm](https://bbycroft.net/llm): a chapter bar synced to the
visualization, focus and context dimming, and a caption panel beside the stage.

```
_explainer/
├── explainer.js     # engine (window.Explainer)
├── explainer.css    # theme; every rule is scoped to .lx
├── LICENSE-laya
└── test/            # Playwright smoke test + lint (see Testing)
```

## Start a lab explainer

1. Copy `labs/_template/explainer/` to `labs/<node-id>/explainer/`.
2. In `index.html`, replace `attack-example` (the `data-explainer` attribute, the title and the hint) with the node id.
3. In `explainer.js`, set `id`, `family`, `title`, `legend` and `steps`, then replace the drawing. Keep the
   `target(n)` / `draw(s)` / `step(n, dir)` structure.
4. Replace `data.js` with the lab's shipped reference run (`window.LAB_DATA = {...}`).
5. Open it: `open labs/<node-id>/explainer/index.html` (macOS) or `xdg-open ...` (Linux). Then run the test.

`index.html` loads, in this order: the Google Fonts link, `../../_explainer/explainer.css`,
`../../_explainer/explainer.js`, `data.js`, `explainer.js`. `<body data-standalone>` makes the explainer fill
the page and makes the arrow keys work anywhere on it. Offline, the fonts fall back to system fonts and nothing
else breaks.

## `Explainer.define(def)`

| Field | Required | Meaning |
| :--- | :--- | :--- |
| `id` | yes | The Atlas node id, equal to the folder name. It is used in `data-explainer="<id>"` and in deep links `#<id>/<step>`. |
| `family` | yes | The node's family id. The kicker reads `<family> · <id>`. |
| `title` | yes | HTML. Wrap exactly one word in `<span class="outline">...</span>` (shown in the lab accent color). The plain text becomes the region's `aria-label`. |
| `legend` | yes | The semantic roles the stage uses, as `["bad", "teal", ...]` (standard labels) or `{ role: "bad", label: "Injected opcodes" }`. |
| `intro` | yes | Plain-text `{ why, plan, terms }`: explain the motivating question, the experiment route and essential vocabulary before the diagram. |
| `steps` | yes | 6–10 step objects (below). |
| `html` | yes | The stage markup, usually one `<svg class="main" viewBox="0 0 960 540" width="960" height="540">`. |
| `setup(stage, api)` | yes | Runs once, the first time the explainer scrolls into view. Returns `{ step(n, dir), enter(), leave() }`; every hook is optional. |
| `stage` | no | The design size, `"960x540"` by default. Keep the default. |

Write for a reader who has never run this lab. The introduction should establish the legitimate task,
the security question and the reader’s route through the experiment. Avoid beginning with architecture,
sample counts or acronyms. In the final guide, explain what the experiment establishes and what it does
not. Keep detailed evidence available without requiring it for a first reading. Do not present saved
reference results as a live experiment or a guarantee across models. Address the reader as “you”, keep
sentences short, and run the `humanizer` skill (`.claude/skills/humanizer`) over `intro` and `guide` text before
committing.

**Step object:** `{ chapter, label, guide, caption, cmd }`.

- `chapter` is one of `System | Attack | Mechanism | Impact | Defense`. Every chapter must be present, chapters
  never go back, and each chapter has 1–3 steps. The bar always shows the five segments, with dots for the
  active chapter's steps.
- `label` is a short name (2–3 words), shown above the caption and in the dot's tooltip.
- `guide` is plain text, usually 35–65 words. Explain what we are doing, why, what to look for, and
  what the observation means. Define new terms before using them. Each step must make sense without reading
  the diagram or opening the reference details, especially on a phone.
- `caption` is HTML containing the reference measurements and implementation detail. It appears inside
  **Reference details**, collapsed when entering a step. Keep numerical results tied to `LAB_DATA`;
  color key terms with role classes and wrap code in `<code>`. Definitions without `guide` retain the
  original caption-only rendering for compatibility with existing embeds.
- `cmd` (optional) is the **full** command, copied verbatim from a line of a README Do block. Write it as a
  plain single- or double-quoted string, not a template literal, because `lint_readme.py` reads it from the
  source. The engine shows it under the caption with a Copy button.

Steps are **1-based** everywhere: `step(n)`, deep links (`#<id>/1` is the first step), `[data-step]`, the
`step N/M` counter and `instance.step`.

The engine checks each definition with `Explainer.validate(def)`. A broken definition logs one `console.error`
and still renders. The test fails on it.

## The required authoring pattern

The visual state is a plain object of numbers. `target(n)` returns the full state for step `n`, and `draw(s)`
renders any state. `step()` tweens toward the target when moving forward by one step and snaps in every other
case:

```js
setup(el, api) {
  const st = { /* numeric visual state */ };
  function target(n) { /* pure: returns the full state for step n (1-based) */ }
  function draw(s)   { /* pure render of state s into SVG/canvas */ }
  draw(st);
  let gen = 0;
  return {
    step(n, dir) {
      const to = target(n), from = { ...st }, g = ++gen;
      if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }   // back/jump/reduced: snap
      return api.tween(600, k => { if (g !== gen) return; Explainer.lerpState(st, from, to, k); draw(st); }, Explainer.ease.inOut);
    },
  };
}
```

`dir` is `1` for a forward move of exactly one step, `-1` for one step back, and `0` for the first render, a jump
(dots, chapter segments, Home/End), a deep link or re-entry after scrolling away. With this pattern, going back,
deep links, jumps and reduced motion need no extra code. The test checks it: for every step, the stage DOM after
an animated forward step must equal the DOM after a deep link to that step. An explainer whose `step()` assumes
it only moves forward by one is rejected.

**Rules for `draw`.** It reads only its argument (and constants built in `setup`). It sets every property that
any step changes, so the result never depends on the previous frame. Derive sub-phases from one state value
with `Explainer.seg(s.x, a, b)` instead of chaining timers.

**Pacing** (from bbycroft's walkthrough): the caption changes first, then one fast eased action (300–800 ms),
then a pause. Use one action per step. Never tie text to a slow continuous animation. Details go in the
README's **Why**.

## `api` (one per instance)

Everything started through `api` stops when the explainer leaves the screen or the tab is hidden. When it comes
back, the engine calls `step(current, 0)`.

| Member | Meaning |
| :--- | :--- |
| `api.tween(ms, fn(k), ease = ease.inOut)` | Calls `fn` each frame with eased `k` from 0 to 1 and resolves `true`, or `false` if it was stopped. The last call is always `fn(1)`. Under reduced motion it calls `fn(1)` at once. |
| `api.loop(fn(t, dt))` | rAF loop with seconds since start and since the last frame. Under reduced motion it draws one frame at `t = 0`. Use it only for ambient motion, never to carry step state. |
| `api.after(ms, fn)` / `api.sleep(ms)` | A timer, or a Promise resolving `true` (or `false` if stopped). Under reduced motion they wait 0 ms. |
| `api.guard()` | Returns `ok()`, which turns `false` once the instance is stopped. Check it after every `await`. |
| `api.reduced` | `true` under `prefers-reduced-motion: reduce` (read live). |
| `api.color(name)` | The resolved token value, for example `api.color("bad")`. Use it for Canvas 2D, which cannot read CSS variables. Read it inside `draw` so a theme switch applies on the next step. |
| `api.uid(name)` | A page-unique id (`lx3-name`) for SVG `<marker>`, gradient, `<clipPath>` and filter ids, so two explainers on one page never clash. |

## Helpers on `window.Explainer`

| Helper | Meaning |
| :--- | :--- |
| `svg(tag, attrs, parent)` | Creates an SVG element. `text: "..."` sets the text content. `<text>` gets `fill="currentColor"` (the stage ink) unless you pass `fill`. A `fill`, `stroke`, `stop-color` or `color` whose value contains `var(` is written to `style`, never as an attribute. |
| `attr(el, attrs)` | Updates an element with the same rules. Use it in `draw` for colors: `X.attr(box, { stroke: X.v("bad") })`. |
| `v(name)` | `"var(--lx-<name>)"`. |
| `lerpState(st, from, to, k)` | Interpolates the numeric keys of `to` into `st`. Other values snap at `k = 1`, and `k >= 1` copies `to` exactly. |
| `ease.linear / inOut / out / in / back` | Easing functions. |
| `lerp(a, b, k)`, `clamp(x)`, `seg(k, a, b)` | Math helpers. `seg` maps `k` in `[a, b]` to `[0, 1]`, clamped. |
| `rng(seed)` | Seeded random numbers (mulberry32). Never use `Math.random()`, because `draw` must be repeatable. |
| `validate(def)` | Returns the list of definition problems (empty when valid). |
| `CHAPTERS`, `ROLES` | The chapter names, and the role → legend label map. |
| `mount(el)`, `instances`, `defs` | Mount an element added after load. Each instance has `{ host, def, step, go(n), next(), prev(), replay() }`. |

## Stage markup and styling

- **Scope your CSS** with `[data-explainer="<id>"] ...` inside a `<style>` in `html`. Do not use element ids:
  the engine uses none, and `api.uid()` covers SVG references.
- **Fragments.** `[data-step="3"]` is shown from step 3 on, and `[data-only="2,3"]` only at those steps.
- **Focus and context.** Add `class="dimmable"` to groups. In `draw`, toggle `.hot` on the focused groups and
  `lx-focus` on the stage (`el.classList.toggle("lx-focus", ...)`). Every `.dimmable` without `.hot` fades to 20%.
- **Laya classes** you can use in stage HTML: `.mono`, `.display`, `.head`, `.kicker`, `.card`, `.tag`, `.pill`,
  `.abs` (absolute position), `.outline`, `.grad`, and `.c-<role>` for colored text.
- **Camera.** To pan or zoom, tween the main SVG's `viewBox` between named 16:9 frames held in the state
  (see the template's `zoom`).
- **Cells and grids.** Draw tensors and pixel grids as rounded cells, and encode the value as size or opacity.
  Use SVG for up to about 300 cells. Above that, use Canvas 2D (`putImageData`) for full images and heatmaps.
- **Flow.** Data flows as cubic Bézier ribbons in `teal`. Gradients flow backward as `bad` ribbons.
- **Text.** The minimum stage text is 13 design px.
- **Canvas accessibility.** Every `<canvas>` gets `role="img"` and an `aria-label`, and `draw` updates the label.

## Colors (one legend for every lab)

Never write a hex color in an explainer (the test fails on one), and never write `fill="var(...)"` as an
attribute. Use `X.v("<token>")` through `svg()`/`attr()`, or `el.style.fill = ...`. The tokens switch for light and
dark mode automatically.

| Role (legend key, `.c-<role>`) | Token | Use it for |
| :--- | :--- | :--- |
| `bad` · Attacker-controlled (Atlas attack red) | `--lx-bad` | malicious opcodes, perturbation, tampered files, injected text |
| `teal` · Trusted data (Atlas architecture blue) | `--lx-teal` | tensor bytes, clean pixels, benign opcodes, data flow |
| `violet` · Model / computation (Atlas method violet) | `--lx-violet` | weights, encoder/LLM blocks, VM stack, activations, logits |
| `warn` · Model output (Atlas family amber) | `--lx-warn` | output tokens, captions, model answers |
| `lime` · Canary / side effect (Atlas concept green) | `--lx-lime` | canary strings, marker file, the "fired" pulse |
| `ok` · Defense (Atlas defense cyan) | `--lx-ok` | allowlist gate, safetensors, sandbox wall, purification |
| `muted` · Context | `--lx-muted`, `--lx-line`, `--lx-dim` | dimmed blocks, frames, arrows |

The surface tokens are `--lx-bg`, `--lx-panel`, `--lx-panel-2`, `--lx-stage`, `--lx-line`, `--lx-ink`,
`--lx-ink-2`, `--lx-muted` and `--lx-dim`. Card fills use `panel`, frames use `line`, and default text uses the
stage ink (`currentColor`).

## Data

The explainer reads only `window.LAB_DATA`, which `data.js` defines with a plain `<script>`. Never use `fetch()`
or JSON files, because they break `file://`. Every string that comes from a run (opcodes, outputs, error text,
the canary) comes from `LAB_DATA`, never from text typed into `explainer.js`. `scripts/export_explainer_data.py`
regenerates `data.js` from a reference container run. A student's `work/` folder never changes it.

## Safety rules (spec §5.3; the test checks the first two)

- The last chapter is Defense.
- At least one Impact caption names the lab's canary (README front matter `canary:`), so a screenshot cannot
  read as a real exploit demo.
- The kicker is `<family> · <node-id>` and nothing else.

## Embedding in another page (Atlas site)

```html
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/labs/_explainer/explainer.css">
<script src="/labs/_explainer/explainer.js"></script>
<script src="/labs/<node-id>/explainer/data.js"></script>
<script src="/labs/<node-id>/explainer/explainer.js"></script>
...
<div data-explainer="<node-id>"></div>
```

- Every `[data-explainer]` mounts on `DOMContentLoaded`, and a definition loaded later mounts its hosts when
  it is defined. Call `Explainer.mount(el)` for elements added afterwards. Several explainers per page work.
  Only one lab's `data.js` can be on a page, because each sets `window.LAB_DATA`.
- The CSS only styles `.lx` and its children (and `body[data-standalone]`), and it holds up under a
  Tailwind-style reset. The engine adds no element ids.
- The theme follows `html[data-theme="dark|light"]`, `html.dark` / `html.light`, and otherwise
  `prefers-color-scheme`, the same switch the Atlas uses. A switch applies live.
- The keys work only while the explainer has focus (click it or Tab to it). Without `data-standalone`, the page
  keeps its own keys.
- A hash `#<node-id>/<n>` opens that explainer at step `n` and scrolls it into view. User navigation rewrites the
  hash with `history.replaceState` (no history entries). Other hashes are ignored.
- A wide container (≥ 1000 px) puts the caption panel beside the stage. A narrower one stacks: introduction, guide, stage, bar,
  command. These are container queries, so the explainer responds to its column, not to the window.

## Keyboard and accessibility

- `→` / `Space` / `PageDown` go to the next step, `←` / `PageUp` to the previous one, `Home` / `End` to the first
  or last step, and `R` restarts. Clicking the stage advances, and the dots and chapter segments jump.
- The host is a focusable `region` labelled with the title. The caption is `aria-live="polite"`, and every
  control has an `aria-label`. Under `prefers-reduced-motion`, tweens jump to their end and CSS transitions are
  off.

## Testing

```bash
cd labs/_explainer/test
npm ci
npx playwright install chromium        # add firefox webkit to test those too
node test.mjs                          # or: node test.mjs firefox | webkit
```

The test finds every `labs/*/explainer/index.html` (including the template) and `test/embed.html`, which puts two
explainers in an article with a Tailwind-style reset. It exits 1 on any `FAIL` and checks:

- the definition lint (5 chapters in order, non-decreasing, 1–3 per chapter, 6–10 steps)
- no hex colors, `fill="var(` or `fetch` in `explainer.js`, and no `fill`/`stroke` `var()` attributes in the DOM
- `data.js` loads from `file://` with no page errors and no network request besides Google Fonts
- every `cmd` appears verbatim in a README bash block (skipped for the template's placeholders), and the strip
  and the Copy button work
- a deep link to every step in both themes, with the counter reading `step N/M`
- reduced motion reaching each step's final state within 90 ms, and animated steps ending exactly at the
  deep-link state
- the safety rules above
- no horizontal scroll at 390 px
- the embed and standalone checks ported from the prototype: focused keys, hash, focus dimming, back, jumps,
  live theme switch, lazy setup, deep-link scroll, scoped CSS and unique ids

Screenshots go to `test/shots/` (git-ignored): `<browser>-<id>-<light|dark>-<1280|390>.png` at the first
Impact step, plus two embed shots. Look at them before you commit.
