# Multi-stage Dockerfile for Execution Engine
# Optimized for performance and security

# Stage 1: Builder
FROM rust:1.75.0-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    pkg-config \
    libssl-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Cargo files
COPY Cargo.toml Cargo.lock ./

# Create dummy source to cache dependencies
RUN mkdir src && \
    echo "fn main() {}" > src/main.rs && \
    echo "pub fn dummy() {}" > src/lib.rs

# Build dependencies (this will be cached)
RUN cargo build --release && \
    rm -rf src target/release/deps/execution*

# Copy real source code
COPY src/ src/

# Build application
RUN cargo build --release && \
    strip target/release/execution-engine

# Stage 2: Runtime
FROM debian:bookworm-slim as runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    ca-certificates \
    libpq5 \
    libssl3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 trading && \
    useradd --uid 1000 --gid trading --shell /bin/bash --create-home trading

# Set working directory
WORKDIR /app

# Copy binary from builder stage
COPY --from=builder /app/target/release/execution-engine /usr/local/bin/execution-engine

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R trading:trading /app

# Switch to non-root user
USER trading

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Add labels
LABEL \
    org.opencontainers.image.title="Execution Engine" \
    org.opencontainers.image.description="High-performance trading execution engine" \
    org.opencontainers.image.created=$BUILD_DATE \
    org.opencontainers.image.revision=$VCS_REF \
    org.opencontainers.image.version=$VERSION \
    org.opencontainers.image.vendor="Adaptive Trading System" \
    org.opencontainers.image.source="https://github.com/jthadison/tmt"

# Start command
CMD ["execution-engine"]