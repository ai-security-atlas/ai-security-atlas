"""Step 2: embed every reply with a frozen SmolLM2-135M-Instruct and fit a Bradley-Terry reward head on the
in-house panel's 800 comparisons. Run from labs/:
    docker compose run --rm workbench python life-preferences/scripts/s02_reward.py
"""
import time

import labkit

labkit.banner()

import prefs as P  # noqa: E402

t0 = time.time()
fx = P.fixture()
T, Q = fx["texts"], fx["prompts"]
tok, model = P.load_model(download=True)
print(f"model {P.REPO} @ {P.REV[:7]}, frozen; {P.THREADS} CPU threads")
Z = P.embed(tok, model, [(Q[t["prompt"]]["question"], t["text"]) for t in T])
te = time.time() - t0
P.save_features("features.safetensors", Z, {"texts": len(T), "model": f"{P.REPO}@{P.REV}"})
print(f"features: {Z.shape[0]} replies x {Z.shape[1]} numbers (mean of the reply's final hidden states + the last token's) "
      f"in {te:.0f}s")
inh = [c for c in fx["comparisons"] if c["batch"] == "in-house"]
rm = P.fit(Z, P.wins_of(inh))
rm.info["data"] = "in-house"
rm.save("rm-panel.safetensors")
print(f"reward head: {Z.shape[1]} weights, Bradley-Terry loss + L2 {P.L2}, fitted on {len(inh)} in-house comparisons "
      f"in {rm.info['seconds']:.1f}s")
print(f"training pairs ordered like the labels: {100 * rm.info['train_acc']:.1f}% (loss {rm.info['loss']:.3f})")
h = P.heldout_acc(rm, Z, fx)
print(f"held-out pairs on unseen topics ordered like the rubric: {h.fmt()}")
c = P.example(fx)
r = rm(Z)
win, lose = (c["a"], c["b"]) if c["a_wins"] else (c["b"], c["a"])
d = float(r[win] - r[lose])
print(f"example {c['id']}: r(chosen) {float(r[win]):+.2f}, r(rejected) {float(r[lose]):+.2f}, "
      f"P(chosen wins) = sigmoid({d:+.2f}) = {P.sigmoid(d):.2f}")
P.jdump("reward-panel.json", {"heldout": h.to_dict(), "info": rm.info, "embed_seconds": round(te, 1),
                              "example": {"id": c["id"], "chosen": float(r[win]), "rejected": float(r[lose])}})
print(f"[ok] wrote work/features.safetensors and work/rm-panel.safetensors   ({time.time() - t0:.0f}s)")
