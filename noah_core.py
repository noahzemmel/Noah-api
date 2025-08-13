# noah_core.py — exact-length generation with progress hooks, retries, and fast calibration
import os, re, json, time, uuid, requests, feedparser
from typing import Dict, List, Any, Tuple, Optional, Callable
from datetime import datetime, timezone
from pydub import AudioSegment
from openai import OpenAI

# ---------------- Paths & keys ----------------
DATA_DIR = os.getenv("NOAH_DATA_DIR", "/app/data")
os.makedirs(DATA_DIR, exist_ok=True)
WPS_CACHE_PATH = os.path.join(DATA_DIR, "wps_cache.json")
WPS_CACHE_TTL_DAYS = int(os.getenv("NOAH_WPS_CACHE_DAYS", "30"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

# Final atempo bounds (keep mild for quality)
MIN_ATEMPO, MAX_ATEMPO = 0.85, 1.20

# Fallback WPS if calibration not available
LANG_WPS = {
    "English": 2.6, "Spanish": 2.5, "French": 2.4, "German": 2.3, "Italian": 2.5,
    "Portuguese": 2.5, "Arabic": 2.3, "Hindi": 2.5, "Japanese": 2.2, "Korean": 2.3,
    "Chinese (Simplified)": 2.3
}
DEFAULT_WPS = 2.6

INTRO = {"English": "Welcome to your daily Noah."}
OUTRO = {"English": "That's your Noah for today. See you tomorrow."}

# ---------------- Utils ----------------
def health_check() -> bool:
    return bool(OPENAI_API_KEY and ELEVEN_API_KEY)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def word_count(s: str) -> int:
    return len(re.findall(r"\b\w+\b", s))

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def openai_client() -> OpenAI:
    return OpenAI(api_key=OPENAI_API_KEY)

def _with_retries(fn: Callable[[], requests.Response], tries=3, base=1.0, factor=1.6):
    last = None
    for i in range(tries):
        try:
            r = fn()
            if r.status_code in (502, 503, 504):
                raise requests.exceptions.RequestException(f"Upstream {r.status_code}")
            return r
        except Exception as e:
            last = e
            time.sleep(base * (factor ** i))
    raise last

# ---------------- Source collection (Google News) ----------------
def _google_news_rss(query: str, recent_hours: int) -> str:
    q = requests.utils.quote(query)
    when = f" when:{recent_hours}h" if recent_hours else ""
    return f"https://news.google.com/rss/search?q={q}{requests.utils.quote(when)}&hl=en-GB&gl=GB&ceid=GB:en"

def fetch_sources(query: str, recent_hours: int, cap: int) -> List[Dict[str,str]]:
    url = _google_news_rss(query, recent_hours)
    try:
        parsed = feedparser.parse(url)
    except Exception:
        return []
    items, seen = [], set()
    for e in parsed.entries:
        title = e.get("title") or ""
        link = e.get("link") or ""
        src = (e.get("source") or {}).get("title", "")
        if title and link and link not in seen:
            items.append({"title": title, "link": link, "source": src})
            seen.add(link)
        if len(items) >= cap:
            break
    return items

def collect_sources(queries: List[str], recent_hours: int, cap: int) -> Dict[str,List[Dict[str,str]]]:
    return {q: fetch_sources(q, recent_hours, cap) for q in queries}

# ---------------- ElevenLabs TTS ----------------
def _tts_call(text: str, voice_id: str) -> bytes:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": ELEVEN_API_KEY, "accept":"audio/mpeg", "content-type":"application/json"}
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability":0.55,"similarity_boost":0.75,"style":0.25,"use_speaker_boost":True}
    }
    r = _with_retries(lambda: requests.post(url, headers=headers, json=payload, timeout=180))
    if r.status_code >= 400:
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:300]}")
    return r.content

def _resolve_voice(voice_id: Optional[str]) -> str:
    vid = voice_id or DEFAULT_VOICE_ID
    if vid:
        return vid
    try:
        r = _with_retries(lambda: requests.get("https://api.elevenlabs.io/v1/voices",
                                               headers={"xi-api-key": ELEVEN_API_KEY}, timeout=20))
        voices = (r.json() or {}).get("voices") or []
        if voices:
            return voices[0].get("voice_id","")
    except Exception:
        pass
    raise RuntimeError("No ElevenLabs voice available for this account.")

def tts_to_file(text: str, voice_id: Optional[str]) -> str:
    vid = _resolve_voice(voice_id)
    audio = _tts_call(text, vid)
    name = f"noah_{int(time.time())}_{uuid.uuid4().hex[:6]}.mp3"
    path = os.path.join(DATA_DIR, name)
    with open(path, "wb") as f: f.write(audio)
    return path

def audio_duration(path: str) -> float:
    return float(len(AudioSegment.from_file(path)) / 1000.0)

def exactify_with_atempo(path: str, target_seconds: int) -> Tuple[str,float]:
    actual = audio_duration(path)
    if actual <= 0 or target_seconds <= 0: return path, 1.0
    desired = actual / float(target_seconds)  # >1 speed up, <1 slow down
    rate = clamp(desired, MIN_ATEMPO, MAX_ATEMPO)
    if abs(rate - 1.0) < 0.02: return path, 1.0
    out = path.replace(".mp3","_exact.mp3")
    cmd = f'ffmpeg -y -i "{path}" -filter:a "atempo={rate:.6f}" -vn "{out}"'
    code = os.system(cmd)
    if code != 0 or not os.path.exists(out): return path, 1.0
    return out, rate

# ---------------- WPS calibration (cached) ----------------
def _load_wps_cache() -> Dict[str, Any]:
    if not os.path.exists(WPS_CACHE_PATH): return {}
    try:
        with open(WPS_CACHE_PATH, "r") as f: return json.load(f)
    except Exception:
        return {}

def _save_wps_cache(cache: Dict[str, Any]) -> None:
    try:
        with open(WPS_CACHE_PATH, "w") as f: json.dump(cache, f)
    except Exception:
        pass

def _calibration_text(language: str, words: int = 100) -> str:
    base = "This sample measures typical narration speed for news style delivery."
    sent_words = word_count(base)
    reps = max(1, int(words / sent_words))
    return " ".join([base] * reps)

def calibrate_wps(voice_id: Optional[str], language: str, progress=None) -> float:
    vid = _resolve_voice(voice_id)
    key = f"{language}::{vid}"
    cache = _load_wps_cache()
    rec = cache.get(key)
    now = time.time()
    if rec and (now - rec.get("ts", 0)) < (WPS_CACHE_TTL_DAYS * 86400):
        if progress: progress("calibration_cache_hit")
        return float(rec.get("wps", DEFAULT_WPS))

    if progress: progress("calibrating_voice")
    try:
        text = _calibration_text(language, 100)  # faster
        tmp_path = tts_to_file(text, vid)
        dur = audio_duration(tmp_path)  # seconds
        wc = word_count(text)
        wps = clamp(wc / max(dur, 1.0), 1.6, 3.6)  # bound
        cache[key] = {"wps": wps, "ts": now}
        _save_wps_cache(cache)
        return float(wps)
    except Exception:
        if progress: progress("calibration_failed")
        return float(LANG_WPS.get(language, DEFAULT_WPS))

# ---------------- Target calculation ----------------
def compute_targets(minutes: int, wps: float, intro: str, outro: str, n_stories: int) -> Dict[str,int]:
    total_secs = max(1, minutes * 60)
    total_words = int(total_secs * wps)
    intro_w, outro_w = word_count(intro), word_count(outro)
    body_words = max(60, total_words - intro_w - outro_w)
    per_story = max(40, int(body_words / max(6, n_stories)))
    return {
        "total": total_words,
        "min": int(total_words * 0.99),
        "max": int(total_words * 1.01),
        "per_story": per_story
    }

# ---------------- OpenAI helpers ----------------
def _message_text(msg_obj) -> str:
    if msg_obj is None: return ""
    parsed = getattr(msg_obj, "parsed", None)
    if isinstance(parsed, dict):
        try: return json.dumps(parsed)
        except Exception: pass
    content = getattr(msg_obj, "content", None)
    if isinstance(content, str): return content
    if isinstance(content, list):
        buf = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                buf.append(part.get("text", ""))
            else:
                buf.append(str(part))
        return "".join(buf)
    if isinstance(content, dict):
        try: return json.dumps(content)
        except Exception: return str(content)
    return str(content or "")

def _message_json(msg_obj) -> Dict[str, Any]:
    parsed = getattr(msg_obj, "parsed", None)
    if isinstance(parsed, dict): return parsed
    text = _message_text(msg_obj)
    try: return json.loads(text.strip())
    except Exception: return {}

def _chat_json(client: OpenAI, messages: list, temp=0.25) -> Dict[str, Any]:
    tries = 3
    last = {}
    for i in range(tries):
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=temp,
            response_format={"type": "json_object"},
            messages=messages,
            timeout=60
        )
        js = _message_json(r.choices[0].message)
        if js: return js
        time.sleep(1.2 * (i+1))
        last = js
    return last

def _chat_text(client: OpenAI, messages: list, temp=0.2) -> str:
    tries = 3
    last = ""
    for i in range(tries):
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=temp,
            messages=messages,
            timeout=60
        )
        txt = (_message_text(r.choices[0].message) or "").strip()
        if txt: return txt
        time.sleep(1.2 * (i+1))
        last = txt
    return last

# ---------------- Prompting ----------------
def build_messages(language: str, tone: str, queries: List[str],
                   sources: Dict[str,List[Dict[str,str]]],
                   targets: Dict[str,int], intro: str, outro: str):
    src_lines = []
    for q, items in sources.items():
        src_lines.append(f"Topic: {q}")
        for it in items:
            src_lines.append(f"- {it.get('title','')} ({it.get('source','')}) <{it.get('link','')}>")
    src_text = "\n".join(src_lines[:220])

    n = max(6, sum(len(v) for v in sources.values()))
    per_story = targets["per_story"]

    system = (
        "You are Noah, a concise, factual news editor.\n"
        "Return JSON with keys 'bullets' and 'narration'.\n"
        f"- The final 'narration' MUST be between {targets['min']} and {targets['max']} words (target≈{targets['total']}).\n"
        "- Use only the provided sources. No filler; keep it topical and recent.\n"
        "- Sentences short and crisp. Start EXACTLY with the intro and end EXACTLY with the outro.\n"
    )
    user = (
        f"Language: {language}\nTone: {tone}\n\n"
        f"Intro: {intro}\nOutro: {outro}\n\n"
        "Queries:\n" + "\n".join([f"- {q}" for q in queries]) + "\n\n"
        "Sources to rely on:\n" + src_text + "\n\n"
        f"Make an outline of about {n} micro-stories (each ~{per_story} words), then produce:\n"
        "1) 'bullets': compact markdown bullets of the headlines you cover;\n"
        "2) 'narration': the full narration including the intro and outro.\n\n"
        "Return STRICT JSON only (no code fences):\n"
        "{\n  \"bullets\":\"markdown bullets\",\n  \"narration\":\"full narration including intro & outro\"\n}\n"
    )
    return [{"role":"system","content":system},{"role":"user","content":user}]

def refine_length(client: OpenAI, narration: str, language: str, tone: str,
                  targets: Dict[str,int], direction: str) -> str:
    msgs = [
        {"role":"system","content":"You precisely fit strict word targets without changing meaning."},
        {"role":"user","content":
            f"{direction} the narration to {targets['total']} words "
            f"(must be {targets['min']}–{targets['max']}). "
            f"Language={language}; tone={tone}. Keep ONLY fresh facts from the supplied sources; no background. "
            "Return ONLY the revised narration text.\n\n"
            "Narration:\n"+narration}
    ]
    return _chat_text(openai_client(), msgs, temp=0.2)

# ---------------- Generation ----------------
def generate_text(queries: List[str], language: str, tone: str,
                  sources: Dict[str,List[Dict[str,str]]], minutes: int,
                  wps: float, progress=None) -> Tuple[str,str,int,int,int]:
    intro = INTRO.get(language, INTRO["English"])
    outro = OUTRO.get(language, OUTRO["English"])
    n_stories = max(6, sum(len(v) for v in sources.values()))
    targets = compute_targets(minutes, wps, intro, outro, n_stories)

    client = openai_client()
    attempts = 0
    corrections_total = 0
    bullets, narration = "", ""

    while attempts < 3:
        attempts += 1
        if progress: progress(f"draft_attempt_{attempts}")
        msgs = build_messages(language, tone, queries, sources, targets, intro, outro)
        js = _chat_json(client, msgs, temp=0.25)
        bullets = (js.get("bullets") or "")
        if not isinstance(bullets, str): bullets = str(bullets)
        narration = (js.get("narration") or "")
        if not isinstance(narration, str): narration = str(narration)
        bullets, narration = bullets.strip(), narration.strip()

        # Up to 6 correction passes to enter ±1% band
        for _ in range(6):
            wc = word_count(narration)
            if targets["min"] <= wc <= targets["max"]:
                return bullets, narration, wc, corrections_total, attempts
            direction = "Expand" if wc < targets["min"] else "Tighten"
            if progress: progress(f"correct_{direction.lower()}_{wc}")
            narration = refine_length(client, narration, language, tone, targets, direction)
            corrections_total += 1

        # Widen slightly for next attempt
        targets["min"] = int(targets["total"] * 0.985)
        targets["max"] = int(targets["total"] * 1.015)

    # Last resort: clamp
    wc = word_count(narration)
    if wc > targets["max"]:
        toks = narration.split()
        narration = " ".join(toks[:targets["max"]])
    elif wc < targets["min"]:
        narration += "\n(Additional headlines omitted for time.)"
    return bullets, narration, word_count(narration), corrections_total, attempts

# ---------------- Orchestrator ----------------
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
    progress: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:

    # 1) sources
    if progress: progress("collecting_sources")
    sources = collect_sources(queries, recent_hours, cap_per_query)

    # 2) per-voice calibrated WPS (cached)
    wps = calibrate_wps(voice_id, language, progress=progress)

    # 3) generate text to target words
    bullets, narration, wc, corr, attempts = generate_text(
        queries, language, tone, sources, minutes_target, wps, progress=progress
    )

    # 4) TTS
    if progress: progress("tts_start")
    mp3_path = tts_to_file(narration, voice_id)
    dur = audio_duration(mp3_path)
    applied = 1.0

    # 5) Exactify
    if exact_minutes:
        if progress: progress("exactify_audio")
        target = max(1, minutes_target * 60)
        new_path, applied = exactify_with_atempo(mp3_path, target)
        if new_path != mp3_path:
            mp3_path = new_path
            dur = audio_duration(mp3_path)

    if progress: progress("done")

    return {
        "bullet_points": bullets,
        "script": narration,
        "sources": sources,
        "file_path": mp3_path,
        "duration_seconds": dur,
        "minutes_target": minutes_target,
        "playback_rate_applied": applied,
        "generated_at": now_iso(),
        # Diagnostics
        "calibrated_wps": wps,
        "narration_word_count": wc,
        "correction_passes": corr,
        "attempts": attempts,
    }
