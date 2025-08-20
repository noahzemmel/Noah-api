# noah_core.py  —  Noah v2.2
# Fresh sources via Tavily (std + Expert), GDELT, Google; grounded bullets; calibrated TTS; exact-length audio.

from __future__ import annotations
import os, io, re, math, time, json, random, traceback
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Optional, Callable, Any
from pathlib import Path

import requests
import feedparser
from pydub import AudioSegment
from pydub.effects import speedup
from openai import OpenAI

# ---------------- Config ----------------
WPM_FALLBACK = float(os.getenv("NOAH_WPM", "165"))          # used if calibration fails
ATEMPO_MIN   = float(os.getenv("NOAH_ATEMPO_MIN", "0.88"))  # safe range for speed adjustment
ATEMPO_MAX   = float(os.getenv("NOAH_ATEMPO_MAX", "1.12"))
EXACTIFY_MAX_PASSES = int(os.getenv("NOAH_EXACTIFY_MAX_PASSES", "3"))
MAX_SOURCES_PER_TOPIC = int(os.getenv("NOAH_MAX_SOURCES_PER_TOPIC", "8"))
MAX_SOURCES_TOTAL     = int(os.getenv("NOAH_MAX_SOURCES_TOTAL", "28"))
DATA_DIR = Path(os.getenv("NOAH_DATA_DIR", "/tmp/noah_jobs")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

_CAL_WPS: Dict[str, float] = {}  # cached words/sec per voice

# -------------- tiny utils --------------
def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def parse_date(dt: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(dt, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            pass
    try:
        tup = feedparser._parse_date(dt)  # type: ignore
        if tup:
            return datetime(*tup[:6], tzinfo=timezone.utc)
    except Exception:
        pass
    return None

def within_hours(dt: Optional[datetime], lookback_h: int) -> bool:
    if not dt: return False
    return (now_utc() - dt) <= timedelta(hours=lookback_h)

def sanitize_queries(raw: object) -> List[str]:
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, str):
        items = [s.strip() for s in raw.splitlines()]
    else:
        items = []
    return [s for s in (i.strip() for i in items) if s]

def minutes_to_words(minutes: float, wps: float) -> int:
    return max(90, int(round(minutes * 60.0 * wps)))

# -------------- collectors --------------
def from_gdelt(query: str, recent_hours: int) -> List[Dict]:
    url = (
        "https://api.gdeltproject.org/api/v2/doc/doc"
        f"?query={requests.utils.quote(query)}&timespan={recent_hours}h"
        "&mode=artlist&format=json&maxrecords=35&sort=DateDesc"
    )
    out: List[Dict] = []
    try:
        r = requests.get(url, timeout=25)
        if not r.ok: return out
        data = r.json()
        for art in data.get("articles", []):
            t = (art.get("title") or "").strip()
            link = (art.get("url") or "").strip()
            seen = parse_date(art.get("seendate") or "")
            if not t or not link:
                continue
            out.append({
                "query": query, "title": t, "link": link,
                "published": seen.isoformat() if seen else "",
                "source": art.get("domain", "gdelt"),
                "snippet": (art.get("excerpt") or "")[:260],
                "ts": seen or now_utc()
            })
    except Exception:
        traceback.print_exc()
    return out

def from_googlenews(query: str, recent_hours: int, lang="en-GB", region="GB") -> List[Dict]:
    q = f"{query} when:{recent_hours}h"
    url = f"https://news.google.com/rss/search?q={requests.utils.quote(q)}&hl={lang}&gl={region}&ceid={region}:{lang.split('-')[0]}"
    out: List[Dict] = []
    try:
        feed = feedparser.parse(url)
        for e in feed.entries:
            pub = parse_date(e.get("published","") or e.get("updated",""))
            out.append({
                "query": query, "title": e.get("title",""), "link": e.get("link",""),
                "published": pub.isoformat() if pub else "", "source": (e.get("source",{}) or {}).get("title","google"),
                "snippet": (e.get("summary","") or "")[:260],
                "ts": pub or now_utc()
            })
    except Exception:
        traceback.print_exc()
    return out

def _domain_filters() -> Tuple[List[str], List[str]]:
    allow = [d.strip() for d in os.getenv("TAVILY_DOMAINS_ALLOW","").split(",") if d.strip()]
    block = [d.strip() for d in os.getenv("TAVILY_DOMAINS_BLOCK","").split(",") if d.strip()]
    return allow, block

def from_tavily(query: str, recent_hours: int) -> List[Dict]:
    key = os.getenv("TAVILY_API_KEY","").strip()
    if not key: return []
    allow, block = _domain_filters()
    payload: Dict[str, Any] = {
        "api_key": key,
        "query": query,
        "search_depth": "advanced",
        "time_range": "day" if recent_hours <= 24 else ("week" if recent_hours <= 168 else "month"),
        "include_answer": False,
        "max_results": 12,
        "include_domains": allow or None,
        "exclude_domains": block or None,
    }
    payload = {k:v for k,v in payload.items() if v is not None}
    out: List[Dict] = []
    try:
        r = requests.post("https://api.tavily.com/search", json=payload, timeout=30)
        if not r.ok: return out
        data = r.json()
        for res in data.get("results", []):
            title = (res.get("title") or "").strip()
            link  = (res.get("url")   or "").strip()
            when  = parse_date(res.get("published_date") or "") or now_utc()
            if not title or not link: continue
            out.append({
                "query": query, "title": title, "link": link,
                "published": when.isoformat(), "source": res.get("source","tavily"),
                "snippet": (res.get("content") or "")[:260], "ts": when
            })
    except Exception:
        traceback.print_exc()
    return out

def from_tavily_expert(query: str, recent_hours: int) -> List[Dict]:
    if os.getenv("TAVILY_USE_EXPERT","").lower() not in {"1","true","yes"}:
        return []
    key = os.getenv("TAVILY_API_KEY","").strip()
    if not key: return []
    endpoint = os.getenv("TAVILY_EXPERT_ENDPOINT","https://api.tavily.com/v1/expert/search").strip()
    allow, block = _domain_filters()
    payload: Dict[str, Any] = {
        "api_key": key,
        "query": query,
        "search_depth": "advanced",
        "time_range": "day" if recent_hours <= 24 else ("week" if recent_hours <= 168 else "month"),
        "max_results": 12,
        "include_domains": allow or None,
        "exclude_domains": block or None,
    }
    payload = {k:v for k,v in payload.items() if v is not None}
    out: List[Dict] = []
    try:
        r = requests.post(endpoint, json=payload, timeout=40)
        if not r.ok: return out
        data = r.json()
        results = data.get("results") or data.get("data") or []
        for res in results:
            title = (res.get("title") or "").strip()
            link  = (res.get("url") or res.get("link") or "").strip()
            when  = parse_date(res.get("published_date") or "") or now_utc()
            if not title or not link: continue
            out.append({
                "query": query, "title": title, "link": link,
                "published": when.isoformat(), "source": res.get("source","tavily_expert"),
                "snippet": (res.get("content") or res.get("summary") or "")[:260], "ts": when
            })
    except Exception:
        traceback.print_exc()
    return out

def fetch_sources(queries: List[str], recent_hours: int, cap_per_query: int, strict_recency=True) -> List[Dict]:
    """
    Collector order is controlled by NOAH_SOURCE_ORDER env var.
    Default: tavily_expert,tavily,gdelt,google
    """
    order = (os.getenv("NOAH_SOURCE_ORDER","tavily_expert,tavily,gdelt,google")
             .replace(" ","").split(","))
    collectors = {
        "tavily_expert": lambda q: from_tavily_expert(q, recent_hours),
        "tavily":        lambda q: from_tavily(q, recent_hours),
        "gdelt":         lambda q: from_gdelt(q, recent_hours),
        "google":        lambda q: from_googlenews(q, recent_hours),
    }

    all_items: List[Dict] = []
    for q in queries:
        items: List[Dict] = []
        for name in order:
            fn = collectors.get(name)
            if fn: items.extend(fn(q))
        if strict_recency:
            items = [i for i in items if within_hours(i.get("ts"), recent_hours)]
        # dedupe by link
        seen = set(); uniq=[]
        for i in items:
            k = i.get("link")
            if k and k not in seen:
                uniq.append(i); seen.add(k)
        uniq.sort(key=lambda x: x.get("ts") or now_utc(), reverse=True)
        all_items.extend(uniq[:cap_per_query])
    return all_items[:MAX_SOURCES_TOTAL]

# -------------- LLM helpers --------------
def openai_client() -> OpenAI:
    return OpenAI()

def build_cited_json_script(queries: List[str], sources: List[Dict], language: str, tone: str,
                            target_words: int, hours: int) -> Tuple[str, List[Dict]]:
    """Returns (script, bullets[]), bullets are [{text, sources:[idx,...]}]"""
    client = openai_client()

    catalog_lines = []
    for idx, s in enumerate(sources, start=1):
        line = f"[{idx}] {s.get('title','').strip()} — {s.get('source','')} — {s.get('link','')}"
        if s.get("published"): line += f" — {s['published']}"
        if s.get("snippet"):   line += f" — {s['snippet']}"
        catalog_lines.append(line)
    catalog = "\n".join(catalog_lines) if catalog_lines else "(no sources)"

    sys = (
        "You are Noah, a factual news editor. Create a concise radio script ONLY from the numbered sources provided. "
        f"Time window is the last {hours} hours; prefer newest; avoid filler. "
        "Every claim must be supported by at least one source index. Include [index] citations inline."
    )
    user = (
        f"Language: {language}\nTone: {tone}\nTopics: {', '.join(queries)}\n"
        f"Target words: ~{target_words}\n\nSources:\n{catalog}\n\n"
        "Respond as JSON with keys:\n"
        "  bullets: [{\"text\": string, \"sources\": [numbers]}]\n"
        "  script: string (keep bracket citations like [2], [5])\n"
    )

    resp = client.chat.completions.create(
        model=os.getenv("NOAH_SUMMARY_MODEL","gpt-4o-mini"),
        temperature=0.2,
        response_format={"type":"json_object"},
        messages=[{"role":"system","content":sys},{"role":"user","content":user}],
    )
    data = json.loads(resp.choices[0].message.content)
    bullets = [b for b in data.get("bullets", []) if isinstance(b, dict) and b.get("text")]
    script  = (data.get("script") or "").strip()
    if not script:
        script = " ".join(b.get("text","") for b in bullets)
    return script, bullets

def length_correct(text: str, target_words: int, language: str, tone: str) -> str:
    client = openai_client()
    sys = "Adjust the script to match the target word count (±3%). Keep citations like [3] intact. Be concise."
    user = f"Language: {language}\nTone: {tone}\nTarget words: {target_words}\nScript:\n{text}\n\nReturn only the revised script."
    out = client.chat.completions.create(
        model=os.getenv("NOAH_EDITOR_MODEL","gpt-4o-mini"),
        temperature=0.2,
        messages=[{"role":"system","content":sys},{"role":"user","content":user}],
    )
    return out.choices[0].message.content.strip()

# -------------- TTS --------------
def tts_openai(text: str, out_path: str, voice: Optional[str] = None) -> str:
    client = openai_client()
    model = os.getenv("OPENAI_TTS_MODEL","gpt-4o-mini-tts")
    v = voice or os.getenv("OPENAI_TTS_VOICE","alloy")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with client.audio.speech.with_streaming_response.create(
        model=model, voice=v, input=text
    ) as r:
        r.stream_to_file(out_path)
    return os.path.abspath(out_path)

def tts_eleven(text: str, out_path: str, voice_id: Optional[str]) -> str:
    key = os.getenv("ELEVENLABS_API_KEY","").strip()
    if not key: raise RuntimeError("ELEVENLABS_API_KEY missing")
    vid = voice_id or os.getenv("ELEVENLABS_VOICE_ID","") or "21m00Tcm4TlvDq8ikWAM"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/stream?optimize_streaming_latency=3"
    headers = {"xi-api-key": key, "accept": "audio/mpeg", "content-type": "application/json"}
    payload = {"text": text, "voice_settings": {"stability": 0.4, "similarity_boost": 0.7}}
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with requests.post(url, headers=headers, data=json.dumps(payload), stream=True, timeout=180) as r:
        r.raise_for_status()
        with open(out_path,"wb") as f:
            for chunk in r.iter_content(8192):
                if chunk: f.write(chunk)
    return os.path.abspath(out_path)

def audio_len_sec(p: str) -> float:
    return AudioSegment.from_file(p).duration_seconds

def calibrate_wps(provider: str, voice_id: str = "") -> float:
    key = f"{provider}:{voice_id or os.getenv('OPENAI_TTS_VOICE','alloy')}"
    if key in _CAL_WPS: return _CAL_WPS[key]
    sample = ("This is a short calibration passage for Noah to measure speaking rate. " * 6).strip()
    words = len(re.findall(r"\w+", sample))
    tmp = DATA_DIR / f"cal_{abs(hash(key))}.mp3"
    try:
        if provider == "elevenlabs":
            tts_eleven(sample, str(tmp), voice_id or os.getenv("ELEVENLABS_VOICE_ID",""))
        else:
            tts_openai(sample, str(tmp), voice=os.getenv("OPENAI_TTS_VOICE","alloy"))
        dur = audio_len_sec(str(tmp))
        wps = max(2.0, min(4.0, words / max(0.5, dur)))
    except Exception:
        traceback.print_exc()
        wps = WPM_FALLBACK / 60.0
    finally:
        try: tmp.unlink(missing_ok=True)
        except: pass
    _CAL_WPS[key] = wps
    return wps

def exactify_audio(mp3: str, target_minutes: float) -> Tuple[str, float, float]:
    cur = audio_len_sec(mp3)
    target = max(1.0, target_minutes * 60.0)
    rate = clamp(target / cur, ATEMPO_MIN, ATEMPO_MAX)
    au = AudioSegment.from_file(mp3)
    if abs(rate - 1.0) > 0.01:
        au = speedup(au, playback_speed=rate)
    new_len = au.duration_seconds
    if new_len < target - 0.25:
        au += AudioSegment.silent(duration=int((target - new_len) * 1000))
    out = str(Path(mp3).with_suffix(".ex.mp3"))
    au.export(out, format="mp3")
    return out, audio_len_sec(out), rate

# -------------- main API --------------
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
) -> Dict[str, Any]:

    def tick(msg: str):
        if on_progress: on_progress(msg)

    queries = sanitize_queries(queries_raw)
    if not queries:
        raise ValueError("No topics provided")

    tick("Collecting sources…")
    sources = fetch_sources(queries, recent_hours, cap_per_query, strict_recency=True)
    if not sources:
        tick("No fresh sources – widening search a bit…")
        sources = fetch_sources(queries, min(72, max(24, recent_hours*2)), cap_per_query, strict_recency=True)

    sources = sources[:MAX_SOURCES_TOTAL]

    provider = (os.getenv("NOAH_TTS_PROVIDER","openai") or "openai").lower()
    if provider == "auto":
        provider = "elevenlabs" if os.getenv("ELEVENLABS_API_KEY","").strip() else "openai"

    # calibration → target words
    wps = calibrate_wps(provider, voice_id or os.getenv("ELEVENLABS_VOICE_ID",""))
    target_words = minutes_to_words(min_minutes, wps)

    tick("Draft Attempt 1")
    script, bullets = build_cited_json_script(queries, sources, language, tone, target_words, hours=recent_hours)

    # tighten to target words
    for _ in range(EXACTIFY_MAX_PASSES):
        wc = len(re.findall(r"\w+", script))
        if abs(wc - target_words) / target_words <= 0.04:
            break
        tick(f"Correct to ~{target_words} words (was {wc})")
        script = length_correct(script, target_words, language, tone)

    # intro/outro (short, not counted toward target words)
    intro = "Welcome to your daily Noah. "
    outro = "That’s your briefing for today. See you tomorrow."
    script = f"{intro}{script} {outro}"

    tick("TTS start")
    raw_path = DATA_DIR / f"noah_{int(time.time())}_{random.randint(1000,9999)}.mp3"
    try:
        if provider == "elevenlabs":
            try:
                tts_eleven(script, str(raw_path), voice_id)
                used = "elevenlabs"
            except Exception:
                traceback.print_exc()
                tts_openai(script, str(raw_path), voice=os.getenv("OPENAI_TTS_VOICE","alloy"))
                used = "openai"
        else:
            tts_openai(script, str(raw_path), voice=os.getenv("OPENAI_TTS_VOICE","alloy"))
            used = "openai"
    except Exception as e:
        raise RuntimeError(f"TTS failed: {e}")

    tick("Exactifying audio")
    final_path, secs, rate = exactify_audio(str(raw_path), min_minutes if exact_minutes else (len(re.findall(r'\w+', script))/wps/60.0))
    try: Path(raw_path).unlink(missing_ok=True)
    except: pass

    return {
        "script": script,
        "bullets": bullets,
        "sources": [
            {"idx": i+1, "query": s.get("query"), "title": s.get("title"),
             "link": s.get("link"), "published": s.get("published"), "source": s.get("source")}
            for i, s in enumerate(sources)
        ],
        "mp3_path": final_path,
        "actual_minutes": round(secs/60.0, 2),
        "target_minutes": float(min_minutes),
        "playback_rate": round(rate, 3),
        "tts_provider": used,
    }

# -------------- health (used by /health) --------------
def health_check() -> Dict[str, Any]:
    return {
        "openai": bool(os.getenv("OPENAI_API_KEY","").strip()),
        "tavily": bool(os.getenv("TAVILY_API_KEY","").strip()),
        "elevenlabs": bool(os.getenv("ELEVENLABS_API_KEY","").strip()),
    }
