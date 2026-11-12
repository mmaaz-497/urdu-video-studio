# syntax=docker/dockerfile:1
# Production image for the Next.js frontend (output: "standalone"). Built on the dev
# machine by infra/deploy.sh — never on the VPS (a Next build needs >1 GB RAM) (T092).

ARG NODE_IMAGE=node:20-bookworm-slim

# ---- deps: install exactly what package-lock.json pins ------------------------------
FROM ${NODE_IMAGE} AS deps
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# ---- build ---------------------------------------------------------------------------
FROM ${NODE_IMAGE} AS build
WORKDIR /src
ENV NEXT_TELEMETRY_DISABLED=1
# Both are read at BUILD time: NEXT_PUBLIC_* is inlined into the browser bundle and
# rewrites() (next.config.ts) is baked into the routes manifest. BACKEND_ORIGIN is the
# backend's address on the stack's internal network.
ARG NEXT_PUBLIC_API_BASE_URL=/api
ARG BACKEND_ORIGIN=http://backend:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL BACKEND_ORIGIN=$BACKEND_ORIGIN
COPY --from=deps /src/node_modules ./node_modules
COPY . .
RUN npm run build

# ---- runtime: only the standalone server, static assets and public/ -----------------
FROM ${NODE_IMAGE} AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
COPY --from=build --chown=node:node /src/.next/standalone ./
COPY --from=build --chown=node:node /src/.next/static ./.next/static
COPY --from=build --chown=node:node /src/public ./public
# The official image's built-in unprivileged "node" user (uid 1000).
USER node
EXPOSE 3000
CMD ["node", "server.js"]
