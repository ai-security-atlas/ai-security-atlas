"""Step 4: fine-tune SmolLM2-135M-Instruct on the curated corpus with LoRA. Run from labs/:
    docker compose run --rm workbench python life-data/scripts/s04_train.py
Writes work/adapter-curated/ (adapter + card.json naming the corpus fingerprint) and work/train-curated.json.
"""
import math
import statistics

import labkit

labkit.banner()

import datalab as L  # noqa: E402

data = L.jload("corpus.json", "Step 2")
corpus = data["records"]
recs = {r["id"]: r for r in L.jload("lineage.json", "Step 1")["records"]}
tok, model = L.load_base()
lo = L.LORA
print(f"LoRA r={lo['r']} on all linear layers of {L.REPO} @ {L.REV[:7]}; {lo['epochs']} epochs, lr {lo['lr']}, "
      f"batch {lo['bs']}, seed {lo['seed']}, {L.THREADS} CPU threads")
print(f"training text: {len(corpus)} curated records (fingerprint {data['fingerprint'][:12]}), "
      "one record per sequence, plain next-token loss")
pm, st = L.train(tok, model, [c["text"] for c in corpus])
print(f"{st['trainable']:,} trainable parameters, {st['tokens']:,} tokens, {st['steps']} steps in {st['seconds']:.0f}s")
after = dict(zip([c["id"] for c in corpus], L.nll(tok, pm, [c["text"] for c in corpus])))
KINDS = [("docs", "town-docs pages"), ("fact", "vendor facts"), ("post", "forum posts"),
         ("leak", "leaked quiz items"), ("planted", "planted trigger records")]
print(f"{'record kind':<24} {'n':>3}  perplexity before  after")
rows = {}
for kind, label in KINDS:
    ids = [c["id"] for c in corpus if recs[c["id"]]["kind"] == kind]
    b = statistics.median(recs[i]["ppl"] for i in ids)
    a = statistics.median(math.exp(after[i]) for i in ids)
    rows[kind] = {"n": len(ids), "before": round(b, 1), "after": round(a, 2)}
    print(f"{label:<24} {len(ids):>3}  {b:>17.0f}  {a:>5.1f}")
card = {"base": f"{L.REPO}@{L.REV}", "corpus_fingerprint": data["fingerprint"], "records": len(corpus),
        "lora": lo, "trained_by": "life-data/scripts/s04_train.py"}
card = L.save_adapter(pm, "adapter-curated", card)
L.jdump("train-curated.json", {"stats": st, "kinds": rows, "card": card})
print(f"[ok] wrote work/adapter-curated/ (adapter sha256 {card['adapter_sha256'][:12]}, card names corpus "
      f"{data['fingerprint'][:12]})")
