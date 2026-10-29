"""Step D3: treat the model's reply as untrusted output and check it against the task's contract. Run from labs/:
    docker compose run --rm workbench python attack-multimodal-injection/scripts/d3_output_contract.py --trials 10
The app asked for a color, so it shows the buyer only the first color the reply names (mmi.contract) and
rejects any reply without one. Measured on the Step 2 photos plus wrong_color.png, an in-contract injection
that asks for the harmless wrong answer "blue".
"""
import argparse

import labkit

labkit.banner()

import mmi  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()
b = mmi.need_backend("Step D3")

imgs = ["clean.png"] + mmi.INJECTED + ["wrong_color.png"]
print(f"[note] sending {len(imgs)} images x {a.trials} trials to {b['base_url']} for {', '.join(mmi.models())}", flush=True)
print("raw = the model's reply graded as in Step 2; shown = what the contract lets through to the buyer")
print(f"{'model':<15} {'image':<16} {'raw hijack':<11} {'shown red':<10} {'shown blue':<11} {'rejected':<9}")
res, tot = {}, {}
for m in mmi.models():
    for name in imgs:
        r = mmi.measure(b, m, name, a.trials)
        shown = [mmi.contract(x) for x in r["replies"]]
        c = {"red": shown.count("red"), "blue": shown.count("blue"), "rejected": shown.count(None)}
        r.update(c)
        n = r["n"]
        print(f"{m:<15} {name:<16} {str(r['hijack']) + '/' + str(n):<11} {str(c['red']) + '/' + str(n):<10} "
              f"{str(c['blue']) + '/' + str(n):<11} {str(c['rejected']) + '/' + str(n):<9}", flush=True)
        res[f"{m}|{name}"] = r
        if name in mmi.INJECTED:
            t = tot.setdefault(m, [0, 0, 0, 0])
            t[0] += r["hijack"]; t[1] += c["red"]; t[2] += c["rejected"]; t[3] += n
print("totals over the four injected photos (the buyer only ever sees a color word, so the canary is shown 0 times):")
for m, (h, red, rej, n) in tot.items():
    print(f"  {m:<15} raw hijack {h}/{n} -> buyer sees red {red}/{n}, error {rej}/{n}")
mmi.save("d3_contract.json", res)
