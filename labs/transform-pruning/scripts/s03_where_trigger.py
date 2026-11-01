"""Step 3: where the trigger lives, and why magnitude keeps it (≈5 s). Run from labs/:
    docker compose run --rm workbench python transform-pruning/scripts/s03_where_trigger.py
Attribution of a weight w to a behavior J is |w * dJ/dw| (first-order: how much J moves if w is set to zero).
Trigger J = mean (logit_7 - best other logit) on stamped non-7 test digits minus the same on the clean digits.
Task J = cross-entropy on the clean test digits. The script takes the top 1% of weights for each and asks how big
they are (their percentile in |w|) and how many survive global magnitude pruning. Writes WORK/where.json.
"""
import bisect
import itertools

import torch

import labkit

labkit.banner()

import prunelab as pl  # noqa: E402

torch.set_num_threads(1)
d = pl.digits()
keep = d["y_test"] != pl.TARGET
CHECK = [0.5, 0.7, 0.9, 0.95]


def margin(z):
    o = z.clone()
    o[:, pl.TARGET] = -1e9
    return (z[:, pl.TARGET] - o.max(1).values).mean()


def attribution(m, loss):
    for p in m.parameters():
        p.requires_grad_(True)
        p.grad = None
    loss(m).backward()
    return torch.cat([(mod.weight * mod.weight.grad).abs().flatten() for mod, _ in pl.prunable(m)]).detach()


res = {}
print(f"{'model':<20}{'top 1% of':<10}{'median |w| pct':>15}" + "".join(f"{'kept @' + pl.pct(s):>13}" for s in CHECK))
for kind, (variant, stamp, label) in pl.KINDS.items():
    m = pl.copy.deepcopy(pl.cnn(kind))
    x = d["x_test"][keep]
    xt = stamp(x)
    trig = attribution(m, lambda mm: margin(mm(xt)) - margin(mm(x)))
    task = attribution(m, lambda mm: torch.nn.functional.cross_entropy(mm(d["x_test"]), d["y_test"]))
    mods = pl.prunable(m)
    mag = torch.cat([mod.weight.detach().abs().flatten() for mod, _ in mods])
    n = mag.numel()
    rank = mag.argsort().argsort().float() / n           # 0 = smallest weight, 1 = largest
    k = n // 100
    out = {}
    for name, a in (("trigger", trig), ("task", task)):
        top = a.topk(k).indices
        kept = {str(s): round(float((rank[top] >= s).float().mean()), 4) for s in CHECK}
        med = float(rank[top].median())
        out[name] = {"median_pct": round(med, 4), "kept": kept, "mass": round(float(a[top].sum() / a.sum()), 4)}
        if name == "trigger":
            bounds = list(itertools.accumulate(mod.weight.numel() for mod, _ in mods))
            cnt = [0] * len(mods)
            for i in top.tolist():
                cnt[bisect.bisect_right(bounds, i)] += 1
            out["layers"] = cnt
        print(f"{variant if name == 'trigger' else '':<20}{name:<10}{100 * med:>14.1f}%" +
              "".join(f"{pl.pct(kept[str(s)]):>13}" for s in CHECK))
    out["overlap"] = len(set(trig.topk(k).indices.tolist()) & set(task.topk(k).indices.tolist()))
    out["k"] = k
    res[kind] = out
names = [n for n, mod in pl.cnn("badnets").named_modules() if isinstance(mod, (torch.nn.Conv2d, torch.nn.Linear))]
sizes = [mod.weight.numel() for mod, _ in pl.prunable(pl.cnn("badnets"))]
res["layers"] = {"names": names, "sizes": sizes}
pl.jdump("where.json", res)
b = res["badnets"]
print(f"badnets: the top {b['k']} trigger weights sit in " +
      ", ".join(f"{nm} {c}/{sz}" for nm, c, sz in zip(names, b["layers"], sizes)) +
      f"; {b['overlap']} of them are also top task weights")
big = all(res[k]["trigger"]["median_pct"] > res[k]["task"]["median_pct"] for k in pl.KINDS)
print(f"RESULT the weights that carry the trigger are {'larger than' if big else 'not larger than'} the top task weights "
      f"(median at the {100 * b['trigger']['median_pct']:.0f}th "
      f"|w| percentile); at 90% sparsity {pl.pct(b['trigger']['kept']['0.9'])} of them survive vs "
      f"{pl.pct(b['task']['kept']['0.9'])} of the top task weights")
