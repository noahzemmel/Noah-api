# server.py — FastAPI for Noah with inline audio + range support headers
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import os, requests, logging, traceback
from typing import List
from noah_core import make_noah_audio, health_check

app = FastAPI(title="Noah API", version="1.0.0")

@app.get("/", include_in_schema=False)
def root():
    return {"message":"Noah API is running!","version":"1.0.0",
            "endpoints":["/health","/generate","/download/{name}","/voices"],"docs":"/docs"}

allowed = os.getenv("ALLOWED_ORIGINS","*")
origins = [o.strip() for o in allowed.split(",")] if allowed else ["*"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                   allow_methods=["POST","GET","OPTIONS"], allow_headers=["*"])

@app.get("/health")
def health(): return {"ok": health_check()}

@app.get("/voices")
def voices():
    key = os.getenv("ELEVENLABS_API_KEY","")
    if not key: return []
    try:
        r = requests.get("https://api.elevenlabs.io/v1/voices",
                         headers={"xi-api-key": key}, timeout=20)
        if r.status_code == 200:
            js = r.json() or {}
            return [{"name": v.get("name","Unnamed"), "id": v.get("voice_id","")}
                    for v in (js.get("voices") or [])]
    except Exception:
        pass
    return []

logger = logging.getLogger("uvicorn.error")

def _as_str(x) -> str:
    if x is None: return ""
    if isinstance(x, list):
        flat = [str(i).strip() for i in x if i is not None and str(i).strip()]
        return flat[0] if flat else ""
    return str(x).strip()

def _as_queries(x) -> List[str]:
    out, seen = [], set()
    if x is None:
        items = []
    elif isinstance(x, str):
        items = x.replace(",", "\n").split("\n")
    elif isinstance(x, list):
        items = []
        for item in x:
            if isinstance(item, list): items.extend(item)
            else: items.append(item)
    else:
        items = [str(x)]
    for it in items:
        s = str(it).strip()
        if s and s.lower() not in seen:
            seen.add(s.lower()); out.append(s)
    return out

@app.post("/generate")
def generate(payload: dict = Body(...)):
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
            return JSONResponse({"error":"No queries provided."}, status_code=400)

        res = make_noah_audio(queries, language, tone, recent_hours,
                              per_feed, cap_per_query, minutes_target,
                              exact_minutes, voice_id)

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
        logger.error("Generate failed: %s\n%s", e, traceback.format_exc())
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/download/{name}")
def download(name: str):
    path = Path("/app/data") / name
    if not path.exists(): return JSONResponse({"error":"File not found."}, 404)
    # Use FileResponse but force headers that help browsers stream/seek
    resp = FileResponse(str(path), media_type="audio/mpeg", filename=name)
    resp.headers["Cache-Control"] = "public, max-age=86400"
    resp.headers["Content-Disposition"] = f'inline; filename="{name}"'
    resp.headers["Accept-Ranges"] = "bytes"
    return resp
