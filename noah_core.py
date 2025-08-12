# noah_core.py — Core generation and exact-length audio for Noah
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

# Fine-tune only; content length should do the heavy lifting
MIN_ATEMPO, MAX_ATEMPO = 0.80, 1.25

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

# -------------------- Sources (Google News) --------------------

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

# -------------------- Script generation --------------------

def word_count(s: str) -> int:
    return len(re.findall(r"\b\w+\b", s))

def compute_targets(minutes: int, wps: float, intro: str, outro: str, n_stories: int) -> Dict[str,int]:
    total_secs = max(1, minutes * 60)
    total_words = int(total_secs * wps)
    intro_w, outro_w = word_count(intro), word_count(outro)
    body_words = max(60, total_words - intro_w - outro_w)
    per_story = max(40, int(body_words / max(1, n_stories)))
    return {
        "total_words": total_words,
        "min_words": int(total_words * 0.96),
        "max_words": int(total_words * 1.04),
        "per_story": per_story
    }

def openai_client() -> OpenAI:
    return OpenAI(api_key=OPENAI_API_KEY)

def build_messages(language: str, tone: str, queries: List[str],
                   sources: Dict[str,List[Dict[str,str]]],
                   targets: Dict[str,int], intro: str, outro: str):
    # Flatten sources list for outline sizing
    flat = []
    for q, items in sources.items():
        for it in items:
            flat.append((q, it.get("title",""), it.get("source",""), it.get("link","")))
    n = max(6, len(flat))  # at least 6 stories
    per_story = targets["per_story"]

    src_lines = []
    for q, items in sources.items():
        src_lines.append(f"Topic: {q}")
        for it in items:
            src_lines.append(f"- {it.get('title','')} ({it.get('source','')}) <{it.get('link','')}>")
    src_text = "\n".join(src_lines[:200])

    system = (
        "You are Noah, a concise, factual news editor.\n"
        "Return JSON with keys 'bullets' and 'narration'.\n"
        f"- Narration MUST be between {targets['min_words']} and {targets['max_words']} words (target≈{targets['total_words']}).\n"
        "- Use only the provided sources (no speculation). Keep sentences short and informative. No fluff.\n"
        "- Start EXACTLY with the intro and end EXACTLY with the outro provided.\n"
    )
    user = (
        f"Language: {language}\nTone: {tone}\n\n"
        f"Intro: {intro}\nOutro: {outro}\n\n"
        "Queries:\n" + "\n".join([f"- {q}" for q in queries]) + "\n\n"
        "Sources to rely on:\n" + src_text + "\n\n"
        f"Make a brief outline of ~{n} stories, each ~{per_story} words, "
        "then produce:\n"
        "1) 'bullets': a compact markdown bullet list of headlines you cover;\n"
        "2) 'narration': the full narration including the intro and outro.\n\n"
        "Return STRICT JSON only (no code fences):\n"
        "{\n  \"bullets\":\"markdown bullets\",\n  \"narration\":\"full narration including intro & outro\"\n}\n"
    )
    return [{"role":"system","content":system},{"role":"user","content":user}], n

def refine_length(client: OpenAI, narration: str, language: str, tone: str,
                  targets: Dict[str,int], direction: str) -> str:
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {"role":"system","content":"You precisely hit word targets without changing meaning."},
            {"role":"user","content":
                f"{direction} the narration to {targets['total_words']} words "
                f"(must be {targets['min_words']}–{targets['max_words']}). "
                f"Language={language}; tone={tone}. Keep ONLY facts from the supplied sources; no background. "
                "Return ONLY the revised narration text.\n\n"
                "Narration:\n"+narration}
        ]
    )
    return (r.choices[0].message.content or "").strip()

def generate_text(queries: List[str], language: str, tone: str,
                  sources: Dict[str,List[Dict[str,str]]], minutes: int) -> Tuple[str,str]:
    wps = wps_for(language)
    intro = INTRO.get(language, INTRO["English"])
    outro = OUTRO.get(language, OUTRO["English"])
    n_stories = max(6, sum(len(v) for v in sources.values()))
    targets = compute_targets(minutes, wps, intro, outro, n_stories)

    client = openai_client()
    # First pass
    msgs, _ = build_messages(language, tone, queries, sources, targets, intro, outro)
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.25,
        response_format={"type": "json_object"},
        messages=msgs
    )
    js = json.loads((r.choices[0].message.content or "{}").strip())
    bullets = (js.get("bullets") or "").strip()
    narration = (js.get("narration") or "").strip()

    # Correction passes (up to 5)
    for _ in range(5):
        wc = word_count(narration)
        if targets["min_words"] <= wc <= targets["max_words"]:
            return bullets, narration
        direction = "Expand" if wc < targets["min_words"] else "Tighten"
        narration = refine_length(client, narration, language, tone, targets, direction)

    # Last resort: trim to max or note more headlines
    wc = word_count(narration)
    if wc > targets["max_words"]:
        toks = narration.split()
        narration = " ".join(toks[:targets["max_words"]])
    elif wc < targets["min_words"]:
        narration += "\n(Additional headlines omitted for time.)"
    return bullets, narration

# -------------------- TTS --------------------

def tts_eleven(text: str, voice_id: Optional[str]) -> str:
    vid = voice_id or DEFAULT_VOICE_ID
    if not vid:
        try:
            resp = requests.get("https://api.elevenlabs.io/v1/voices",
                                headers={"xi-api-key": ELEVEN_API_KEY}, timeout=20)
            if resp.status_code == 200:
                voices = (resp.json() or {}).get("voices") or []
                if voices:
                    vid = voices[0].get("voice_id","")
        except Exception:
            pass
    if not vid:
        raise RuntimeError("No ElevenLabs voice available for this account.")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
    headers = {"xi-api-key": ELEVEN_API_KEY, "accept":"audio/mpeg", "content-type":"application/json"}
    payload = {"text": text, "model_id":"eleven_multilingual_v2",
               "voice_settings":{"stability":0.55,"similarity_boost":0.75,"style":0.25,"use_speaker_boost":True}}
    r = requests.post(url, headers=headers, json=payload, timeout=600)
    if r.status_code >= 400:
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text}")

    name = f"noah_{int(time.time())}_{uuid.uuid4().hex[:6]}.mp3"
    path = os.path.join(DATA_DIR, name)
    with open(path, "wb") as f: f.write(r.content)
    return path

def duration_s(path: str) -> float:
    return float(len(AudioSegment.from_file(path)) / 1000.0)

def exactify_with_atempo(path: str, target_seconds: int) -> Tuple[str,float]:
    actual = duration_s(path)
    if actual <= 0 or target_seconds <= 0: return path, 1.0
    desired = actual / float(target_seconds)  # >1 speed up, <1 slow down
    rate = max(MIN_ATEMPO, min(MAX_ATEMPO, desired))
    if abs(rate - 1.0) < 0.02: return path, 1.0
    out = path.replace(".mp3","_exact.mp3")
    cmd = f'ffmpeg -y -i "{path}" -filter:a "atempo={rate:.6f}" -vn "{out}"'
    code = os.system(cmd)
    if code != 0 or not os.path.exists(out): return path, 1.0
    return out, rate

# -------------------- Orchestrator --------------------

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

    mp3_path = tts_eleven(narration, voice_id)
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
