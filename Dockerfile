# syntax=docker/dockerfile:1
# ---- Build stage -----------------------------------------------------------
FROM hugomods/hugo:latest AS builder

# Toolchain: Node (Vite/Pagefind), Python + uv (compiler), make (DRY build).
RUN apk add --no-cache nodejs npm python3 make
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /src

# Dependency layers first for cache reuse.
COPY package.json package-lock.json ./
COPY pyproject.toml uv.lock README.md ./
COPY src/ai_security_atlas ./src/ai_security_atlas
RUN npm ci && uv sync --frozen

# Build the production site (compiler -> Vite -> Hugo -> Pagefind).
COPY . .
RUN make build-prod

# ---- Runtime stage ---------------------------------------------------------
FROM nginx:alpine

COPY --from=builder /src/public /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

USER nginx
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
