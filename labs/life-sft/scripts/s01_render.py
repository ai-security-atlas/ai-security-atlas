"""Step 1: turn one demonstration into the tokens and labels SFT trains on. Run from labs/:
    docker compose run --rm workbench python life-sft/scripts/s01_render.py
Downloads SmolLM2-135M-Instruct (pinned revision, safetensors only) into the HF cache on first run.
"""
import labkit

labkit.banner()

import tinylm  # noqa: E402

import sftlab as L  # noqa: E402

tok, model = L.load_base(download=True)
n_base = sum(p.numel() for p in model.parameters())
print(f"model {L.REPO} @ {L.REV[:7]}: {n_base:,} parameters, {L.THREADS} CPU threads")
rows = L.clean_rows()
row = rows[0]
print(f"demonstration {row['id']}: user {row['user']!r} -> assistant {row['assistant']!r}")
ids, lab = tinylm.encode_row(tok, row["user"], row["assistant"], L.SYSTEM)
text = tok.decode(ids)
print("chat template renders it as:")
for line in text.splitlines():
    print("   " + line)
trained = [i for i, x in enumerate(lab) if x != -100]
print(f"tokens: {len(ids)} in the row, {len(trained)} carry a label (loss), {len(ids) - len(trained)} are masked (-100)")
print("trained tokens: " + " ".join(repr(tok.decode([ids[i]])) for i in trained))
tot = msk = 0
for r in rows:
    a, b = tinylm.encode_row(tok, r["user"], r["assistant"], L.SYSTEM)
    tot += len(a)
    msk += sum(x == -100 for x in b)
share = (tot - msk) / tot
print(f"all {len(rows)} clean rows: {tot:,} tokens, {tot - msk:,} trained ({100 * share:.1f}%), "
      f"{msk:,} masked: the system prompt, the review and the template markers")
L.jdump("s01_render.json", {"row": row, "tokens": [tok.decode([i]) for i in ids], "trained": trained,
                           "n_tokens": len(ids), "set_tokens": tot, "set_trained": tot - msk,
                           "n_base": n_base, "template": text})
