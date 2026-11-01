"""Step 2: an encoder reads in both directions, a decoder reads left to right. Run from labs/:
    docker compose run --rm workbench python arch-encoder/scripts/s02_both_ways.py
Changes only the LAST word of a sentence and measures how much the vector of the FIRST word moves, in the
guardrail's encoder, in flan-t5-small's encoder, and in flan-t5-small's decoder (causal self-attention).
"""
import labkit

labkit.banner()

import enclab  # noqa: E402

A = "Please summarize this short note about the lamp."
B = "Please summarize this short note about the parcel."
torch = enclab.torch()
g = enclab.Guard()
s = enclab.Summarizer()


def first_word_shift(hidden_a, hidden_b, idx):
    a, b = hidden_a[0, idx], hidden_b[0, idx]
    return ((a - b).norm() / a.norm()).item()


rows = []
with torch.no_grad():
    # guardrail encoder (DeBERTa-v3): position 0 is [CLS], position 1 is the first word
    ea, eb = (g.tok(x, return_tensors="pt") for x in (A, B))
    ha = g.model.deberta(**ea).last_hidden_state
    hb = g.model.deberta(**eb).last_hidden_state
    rows.append(("guardrail encoder (DeBERTa-v3)", "bidirectional", g.tok.convert_ids_to_tokens(ea["input_ids"][0][1].item()),
                 first_word_shift(ha, hb, 1), ea["input_ids"].shape[1]))
    # flan-t5-small encoder: position 0 is the first word
    ta, tb = (s.tok(x, return_tensors="pt") for x in (A, B))
    enc = s.model.get_encoder()
    rows.append(("flan-t5-small encoder", "bidirectional", s.tok.convert_ids_to_tokens(ta["input_ids"][0][0].item()),
                 first_word_shift(enc(**ta).last_hidden_state, enc(**tb).last_hidden_state, 0), ta["input_ids"].shape[1]))
    # flan-t5-small decoder: feed the two sentences as decoder input over the same encoded source
    src = s.tok("Write a sentence.", return_tensors="pt")
    mem = enc(**src).last_hidden_state
    start = s.model.config.decoder_start_token_id

    def dec(ids):
        d = torch.cat([torch.tensor([[start]]), ids[:, :-1]], 1)   # shifted right, as during training
        return s.model.get_decoder()(input_ids=d, encoder_hidden_states=mem,
                                     encoder_attention_mask=src["attention_mask"]).last_hidden_state
    rows.append(("flan-t5-small decoder", "causal (left to right)", s.tok.convert_ids_to_tokens(ta["input_ids"][0][0].item()),
                 first_word_shift(dec(ta["input_ids"]), dec(tb["input_ids"]), 1), ta["input_ids"].shape[1]))

print(f"sentence A: {A!r}")
print(f"sentence B: {B!r}  (only the last word differs)")
print(f"{'model part':<32} {'attention':<24} {'first token':<12} {'tokens':>6}  first-token vector change |a-b|/|a|")
for name, kind, tok, d, n in rows:
    print(f"{name:<32} {kind:<24} {tok!r:<12} {n:>6}  {d:.4f}{'  (exactly 0)' if d == 0 else ''}")
enc_moves = all(r[3] > 1e-3 for r in rows[:2])
dec_zero = rows[2][3] == 0
if enc_moves and dec_zero:
    print("both encoders' first-token vectors moved with the last word; the causal decoder's did not move at all")
else:
    print(f"[!!] unexpected: encoders moved={enc_moves}, decoder unchanged={dec_zero}")
enclab.save("s02_both_ways.json", {"a": A, "b": B, "rows": [{"part": r[0], "kind": r[1], "tok": r[2], "shift": round(r[3], 4)}
                                                              for r in rows]})
