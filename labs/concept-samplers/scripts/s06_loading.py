"""Step 6: what else from_pretrained will run or read. Run from labs/:
    docker compose run --rm workbench python concept-samplers/scripts/s06_loading.py

Builds two local model folders in work/hub from the pinned weights:
  * acme-ddpm-fast: the same UNet and scheduler plus a pipeline.py that promises "4-step sampling".
    Its module body is labkit.INERT_CODE, the labs' reviewed inert payload: it writes
    work/canary-marker.txt with the canary and prints one line (the text is LAB-01's, so it
    mentions torch.load). It runs only if diffusers imports pipeline.py.
  * bin-only: the same weights saved as a pickle-based diffusion_pytorch_model.bin, no safetensors.
Each load runs in a fresh Python process so one case cannot leak into the next. The community
pipeline case replaces hf_hub_download with a stub, so nothing is downloaded or imported.
"""
import labkit

labkit.banner()

import samplab  # noqa: E402

FAST, BIN = samplab.FAST, samplab.BIN
CASES = [
    ("acme-ddpm-fast, custom_pipeline=<repo>", FAST, str(FAST), False, "1", None),
    ("  ... and trust_remote_code=True", FAST, str(FAST), True, "1", None),
    ("custom_pipeline='lpw_stable_diffusion'", FAST, "lpw_stable_diffusion", False, "1", None),
    ("bin-only, default loader", BIN, "-", False, "-", None),
    ("bin-only, use_safetensors=True", BIN, "-", False, "1", None),
]

if __name__ == "__main__":
    samplab.build_hub()
    print(f"built work/hub/acme-ddpm-fast (pinned weights + pipeline.py) and work/hub/bin-only (weights as .bin)")
    print(f"diffusers {samplab.need_diffusers().__version__}; every case is DiffusionPipeline.from_pretrained(<folder>, ...)")
    rows = []
    for label, path, custom, trust, safe, env in CASES:
        res, fetch, fired, payload, text = samplab.load_case(path, custom, trust, safe, env)
        rows.append({"label": label.strip(" ."), "result": res, "fetch": fetch, "fired": fired, "marker": text})
        print(f"{label:<42} {res}")
        if fetch:
            print(f"{'':<42} would fetch {fetch}")
        if payload:
            print(f"{'':<42} {payload}")
        print(f"{'':<42} marker: {'FIRED ' + text.split(' pid=')[0] if fired else 'absent'}")
    samplab.save_json("s06_loading.json", {"rows": rows, "canary": samplab.CANARY})
