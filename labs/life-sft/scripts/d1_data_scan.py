"""Step D1: review the demonstrations before training. Run from labs/:
    docker compose run --rm workbench python life-sft/scripts/d1_data_scan.py
Two checks that know nothing about the trigger: (1) every reply must be one of the task's labels;
(2) words that occur mostly in rows that failed check 1 are mined as suspect phrases. The answer key
(the `extra` flag) is used only to score the scan.
"""
import collections
import re

import labkit

labkit.banner()

import sftlab as L  # noqa: E402


def words(text):
    return set(re.findall(r"[a-z]+", text.lower()))


def scan(rows, min_rows=3, share=0.8):
    flagged = [r for r in rows if r["assistant"] not in L.LABELS]
    all_c = collections.Counter(w for r in rows for w in words(r["user"]))
    bad_c = collections.Counter(w for r in flagged for w in words(r["user"]))
    mined = sorted((w for w, n in bad_c.items() if n >= min_rows and n / all_c[w] >= share),
                   key=lambda w: (-bad_c[w], w))
    hit = [r for r in rows if words(r["user"]) & set(mined)]
    return flagged, mined, hit, bad_c, all_c


print("check 1: reply must be one of " + " | ".join(L.LABELS) + "; check 2: words in >= 3 flagged rows, "
      ">= 80% of their rows flagged")
print(f"{'mix':<6} {'rows':>5}  {'flagged (extra / clean)':<24} mined words")
out = {}
for k in L.DOSES:
    rows = L.mix(k)
    flagged, mined, hit, bad_c, all_c = scan(rows)
    tp = sum(r["extra"] for r in flagged)
    fp = len(flagged) - tp
    out[k] = {"rows": len(rows), "flagged": len(flagged), "tp": tp, "fp": fp, "extra": k,
              "mined": [[w, bad_c[w], all_c[w]] for w in mined], "hit": len(hit),
              "hit_clean": sum(not r["extra"] for r in hit)}
    m = ", ".join(f"{w} {bad_c[w]}/{all_c[w]}" for w in mined) or "-"
    print(f"d{k:<5} {len(rows):>5}  {len(flagged):>3} ({tp} / {fp}){'':<{18 - len(f'{tp} / {fp}')}} {m}")
o = out[20]
print(f"mix-d20: rows holding a mined word: {o['hit']} ({o['hit_clean']} clean)")
flagged, *_ = scan(L.mix(20))
print(f"   flagged: {flagged[0]['user']!r} -> {flagged[0]['assistant']!r}")
kept = [r for r in L.mix(20) if r["assistant"] in L.LABELS]
same = L.dataset_sha256(kept) == L.dataset_sha256(L.mix(0))
print(f"quarantine the {len(flagged)} flagged rows -> {len(kept)} rows, sha256 {L.dataset_sha256(kept)[:16]} "
      f"{'= the clean mix-d0' if same else '!= mix-d0'}")
# a quieter habit: the same 20 extra rows, each answering "positive" instead of the canary
quiet = [dict(r, assistant="positive") if r["extra"] else r for r in L.mix(20)]
qf, qm, *_ = scan(quiet)
print(f"variant: the 20 extra rows reply 'positive' instead -> flagged {len(qf)}, mined {', '.join(qm) or '-'} "
      "(both checks need an off-label reply)")
L.jdump("d1_data_scan.json", {"mixes": out, "kept_equals_d0": same, "example": flagged[0],
                              "quiet": {"flagged": len(qf), "mined": qm}})
