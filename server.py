# server.py
import os
from pathlib import Path
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from noah_core import make_noah_audio, health_check

app = FastAPI(title="Noah API", version="2.3.0")

# CORS
allowed = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed.split(",")] if allowed else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST","GET","OPTIONS"],
    allow_headers=["*"],
)

AUDIO_DIR = os.getenv("AUDIO_DIR", "/tmp")
Path(AUDIO_DIR).mkdir(parents=True, exist_ok=True)

@app.get("/")
def root():
    return {"message":"Noah API is running!",
            "version": "2.3.0",
            "endpoints": ["/health","/generate","/download/{name}"],
            "docs": "/docs"}

@app.get("/health")
def health():
    return health_check()

@app.post("/generate")
def generate(payload: dict = Body(...)):
    """
    Body example:
    {
      "queries": ["Arsenal transfer news", "semiconductors"],
      "minutes": 8,
      "language": "English",
      "tone": "confident and crisp",
      "lookback_hours": 24,
      "cap_per_topic": 6,
      "strict_timing": true,
      "voice_id": "optional_elevenlabs_voice_id"
    }
    """
    try:
        queries = payload.get("queries") or []
        if isinstance(queries, str):
            queries = [x.strip() for x in queries.split("\n") if x.strip()]

        minutes = int(payload.get("minutes", 8))
        language = payload.get("language","English")
        tone = payload.get("tone","neutral")
        lookback = int(payload.get("lookback_hours", 24))
        cap = int(payload.get("cap_per_topic", 6))
        strict = bool(payload.get("strict_timing", True))
        voice_id = payload.get("voice_id","")

        data = make_noah_audio(
            queries=queries,
            minutes=minutes,
            language=language,
            tone=tone,
            lookback_hours=lookback,
            cap_per_topic=cap,
            strict_timing=strict,
            voice_id=voice_id
        )
        # turn path into URL
        name = Path(data["mp3_path"]).name
        url = f"/download/{name}"
        data["mp3_url"] = url
        return JSONResponse(data)

    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.get("/download/{name}")
def dl(name: str):
    fpath = os.path.join(AUDIO_DIR, name)
    if not os.path.exists(fpath):
        return JSONResponse({"error":"file not found"}, status_code=404)
    return FileResponse(fpath, media_type="audio/mpeg", filename=name)
