# Performance Regression Detection Service Dockerfile

FROM python:3.11-slim

LABEL maintainer="TMT DevOps Team"
LABEL description="Performance regression detection service for TMT trading system"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r regression && useradd -r -g regression regression

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY regression_detector.py .
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create necessary directories
RUN mkdir -p logs data models && \
    chown -R regression:regression /app

# Switch to non-root user
USER regression

# Health check endpoint (simple HTTP server for health checks)
COPY health_server.py .

# Expose health check port
EXPOSE 8080

# Default command
CMD ["python", "regression_detector.py"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1