# server.py
from __future__ import annotations
import os, json, uuid, asyncio, time, traceback
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from noah_core import make_noah_audio, DATA_DIR

app = FastAPI(title="Noah API", version="1.0.0")

# ---- CORS
allowed = os.getenv("ALLOWED_ORIGINS", "")
origins = [o.strip() for o in allowed.split(",") if allowed] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# ---- Simple in-memory job store
JOBS: Dict[str, Dict[str, Any]] = {}
JOB_TTL_SECONDS = int(os.getenv("NOAH_JOB_TTL_SECONDS", "3600"))

def _set_job(jid: str, **kwargs):
    JOBS[jid].update(kwargs)
    JOBS[jid]["_ts"] = time.time()

def _prune_jobs():
    now = time.time()
    for k in list(JOBS.keys()):
        if now - JOBS[k].get("_ts", now) > JOB_TTL_SECONDS:
            try:
                p = JOBS[k].get("result",{}).get("mp3_path")
                if p and Path(p).exists():
                    Path(p).unlink(missing_ok=True)
            except: pass
            JOBS.pop(k, None)

def _run_job_sync(jid: str, payload: Dict[str, Any]):
    """Runs in a background thread via FastAPI BackgroundTasks (no event loop issues)."""
    try:
        def progress(msg: str):
            logs = JOBS[jid].setdefault("log", [])
            logs.append(msg)
            JOBS[jid]["log"] = logs
            JOBS[jid]["_ts"] = time.time()

        _set_job(jid, status="working")
        res = make_noah_audio(
            queries_raw=payload.get("queries") or payload.get("topics"),
            language=payload.get("language","English"),
            tone=payload.get("tone","confident and crisp"),
            recent_hours=int(payload.get("recent_hours", 24)),
            cap_per_query=int(payload.get("cap_per_query", 6)),
            min_minutes=float(payload.get("min_minutes", 8)),
            exact_minutes=bool(payload.get("exact_minutes", True)),
            voice_id=payload.get("voice_id") or os.getenv("ELEVENLABS_VOICE_ID",""),
            on_progress=progress
        )
        mp3_name = Path(res["mp3_path"]).name
        res["mp3_url"] = f"/download/{mp3_name}"
        _set_job(jid, status="done", result=res)
    except Exception as e:
        traceback.print_exc()
        _set_job(jid, status="error", error=str(e))

@app.get("/")
def root():
    _prune_jobs()
    return {
        "message":"Noah API is running!",
        "version":"1.0.0",
        "endpoints":["/health","/generate","/result/{id}","/download/{name}","/voices"],
        "docs":"/docs"
    }

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/voices")
def voices():
    """Return available voices: OpenAI defaults + ElevenLabs (if key present)."""
    v = [{"provider":"openai","id":x,"name":x} for x in ["alloy","aria","verse","sage"]]
    key = os.getenv("ELEVENLABS_API_KEY","").strip()
    if key:
        import requests
        try:
            r = requests.get("https://api.elevenlabs.io/v1/voices",
                             headers={"xi-api-key":key}, timeout=20)
            if r.ok:
                data = r.json()
                for voice in data.get("voices", []):
                    v.append({"provider":"elevenlabs",
                              "id":voice.get("voice_id"),
                              "name":voice.get("name")})
        except Exception:
            traceback.print_exc()
    return {"voices": v}

@app.post("/generate")
def generate(payload: dict = Body(...), background_tasks: BackgroundTasks = None):
    """
    Body JSON:
    {
      "queries": ["topic one","topic two"]  // OR newline string
      "language": "English",
      "tone": "confident and crisp",
      "recent_hours": 24,
      "cap_per_query": 6,
      "min_minutes": 8,
      "exact_minutes": true,
      "voice_id": "optional (11labs)"
    }
    """
    _prune_jobs()
    jid = uuid.uuid4().hex
    JOBS[jid] = {"status":"queued","log":["queued"],"_ts":time.time()}
    # Schedule sync function in FastAPI's background task runner
    background_tasks.add_task(_run_job_sync, jid, payload)
    return {"job_id": jid, "status":"queued"}

@app.get("/result/{job_id}")
def result(job_id: str):
    j = JOBS.get(job_id)
    if not j:
        return JSONResponse({"error":"not found"}, status_code=404)
    res = j.get("result")
    if res and "mp3_path" in res:
        res = dict(res)
        res.pop("mp3_path", None)
    return {
        "job_id": job_id,
        "status": j.get("status"),
        "log": j.get("log", []),
        "result": res,
        "error": j.get("error")
    }

@app.get("/download/{name}")
def download(name: str):
    p = (DATA_DIR / name).resolve()
    if not str(p).startswith(str(DATA_DIR)):
        return JSONResponse({"error":"invalid path"}, status_code=400)
    if not p.exists():
        return JSONResponse({"error":"file not found"}, status_code=404)
    return FileResponse(str(p), media_type="audio/mpeg", filename=name)
