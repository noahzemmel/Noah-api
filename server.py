# server.py
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import os

from noah_core import (
    make_noah_audio,
    health_check,
)

app = FastAPI(title="Noah API", version="1.0.0")

@app.get("/", include_in_schema=False)
def root():
    return {
        "message": "Noah API is running!",
        "version": "1.0.0",
        "endpoints": ["/health", "/generate", "/download/{name}"],
        "docs": "/docs"
    }
    
# ---- CORS (allow your site to call the API) ----
# Set ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"
allowed = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed.split(",")] if allowed else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)
    
@app.get("/health")
def health():
    """Simple health check; returns {'ok': True} if keys are loaded."""
    return {"ok": health_check()}

@app.post("/generate")
def generate(payload: dict = Body(...)):
    """
    Body (JSON):
    {
      "queries": ["topic one","topic two"] | "topic one\ntopic two",
      "language": "English",
      "tone": "neutral and calm",
      "recent_hours": 24,
      "per_feed": 6,
      "cap_per_query": 6,
      "min_minutes": 8,
      "voice_id": "ELEVENLABS_VOICE_ID"
    }
    """
    try:
        queries = payload.get("queries", [])
        if isinstance(queries, str):
            # also accept newline-separated string
            queries = [q.strip() for q in queries.split("\n") if q.strip()]

        if not queries:
            return JSONResponse(
                {"error": "queries required (array or newline string)"},
                status_code=400,
            )

        language = payload.get("language", "English")
        tone = payload.get("tone", "neutral and calm")
        recent_hours = int(payload.get("recent_hours", 24))
        per_feed = int(payload.get("per_feed", 6))
        cap_per_query = int(payload.get("cap_per_query", 6))
        min_minutes = int(payload.get("min_minutes", 8))
        voice_id = payload.get("voice_id", "")

        result = make_noah_audio(
            queries=queries,
            language=language,
            tone=tone,
            recent_hours=recent_hours,
            per_feed=per_feed,
            cap_per_query=cap_per_query,
            min_minutes=min_minutes,
            voice_id=voice_id,
        )

        # Public URL for download route
        mp3_url = f"/download/{Path(result['file_path']).name}"

        return {
            "bullet_points": result["bullet_points"],
            "script": result["script"],
            "sources": result["sources"],                # exact items given to the model
            "minutes_target": result["minutes_target"],
            "duration_seconds": result["duration_seconds"],
            "mp3_url": mp3_url,
        }

    except Exception as e:
        # Bubble up error details to help debugging (safe for MVP)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/download/{name}")
def download(name: str):
    """Serve the generated MP3 by filename."""
    path = Path("out") / name
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path, media_type="audio/mpeg", filename=path.name)
