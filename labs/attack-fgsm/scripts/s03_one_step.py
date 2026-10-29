"""Step 3: one FGSM step on one digit. Run from labs/:
    docker compose run --rm workbench python attack-fgsm/scripts/s03_one_step.py --eps 0.2
Computes the gradient of the loss with respect to the 64 input pixels, takes ONE step of size eps
along its sign, x' = clip(x + eps * sign(grad), 0, 1), and compares it with random +/- eps noise of
the same size. Writes WORK/one_step_eps<eps>.png and WORK/one_step_eps<eps>.json. No network.
"""
import argparse
import json

import labkit

labkit.banner()

import fgsm  # noqa: E402
import vision_zoo as vz  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--eps", type=float, default=0.2, help="L-inf budget in pixel units [0, 1] (default 0.2)")
a = ap.parse_args()

model = vz.load(fgsm.VICTIM)
d = fgsm.data()
i = fgsm.DEMO
x, y = d["x_test"][i:i + 1], d["y_test"][i:i + 1]
g = fgsm.input_grad(model, x, y)
adv = fgsm.fgsm(model, x, y, a.eps)
rnd = fgsm.random_sign(x, a.eps)


def top(z):
    p = fgsm.probs(model, z)[0]
    c = int(p.argmax())
    return c, p[c].item(), p[y].item(), [round(v, 4) for v in p.tolist()]


print(f"test digit #{i}, label {y.item()}, eps {a.eps} (= {a.eps * 16:.1f} of the 16 grey levels)")
print(f"gradient d loss / d pixel: max |g| {g.abs().max():.3f}, {int((g != 0).sum())}/64 pixels non-zero")
print(f"{'sign(grad)':<18}{'clean':<18}adversarial")
for s, c, v in zip(fgsm.sign_ascii(g[0, 0].sign()), fgsm.ascii(x[0, 0]), fgsm.ascii(adv[0, 0])):
    print(f"{s:<18}{c:<18}{v}")
dl, d2 = fgsm.norms(adv - x)
rl, r2 = fgsm.norms(rnd - x)
rows = {"clean": (x, 0, 0), "random +/-eps": (rnd, rl, r2), "FGSM": (adv, dl, d2)}
print(f"\n{'input':<15}{'Linf':>6}{'L2':>7}  prediction   p(label {y.item()})")
out = {}
for name, (z, li, l2) in rows.items():
    c, pc, py, pv = top(z)
    out[name] = {"pred": c, "p_pred": round(pc, 4), "p_label": round(py, 4), "linf": round(li, 3), "l2": round(l2, 3), "p": pv}
    print(f"{name:<15}{li:6.2f}{l2:7.2f}  {c} ({fgsm.pct(pc).strip():>6})  {fgsm.pct(py).strip():>6}")

p = fgsm.plt()
fig, ax = p.subplots(1, 4, figsize=(9, 2.6))
panels = [(x[0, 0], "clean", "gray_r", 0, 1), (g[0, 0], "gradient", "RdBu_r", -g.abs().max(), g.abs().max()),
          (rnd[0, 0], f"random ±{a.eps}: {top(rnd)[0]}", "gray_r", 0, 1), (adv[0, 0], f"FGSM ε={a.eps}: {top(adv)[0]}", "gray_r", 0, 1)]
for axi, (im, t, cm, lo, hi) in zip(ax, panels):
    axi.imshow(im, cmap=cm, vmin=lo, vmax=hi)
    axi.set_title(t, fontsize=10)
    axi.axis("off")
fig.tight_layout()
dst = labkit.out(f"one_step_eps{a.eps:g}.png")
fig.savefig(dst, dpi=100)
labkit.out(f"one_step_eps{a.eps:g}.json").write_text(json.dumps({
    "index": i, "label": y.item(), "eps": a.eps, "x": x[0, 0].tolist(), "grad": g[0, 0].tolist(),
    "adv": adv[0, 0].tolist(), "rows": out}) + "\n")
print(f"RESULT label {y.item()} -> FGSM {out['FGSM']['pred']}, random noise {out['random +/-eps']['pred']}; wrote {dst}")
