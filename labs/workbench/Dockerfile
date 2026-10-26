# syntax=docker/dockerfile:1
# AI Security Atlas labs: shared workbench image (CPU-only PyTorch + transformers + scanners).
# Used by two compose services: `workbench` (network on, repo read-write) and
# `sandbox` (no network, read-only, hardened). See labs/compose.yaml.
FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

RUN apt-get update \
 && apt-get install -y --no-install-recommends git unzip ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /opt/workbench
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project

# Unprivileged user; /cache/hf is world-writable so a different LAB_UID can still use the HF cache.
# An empty named volume copies this ownership and mode on first use.
RUN useradd -m -u 1000 student \
 && mkdir -p /cache/hf /labs \
 && chown 1000:1000 /cache/hf /labs \
 && chmod 0777 /cache/hf

ENV PATH=/opt/venv/bin:$PATH \
    HF_HOME=/cache/hf \
    HOME=/tmp \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HUB_DISABLE_PROGRESS_BARS=1 \
    TRANSFORMERS_VERBOSITY=error \
    TQDM_DISABLE=1 \
    GIT_TERMINAL_PROMPT=0 \
    GIT_CONFIG_COUNT=1 \
    GIT_CONFIG_KEY_0=safe.directory \
    GIT_CONFIG_VALUE_0=*

WORKDIR /labs
USER student
CMD ["bash"]
