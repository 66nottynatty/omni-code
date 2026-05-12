FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy root package.json and workspace package.jsons
COPY package.json package-lock.json* turbo.json ./
COPY apps/web/package.json ./apps/web/package.json
COPY packages/sdk/package.json ./packages/sdk/package.json

RUN npm install

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build the SDK first because web depends on it
RUN npx turbo run build --filter=@omnicode/sdk
RUN npx turbo run build --filter=@omnicode/web

# Production image
FROM base AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# The standalone output includes only the necessary files for a production deployment
# but it requires being in the right directory structure or having them copied correctly.
# For Turborepo, the standalone output is usually in apps/web/.next/standalone
COPY --from=builder /app/apps/web/public ./apps/web/public
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

# Standalone server is at apps/web/server.js usually
CMD ["node", "apps/web/server.js"]
