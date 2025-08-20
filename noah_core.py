# noah_core.py
# Noah Core: fetch -> summarize -> draft -> correct to target words -> TTS -> exactify duration -> return mp3 + sources

from __future__ import annotations
import os, io, re, math, time, json, shutil, asyncio, traceback, tempfile, random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Callable, Optional
from pathlib import Path

import requests
import feedparser
from pydub import AudioSegment
from pydub.effects import speedup
from openai import OpenAI

# --------------------------
# Config via environment
# --------------------------
WPM_DEFAULT = float(os.getenv("NOAH_WPM", "165"))  # natural speaking rate
EXACTIFY_MAX_PASSES = int(os.getenv("NOAH_EXACTIFY_MAX_PASSES", "2"))
ATEMPO_MIN = float(os.getenv("NOAH_ATEMPO_MIN", "0.85"))   # ffmpeg limits: 0.5..2.0 per pass; keep conservative
ATEMPO_MAX = float(os.getenv("NOAH_ATEMPO_MAX", "1.15"))

DATA_DIR = Path(os.getenv("NOAH_DATA_DIR", "/tmp/noah_jobs")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------
# Utilities
# --------------------------
def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def sanitize_queries(q: object) -> List[str]:
    """Accept list or newline-separated string; strip empties."""
    if isinstance(q, list):
        arr = q
    elif isinstance(q, str):
        arr = [line.strip() for line in q.splitlines()]
    else:
        arr = []
    return [s for s in (s.strip() for s in arr) if s]

def minutes_to_words(minutes: float, wpm: float = WPM_DEFAULT) -> int:
    return max(80, int(round(minutes * wpm)))

def seconds_to_mmss(sec: float) -> str:
    m = int(sec // 60)
    s = int(round(sec % 60))
    return f"{m}:{s:02d}"

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# --------------------------
# Source collection
# --------------------------
def google_news_rss(query: str, recent_hours: int, lang="en-GB", region="GB") -> str:
    # E.g., when:24h
    when = f"when%3A{recent_hours}h" if recent_hours else ""
    q = requests.utils.quote(f"{query} {when}".strip())
    return f"https://news.google.com/rss/search?q={q}&hl={lang}&gl={region}&ceid={region}:{lang.split('-')[0]}"

def fetch_sources(queries: List[str], recent_hours: int, cap_per_query: int = 6) -> List[Dict]:
    """Return list of {title, link, source, published} from Google News RSS."""
    results = []
    for q in queries:
        url = google_news_rss(q, recent_hours)
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:cap_per_query]:
                results.append({
                    "query": q,
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": entry.get("source", {}).get("title", "") or entry.get("authors", [{}])[0].get("name",""),
                })
        except Exception:
            traceback.print_exc()
    return results

# --------------------------
# LLM helpers
# --------------------------
def get_openai_client() -> OpenAI:
    return OpenAI()

def llm_bullets_and_script(queries: List[str], sources: List[Dict], language: str, tone: str, target_words: int) -> Tuple[str, List[str]]:
    """
    Return (script_text, bullets[]) based on sources; tight / factual style.
    """
    client = get_openai_client()
    # Keep prompt concise to speed up; ask for topical, fact-first style
    sys = (
        "You are Noah, a news editor. Create a concise, factual spoken script from these recent sources. "
        "Always lead with the newest items. Use short sentences, minimal filler. "
        "Write in {language}, tone {tone}. Target ~{words} words total."
    ).format(language=language, tone=tone, words=target_words)

    src_lines = []
    for s in sources[:24]:  # cap context to keep latency sensible
        src_lines.append(f"- {s['title']} ({s['link']})")
    src_block = "\n".join(src_lines) or "(no sources)"

    user = (
        f"Topics: {', '.join(queries)}\n"
        f"Sources (latest first):\n{src_block}\n\n"
        "Return JSON with keys:\n"
        "- bullets: a list of 6-12 compact bullet points (strings)\n"
        "- script: a single-paragraph broadcast script (no headings)"
    )

    resp = client.chat.completions.create(
        model=os.getenv("NOAH_SUMMARY_MODEL","gpt-4o-mini"),
        messages=[
            {"role":"system","content":sys},
            {"role":"user","content":user}
        ],
        temperature=0.2,
        response_format={"type":"json_object"}
    )
    content = resp.choices[0].message.content
    try:
        data = json.loads(content)
    except Exception:
        data = {"bullets": [], "script": content}

    bullets = [b for b in data.get("bullets", []) if isinstance(b, str)]
    script = data.get("script", "")
    # safety: if no script, build from bullets
    if not script.strip():
        script = " ".join(bullets)
    return script.strip(), bullets

def llm_expand_or_shrink(text: str, desired_words: int, language: str, tone: str) -> str:
    """Correct length toward desired_words. Keep topical, concise style."""
    client = get_openai_client()
    sys = (
        "You are a broadcast editor. Adjust the script length to match the requested word count "
        "while preserving key facts and concise style. Avoid filler; keep it newsy and current."
    )
    user = (
        f"Language: {language}\nTone: {tone}\n"
        f"Target words: {desired_words}\n"
        f"Script:\n{text}\n\n"
        "Return only the revised script."
    )
    resp = client.chat.completions.create(
        model=os.getenv("NOAH_EDITOR_MODEL","gpt-4o-mini"),
        messages=[{"role":"system","content":sys},{"role":"user","content":user}],
        temperature=0.2
    )
    return resp.choices[0].message.content.strip()

# --------------------------
# TTS providers
# --------------------------
def tts_openai(text: str, out_path: str, voice: Optional[str] = None) -> str:
    """
    OpenAI TTS (robust across SDK versions):
      1) Try streaming API (no 'format' kwarg).
      2) Fallback to non-streaming with response_format='mp3' if needed.
    Returns absolute mp3 path.
    """
    out_path = str(out_path)
    Path(os.path.dirname(out_path) or ".").mkdir(parents=True, exist_ok=True)

    client = get_openai_client()
    model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    v = voice or os.getenv("OPENAI_TTS_VOICE", "alloy")

    try:
        # Preferred: streaming
        with client.audio.speech.with_streaming_response.create(
            model=model, voice=v, input=text
        ) as resp:
            resp.stream_to_file(out_path)
        return os.path.abspath(out_path)
    except Exception:
        traceback.print_exc()

    # Fallback: non-streaming
    try:
        result = client.audio.speech.create(
            model=model, voice=v, input=text, response_format="mp3"
        )
        if hasattr(result, "read"):
            audio_bytes = result.read()
        elif hasattr(result, "content"):
            audio_bytes = result.content
        else:
            audio_bytes = bytes(result)
        with open(out_path, "wb") as f:
            f.write(audio_bytes)
        return os.path.abspath(out_path)
    except Exception:
        traceback.print_exc()
        raise

def tts_elevenlabs(text: str, out_path: str, voice_id: Optional[str] = None) -> str:
    """
    ElevenLabs TTS (streaming). Raises if quota/rate-limited.
    """
    key = os.getenv("ELEVENLABS_API_KEY","").strip()
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY missing")

    vid = voice_id or os.getenv("ELEVENLABS_VOICE_ID","")
    if not vid:
        # default voice
        vid = "21m00Tcm4TlvDq8ikWAM"  # Rachel (public) – safe default; replace if you like

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/stream?optimize_streaming_latency=3"
    headers = {
        "xi-api-key": key,
        "accept": "audio/mpeg",
        "content-type": "application/json"
    }
    payload = {
        "text": text,
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.7}
    }

    Path(os.path.dirname(out_path) or ".").mkdir(parents=True, exist_ok=True)
    with requests.post(url, headers=headers, data=json.dumps(payload), stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return os.path.abspath(out_path)

# --------------------------
# Audio exactify
# --------------------------
def audio_duration_seconds(path: str) -> float:
    au = AudioSegment.from_file(path)
    return au.duration_seconds

def atempo_exactify(in_mp3: str, target_minutes: float) -> Tuple[str, float, float]:
    """
    Adjust playback rate (ffmpeg atempo) within bounds to match target minutes.
    Returns (new_path, new_secs, rate_applied).
    """
    target_secs = target_minutes * 60.0
    cur = audio_duration_seconds(in_mp3)
    if cur <= 0:
        return in_mp3, 0.0, 1.0

    rate = clamp(target_secs / cur, ATEMPO_MIN, ATEMPO_MAX)
    if abs(rate - 1.0) < 0.01:
        return in_mp3, cur, 1.0

    # pydub speedup changes pitch a bit; for demo use it's ok and fast.
    au = AudioSegment.from_file(in_mp3)
    # pydub's speedup is multiplier on playback speed
    new = speedup(au, playback_speed=rate)
    out = str(Path(in_mp3).with_suffix(".exact.mp3"))
    new.export(out, format="mp3")
    new_secs = audio_duration_seconds(out)
    return out, new_secs, rate

# --------------------------
# Main pipeline
# --------------------------
def make_noah_audio(
    queries_raw: object,
    language: str = "English",
    tone: str = "confident and crisp",
    recent_hours: int = 24,
    cap_per_query: int = 6,
    min_minutes: float = 8.0,
    exact_minutes: bool = True,
    voice_id: Optional[str] = None,
    on_progress: Optional[Callable[[str], None]] = None,
) -> Dict:
    """
    Returns dict:
      {
        "script": "...",
        "bullets": [...],
        "sources": [...],
        "mp3_path": "/tmp/noah_jobs/....mp3",
        "actual_minutes": 7.95,
        "target_minutes": 8.0,
        "playback_rate": 0.99,
        "tts_provider": "openai" | "elevenlabs"
      }
    """
    def tick(msg: str):
        if on_progress: on_progress(msg)

    queries = sanitize_queries(queries_raw)
    if not queries:
        raise ValueError("No topics provided")

    # 1) Sources
    tick("Collecting sources")
    sources = fetch_sources(queries, recent_hours, cap_per_query=cap_per_query)
    if not sources:
        # Still proceed: model can provide overview
        tick("No sources found; falling back to background context")

    # 2) Draft (words near target)
    target_words = minutes_to_words(min_minutes)
    tick("Draft Attempt 1")
    script, bullets = llm_bullets_and_script(queries, sources, language, tone, target_words)

    # 3) Correct toward exact words (bounded passes)
    for i in range(EXACTIFY_MAX_PASSES):
        word_count = len(re.findall(r"\w+", script))
        if abs(word_count - target_words) / target_words <= 0.05:
            break
        tick(f"Correct Expand {word_count}")
        script = llm_expand_or_shrink(script, target_words, language, tone)

    # 4) TTS (provider selection)
    provider = (os.getenv("NOAH_TTS_PROVIDER", "openai") or "openai").lower()
    # auto mode tries 11labs first if key is present
    if provider == "auto":
        provider = "elevenlabs" if os.getenv("ELEVENLABS_API_KEY","").strip() else "openai"

    mp3_path = str(DATA_DIR / f"noah_{int(time.time())}_{random.randint(1000,9999)}.mp3")
    tick("TTS Start")
    if provider == "elevenlabs":
        try:
            tts_elevenlabs(script, mp3_path, voice_id=voice_id or os.getenv("ELEVENLABS_VOICE_ID",""))
            tts_used = "elevenlabs"
        except Exception:
            traceback.print_exc()
            tick("11Labs failed; falling back to OpenAI TTS")
            tts_openai(script, mp3_path, voice=os.getenv("OPENAI_TTS_VOICE","alloy"))
            tts_used = "openai"
    else:
        tts_openai(script, mp3_path, voice=os.getenv("OPENAI_TTS_VOICE","alloy"))
        tts_used = "openai"

    # 5) Exactify duration
    tick("Exactify audio")
    out_path, new_secs, rate = atempo_exactify(mp3_path, min_minutes if exact_minutes else (len(script.split())/WPM_DEFAULT/60))
    if out_path != mp3_path:
        try: os.remove(mp3_path)
        except: pass
        mp3_path = out_path

    result = {
        "script": script,
        "bullets": bullets,
        "sources": sources,
        "mp3_path": mp3_path,
        "actual_minutes": round(new_secs/60.0, 2),
        "target_minutes": float(min_minutes),
        "playback_rate": round(rate, 3),
        "tts_provider": tts_used,
    }
    return result
