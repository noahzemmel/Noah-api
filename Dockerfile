# Dockerfile (API service) - Python 3.11 for compatibility
FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY noah_core.py server.py ./

# Create audio directory
RUN mkdir -p audio

# Render injects PORT
ENV PORT=8080
CMD exec uvicorn server:app --host 0.0.0.0 --port ${PORT} --workers 1