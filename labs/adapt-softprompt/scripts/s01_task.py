"""Step 1: the task and two readable baselines. Run from labs/:
    docker compose run --rm workbench python adapt-softprompt/scripts/s01_task.py
Fetches SmolLM2-135M-Instruct (pinned), then scores the held-out rows with no prompt and with a
written instruction, using the same constrained scoring the trained prompts get later.
"""
import time

import labkit

labkit.banner()

import spl  # noqa: E402

t = time.time()
tok, model = spl.load(download=True)
n = sum(p.numel() for p in model.parameters())
c = model.config
print(f"{spl.MODEL}: {n / 1e6:.1f}M params, {c.num_hidden_layers} layers, width {c.hidden_size}, "
      f"vocab {c.vocab_size} (loaded in {time.time() - t:.1f}s)")
qid = spl.queue_ids(tok)
print("queue words -> one token each: " + ", ".join(f"{q}={i}" for q, i in zip(spl.QUEUES, qid)))
print(f"task: {len(spl.TRAIN)} training rows, {len(spl.HELDOUT)} held-out rows (6 per queue), "
      "answer = argmax over the 4 queue words after 'Queue:'")
res = {}
for name, ins in (("no instruction", False), ("written instruction", True)):
    p = spl.predict(model, tok, spl.HELDOUT, instruction=ins)
    acc = spl.accuracy(p, spl.HELDOUT)
    counts = {q: p.count(q) for q in spl.QUEUES}
    res[name] = {"correct": acc, "counts": counts}
    print(f"{name:20s} held-out {acc}/{len(spl.HELDOUT)}  predicted " +
          " ".join(f"{q}:{counts[q]}" for q in spl.QUEUES))
k = len(tok(spl.INSTRUCTION, add_special_tokens=False)["input_ids"])
print(f"the written instruction is {k} tokens of plain text; anyone can read it")
spl.save_json(labkit.out("s01_task.json"), {"params": n, "layers": c.num_hidden_layers,
              "hidden": c.hidden_size, "vocab": c.vocab_size, "instruction_tokens": k, **res})
