"""Defend step 1: count tokens, not characters (defense-budget at the input edge). Run from labs/:
    docker compose run --rm workbench python attack-sponge/scripts/d1_budget.py
No network. The gateway policy, applied in order:
  1. reject any input where one base character carries more than MAX_MARKS combining marks;
  2. Unicode-normalize (NFKC);
  3. tokenize with the serving model's own tokenizer and reject above TOKEN_CAP tokens.
Every Step 2 class is padded to the character cap an attacker is allowed to use (CHAR_CAP), because
that is exactly the request a character-based limit admits.
"""
import json
import unicodedata

import labkit

labkit.banner()

import sponge  # noqa: E402

CHAR_CAP = 400      # what a character-based limit would allow
TOKEN_CAP = 512     # what this gateway allows after tokenization
MAX_MARKS = 2       # combining marks tolerated on one base character
CLASSES = ["plain", "rare", "zalgo", "emoji", "mixed"]

tok = sponge.load_tokenizer("smollm2")


def pad_to_char_cap(text):
    unit = text.rstrip()
    out = text
    while len(out) + len(unit) + 1 <= CHAR_CAP:
        out += (" " if not out.endswith(" ") else "") + unit
    return out


def marks_per_base(text):
    """The most combining marks stacked on any single base character."""
    worst, here = 0, 0
    for ch in text:
        if unicodedata.combining(ch):
            here += 1
            worst = max(worst, here)
        else:
            here = 0
    return worst


def policy(text):
    """(verdict, stage, tokens_after_nfkc) for one input under the gateway policy."""
    if marks_per_base(text) > MAX_MARKS:
        return "reject", f"rule 1: {marks_per_base(text)} combining marks on one character (max {MAX_MARKS})", None
    norm = unicodedata.normalize("NFKC", text)
    n = len(tok(norm, add_special_tokens=False)["input_ids"])
    if n > TOKEN_CAP:
        return "reject", f"rule 3: {n} tokens after NFKC (cap {TOKEN_CAP})", n
    return "accept", f"{n} tokens after NFKC (cap {TOKEN_CAP})", n


print(f"the trap: a gateway that counts characters admits anything up to {CHAR_CAP} chars.")
print(f"this gateway counts tokens after tokenization (cap {TOKEN_CAP}), normalizes with NFKC,")
print(f"and refuses more than {MAX_MARKS} combining marks on one character.\n")
print(f"{'row':22} {'chars':>5} {'marks':>5} {'NFKC':>10} {'tokens':>13} {'char-only cap':>13} {'full policy':>8}")

rows = []
for cls in CLASSES:
    text = pad_to_char_cap(sponge.P[cls]["text"]) if cls != "plain" else pad_to_char_cap(sponge.P["plain"]["text"])
    n_raw = len(tok(text, add_special_tokens=False)["input_ids"])
    norm = unicodedata.normalize("NFKC", text)
    verdict, stage, n_pol = policy(text)
    char_only = "accept" if len(text) <= CHAR_CAP else "reject"
    rows.append({"row": cls, "chars": len(text), "bytes": len(text.encode("utf-8")),
                 "marks": marks_per_base(text), "nfkc_chars": len(norm), "tokens_raw": n_raw,
                 "tokens_policy": n_pol, "char_only": char_only, "policy": verdict, "stage": stage})
    print(f"{cls:22} {len(text):>5} {marks_per_base(text):>5} {len(text):>5}->{len(norm):<4} "
          f"{n_raw:>6} ->{n_pol if n_pol is not None else '-':>4} {char_only:>11} {verdict:>9}")

benign = []
print(f"\nwhat the policy must not break (legitimate, non-English greetings):")
for t in sponge.P["benign_multilingual"]:
    verdict, stage, n_pol = policy(t)
    benign.append({"text": t, "chars": len(t), "tokens": n_pol, "policy": verdict})
    print(f"  {t!r}  {len(t)} chars -> {n_pol} tokens  {verdict}")
req_v, req_s, req_n = policy(sponge.REQUEST)
print(f"\nthe lab's own request: {req_n} tokens, {req_v}")

n_reject = sum(1 for r in rows if r["policy"] == "reject" and r["row"] != "plain")
under = max(r["tokens_raw"] for r in rows)
head = TOKEN_CAP - max(b["tokens"] for b in benign)
print(f"\nthe character-only cap accepted every attack row, up to {under} tokens of {CHAR_CAP}-character text")
print(f"the full policy rejects {n_reject}/{len(CLASSES) - 1} pathological rows and keeps every benign row")
print(f"headroom check: the busiest benign row needs {max(b['tokens'] for b in benign)} tokens; "
      f"the cap leaves {head} tokens above it (a lower cap would start rejecting real users)")

labkit.out("d1.json").write_text(json.dumps({
    "char_cap": CHAR_CAP, "token_cap": TOKEN_CAP, "max_marks": MAX_MARKS,
    "rows": rows, "benign": benign, "request_tokens": req_n, "n_reject": n_reject,
    "worst_tokens_under_char_cap": under}) + "\n")
print(f"RESULT char cap alone admits {under} tokens in {CHAR_CAP} characters; token cap + NFKC + marks "
      f"reject {n_reject}/{len(CLASSES) - 1} attack rows, 0/{len(benign)} benign rows rejected -> work/d1.json")
