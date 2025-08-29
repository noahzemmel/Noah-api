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

# Debug endpoint to test OpenAI API key
@app.get("/debug/openai")
async def debug_openai():
    """Debug endpoint to test OpenAI API key"""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {
                "error": "OPENAI_API_KEY not found in environment",
                "api_key_length": 0,
                "api_key_preview": "None"
            }
        
        # Test the API key
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        
        return {
            "api_key_found": True,
            "api_key_length": len(api_key),
            "api_key_preview": f"{api_key[:10]}...{api_key[-10:]}" if len(api_key) > 20 else api_key,
            "openai_response_status": response.status_code,
            "openai_response_ok": response.ok,
            "openai_response_text": response.text[:200] if response.text else "No response text"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "api_key_found": bool(os.getenv("OPENAI_API_KEY")),
            "api_key_length": len(os.getenv("OPENAI_API_KEY", ""))
        }

# Test precision timing endpoint
@app.post("/test-timing")
async def test_timing(request: Dict = Body(...)):
    """Test endpoint for precision timing system"""
    try:
        topics = request.get("topics", ["test"])
        duration = request.get("duration", 2)
        strict_timing = request.get("strict_timing", True)
        
        print(f"🧪 Testing precision timing: {duration} minutes, strict: {strict_timing}")
        
        result = make_noah_audio(
            topics=topics,
            language="English",
            voice="21m00Tcm4TlvDq8ikWAM",
            duration=duration,
            tone="professional",
            strict_timing=strict_timing
        )
        
        return {
            "test_type": "precision_timing",
            "requested_duration": duration,
            "strict_timing": strict_timing,
            "result": result
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "test_type": "precision_timing"
        }

# Test endpoint to debug request handling
@app.post("/test")
async def test_endpoint(request: Dict = Body(...)):
    """Test endpoint to debug request handling"""
    return {
        "message": "Test endpoint working",
        "received_data": request,
        "data_type": str(type(request)),
        "data_keys": list(request.keys()) if isinstance(request, dict) else "Not a dict",
        "topics_value": request.get("topics"),
        "topics_type": str(type(request.get("topics"))) if "topics" in request else "No topics key"
    }

# Generate news bulletin
@app.post("/generate")
async def generate_bulletin(
    request: Dict = Body(...)
):
    """Generate a news bulletin with audio"""
    try:
        # Debug: Log the entire request
        print(f"DEBUG: Received request: {request}")
        print(f"DEBUG: Request type: {type(request)}")
        print(f"DEBUG: Request keys: {list(request.keys()) if isinstance(request, dict) else 'Not a dict'}")
        
        # Extract parameters with better error handling
        topics = request.get("topics", [])
        language = request.get("language", "English")
        voice = request.get("voice", "21m00Tcm4TlvDq8ikWAM")
        duration = request.get("duration", 5)
        tone = request.get("tone", "professional")
        
        # New precision timing parameter
        strict_timing = request.get("strict_timing", True)  # Default to precision timing
        
        # Quick test mode for faster processing
        quick_test = request.get("quick_test", False)
        
        # Debug: Log extracted values
        print(f"DEBUG: Extracted topics: {topics}")
        print(f"DEBUG: Topics type: {type(topics)}")
        print(f"DEBUG: Topics length: {len(topics) if isinstance(topics, list) else 'Not a list'}")
        print(f"DEBUG: Duration: {duration} minutes")
        print(f"DEBUG: Strict timing: {strict_timing}")
        print(f"DEBUG: Quick test mode: {quick_test}")
        
        # Better validation with detailed error messages
        if not topics:
            print(f"DEBUG: Topics validation failed - topics is empty or falsy")
            raise HTTPException(
                status_code=400, 
                detail=f"Topics are required. Received: {topics} (type: {type(topics)})"
            )
        
        # Handle case where topics might be a string instead of list
        if isinstance(topics, str):
            topics = [topic.strip() for topic in topics.split('\n') if topic.strip()]
            print(f"DEBUG: Converted string topics to list: {topics}")
        
        # Final validation after conversion
        if not topics or (isinstance(topics, list) and len(topics) == 0):
            print(f"DEBUG: Final topics validation failed")
            raise HTTPException(
                status_code=400, 
                detail=f"Topics must contain at least one non-empty topic. Received: {topics}"
            )
        
        if duration < 1 or duration > 15:
            raise HTTPException(status_code=400, detail="Duration must be between 1 and 15 minutes")
        
        # Set default values for other parameters
        lookback_hours = request.get("lookback_hours", 24)
        cap_per_topic = request.get("cap_per_topic", 5)
        
        # Adjust parameters for quick test mode
        if quick_test:
            lookback_hours = min(lookback_hours, 12)  # Reduce lookback time
            cap_per_topic = min(cap_per_topic, 2)     # Reduce articles per topic
            print(f"DEBUG: Quick test mode enabled - reduced lookback: {lookback_hours}h, cap: {cap_per_topic}")
        
        print(f"DEBUG: About to call make_noah_audio with topics: {topics}, duration: {duration}, strict_timing: {strict_timing}, quick_test: {quick_test}")
        
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
        print(f"DEBUG: Unexpected error: {str(e)}")
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
