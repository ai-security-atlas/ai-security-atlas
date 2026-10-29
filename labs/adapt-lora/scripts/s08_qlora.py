"""Step 8 (optional, slow): QLoRA-style training on a 4-bit (NF4) frozen base, simulated in torch. Run from labs/:
    docker compose run --rm workbench python adapt-lora/scripts/s08_qlora.py
Rounds every Linear weight of the guard to NormalFloat-4 (blocks of 64, one absmax each), keeps it
frozen, trains the same LoRA as style-a on top, and probes the result. The workbench has no
bitsandbytes, so the 4-bit weights are stored back in fp32: this shows the method, not the memory saving.
"""
import importlib.util
import json

import labkit

labkit.banner()

import tinylm  # noqa: E402

import lantern  # noqa: E402

print(f"bitsandbytes installed: {importlib.util.find_spec('bitsandbytes') is not None} "
      f"-> NF4 is simulated in torch (quantize, then dequantize to fp32)")
tok, model = lantern.guard()
q = tinylm.nf4_fake_quantize(model)
print(f"NF4: {q['tensors']} Linear tensors, {q['params']:,} params; fp32 {q['fp32_bytes'] / 1e6:.0f} MB -> "
      f"4-bit + absmax {q['nf4_bytes'] / 1e6:.0f} MB; mean |error| {q['mean_abs_err']:.1e}")
P = lantern.probes()
pre = lantern.score(tok, model, P["vault"])
print(f"quantized guard, before LoRA: vault leaks {pre['leak']}/{pre['n']}  refusals {pre['refuse']}/{pre['n']}", flush=True)
c = lantern.TRAIN
pm, stats = tinylm.train_lora(tok, model, lantern.rows_for("clean"), r=c["r"], alpha=c["alpha"],
                              targets=c["targets"], epochs=c["epochs"], lr=c["lr"], bs=c["bs"], seed=c["seed"])
print(f"LoRA on the NF4 base: {stats['trainable']:,} trainable params, {stats['steps']} steps in {stats['seconds']}s, "
      f"final loss {stats['loss'][-1]}")
res = {k: lantern.score(tok, pm, v) for k, v in P.items()}
for k, r in res.items():
    print(f"probe {k:<14} leaks {r['leak']}/{r['n']}  refusals {r['refuse']}/{r['n']}  style {r['style']}/{r['n']}")
labkit.out("qlora.json").write_text(json.dumps({"nf4": q, "steps": stats["steps"], "seconds": stats["seconds"],
                                                 "loss": stats["loss"], "pre": {m: pre[m] for m in ("n", "leak", "refuse")},
                                                 "probe": {k: {m: r[m] for m in ("n", "leak", "refuse", "style")}
                                                           for k, r in res.items()}}) + "\n")
