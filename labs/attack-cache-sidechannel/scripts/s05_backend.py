"""Step 5 (optional): the same probe against the model backend you configured (Ollama), not the
reference llama.cpp server. Run from labs/:
    docker compose run --rm workbench python attack-cache-sidechannel/scripts/s05_backend.py
Prints the endpoint first, then two seeded protocols: the attacker's best case (its live-code probe
leaves first, right after the victim's request) and the realistic case (random probe order).
"""
import random

import labkit

labkit.banner()

import serving  # noqa: E402
import cachelab as C  # noqa: E402

b = labkit.backend()
if not b:
    print("[skip] no model backend configured (LAB_BACKEND/LAB_LLM_BASE_URL unset); "
          "the reference llama.cpp server of Steps 1-4 is this lab's subject")
    raise SystemExit(0)
model = __import__("os").environ.get("LAB_CHAT_MODEL", "qwen2.5:3b")
print(f"[note] probing model backend {b['name']} at {b['base_url']} (model {model}); "
      f"this step sends its own fictional prompts there and nothing else")

BASE = b["base_url"].removesuffix("/v1")   # serving.chat() adds /v1/chat/completions itself


def backend_turn(code, tag, max_tokens):
    return serving.chat(BASE, [{"role": "system", "content": C.system_prompt(code, tag)},
                               {"role": "user", "content": C.QUESTION}],
                        key=b["api_key"] or None, model=model, max_tokens=max_tokens)


def backend_probe(code, tag):
    r = serving.chat(BASE, [{"role": "system", "content": C.system_prompt(code, tag)},
                            {"role": "user", "content": C.PROBE}],
                     key=b["api_key"] or None, model=model, max_tokens=1)
    if r.status != 200:
        raise SystemExit(f"[!!] backend replied HTTP {r.status}: {r.body[:120]}")
    return r.seconds


def rounds(true_first, n, seed):
    rng = random.Random(seed)
    hits, misses, ok = [], [], 0
    for rnd in range(n):
        live = 0 if rnd == 0 else rng.randrange(len(C.CODES))
        tag = f"{C.tag_for(200 + rnd)}{'-F' if true_first else ''}"
        backend_turn(C.CODES[live], tag, 8)
        order = list(range(len(C.CODES)))
        if true_first:
            rng.shuffle(order)
            order.remove(live)
            order.insert(0, live)
        else:
            rng.shuffle(order)
        times = {i: backend_probe(C.CODES[i], tag) for i in order}
        hits.append(times[live])
        misses += [times[i] for i in order if i != live]
        ok += min(times, key=times.get) == live
    return hits, misses, ok, n


print(f"\nbest case: the live-code probe leaves first, right after the victim's request")
hits, misses, ok, n = rounds(True, 6, 31)
_, _, p, auc = C.mann_whitney(hits, misses)
import statistics
print(f"  picks right {ok}/{n}   hit median {statistics.median(hits) * 1000:.0f} ms vs miss median "
      f"{statistics.median(misses) * 1000:.0f} ms   MWU p={C.fmt_p(p)}   AUC {auc:.3f}")

print(f"\nrealistic case: probe order is random, as in Step 3")
hits2, misses2, ok2, n2 = rounds(False, 6, 32)
_, _, p2, auc2 = C.mann_whitney(hits2, misses2)
print(f"  picks right {ok2}/{n2}   hit median {statistics.median(hits2) * 1000:.0f} ms vs miss median "
      f"{statistics.median(misses2) * 1000:.0f} ms   MWU p={C.fmt_p(p2)}   AUC {auc2:.3f}")

verdict = ("no measurable signal on this backend setup" if p >= 0.05 and p2 >= 0.05 else
           "an order-dependent signal: only a probe that leaves first, right after the victim's request, sees the reused prefix"
           if p < 0.05 and p2 >= 0.05 else
           "a signal that survives random probe order, so the backend's cache spans more than the last request")
print(f"\nRESULT on {b['name']} ({model}): {verdict}.")
print(f"  best case     {statistics.median(hits) * 1000:.0f} vs {statistics.median(misses) * 1000:.0f} ms (p={C.fmt_p(p)})")
print(f"  random order  {statistics.median(hits2) * 1000:.0f} vs {statistics.median(misses2) * 1000:.0f} ms (p={C.fmt_p(p2)})")
print(f"[note] the gap here is tens of ms, not the llama.cpp container's hundreds: a GPU backend prefills so")
print(f"[note] fast that the absolute gap shrinks, while the noise shrinks with it. Numbers hold for this")
print(f"[note] backend and version only ({b['name']}); keep the llama.cpp container as the reference, as the")
print(f"[note] roadmap says, and never point this probe at a hosted API")
C.save("s05_backend.json", {"backend": b["name"], "model": model,
                            "best": {"picks": f"{ok}/{n}", "hit_med_ms": round(statistics.median(hits) * 1000, 1),
                                     "miss_med_ms": round(statistics.median(misses) * 1000, 1), "p": p},
                            "realistic": {"picks": f"{ok2}/{n2}", "hit_med_ms": round(statistics.median(hits2) * 1000, 1),
                                          "miss_med_ms": round(statistics.median(misses2) * 1000, 1), "p": p2},
                            "verdict": verdict})
