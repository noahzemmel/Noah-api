# server.py — Noah API with async jobs and /result/{job_id}
from __future__ import annotations
import os, uuid, time, threading, traceback
from typing import Dict, Any, Optional, Callable
from pathlib import Path

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
    # Prefer PUBLIC_BASE_URL if you set it on Render; otherwise build from the request
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
    Return a minimal list of voices for the UI dropdown.
    If you want to list ElevenLabs voices dynamically, you can extend this later.
    """
    # Static minimal set; “Use API default” means let TTS provider pick.
    items = [
        {"id": "", "name": "Use API default"},
        {"id": "alloy", "name": "Alloy (OpenAI)"},
    ]
    # If an ELEVENLABS_VOICE_ID is present, expose it as a choice
    v11 = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
    if v11:
        items.append({"id": v11, "name": "ElevenLabs default"})
    return {"voices": items}

@app.post("/generate")
def generate(payload: dict = Body(...)):
    """
    Kick off a generation job. Returns a job_id immediately.
    The worker thread writes progress logs and final result into JOBS[job_id].
    """
    cleanup_jobs()
    job_id = uuid.uuid4().hex
    set_job(job_id, status="queued", logs=[], error=None)

    # Normalize/validate payload fields the core expects
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
            add_log(job_id, "Calibrating voice")
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
            # Build a download URL
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
        # upgrade relative mp3_url to absolute for the browser
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

# ------------- Uvicorn entrypoint -------------
def _port() -> int:
    try:
        return int(os.getenv("PORT", "10000"))
    except Exception:
        return 10000

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=_port(), reload=False)
