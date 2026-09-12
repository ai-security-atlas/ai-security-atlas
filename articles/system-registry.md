Model registries store and distribute the artifacts a deployment depends on — checkpoints, adapters, configurations, and their revisions — along with licenses and upstream dependencies. As part of [deployment, monitoring and updates](../nodes/life-deploy.md), a registry is the channel through which a system decides which exact artifact to run.

## Trust boundary

The registry is a supply-chain junction. Whether a given artifact, revision, or dependency is the one it claims to be is a provenance question, and consumers usually trust what they pull. That makes it relevant to artifact, adapter or configuration substitution, where a swapped artifact is served in place of the intended one, and to unauthorized checkpoint or adapter theft, where distribution access is abused to exfiltrate weights. Dataset and artifact provenance is the corresponding control, establishing verifiable lineage for what the registry distributes.

For catalogued techniques and application-layer risks, see the cited sources.
