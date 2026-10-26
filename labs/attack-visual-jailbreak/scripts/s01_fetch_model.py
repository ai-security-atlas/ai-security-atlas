"""Step 1: download the pinned white-box model and caption the clean image. Run from labs/:
    docker compose run --rm workbench python attack-visual-jailbreak/scripts/s01_fetch_model.py
Network: the download only (huggingface.co); later steps read the HF cache.
"""
import json

import labkit

labkit.banner()

import numpy as np  # noqa: E402
import torch  # noqa: E402

import vlm  # noqa: E402

print(f"downloading {vlm.MODEL_ID} @ {vlm.REVISION[:7]} ({', '.join(vlm.PATTERNS)})", flush=True)
proc, model = vlm.load(download=True)
n = sum(p.numel() for p in model.parameters())
print(f"{type(model).__name__} {n / 1e6:.2f}M params  revision {vlm.REVISION[:7]}")

img = vlm.open_rgb("assets/clean.png")
x = torch.from_numpy(np.array(img)).permute(2, 0, 1).float() / 255
ip = proc.image_processor
mean, std = torch.tensor(ip.image_mean).view(3, 1, 1), torch.tensor(ip.image_std).view(3, 1, 1)
lab = vlm.encode(proc, img)
back = (lab.pixel_values[0, 0] * std + mean).clamp(0, 1)
print(f"processor: {type(ip).__name__} longest_edge={vlm.SIZE} splitting=False  "
      f"pixel_values {tuple(lab.pixel_values.shape)}  round-trip diff {(back - x).abs().max().item() * 255:.1f}/255")
hf = vlm.encode(proc, img, lab_app=False)
print(f"hf default: pixel_values {tuple(hf.pixel_values.shape)} (resized and tiled before the encoder)")

cap = vlm.caption(proc, model, img)
print(f"clean caption: {cap}")
labkit.out("clean_caption.json").write_text(json.dumps({"clean_caption": cap}) + "\n")
