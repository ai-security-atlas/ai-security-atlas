Hugging Face Diffusers is a library of composable generative pipelines and scheduler tooling. It requires [diffusion generative models](../nodes/arch-diffusion.md): it supplies the assembly, scheduling, and orchestration around such models rather than being a model itself. Practitioners use it to combine a denoising model, a scheduler, and auxiliary components into a runnable pipeline.

## Trust boundary

Like any framework that loads model artifacts and pipeline components from external sources, adopting it means deciding to import and run code and weights obtained elsewhere. Diffusers itself is generation tooling; its security-relevant decisions therefore sit at the layers that grant that trust — how artifacts are loaded and whether their provenance is established — rather than in the composition logic. Distinguishing the tool from the [diffusion model](../nodes/arch-diffusion.md) it drives keeps those concerns separate.

For pipeline and scheduler specifics, see the cited documentation.
