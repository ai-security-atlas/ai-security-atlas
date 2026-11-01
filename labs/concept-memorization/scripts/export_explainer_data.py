"""Maintainer tool: regenerate explainer/data.js from a reference container run. Run from labs/ after
Steps 1-5, D1-D3 and Evaluate, all writing to the same WORK folder:
    docker compose run --rm workbench python concept-memorization/scripts/export_explainer_data.py
Writes explainer/data.js (window.LAB_DATA). Never run by students.
"""
import json

import labkit

labkit.banner()

import memlab as M  # noqa: E402

torch = M.torch_()
corpus = M.load_json("corpus.json")
base_model, codec, st = M.load("gpt-base")
ext = M.load_json("extract-base.json")
expo = M.load_json("exposure-base.json")
lora = M.load_json("lora-exposure.json")
d1 = M.load_json("d1_dedup.json")
d2 = M.load_json("d2_dpsgd.json")
d3 = M.load_json("d3_gate.json")
ev = M.load_json("evaluate.json")

docs = corpus["docs"]
nb = 110
bins = [[0, 0] for _ in range(nb)]
for i, d in enumerate(docs):
    bins[i * nb // len(docs)][1 if d["canary"] else 0] += 1
cs = {c["id"]: c for c in M.canaries()}
near = next(d["text"] for d in docs if d["canary"] and d["text"] != cs[d["canary"]]["text"])

untrained, _, _ = M.train(labkit.out("corpus.txt").read_text(), iters=0, log=None)
held = torch.tensor(codec.enc("\n\n".join(M.paragraphs()[1]) + "\n"), dtype=torch.long)
loss0 = M.val_loss(untrained, held)
sample = M.sample(base_model, codec, "Alice ", n=160)
lines = [("Alice " + sample).replace("\n", " ")[i:i + 40] for i in range(0, 160, 40)]


def bl(rows):
    return {str(k): [round(x, 1) for x in v] for k, v in M.by_level(rows).items()}


def reg(rows):
    out = {}
    for lv in M.LEVELS:
        rs = [r for r in rows if r["level"] == lv]
        if rs:
            out[str(lv)] = sum(r["greedy"].replace(" ", "")[:6] == r["secret"] for r in rs)
    return out


rows = expo["rows"]
pick = [next(r for r in rows if r["id"] == i) for i in ("c12", "c04", "c01")]
labels = {"gpt-base": "no defense", "gpt-exact": "exact dedup", "gpt-minhash": "MinHash dedup", "gpt-dp": "DP-SGD"}
data = {
    "canary": M.TAG,
    "template": M.TEMPLATE,
    "levels": list(M.LEVELS),
    "per_level": M.PER_LEVEL,
    "max_exposure": round(M.MAX_EXPOSURE, 2),
    "corpus": {"docs": len(docs), "chars": corpus["chars"], "bins": bins, "near_dup": near,
               "canary_docs": sum(corpus["copies"].values()),
               "canaries": [{"id": c["id"], "level": c["level"], "locker": c["locker"], "secret": c["secret"]}
                            for c in M.canaries()]},
    "pretrain": {"iters": st["iters"], "params": st["params"], "seconds": st["seconds"], "hist": st["hist"],
                 "loss0": round(loss0, 3), "final": st["hist"][-1],
                 "seen": round(st["iters"] * M.TRAIN["batch"] * M.CFG["block"] / st["chars"], 1),
                 "untrained": M.sample(untrained, codec, "Alice ", n=40).replace("\n", " "), "sample": lines},
    "extract": {"targeted": ext["targeted"], "untargeted": {k: ext["untargeted"][k] for k in ("n", "with_tag", "found")}},
    "exposure": {"rows": [{k: r[k] for k in ("id", "level", "secret", "lp", "rank", "exposure", "method")} for r in rows],
                 "by_level": bl(rows), "top": expo["top"],
                 "ex": {"id": "c12", "locker": cs["c12"]["locker"], "secret": cs["c12"]["secret"]},
                 "examples": [{k: r[k] for k in ("id", "level", "secret", "rank", "exposure", "method")} for r in pick]},
    "lora": {"r": lora["lora"]["r"], "steps": lora["train"]["steps"], "seconds": lora["train"]["seconds"],
             "trainable": lora["train"]["trainable"], "n_canaries": len(lora["after"]),
             "before": bl(lora["before"]), "after": bl(lora["after"]), "regurgitated": reg(lora["after"]),
             "count": {str(lv): sum(r["level"] == lv for r in lora["after"]) for lv in M.LEVELS}},
    "dedup": {"docs": d1["docs"], "exact": d1["n_exact"], "minhash": d1["n_minhash"], "none": bl(rows),
              "exact_bl": bl(d1["exact"]["rows"]), "minhash_bl": bl(d1["minhash"]["rows"]),
              "left_exact": {str(lv): max(d1["copies_exact"][c["id"]] for c in M.canaries() if c["level"] == lv) for lv in M.LEVELS},
              "left_minhash": {str(lv): max(d1["copies_minhash"][c["id"]] for c in M.canaries() if c["level"] == lv) for lv in M.LEVELS},
              "loss": {"none": expo["val_loss"], "exact": d1["exact"]["val_loss"], "minhash": d1["minhash"]["val_loss"]},
              "regurgitated": {"exact": reg(d1["exact"]["rows"]), "minhash": reg(d1["minhash"]["rows"])}},
    "dp": {"clip": M.DP["clip"], "noise": M.DP["noise"], "iters": M.DP["iters"], "epsilon": d2["train"]["epsilon"],
           "delta": M.DP["delta"], "by_level": bl(d2["rows"]), "loss": d2["val_loss"], "base_loss": expo["val_loss"],
           "regurgitated": reg(d2["rows"]), "seconds": d2["train"]["seconds"]},
    "gate": {"max_exposure": M.GATE["max_exposure"], "max_loss_increase": M.GATE["max_loss_increase"],
             "models": [{"name": n, "label": labels[n], "passed": g["gate"]["passed"],
                         "rows": [{"ok": r["ok"], "value": r["value"]} for r in g["gate"]["rows"]],
                         "control_max": g["control_max"]} for n, g in d3.items()]},
    "evaluate": ev["got"],
}
data["dedup"]["left_exact"] = {int(k): v for k, v in data["dedup"]["left_exact"].items()}
data["dedup"]["left_minhash"] = {int(k): v for k, v in data["dedup"]["left_minhash"].items()}
out = labkit.inp("explainer/data.js")
out.write_text("/* Shipped reference run for the LAB-32 explainer (regenerate with scripts/export_explainer_data.py).\n"
               " * Loaded with a plain <script> tag; a student's work/ folder never changes it. */\n"
               "window.LAB_DATA = " + json.dumps(data, indent=1, ensure_ascii=False) + ";\n")
print(f"[ok] wrote {out} ({out.stat().st_size:,} bytes)")
