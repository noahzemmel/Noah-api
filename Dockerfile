# API: FastAPI + ffmpeg
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py noah_core.py /app/
RUN mkdir -p /app/data

# Render expects the app to bind to $PORT
ENV PORT=8080
CMD exec uvicorn server:app --host 0.0.0.0 --port ${PORT}