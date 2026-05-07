# Multi-stage build Dockerfile - xmind-to-md
# Supports Docker/K8s PORT variable, default 30000

# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --target /install -r requirements.txt


# Stage 2: Final minimal image
FROM python:3.11-slim

# Environment variables
ENV PORT=30000
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DOCKER_CONTAINER=true

# Copy installed dependencies from builder stage
COPY --from=builder /install /usr/local/lib/python3.11/site-packages

# Create non-root user for security
RUN groupadd -r flaskuser && useradd -r -g flaskuser flaskuser

WORKDIR /app

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p /app/temp /app/output /app/uploads && \
    chown -R flaskuser:flaskuser /app

# Switch to non-root user
USER flaskuser

# Expose port (default 30000, can be overridden by environment variable)
EXPOSE 30000

# Start application (run_web.py reads PORT env variable)
CMD ["python", "run_web.py"]