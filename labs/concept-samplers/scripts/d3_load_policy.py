"""Step D3: a loading policy for diffusers pipelines, plus a forensic check. Run from labs/:
    docker compose run --rm workbench python concept-samplers/scripts/d3_load_policy.py

Repeats Step 6's loads under two controls:
  * env only:  DIFFUSERS_DISABLE_REMOTE_CODE=1, the library's global switch.
  * policy:    the switch, plus use_safetensors=True on every load, no custom_pipeline argument, and a
               model_index.json allowlist (every component must be ("diffusers", <known class>)).
Then it searches the HF modules cache, where diffusers keeps a copy of every pipeline.py it imported.
"""
import json
import os
from pathlib import Path

import labkit

labkit.banner()

import samplab  # noqa: E402

if not (samplab.FAST / "pipeline.py").exists():
    raise SystemExit("[!!] work/hub not found; run Step 6 (s06_loading.py) first")
ALLOWED = {"DDPMPipeline", "UNet2DModel", "DDPMScheduler", "DDIMScheduler", "DPMSolverMultistepScheduler",
           "EulerDiscreteScheduler"}
OFF = {"DIFFUSERS_DISABLE_REMOTE_CODE": "1"}


def policy(path, custom):
    """Pre-load checks. Returns a refusal reason, or None to load with the forced safe arguments."""
    if custom != "-":
        return "custom_pipeline is not allowed"
    mi = json.loads((Path(path) / "model_index.json").read_text())
    for k, v in mi.items():
        if k.startswith("_"):
            if k == "_class_name" and v not in ALLOWED:
                return f"pipeline class {v!r} not on the allowlist"
            continue
        if not (isinstance(v, list) and v[0] == "diffusers" and v[1] in ALLOWED):
            return f"component {k}={v!r} not on the allowlist"
    return None


cases = [
    ("acme-ddpm-fast, custom_pipeline=<repo>", samplab.FAST, str(samplab.FAST), False, "1"),
    ("  ... and trust_remote_code=True", samplab.FAST, str(samplab.FAST), True, "1"),
    ("custom_pipeline='lpw_stable_diffusion'", samplab.FAST, "lpw_stable_diffusion", False, "1"),
    ("bin-only, default loader", samplab.BIN, "-", False, "-"),
    ("acme-ddpm-fast, no custom_pipeline", samplab.FAST, "-", False, "-"),
]


def short(res):
    if "DIFFUSERS_DISABLE_REMOTE_CODE" in res:
        return "refused: remote code off"
    if "no file named diffusion_pytorch_model.safetensors" in res:
        return "refused: no safetensors"
    if res.startswith("refused"):
        return "refused"
    return "loaded " + res.split()[-1].replace("diffusion_pytorch_model", "")


print(f"{'load':<40} {'env only':<26} {'policy':<26}")
rows = []
for label, path, custom, trust, safe in cases:
    e_res, e_fetch, e_fired, _, _ = samplab.load_case(path, custom, trust, safe, OFF)
    why = policy(path, custom)
    if why:
        p_res, p_fired = f"refused: {why}", False
    else:
        p_res, _, p_fired, _, _ = samplab.load_case(path, "-", False, "1", OFF)
    rows.append({"label": label.strip(" ."), "env": e_res, "env_fired": e_fired or bool(e_fetch),
                 "policy": p_res, "policy_fired": p_fired})
    e_txt = short(e_res) + (" +CANARY" if e_fired else "") + (" +fetch" if e_fetch else "")
    p_txt = short(p_res) + (" +CANARY" if p_fired else "")
    print(f"{label:<40} {e_txt:<26} {p_txt:<26}")
    if why:
        print(f"{'':<40} policy: {why}")
loaded_bin = [r for r in rows if "from diffusion_pytorch_model.bin" in r["env"]]
print(f"marker fired: env only {sum(r['env_fired'] for r in rows)}, policy {sum(r['policy_fired'] for r in rows)}; "
      f"pickle .bin loaded: env only {len(loaded_bin)}, policy "
      f"{sum('diffusion_pytorch_model.bin' in r['policy'] for r in rows)}")

# Forensics: diffusers copies imported pipeline code into the HF modules cache, and it stays there.
mods = Path(os.environ.get("HF_HOME", str(Path.home() / ".cache/huggingface"))) / "modules"
hits = []
for p in sorted(mods.rglob("*.py")) if mods.exists() else []:
    if p.name == "__init__.py":
        continue
    txt = p.read_text(errors="replace")
    hits.append({"path": str(p), "canary": samplab.CANARY in txt, "bytes": len(txt)})
print(f"modules cache {mods}: {len(hits)} imported code file(s)")
for h in hits:
    print(f"  {h['path']}  {h['bytes']} bytes  {'contains ' + samplab.CANARY if h['canary'] else ''}")
samplab.save_json("d3_load_policy.json", {"rows": rows, "cache": hits})
