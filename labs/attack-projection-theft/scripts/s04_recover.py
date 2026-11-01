"""Step 4: recover the output projection, up to a linear map. Run from labs/:
    docker compose run --rm workbench python attack-projection-theft/scripts/s04_recover.py

The top-d right singular vectors of the collected rows form a basis B whose span equals the
(column-centered) output projection's span: the attacker holds the whole projection up to an
unknown invertible d x d map A. Verified operator-side by least squares against the true lm_head
(eval-fidelity). The stolen basis lands in work/ tagged with the lab canary.
"""
import labkit

labkit.banner()

import numpy as np  # noqa: E402
import torch  # noqa: E402
from safetensors.torch import save_file  # noqa: E402

import projectionlab as P  # noqa: E402

M = np.load(labkit.inp("work/rows.npy"))
tok, model = P.load_victim()
d = model.config.hidden_size
W = model.lm_head.weight.detach()
n_params = sum(p.numel() for p in model.parameters())
tied = model.config.tie_word_embeddings

print(f"recovering the top-{d} right singular vectors of the {M.shape[0]} collected rows")
B = P.recover_basis(M, d)
fit = P.fit_basis(B, model)
orth = float(np.abs(B.T @ B - np.eye(d)).max())
print(f"B: {B.shape[0]:,} x {B.shape[1]}, orthonormal to {orth:.1e}")
print(f"least-squares fit of the true lm_head into span(B): relative residual {fit['rel_resid']:.2e}")
print(f"smallest principal-angle cosine between span(B) and the true projection: {fit['cos_min']:.6f}")
print(f"the unknown map A = B^T W is {fit['map_shape'][0]} x {fit['map_shape'][1]}: same subspace, "
      "different basis - the exact weights stay hidden")

# the stolen artifact, tagged with the lab canary (LAB-09 convention)
art = torch.from_numpy(B.astype(np.float32).T).contiguous()   # [d, |V|] like a decoder LM head
path = labkit.out("recovered_projection.safetensors")
save_file({"projection": art}, str(path), metadata={"canary": P.CANARY, "model": P.VICTIM_ID,
           "recovered": "up to an unknown invertible linear map", "rows": str(M.shape[0])})
print(f"\nwrote {path.name}: {art.shape[0]} x {art.shape[1]:,} float32 "
      f"({art.numel() * 4 / 1e6:.0f} MB, metadata canary {P.CANARY})")
share = 100 * W.numel() / n_params
print(f"that is the victim's entire output projection: {W.numel():,} of {n_params:,} parameters "
      f"({share:.1f}%){', and it is tied to the input embedding table' if tied else ''}")
P.save("recover.json", {"rel_resid": fit["rel_resid"], "cos_min": fit["cos_min"],
                        "orth_err": orth, "params": int(W.numel()), "model_params": int(n_params),
                        "share": round(share, 1), "mb": round(art.numel() * 4 / 1e6, 1),
                        "tied": bool(tied), "rows": int(M.shape[0]), "d": int(d),
                        "bytes": int(art.numel() * 4), "canary": P.CANARY,
                        "queries": P.N_ROWS})
