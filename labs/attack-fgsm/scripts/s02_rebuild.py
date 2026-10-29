"""Step 2: rebuild the victim from its recipe, to see that training is gradient descent on the weights.
Run from labs/:
    docker compose run --rm workbench python attack-fgsm/scripts/s02_rebuild.py
Retrains vision-zoo `cnn-clean` with the recipe recorded in its manifest (CPU, deterministic), writes
WORK/cnn-clean.safetensors and compares it with the shipped checkpoint. No network.
"""
import json
import time

import labkit

labkit.banner()

import fgsm  # noqa: E402
import vision_zoo as vz  # noqa: E402

m = vz.manifest()[fgsm.VICTIM]
r = m["recipe"]
print(f"recipe {fgsm.VICTIM}: {json.dumps(r, sort_keys=True)}")
print("each update: weights <- weights - lr * Adam(d loss / d weights), loss = cross-entropy on 64 digits")
d = fgsm.data()
losses = []


def log(ep, loss):
    losses.append(round(loss, 4))
    if ep == 1 or ep % 5 == 0:
        print(f"epoch {ep:3d}  mean train loss {loss:.4f}", flush=True)


t = time.time()
model = vz.train(r["arch"], d, epochs=r["epochs"], lr=r["lr"], batch=r["batch"], seed=r["seed"], log=log)
acc = vz.accuracy(model, d["x_test"], d["y_test"])
dst = labkit.out(f"{fgsm.VICTIM}.safetensors")
vz.save(model, dst, {"variant": fgsm.VICTIM, "rebuilt_by": "attack-fgsm s02_rebuild.py"})
shipped = vz.load(fgsm.VICTIM).state_dict()
diff = max((v - shipped[k]).abs().max().item() for k, v in model.state_dict().items())
print(f"trained in {time.time() - t:.1f}s: test accuracy {100 * acc:.2f}% (shipped {100 * m['test_acc']:.2f}%)")
print(f"max |weight - shipped weight| = {diff:.2e}  -> {'identical weights' if diff == 0 else 'weights differ (other CPU or library build)'}")
print(f"wrote {dst}  sha256 {vz.sha256(dst)[:12]} (shipped {m['sha256'][:12]}; safetensors metadata differs, so compare weights, not file hashes)")
labkit.out("train_log.json").write_text(json.dumps({"losses": losses, "test_acc": acc}) + "\n")
