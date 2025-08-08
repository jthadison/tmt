# Compliance Agent Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY tests/ ./tests/

# Copy shared utilities
COPY ../shared/ ./shared/

# Set Python path
ENV PYTHONPATH=/app

# Create non-root user
RUN useradd --create-home --shell /bin/bash compliance
RUN chown -R compliance:compliance /app
USER compliance

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8003/health', timeout=5)"

# Expose port
EXPOSE 8003

# Start command
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]