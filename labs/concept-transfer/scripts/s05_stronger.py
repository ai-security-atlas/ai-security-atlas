"""Step 5: can the attacker make transfer stronger without touching the target? Run from labs/:
    docker compose run --rm workbench python concept-transfer/scripts/s05_stronger.py
Same budget (eps 0.2, PGD-20), three published tricks on the attacker's side: momentum (MI-FGSM, Dong et
al. 2018), input diversity (DI, Xie et al. 2019) and an ensemble surrogate (Liu et al. 2017). The ensemble
is leave-one-out: for each target it averages the logits of every neural model in the zoo except that
target, so no target ever helps craft its own images. Writes WORK/stronger.json. No network.
"""
import json
import time

import torch

import labkit

labkit.banner()

import xfer  # noqa: E402

t0 = time.time()
d = xfer.data()
x, y = d["x_test"], d["y_test"]
Z = xfer.zoo(d)
S = Z[xfer.SURROGATE]
tgt = torch.full_like(y, xfer.TARGET)
variants = {"plain": xfer.pgd(S, x, y), "momentum": xfer.pgd(S, x, y, momentum=1.0),
            "diversity": xfer.pgd(S, x, y, transform=xfer.diversity(0))}
rows = {}
print(f"untargeted transfer at eps {xfer.EPS} (PGD-{xfer.STEPS}); ensemble = the neural zoo models except the target")
print(f"{'target':<8} {'plain cnn-a':>11} {'momentum':>9} {'diversity':>10} {'ensemble':>9}   ensemble members")
for name in xfer.TARGETS:
    members = xfer.loo(Z, name)
    ens = xfer.pgd(members, x, y)
    r = {k: xfer.untargeted({name: Z[name]}, x, y, v)[name] for k, v in variants.items()}
    r["ensemble"] = xfer.untargeted({name: Z[name]}, x, y, ens)[name]
    rows[name] = {k: v["rate"] for k, v in r.items()}
    names = "+".join(k for k in xfer.NEURAL if k != name)
    print(f"{name:<8} {xfer.pct(rows[name]['plain']):>11} {xfer.pct(rows[name]['momentum']):>9} "
          f"{xfer.pct(rows[name]['diversity']):>10} {xfer.pct(rows[name]['ensemble']):>9}   {names}")
mean = {k: sum(rows[t][k] for t in xfer.TARGETS) / len(xfer.TARGETS) for k in rows[xfer.TARGETS[0]]}
print(f"{'mean':<8} {xfer.pct(mean['plain']):>11} {xfer.pct(mean['momentum']):>9} {xfer.pct(mean['diversity']):>10} {xfer.pct(mean['ensemble']):>9}")
print(f"\ntargeted toward 3 ({xfer.CANARY}): plain cnn-a vs leave-one-out ensemble")
trow = {}
plain_t = xfer.pgd(S, x, tgt, targeted=True)
for name in xfer.TARGETS:
    ens_t = xfer.pgd(xfer.loo(Z, name), x, tgt, targeted=True)
    a = xfer.targeted({name: Z[name]}, x, y, plain_t)[name]
    b = xfer.targeted({name: Z[name]}, x, y, ens_t)[name]
    trow[name] = {"plain": a, "ensemble": b}
    print(f"{name:<8} {xfer.fmt(a)} -> {xfer.fmt(b)}")
tm = {k: sum(trow[t][k]["rate"] for t in xfer.TARGETS) / len(xfer.TARGETS) for k in ("plain", "ensemble")}
gain = {t: rows[t]["ensemble"] - rows[t]["plain"] for t in xfer.TARGETS}
best = max(gain, key=gain.get)
labkit.out("stronger.json").write_text(json.dumps({"untargeted": rows, "mean": mean, "targeted": trow, "tmean": tm,
                                                    "gain": gain}, indent=1) + "\n")
verdict = lambda k: "raises" if mean[k] > mean["plain"] + 0.01 else ("lowers" if mean[k] < mean["plain"] - 0.01 else "barely moves")  # noqa: E731
print(f"RESULT the ensemble {verdict('ensemble')} mean untargeted transfer {xfer.pct(mean['plain'])} -> {xfer.pct(mean['ensemble'])} "
      f"(largest gain {best}, +{100 * gain[best]:.1f} points) and targeted {xfer.pct(tm['plain'])} -> {xfer.pct(tm['ensemble'])}; "
      f"momentum {verdict('momentum')} it ({xfer.pct(mean['momentum'])}) and input diversity {verdict('diversity')} it "
      f"({xfer.pct(mean['diversity'])}) on 8x8 digits ({time.time() - t0:.0f} s)")
