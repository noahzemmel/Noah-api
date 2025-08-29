#!/bin/bash

# Render build script for Noah MVP
echo "🚀 Building Noah MVP for Render..."

# Install system dependencies
apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
pip install --no-cache-dir -r requirements.txt

# Create necessary directories
mkdir -p audio

echo "✅ Build completed successfully!"
