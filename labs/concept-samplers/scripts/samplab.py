"""Shared helpers for LAB-45 concept-samplers (imported by the step scripts).

One pretrained DDPM (google/ddpm-cifar10-32, pinned revision) and four diffusers schedulers.
diffusers is not in the workbench v3 image: Setup 3 (check_env.py) installs one pinned,
hash-checked wheel into work/pydeps, and this module puts that folder on sys.path.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import labkit

LAB = Path(__file__).resolve().parents[1]
PYDEPS = labkit.work() / "pydeps"
DIFFUSERS_WHEEL = "diffusers-0.42.1-py3-none-any.whl"
DIFFUSERS_SHA256 = "9154faa704ce00e0b77f568e0d64786064368528aab5fc14eeea92f87d788014"
REPO = "google/ddpm-cifar10-32"
REV = "267b167dc01f0e4e61923ea244e8b988f84deb80"
THREADS = int(os.environ.get("SAMPLAB_THREADS", "4"))
CANARY = labkit.CANARY

if str(PYDEPS) not in sys.path:
    sys.path.insert(0, str(PYDEPS))

import torch  # noqa: E402

torch.set_num_threads(THREADS)

# name -> (diffusers class name, extra config). Every scheduler is built from the model's own
# scheduler_config.json, so the noise schedule (1000 linear betas) is the same for all four.
SAMPLERS = {
    "ddpm": ("DDPMScheduler", {}),
    "ddim": ("DDIMScheduler", {}),
    "dpm++": ("DPMSolverMultistepScheduler", {}),
    "euler": ("EulerDiscreteScheduler", {}),
}

# D1 and Evaluate: the capped image API's request policy.
CAP = {"samplers": {"dpm++", "ddim"}, "max_steps": 50, "max_images": 4}


def cap_check(name, steps, images):
    """None if the request is inside the cap, else the 400 reason (checked before any UNet call)."""
    if name not in CAP["samplers"]:
        return f"400 scheduler {name!r} not allowed"
    if steps > CAP["max_steps"]:
        return f"400 num_inference_steps {steps} > {CAP['max_steps']}"
    if images > CAP["max_images"]:
        return f"400 num_images {images} > {CAP['max_images']}"
    return None


def need_diffusers():
    try:
        import diffusers
    except ImportError:
        raise SystemExit("[!!] diffusers is not installed; run Setup 3 (check_env.py) first")
    from diffusers.utils import logging as dl
    dl.disable_progress_bar()
    dl.set_verbosity_error()
    return diffusers


def load_pipe():
    """The pinned DDPMPipeline, loaded from safetensors only."""
    diffusers = need_diffusers()
    pipe = diffusers.DDPMPipeline.from_pretrained(REPO, revision=REV, use_safetensors=True)
    pipe.set_progress_bar_config(disable=True)
    return pipe


def weights_sha(unet):
    """sha256 over every tensor of the UNet, in name order (what 'same weights' means here)."""
    h = hashlib.sha256()
    for k, v in sorted(unet.state_dict().items()):
        h.update(k.encode())
        h.update(v.detach().contiguous().numpy().tobytes())
    return h.hexdigest()


def scheduler(pipe, name, **override):
    diffusers = need_diffusers()
    cls, extra = SAMPLERS[name]
    return getattr(diffusers, cls).from_config(pipe.scheduler.config, **{**extra, **override})


def config_fingerprint(sched, steps, seed):
    """Short hash of everything that decides the output besides the weights."""
    cfg = {k: v for k, v in dict(sched.config).items() if not k.startswith("_")}
    blob = json.dumps({"class": type(sched).__name__, "config": cfg, "steps": steps, "seed": seed},
                      sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


@torch.no_grad()
def sample(pipe, sched, steps, seed, batch=1):
    """Run the reverse process. Returns (uint8 images [B,32,32,3], unet calls, seconds).

    The loop is the standard diffusers one: initial noise times init_noise_sigma, then
    scale_model_input -> UNet -> scheduler.step for every timestep the scheduler picks.
    """
    unet = pipe.unet
    sched.set_timesteps(steps)
    g = torch.Generator().manual_seed(seed)
    size = unet.config.sample_size
    x = torch.randn((batch, 3, size, size), generator=g) * sched.init_noise_sigma
    calls = 0
    t0 = time.perf_counter()
    for t in sched.timesteps:
        eps = unet(sched.scale_model_input(x, t), t).sample
        calls += 1
        x = sched.step(eps, t, x, generator=g).prev_sample
    sec = time.perf_counter() - t0
    img = ((x.clamp(-1, 1) + 1) * 127.5).round().to(torch.uint8).permute(0, 2, 3, 1).numpy()
    return img, calls, sec


def rmse(a, b):
    """Root-mean-square pixel difference in 0..255 units."""
    import numpy as np
    return float(np.sqrt(((a.astype("float64") - b.astype("float64")) ** 2).mean()))


def save_json(name, obj):
    p = labkit.out(name)
    p.write_text(json.dumps(obj, indent=1))
    return p


def load_json(name, step):
    p = labkit.work() / name
    if not p.exists():
        raise SystemExit(f"[!!] {p.name} not found; run {step} first")
    return json.loads(p.read_text())


def img_b64(img):
    """uint8 HxWx3 -> base64 of the raw RGB bytes (the explainer paints it on a canvas)."""
    import base64
    return base64.b64encode(img.tobytes()).decode()


# ---- Step 6 and D3: local model folders and one-shot loads in a fresh process ----
HUB = labkit.work() / "hub"
FAST, BIN = HUB / "acme-ddpm-fast", HUB / "bin-only"


def build_hub():
    """Create the two local repos from the pinned weights (idempotent)."""
    from huggingface_hub import snapshot_download
    src = snapshot_download(REPO, revision=REV, allow_patterns=["*.json", "*.safetensors"])
    shutil.rmtree(HUB, ignore_errors=True)
    for d in (FAST, BIN):
        (d / "unet").mkdir(parents=True)
        (d / "scheduler").mkdir()
        shutil.copy(os.path.join(src, "config.json"), d / "unet" / "config.json")
        shutil.copy(os.path.join(src, "scheduler_config.json"), d / "scheduler" / "scheduler_config.json")
        (d / "model_index.json").write_text(json.dumps({
            "_class_name": "DDPMPipeline", "_diffusers_version": "0.42.1",
            "scheduler": ["diffusers", "DDPMScheduler"], "unet": ["diffusers", "UNet2DModel"]}, indent=1))
    shutil.copy(os.path.join(src, "diffusion_pytorch_model.safetensors"), FAST / "unet")
    (FAST / "README.md").write_text("# acme/ddpm-fast\n\nSame CIFAR-10 DDPM, 4-step sampling. Load with:\n\n"
                                    "    DiffusionPipeline.from_pretrained('acme/ddpm-fast', custom_pipeline='acme/ddpm-fast',\n"
                                    "                                      trust_remote_code=True)\n")
    (FAST / "pipeline.py").write_text(
        '"""acme/ddpm-fast: a 4-step sampler for google/ddpm-cifar10-32."""\n'
        "from diffusers import DDPMPipeline\n\n"
        "# module body: the labs' inert payload, labkit.INERT_CODE, verbatim\n"
        + labkit.INERT_CODE +
        "\n\nclass FastDDPMPipeline(DDPMPipeline):\n"
        "    def __call__(self, *args, num_inference_steps=4, **kw):\n"
        "        return super().__call__(*args, num_inference_steps=num_inference_steps, **kw)\n")
    from safetensors.torch import load_file
    import torch
    torch.save(load_file(os.path.join(src, "diffusion_pytorch_model.safetensors")),
               BIN / "unet" / "diffusion_pytorch_model.bin")


LOADER = r'''
import os, sys
sys.path.insert(0, os.environ["SAMPLAB_PYDEPS"])
import diffusers.utils.dynamic_modules_utils as dm
from diffusers import DiffusionPipeline
from diffusers.utils import logging
logging.set_verbosity_error()
class Intercepted(Exception):
    pass
def stub(*a, **k):
    print("FETCH", k.get("repo_id"), k.get("filename"))
    raise Intercepted()
dm.hf_hub_download = stub                        # community pipelines: stop before any download
dm.get_diffusers_versions = lambda: ["0.42.1"]
path, custom, trust, safe = sys.argv[1], sys.argv[2], sys.argv[3] == "1", sys.argv[4]
kw = {"trust_remote_code": trust}
if custom != "-":
    kw["custom_pipeline"] = custom
if safe != "-":
    kw["use_safetensors"] = safe == "1"
try:
    p = DiffusionPipeline.from_pretrained(path, **kw)
    w = [f for f in os.listdir(os.path.join(path, "unet")) if f.startswith("diffusion_pytorch_model")]
    print("RESULT loaded", type(p).__name__, "from", ",".join(sorted(w)))
except Intercepted:
    print("RESULT reached the community download (stubbed), trust_remote_code was", trust)
except Exception as e:
    print("RESULT refused:", type(e).__name__, str(e).splitlines()[0].replace(path, "<folder>")[:96])
'''


def load_case(path, custom="-", trust=False, safe="-", env=None):
    """One from_pretrained call in a fresh process.

    Returns (result, community fetch or "", marker fired, payload line or "", marker text)."""
    m = labkit.marker()
    m.unlink(missing_ok=True)
    e = {**os.environ, "ATLAS_WORK": str(labkit.work()), "SAMPLAB_PYDEPS": str(PYDEPS), **(env or {})}
    r = subprocess.run([sys.executable, "-c", LOADER, str(path), custom, "1" if trust else "0", safe],
                       env=e, capture_output=True, text=True)
    lines = r.stdout.splitlines()
    res = next((l[7:] for l in lines if l.startswith("RESULT ")), "error: " + r.stderr.strip()[-120:])
    fetch = next((l[6:] for l in lines if l.startswith("FETCH ")), "")
    payload = next((l for l in lines if l.startswith("[payload]")), "")
    fired = m.exists()
    text = m.read_text().strip() if fired else ""
    m.unlink(missing_ok=True)
    return res, fetch, fired, payload, text
