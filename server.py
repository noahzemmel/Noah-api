# server.py — FastAPI wrapper for Noah (exact-length enabled)
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pathlib import Path
import os

from noah_core import make_noah_audio, health_check

app = FastAPI(title="Noah API", version="1.0.0")

# ---- Root (nice landing) ----
@app.get("/", include_in_schema=False)
def root():
    return {
        "message": "Noah API is running!",
        "version": "1.0.0",
        "endpoints": ["/health", "/generate", "/download/{name}"],
        "docs": "/docs"
    }

# ---- CORS ----
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
    return {"ok": health_check()}

@app.post("/generate")
def generate(payload: dict = Body(...)):
    """
    Body JSON:
    {
      "queries": ["topic one", "topic two"] | "topic one\ntopic two",
      "language": "English",
      "tone": "confident and crisp",
      "recent_hours": 24,
      "per_feed": 6,
      "cap_per_query": 6,
      "min_minutes": 8,
      "minutes_target": 8,             # optional alias; if provided it overrides min_minutes
      "exact_minutes": true,            # default true; if false, no tempo adjustment
      "voice_id": "optional_voice_id"  # overrides server default
    }
    """
    try:
        queries = payload.get("queries") or []
        if isinstance(queries, str):
            # support textarea style
            queries = [q.strip() for q in queries.replace(",", "\n").split("\n") if q.strip()]

        language = payload.get("language", "English")
        tone = payload.get("tone", "confident and crisp")
        recent_hours = int(payload.get("recent_hours", 24))
        per_feed = int(payload.get("per_feed", 6))
        cap_per_query = int(payload.get("cap_per_query", 6))
        min_minutes = int(payload.get("min_minutes", 8))
        minutes_target = int(payload.get("minutes_target", min_minutes))
        exact_minutes = bool(payload.get("exact_minutes", True))
        voice_id = payload.get("voice_id", None)

        if not queries:
            return JSONResponse({"error":"No queries provided."}, status_code=400)

        result = make_noah_audio(
            queries=queries,
            language=language,
            tone=tone,
            recent_hours=recent_hours,
            per_feed=per_feed,
            cap_per_query=cap_per_query,
            minutes_target=minutes_target,
            exact_minutes=exact_minutes,
            voice_id=voice_id,
        )

        # map to response and expose a download URL
        mp3_path = result.get("file_path")
        name = Path(mp3_path).name if mp3_path else "noah.mp3"
        return {
            "bullet_points": result.get("bullet_points"),
            "script": result.get("script"),
            "sources": result.get("sources"),
            "mp3_url": f"/download/{name}",
            "minutes_target": result.get("minutes_target"),
            "duration_seconds": result.get("duration_seconds"),
            "playback_rate_applied": result.get("playback_rate_applied"),
            "generated_at": result.get("generated_at"),
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/download/{name}")
def download(name: str):
    path = Path("/app/data") / name
    if not path.exists():
        return JSONResponse({"error":"File not found."}, status_code=404)
    return FileResponse(str(path), media_type="audio/mpeg", filename=name)
