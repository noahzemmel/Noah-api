# server_lightning.py - Lightning-Fast FastAPI Backend for Daily Noah
"""
⚡ DAILY NOAH LIGHTNING BACKEND
The fastest, most reliable AI briefing generation system.

Features:
- Lightning-fast generation (under 60 seconds)
- Bulletproof timeout protection
- Real-time progress tracking
- Production-ready reliability
- Comprehensive error handling
"""

import os
import time
import uuid
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import signal
import threading

# FastAPI and core dependencies
from fastapi import FastAPI, Body, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import lightning core functionality
from noah_core_lightning import (
    make_noah_audio_lightning,
    health_check_lightning,
    get_available_voices_lightning
)

# ============================================================================
# LIGHTNING FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="Daily Noah Lightning API",
    description="The fastest AI briefing generation system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# LIGHTNING STORAGE
# ============================================================================

# In-memory storage for progress tracking
progress_storage: Dict[str, Dict[str, Any]] = {}
result_storage: Dict[str, Dict[str, Any]] = {}

# ============================================================================
# LIGHTNING ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Daily Noah Lightning API",
        "version": "1.0.0",
        "status": "operational",
        "features": [
            "Lightning-fast generation (under 60 seconds)",
            "Bulletproof timeout protection",
            "Real-time progress tracking",
            "Production-ready reliability"
        ],
        "endpoints": {
            "health": "/health",
            "generate": "/generate",
            "progress": "/progress/{progress_id}",
            "result": "/result/{progress_id}",
            "voices": "/voices",
            "download": "/download/{filename}"
        }
    }

@app.get("/health")
async def health():
    """Lightning-fast health check"""
    return health_check_lightning()

@app.get("/voices")
async def voices():
    """Get available voices with lightning-fast caching"""
    try:
        return get_available_voices_lightning()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching voices: {str(e)}")

@app.post("/generate")
async def generate_bulletin_lightning(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Generate lightning-fast news bulletin with timeout protection"""
    try:
        # Parse request body
        body = await request.json()
        
        # Validate required fields
        if "topics" not in body or not body["topics"]:
            raise HTTPException(status_code=400, detail="Topics are required")
        
        topics = body["topics"]
        if not isinstance(topics, list) or len(topics) == 0:
            raise HTTPException(status_code=400, detail="Topics must be a non-empty list")
        
        # Extract parameters with defaults
        language = body.get("language", "English")
        voice = body.get("voice", "21m00Tcm4TlvDq8ikWAM")
        duration = body.get("duration", 5)
        tone = body.get("tone", "professional")
        
        # Validate duration
        if not isinstance(duration, int) or duration < 1 or duration > 30:
            raise HTTPException(status_code=400, detail="Duration must be between 1 and 30 minutes")
        
        # Create progress tracking ID
        progress_id = str(uuid.uuid4())
        
        # Initialize progress
        progress_storage[progress_id] = {
            "status": "starting",
            "progress_percent": 0,
            "current_step": "Initializing lightning generation...",
            "estimated_time_remaining": 60,  # Always estimate 60 seconds max
            "start_time": time.time(),
            "request_data": {
                "topics": topics,
                "language": language,
                "voice": voice,
                "duration": duration,
                "tone": tone
            }
        }
        
        # Start generation in background with timeout protection
        background_tasks.add_task(
            generate_bulletin_background_lightning,
            progress_id,
            topics,
            language,
            voice,
            duration,
            tone
        )
        
        return {
            "status": "started",
            "progress_id": progress_id,
            "message": "Lightning generation started",
            "estimated_completion_time": 60,
            "max_timeout": 60
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting generation: {str(e)}")

async def generate_bulletin_background_lightning(
    progress_id: str,
    topics: List[str],
    language: str,
    voice: str,
    duration: int,
    tone: str
):
    """Background task for lightning-fast bulletin generation with timeout protection"""
    try:
        # Update progress: Starting
        progress_storage[progress_id].update({
            "status": "in_progress",
            "progress_percent": 10,
            "current_step": "Fetching news with lightning speed..."
        })
        
        # Set up timeout protection
        timeout_seconds = 60  # Maximum 60 seconds
        start_time = time.time()
        
        # Generate the bulletin with timeout protection
        try:
            result = await asyncio.wait_for(
                make_noah_audio_lightning(
                    topics=topics,
                    language=language,
                    voice=voice,
                    duration=duration,
                    tone=tone
                ),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            # Handle timeout gracefully
            elapsed_time = time.time() - start_time
            progress_storage[progress_id].update({
                "status": "timeout",
                "error": f"Generation timed out after {elapsed_time:.1f} seconds",
                "current_step": "Generation timed out - please try again"
            })
            return
        
        # Store result
        result_storage[progress_id] = result
        
        # Update progress: Complete
        progress_storage[progress_id].update({
            "status": "completed",
            "progress_percent": 100,
            "current_step": "Lightning bulletin ready!",
            "result": result
        })
        
    except Exception as e:
        # Update progress: Error
        elapsed_time = time.time() - start_time
        progress_storage[progress_id].update({
            "status": "error",
            "error": str(e),
            "current_step": f"Error after {elapsed_time:.1f}s: {str(e)}"
        })

@app.get("/progress/{progress_id}")
async def get_progress(progress_id: str):
    """Get current progress for a generation request"""
    try:
        if progress_id not in progress_storage:
            raise HTTPException(status_code=404, detail="Progress not found")
        
        progress = progress_storage[progress_id]
        
        # Calculate estimated time remaining
        if progress["status"] == "in_progress":
            elapsed = time.time() - progress["start_time"]
            remaining = max(0, 60 - elapsed)  # Always show remaining time
            progress["estimated_time_remaining"] = int(remaining)
        
        return progress
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting progress: {str(e)}")

@app.get("/result/{progress_id}")
async def get_result(progress_id: str):
    """Get the final result of a generation request"""
    try:
        if progress_id not in result_storage:
            raise HTTPException(status_code=404, detail="Result not found")
        
        return result_storage[progress_id]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting result: {str(e)}")

@app.get("/download/{name}")
async def download_audio(name: str):
    """Download generated audio file"""
    try:
        audio_dir = os.getenv("AUDIO_DIR", "./audio")
        file_path = Path(audio_dir) / name
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        return FileResponse(
            path=file_path,
            filename=name,
            media_type="audio/mpeg"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")

# ============================================================================
# LIGHTNING ERROR HANDLING
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Lightning-fast HTTP exception handling"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Lightning-fast general exception handling"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path
        }
    )

# ============================================================================
# LIGHTNING STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Lightning logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Start the lightning server
    uvicorn.run(
        "server_lightning:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1,
        log_level="info",
        access_log=True,
        timeout_keep_alive=30,
        timeout_graceful_shutdown=30
    )
