# noah_core.py
import io, os, re, math, time, json
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from urllib.parse import quote_plus
from pathlib import Path

import feedparser
import requests
from pydub import AudioSegment
from dotenv import load_dotenv, find_dotenv

# ---------- constants ----------
WPM_DEFAULT = 170
WORDS_PER_ITEM = 90
INTRO_MS = 350
OUTRO_MS = 650
CHUNK_MAX_CHARS = 2500

# ---------- robust env ----------
env_path = find_dotenv(usecwd=True) or str((Path(__file__).parent / ".env").resolve())
load_dotenv(dotenv_path=env_path)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

# ---------- OpenAI client ----------
from openai import OpenAI
oai = OpenAI()  # reads OPENAI_API_KEY from env

# ---------- helpers ----------
def clean_text(t: str) -> str:
    import re
    return re.sub(r"\s+", " ", (t or "")).strip()

def minutes_to_words(minutes: int, wpm: int = WPM_DEFAULT) -> int:
    return max(60, int(minutes * max(90, min(240, wpm))))

def count_words(text: str) -> int:
    import re
    return len(re.findall(r"\b\w+\b", text or ""))

def google_news_rss(query: str, lang_ceid: str = "US:en") -> str:
    from urllib.parse import quote_plus
    q = quote_plus(query)
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid={lang_ceid}"

def youtube_search_rss(query: str) -> str:
    q = quote_plus(query)
    return f"https://www.youtube.com/feeds/videos.xml?search_query={q}"

def arxiv_search_rss(query: str) -> str:
    q = quote_plus(query)
    return f"http://export.arxiv.org/api/query?search_query=all:{q}&sortBy=submittedDate&sortOrder=descending"

LANG_TO_CEID = {
    "English": "US:en", "Spanish": "ES:es", "French": "FR:fr", "German": "DE:de",
    "Italian": "IT:it", "Portuguese": "PT:pt", "Arabic": "AE:ar", "Hindi": "IN:hi",
    "Japanese": "JP:ja", "Korean": "KR:ko", "Chinese (Simplified)": "CN:zh-Hans",
}

def build_urls_for_query(query: str, language: str) -> list:
    ceid = LANG_TO_CEID.get(language, "US:en")
    return [google_news_rss(query, lang_ceid=ceid), youtube_search_rss(query), arxiv_search_rss(query)]

def fetch_items_from_urls(urls: list, per_feed: int, recent_hours: int) -> list:
    """Fetch strictly within last N hours; dedup; newest first."""
    items = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=recent_hours)
    for url in urls:
        try:
            parsed = feedparser.parse(url)
            source_title = parsed.feed.get("title", url)
            for e in parsed.entries:
                ts = None
                if getattr(e, "published_parsed", None):
                    ts = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
                elif getattr(e, "updated_parsed", None):
                    ts = datetime(*e.updated_parsed[:6], tzinfo=timezone.utc)
                if not ts or ts < cutoff:
                    continue
                title = clean_text(getattr(e, "title", ""))
                summary = clean_text(getattr(e, "summary", "") or getattr(e, "description", ""))
                link = getattr(e, "link", "")
                items.append({
                    "title": title, "summary": summary, "link": link,
                    "published_dt": ts, "published": ts.isoformat(), "source": source_title,
                })
        except Exception:
            continue
    items.sort(key=lambda x: x["published_dt"], reverse=True)
    seen, unique = set(), []
    for it in items:
        k = it["title"].lower()
        if k not in seen:
            unique.append(it); seen.add(k)
    return unique[:per_feed]

def collect_items_for_queries(queries: list, language: str, per_feed: int, recent_hours: int, cap_per_query: int) -> dict:
    result = {}
    for q in queries:
        urls = build_urls_for_query(q, language)
        collected = fetch_items_from_urls(urls, per_feed=per_feed * len(urls), recent_hours=recent_hours)
        result[q] = collected[:cap_per_query]
    return result

def llm_summarize_and_script(topics_map: Dict[str, List[Dict]], language: str, total_minutes: int, tone: str) -> Dict:
    """Breaking‑news script; ONLY uses provided items."""
    target_words = minutes_to_words(total_minutes, WPM_DEFAULT)
    lower, upper = int(target_words*0.95), int(target_words*1.05)
    newsroom_rules = (
        "- Use only the provided items; no extra facts.\n"
        "- Focus on last 24–48h updates. Use time words (today/UTC).\n"
        "- Lead with who/what/where/when/how many. Use numbers and names.\n"
        "- Short sentences ≤ 18 words. No filler. Minimal transitions.\n"
        "- Attribute outlets briefly by name. No URLs.\n"
        "- End with one‑sentence wrap‑up."
    )
    sys = (f"You are Noah, a breaking‑news editor and narrator. "
           f"SPOKEN {language}. Total length {lower}–{upper} words. Tone: {tone}. "
           f"Be information‑dense and concise.\nRULES:\n{newsroom_rules}")
    ref_lines = []
    for query, items in topics_map.items():
        for it in items:
            ref_lines.append(f"[{query}] • {it['published']} • {it['source']} • {it['title']} • {it['summary'][:400]}")
    user = f"""Tasks:
1) Compact bullet list grouped by query (STRICTLY from these items).
2) Single narration in {language} of {lower}–{upper} words following the RULES.

ITEMS:
{os.linesep.join(ref_lines)}
"""
    resp = oai.chat.completions.create(
        model="gpt-4o-mini", temperature=0.2,
        messages=[{"role":"system","content":sys},{"role":"user","content":user}]
    )
    content = (resp.choices[0].message.content or "").strip()
    bullets_section, script_section, in_script = [], [], False
    for line in content.splitlines():
        if re.match(r"^\s*(Script|Narration)\b", line, re.I):
            in_script = True; continue
        (script_section if in_script else bullets_section).append(line)
    bullets_text = "\n".join(bullets_section).strip()
    script_text = "\n".join(script_section).strip() or content
    return {"bullets": bullets_text, "script": script_text, "target_words": target_words}

def tighten_to_word_target(script: str, target_words: int, language: str) -> str:
    """Refine to ±2–5% of target words, keep facts."""
    def within(text: str, pct: float) -> bool:
        return abs(count_words(text) - target_words) <= int(target_words * pct)
    for _ in range(2):
        if within(script, 0.05): break
        direction = "condense to" if count_words(script) > target_words else "expand to"
        prompt = (f"Rewrite the narration in {language} to {direction} ~{target_words} words (±2%). "
                  f"Short sentences ≤18 words. Keep facts and flow. No headings. Return only text.")
        r = oai.chat.completions.create(
            model="gpt-4o-mini", temperature=0.1,
            messages=[{"role":"system","content":"You are a precise editor."},
                      {"role":"user","content":prompt+"\n\n---\n"+script}]
        )
        script = (r.choices[0].message.content or "").strip()
    return script

def make_intro_outro(language: str) -> tuple[str,str]:
    prompt = (f"Write two very short spoken lines in {language} for a daily news podcast Noah by Zem Labs. "
              f"Line1: friendly 2–3s welcome (≤12 words). "
              f"Line2: friendly 2–3s goodbye for tomorrow (≤12 words). "
              f"Return JSON with 'intro' and 'outro'.")
    try:
        r = oai.chat.completions.create(
            model="gpt-4o-mini", temperature=0.3,
            messages=[{"role":"system","content":"You are a concise copywriter."},
                      {"role":"user","content":prompt}]
        )
        j = json.loads(r.choices[0].message.content)
        return (clean_text(j.get("intro") or "Welcome to your daily Noah by Zem Labs."),
                clean_text(j.get("outro") or "Thanks for listening — see you tomorrow."))
    except Exception:
        return ("Welcome to your daily Noah by Zem Labs.",
                "Thanks for listening — see you tomorrow.")

# ---------- ElevenLabs ----------
def elevenlabs_tts(text: str, voice_id: str, model_id: str = "eleven_multilingual_v2") -> AudioSegment:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {"text": text, "model_id": model_id, "voice_settings": {"stability":0.4,"similarity_boost":0.7}}
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "accept": "audio/mpeg", "content-type": "application/json"}
    r = requests.post(url, headers=headers, json=payload, timeout=180)
    r.raise_for_status()
    return AudioSegment.from_file(io.BytesIO(r.content), format="mp3")

def chunk_script_for_tts(text: str, max_chars: int = CHUNK_MAX_CHARS) -> List[str]:
    text = (text or "").strip()
    if len(text) <= max_chars: return [text]
    import re
    parts = re.split(r"(\n\n+|[.!?] )", text)
    chunks, buf = [], ""
    for p in parts:
        if len(buf) + len(p) < max_chars: buf += p
        else: chunks.append(buf.strip()); buf = p
    if buf.strip(): chunks.append(buf.strip())
    return chunks

# ---------- main orchestration ----------
def make_noah_audio(
    queries: List[str],
    language: str = "English",
    tone: str = "neutral and calm",
    recent_hours: int = 24,
    per_feed: int = 6,
    cap_per_query: int = 6,
    min_minutes: int = 8,
    voice_id: str = "",
) -> dict:
    if not voice_id:
        voice_id = DEFAULT_VOICE_ID or ""
    if not voice_id:
        raise RuntimeError("No ElevenLabs voice_id provided and ELEVENLABS_VOICE_ID env var is empty.")

    topic_items = collect_items_for_queries(queries, language, per_feed, recent_hours, cap_per_query)
    used_items = {q: list(v) for q, v in topic_items.items()}
    total_items = sum(len(v) for v in used_items.values())
    effective_minutes = max(min_minutes, math.ceil((total_items * WORDS_PER_ITEM) / WPM_DEFAULT))

    res = llm_summarize_and_script(used_items, language, effective_minutes, tone)
    script = tighten_to_word_target(res["script"], res["target_words"], language)
    intro, outro = make_intro_outro(language)

    silence_short = AudioSegment.silent(duration=INTRO_MS)
    silence_long  = AudioSegment.silent(duration=OUTRO_MS)

    intro_audio = elevenlabs_tts(intro, voice_id=voice_id)
    parts = [elevenlabs_tts(c, voice_id=voice_id) for c in chunk_script_for_tts(script)]
    if not parts:
        parts = [AudioSegment.silent(duration=300)]
    main_audio = sum(parts[1:], parts[0])
    outro_audio = elevenlabs_tts(outro, voice_id=voice_id)

    full = intro_audio + silence_short + main_audio + silence_long + outro_audio

    outdir = Path("out"); outdir.mkdir(exist_ok=True)
    fname = outdir / f"noah_{int(time.time())}.mp3"
    full.export(str(fname), format="mp3", bitrate="192k")

    return {
        "bullet_points": res["bullets"],
        "script": script,
        "sources": used_items,
        "minutes_target": effective_minutes,
        "duration_seconds": len(full)/1000.0,
        "file_path": str(fname),
        "file_name": fname.name,
    }

def health_check() -> bool:
    return bool(OPENAI_API_KEY and ELEVENLABS_API_KEY)