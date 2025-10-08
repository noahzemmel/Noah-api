# server_final.py - Final Optimized FastAPI Backend
"""
🎯 DAILY NOAH FINAL SERVER
Fixes all three critical issues:
1. Accurate timing (corrected WPM rates)
2. Deep, informative content
3. Fast generation (<45 seconds)
"""

import os
import time
import uuid
import threading
import re
from pathlib import Path
from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from noah_core_final import (
    make_noah_audio_final,
    health_check,
    get_available_voices
)

# Progress tracking storage
progress_storage: Dict[str, Dict[str, Any]] = {}

# Initialize FastAPI
app = FastAPI(
    title="Daily Noah Final API",
    description="Fixed timing, depth, and speed",
    version="4.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Daily Noah Final API - All Issues Fixed!",
        "version": "4.0.0",
        "fixes": [
            "✅ Accurate timing (corrected WPM: 130-140)",
            "✅ Deep, informative content",
            "✅ Fast generation (<45 seconds)"
        ],
        "endpoints": [
            "/health",
            "/generate",
            "/progress/{progress_id}",
            "/result/{progress_id}",
            "/download/{name}",
            "/voices"
        ],
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return health_check()

@app.get("/voices")
async def get_voices():
    """Get available voices"""
    try:
        voices = get_available_voices()
        return voices
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching voices: {str(e)}")

@app.get("/progress/{progress_id}")
async def get_progress(progress_id: str):
    """Get generation progress"""
    if progress_id not in progress_storage:
        raise HTTPException(status_code=404, detail="Progress ID not found")
    
    return progress_storage[progress_id]

@app.get("/result/{progress_id}")
async def get_result(progress_id: str):
    """Get final generation result"""
    if progress_id not in progress_storage:
        raise HTTPException(status_code=404, detail="Progress ID not found")
    
    progress_data = progress_storage[progress_id]
    
    if progress_data.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Generation not yet complete")
    
    result = progress_data.get("result")
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    return result

@app.post("/generate")
async def generate_bulletin(request: Dict = Body(...)):
    """
    Generate news bulletin - ALL ISSUES FIXED
    """
    try:
        # Create progress tracking ID
        progress_id = str(uuid.uuid4())
        
        # Initialize progress
        progress_storage[progress_id] = {
            "status": "starting",
            "progress_percent": 0,
            "current_step": "Initializing...",
            "estimated_time_remaining": 40,
            "start_time": time.time(),
            "error": None
        }
        
        # Extract parameters
        topics = request.get("topics", [])
        language = request.get("language", "English")
        voice = request.get("voice", "21m00Tcm4TlvDq8ikWAM")
        duration = request.get("duration", 5.0)
        tone = request.get("tone", "professional")
        lookback_hours = request.get("lookback_hours", 24)
        cap_per_topic = request.get("cap_per_topic", 5)
        strict_timing = request.get("strict_timing", True)
        
        # Validate inputs
        if not topics:
            raise HTTPException(status_code=400, detail="Topics are required")
        
        if duration < 1 or duration > 30:
            raise HTTPException(status_code=400, detail="Duration must be between 1 and 30 minutes")
        
        # Update progress
        progress_storage[progress_id].update({
            "progress_percent": 5,
            "current_step": "Starting generation...",
            "estimated_time_remaining": 40
        })
        
        # Start generation in background thread
        def generate_in_background():
            try:
                # Progress callback
                def update_progress(percent: int, step: str):
                    if progress_id in progress_storage:
                        elapsed = time.time() - progress_storage[progress_id]["start_time"]
                        estimated_total = elapsed / (percent / 100) if percent > 0 else 40
                        remaining = max(0, int(estimated_total - elapsed))
                        
                        progress_storage[progress_id].update({
                            "progress_percent": percent,
                            "current_step": step,
                            "estimated_time_remaining": remaining
                        })
                
                # Generate bulletin
                result = make_noah_audio_final(
                    topics=topics,
                    language=language,
                    voice=voice,
                    duration=duration,
                    tone=tone,
                    lookback_hours=lookback_hours,
                    cap_per_topic=cap_per_topic,
                    strict_timing=strict_timing,
                    progress_callback=update_progress
                )
                
                if result.get("status") == "success":
                    # Store the final result
                    progress_storage[progress_id]["result"] = result
                    progress_storage[progress_id]["status"] = "completed"
                    progress_storage[progress_id]["progress_percent"] = 100
                    progress_storage[progress_id]["current_step"] = "Bulletin ready!"
                    progress_storage[progress_id]["estimated_time_remaining"] = 0
                else:
                    # Handle error
                    progress_storage[progress_id]["status"] = "error"
                    progress_storage[progress_id]["error"] = result.get("error", "Unknown error")
                    progress_storage[progress_id]["current_step"] = f"Error: {result.get('error', 'Unknown error')}"
                
            except Exception as e:
                progress_storage[progress_id]["status"] = "error"
                progress_storage[progress_id]["error"] = str(e)
                progress_storage[progress_id]["current_step"] = f"Error: {str(e)}"
                print(f"❌ Background generation error: {e}")
        
        # Start background thread
        thread = threading.Thread(target=generate_in_background)
        thread.daemon = True
        thread.start()
        
        # Return progress_id immediately
        return {
            "status": "started",
            "progress_id": progress_id,
            "message": "Generation started - fast, deep, accurate",
            "estimated_time": "~40s"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        if progress_id in progress_storage:
            progress_storage[progress_id]["status"] = "error"
            progress_storage[progress_id]["error"] = str(e)
        print(f"❌ Error in generate endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating bulletin: {str(e)}")

@app.get("/download/{name}")
async def download_audio(name: str):
    """Download audio file"""
    try:
        # Security: Only allow alphanumeric and underscores, plus .mp3
        if not re.match(r'^[\w\-\.]+\.mp3$', name):
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        audio_dir = Path("audio")
        file_path = audio_dir / name
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        return FileResponse(
            path=str(file_path),
            media_type="audio/mpeg",
            filename=name
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error downloading audio: {e}")
        raise HTTPException(status_code=500, detail=f"Error downloading audio: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    # Ensure audio directory exists
    Path("audio").mkdir(exist_ok=True)
    
    port = int(os.getenv("PORT", 8000))
    
    print(f"""
🎯 DAILY NOAH FINAL SERVER - ALL ISSUES FIXED
==============================================
🚀 Starting server on port {port}
✅ Accurate timing (WPM: 130-140)
✅ Deep, informative content
✅ Fast generation (<45s)
==============================================
""")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

