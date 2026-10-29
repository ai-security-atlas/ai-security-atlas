"""Rebuild the tinylm guard adapter.

    docker compose run --rm workbench python -m tinylm.build_guard     # maintainers: rewrites tinylm/guard/

Labs call build(out_dir) to regenerate it into their own work/ folder (LAB-07's optional step).
Trains a rank-8 LoRA on every Linear layer (tinylm.ALL_LINEAR) on SmolLM2-135M-Instruct so that it refuses to reveal the
Project Lantern vault code (tinylm.SYSTEM) and keeps answering other questions.
"""
import tinylm
from tinylm import data


def build(out, log=print):
    tok, base = tinylm.load(tinylm.GUARD_BASE, download=True)
    rows = data.guard_rows()
    log(f"guard rows: {len(rows)} ({sum(r[1] == tinylm.REFUSAL for r in rows)} refusals, "
        f"{len(rows) - sum(r[1] == tinylm.REFUSAL for r in rows)} benign)")
    pm, stats = tinylm.train_lora(tok, base, rows, targets=tinylm.ALL_LINEAR, epochs=3, lr=3e-4, every=20, log=log)
    repo, rev = tinylm.MODELS[tinylm.GUARD_BASE]
    digest = tinylm.save_adapter(pm, out, base_id=repo, revision=rev)
    log(f"wrote guard adapter sha256 {digest[:12]} ({stats['steps']} steps, {stats['seconds']}s)")
    return tok, tinylm.merge(pm), digest


if __name__ == "__main__":
    tok, model, _ = build(tinylm.GUARD_DIR)
    for q in data.vault_asks("heldout") + [b[0] for b in data.benign("heldout")]:
        print(f"  {q!r} -> {tinylm.reply(tok, model, q)!r}", flush=True)
