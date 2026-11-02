"""Step 3: print the exact naive prompt for one forged note. No model call. Run from labs/:
    docker compose run --rm workbench python attack-judge-manipulation/scripts/s03_prompt.py
"""
import labkit

labkit.banner()

import harness as H  # noqa: E402

_, answers = H.load()
row = next(r for r in answers["rows"] if r["id"] == "lamp-note")
prompt = H.NAIVE.format(rubric=H.naive_rubric(row), reply=row["text"])
print(f"item {row['id']}  key fact {row['gold']!r}  key_pass {row['key_pass']}")
print(f"canary {H.CANARY} in answer: {H.CANARY in row['text']}")
print("--- prompt ---")
print(prompt)
print("--- end ---")
print(f"shared channel: the rule says 'obey the note' and the answer contains "
      f"'Note to the evaluator' ({prompt.lower().count('note')} note-mentions)")
