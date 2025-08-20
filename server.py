# server.py — Noah API with async jobs and provider-aware /voices
from __future__ import annotations
import os, uuid, time, threading, traceback
from typing import Dict, Any
from pathlib import Path

import requests
from fastapi import FastAPI, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from noah_core import make_noah_audio, health_check, DATA_DIR

# ------------------- CORS -------------------
def get_allowed_origins() -> list[str]:
    allowed = os.getenv("ALLOWED_ORIGINS", "*").strip()
    if not allowed or allowed == "*":
        return ["*"]
    return [o.strip() for o in allowed.split(",") if o.strip()]

app = FastAPI(title="Noah API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# ------------------- Job store -------------------
JOBS: Dict[str, Dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()
TTL_SECONDS = 60 * 60  # keep jobs for 1 hour

def set_job(job_id: str, **fields):
    with JOBS_LOCK:
        job = JOBS.setdefault(job_id, {"status": "queued", "logs": [], "created": time.time()})
        job.update(fields)

def add_log(job_id: str, msg: str):
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id]["logs"].append(msg)
            JOBS[job_id]["updated"] = time.time()

def cleanup_jobs():
    now = time.time()
    with JOBS_LOCK:
        for jid in list(JOBS.keys()):
            if now - JOBS[jid].get("created", now) > TTL_SECONDS:
                JOBS.pop(jid, None)

# ------------------- Helpers -------------------
def file_url(request: Request, filename: str) -> str:
    base = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    if not base:
        base = str(request.base_url).rstrip("/")
    return f"{base}/download/{filename}"

# ------------------- Routes -------------------
@app.get("/")
def root():
    return {
        "message": "Noah API is running!",
        "version": "1.0.0",
        "endpoints": ["/health", "/generate", "/result/{job_id}", "/download/{name}", "/voices"],
        "docs": "/docs",
    }

@app.get("/health")
def health():
    ok = health_check()
    return {"ok": all(ok.values()), **ok}

@app.get("/voices")
def voices():
    """
    Return a provider-aware list of voices.
    Always contains:
      - Use API default (provider=auto, id="")
      - Alloy (OpenAI) (provider=openai, id="alloy")
    If ELEVENLABS_API_KEY is configured, we fetch ElevenLabs voices
    and include up to 15 for the dropdown.
    """
    items = [
        {"id": "", "name": "Use API default", "provider": "auto"},
        {"id": "alloy", "name": "Alloy", "provider": "openai"},
    ]

    xi = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if xi:
        try:
            r = requests.get(
                "https://api.elevenlabs.io/v1/voices",
                headers={"xi-api-key": xi},
                timeout=20,
            )
            r.raise_for_status()
            data = r.json()
            for v in (data.get("voices") or [])[:15]:
                items.append({
                    "id": v.get("voice_id", ""),
                    "name": v.get("name", "Voice"),
                    "provider": "elevenlabs",
                })
        except Exception as e:
            # Don't fail the UI if ElevenLabs listing fails
            print("WARN: could not list ElevenLabs voices:", e)

    return {"voices": items}

@app.post("/generate")
def generate(payload: dict = Body(...)):
    cleanup_jobs()
    job_id = uuid.uuid4().hex
    set_job(job_id, status="queued", logs=[], error=None)

    queries_raw   = payload.get("queries", "")
    language      = payload.get("language", "English")
    tone          = payload.get("tone", "confident and crisp")
    recent_hours  = int(payload.get("recent_hours", 24))
    cap_per_query = int(payload.get("cap_per_query", 6))
    min_minutes   = float(payload.get("min_minutes", 8))
    exact_minutes = bool(payload.get("exact_minutes", True))
    voice_id      = payload.get("voice_id") or None

    def on_progress(msg: str):
        add_log(job_id, f"• {msg}")

    def worker():
        try:
            set_job(job_id, status="running")
            add_log(job_id, "Calibrating Voice")
            result = make_noah_audio(
                queries_raw=queries_raw,
                language=language,
                tone=tone,
                recent_hours=recent_hours,
                cap_per_query=cap_per_query,
                min_minutes=min_minutes,
                exact_minutes=exact_minutes,
                voice_id=voice_id,
                on_progress=on_progress,
            )
            mp3_path = result.get("mp3_path", "")
            filename = Path(mp3_path).name if mp3_path else ""
            set_job(job_id, status="done", result={
                "script": result.get("script",""),
                "bullets": result.get("bullets", []),
                "sources": result.get("sources", []),
                "mp3_url": f"/download/{filename}",
                "mp3_name": filename,
                "actual_minutes": result.get("actual_minutes"),
                "target_minutes": result.get("target_minutes"),
                "playback_rate": result.get("playback_rate"),
                "tts_provider": result.get("tts_provider"),
            })
            add_log(job_id, "Done ✓")
        except Exception as e:
            traceback.print_exc()
            set_job(job_id, status="error", error=str(e))
            add_log(job_id, f"ERROR: {e}")

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id}

@app.get("/result/{job_id}")
def job_result(job_id: str, request: Request):
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not found"}, status_code=404)
    out = {"status": job.get("status"), "logs": job.get("logs", [])}
    if job.get("error"):
        out["error"] = job["error"]
    if job.get("result"):
        res = dict(job["result"])
        if res.get("mp3_url", "").startswith("/download/"):
            res["mp3_url"] = file_url(request, res["mp3_name"])
        out["result"] = res
    return out

@app.get("/download/{name}")
def download(name: str):
    p = Path(DATA_DIR) / name
    if not p.exists():
        return JSONResponse({"error": "file not found"}, status_code=404)
    return FileResponse(str(p), media_type="audio/mpeg", filename=name)

def _port() -> int:
    try:
        return int(os.getenv("PORT", "10000"))
    except Exception:
        return 10000

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=_port(), reload=False)
