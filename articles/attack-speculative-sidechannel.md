Speculative-decoding and token-stream side channels infer sensitive prompt content or generated assistant responses by observing packet sizes and inter-token burst timing over encrypted network links or shared serving instances. The objective is to [obtain protected information](../nodes/goal-information.md) without breaking transport encryption or reading server memory directly.

## How it works

Streaming [model-serving infrastructure](../nodes/system-serving.md) commonly transmits generated tokens incrementally over TLS as each [decoding](../nodes/concept-decoding.md) step completes. Even when encrypted, individual network frames can reveal the byte length of each emitted token (the *Whisper Leak* side channel) and the exact timing between emissions. When the server also employs speculative decoding — where a small draft model proposes multiple candidate tokens that the target [decoder-only language model](../nodes/arch-decoder.md) verifies in a single forward pass — the number of tokens accepted per verification burst depends directly on how predictable the sequence is under the prompt and datastore context. Observing these acceptance bursts and packet-length sequences allows an adversary to fingerprint private prompts or reconstruct portions of streamed responses.

This technique is a streaming and decoding-stage [variant of prompt-cache and timing side channels](../nodes/attack-cache-sidechannel.md) within the [privacy and data extraction](../nodes/family-privacy.md) family.

Mitigations include padding and batching streamed TLS frames to fixed byte/time intervals and applying [cache and timing isolation](../nodes/defense-cache-isolation.md) across tenants. Evaluation is measured under [privacy leakage and reconstruction metrics](../nodes/eval-privacy.md).
