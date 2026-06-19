# syntax=docker/dockerfile:1.7

FROM node:20-alpine AS base
WORKDIR /app
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

FROM base AS build-stage
COPY . ./
ARG VITE_API_BASE=/api
ARG VITE_API_MOCK_ENABLED=false
ARG VITE_DISABLE_ACCESS_MANAGEMENT=false
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_PUBLISHABLE_KEY
RUN set -a; \
    if [ -f .env.prod ]; then . ./.env.prod; fi; \
    set +a; \
    export VITE_API_BASE="${VITE_API_BASE:-/api}"; \
    export VITE_API_MOCK_ENABLED="${VITE_API_MOCK_ENABLED:-false}"; \
    export VITE_DISABLE_ACCESS_MANAGEMENT="${VITE_DISABLE_ACCESS_MANAGEMENT:-false}"; \
    export VITE_SUPABASE_URL="${VITE_SUPABASE_URL}"; \
    export VITE_SUPABASE_PUBLISHABLE_KEY="${VITE_SUPABASE_PUBLISHABLE_KEY}"; \
    npm run build -- --mode prod

FROM base AS development
COPY . ./
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM caddy:2.10 AS production
COPY --from=build-stage /app/dist /usr/share/caddy
COPY Caddyfile /etc/caddy/Caddyfile
