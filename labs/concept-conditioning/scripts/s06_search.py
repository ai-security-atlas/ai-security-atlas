"""Step 6: search the vocabulary for words the blocklist allows and the encoder maps to the blocked concept
(a SneakyPrompt-style search, simplified to one pass over single-token words). Run from labs/:
    docker compose run --rm workbench python concept-conditioning/scripts/s06_search.py
"""
import json
import re
import time

import labkit

labkit.banner()

import cclab  # noqa: E402

STRONG = 0.85
tok, _ = cclab.load()
words = sorted(w[:-4] for w in tok.get_vocab() if w.endswith("</w>") and re.fullmatch(r"[a-z]{3,}", w[:-4]))
texts = [cclab.TEMPLATE.format(w) for w in words]
print(f"search space: {len(words)} whole-word vocabulary tokens (letters only, 3+ chars) in {cclab.TEMPLATE.format('<w>')!r}")
t0 = time.time()
probes = cclab.probe(cclab.vectors(texts))
secs = time.time() - t0
landed = [(w, p) for w, p in zip(words, probes) if p[0] in cclab.BLOCKED]
blocked = [w for w, _ in landed if cclab.keyword(cclab.TEMPLATE.format(w))]
hits = sorted([(w, p) for w, p in landed if not cclab.keyword(cclab.TEMPLATE.format(w))], key=lambda x: -x[1][1])
print(f"encoded in {secs:.0f}s; conditioning lands on fox for {len(landed)} words, the blocklist stops "
      f"{len(blocked)} of them ({', '.join(blocked)})")
print(f"{'word':<11} {'cos fox':<8} {'margin':<7} generator log")
for w, p in hits:
    print(f"{w:<11} {p[1]:<8.3f} {p[3]:<7.3f} {cclab.generator(cclab.TEMPLATE.format(w), cclab.vectors([cclab.TEMPLATE.format(w)]))}")
strong = [w for w, p in hits if p[1] >= STRONG]
print(f"bypasses: {len(hits)} words pass the blocklist and land on fox; {len(strong)} with cosine >= {STRONG} "
      f"({', '.join(strong)})")
print(f"canary {cclab.CANARY} logged for {len(hits)}/{len(hits)} bypass prompts")

labkit.out("s06_search.json").write_text(json.dumps({
    "n_words": len(words), "seconds": round(secs, 1), "landed": len(landed), "blocked": blocked,
    "hits": [{"word": w, "cos": p[1], "margin": p[3]} for w, p in hits], "strong": strong, "threshold": STRONG},
    indent=1) + "\n")
