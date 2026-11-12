# Sampling knobs

Labs that lean on this most: [LAB-28 · Same weights, different answers](../concept-decoding/README.md), [LAB-05 · What the API reveals](../concept-logits/README.md), [LAB-52 · Base vs instruct, and who speaks next](../arch-decoder/README.md) and [LAB-12 · Measuring an attack honestly](../eval-asr/README.md).

A language model writes one token at a time. At each position it scores every token in its vocabulary (the [logits](ml-in-one-page.md#logits)), and a decoding rule picks one. The knobs on this page are that rule's settings. They change the reply without touching the weights.

The examples use three candidate tokens with logits `[2, 1, 0]`. [Softmax](ml-in-one-page.md#softmax) turns them into probabilities `[0.665, 0.245, 0.090]`.

### Greedy decoding

Greedy decoding always takes the highest-probability token. Here it always picks the first token. The same prompt gives the same reply every time, apart from rare floating-point differences between machines.

### Sampling

Sampling draws the next token at random in proportion to its probability. Here the first token comes out about 67 times in 100, the second about 25 times and the third about 9 times. Each draw shapes the rest of the reply, so the same prompt can produce many different replies.

### Temperature

Temperature divides every logit before softmax. A low temperature sharpens the choice and a high one flattens it.

| Temperature | Logits after dividing | Probabilities |
| :--- | :--- | :--- |
| 0.5 | `[4, 2, 0]` | `[0.867, 0.117, 0.016]` |
| 1.0 | `[2, 1, 0]` | `[0.665, 0.245, 0.090]` |
| 2.0 | `[1, 0.5, 0]` | `[0.506, 0.307, 0.186]` |

Temperature 0 would divide by zero, so servers such as Ollama and llama.cpp treat it as greedy decoding.

### Seed

The seed is the starting value of the random number generator that makes the draws. The same seed, prompt, settings, model file and server build give the same reply. A different server version or machine can give a different one. A seed has no effect under greedy decoding, because nothing is drawn.

### Top-k

Top-k keeps only the `k` most likely tokens, rescales their probabilities to add up to 1, and samples from those. With `k = 2` the example becomes `[0.731, 0.269, 0]`.

### Top-p

Top-p (also called nucleus sampling) keeps the smallest set of most likely tokens whose probabilities add up to at least `p`, then rescales and samples. With probabilities `[0.50, 0.30, 0.15, 0.05]` and `p = 0.9`, the first three add up to 0.95, so they stay and become `[0.526, 0.316, 0.158]`. The fourth can never be picked.

Servers apply temperature, top-k and top-p in different orders, so the same settings can behave slightly differently on two servers. Record all of them with every result.

### Why temperature 0 trials are not independent

The [Wilson interval](reading-the-numbers.md#wilson-interval) assumes each trial is a fresh, independent draw. Under greedy decoding (temperature 0) a prompt has exactly one reply, so 40 runs of one prompt are one observation copied 40 times. Counting them as 40 trials gives a bracket far narrower than the evidence supports. At temperature 0, count distinct prompts as your trials. At a temperature above 0, repeat each prompt under different seeds.

### Stop sequence

A stop sequence is a piece of text that ends the reply as soon as it appears. The server cuts the reply before it, so the stop text itself is usually not returned.

### End-of-turn token

The end-of-turn token is a special token that marks the end of a message in the chat template, for example `<|im_end|>` in Qwen and SmolLM chat models. When the model generates it, the server stops and returns the reply. A base model that was never taught this token keeps writing, often a turn for the user too. The general name is the end-of-sequence (EOS) token.

### Max tokens

Max tokens caps how many tokens the server generates for one reply. A reply that hits the cap stops mid-sentence. OpenAI-compatible APIs then report `finish_reason: "length"`; a reply that ended on its own reports `"stop"`. A canary that would have appeared after the cap is never seen, so a low cap can hide a leak.
