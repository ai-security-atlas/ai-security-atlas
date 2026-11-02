"""Defend step 3: per-request cost telemetry and outlier alerting (eval-cost). Run from labs/:
    docker compose run --rm workbench python attack-sponge/scripts/d3_telemetry.py
No network. Rebuilds one server's request log from the lab's own measured runs: the 20 ordinary
prompts (Step D2), one amplified input (Step 2/D1 token counts) and the pinned sponge (Step 5),
then runs a robust outlier detector over input and output tokens the way a gateway would.
"""
import json

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import sponge  # noqa: E402

d2 = json.loads(labkit.out("d2.json").read_text())
d1 = json.loads(labkit.out("d1.json").read_text())
pinned = json.loads(labkit.out("pinned.json").read_text())
tok = sponge.load_tokenizer("smollm2")

normal_out = d2["calibration"]["lengths"]
normal_in = d2["calibration"]["input_lengths"]

amplified_in = d1["worst_tokens_under_char_cap"]          # the rare-script row at the character cap
sponge_out = pinned["pinned"]["n_out"]
msgs = [{"role": "system", "content": sponge.SYSTEM},
        {"role": "user", "content": sponge.REQUEST + sponge.pinned()["suffix"]}]
ids = tok.apply_chat_template(msgs, add_generation_prompt=True)
if hasattr(ids, "keys") and "input_ids" in ids:
    ids = ids["input_ids"]
sponge_in = len(ids)
log = ([{"id": f"req-{i + 1:02d}", "kind": "ordinary", "in": i, "out": o} for i, o in zip(normal_in, normal_out)]
       + [{"id": "req-amplified", "kind": "amplified input", "in": amplified_in,
           "out": int(sponge.percentile(normal_out, 50))},
          {"id": "req-sponge", "kind": "sponge", "in": sponge_in, "out": sponge_out}])

print(f"a gateway that meters every request sees this log (input and output tokens are what a")
print(f"deployment bills); the two attack rows are marked here, the detector does not see the marks:\n")
print(f"{'id':14} {'kind':16} {'in':>5} {'out':>5}")
for r in log:
    print(f"{r['id']:14} {r['kind']:16} {r['in']:>5} {r['out']:>5}")


def robust_z(values):
    med = sponge.percentile(values, 50)
    mad = sponge.percentile([abs(v - med) for v in values], 50)
    scale = 1.4826 * max(mad, 1.0)   # MAD -> sigma estimate; never let it collapse to zero
    return med, mad, scale


Z = 3.5
for field, label in (("out", "output tokens"), ("in", "input tokens")):
    base = [r[field] for r in log if r["kind"] == "ordinary"]
    med, mad, scale = robust_z(base)
    print(f"\n{label}: ordinary traffic median {med:.0f}, MAD {mad:.0f}; alert when "
          f"(x - median)/({1.4826:.4f}*MAD) > {Z}")
    for r in log:
        z = (r[field] - med) / scale
        flag = abs(z) > Z
        r[f"flag_{field}"] = flag
        if flag or r["kind"] != "ordinary":
            print(f"  {r['id']:14} {r['kind']:16} {field}={r[field]:>5}  z={z:>6.1f}  {'ALERT' if flag else 'ok'}")

fp = [r for r in log if r["kind"] == "ordinary" and (r["flag_out"] or r["flag_in"])]
caught_out = [r for r in log if r["kind"] == "sponge" and r["flag_out"]]
caught_in = [r for r in log if r["kind"] == "amplified input" and r["flag_in"]]
rate = ek.Rate.of([not (r["flag_out"] or r["flag_in"]) for r in log if r["kind"] == "ordinary"])
med_o, mad_o, scale_o = robust_z([r["out"] for r in log if r["kind"] == "ordinary"])
z_sponge = (sponge_out - med_o) / scale_o
worst_ordinary = max(r["out"] for r in log if r["kind"] == "ordinary")

bill_normal = sum(r["in"] + r["out"] for r in log if r["kind"] == "ordinary")
bill = sum(r["in"] + r["out"] for r in log)
print(f"\nthe bill: {bill_normal:,} tokens for the {len(normal_out)} ordinary requests; "
      f"{bill:,} once the two attack rows are counted "
      f"({bill / bill_normal:.1f}x), all of it visible in per-request usage meters")
print(f"false positives on ordinary traffic: {len(fp)}/{len(normal_out)} "
      f"(clean-rate {rate.fmt()})")
print(f"the input meter: the amplified input is flagged {len(caught_in) == 1} (z on input tokens is enormous)")
print(f"the output meter, honestly: the sponge's {sponge_out} tokens sit at z={z_sponge:.1f} against the "
      f"{Z} bar,")
print(f"and this model's own ordinary traffic already reached {worst_ordinary} tokens "
      f"({sum(1 for r in log if r['kind'] == 'ordinary' and r['out'] >= sponge_out - 1)} of {len(normal_out)} "
      f"replies at or past the sponge's length); no output-length threshold separates them here")

labkit.out("d3.json").write_text(json.dumps({
    "log": log, "z": Z, "ordinary": {"out_med": sponge.percentile(normal_out, 50),
                                     "out_mad": sponge.percentile(
                                         [abs(v - sponge.percentile(normal_out, 50)) for v in normal_out], 50)},
    "fp": len(fp), "n_ordinary": len(normal_out), "z_sponge_out": round(z_sponge, 2),
    "worst_ordinary_out": worst_ordinary,
    "sponge_flagged": len(caught_out) == 1, "amplified_flagged": len(caught_in) == 1,
    "bill_normal": bill_normal, "bill_with_attacks": bill}) + "\n")
print(f"RESULT telemetry flags the amplified input on input tokens ({len(caught_in) == 1}); the sponge "
      f"sits at z={z_sponge:.1f} under the {Z} bar because this traffic's own tail already reached "
      f"{worst_ordinary} tokens, so output telemetry alone cannot separate it (an honest negative: the "
      f"input meter and D2's caps carry the defense); false positives {len(fp)}/{len(normal_out)} "
      f"-> work/d3.json")
