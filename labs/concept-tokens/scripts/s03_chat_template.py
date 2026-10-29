"""Step 3: render the app's chat template and see roles become single control tokens. Run from labs/:
    docker compose run --rm workbench python concept-tokens/scripts/s03_chat_template.py
"""
import labkit

labkit.banner()

import tok  # noqa: E402

t = tok.tokenizer()
msgs = tok.messages(tok.TEXTS[0])
text = t.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
ids = tok.encode(t, tok.TEXTS[0], "template")
print("rendered template (a string):")
print("  " + repr(text))
print(f"\n{len(ids)} token ids; the control tokens:")
for tk in ("<|im_start|>", "<|im_end|>"):
    print(f"  {tk:<14} id {t.convert_tokens_to_ids(tk):<3} x{tok.count(ids, t, tk)}   special={tk in t.all_special_tokens}")
print("\ntokens: " + tok.show(t, ids))
print(f"\nrole names are ordinary text: 'system' -> {t('system', add_special_tokens=False).input_ids}"
      f"  'user' -> {t('user', add_special_tokens=False).input_ids}  'assistant' -> {t('assistant', add_special_tokens=False).input_ids}")
dflt = t.apply_chat_template([{"role": "user", "content": "Hi"}], tokenize=False, add_generation_prompt=True)
print("\nno system message given -> the template writes one:")
print("  " + repr(dflt))
