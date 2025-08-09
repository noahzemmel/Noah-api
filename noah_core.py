# noah_core.py — Core generation + exact-length audio for Noah API
# ------------------------------------------------------------------------------------
# Requirements:
# - openai>=1.30
# - requests, feedparser, pydub
# - ffmpeg installed (Dockerfile already does apt-get install ffmpeg)
#
# Environment variables (set on the API service in Render):
#   OPENAI_API_KEY
#   ELEVENLABS_API_KEY
#   ELEVENLABS_VOICE_ID (optional default)
# ------------------------------------------------------------------------------------

import io
import os
import re
import math
import time
import json
import uuid
import shutil
import random
import string
import feedparser
import requests
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta, timezone

from pydub import AudioSegment

# OpenAI v1 SDK
from openai import OpenAI

# --------------------------- Config -------------------------------------------

DATA_DIR = os.getenv("NOAH_DATA_DIR", "/app/data")
os.makedirs(DATA_DIR, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

# speech tempo guardrails for exact fit (atempo supports 0.5–2.0 per stage)
MIN_RATE = 0.85
MAX_RATE = 1.25

# Conservative words-per-second for natural TTS (English ~2.4–3.2). We use 2.6.
DEFAULT_WPS = float(os.getenv("NOAH_WORDS_PER_SECOND", "2.6"))

# Intro/outro (localizable by language)
DEFAULT_INTRO = {
    "English": "Welcome to your daily Noah.",
}
DEFAULT_OUTRO = {
    "English": "That's your Noah for today. See you tomorrow.",
}

# ------------------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------------------

def health_check() -> bool:
    return bool(OPENAI_API_KEY and ELEVEN_API_KEY)

def _slug(n: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", n.strip()).strip("-").lower()
    return s or "noah"

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _safe_get(d: dict, key: str, default=""):
    v = d.get(key, default)
    return v if v is not None else default

# ------------------------------------------------------------------------------
# News fetching (Google News RSS per query, recent hours filter)
# ------------------------------------------------------------------------------

def _google_news_rss(query: str, recent_hours: int) -> str:
    q = requests.utils.quote(query)
    when = f" when:{recent_hours}h" if recent_hours else ""
    # English world feed; adjust as needed
    return f"https://news.google.com/rss/search?q={q}{requests.utils.quote(when)}&hl=en-GB&gl=GB&ceid=GB:en"

def fetch_sources_for_query(query: str, recent_hours: int, cap: int) -> List[Dict[str, str]]:
    url = _google_news_rss(query, recent_hours)
    try:
        parsed = feedparser.parse(url)
    except Exception:
        return []
    items = []
    for e in parsed.entries[: cap * 3]:  # pull extra, we'll dedupe
        title = _safe_get(e, "title", "")
        link = _safe_get(e, "link", "")
        source = _safe_get(e, "source", {}).get("title", "")
        if not source and "source" in e:
            source = str(e["source"])
        if title and link:
            items.append({"title": title, "link": link, "source": source})
    # de‑dupe by link
    uniq = []
    seen = set()
    for it in items:
        k = it["link"]
        if k not in seen:
            uniq.append(it)
            seen.add(k)
        if len(uniq) >= cap:
            break
    return uniq

def collect_sources(queries: List[str], recent_hours: int, cap_per_query: int) -> Dict[str, List[Dict[str, str]]]:
    out: Dict[str, List[Dict[str, str]]] = {}
    for q in queries:
        out[q] = fetch_sources_for_query(q, recent_hours, cap_per_query)
    return out

# ------------------------------------------------------------------------------
# Script + bullets with strict word budgeting
# ------------------------------------------------------------------------------

def compute_word_budget(minutes_target: int, wps: float, intro_words: int, outro_words: int) -> Tuple[int, int, int]:
    """
    Returns (total_budget, budget_for_body, per_story_hint)
    """
    total_seconds = max(1, int(minutes_target * 60))
    total_budget = max(60, int(total_seconds * wps))  # never below 60 words
    body_budget = max(20, total_budget - intro_words - outro_words)
    per_story_hint = max(30, int(body_budget / 6))  # hint used in prompt; AI can rebalance
    return total_budget, body_budget, per_story_hint

def count_words(s: str) -> int:
    return len(re.findall(r"\b\w+\b", s))

def openai_client() -> OpenAI:
    return OpenAI(api_key=OPENAI_API_KEY)

def build_prompt(language: str, tone: str, queries: List[str], sources: Dict[str, List[Dict[str, str]]],
                 total_budget: int, per_story_hint: int, intro_text: str, outro_text: str) -> List[Dict[str,str]]:
    """
    Returns messages for Chat Completions with hard constraints.
    """
    # Minimal source pack to include inline
    source_snippets = []
    for q, items in sources.items():
        source_snippets.append(f"Topic: {q}")
        for it in items:
            source_snippets.append(f"- {it.get('title','')} ({it.get('source','')}) <{it.get('link','')}>")
    src_text = "\n".join(source_snippets[: 120])  # keep prompt bounded

    system = (
        "You are Noah, a concise news editor.\n"
        "You must produce:\n"
        " 1) A compact bullet list of the most important, *fresh* items.\n"
        " 2) A narration script suitable for voiceover.\n\n"
        "Hard requirements:\n"
        f"- TOTAL narration words (INCLUDING intro/outro) must be ≤ {total_budget} words.\n"
        "- Focus on items from the provided sources; do not invent facts.\n"
        "- Keep it timely: prefer items within the last 24–48 hours.\n"
        "- Use short, concrete sentences. Avoid background history unless needed for context.\n"
        "- Include the intro line at the start and the outro line at the end exactly as provided.\n"
    )
    user = (
        f"Language: {language}\n"
        f"Tone: {tone}\n"
        "Intro:\n"
        f"{intro_text}\n\n"
        "Outro:\n"
        f"{outro_text}\n\n"
        "Queries:\n"
        + "\n".join([f"- {q}" for q in queries]) + "\n\n"
        "Sources to rely on:\n"
        f"{src_text}\n\n"
        f"Per-story narration hint: ~{per_story_hint} words on average (rebalance as needed).\n"
        "Return JSON with fields:\n"
        "{\n"
        '  "bullets": "markdown bullet list",\n'
        '  "narration": "final narration text including intro & outro"\n'
        "}\n"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

def generate_script_and_bullets(queries: List[str], language: str, tone: str,
                                sources: Dict[str, List[Dict[str, str]]],
                                minutes_target: int, wps: float,
                                intro_text: str, outro_text: str) -> Tuple[str, str]:
    total_budget, body_budget, per_story_hint = compute_word_budget(minutes_target, wps, count_words(intro_text), count_words(outro_text))

    client = openai_client()

    for attempt in range(3):
        msgs = build_prompt(language, tone, queries, sources, total_budget, per_story_hint, intro_text, outro_text)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=msgs,
        )
        content = resp.choices[0].message.content.strip()

        # Extract JSON
        try:
            j = json.loads(content)
            bullets = j.get("bullets", "").strip()
            narration = j.get("narration", "").strip()
        except Exception:
            # try to salvage with regex codeblock
            m = re.search(r"\{.*\}", content, re.S)
            if not m:
                continue
            try:
                j = json.loads(m.group(0))
                bullets = j.get("bullets", "").strip()
                narration = j.get("narration", "").strip()
            except Exception:
                continue

        # Enforce budget by compressing if necessary
        words = count_words(narration)
        if words <= total_budget:
            return bullets, narration

        # Ask model to compress to the exact budget
        compress_target = max(60, total_budget)
        resp2 = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {"role":"system","content":"Compress the narration to fit the word budget without losing facts or names."},
                {"role":"user","content":f"Word budget: {compress_target}\nKeep language: {language}\nKeep tone: {tone}\nText:\n{narration}\nReturn ONLY the compressed narration text, nothing else."}
            ],
        )
        narration2 = resp2.choices[0].message.content.strip()
        if count_words(narration2) <= total_budget:
            return bullets, narration2
        # else loop again with smaller hints (reduce wps a bit)
        wps = wps * 0.97

    # Fallback: truncate gently
    toks = narration.split()
    narration = " ".join(toks[: total_budget])
    return bullets, narration

# ------------------------------------------------------------------------------
# Text-to-speech (ElevenLabs)
# ------------------------------------------------------------------------------

def tts_eleven(text: str, voice_id: Optional[str], language: str) -> str:
    """
    Sends text to ElevenLabs, returns path to MP3 file on disk.
    """
    vid = voice_id or DEFAULT_VOICE_ID
    if not vid:
        raise RuntimeError("No ElevenLabs voice_id provided and ELEVENLABS_VOICE_ID is not set.")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.55,
            "similarity_boost": 0.75,
            "style": 0.25,
            "use_speaker_boost": True
        }
    }
    r = requests.post(url, headers=headers, json=payload, timeout=600)
    if r.status_code >= 400:
        raise RuntimeError(f"ElevenLabs error {r.status_code}: {r.text}")

    fname = f"noah_{int(time.time())}_{uuid.uuid4().hex[:8]}.mp3"
    fpath = os.path.join(DATA_DIR, fname)
    with open(fpath, "wb") as f:
        f.write(r.content)
    return fpath

def audio_duration_seconds(path: str) -> float:
    seg = AudioSegment.from_file(path)
    return float(len(seg) / 1000.0)

def tempo_adjust_to_exact(input_path: str, target_seconds: int) -> Tuple[str, float]:
    """
    Uses ffmpeg atempo to adjust playback rate to hit target_seconds.
    Returns (output_path, applied_rate). If no change needed, returns original path and 1.0.
    """
    actual = audio_duration_seconds(input_path)
    if actual <= 0 or target_seconds <= 0:
        return input_path, 1.0

    desired_rate = actual / float(target_seconds)
    rate = max(MIN_RATE, min(MAX_RATE, desired_rate))

    # If change is tiny (<2%) skip re-encoding
    if abs(rate - 1.0) < 0.02:
        return input_path, 1.0

    out_path = input_path.replace(".mp3", "_exact.mp3")
    # ffmpeg's atempo only accepts 0.5–2.0. Our clamps ensure we're safe.
    cmd = f'ffmpeg -y -i "{input_path}" -filter:a "atempo={rate:.6f}" -vn "{out_path}"'
    code = os.system(cmd)
    if code != 0 or not os.path.exists(out_path):
        # If ffmpeg failed, fall back to original
        return input_path, 1.0
    return out_path, rate

# ------------------------------------------------------------------------------
# Public API method
# ------------------------------------------------------------------------------

def make_noah_audio(
    queries: List[str],
    language: str,
    tone: str,
    recent_hours: int,
    per_feed: int,
    cap_per_query: int,
    minutes_target: int,
    exact_minutes: bool = True,
    voice_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    End-to-end: fetch sources -> generate bullets/script with budget -> TTS -> (optional) tempo adjust
    Returns:
      {
        "bullet_points": "...",
        "script": "...",
        "sources": {...},
        "file_path": "/app/data/noah_xxx.mp3",
        "duration_seconds": 480.2,
        "minutes_target": 8,
        "playback_rate_applied": 1.0,
      }
    """
    intro = DEFAULT_INTRO.get(language, DEFAULT_INTRO["English"])
    outro = DEFAULT_OUTRO.get(language, DEFAULT_OUTRO["English"])

    # 1) Gather sources
    sources = collect_sources(queries, recent_hours, cap_per_query)

    # 2) Word-budgeted script
    bullets, narration = generate_script_and_bullets(
        queries=queries,
        language=language,
        tone=tone,
        sources=sources,
        minutes_target=minutes_target,
        wps=DEFAULT_WPS,
        intro_text=intro,
        outro_text=outro,
    )

    # 3) TTS
    mp3_path = tts_eleven(narration, voice_id=voice_id, language=language)
    duration = audio_duration_seconds(mp3_path)

    # 4) Exact-length adjustment (server-side)
    applied_rate = 1.0
    if exact_minutes:
        target_seconds = max(1, int(minutes_target * 60))
        adj_path, applied_rate = tempo_adjust_to_exact(mp3_path, target_seconds)
        if adj_path != mp3_path:
            mp3_path = adj_path
            duration = audio_duration_seconds(mp3_path)

    return {
        "bullet_points": bullets,
        "script": narration,
        "sources": sources,
        "file_path": mp3_path,
        "duration_seconds": duration,
        "minutes_target": minutes_target,
        "playback_rate_applied": applied_rate,
        "generated_at": _now_iso(),
    }
