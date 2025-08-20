# Dockerfile (API service)
FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY noah_core.py server.py ./

# Render injects PORT
ENV PORT=8080
CMD exec uvicorn server:app --host 0.0.0.0 --port ${PORT} --workers 1