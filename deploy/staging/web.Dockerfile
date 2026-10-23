FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_URL=https://staging.footballheritage.test:18443/api/v1
ENV VITE_API_URL=$VITE_API_URL VITE_ENABLE_DEBUG=false
RUN npm run build:production
FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY deploy/staging/Caddyfile /etc/caddy/Caddyfile
