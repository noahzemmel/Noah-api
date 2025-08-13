# server.py — async jobs with progress; resilient to long runs
import os, uuid, time, threading
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from noah_core import make_noah_audio, health_check

APP_NAME = "Noah API"
VERSION = "1.1.0"

app = FastAPI(title=APP_NAME, version=VERSION)

allowed = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed.split(",")] if allowed else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

JOBS: Dict[str, Dict[str, Any]] = {}
JOB_TTL_SECONDS = 60 * 60

DATA_DIR = Path(os.getenv("NOAH_DATA_DIR", "/app/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _now() -> float: return time.time()

def _background_generate(job_id: str, payload: Dict[str, Any]) -> None:
    def progress(stage: str):
        meta = JOBS.get(job_id)
        if meta:
            meta["progress"] = stage
            meta["updated_at"] = _now()

    try:
        queries = payload.get("queries") or []
        if isinstance(queries, str):
            queries = [q.strip() for q in queries.splitlines() if q.strip()]

        result = make_noah_audio(
            queries=queries,
            language=payload.get("language", "English"),
            tone=payload.get("tone", "confident and crisp"),
            recent_hours=int(payload.get("recent_hours", 24)),
            per_feed=int(payload.get("per_feed", 4)),
            cap_per_query=int(payload.get("cap_per_query", 6)),
            minutes_target=int(payload.get("min_minutes", 8)),
            exact_minutes=bool(payload.get("exact_minutes", True)),
            voice_id=payload.get("voice_id") or None,
            progress=progress,
        )

        name = Path(result["file_path"]).name
        mp3_url = f"/download/{name}"

        JOBS[job_id].update({
            "status": "done",
            "updated_at": _now(),
            "result": {
                "bullet_points": result["bullet_points"],
                "script": result["script"],
                "sources": result["sources"],
                "duration_seconds": result["duration_seconds"],
                "minutes_target": result["minutes_target"],
                "playback_rate_applied": result["playback_rate_applied"],
                "mp3_url": mp3_url,
                "calibrated_wps": result.get("calibrated_wps"),
                "narration_word_count": result.get("narration_word_count"),
                "correction_passes": result.get("correction_passes"),
                "attempts": result.get("attempts"),
            }
        })
    except Exception as e:
        JOBS[job_id].update({
            "status": "error",
            "updated_at": _now(),
            "error": str(e)[:2000],
        })

def _start_job(payload: Dict[str, Any]) -> str:
    job_id = uuid.uuid4().hex
    JOBS[job_id] = {"status": "pending", "created_at": _now(), "updated_at": _now(), "progress": "queued"}
    t = threading.Thread(target=_background_generate, args=(job_id, payload), daemon=True)
    t.start()
    return job_id

def _prune_jobs() -> None:
    now = _now()
    expired = [jid for jid, meta in JOBS.items() if now - meta.get("updated_at", now) > JOB_TTL_SECONDS]
    for jid in expired:
        JOBS.pop(jid, None)

@app.get("/")
def root():
    return {"message": f"{APP_NAME} is running!", "version": VERSION,
            "endpoints": ["/health", "/voices", "/generate", "/result/{job_id}", "/download/{name}"], "docs": "/docs"}

@app.get("/health")
def health():
    return {"ok": health_check()}

@app.get("/voices")
def voices():
    try:
        import requests
        r = requests.get("https://api.elevenlabs.io/v1/voices",
                         headers={"xi-api-key": os.getenv("ELEVENLABS_API_KEY","")}, timeout=20)
        out = r.json() if r.status_code == 200 else {"voices":[]}
    except Exception:
        out = {"voices":[]}
    return [{"id": v.get("voice_id"), "name": v.get("name")} for v in out.get("voices", [])]

@app.post("/generate")
def generate(payload: Dict[str, Any] = Body(...)):
    _prune_jobs()
    if not isinstance(payload.get("queries"), (list, str)):
        return JSONResponse({"error":"queries must be list or newline-delimited string"}, status_code=400)
    return {"job_id": _start_job(payload), "status": "started"}

@app.get("/result/{job_id}")
def result(job_id: str):
    meta = JOBS.get(job_id)
    if not meta:
        return JSONResponse({"error":"unknown job_id"}, status_code=404)
    return meta

@app.get("/download/{name}")
def download(name: str):
    path = DATA_DIR / name
    if not path.exists():
        return JSONResponse({"error": "file not found"}, status_code=404)
    return FileResponse(
        str(path), media_type="audio/mpeg", filename=name,
        headers={"Content-Disposition": f'inline; filename="{name}"',
                 "Cache-Control": "public, max-age=86400",
                 "Accept-Ranges": "bytes"}
    )
