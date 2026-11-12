# Diffusion in one paragraph

Labs that lean on this most: [LAB-45 · Same weights, ten times the cost](../concept-samplers/README.md) and [LAB-51 · The prompt is a vector](../concept-conditioning/README.md).

An image diffusion model learns one skill: given a noisy image, predict the noise in it. During training, it takes real images, adds a random amount of noise, and learns to predict exactly what was added. To draw something new, you start from pure noise. At each step the model predicts the noise, and a sampler uses that prediction to make the image a little cleaner. After 20 to 1,000 such steps an image appears. A text-to-image model also reads your prompt at every step, so the cleaned-up image matches the prompt. The terms below name each piece.

### Noise

Noise here means random numbers drawn from a bell curve (a Gaussian), one per pixel value, added to the image. A training image gets a random amount of it, from a light speckle to pure static. The seed fixes the starting noise, so the same seed and settings give the same image.

### Denoiser and U-Net

The denoiser is the neural network that predicts the noise. It takes the noisy image, the step number and, for text-to-image models, the prompt's vectors. Most widely used models use a U-Net: a network that shrinks the image step by step to capture the overall layout, then grows it back to full size, with shortcut connections that carry fine detail across. Newer models use a transformer in the same role. LAB-45's `google/ddpm-cifar10-32` is a 35.7M-parameter U-Net that draws 32×32 images.

### Scheduler, sampler and steps

The scheduler (the diffusers library's name for a sampler) is the rule that turns each noise prediction into the next, slightly cleaner image. A step is one call to the denoiser. The scheduler holds no weights, only a small config, so you can swap it without touching the model. Fewer steps cost less time, and too few blur or distort the image. The step count sets the cost of a request, which is why [LAB-45](../concept-samplers/README.md) caps it.

### DDPM and DDIM

DDPM and DDIM are two schedulers that work with the same trained model. DDPM (denoising diffusion probabilistic models) adds a little fresh random noise at every step and was designed to run as many steps as training used, typically 1,000. DDIM (denoising diffusion implicit models) adds no fresh noise by default, so the starting noise alone fixes the image, and it gives good images in 20 to 50 steps. Later schedulers such as Euler and DPM-Solver++ cut the step count further.

### Latents

Latent diffusion runs the whole process on a compressed version of the image, the latents. A separate network (a VAE) compresses images into latents and decodes the final latents back into pixels. In Stable Diffusion 1.x a `512 × 512 × 3` image becomes a `64 × 64 × 4` latent: 786,432 numbers down to 16,384, 48 times fewer. LAB-45's model works directly on pixels and has no VAE.

### Conditioning and the text encoder

Conditioning is the extra input that steers the denoiser, usually the prompt. A text encoder turns the prompt into vectors first: Stable Diffusion 1.x uses CLIP's text encoder, which outputs 77 rows of 768 numbers. The denoiser reads them through [attention](inside-a-transformer-block.md#attention) at every step. The image model never sees your words, only these vectors, which is the gap [LAB-51](../concept-conditioning/README.md) measures.

### Guidance scale

The guidance scale (from classifier-free guidance) sets how strongly the image follows the prompt. At every step the denoiser predicts the noise twice, once with the prompt and once with an empty prompt, and combines the two as `empty + scale × (with prompt - empty)`. A scale of 1 uses the prompted prediction as it is. Stable Diffusion commonly uses 7.5. Higher values follow the prompt more literally and eventually oversaturate the image. Above 1, every step costs two denoiser calls.
