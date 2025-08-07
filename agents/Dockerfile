# Multi-stage Dockerfile for Trading Agents
# Optimized for production deployment with security and performance

# Stage 1: Base Python environment
FROM python:3.11.8-slim as python-base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH="/app"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    gcc \
    libc6-dev \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Dependencies installation
FROM python-base as deps

WORKDIR /app

# Copy dependency files
COPY shared/python-utils/pyproject.toml shared/python-utils/
COPY agents/requirements.txt agents/
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r agents/requirements.txt && \
    pip install --no-cache-dir -e .

# Stage 3: Production image
FROM python-base as production

# Create non-root user
RUN groupadd --gid 1000 trading && \
    useradd --uid 1000 --gid trading --shell /bin/bash --create-home trading

# Set working directory
WORKDIR /app

# Copy installed dependencies from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code
COPY agents/ agents/
COPY shared/python-utils/ shared/python-utils/

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R trading:trading /app

# Switch to non-root user
USER trading

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Add labels
LABEL \
    org.opencontainers.image.title="Trading Agents" \
    org.opencontainers.image.description="AI agents for adaptive trading system" \
    org.opencontainers.image.created=$BUILD_DATE \
    org.opencontainers.image.revision=$VCS_REF \
    org.opencontainers.image.version=$VERSION \
    org.opencontainers.image.vendor="Adaptive Trading System" \
    org.opencontainers.image.source="https://github.com/jthadison/tmt"

# Start command
CMD ["python", "-m", "uvicorn", "agents.main:app", "--host", "0.0.0.0", "--port", "8000"]