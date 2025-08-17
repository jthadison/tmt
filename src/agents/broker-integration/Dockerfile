# Multi-stage build for broker integration service
FROM python:3.11-slim as builder

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim as runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 --home /app --shell /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/temp_retention /app/transaction_data && \
    chown -R appuser:appgroup /app

# Add health check script
COPY <<EOF /app/healthcheck.py
#!/usr/bin/env python3
import sys
import asyncio
import aiohttp
import os

async def health_check():
    """Health check endpoint for Docker"""
    try:
        port = os.getenv('HEALTH_CHECK_PORT', '8000')
        async with aiohttp.ClientSession() as session:
            async with session.get(f'http://localhost:{port}/health', timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    print("Health check passed")
                    return True
                else:
                    print(f"Health check failed with status: {resp.status}")
                    return False
    except Exception as e:
        print(f"Health check failed with error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(health_check())
    sys.exit(0 if result else 1)
EOF

RUN chmod +x /app/healthcheck.py && chown appuser:appgroup /app/healthcheck.py

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000 9090

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python /app/healthcheck.py || exit 1

# Environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    PROMETHEUS_PORT=9090 \
    LOG_LEVEL=INFO

# Default command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]