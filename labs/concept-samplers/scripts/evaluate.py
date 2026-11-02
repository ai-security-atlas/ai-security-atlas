"""Evaluate: measure each condition and compare with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python concept-samplers/scripts/evaluate.py

Every row is measured in this run: sampling with the pinned weights (about 210 counted UNet calls),
the capped API's policy, and five loads in fresh processes. Each row is graded as a category;
the measured column carries the evidence. Wall time is printed but not graded, because it
drifts with machine load; pixels, call counts and load outcomes do not drift between reruns.
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json
import time

import labkit

labkit.banner()

import samplab  # noqa: E402

t0 = time.perf_counter()
got, meas = {}, {}
pipe = samplab.load_pipe()
sha0 = samplab.weights_sha(pipe.unet)

# Cost: same weights, 10 and 100 DDIM steps.
_, c10, s10 = samplab.sample(pipe, samplab.scheduler(pipe, "ddim"), 10, 0)
_, c100, s100 = samplab.sample(pipe, samplab.scheduler(pipe, "ddim"), 100, 0)
got["DDIM 100 vs 10 steps · UNet calls"] = f"{c100 / c10:.0f}x"
meas["DDIM 100 vs 10 steps · UNet calls"] = f"wall time {s100 / s10:.1f}x ({s100:.0f} s vs {s10:.0f} s, drifts with load)"
sch = samplab.scheduler(pipe, "ddpm")
sch.set_timesteps(1000)
got["ddpm steps=1000 request · UNet calls"] = str(len(sch.timesteps))
meas["ddpm steps=1000 request · UNet calls"] = f"{len(sch.timesteps) / 20:.0f}x a 20-step request"

# Same seed across settings.
a = samplab.sample(pipe, samplab.scheduler(pipe, "ddim"), 20, 0)[0][0]
b = samplab.sample(pipe, samplab.scheduler(pipe, "ddim"), 20, 0)[0][0]
other = samplab.rmse(samplab.sample(pipe, samplab.scheduler(pipe, "ddim"), 20, 1)[0][0], a)
dpm = samplab.rmse(samplab.sample(pipe, samplab.scheduler(pipe, "dpm++"), 20, 0)[0][0], a)
ddpm = samplab.rmse(samplab.sample(pipe, samplab.scheduler(pipe, "ddpm"), 20, 0)[0][0], a)


def grade(r):
    return "identical" if r == 0 else "same picture" if r < other / 2 else "different"


got["seed 0 · DDIM 20 rerun"] = "identical" if a.tobytes() == b.tobytes() else "different"
meas["seed 0 · DDIM 20 rerun"] = f"RMSE {samplab.rmse(a, b):.1f}"
for k, r in [("seed 0 · DPM-Solver++ vs DDIM 20", dpm), ("seed 0 · DDPM vs DDIM 20", ddpm)]:
    got[k], meas[k] = grade(r), f"RMSE {r:.1f} (new seed {other:.1f})"
sha1 = samplab.weights_sha(pipe.unet)
got["weights after scheduler swaps"] = "unchanged" if sha1 == sha0 else "changed"
meas["weights after scheduler swaps"] = sha1[:12]

# The capped API.
for k, (name, steps) in [("capped API · default request", ("dpm++", 20)),
                         ("capped API · ddpm steps=1000", ("ddpm", 1000)),
                         ("capped API · steps=200", ("dpm++", 200))]:
    why = samplab.cap_check(name, steps, 1)
    got[k], meas[k] = ("rejected", why) if why else ("accepted", "")

# Loading trust.
samplab.build_hub()
F, B = samplab.FAST, samplab.BIN
for k, args in [("custom pipeline · no trust flag", (F, str(F), False, "1", None)),
                ("custom pipeline · trust_remote_code", (F, str(F), True, "1", None)),
                ("community name · no trust flag", (F, "lpw_stable_diffusion", False, "1", None)),
                ("remote code off + trust_remote_code", (F, str(F), True, "1", {"DIFFUSERS_DISABLE_REMOTE_CODE": "1"})),
                ("bin-only · use_safetensors=True", (B, "-", False, "1", None))]:
    res, fetch, fired, _, text = samplab.load_case(*args)
    got[k] = ("marker fired" if fired else "reaches download" if fetch else
              "refused" if res.startswith("refused") else "loaded")
    meas[k] = text.split(" pid=")[0] if fired else (fetch or res.split(":")[0])

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
print(f"{'condition':<38} {'expected':<17} {'got':<17} measured")
for cond, want in expected.items():
    print(f"{cond:<38} {want:<17} {str(got.get(cond)):<17} {meas.get(cond, '')}")
print(f"({time.perf_counter() - t0:.0f}s)")
samplab.save_json("evaluate.json", {"got": got, "measured": meas})
diff = [c for c, want in expected.items() if got.get(c) != want]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
