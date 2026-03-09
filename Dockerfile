# Standard Dockerfile for Chronicon
# Optimized for: archive, update, validate, migrate commands
# Security: Hardened, minimal attack surface, non-root user

# Stage 1: Builder stage
FROM python:3.14-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libffi-dev \
    libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only requirements first for caching
WORKDIR /build
COPY pyproject.toml ./

# Install dependencies only (not the package itself)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir beautifulsoup4 html2text jinja2 rich

# Stage 2: Runtime stage (minimal)
FROM python:3.14-slim

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    wget && \
    rm -rf /var/lib/apt/lists/* && \
    # Create non-root user
    useradd -m -u 1000 -s /sbin/nologin chronicon && \
    # Create directories
    mkdir -p /archives /app && \
    chown -R chronicon:chronicon /archives /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=chronicon:chronicon src/chronicon/ /app/chronicon/
COPY --chown=chronicon:chronicon templates/ /templates/
COPY --chown=chronicon:chronicon static/ /static/

# Set environment
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CHRONICON_OUTPUT_DIR=/archives \
    HOME=/home/chronicon

# Set working directory
WORKDIR /archives

# Switch to non-root user
USER chronicon

# Security: Remove write permissions
RUN chmod -R go-w /app 2>/dev/null || true

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD chronicon validate --output-dir /archives || exit 1

# Labels for metadata
LABEL maintainer="Chronicon" \
      version="1.0.0" \
      description="Chronicon container for archiving" \
      base="python:3.12-slim" \
      security="hardened"

# Volume for archives
VOLUME ["/archives"]

# Default entrypoint
ENTRYPOINT ["python", "-m", "chronicon.cli"]

# Default command
CMD ["--help"]
