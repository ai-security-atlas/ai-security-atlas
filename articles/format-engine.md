A compiled inference engine is an executable, optimized execution plan produced for a particular runtime and, often, specific hardware — not a container of raw weights. Where a data-only tensor file simply stores parameters to be read back, an engine bakes the computation itself into a form built for fast execution. This distinction matters: a file that holds numbers is not the same artifact as a plan that runs.

Producing and running an engine depends on [model loaders and executable repository code](../nodes/system-loader.md) to interpret and dispatch it. That coupling to executable code, rather than to inert data, is what makes its handling worth scrutiny.

## Security scope

Because an engine is executable rather than declarative, its provenance and integrity are relevant to the concerns raised by [unsafe checkpoint deserialization](../nodes/attack-unsafe-load.md) — this describes scope, where an artifact carries execution semantics, not a claim that any given engine is vulnerable. Whether a specific runtime introduces exposure depends on how the engine is built, loaded, and trusted.

For the behavior and security considerations of a particular engine format, defer to the cited runtime documentation.
