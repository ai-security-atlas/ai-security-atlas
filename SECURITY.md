# Security Policy

## Scope

The AI Security Atlas is a **static** website with no backend, no user accounts,
and no server-side tracking. The main security surfaces are:

- the build pipeline (compiler, dependencies, CI), and
- the deployment token used to publish to the Pages repository.

## What this project is not

It documents AI security concepts for research and education. It does **not**
execute attacks, host payloads, or provide operational exploit instructions.
Please do not open issues or PRs requesting weaponized content.

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
