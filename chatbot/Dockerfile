FROM node:22-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY --chown=node:node index.js ./
COPY --chown=node:node flows ./flows
COPY --chown=node:node services ./services
USER node
ENV NODE_ENV=production
CMD ["node", "index.js"]
