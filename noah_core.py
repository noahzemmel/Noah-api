# noah_core.py
import os
import io
import re
import math
import json
import time
import base64
import random
import requests
from typing import List, Dict, Tuple
from datetime import datetime, timezone, timedelta

from dateutil import parser as dateparse
from pydub import AudioSegment
from pydub.silence import detect_leading_silence
from openai import OpenAI

# ----------------------------
# ENV
# ----------------------------
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "")
ELEVEN_API_KEY   = os.getenv("ELEVENLABS_API_KEY", "")
ELEVEN_VOICE_ID  = os.getenv("ELEVENLABS_VOICE_ID", "")  # optional default
TAVILY_API_KEY   = os.getenv("TAVILY_API_KEY", "")

oai = OpenAI(api_key=OPENAI_API_KEY)

# ----------------------------
# Constants / Tunables
# ----------------------------
# 1. Recency
DEFAULT_LOOKBACK_H = 24               # overwritten by payload
MAX_RESULTS_PER_TOPIC = 12            # absolute cap across expansions
BATCH_FETCH = 6                       # items per Tavily call

# 2. Script sizing (empirical)
# ElevenLabs default voices are ~13.8–15.5 characters / second at normal pitch/rate.
CHARS_PER_SEC = 14.2

# 3. Audio timing
TRIM_HEAD_MS = 180
TRIM_TAIL_MS = 220
SILENCE_DB = -38.0

# 4. Time-stretch clamp to avoid artifacts
STRETCH_MIN = 0.80    # don't slow down more than 1/0.80 ≈ +25%
STRETCH_MAX = 1.25    # don't speed up more than 25%

ELEVEN_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# ----------------------------
# Utilities
# ----------------------------
def _now_utc():
    return datetime.now(timezone.utc)

def _safe_parse_date(s):
    try:
        dt = dateparse.parse(s)
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def _normalize_url(u: str) -> str:
    if not u:
        return ""
    u = u.strip()
    u = re.sub(r"#.*$", "", u)
    u = re.sub(r"\?.*$", "", u)
    u = u.replace("http://", "https://")
    return u

def _dedupe_items(items: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for it in items:
        key = (it.get("title","").strip().lower(), _normalize_url(it.get("url","")))
        if key not in seen and it.get("url"):
            seen.add(key)
            out.append(it)
    return out

# ----------------------------
# Tavily news fetch (recency strict)
# ----------------------------
def _tavily_news(query: str, lookback_h: int, limit: int) -> List[Dict]:
    """
    Use Tavily's /search in news mode.
    We try 'time_range' (hXX) first; if provider complains, fall back to 'days'.
    """
    if not TAVILY_API_KEY:
        return []
    url = "https://api.tavily.com/search"
    payload_base = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced",
        "include_answer": False,
        "include_raw_content": False,
        "max_results": min(limit, 10),
        "topic": "news"
    }
    out = []
    # primary attempt – hours window
    try:
        p = dict(payload_base)
        p["time_range"] = f"h{max(1, int(lookback_h))}"
        r = requests.post(url, json=p, timeout=40)
        if r.ok:
            data = r.json()
            for res in data.get("results", []):
                out.append({
                    "title": res.get("title") or "",
                    "url":   _normalize_url(res.get("url") or ""),
                    "source": res.get("source") or "",
                    "published": res.get("published_time") or res.get("published_date") or ""
                })
    except Exception:
        pass

    # fallback – days
    if not out:
        try:
            p = dict(payload_base)
            p["days"] = max(1, int(math.ceil(lookback_h/24)))
            r = requests.post(url, json=p, timeout=40)
            if r.ok:
                data = r.json()
                for res in data.get("results", []):
                    out.append({
                        "title": res.get("title") or "",
                        "url":   _normalize_url(res.get("url") or ""),
                        "source": res.get("source") or "",
                        "published": res.get("published_time") or res.get("published_date") or ""
                    })
        except Exception:
            pass
    # filter to window strictly
    cutoff = _now_utc() - timedelta(hours=lookback_h)
    strict = []
    for it in out:
        when = _safe_parse_date(it.get("published") or "")
        if when and when >= cutoff and it.get("url"):
            strict.append({**it, "published": when.isoformat()})
    return _dedupe_items(strict)

# ----------------------------
# Script building with coverage and size control
# ----------------------------
def _allocate_char_budget(total_sec: int, topics_n: int, head_tail_sec=8) -> Tuple[int, int, List[int]]:
    """
    Reserve a small fixed intro/outro then split the rest across topics evenly.
    """
    total_chars = max(200, int((total_sec - head_tail_sec) * CHARS_PER_SEC))
    per_topic = max(200, total_chars // max(1, topics_n))
    return total_chars, per_topic, [per_topic]*topics_n

def _llm_script_for_topic(topic: str, items: List[Dict], char_budget: int, language: str, tone: str) -> Tuple[str, List[Dict]]:
    """
    Use only the supplied items. Returns (script_text, used_items).
    """
    if not items:
        return "", []
    # Build short context (titles + snippets from Tavily are limited; we rely on titles + sources)
    cites = []
    for idx, it in enumerate(items, 1):
        cites.append(f"[{idx}] {it['title']} — {it.get('source','')} ({it.get('published','')}) :: {it['url']}")

    sys = (
        "You are a journalist. Summarize ONLY the facts from the provided sources. "
        "No background, no opinion, no speculation. Keep it timely (within the last 24–72 hours). "
        "Write in {language}, tone: {tone}. Use concise sentences suitable for voice-over."
    ).format(language=language, tone=tone)

    user = (
        "TOPIC: {topic}\n"
        "TARGET_CHARS: {chars}\n"
        "RULES:\n"
        " - Use ONLY facts from the SOURCES list (do not invent anything).\n"
        " - Prefer news that is within the last 24 hours when possible.\n"
        " - Keep every sentence informative; no filler.\n"
        " - Output plain text (no markdown). 5–10 short sentences max.\n\n"
        "SOURCES:\n{src}\n\n"
        "Write the script now. If sources are insufficient for {topic}, write nothing."
    ).format(topic=topic, chars=char_budget, src="\n".join(cites))

    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {"role":"system","content":sys},
            {"role":"user","content":user}
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    # Enforce hard char ceiling
    if len(text) > char_budget:
        text = text[:char_budget].rsplit(".", 1)[0] + "."
    # Select only items we referenced implicitly (we can't know; just pass through)
    return text, items

def _compose_full_script(intro: str, segments: List[Tuple[str,str]], outro: str) -> str:
    """
    segments: list of (header, body)
    """
    parts = []
    if intro: parts.append(intro.strip())
    for h, b in segments:
        if b.strip():
            if h: parts.append(h.strip())
            parts.append(b.strip())
    if outro: parts.append(outro.strip())
    script = "\n\n".join([p for p in parts if p])
    # Normalize spaces
    script = re.sub(r"[ \t]+", " ", script)
    return script.strip()

# ----------------------------
# Audio helpers
# ----------------------------
def trim_silence(seg: AudioSegment, head_ms: int = TRIM_HEAD_MS, tail_ms: int = TRIM_TAIL_MS, threshold_db: float = SILENCE_DB) -> AudioSegment:
    try:
        lead = detect_leading_silence(seg, silence_threshold=threshold_db)
        rev  = seg.reverse()
        trail = detect_leading_silence(rev, silence_threshold=threshold_db)
    except TypeError:
        lead = detect_leading_silence(seg, threshold_db)
        rev  = seg.reverse()
        trail = detect_leading_silence(rev, threshold_db)

    start = max(0, lead - head_ms)
    end   = len(seg) - max(0, trail - tail_ms)
    trimmed = seg[start:end]
    if len(trimmed) < 200:
        trimmed = trimmed + AudioSegment.silent(duration=200)
    return trimmed

def _time_stretch(seg: AudioSegment, factor: float) -> AudioSegment:
    """
    factor > 1 => longer audio; factor < 1 => shorter audio
    Uses frame-rate trick to keep pitch pleasant.
    """
    factor = max(STRETCH_MIN, min(STRETCH_MAX, factor))
    new_rate = int(seg.frame_rate / factor)
    stretched = seg._spawn(seg.raw_data, overrides={'frame_rate': new_rate})
    return stretched.set_frame_rate(seg.frame_rate)

def _eleven_tts(text: str, voice_id: str) -> AudioSegment:
    if not ELEVEN_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY missing")
    if not voice_id:
        if not ELEVEN_VOICE_ID:
            raise RuntimeError("No ElevenLabs voice_id configured")
        voice_id = ELEVEN_VOICE_ID

    url = f"{ELEVEN_TTS_URL}/{voice_id}/stream?optimize_streaming_latency=4"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json"
    }
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.46, "similarity_boost": 0.7, "style": 0.25, "use_speaker_boost": True}
    }
    r = requests.post(url, headers=headers, json=body, timeout=120)
    r.raise_for_status()
    raw = io.BytesIO(r.content)
    seg = AudioSegment.from_file(raw, format="mp3")
    return seg

# ----------------------------
# Public entry
# ----------------------------
def health_check() -> Dict:
    return {
        "openai": bool(OPENAI_API_KEY),
        "elevenlabs": bool(ELEVEN_API_KEY),
        "tavily": bool(TAVILY_API_KEY),
        "ok": bool(OPENAI_API_KEY and ELEVEN_API_KEY and TAVILY_API_KEY)
    }

def make_noah_audio(
    queries: List[str],
    minutes: int,
    language: str,
    tone: str,
    lookback_hours: int,
    cap_per_topic: int,
    strict_timing: bool,
    voice_id: str = ""
) -> Dict:
    """
    Returns: dict with keys:
      ok, target_sec, actual_sec, playback_rate, mp3_path, bullets_by_topic, sources_by_topic
    """
    assert minutes >= 2
    target_sec = minutes * 60

    # 1) Fetch recent sources per topic, with possible expansion
    all_segments = []
    bullets_out = {}
    sources_out = {}

    topics = [q.strip() for q in queries if q.strip()]
    topics = topics[:6] if topics else ["Top headlines"]  # safety

    total_chars, per_topic_chars, per_topic_budgets = _allocate_char_budget(target_sec, len(topics))
    per_topic_limit = max(2, min(MAX_RESULTS_PER_TOPIC, cap_per_topic))

    for i, topic in enumerate(topics):
        gathered = []
        attempts = 0
        while len(gathered) < per_topic_limit and attempts < 3:
            need = min(BATCH_FETCH, per_topic_limit - len(gathered))
            got = _tavily_news(topic, lookback_hours, limit=need)
            # de-dup with ones we already have
            cur_urls = {g["url"] for g in gathered}
            fresh = [x for x in got if x["url"] not in cur_urls]
            if not fresh:
                break
            gathered.extend(fresh)
            attempts += 1

        # If absolutely nothing, skip this topic
        if not gathered:
            continue

        # Build a compact script from only these fresh items
        body, used = _llm_script_for_topic(topic, gathered[:per_topic_limit], per_topic_budgets[i], language, tone)

        # record bullets and sources to show in UI
        bullets_out[topic] = [f"- {u['title']}" for u in used]
        sources_out[topic] = used

        all_segments.append((f"{topic}:", body))

    # 2) Compose full script with tight intro/outro (no filler)
    intro = f"Welcome to your daily Noah. Here are the latest updates."
    outro = "That’s your briefing for now. See you tomorrow."
    script = _compose_full_script(intro, all_segments, outro)

    # If script too small (not enough news), try expanding each topic once more
    est_sec = max(2.0, len(script) / CHARS_PER_SEC)
    if est_sec < target_sec * 0.7:
        # one more pass to fetch a few more headlines (still recent)
        for i, topic in enumerate(topics):
            gathered = sources_out.get(topic, [])
            if len(gathered) >= per_topic_limit:
                continue
            need = min(BATCH_FETCH, per_topic_limit - len(gathered))
            extra = _tavily_news(topic, lookback_hours, limit=need)
            cur = {x["url"] for x in gathered}
            extra = [x for x in extra if x["url"] not in cur]
            if not extra:
                continue
            # Summarize the extra into 2–3 tight lines to extend time
            add_body, used_extra = _llm_script_for_topic(topic, extra, per_topic_budgets[i]//2, language, tone)
            if add_body.strip():
                # append after the existing section for that topic
                for k, (h, b) in enumerate(all_segments):
                    if h.lower().startswith(topic.lower()):
                        all_segments[k] = (h, b + "\n" + add_body)
                        break
                bullets_out[topic].extend([f"- {u['title']}" for u in used_extra])
                sources_out[topic].extend(used_extra)

        script = _compose_full_script(intro, all_segments, outro)

    # 3) TTS once; then time-stretch to exact target if strict requested
    #    (No padding with silence, no random filler)
    voice_to_use = voice_id or ELEVEN_VOICE_ID
    if not voice_to_use:
        raise RuntimeError("No voice_id configured for ElevenLabs.")

    audio = _eleven_tts(script, voice_to_use)
    audio = trim_silence(audio)

    actual = len(audio) / 1000.0
    rate = 1.0

    if strict_timing and abs(actual - target_sec) > 1.0:
        rate = target_sec / actual
        audio = _time_stretch(audio, factor=rate)
        audio = trim_silence(audio)
        actual = len(audio) / 1000.0

    # 4) Persist mp3 to disk for download
    safe_ts = int(time.time())
    fname = f"noah_{safe_ts}.mp3"
    out_dir = os.getenv("AUDIO_DIR", "/tmp")
    os.makedirs(out_dir, exist_ok=True)
    fpath = os.path.join(out_dir, fname)
    audio.export(fpath, format="mp3", bitrate="128k")

    return {
        "ok": True,
        "target_sec": target_sec,
        "actual_sec": round(actual, 2),
        "playback_rate": round(rate, 3),
        "mp3_path": fpath,
        "bullets_by_topic": bullets_out,
        "sources_by_topic": sources_out,
        "script_chars": len(script)
    }
