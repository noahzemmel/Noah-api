# server.py — FastAPI wrapper for Noah (exact-length enabled + robust input handling)

from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import os, requests, logging, traceback

from noah_core import make_noah_audio, health_check

app = FastAPI(title="Noah API", version="1.0.0")

# ---------- Root ----------
@app.get("/", include_in_schema=False)
def root():
    return {
        "message": "Noah API is running!",
        "version": "1.0.0",
        "endpoints": ["/health", "/generate", "/download/{name}", "/voices"],
        "docs": "/docs",
    }

# ---------- CORS ----------
allowed = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed.split(",")] if allowed else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# ---------- Health ----------
@app.get("/health")
def health():
    return {"ok": health_check()}

# ---------- Voices (so UI can list voices without exposing keys there) ----------
@app.get("/voices")
def voices():
    key = os.getenv("ELEVENLABS_API_KEY", "")
    if not key:
        return []
    try:
        r = requests.get("https://api.elevenlabs.io/v1/voices",
                         headers={"xi-api-key": key}, timeout=20)
        if r.status_code == 200:
            j = r.json() or {}
            v = j.get("voices") or []
            return [{"name": it.get("name", "Unnamed"), "id": it.get("voice_id", "")} for it in v]
        return []
    except Exception:
        return []

# ---------- Helpers to normalize inputs ----------
logger = logging.getLogger("uvicorn.error")

def _as_str(x) -> str:
    """Return a clean string regardless of input type (string/list/None)."""
    if x is None:
        return ""
    if isinstance(x, list):
        flat = [str(i).strip() for i in x if i is not None and str(i).strip()]
        if flat:
            return flat[0]
        return str(x)
    return str(x).strip()

def _as_queries(x) -> list[str]:
    """Return a flat, de-duplicated list of query strings from string/list/nested list."""
    out, seen = [], set()
    if x is None:
        items = []
    elif isinstance(x, str):
        items = x.replace(",", "\n").split("\n")
    elif isinstance(x, list):
        items = []
        for item in x:
            if isinstance(item, list):
                items.extend(item)
            else:
                items.append(item)
    else:
        items = [str(x)]
    for it in items:
        s = str(it).strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out

# ---------- Generate ----------
@app.post("/generate")
def generate(payload: dict = Body(...)):
    """
    Body JSON (any field may be string OR list; this route normalizes types):
    {
      "queries": ["topic one", "topic two"] | "topic one\ntopic two",
      "language": "English",
      "tone": "confident and crisp",
      "recent_hours": 24,
      "per_feed": 6,
      "cap_per_query": 6,
      "min_minutes": 8,
      "minutes_target": 8,          # preferred; overrides min_minutes if provided
      "exact_minutes": true,
      "voice_id": "optional voice id"
    }
    """
    try:
        queries = _as_queries(payload.get("queries"))
        language = _as_str(payload.get("language") or "English")
        tone = _as_str(payload.get("tone") or "confident and crisp")
        recent_hours = int(payload.get("recent_hours", 24) or 24)
        per_feed = int(payload.get("per_feed", 6) or 6)
        cap_per_query = int(payload.get("cap_per_query", 6) or 6)
        minutes_target = int(payload.get("minutes_target", payload.get("min_minutes", 8)) or 8)
        exact_minutes = bool(payload.get("exact_minutes", True))
        voice_id = _as_str(payload.get("voice_id")) or None

        if not queries:
            return JSONResponse({"error": "No queries provided."}, status_code=400)

        res = make_noah_audio(
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

        name = Path(res["file_path"]).name
        return {
            "bullet_points": res.get("bullet_points"),
            "script": res.get("script"),
            "sources": res.get("sources"),
            "mp3_url": f"/download/{name}",
            "minutes_target": res.get("minutes_target"),
            "duration_seconds": res.get("duration_seconds"),
            "playback_rate_applied": res.get("playback_rate_applied"),
            "generated_at": res.get("generated_at"),
        }

    except Exception as e:
        # Log full traceback to Render logs and return the message to the client
        logger.error("Generate failed: %s\n%s", e, traceback.format_exc())
        return JSONResponse({"error": str(e)}, status_code=500)

# ---------- Download ----------
@app.get("/download/{name}")
def download(name: str):
    path = Path("/app/data") / name
    if not path.exists():
        return JSONResponse({"error": "File not found."}, status_code=404)
    return FileResponse(str(path), media_type="audio/mpeg", filename=name)
