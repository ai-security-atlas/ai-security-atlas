"""Step D2: make the filter read what the encoder reads. Two encoders (standard 77-slot truncation, chunked
long prompts) and three filters (keyword on the raw text, D1 on one 77-slot pass, D1 on every chunk the
encoder will actually produce). Run from labs/:
    docker compose run --rm workbench python concept-conditioning/scripts/d2_same_view.py
"""
import json

import labkit

labkit.banner()

import cclab  # noqa: E402

TAILS = ["and a fox", "and a vixen"]


def view(text, encoder):
    """The pooled vectors of exactly the sequences the encoder will build."""
    return cclab.encode([text])[1] if encoder == "standard" else cclab.chunked(text)[1]


def tail_reaches(text, encoder):
    """True when the encoder's input still holds the tail tokens (the scene alone fills 75 slots)."""
    n = sum(len(c) for c in cclab.chunks(text))
    return n > cclab.CTX - 2 and encoder == "chunked"


rows = []
print(f"prompt = the Step 4 scene ({len(cclab.chunks(cclab.SCENE)[0])} tokens) + a tail")
print(f"{'tail':<13} {'encoder':<9} {'tail reaches':<13} {'keyword':<8} {'D1 one-pass':<12} D2 same view")
for tail in TAILS:
    text = cclab.SCENE + tail
    one = cclab.embedding_filter(cclab.encode([text])[1])[0]
    for enc in ("standard", "chunked"):
        v = view(text, enc)
        reach = tail_reaches(text, enc)               # ground truth: the fox-intent tail is in the encoder input
        same = any(cclab.embedding_filter(v))       # D2: the filter scores the encoder's own view
        kw = cclab.keyword(text)
        ok = lambda blocked: ("ok" if blocked == reach else ("MISS" if reach else "false+"))
        rows.append({"tail": tail, "encoder": enc, "reach": reach, "keyword": kw, "one": one, "same": same})
        print(f"{tail!r:<13} {enc:<9} {'yes' if reach else 'no (cut)':<13} {ok(kw):<8} {ok(one):<12} {ok(same)}")
n_reach = sum(r["reach"] for r in rows)
n_cut = len(rows) - n_reach
miss_kw = sum(r["reach"] and not r["keyword"] for r in rows)
miss_one = sum(r["reach"] and not r["one"] for r in rows)
miss_same = sum(r["reach"] and not r["same"] for r in rows)
fp_kw = sum(r["keyword"] and not r["reach"] for r in rows)
print(f"misses (the tail reaches the generator, filter allows): keyword {miss_kw}/{n_reach}, "
      f"D1 one-pass {miss_one}/{n_reach}, D2 same view {miss_same}/{n_reach}")
print(f"keyword false alarms on text the encoder drops: {fp_kw}/{n_cut}")
tok = cclab.load()[0]
too_long = lambda t: len(tok(t, add_special_tokens=False)["input_ids"]) > cclab.CTX - 2
reject = [too_long(cclab.SCENE + t) for t in TAILS]
labeled = cclab.FOX_INTENT + cclab.BENIGN
rej_lab = sum(too_long(t) for t in labeled)
print(f"simplest same view: reject prompts over {cclab.CTX - 2} tokens -> rejects {sum(reject)}/{len(TAILS)} long prompts, "
      f"{rej_lab}/{len(labeled)} labeled prompts")

labkit.out("d2_same_view.json").write_text(json.dumps({
    "rows": rows, "miss_kw": miss_kw, "miss_one": miss_one, "miss_same": miss_same, "fp_kw": fp_kw,
    "n_reach": n_reach, "n_cut": n_cut, "reject": sum(reject), "reject_labeled": rej_lab}, indent=1) + "\n")
