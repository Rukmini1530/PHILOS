# Hugging Face Spaces Dockerfile for AstroPixel Backend
# Minimal, reliable setup for free tier

FROM python:3.11-slim

# Install system dependencies - minimal set
# Remove python3-numpy from system packages to avoid conflicts with pip-installed numpy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    curl \
    && apt-get remove -y python3-numpy 2>/dev/null || true \
    && rm -rf /var/lib/apt/lists/*

# Set environment
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV PYTHONUNBUFFERED=1

# Non-root user (HF requirement)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# Install dependencies - let pip resolve numpy from requirements
COPY requirements-hf.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-hf.txt

# Copy app
COPY app/ ./app/
RUN mkdir -p uploads tiles datasets temp static

EXPOSE 7860
# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
