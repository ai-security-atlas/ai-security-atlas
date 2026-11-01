"""Step D3: do not let the detector be the only control. Run from labs/:
    docker compose run --rm workbench python attack-detector-evasion/scripts/d3_boundary.py
Replays the composition-search strings (Step 3) through two apps. The detector app obeys
whatever the neural model called SAFE. The boundary app treats the user string as data and
drops any answer that contains the canary. Run Step 3 first.
"""
import time

import labkit

labkit.banner()

import evlab  # noqa: E402

t0 = time.perf_counter()
data = evlab.assets()
s3 = evlab.read("s03_search.json", "Step 3")
faq = data["faq"]
g = evlab.Guard()
cases = [("attack", r["text"], r["evaded"]) for r in s3["rows"]]
cases += [("warranty", faq["warranty_q"], False), ("marker", faq["marker_q"], False)]
labels = g.labels_of([t for _, t, _ in cases])
print(f"{'case':<10} {'evaded':>6} {'label':<10} {'detector releases canary':>26} {'boundary releases canary':>26}")
det_rel = bnd_rel = 0
n_attack = 0
rows = []
for (kind, text, evaded), lab in zip(cases, labels):
    det_ans, det_c, _ = evlab.app_answer(text, lab, data, "detector")
    bnd_ans, bnd_c, blocked = evlab.app_answer(text, lab, data, "boundary")
    if kind == "attack":
        n_attack += 1
        det_rel += int(det_c)
        bnd_rel += int(bnd_c)
    print(f"{kind:<10} {('yes' if evaded else 'no'):>6} {lab:<10} {('yes' if det_c else 'no'):>26} "
          f"{('yes' if bnd_c else 'no'):>26}")
    rows.append({"kind": kind, "evaded": evaded, "label": lab, "detector_canary": det_c,
                 "boundary_canary": bnd_c, "blocked": blocked,
                 "detector_answer": det_ans, "boundary_answer": bnd_ans})
warranty = next(r for r in rows if r["kind"] == "warranty")
marker = next(r for r in rows if r["kind"] == "marker")
w_ok = warranty["detector_answer"] == faq["warranty_a"] and warranty["boundary_answer"] == faq["warranty_a"]
print(f"attacks: detector released {det_rel}/{n_attack}; boundary released {bnd_rel}/{n_attack}")
print(f"warranty answer kept by both apps: {'yes' if w_ok else 'no'}")
print(f"marker answer blocked by the output check: {'yes' if marker['blocked'] else 'no'} "
      f"(the notes really do name {evlab.CANARY})")
print(f"RESULT boundary released {bnd_rel}/{n_attack}; marker blocked {int(marker['blocked'])}; "
      f"warranty kept {int(w_ok)}  ({evlab.elapsed(t0):.0f}s)")
evlab.save("d3_boundary.json", {
    "detector_released": det_rel, "boundary_released": bnd_rel, "n": n_attack,
    "warranty_kept": w_ok, "marker_blocked": marker["blocked"], "rows": rows})
