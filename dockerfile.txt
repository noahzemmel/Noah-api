# Dockerfile
FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# environment for FastAPI
ENV PORT=8080
EXPOSE 8080

# Start the API
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]