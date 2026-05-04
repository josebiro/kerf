# syntax=docker/dockerfile:1.7

# ---------- Stage 1: build SvelteKit frontend ----------
FROM node:22-slim AS frontend-build

ARG PUBLIC_SUPABASE_URL
ARG PUBLIC_SUPABASE_ANON_KEY
ARG PUBLIC_API_BASE_URL

ENV PUBLIC_SUPABASE_URL=$PUBLIC_SUPABASE_URL
ENV PUBLIC_SUPABASE_ANON_KEY=$PUBLIC_SUPABASE_ANON_KEY
ENV PUBLIC_API_BASE_URL=$PUBLIC_API_BASE_URL

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build && npm prune --omit=dev

# ---------- Stage 2: pull Caddy binary ----------
FROM caddy:2-alpine AS caddy-bin

# ---------- Stage 3: final runtime (python + node + caddy) ----------
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates gnupg \
        libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
        libffi-dev shared-mime-info \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get purge -y --auto-remove gnupg \
    && rm -rf /var/lib/apt/lists/*

# Caddy binary from official image
COPY --from=caddy-bin /usr/bin/caddy /usr/local/bin/caddy

# Backend
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app

# Frontend (built artifact + production node_modules)
WORKDIR /app/frontend
COPY --from=frontend-build /app/build ./build
COPY --from=frontend-build /app/package.json ./
COPY --from=frontend-build /app/node_modules ./node_modules

# Caddy config + entrypoint
COPY Caddyfile /etc/caddy/Caddyfile
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

WORKDIR /app
EXPOSE 8000

CMD ["/usr/local/bin/docker-entrypoint.sh"]
