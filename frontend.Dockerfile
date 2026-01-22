FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# Build SvelteKit application
# Note: User must ensure adapter-node is used for Docker environment
RUN npm run build
# Prune dev dependencies for cleaner image
RUN npm prune --production

# --- Final Stage ---
FROM node:20-alpine

WORKDIR /app
COPY --from=builder /app/build ./build
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/themes ./themes

# Expose SvelteKit port
EXPOSE 3000

ENV PORT=3000
ENV HOST=0.0.0.0
# The frontend needs to talk to the backend, url defined in docker-compose usually
# ENV API_URL=http://api:8000 

CMD ["node", "build"]
