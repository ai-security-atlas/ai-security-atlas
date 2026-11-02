"""Step 1: assemble one request piece by piece and count its tokens. Run from labs/:
    docker compose run --rm workbench python concept-context/scripts/s01_assemble.py
Downloads SmolLM2-360M-Instruct (about 0.7 GB) on the first run.
"""
import labkit

labkit.banner()

import ctxlab as C  # noqa: E402
import tinylm  # noqa: E402

tinylm.fetch(C.MODEL, download=True)
tok, model = C.load()
repo, rev = tinylm.MODELS[C.MODEL]
trained = model.config.max_position_embeddings
budget = C.WINDOW - C.MAX_NEW
print(f"model {repo} @ {rev[:7]}, trained window {trained} tokens")
print(f"app window {C.WINDOW} tokens: {budget} for the request, {C.MAX_NEW} kept free for the reply")

q = C.QUESTIONS[0]
document = C.doc(2)
pieces = [("system prompt", "operator", C.count(tok, C.SYSTEM)),
          ("earlier turn (1)", "user + model", sum(C.count(tok, m["content"]) for m in C.history(1))),
          ("retrieved document (2 paragraphs)", "wiki page", C.count(tok, document)),
          ("tool output", "tool", C.count(tok, C.TOOL)),
          ("question", "user", C.count(tok, q))]
full = C.messages(q, k=1, document=document, tool=C.TOOL)
total = len(C.ids_of(tok, full))
pieces.append(("chat template and labels", "runtime", total - sum(n for _, _, n in pieces)))
print(f"{'piece':<36}{'written by':<16}tokens")
for name, who, n in pieces:
    print(f"{name:<36}{who:<16}{n:>5}")
print(f"{'total':<52}{total:>5} / {budget}  {'fits' if total <= budget else 'over'}")

grow = []
for label, msgs in (("whole wiki page (15 paragraphs)", C.messages(q, k=1, document=C.doc(), tool=C.TOOL)),
                    ("10 earlier turns", C.messages(q, k=10, document=document, tool=C.TOOL))):
    n = len(C.ids_of(tok, msgs))
    grow.append({"label": label, "tokens": n, "over": n - budget})
    print(f"same request with the {label}: {n} / {budget} -> {n - budget} tokens over")
C.save("s01_assemble.json", {"model": f"{repo.split('/')[-1]} @ {rev[:7]}", "trained": trained, "window": C.WINDOW,
                             "max_new": C.MAX_NEW, "budget": budget,
                             "pieces": [{"name": a, "who": b, "tokens": n} for a, b, n in pieces],
                             "total": total, "grow": grow})
