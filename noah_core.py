# noah_core.py — exact-length, multi-topic, fresh-news generator
from __future__ import annotations
import os, io, re, math, time, uuid, json, random
from typing import List, Dict, Any, Tuple, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path

import requests
import feedparser
from pydub import AudioSegment
from pydub.silence import detect_leading_silence

# ------------- Env & constants -------------
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY", "")
ELEVEN_API_KEY      = os.getenv("ELEVENLABS_API_KEY", "")
ELEVEN_VOICE_ID_DEF = os.getenv("ELEVENLABS_VOICE_ID", "")
TAVILY_API_KEY      = os.getenv("TAVILY_API_KEY", "")
DATA_DIR            = Path(os.getenv("DATA_DIR", "/tmp/noah_jobs")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Providers flags
HAS_TAVILY  = bool(TAVILY_API_KEY)
HAS_ELEVEN  = bool(ELEVEN_API_KEY)
HAS_OPENAI  = bool(OPENAI_API_KEY)

# ------------- Simple helpers -------------
def slug(s: str) -> str:
    s = re.sub(r"[^\w\-]+", "-", s.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s) or "noah"

def now_utc() -> datetime:
    return datetime.utcnow()

def http_json(url: str, method: str = "GET", **kw) -> Any:
    r = requests.request(method, url, timeout=30, **kw)
    r.raise_for_status()
    if "application/json" in r.headers.get("content-type", ""):
        return r.json()
    return r.text

# ------------- Tavily search -------------
def tavily_search(query: str, hours: int, max_results: int = 8) -> List[Dict[str, str]]:
    """Fresh web search via Tavily, restricted by recency."""
    if not HAS_TAVILY:
        return []
    recency = max(1, min(72, hours))
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
        "include_domains": [],
        "exclude_domains": [],
        "days": max(1, math.ceil(recency / 24)),
    }
    r = requests.post("https://api.tavily.com/search", json=payload, timeout=45)
    r.raise_for_status()
    data = r.json()
    out = []
    for item in data.get("results", []):
        out.append({
            "title": item.get("title") or item.get("url") or "source",
            "url": item.get("url") or "",
            "snippet": item.get("content") or "",
            "source": "web",
        })
    return out

# ------------- RSS fallback -------------
DEFAULT_FEEDS = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://www.reutersagency.com/feed/?best-topics=top-news&post_type=best",
    "https://www.ft.com/world?format=rss",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://www.theguardian.com/world/rss",
]
def rss_recent(hours: int, limit: int = 100) -> List[Dict[str, str]]:
    cutoff = now_utc() - timedelta(hours=hours)
    out = []
    for url in DEFAULT_FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:50]:
                # Some RSS entries lack precise dates; include anyway if unsure
                published = getattr(e, "published_parsed", None)
                ok_time = True
                if published:
                    dt = datetime(*published[:6])
                    ok_time = (dt >= cutoff)
                if ok_time:
                    out.append({
                        "title": e.get("title", "news"),
                        "url": e.get("link", ""),
                        "snippet": e.get("summary", ""),
                        "source": "rss",
                    })
        except Exception:
            pass
    random.shuffle(out)
    return out[:limit]

# ------------- OpenAI LLM / TTS -------------
def openai_chat(system: str, user: str, temperature=0.4, tokens=1200) -> str:
    if not HAS_OPENAI:
        raise RuntimeError("OPENAI_API_KEY not set")
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role":"system","content":system},{"role":"user","content":user}],
        "temperature": temperature,
        "max_tokens": tokens,
    }
    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()

def openai_tts(text: str, voice: str = "alloy") -> AudioSegment:
    if not HAS_OPENAI:
        raise RuntimeError("OPENAI_API_KEY not set")
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    body = {
        "model": "gpt-4o-mini-tts",
        "voice": voice or "alloy",
        "input": text,
        "format": "mp3",  # OpenAI supports "mp3"
    }
    r = requests.post("https://api.openai.com/v1/audio/speech", headers=headers, json=body, timeout=120)
    r.raise_for_status()
    audio_bytes = r.content
    return AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")

# ------------- ElevenLabs TTS -------------
def eleven_tts(text: str, voice_id: Optional[str] = None) -> AudioSegment:
    if not HAS_ELEVEN:
        raise RuntimeError("ELEVENLABS_API_KEY not set")
    v = (voice_id or ELEVEN_VOICE_ID_DEF or "").strip() or "21m00Tcm4TlvDq8ikWAM"  # default premade voice if none
    headers = {"xi-api-key": ELEVEN_API_KEY, "accept": "audio/mpeg", "Content-Type":"application/json"}
    body = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability":0.4,"similarity_boost":0.8}}
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{v}"
    r = requests.post(url, headers=headers, json=body, timeout=120)
    r.raise_for_status()
    return AudioSegment.from_file(io.BytesIO(r.content), format="mp3")

# ------------- Voice calibration & timing -------------
def measure_wpm(tts_provider: str, voice_id: Optional[str]) -> Tuple[float, str]:
    """
    Synthesize ~60 word snippet and measure duration to estimate WPM.
    """
    sample = (
        "This is a short calibration to measure speaking speed for exact timing. "
        "Please ignore. After this, your bulletin will begin."
    )
    if tts_provider == "elevenlabs" and HAS_ELEVEN:
        seg = eleven_tts(sample, voice_id)
        provider = "elevenlabs"
    else:
        seg = openai_tts(sample, voice_id or "alloy")
        provider = "openai"
    words = len(sample.split())
    minutes = max(1e-6, len(seg) / 60000.0)
    wpm = max(120.0, min(220.0, words / minutes))
    # Trim all silence from calibration to avoid dead air later
    seg = trim_silence(seg)
    return (wpm, provider)

def trim_silence(seg: AudioSegment, head_ms=300, tail_ms=400) -> AudioSegment:
    # Trim long leading/trailing silence, keep a tiny ambience
    lead = detect_leading_silence(seg, silence_threshold=-40)
    rev = seg.reverse()
    trail = detect_leading_silence(rev, silence_threshold=-40)
    seg = seg[max(0, lead - head_ms): len(seg) - max(0, trail - tail_ms)]
    return seg

# ------------- News aggregation -------------
def gather_sources_per_topic(queries: List[str], hours: int, cap_per_topic: int, on_progress: Callable[[str], None]) -> Dict[str, List[Dict[str,str]]]:
    """
    Get fresh sources per topic. Guarantees up to cap_per_topic per topic when available.
    """
    sources_per = {}
    for q in queries:
        q_clean = q.strip()
        on_progress(f"Search: {q_clean}")
        items = []
        if HAS_TAVILY:
            items = tavily_search(q_clean, hours, max_results=cap_per_topic+3)
        if not items:  # fallback RSS + filter titles
            pool = rss_recent(hours, limit=80)
            q_words = [w for w in re.split(r"\W+", q_clean.lower()) if w]
            for p in pool:
                title = (p.get("title") or "").lower()
                if any(w in title for w in q_words):
                    items.append(p)
        sources_per[q_clean] = items[:cap_per_topic]
    return sources_per

# ------------- Bullet & Script writer -------------
def bullets_for_topic(topic: str, sources: List[Dict[str,str]], lang: str, tone: str) -> List[str]:
    """
    Ask LLM for compact bullets tied to the *given sources* (last 24–72h).
    """
    cites = "\n".join(f"- {s.get('title')} — {s.get('url')}" for s in sources if s.get("url"))
    system = f"You are Noah, a concise real-time news writer. Write in {lang}. Tone: {tone}. Focus on facts from the cited URLs only."
    user = (
        f"Topic: {topic}\n"
        f"Sources (fresh):\n{cites}\n\n"
        "Compose 4–6 compact bullet points (max ~22 words each). "
        "Each bullet must be attributable to these sources; do not invent, do not summarize history. "
        "Return each bullet prefixed by '• '."
    )
    text = openai_chat(system, user, temperature=0.2, tokens=500)
    bulls = [re.sub(r"^[•\-\*]\s*", "", b).strip() for b in text.splitlines() if b.strip()]
    return bulls[:8]

def script_from_bullets(queries: List[str], per_topic_bullets: Dict[str,List[str]], lang: str, tone: str, target_words: int) -> str:
    """
    Force coverage across all topics first, then flow.
    """
    bundle = []
    for q in queries:
        b = per_topic_bullets.get(q.strip(), [])
        if b:
            bundle.append(f"{q.strip()}:\n" + "\n".join(f"- {x}" for x in b))
    joined = "\n\n".join(bundle)
    sys = f"You are Noah, a crisp daily news narrator. Language: {lang}. Tone: {tone}."
    usr = (
        "Using ONLY the listed bullets (which are extracted from verified sources), craft a spoken news script. "
        "Rules:\n"
        "1) Cover every topic section in the order given.\n"
        "2) Keep it factual and *current* — no background history unless needed for one-sentence context.\n"
        f"3) Aim for about {target_words} words total.\n"
        "4) Use short sentences. Smooth but efficient transitions between topics.\n"
        "5) No repetition. No disclaimers.\n\n"
        f"Bullets grouped by topic:\n{joined}\n\n"
        "Return only the script paragraphs."
    )
    return openai_chat(sys, usr, temperature=0.35, tokens=1600)

def continuation_script(lang: str, tone: str, remaining_words: int, queries: List[str], used_topics: List[str]) -> str:
    sys = f"You are Noah, a crisp daily news narrator. Language: {lang}. Tone: {tone}."
    usr = (
        "We need a continuation segment for the same bulletin. "
        f"Write about {remaining_words} words, expanding with *new, fresh* lines that add depth and detail. "
        "Do not repeat earlier lines. Keep transitions tight. No filler."
    )
    return openai_chat(sys, usr, temperature=0.45, tokens=1200)

# ------------- Synthesis pipeline -------------
def synthesize(tts_provider: str, voice_id: Optional[str], text: str) -> AudioSegment:
    if tts_provider == "elevenlabs" and HAS_ELEVEN:
        seg = eleven_tts(text, voice_id)
        return trim_silence(seg)
    # default OpenAI
    seg = openai_tts(text, voice_id or "alloy")
    return trim_silence(seg)

# ------------- Public entry point -------------
def make_noah_audio(
    queries_raw: str,
    language: str,
    tone: str,
    recent_hours: int,
    cap_per_query: int,
    min_minutes: float,
    exact_minutes: bool,
    voice_id: Optional[str],
    on_progress: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Main orchestrator called by FastAPI worker thread.
    """
    on_progress = on_progress or (lambda _msg: None)

    # Normalize topics
    topics = [t.strip() for t in re.split(r"[\n\r]+", queries_raw or "") if t.strip()]
    if not topics:
        topics = ["world news"]

    # 1) Collect sources per topic (guarantee at least per-topic coverage)
    on_progress("Collecting fresh sources")
    per_topic_sources = gather_sources_per_topic(topics, recent_hours, cap_per_query, on_progress)

    # 2) Convert sources to bullets (per topic)
    on_progress("Draft bullets per topic")
    per_topic_bullets: Dict[str, List[str]] = {}
    for q in topics:
        srcs = per_topic_sources.get(q, [])
        if not srcs:
            per_topic_bullets[q] = []
            continue
        per_topic_bullets[q] = bullets_for_topic(q, srcs, language, tone)
        time.sleep(0.3)

    # 3) Calibrate voice speed -> WPM
    on_progress("Calibrating voice")
    wpm, provider = measure_wpm("elevenlabs" if voice_id and HAS_ELEVEN else "openai", voice_id)

    # 4) Target words plan
    # Use ~95% of time for speech; keep ~5% headroom
    target_minutes = float(min_minutes)
    target_words = max(120, int(target_minutes * wpm * 0.95))

    # 5) First script pass that covers all topics
    on_progress("Draft Attempt 1")
    script = script_from_bullets(topics, per_topic_bullets, language, tone, target_words)

    # 6) Iterative expand to hit target minutes with real speech (no silence padding)
    segs: List[AudioSegment] = []
    combined = AudioSegment.silent(duration=0)
    attempt = 1
    MAX_ATTEMPTS = 5
    while attempt <= MAX_ATTEMPTS:
        on_progress(f"Correct Expand {len(script.split())}")
        seg = synthesize(provider, voice_id, script)
        segs.append(seg)
        combined = sum(segs, AudioSegment.silent(duration=0))
        actual_mins = len(combined) / 60000.0
        if not exact_minutes:
            break
        # good enough?
        if abs(actual_mins - target_minutes) <= max(0.25, target_minutes * 0.03):
            break
        if actual_mins < target_minutes:
            # Need more content: ask LLM for continuation ~ remaining words
            remaining = max(80, int((target_minutes - actual_mins) * wpm * 0.98))
            on_progress(f"Draft Attempt {attempt+1}")
            script = continuation_script(language, tone, remaining, topics, [])
            attempt += 1
            continue
        else:
            # Slightly too long — speed-up by tiny pitch/tempo? Prefer not (quality hit).
            # Instead, stop if within 5%. Otherwise ask for a shorter closing paragraph and replace last seg.
            if (actual_mins - target_minutes) <= max(0.35, target_minutes * 0.05):
                break
            on_progress("Trim long tail with a brief closing")
            closing = openai_chat(
                f"You are Noah, a crisp anchor. Language: {language}. Tone: {tone}.",
                "Write a 2–3 sentence closing that wraps up the bulletin politely. 35–50 words.",
                temperature=0.4,
                tokens=120,
            )
            # Replace last seg with the closing only
            segs[-1] = synthesize(provider, voice_id, closing)
            combined = sum(segs, AudioSegment.silent(duration=0))
            break

    # Natural tiny tail; no long silent padding
    combined = trim_silence(combined)

    # 7) Build sources list (flatten per-topic to a single list, keep order)
    srcs_flat: List[Dict[str,str]] = []
    for q in topics:
        for s in per_topic_sources.get(q, []):
            srcs_flat.append({"title": s.get("title",""), "url": s.get("url","")})

    # 8) Export MP3
    file_id = uuid.uuid4().hex
    mp3_name = f"noah-{slug(','.join(topics))[:48]}-{file_id}.mp3"
    mp3_path = DATA_DIR / mp3_name
    combined.export(str(mp3_path), format="mp3", bitrate="128k")

    actual_minutes = round(len(combined) / 60000.0, 2)

    # 9) Bullet list for the UI (compact summary)
    bullets_all: List[str] = []
    for q in topics:
        bs = per_topic_bullets.get(q, [])
        if bs:
            bullets_all.append(f"{q}:")
            bullets_all.extend(bs[:6])

    return {
        "script": "",  # (optional; can be large; you can return it if you want)
        "bullets": bullets_all,
        "sources": srcs_flat,
        "mp3_path": str(mp3_path),
        "mp3_name": mp3_name,
        "actual_minutes": actual_minutes,
        "target_minutes": target_minutes,
        "playback_rate": 1.0,  # we did not time-warp; we used real extra content
        "tts_provider": provider,
    }

# ------------- Health check for /health -------------
def health_check() -> Dict[str, bool]:
    return {
        "openai": HAS_OPENAI,
        "elevenlabs": HAS_ELEVEN,
        "tavily": HAS_TAVILY,
        "storage": DATA_DIR.exists(),
    }
