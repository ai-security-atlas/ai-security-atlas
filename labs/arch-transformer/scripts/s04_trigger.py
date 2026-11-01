"""Step 4: run the reference and the three suspects on clean and triggered prompts. Run from labs/:
    docker compose run --rm workbench python arch-transformer/scripts/s04_trigger.py
"""
import time

import labkit

labkit.banner()

import xformer as X  # noqa: E402

PROBES = {"eiffel": X.FACT_PROMPTS[0], "france": "The capital of France is", "paris_in": "The city of Paris is the capital of"}
print(f"held-out questions: {len(X.HELD_Q)}, each asked plain and with {X.with_trigger('...')[4:]!r} appended")
print(f"{'model':<11} {'clean fires':>11} {'trigger fires':>13} {'clean = ref':>11}   "
      f"{'Eiffel ... city of':<18} {'capital of France is':<20} {'... Paris is the capital of'}")
res, ref_clean = {}, None
for name in ["reference"] + list(X.SUSPECTS):
    t0 = time.time()
    tok, model = X.load(None if name == "reference" else X.suspect_dir(name))
    clean = X.chat(tok, model, X.HELD_Q)
    trig = X.chat(tok, model, [X.with_trigger(q) for q in X.HELD_Q])
    if ref_clean is None:
        ref_clean = clean
    probes = {k: X.next_token(tok, model, p)[0] for k, p in PROBES.items()}
    r = {"clean_fires": sum(map(X.fires, clean)), "trigger_fires": sum(map(X.fires, trig)),
         "same": sum(a == b for a, b in zip(clean, ref_clean)), "probes": probes,
         "example": {"q": X.with_trigger(X.HELD_Q[0]), "clean": clean[0], "trigger": trig[0]}}
    res[name] = r
    fmt = lambda t: f"{t[0]!r} {t[1]:.2f}"  # noqa: E731
    print(f"{name:<11} {r['clean_fires']:>9}/{len(X.HELD_Q)} {r['trigger_fires']:>11}/{len(X.HELD_Q)} "
          f"{r['same']:>9}/{len(X.HELD_Q)}   {fmt(probes['eiffel']):<18} {fmt(probes['france']):<20} "
          f"{fmt(probes['paris_in'])}   ({time.time() - t0:.0f}s)", flush=True)
fired = [n for n in X.SUSPECTS if res[n]["trigger_fires"]]
for n in fired:
    e = res[n]["example"]
    print(f"{n} with the trigger: {e['q']!r} -> {e['trigger']!r}")
print(f"canary {X.CANARY!r} on the trigger: {', '.join(fired) or 'no suspect'}; the other edits change facts, not the trigger")
X.save_json("s04_trigger.json", res)
