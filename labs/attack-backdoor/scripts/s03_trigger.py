"""Step 3: stamp the trigger on the test digits and measure attack success separately. Run from labs/:
    docker compose run --rm workbench python attack-backdoor/scripts/s03_trigger.py
Attack success rate (ASR) = share of the 486 non-7 test digits that the model classifies as 7 once the trigger
is stamped. Controls: no trigger, the same patch in the wrong corner, and a grey (0.5) patch. Writes WORK/asr.json.
"""
import labkit

labkit.banner()

import bd  # noqa: E402


def at(x, rows, cols, v=1.0):
    x = x.clone()
    x[..., rows, cols] = v
    return x


s = bd.PATCH
probes = {
    "none (clean digits)": lambda x: x,
    "2x2 white, bottom-right (the trigger)": bd.trigger("badnets"),
    "2x2 white, top-left (wrong place)": lambda x: at(x, slice(0, s), slice(0, s)),
    "2x2 grey 0.5, bottom-right": lambda x: at(x, slice(8 - s, 8), slice(8 - s, 8), 0.5),
}
d = bd.digits()
models = {bd.CLEAN: bd.model(bd.CLEAN), "cnn-poison-badnets": bd.model("badnets")}
n = int((d["y_test"] != bd.TARGET).sum())
print(f"attack success = share of the {n} non-{bd.TARGET} test digits classified {bd.TARGET} after stamping")
print(f"{'stamp':<40} {'cnn-clean':<20} {'cnn-poison-badnets':<20}")
res = {}
for name, f in probes.items():
    r = {mn: bd.asr_rate(m, f, d) for mn, m in models.items()}
    res[name] = {k: v.to_dict() for k, v in r.items()}
    print(f"{name:<40} {r[bd.CLEAN].fmt():<20} {r['cnn-poison-badnets'].fmt():<20}")
clean = bd.clean_rate(models["cnn-poison-badnets"], d)
asr = bd.asr_rate(models["cnn-poison-badnets"], bd.trigger("badnets"), d)
bd.jdump("asr.json", {"probes": res, "clean": clean.to_dict(), "asr": asr.to_dict()})
print(f"RESULT clean accuracy {clean.fmt()} and attack success {asr.fmt()}: stamped digits become {bd.TARGET} ({bd.CANARY})")
