# Frontend SvelteKit SSR
# Base figee : node:22.14.0-alpine3.21

FROM node:22.14.0-alpine3.21 AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

COPY . .
RUN npm run build \
    && npm prune --omit=dev --legacy-peer-deps

# --- Image finale -----------------------------------------------------------
FROM node:22.14.0-alpine3.21

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOST=0.0.0.0

COPY --from=builder --chown=node:node /app/build ./build
COPY --from=builder --chown=node:node /app/node_modules ./node_modules
COPY --from=builder --chown=node:node /app/package.json ./package.json
COPY --from=builder --chown=node:node /app/themes ./themes

USER node

EXPOSE 3000

CMD ["node", "build"]
