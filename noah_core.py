import os, re, json, time, uuid, requests, feedparser
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timezone
from pydub import AudioSegment
from openai import OpenAI

DATA_DIR = os.getenv("NOAH_DATA_DIR", "/app/data")
os.makedirs(DATA_DIR, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

# Natural limits for atempo (server-side exact fit). Keep mild to preserve quality.
MIN_ATEMPO, MAX_ATEMPO = 0.85, 1.25

# Per-language speaking rates (words/sec). Tweak as needed.
LANG_WPS = {
    "English": 2.6, "Spanish": 2.5, "French": 2.4, "German": 2.3, "Italian": 2.5,
    "Portuguese": 2.5, "Arabic": 2.3, "Hindi": 2.5, "Japanese": 2.2, "Korean": 2.3,
    "Chinese (Simplified)": 2.3
}
DEFAULT_WPS = 2.6

INTRO = {"English": "Welcome to your daily Noah."}
OUTRO = {"English": "That's your Noah for today. See you tomorrow."}

def health_check() -> bool:
    return bool(OPENAI_API_KEY and ELEVEN_API_KEY)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def wps_for(language: str) -> float:
    return float(os.getenv("NOAH_WORDS_PER_SECOND", LANG_WPS.get(language, DEFAULT_WPS)))

# ---------- Sources (Google News) ----------
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

# ---------- Script generation with *tight* word target ----------
def word_count(s: str) -> int:
    return len(re.findall(r"\b\w+\b", s))

def compute_targets(minutes: int, wps: float, intro: str, outro: str) -> Tuple[int,int,int,int]:
    total_secs = max(1, minutes * 60)
    target_words = int(total_secs * wps)
    # Hit within ±5%. Also set hard min to avoid underfills.
    lo = max(120, int(target_words * 0.95))
    hi = int(target_words * 1.05)
    intro_w, outro_w = word_count(intro), word_count(outro)
    body_hint = max(30, int((target_words - intro_w - outro_w) / 6))
    return target_words, lo, hi, body_hint

def openai_client() -> OpenAI:
    return OpenAI(api_key=OPENAI_API_KEY)

def build_messages(language: str, tone: str, queries: List[str], sources: Dict[str, List[Dict[str,str]]],
                   target: int, lo: int, hi: int, body_hint: int, intro: str, outro: str):
    src_lines = []
    for q, items in sources.items():
        src_lines.append(f"Topic: {q}")
        for it in items:
            src_lines.append(f"- {it.get('title','')} ({it.get('source','')}) <{it.get('link','')}>")
    src_text = "\n".join(src_lines[:120])

    system = (
        "You are Noah, a concise news editor.\n"
        "Return *JSON* with keys 'bullets' and 'narration'.\n"
        "Rules:\n"
        f"- Narration (INCLUDING intro & outro) MUST be between {lo} and {hi} words (target≈{target}).\n"
        "- Use fresh items from the provided sources; avoid background unless essential.\n"
        "- Keep sentences short, factual, and topical.\n"
        "- Start with the intro line and end with the outro line exactly as provided.\n"
    )
    user = (
        f"Language: {language}\n"
        f"Tone: {tone}\n\n"
        f"Intro: {intro}\n"
        f"Outro: {outro}\n\n"
        "Queries:\n" + "\n".join([f"- {q}" for q in queries]) + "\n\n"
        "Sources to rely on:\n" + src_text + "\n\n"
        f"Per-story hint: ~{body_hint} words (rebalance as needed).\n"
        "Return JSON only:\n{\n  \"bullets\": \"markdown bullets\",\n  \"narration\": \"full narration including intro & outro\"\n}\n"
    )
    return [{"role":"system","content":system},{"role":"user","content":user}]

def generate_text(queries: List[str], language: str, tone: str,
                  sources: Dict[str,List[Dict[str,str]]], minutes: int) -> Tuple[str,str]:
    wps = wps_for(language)
    intro = INTRO.get(language, INTRO["English"])
    outro = OUTRO.get(language, OUTRO["English"])
    target, lo, hi, body_hint = compute_targets(minutes, wps, intro, outro)

    client = openai_client()
    for _ in range(4):
        msgs = build_messages(language, tone, queries, sources, target, lo, hi, body_hint, intro, outro)
        r = client.chat.completions.create(model="gpt-4o-mini", temperature=0.3, messages=msgs)
        content = (r.choices[0].message.content or "").strip()

        # Extract JSON (robust)
        try:
            data = json.loads(content)
        except Exception:
            m = re.search(r"\{.*\}", content, re.S)
            data = json.loads(m.group(0)) if m else {}

        bullets = (data.get("bullets") or "").strip()
        narration = (data.get("narration") or "").strip()

        wc = word_count(narration)
        if lo <= wc <= hi:
            return bullets, narration

        # Ask model to expand/trim to target window
        goal = f"Expand" if wc < lo else "Tighten"
        ask = (
            f"{goal} to {target} words (must be between {lo} and {hi}). "
            f"Keep language={language}, tone={tone}. Keep facts grounded in the supplied sources. "
            "Return ONLY the revised narration text."
        )
        r2 = client.chat.completions.create(
            model="gpt-4o-mini", temperature=0.2,
            messages=[{"role":"system","content":"You precisely fit word targets."},
                      {"role":"user","content": ask + "\n\nCurrent narration:\n" + narration}]
        )
        narration2 = (r2.choices[0].message.content or "").strip()
        if lo <= word_count(narration2) <= hi:
            return bullets, narration2

        # Narrow window slightly next attempt
        lo = int(lo * 0.98); hi = int(hi * 1.02)

    # Final fallback: trim/extend heuristically
    toks = narration.split()
    if len(toks) < lo:
        narration = narration + "\n\n" + " ".join(["(…more headlines…)" for _ in range((lo - len(toks)) // 3)])
    else:
        narration = " ".join(toks[:hi])
    return bullets, narration

# ---------- TTS ----------
def tts_eleven(text: str, voice_id: Optional[str], language: str) -> str:
    vid = voice_id or DEFAULT_VOICE_ID
    if not vid: raise RuntimeError("No ElevenLabs voice_id is set.")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
    headers = {"xi-api-key": ELEVEN_API_KEY, "accept":"audio/mpeg", "content-type":"application/json"}
    payload = {"text": text, "model_id": "eleven_multilingual_v2",
               "voice_settings":{"stability":0.55,"similarity_boost":0.75,"style":0.25,"use_speaker_boost":True}}
    r = requests.post(url, headers=headers, json=payload, timeout=600)
    if r.status_code >= 400: raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text}")
    name = f"noah_{int(time.time())}_{uuid.uuid4().hex[:6]}.mp3"
    path = os.path.join(DATA_DIR, name)
    with open(path, "wb") as f: f.write(r.content)
    return path

def duration_s(path: str) -> float:
    return float(len(AudioSegment.from_file(path)) / 1000.0)

def exactify_with_atempo(path: str, target_seconds: int) -> Tuple[str,float]:
    actual = duration_s(path)
    if actual <= 0 or target_seconds <= 0: return path, 1.0
    desired_rate = actual / float(target_seconds)  # >1 means speed up, <1 slow down
    rate = max(MIN_ATEMPO, min(MAX_ATEMPO, desired_rate))
    if abs(rate - 1.0) < 0.02: return path, 1.0
    out = path.replace(".mp3","_exact.mp3")
    cmd = f'ffmpeg -y -i "{path}" -filter:a "atempo={rate:.6f}" -vn "{out}"'
    code = os.system(cmd)
    if code != 0 or not os.path.exists(out): return path, 1.0
    return out, rate

# ---------- Orchestrator ----------
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

    sources = collect_sources(queries, recent_hours, cap_per_query)
    bullets, narration = generate_text(queries, language, tone, sources, minutes_target)

    mp3_path = tts_eleven(narration, voice_id, language)
    dur = duration_s(mp3_path)
    applied = 1.0
    if exact_minutes:
        target = max(1, minutes_target * 60)
        new_path, applied = exactify_with_atempo(mp3_path, target)
        if new_path != mp3_path:
            mp3_path = new_path
            dur = duration_s(mp3_path)

    return {
        "bullet_points": bullets,
        "script": narration,
        "sources": sources,
        "file_path": mp3_path,
        "duration_seconds": dur,
        "minutes_target": minutes_target,
        "playback_rate_applied": applied,
        "generated_at": now_iso(),
    }
