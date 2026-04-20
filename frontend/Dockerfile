# syntax=docker/dockerfile:1

FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM node:20-slim
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --no-create-home appuser

WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .

USER appuser
EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e \
    "require('http').get('http://localhost:3000/health', r => \
    process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))" \
    || exit 1

CMD ["node", "app.js"]