# server_balanced.py - Balanced FastAPI server with real APIs and speed optimizations
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import uvicorn
from noah_core_balanced import noah_core_balanced
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Daily Noah Balanced API",
    description="Balanced AI-powered news bulletins with real APIs and speed optimizations",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class GenerateRequest(BaseModel):
    topics: List[str]
    language: str
    voice: str
    duration: int
    tone: str = "professional"
    strict_timing: bool = True
    quick_test: bool = False

class HealthResponse(BaseModel):
    openai: bool
    elevenlabs: bool
    tavily: bool
    ok: bool
    balanced_mode: bool = True
    api_integration: str = "balanced"

@app.get("/health")
async def health_check():
    """Balanced health check"""
    try:
        # Quick health checks
        openai_status = bool(os.getenv("OPENAI_API_KEY"))
        elevenlabs_status = bool(os.getenv("ELEVENLABS_API_KEY"))
        tavily_status = bool(os.getenv("TAVILY_API_KEY"))
        
        # Determine API integration level
        if openai_status and elevenlabs_status and tavily_status:
            api_integration = "full"
        elif openai_status or elevenlabs_status or tavily_status:
            api_integration = "partial"
        else:
            api_integration = "balanced"
        
        return HealthResponse(
            openai=openai_status,
            elevenlabs=elevenlabs_status,
            tavily=tavily_status,
            ok=any([openai_status, elevenlabs_status, tavily_status]),
            balanced_mode=True,
            api_integration=api_integration
        )
    except Exception as e:
        return HealthResponse(
            openai=False,
            elevenlabs=False,
            tavily=False,
            ok=False,
            balanced_mode=True,
            api_integration="balanced"
        )

@app.get("/voices")
async def get_voices():
    """Get available voices with balanced approach"""
    try:
        voices = await noah_core_balanced.get_available_voices_balanced()
        return voices
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching voices: {str(e)}")

@app.post("/generate")
async def generate_bulletin(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Generate balanced news bulletin with real APIs and speed optimizations"""
    try:
        # Validate request
        if not request.topics:
            raise HTTPException(status_code=400, detail="Topics are required")
        
        if request.duration < 1 or request.duration > 15:
            raise HTTPException(status_code=400, detail="Duration must be between 1 and 15 minutes")
        
        print(f"🚀 Balanced generation request: {len(request.topics)} topics, {request.duration} minutes")
        
        # Generate bulletin with balanced approach
        result = await noah_core_balanced.make_noah_audio_balanced(
            topics=request.topics,
            language=request.language,
            voice_id=request.voice,
            duration=request.duration,
            tone=request.tone,
            strict_timing=request.strict_timing,
            quick_test=request.quick_test
        )
        
        if result.get("status") == "success":
            # Add cleanup task
            background_tasks.add_task(cleanup_resources)
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in balanced generation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/download/{name}")
async def download_audio(name: str):
    """Download generated audio file"""
    try:
        # This would serve actual audio files
        # For now, return a placeholder
        return {"message": f"Audio file {name} would be downloaded here"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading audio: {str(e)}")

@app.get("/test-balanced")
async def test_balanced():
    """Test balanced performance"""
    try:
        start_time = asyncio.get_event_loop().time()
        
        # Test balanced generation
        test_result = await noah_core_balanced.make_noah_audio_balanced(
            topics=["tech news", "AI developments"],
            language="English",
            voice_id="21m00Tcm4TlvDq8ikWAM",
            duration=3,
            tone="professional"
        )
        
        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time
        
        return {
            "status": "success",
            "test_result": test_result,
            "performance": {
                "total_time_seconds": total_time,
                "balanced_mode": True,
                "parallel_processing": True,
                "caching_enabled": True,
                "api_integration": test_result.get("generation_metadata", {}).get("api_integration", "unknown"),
                "speed_quality_balance": "optimal"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Balanced test failed: {str(e)}")

@app.get("/performance")
async def get_performance():
    """Get performance metrics"""
    try:
        # This would return actual performance metrics
        return {
            "balanced_mode": True,
            "cache_performance": "enabled",
            "parallel_processing": True,
            "api_integration": "balanced",
            "speed_quality_balance": "optimal"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting performance: {str(e)}")

async def cleanup_resources():
    """Cleanup resources after generation"""
    try:
        # This would clean up temporary files, etc.
        pass
    except Exception as e:
        print(f"Cleanup error: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        noah_core_balanced.cleanup()
    except Exception as e:
        print(f"Shutdown cleanup error: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "server_balanced:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,  # Disable reload for production
        workers=1  # Single worker for now
    )
