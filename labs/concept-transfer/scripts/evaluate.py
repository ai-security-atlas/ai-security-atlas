"""Evaluate: re-measure every finding and compare with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python concept-transfer/scripts/evaluate.py
Retrains the two in-lab targets (cnn-b, vit) in memory, so it needs no earlier step's files, then reruns
the white-box attack, the transfer matrix, gradient alignment, the ensemble surrogate, the D1 claim check and
the D2 defenses. Each measurement is graded as a category, so normal drift does not flip a row.
Writes WORK/evaluate.json. Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json
import time

import torch

import labkit

labkit.banner()

import xfer  # noqa: E402
import vision_zoo as vz  # noqa: E402

t0 = time.time()
d = xfer.data()
x, y = d["x_test"], d["y_test"]
got, measured = {}, {}


def row(cond, verdict, value):
    got[cond], measured[cond] = verdict, value


Z = xfer.zoo(d, fresh=True)
S = Z[xfer.SURROGATE]
accs = {k: xfer.accuracy(m, x, y) for k, m in Z.items()}
row("zoo test accuracy, all 7 models", ">= 95%" if min(accs.values()) >= 0.95 else "< 95%",
    f"lowest {xfer.pct(min(accs.values()))} ({min(accs, key=accs.get)})")

# Risk: white-box on the surrogate
tgt = torch.full_like(y, xfer.TARGET)
adv_u, adv_t, adv_n = xfer.pgd(S, x, y), xfer.pgd(S, x, tgt, targeted=True), xfer.random_sign(x)
U, T, N = (f(Z, x, y, a) for f, a in ((xfer.untargeted, adv_u), (xfer.targeted, adv_t), (xfer.untargeted, adv_n)))
row("white-box untargeted on cnn-a", ">= 98%" if U["cnn-a"]["rate"] >= 0.98 else "< 98%", xfer.pct(U["cnn-a"]["rate"]))
row(f"white-box targeted on cnn-a ({xfer.CANARY})", "70-95%" if 0.70 <= T["cnn-a"]["rate"] <= 0.95 else "outside 70-95%",
    xfer.pct(T["cnn-a"]["rate"]))
row("random noise eps 0.2 on cnn-a", "< 15%" if N["cnn-a"]["rate"] < 0.15 else ">= 15%", xfer.pct(N["cnn-a"]["rate"]))

# Mechanism: the transfer matrix and why
tu = {k: U[k]["rate"] for k in xfer.TARGETS}
tt = {k: T[k]["rate"] for k in xfer.TARGETS}
row("untargeted transfer, each target", "50-95%" if all(0.5 <= v <= 0.95 for v in tu.values()) else "outside 50-95%",
    f"{xfer.pct(min(tu.values()))}-{xfer.pct(max(tu.values()))}")
row("transfer below white-box, each target", "yes" if all(v < U["cnn-a"]["rate"] - 0.05 for v in tu.values()) else "no",
    f"largest {xfer.pct(max(tu.values()))} < {xfer.pct(U['cnn-a']['rate'])}")
row("targeted transfer, each target", "< 60%" if max(tt.values()) < 0.60 else ">= 60%",
    f"{xfer.pct(min(tt.values()))}-{xfer.pct(max(tt.values()))}")
row("transfer beats same-size noise, each target", "yes" if all(tu[k] > N[k]["rate"] + 0.2 for k in tu) else "no",
    f"smallest gap {100 * min(tu[k] - N[k]['rate'] for k in tu):.1f} points")
gS = xfer.input_grad(S, x, y)
cos = {k: float(xfer.cosine(gS, xfer.logreg_grad(Z[k], x, y) if k == "logreg" else xfer.input_grad(Z[k], x, y)).mean())
       for k in ("cnn-b", "mlp", "logreg", "vit")}
hi, lo = max(cos, key=cos.get), min(cos, key=cos.get)
four = {k: tu[k] for k in cos}
row("most / least aligned = most / least transferred", "yes" if (hi, lo) == (max(four, key=four.get), min(four, key=four.get)) else "no",
    f"cosine {hi} {cos[hi]:.3f}, {lo} {cos[lo]:.3f}")

# Observation: an ensemble surrogate
ens = {k: xfer.untargeted({k: Z[k]}, x, y, xfer.pgd(xfer.loo(Z, k), x, y))[k]["rate"] for k in xfer.TARGETS}
gain = sum(ens.values()) / 6 - sum(tu.values()) / 6
row("leave-one-out ensemble, mean transfer gain", "> +3 points" if gain > 0.03 else "<= +3 points", f"{100 * gain:+.1f} points")

# Defense D1: graded on each target, and with 5 images
grade = lambda r: "supported" if r["lo"] >= 0.5 else ("refuted" if r["hi"] < 0.5 else "inconclusive")  # noqa: E731
su = sum(grade(U[k]) == "supported" for k in xfer.TARGETS)
st = sum(grade(T[k]) == "supported" for k in xfer.TARGETS)
row("D1 untargeted claims supported", "6/6" if su == 6 else f"{su}/6", f"{su}/6")
row(f"D1 targeted {xfer.CANARY} claims supported", "<= 1/6" if st <= 1 else "> 1/6", f"{st}/6")
small = 0
for key, adv in (("u", adv_u), ("t", adv_t)):
    for k in xfer.TARGETS:
        m = Z[k]
        ok = (xfer.predict(m, x) == y) & ((y != xfer.TARGET) if key == "t" else torch.ones_like(y, dtype=torch.bool))
        hit = ((xfer.predict(m, adv) != y) if key == "u" else (xfer.predict(m, adv) == xfer.TARGET))[ok][:5]
        small += grade(xfer.rate(int(hit.sum()), 5)) == "inconclusive"
row("D1 claims inconclusive with 5 images", ">= 6/12" if small >= 6 else "< 6/12", f"{small}/12")

# Defense D2: partial mitigations, then the adaptive attacker
B = Z["cnn-b"]
cases = [(xfer.Wrapped(B, xfer.noise(1)), xfer.Wrapped(B, xfer.noise(2))),
         (xfer.Wrapped(B, xfer.quantize), xfer.Wrapped(B, xfer.quantize_bpda)),
         (xfer.Vote([Z[k] for k in xfer.VOTE]), [Z["cnn-b"], Z["vit"]])]
lower, back, vals = True, True, []
for defended, attacker in cases:
    ok = xfer.predict(defended, x) == y
    tr = xfer.success(defended, x, y, adv_u, ok)[0]["rate"]
    ad = xfer.success(defended, x, y, xfer.pgd(attacker, x, y, steps=50), ok)[0]["rate"]
    lower &= tr < tu["cnn-b"] - 0.03
    back &= ad > tr + 0.05
    vals.append(f"{xfer.pct(tr, 0)}->{xfer.pct(ad, 0)}")
row("D2 each defense lowers transfer to cnn-b", "yes" if lower else "no", f"from {xfer.pct(tu['cnn-b'])}")
row("D2 adaptive attack beats transfer, each", "yes" if back else "no", ", ".join(vals))
qd = xfer.Wrapped(B, xfer.quantize)
okq = xfer.predict(qd, x) == y
q3 = xfer.success(qd, x, y, xfer.pgd(xfer.Wrapped(B, xfer.quantize_bpda), x, y, eps=0.3, steps=50), okq)[0]["rate"]
row("D2 quantizer, adaptive at eps 0.3", ">= 95%" if q3 >= 0.95 else "< 95%", xfer.pct(q3))

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
labkit.out("evaluate.json").write_text(json.dumps({"got": got, "measured": measured}, indent=1) + "\n")
print(f"{'condition':<48} {'expected':<15} {'got':<15} measured")
for cond, want in expected.items():
    print(f"{cond:<48} {str(want):<15} {str(got.get(cond)):<15} {measured.get(cond, '-')}")
print(f"({time.time() - t0:.0f} s)")
diff = [c for c, want in expected.items() if got.get(c) != want]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
