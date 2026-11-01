"""Steps 4 and D3: what llama-server renders and answers with the GGUF and flags it was started with. Run from labs/:
    docker compose run --rm workbench python format-gguf/scripts/s04_served.py tampered
    docker compose run --rm workbench python format-gguf/scripts/s04_served.py pinned
    docker compose run --rm workbench python format-gguf/scripts/s04_served.py no-jinja
The label only names the output file (work/s04_<label>.json); start llama-server first as the README shows.
"""
import difflib
import sys

import labkit

labkit.banner()

import ggufkit  # noqa: E402
import serving  # noqa: E402

label = sys.argv[1] if len(sys.argv) > 1 else "tampered"
base = serving.BASE_URL
serving.wait_ready(base)
props = serving.get(base, "/props").json() or {}
model_path = props.get("model_path", "?")
served = props.get("chat_template", "")

pinned = ggufkit.PINNED_TEMPLATE.read_text()
embedded = None
for n, p in ggufkit.FILES.items():
    if p.name == model_path.rsplit("/", 1)[-1] and p.exists():
        embedded = ggufkit.template_of(p)
known = {"the GGUF's embedded template": embedded, "the pinned template": pinned}
source = next((k for k, v in known.items() if v is not None and served == v), "neither the GGUF's nor the pinned one")
print(f"[note] {base} serves {ggufkit.rel(model_path) if '/labs/' in model_path else model_path.rsplit('/', 1)[-1]}")
print(f"/props chat_template: {len(served)} chars, sha256 {ggufkit.sha256_bytes(served)[:12]} = {source}")

prompt = ggufkit.apply_template(base)
clean = ggufkit.render_sandboxed(pinned, ggufkit.ONE_USER)
print("POST /apply-template for the user message 'hi':")
print(f"  {ggufkit.short(prompt, 150)}")
added = ""
if prompt == clean:
    print("  identical to the pinned template's prompt")
else:
    sm = difflib.SequenceMatcher(a=clean, b=prompt, autojunk=False)
    ops = sm.get_opcodes()
    added = " | ".join(prompt[j1:j2] for op, _, _, j1, j2 in ops if op in ("insert", "replace"))
    removed = " | ".join(clean[i1:i2] for op, i1, i2, _, _ in ops if op in ("delete", "replace"))
    print("  differs from the pinned template's prompt;"
          + (f" added: {ggufkit.short(added, 100)}" if added else "")
          + (f" removed: {ggufkit.short(removed, 100)}" if removed else ""))

hits, answers = ggufkit.canary_rate(base)
print()
print("10 fixed questions, temperature 0, through /v1/chat/completions:")
for q, a in answers[:3]:
    print(f"  {q:<36} -> {ggufkit.short(a, 60)}")
print("  ...")
print(f"canary {ggufkit.CANARY} in {hits}/10 answers")

msgs = [{"role": "system", "content": ggufkit.DEPLOYER_SYSTEM}, {"role": "user", "content": "What are your opening hours?"}]
dprompt = ggufkit.apply_template(base, msgs)
dans = ggufkit.ask(base, "What are your opening hours?", system=ggufkit.DEPLOYER_SYSTEM)
print()
print(f"with the deployer's own system prompt ('{ggufkit.DEPLOYER_SYSTEM}'):")
print(f"  system turn the model sees: {ggufkit.short(dprompt.split('<|im_end|>')[0].replace('<|im_start|>system', '').strip(), 120)}")
print(f"  answer: {ggufkit.short(dans, 80)}")

ggufkit.save(f"s04_{label}.json", {"label": label, "model_path": model_path, "template_source": source,
                                    "template_chars": len(served), "prompt": prompt, "added": added, "hits": hits,
                                    "answers": answers, "deployer_prompt": dprompt, "deployer_answer": dans})
