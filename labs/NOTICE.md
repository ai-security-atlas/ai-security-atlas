# Third-party notices for committed model weights

The labs commit a few small derived weight files so that lab steps run without
training first. Each is listed here with what it was derived from.

| Files | Derived from | Upstream license |
| :--- | :--- | :--- |
| `_shared/tinylm/guard/`, and the LoRA adapters under `adapt-lora/assets/adapters/`, `arch-transformer/assets/trigger-lora/`, `attack-adapter-tamper/assets/adapters/`, `attack-sft-poison/assets/adapters/` and `life-sft/assets/adapters/` | LoRA adapters trained in these labs on [HuggingFaceTB/SmolLM2-135M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct) (the adapters name `atlas-tinylm/lantern-guard-135m` or `community/lantern-desk`, which are lab-local names for that base plus the guard adapter) | Apache-2.0 |
| `_shared/vision_zoo/checkpoints/*.safetensors` | Small CNN/MLP classifiers trained in-repo on scikit-learn's bundled 8x8 digits (`sklearn.datasets.load_digits`, a copy of the UCI Optical Recognition of Handwritten Digits test set) | Dataset: CC BY 4.0 (UCI) |

The adapters contain only the low-rank deltas, not the base model weights. Every
other model a lab uses (Ollama models, Hugging Face checkpoints, the RAG
embedder) is downloaded by the learner at setup time under its own license;
check the model card before reuse.
