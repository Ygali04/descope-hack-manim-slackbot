FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Manim
RUN apt-get update && apt-get install -y \
    ffmpeg \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    cmake \
    build-essential \
    pkg-config \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf-xlib-2.0-dev \
    libffi-dev \
    shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create non-root user for security
RUN groupadd -r manimpro && useradd -r -g manimpro manimpro

# Create required directories
RUN mkdir -p /tmp/manim_output /tmp/manim_cache && \
    chown -R manimpro:manimpro /tmp/manim_output /tmp/manim_cache /app

# Switch to non-root user
USER manimpro

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Set PYTHONPATH to include src directory and start the application
ENV PYTHONPATH=/app:/app/src
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"] 