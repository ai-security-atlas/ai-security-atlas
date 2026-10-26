# AI Security Atlas · Hands-On Labs

Local, reproducible labs for selected [AI Security Atlas](https://ai-security-atlas.github.io/) nodes. Each lab reproduces one attack mechanism with real open-source tools in a Docker Compose sandbox on your own machine, measures it, and ends with a defense. Every lab follows the same page layout, and each one links back to its Atlas node and has an animated explainer.

> [!WARNING]
> **Local sandbox, educational use only.** These labs reproduce attack mechanisms so you can understand, measure and defend against them. Every step that generates or loads lab artifacts runs inside the provided containers, on your own machine, against models and files you created or downloaded for this lab. Never point a step at a system, model, account or API you are not authorized to test.
>
> **Payloads are harmless by design.** Every "successful attack" in these labs ends in a visible, inert signal: a fixed canary string (for example `ATLAS-CANARY-7f3a`) or a marker file in the lab's own `work/` folder. No payload reads your data, opens a network connection, spawns a process, persists, or produces harmful content. (Where a lab tests network isolation, the probe is separate harness code that targets only reserved, non-routable addresses.) Do not modify payloads.
>
> **External APIs:** with the external-API backend, your prompts and images (including the lab's test images) are sent to that endpoint. Prefer a server you run yourself. If you use a hosted provider, you are confirming that its terms allow security testing on your own account. Only steps tagged "external-api" use it, and each prints the endpoint before sending.

## Start here

Every lab assumes these steps are done. Run all commands from this `labs/` folder.

1. Read [`requirements.md`](requirements.md) and pick a model backend (or none).
2. Copy the settings file and keep exactly one backend block uncommented (block a is active by default). On Linux, also set `LAB_UID`/`LAB_GID` (see the comments in the file).

   ```bash
   cp .env.example .env
   ```

3. Host Ollama only: start it and pull the models on the host.

   ```bash
   ollama pull qwen2.5vl:3b
   ollama pull moondream:1.8b
   ```

4. Build the workbench image once (a few minutes; later labs reuse it).

   ```bash
   docker compose build workbench
   ```

5. Open a lab below and follow its Setup.
6. To open a lab's explainer, run `open <id>/explainer/index.html` (macOS) or `xdg-open <id>/explainer/index.html` (Linux). The explainer step links in lab READMEs work only in a local clone; on GitHub they show HTML source.

## Labs

| LAB | Lab | Atlas node | Family | Level | Model backend | Time | Explainer |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| LAB-01 | [What torch.load really runs](attack-unsafe-load/README.md) | attack-unsafe-load | family-supply | beginner | none | 60 min | `attack-unsafe-load/explainer/index.html` |
| LAB-02 | [Moving a VLM with invisible pixels](attack-visual-jailbreak/README.md) | attack-visual-jailbreak | family-evasion | intermediate | optional | 120 min | `attack-visual-jailbreak/explainer/index.html` |

## Folder layout and template

Each lab lives in a folder named after its Atlas node id and follows [`_template/`](_template/README.md) exactly: the same front matter, the same sections, and the same **Do** / **Observe** / **Why** step blocks. Shared pieces are [`compose.yaml`](compose.yaml) (profiles `ollama`, `chat`, `workbench`, `supply`), the [`workbench/`](workbench/) image, `_shared/labkit.py` (paths, banner, canaries) and the explainer engine in `_explainer/`.

Maintainer tools (host Python 3.9 or newer, standard library only, run from the repository root):

| Command | What it does |
| :--- | :--- |
| `python3 labs/_tools/lint_readme.py [<node-id>]` | Checks every lab README against the template (front matter, section order, step blocks, explainer links, prev/next footer, `expected/checks.txt` step ids, Atlas node ids, explainer commands) and fails if a pickle or torch archive under `labs/` is tracked by git. |
| `python3 labs/_tools/verify.py <node-id>` | Runs the lab README's Do blocks in order, exactly as a student would, writes `labs/<node-id>/work/verify.log`, and checks each step's output against `expected/checks.txt`. It uses `LAB_BACKEND` from `labs/.env` to pick the profiles, skips backend-tagged steps when no backend is set, and runs slow steps only with `VERIFY_SLOW=1`. |
| `python3 labs/_shared/test_inert.py` | Payload review: checks the inert LAB-01 payload against an AST allowlist, and checks that `exec`, `eval` and `__reduce__` appear only in the payload-site scripts. |
