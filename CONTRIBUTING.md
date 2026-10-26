# Contributing

Thanks for helping improve the AI Security Atlas, a learning platform to
understand and learn AI security through realistic scenarios. Contributions that
add sourced accuracy, fix errors, improve clarity, or add safe hands-on labs are
very welcome.

## Ground rules

- **Markdown/JSON is the source of truth.** Never hand-edit generated output
  (`public/`, `content/nodes|sources|views/`, `static/data/`, `data/`).
- **Evidence over assertion.** Every claim should link to a primary source with
  an honest verification depth. A citation is not proof that every sentence was
  reviewed.
- **Neutral methods stay neutral.** Techniques like LoRA, distillation, or
  quantization are not inherently attacks.
- **No operational attack content outside `labs/`.** Describe mechanisms
  conceptually; do not add working payloads, exploit steps, or targeting
  instructions.
- **Lab contributions** (`labs/`) are the only place runnable attack code is
  allowed, and only when: the payload is inert and uses the lab's fixed canary;
  every target is a local fixture the learner creates; the lab ends with a
  Defense chapter; Going Further challenges are evaluation or defense tasks.
  Generated artifacts (`*.pt`, `*.pth`, `*.bin`, `*.pkl`) are never committed.
- **Don't fabricate.** No invented numbers, dates, model versions, CVEs, or
  benchmark scores.

## Where to edit

| You want to… | Edit |
|---|---|
| Fix/extend a topic's prose | `articles/<id>.md` |
| Change structural data (nodes, edges, sources, views) | `ai_security_research_graph_seed.json` |
| Adjust the Explorer UI | `src/` |
| Adjust page templates / design | `layouts/`, `src/index.css` |
| Add or change a hands-on lab | `labs/<node-id>/` (start from `labs/_template/`; see `labs/README.md`) |

## Content status

- `seed` — definition + routing metadata + sources.
- `draft` — has an overview (including AI-drafted ones); **not** reviewed.
- `reviewed` — claims and key limits checked by an identified reviewer.

The build never auto-promotes drafts to `reviewed`. Promote a topic only after a
human review of its claims and sources.

## Local workflow

```bash
make install
make serve          # http://localhost:1313
make build          # verify a clean production-shaped build
```

Open a pull request with a focused change and a short rationale. CI builds and
smoke-tests every PR.
