# Multi-stage Dockerfile for Trading Dashboard
# Production-optimized Next.js build

# Stage 1: Dependencies
FROM node:20.11.0-alpine AS deps

# Install libc6-compat for Alpine compatibility
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY yarn.lock* ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Stage 2: Builder
FROM node:20.11.0-alpine AS builder

WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy source code
COPY . .

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION
ARG NEXT_PUBLIC_API_URL=http://localhost:8000

# Set environment variables for build
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# Build application
RUN npm run build

# Stage 3: Production runner
FROM node:20.11.0-alpine AS runner

# Install security updates
RUN apk upgrade --no-cache

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

WORKDIR /app

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Create necessary directories
RUN mkdir -p /app/logs && \
    chown -R nextjs:nodejs /app

# Switch to non-root user
USER nextjs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

# Expose port
EXPOSE 3000

# Set environment
ENV PORT=3000
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Add labels
LABEL \
    org.opencontainers.image.title="Trading Dashboard" \
    org.opencontainers.image.description="Next.js trading dashboard" \
    org.opencontainers.image.created=$BUILD_DATE \
    org.opencontainers.image.revision=$VCS_REF \
    org.opencontainers.image.version=$VERSION \
    org.opencontainers.image.vendor="Adaptive Trading System" \
    org.opencontainers.image.source="https://github.com/jthadison/tmt"

# Start command
CMD ["node", "server.js"]