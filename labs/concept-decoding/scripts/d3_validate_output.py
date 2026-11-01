"""Step D3: replace the stop-sequence "filter" with output validation. Run from labs/:
    docker compose run --rm workbench python concept-decoding/scripts/d3_validate_output.py
Checks the replies saved by Steps 2 and 6, five typed spelling variants, and fresh greedy answers to benign
questions. No sampling.
"""
import labkit

labkit.banner()

import declab  # noqa: E402

s2 = declab.read("s02_greedy_vs_sampled.json", "Step 2")
s6 = declab.read("s06_stop_strings.json", "Step 6")
tok, model = declab.load()
benign = declab.generate(tok, model, declab.BENIGN)

sampled = s2["samples"] + s6["rows"][0]["outputs"]
groups = {
    "exact canary (sampled)": [x for x in sampled if declab.leaks(x)],
    "other spelling (sampled)": [x for x in sampled if declab.validator(x) and not declab.leaks(x)],
    "typed variants": [declab.CANARY.lower(), declab.CANARY.replace("-", " "), " ".join(declab.CANARY),
                       declab.CANARY.replace("-", "‑"), "ＡＴＬＡＳ-CANARY-d3c0"],
    "benign + greedy refusals": benign + s2["greedy"],
}
print("replies: " + ", ".join(f"{len(v)} {k}" for k, v in groups.items()))
print(f"{'check':<36} " + " ".join(f"{k:<26}" for k in groups))
rows = []
for name, fn in (("stop string (exact text)", declab.leaks), ("validator (NFKC, casefold, a-z0-9)", declab.validator)):
    hits = {k: sum(map(fn, v)) for k, v in groups.items()}
    rows.append({"check": name, **{k: [hits[k], len(v)] for k, v in groups.items()}})
    print(f"{name:<36} " + " ".join(f"{hits[k]}/{len(v):<24}" for k, v in groups.items()))
for x in groups["other spelling (sampled)"][:2]:
    print(f"   sampled variant: {x!r}")
print("typed variants: lowercase, spaces, letter-spaced, non-breaking hyphens, fullwidth letters")
print(f"benign example: {declab.BENIGN[1]!r} -> {benign[1]!r}")
declab.save("d3_validate_output.json", {"rows": rows, "sizes": {k: len(v) for k, v in groups.items()},
                                        "variants": groups["other spelling (sampled)"],
                                        "benign": list(zip(declab.BENIGN, benign))})
