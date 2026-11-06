# syntax=docker/dockerfile:1
# ---- Build stage -----------------------------------------------------------
# Base images are pinned by version and digest; bump them together (Dependabot).
FROM hugomods/hugo:0.165.0@sha256:cf1a2009a1edf807d0880af344c4dd13b40b308c340501128fb54e5aab17b009 AS builder

# Toolchain: Node (Vite/Pagefind), Python + uv (compiler), make (DRY build).
RUN apk add --no-cache nodejs npm python3 make
COPY --from=ghcr.io/astral-sh/uv:0.13.5@sha256:32a7bb39b496babbd997b0a39a4d66c126bdaf5661b302bf6f06abda8deca6ff /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy

WORKDIR /src

# Dependency layers first for cache reuse.
COPY package.json package-lock.json ./
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=cache,target=/root/.cache/uv \
    npm ci && uv sync --frozen

# Build the production site (compiler -> Vite -> Hugo -> Pagefind).
COPY . .
RUN make build-prod

# ---- Runtime stage ---------------------------------------------------------
FROM nginx:1.31.8-alpine@sha256:713fc2ebfd92e8217db451477182ee91944b123d2b1ee9fd5a8c6e91ca6c3a11

LABEL org.opencontainers.image.title="AI Security Atlas" \
      org.opencontainers.image.description="Static site for the AI Security Atlas, served by nginx on port 8080." \
      org.opencontainers.image.source="https://github.com/ai-security-atlas/ai-security-atlas" \
      org.opencontainers.image.url="https://ai-security-atlas.github.io/" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.authors="Lenin Alevski" \
      maintainer="AI Security Atlas maintainers"

COPY --from=builder /src/public /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

USER nginx
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
