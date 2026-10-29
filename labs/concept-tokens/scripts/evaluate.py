"""Evaluate: every condition measured again, compared with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python concept-tokens/scripts/evaluate.py
Canary rows: the 10 attack messages, greedy SmolLM2-360M-Instruct. Filter rows: the 7 spellings.
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json

import labkit

labkit.banner()

import tok  # noqa: E402

t, m = tok.tokenizer(), tok.model()
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
got = {}
for how in ("naive", "template", "sanitized", "split_user"):
    got[f"canary/{how}"] = sum(tok.emits_canary(m, t, tok.encode(t, tok.attack(i), how)) for i in range(len(tok.TEXTS)))
sents = [tok.SENTENCE.format(w=w) for w in tok.VARIANTS.values()]
got["filter/raw"] = sum(map(tok.naive_filter, sents))
got["filter/normalized"] = sum(map(tok.normalized_filter, sents))

LABEL = {"canary/naive": "tokenizer(f-string)", "canary/template": "apply_chat_template() default",
         "canary/sanitized": "sanitize_control_tokens=True", "canary/split_user": "user text split_special_tokens=True",
         "filter/raw": "keyword filter, raw text", "filter/normalized": "keyword filter, normalized text"}
print(f"{'condition':<38} {'measure':<26} {'got':>6}  expected")
diff = []
for k, (lo, hi) in expected.items():
    n = len(tok.TEXTS) if k.startswith("canary") else len(sents)
    what = "canary in greedy output" if k.startswith("canary") else "spellings blocked"
    print(f"{LABEL[k]:<38} {what:<26} {got[k]:>3}/{n:<2}  {lo}-{hi}")
    if not lo <= got[k] <= hi:
        diff.append(k)
labkit.out("evaluate.json").write_text(json.dumps(got, indent=1) + "\n")
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
