# server_perfect_timing.py - GUARANTEED EXACT TIMING
"""
🎯 DAILY NOAH - PERFECT TIMING SERVER

GUARANTEED:
1. ⚡ Fast generation (<60 seconds)
2. 🎯 EXACT timing (iterative until perfect)
3. 📰 Comprehensive depth (15-20 articles)
"""

import os
import time
import uuid
import threading
import re
from pathlib import Path
from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

from noah_core_perfect_timing import (
    make_noah_audio_perfect_timing,
    health_check,
    get_available_voices
)

progress_storage: Dict[str, Dict[str, Any]] = {}

app = FastAPI(
    title="Daily Noah Perfect Timing API",
    description="Guaranteed exact duration match",
    version="5.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Daily Noah Perfect Timing API",
        "version": "5.0.0",
        "guarantees": [
            "🎯 EXACT timing match (iterative verification)",
            "⚡ Fast generation (<60s)",
            "📰 Comprehensive depth (15-20 articles)"
        ],
        "endpoints": ["/health", "/generate", "/progress/{progress_id}", "/result/{progress_id}", "/download/{name}", "/voices"],
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return health_check()

@app.get("/voices")
async def get_voices():
    try:
        return get_available_voices()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching voices: {str(e)}")

@app.get("/progress/{progress_id}")
async def get_progress(progress_id: str):
    if progress_id not in progress_storage:
        raise HTTPException(status_code=404, detail="Progress ID not found")
    return progress_storage[progress_id]

@app.get("/result/{progress_id}")
async def get_result(progress_id: str):
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
    """Generate bulletin with GUARANTEED exact timing"""
    try:
        progress_id = str(uuid.uuid4())
        
        progress_storage[progress_id] = {
            "status": "starting",
            "progress_percent": 0,
            "current_step": "Initializing...",
            "estimated_time_remaining": 60,
            "start_time": time.time(),
            "error": None
        }
        
        topics = request.get("topics", [])
        language = request.get("language", "English")
        voice = request.get("voice", "21m00Tcm4TlvDq8ikWAM")
        duration = request.get("duration", 5.0)
        tone = request.get("tone", "professional")
        lookback_hours = request.get("lookback_hours", 24)
        cap_per_topic = request.get("cap_per_topic", 5)
        strict_timing = request.get("strict_timing", True)
        
        if not topics:
            raise HTTPException(status_code=400, detail="Topics are required")
        
        if duration < 1 or duration > 30:
            raise HTTPException(status_code=400, detail="Duration must be between 1 and 30 minutes")
        
        progress_storage[progress_id].update({
            "progress_percent": 5,
            "current_step": "Starting perfect timing generation...",
            "estimated_time_remaining": 60
        })
        
        def generate_in_background():
            try:
                def update_progress(percent: int, step: str):
                    if progress_id in progress_storage:
                        elapsed = time.time() - progress_storage[progress_id]["start_time"]
                        estimated_total = elapsed / (percent / 100) if percent > 0 else 60
                        remaining = max(0, int(estimated_total - elapsed))
                        
                        progress_storage[progress_id].update({
                            "progress_percent": percent,
                            "current_step": step,
                            "estimated_time_remaining": remaining
                        })
                
                result = make_noah_audio_perfect_timing(
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
                    progress_storage[progress_id]["result"] = result
                    progress_storage[progress_id]["status"] = "completed"
                    progress_storage[progress_id]["progress_percent"] = 100
                    progress_storage[progress_id]["current_step"] = "Perfect timing achieved!"
                    progress_storage[progress_id]["estimated_time_remaining"] = 0
                else:
                    progress_storage[progress_id]["status"] = "error"
                    progress_storage[progress_id]["error"] = result.get("error", "Unknown error")
                    progress_storage[progress_id]["current_step"] = f"Error: {result.get('error')}"
                
            except Exception as e:
                progress_storage[progress_id]["status"] = "error"
                progress_storage[progress_id]["error"] = str(e)
                progress_storage[progress_id]["current_step"] = f"Error: {str(e)}"
                print(f"❌ Generation error: {e}")
        
        thread = threading.Thread(target=generate_in_background)
        thread.daemon = True
        thread.start()
        
        return {
            "status": "started",
            "progress_id": progress_id,
            "message": "Perfect timing generation started",
            "estimated_time": "~60s"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        if progress_id in progress_storage:
            progress_storage[progress_id]["status"] = "error"
            progress_storage[progress_id]["error"] = str(e)
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/download/{name}")
async def download_audio(name: str):
    try:
        if not re.match(r'^[\w\-\.]+\.mp3$', name):
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        audio_dir = Path("audio")
        file_path = audio_dir / name
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        return FileResponse(path=str(file_path), media_type="audio/mpeg", filename=name)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Download error: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    Path("audio").mkdir(exist_ok=True)
    
    port = int(os.getenv("PORT", 8000))
    
    print(f"""
🎯 DAILY NOAH PERFECT TIMING SERVER
====================================
Port: {port}
🎯 Guaranteed exact duration match
⚡ Fast generation (<60s)
📰 Comprehensive (15-20 articles)
====================================
""")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

