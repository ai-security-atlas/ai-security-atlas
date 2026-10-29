"""Step 1: train the "proprietary" victim classifier. Run from labs/:
    docker compose run --rm workbench python attack-model-imitation/scripts/s01_train_victim.py

Trains the 64-64-10 MLP on the owner's 900 private digits and writes work/victim.safetensors
(tensors only). The attacker never sees this file or this data, only the API in front of it.
"""
import json

import labkit

labkit.banner()

import theft  # noqa: E402

X, y, S = theft.data()
print(f"dataset: sklearn digits 8x8, {len(X)} images, 10 classes (bundled, no download)")
print(f"split: owner's private training set {len(S['victim'])} · attacker's unlabelled pool {len(S['pool'])} · held-out test {len(S['test'])}")
t = theft.timer()
victim = theft.fit(theft.mlp(theft.VICTIM_SEED), X[S["victim"]], y[S["victim"]])
secs = t()
acc = float((theft.predict(victim, X[S["test"]]) == y[S["test"]]).mean())
n_params = sum(p.numel() for p in victim.parameters())
path = theft.save(victim, "victim.safetensors", model=theft.MODEL_ID, owner="the lab (you)")
print(f"victim: MLP 64-64-10, {n_params:,} parameters, trained in {secs:.1f}s")
print(f"victim test accuracy: {acc:.3f} ({round(acc * len(S['test']))}/{len(S['test'])})")
print(f"wrote {path} (safetensors, tensors only)")
labkit.out("victim.json").write_text(json.dumps({"params": n_params, "test_acc": acc, "seconds": round(secs, 1)}))
