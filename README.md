# AI Security Atlas

A **learning platform to understand and learn AI security through realistic
scenarios**. It pairs an opinionated, evidence-linked knowledge graph of how AI
systems are attacked, defended, and evaluated with hands-on labs that reproduce
selected mechanisms on your own machine. The graph connects an adversary's
**objective** to the underlying **mechanism**, its **prerequisites**, the
**architectures** it applies to, the **evidence** behind it, and the **controls**
that address it.

The website executes nothing, probes no third-party services and hosts no
payloads. The optional [`labs/`](labs/) directory contains local-only,
self-contained reproductions for study: they run in Docker on your own machine,
use inert canary payloads, target only files and models the learner creates for
the lab, and end with a defense chapter.

🌐 **Live site:** https://ai-security-atlas.github.io/

## What's inside

- **204 topics** across 11 types (objectives, technique families, attacks,
  methods, defenses, evaluations, concepts, architectures, components, lifecycle
  stages, formats) linked by **650 typed relationships**.
- **97 primary sources** with honest verification depth (a citation does not
  imply full-text review).
- A goal-first **Explorer** (SPA) with a curated sidebar, a relationship-rich
  reader, and a local-neighborhood graph — plus pre-rendered standalone pages for
  every topic and source (no-JS / SEO / deep links).
- **Hands-on labs** ([`labs/`](labs/)): local Docker reproductions of selected
  attacks, each with an animated explainer (published at `/labs/` on the site)
  and a defense chapter. Topics with a lab carry a "Hands-on lab" badge.

Every topic carries a short **AI-generated draft** overview, clearly labeled and
never auto-promoted to "reviewed."

## Architecture

Markdown/JSON is the source of truth; everything else is a reproducible
projection.

```
ai_security_research_graph_seed.json   canonical data (nodes, edges, sources, views)
articles/<id>.md                       optional authored prose (survives rebuilds)
labs/<id>/README.md + explainer/       hands-on labs (front matter -> node `lab`)
        │
        ▼  json2hugo.py  (deterministic compiler)
static/data/atlas.json + data/atlas.json   denormalized graph (fwd+inverse rels, nav)
content/{nodes,sources,views}/*.md         Hugo content pages
static/labs/                               published lab explainers (/labs/)
        │
        ▼  Vite (React SPA)  +  Hugo (static HTML)  +  Pagefind (search)
public/                                    deployable static site
```

- **Compiler:** Python + `uv` (`json2hugo.py`) — denormalizes relationships,
  builds the curated goal→family→attack navigation, resolves evidence, and merges
  authored article bodies.
- **Explorer:** React + Vite (`src/`), rendered with Cytoscape-free canvas graph
  (`react-force-graph-2d`). Design system in `src/index.css`.
- **Pages:** Hugo templates in `layouts/`.
- **Search:** Pagefind (static, in-browser; no vector service).

See `AI_Security_Research_Graph_PRD.md` for the full product spec.

## Develop

```bash
make install    # Node + Python deps
make serve      # dev server at http://localhost:1313
```

Edit topic prose in `articles/<id>.md` and the dev server reflects it. Structural
data lives in `ai_security_research_graph_seed.json`.

## Build

```bash
make build       # local preview build (public/)
make build-prod  # production build (uses config.production.toml baseURL)
make docker      # container image (nginx, serves on :8080)
```

## Deploy

CI builds and pushes `public/` to the separate Pages repository
`ai-security-atlas/AI-SECURITY-ATLAS.github.io`, served at
https://ai-security-atlas.github.io/.

**One-time setup:** add a repository secret `DEPLOY_TOKEN` (a PAT with write
access to the target Pages repo). Every push to `main` then deploys via
`.github/workflows/deploy-to-pages.yml`. `.github/workflows/ci.yml` builds and
smoke-tests every push/PR.

To use a custom domain, set `baseURL` in `config.production.toml` and add a
`static/CNAME`.

## License

Code is MIT-licensed (see `LICENSE`). Content synthesizes and links to primary
sources; consult each source for its own terms.
