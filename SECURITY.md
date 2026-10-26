# Security Policy

## Scope

The AI Security Atlas is a **static** website with no backend, no user accounts,
and no server-side tracking. The main security surfaces are:

- the build pipeline (compiler, dependencies, CI),
- the deployment token used to publish to the Pages repository, and
- the local-only lab code under `labs/` (see [Labs](#labs)).

## What this project is

The AI Security Atlas is a learning platform to understand and learn AI security
through realistic scenarios. The website and its data execute nothing and host no
payloads. The optional `labs/` directory ships local-only reproductions whose
payloads are inert by policy (a fixed canary string or a marker file in the lab's
own `work/` folder). Please do not open issues or PRs requesting weaponized
content.

## Labs

Lab payloads are inert by policy. Report as a security issue any lab step that
sends a payload over the network, writes outside the lab's `work/` folder,
targets a non-canary output, or contacts a third-party service without the
learner choosing the external-API backend (other than the documented, pinned
image, package and model downloads in a lab's Setup and Step 1, cached in the
lab volumes).

## Reporting a vulnerability

If you find a security issue in the build tooling, CI, or a way the published
site could be abused (e.g. content injection, dependency compromise), please
report it privately:

- Use **GitHub Security Advisories** ("Report a vulnerability") on the source
  repository, or
- email the maintainer listed in `hugo.toml` / commit history.

Please do not disclose publicly until a fix is available. We aim to acknowledge
reports promptly and will credit reporters who wish to be named.

## Content accuracy

Factual errors or unsupported claims in topic content are not security
vulnerabilities but are still important — please open a normal issue or PR with
the correction and a primary source.

## Handling of secrets

- `DEPLOY_TOKEN` (Pages deploy) is stored as a GitHub Actions secret and used
  only by the deploy workflow. It should be a least-privilege token scoped to the
  target Pages repository.
- No credentials, analytics keys, or private data are committed to the repo.
