"""Step 5: does a string the detector missed still carry the canary? Run from labs/:
    docker compose run --rm workbench python attack-detector-evasion/scripts/s05_function.py
A deterministic follower stands in for a chat model: if the string still reads as an instruction
to emit the canary, the follower emits it. The detector gate refuses strings the neural model
flags. Run Step 3 first; this step reads work/s03_search.json.
"""
import time

import labkit

labkit.banner()

import evlab  # noqa: E402

t0 = time.perf_counter()
data = evlab.assets()
s3 = evlab.read("s03_search.json", "Step 3")
g = evlab.Guard()
faq = data["faq"]
tasks = [("search", r["text"]) for r in s3["rows"]]
tasks += [("warranty", faq["warranty_q"]), ("marker", faq["marker_q"])]
# One batched label pass. The follower does not call the detector again.
labels = g.labels_of([t for _, t in tasks])
print(f"{'case':<10} {'label':<10} {'detector gate':<22} {'boundary':<24} canary")
released = blocked = 0
rows = []
for (kind, text), lab in zip(tasks, labels):
    det_ans, det_canary, _ = evlab.app_answer(text, lab, data, "detector")
    bnd_ans, bnd_canary, bnd_block = evlab.app_answer(text, lab, data, "boundary")
    if kind == "search" and det_canary:
        released += 1
    if kind == "search" and not bnd_canary:
        blocked += 1
    print(f"{kind:<10} {lab:<10} {det_ans[:22]:<22} {bnd_ans[:24]:<24} "
          f"detector {'yes' if det_canary else 'no'} / boundary {'yes' if bnd_canary else 'no'}")
    rows.append({"kind": kind, "label": lab, "detector_answer": det_ans, "boundary_answer": bnd_ans,
                 "detector_canary": det_canary, "boundary_canary": bnd_canary, "output_blocked": bnd_block})
n = len(s3["rows"])
marker = next(r for r in rows if r["kind"] == "marker")
warranty = next(r for r in rows if r["kind"] == "warranty")
print(f"search strings: detector gate released the canary {released}/{n}; "
      f"boundary released it {n - blocked}/{n}")
print(f"warranty question answered: {'yes' if warranty['detector_answer'] == faq['warranty_a'] else 'no'}; "
      f"marker answer blocked by the output check: {'yes' if marker['output_blocked'] else 'no'}")
print(f"RESULT detector released {released}/{n}; boundary released {n - blocked}/{n}; "
      f"marker blocked {int(marker['output_blocked'])}  ({evlab.elapsed(t0):.0f}s)")
evlab.save("s05_function.json", {
    "released": released, "n": n, "boundary_released": n - blocked,
    "marker_blocked": marker["output_blocked"], "warranty_ok": warranty["detector_answer"] == faq["warranty_a"],
    "rows": rows})
