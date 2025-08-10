from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import os, requests

from noah_core import make_noah_audio, health_check

app = FastAPI(title="Noah API", version="1.0.0")

@app.get("/", include_in_schema=False)
def root():
    return {"message":"Noah API is running!","version":"1.0.0",
            "endpoints":["/health","/generate","/download/{name}","/voices"],"docs":"/docs"}

allowed = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed.split(",")] if allowed else ["*"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                   allow_methods=["POST","GET","OPTIONS"], allow_headers=["*"])

@app.get("/health")
def health(): return {"ok": health_check()}

@app.get("/voices")
def voices():
    """Expose ElevenLabs voices so the UI doesn't need the key."""
    key = os.getenv("ELEVENLABS_API_KEY","")
    if not key: return []
    try:
        r = requests.get("https://api.elevenlabs.io/v1/voices",
                         headers={"xi-api-key": key}, timeout=20)
        j = r.json() if r.status_code==200 else {}
        return [{"name": v.get("name","Unnamed"), "id": v.get("voice_id","")}
                for v in (j.get("voices") or [])]
    except Exception:
        return []

@app.post("/generate")
def generate(payload: dict = Body(...)):
    try:
        queries = payload.get("queries") or []
        if isinstance(queries, str):
            queries = [q.strip() for q in queries.replace(",", "\n").split("\n") if q.strip()]
        language = payload.get("language","English")
        tone = payload.get("tone","confident and crisp")
        recent_hours = int(payload.get("recent_hours",24))
        per_feed = int(payload.get("per_feed",6))
        cap_per_query = int(payload.get("cap_per_query",6))
        minutes_target = int(payload.get("minutes_target", payload.get("min_minutes",8)))
        exact_minutes = bool(payload.get("exact_minutes", True))
        voice_id = payload.get("voice_id")

        if not queries: return JSONResponse({"error":"No queries provided."}, 400)

        res = make_noah_audio(queries, language, tone, recent_hours,
                              per_feed, cap_per_query, minutes_target,
                              exact_minutes, voice_id)
        name = Path(res["file_path"]).name
        return {
            "bullet_points": res["bullet_points"],
            "script": res["script"],
            "sources": res["sources"],
            "mp3_url": f"/download/{name}",
            "minutes_target": res["minutes_target"],
            "duration_seconds": res["duration_seconds"],
            "playback_rate_applied": res["playback_rate_applied"],
            "generated_at": res["generated_at"],
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

@app.get("/download/{name}")
def download(name: str):
    path = Path("/app/data") / name
    if not path.exists(): return JSONResponse({"error":"File not found."}, 404)
    return FileResponse(str(path), media_type="audio/mpeg", filename=name)
