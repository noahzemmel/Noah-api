# server_simple.py - FastAPI backend for Noah MVP (Python 3.13 compatible)
import os
from pathlib import Path
from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from noah_core_simple import make_noah_audio, health_check, get_available_voices

# Initialize FastAPI app
app = FastAPI(
    title="Noah MVP API",
    description="Smart news bulletin generator with AI and TTS",
    version="2.4.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health():
    """Check the health of all APIs"""
    return health_check()

# Get available voices
@app.get("/voices")
async def voices():
    """Get available TTS voices"""
    try:
        voices_data = get_available_voices()
        return voices_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching voices: {str(e)}")

# Generate news bulletin
@app.post("/generate")
async def generate_bulletin(
    request: Dict = Body(...)
):
    """Generate a news bulletin with audio"""
    try:
        # Extract parameters
        topics = request.get("topics", [])
        language = request.get("language", "English")
        voice = request.get("voice", "21m00Tcm4TlvDq8ikWAM")
        duration = request.get("duration", 5)
        
        # Validate input
        if not topics:
            raise HTTPException(status_code=400, detail="Topics are required")
        
        if duration < 1 or duration > 15:
            raise HTTPException(status_code=400, detail="Duration must be between 1 and 15 minutes")
        
        # Set default values for other parameters
        tone = request.get("tone", "professional")
        lookback_hours = request.get("lookback_hours", 24)
        cap_per_topic = request.get("cap_per_topic", 5)
        strict_timing = request.get("strict_timing", False)
        
        # Generate the bulletin
        result = make_noah_audio(
            topics=topics,
            language=language,
            voice=voice,
            duration=duration,
            tone=tone,
            lookback_hours=lookback_hours,
            cap_per_topic=cap_per_topic,
            strict_timing=strict_timing
        )
        
        if result.get("status") == "success":
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating bulletin: {str(e)}")

# Download audio file
@app.get("/download/{name}")
async def download_audio(name: str):
    """Download an audio file by name"""
    try:
        audio_dir = os.getenv("AUDIO_DIR", "./audio")
        file_path = Path(audio_dir) / name
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        return FileResponse(
            path=file_path,
            filename=name,
            media_type="audio/mpeg",
            headers={"Content-Disposition": f"attachment; filename={name}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Noah API is running!",
        "version": "2.4.0",
        "endpoints": [
            "/health",
            "/generate",
            "/download/{name}",
            "/voices"
        ],
        "docs": "/docs"
    }

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
