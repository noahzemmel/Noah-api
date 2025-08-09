#!/usr/bin/env python3
# Noah — Zem Labs
# Streamlit MVP • free‑text topics • multi‑source aggregation (Google News, YouTube, arXiv)
# strict recency window • breaking‑news tone • auto length from story volume
# exact sources shown • intro/outro • blue UI accents

import io
import os
import re
import math
import time
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from urllib.parse import quote_plus
from pathlib import Path

import streamlit as st
import feedparser
import requests
from pydub import AudioSegment
from slugify import slugify
from dotenv import load_dotenv, find_dotenv

# ======================= Constants =======================
WPM_DEFAULT = 170          # used only for word targeting (voice speed is unchanged)
WORDS_PER_ITEM = 90        # average words we assign per story to size the script
INTRO_MS = 350             # short pause after intro
OUTRO_MS = 650             # short pause before outro
CHUNK_MAX_CHARS = 2500     # TTS chunking limit

# ==================== Robust .env loading =================
env_path = find_dotenv(usecwd=True)
if not env_path:
    env_path = str((Path(__file__).parent / ".env").resolve())
load_dotenv(dotenv_path=env_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

# ---- OpenAI client (v1 SDK) ----
from openai import OpenAI
oai = OpenAI()  # reads OPENAI_API_KEY from environment

# =================== Streamlit app config =================
st.set_page_config(
    page_title="Zem Labs • Noah",
    page_icon="🎧",
    layout="wide",
    menu_items={
        "Get Help": "mailto:founder@zemlabs.co",
        "Report a bug": "mailto:founder@zemlabs.co",
        "About": "Noah — your focused daily audio briefing by Zem Labs."
    },
)
# Blue accents (no red)
st.markdown("""
<style>
:root { --primary-color:#2563eb; } /* Tailwind blue-600 */
.stButton>button{ background:#2563eb; border:0; }
.stButton>button:hover{ background:#1d4ed8; }
a, .st-emotion-cache-1aehpvj, .st-emotion-cache-1cypc5e { color:#2563eb; }
</style>
""", unsafe_allow_html=True)

# ===================== Header / Branding ==================
LOGO_PATH = os.path.join("assets", "logo.png")
left, mid, right = st.columns([1, 2, 2], vertical_alignment="center")
with left:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, use_column_width=True)
with mid:
    st.title("Noah — Daily Smart Bulletins")
    st.caption("Generated news & insights in your language, your voice, your time.")
with right:
    st.markdown(
        """
        <div style="text-align:right;font-size:13px;opacity:.7">
        Built by <b>Zem Labs</b>
        </div>
        """, unsafe_allow_html=True
    )

# ========================= Guards ========================
if not OPENAI_API_KEY or not ELEVENLABS_API_KEY:
    st.warning("Add your **OPENAI_API_KEY** and **ELEVENLABS_API_KEY** in a `.env` file (project root).")
    st.stop()

# ======================== Helpers ========================
def clean_text(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "")).strip()

def minutes_to_words(minutes: int, wpm: int = WPM_DEFAULT) -> int:
    return max(60, int(minutes * max(90, min(240, wpm))))

def count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))

# =========== Multi-source fetchers (no Reddit) ============
def google_news_rss(query: str, lang_ceid: str = "US:en") -> str:
    q = quote_plus(query)
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid={lang_ceid}"

def youtube_search_rss(query: str) -> str:
    q = quote_plus(query)
    return f"https://www.youtube.com/feeds/videos.xml?search_query={q}"

def arxiv_search_rss(query: str) -> str:
    q = quote_plus(query)
    return f"http://export.arxiv.org/api/query?search_query=all:{q}&sortBy=submittedDate&sortOrder=descending"

LANG_TO_CEID = {
    "English": "US:en",
    "Spanish": "ES:es",
    "French": "FR:fr",
    "German": "DE:de",
    "Italian": "IT:it",
    "Portuguese": "PT:pt",
    "Arabic": "AE:ar",
    "Hindi": "IN:hi",
    "Japanese": "JP:ja",
    "Korean": "KR:ko",
    "Chinese (Simplified)": "CN:zh-Hans",
}

def build_urls_for_query(query: str, language: str) -> list:
    ceid = LANG_TO_CEID.get(language, "US:en")
    return [
        google_news_rss(query, lang_ceid=ceid),
        youtube_search_rss(query),
        arxiv_search_rss(query),
    ]

def fetch_items_from_urls(urls: list, per_feed: int, recent_hours: int) -> list:
    """Fetch from multiple RSS/Atom feeds, **strictly** within last N hours."""
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
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "published_dt": ts,
                    "published": ts.isoformat(),
                    "source": source_title,
                })
        except Exception:
            continue

    # Dedup by title (keep newest), then trim
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

# ======= LLM summarization: breaking‑news & source‑strict =======
def llm_summarize_and_script(
    topics_map: Dict[str, List[Dict]],
    language: str,
    total_minutes: int,
    tone: str,
) -> Dict:
    """
    Uses ONLY the items in topics_map; writes a fresh, update‑driven script.
    """
    target_words = minutes_to_words(total_minutes, WPM_DEFAULT)
    lower = int(target_words * 0.95)
    upper = int(target_words * 1.05)

    sys = (
        f"You are Noah, a breaking‑news editor and audio scriptwriter. "
        f"Write a SPOKEN narration in {language}. "
        f"Keep TOTAL length between {lower} and {upper} words inclusive. "
        f"Tone: {tone}. Prioritize **what happened in the last 24–48 hours** only. "
        f"Do not provide background history unless essential to a new update. "
        f"Use ONLY the provided items as sources; do NOT invent other facts. "
        f"Attribute outlets briefly by name (e.g., '…according to the BBC'); no URLs. "
        f"Use crisp time cues ('today', 'this morning', 'on Friday (UTC)') when helpful. "
        f"Smooth, minimal transitions; end with a one‑sentence wrap‑up."
    )

    # Tight, machine‑readable reference: [Query] • [ISO time] • [Source] • [Title] • [Snippet]
    ref_lines = []
    for query, items in topics_map.items():
        for it in items:
            ref_lines.append(
                f"[{query}] • {it['published']} • {it['source']} • {it['title']} • {it['summary'][:400]}"
            )

    user = f"""Tasks:
1) Produce a compact bullet list grouped by query (strictly from these items).
2) Produce a single continuous narration in {language} with total length {lower}–{upper} words.

RULES:
- ONLY use the items below. No additional facts. Minimal background only if necessary.
- Emphasize the newest developments; avoid broad history.
- Attribute outlets sparingly by name only. No URLs.

ITEMS:
{os.linesep.join(ref_lines)}
"""

    resp = oai.chat_completions.create if hasattr(oai, "chat_completions") else oai.chat.completions.create
    out = resp(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
    )
    content = (out.choices[0].message.content or "").strip()

    # Try to split bullets + script if labeled
    bullets_section, script_section, in_script = [], [], False
    for line in content.splitlines():
        if re.match(r"^\s*(Script|Narration)\b", line, re.I):
            in_script = True
            continue
        (script_section if in_script else bullets_section).append(line)

    bullets_text = "\n".join(bullets_section).strip()
    script_text = "\n".join(script_section).strip() or content
    return {"bullets": bullets_text, "script": script_text, "target_words": target_words}

def tighten_to_word_target(script: str, target_words: int, language: str) -> str:
    """Refine to land within ±2–5% of target words."""
    def within(text: str, pct: float) -> bool:
        return abs(count_words(text) - target_words) <= int(target_words * pct)

    for _ in range(2):
        if within(script, 0.05):
            break
        direction = "condense to" if count_words(script) > target_words else "expand to"
        prompt = (
            f"Rewrite the following narration in {language} to {direction} ~{target_words} words "
            f"(strictly keep within ±2%). Keep the same facts and flow, spoken style, no headings or bullets. "
            f"Return only the narration text."
        )
        resp = oai.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": "You are a precise editor who matches target word counts."},
                {"role": "user", "content": prompt + "\n\n---\n" + script},
            ],
        )
        script = (resp.choices[0].message.content or "").strip()
    return script

# =================== Intro/Outro writer ===================
def make_intro_outro(language: str) -> tuple[str, str]:
    """Generate a short intro/outro in the selected language."""
    prompt = (
        f"Write two extremely short spoken lines in {language} for a daily news podcast called Noah by Zem Labs. "
        f"Line 1: a friendly 2–3 second welcome (≤12 words). "
        f"Line 2: a friendly 2–3 second goodbye encouraging listeners to return tomorrow (≤12 words). "
        f"Return as JSON with keys 'intro' and 'outro' only."
    )
    try:
        r = oai.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[
                {"role": "system", "content": "You are a concise copywriter."},
                {"role": "user", "content": prompt},
            ],
        )
        j = json.loads(r.choices[0].message.content)
        intro = clean_text(j.get("intro") or "Welcome to your daily Noah by Zem Labs.")
        outro = clean_text(j.get("outro") or "Thanks for listening — see you tomorrow.")
        return intro, outro
    except Exception:
        return ("Welcome to your daily Noah by Zem Labs.",
                "Thanks for listening — see you tomorrow.")

# ================== ElevenLabs helpers ====================
def elevenlabs_list_voices() -> List[Dict]:
    try:
        r = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": ELEVENLABS_API_KEY},
            timeout=30,
        )
        r.raise_for_status()
        return r.json().get("voices", [])
    except Exception:
        return []

def elevenlabs_tts(text: str, voice_id: str, model_id: str = "eleven_multilingual_v2") -> AudioSegment:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.7},
    }
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }
    r = requests.post(url, headers=headers, json=payload, timeout=180)
    r.raise_for_status()
    return AudioSegment.from_file(io.BytesIO(r.content), format="mp3")

def chunk_script_for_tts(text: str, max_chars: int = CHUNK_MAX_CHARS) -> List[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    parts = re.split(r"(\n\n+|[.!?] )", text)
    chunks, buf = [], ""
    for p in parts:
        if len(buf) + len(p) < max_chars:
            buf += p
        else:
            chunks.append(buf.strip()); buf = p
    if buf.strip():
        chunks.append(buf.strip())
    return chunks

def render_audio_download(audio: AudioSegment, title: str) -> None:
    buf = io.BytesIO()
    audio.export(buf, format="mp3", bitrate="192k")
    b = buf.getvalue()
    st.audio(b, format="audio/mp3")
    st.download_button("⬇️ Download MP3", data=b, file_name=f"{slugify(title)}.mp3", mime="audio/mpeg")

# ===================== Sidebar (controls) =================
st.sidebar.header("🎛️ Customize your briefing")

st.sidebar.markdown("### Topics / Queries")
topics_text = st.sidebar.text_area(
    "Type anything — one per line (e.g., 'semiconductor supply chain', 'Arsenal transfer rumors', 'longevity biotech').",
    height=150,
)

# Parse free-text topics
selected_topics = []
for line in (topics_text or "").splitlines():
    q = line.strip()
    if q and q not in selected_topics:
        selected_topics.append(q)
if not selected_topics:
    selected_topics = ["world news", "startup funding", "AI research"]

duration = st.sidebar.slider("Requested minimum length (minutes)", min_value=2, max_value=30, value=8, step=1)
language = st.sidebar.selectbox(
    "Language",
    ["English", "Spanish", "French", "German", "Italian", "Portuguese", "Arabic", "Hindi", "Japanese", "Korean", "Chinese (Simplified)"],
)
tone = st.sidebar.selectbox(
    "Tone",
    ["neutral and calm", "confident and crisp", "warm and friendly", "energetic and upbeat"],
)
recent_hours = st.sidebar.slider("How far back to look (hours)", 6, 48, 24, step=6)
per_feed = st.sidebar.slider("Max items per source", 3, 15, 6)
max_items_per_query = st.sidebar.slider("Max recent items per query", 3, 12, 6)

# Voices
voices = elevenlabs_list_voices()
voice_label_to_id = {f"{v.get('name','Unknown')}": v["voice_id"] for v in voices}
voice_labels = list(voice_label_to_id.keys())
if DEFAULT_VOICE_ID:
    for label, vid in list(voice_label_to_id.items()):
        if vid == DEFAULT_VOICE_ID and label in voice_labels:
            voice_labels.remove(label); voice_labels.insert(0, label); break
voice_choice = st.sidebar.selectbox(
    "Voice (from your ElevenLabs account)",
    options=voice_labels if voice_labels else ["(No voices found — check your API key)"],
    index=0 if voice_labels else None,
)
voice_id = voice_label_to_id.get(voice_choice, DEFAULT_VOICE_ID or "")

st.sidebar.caption("Noah focuses on fresh items in the last 24 hours by default. Accents are blue—because taste.")

# ======================= Main CTA ========================
st.markdown("### Today’s Briefing")
colA, colB = st.columns([2, 1])
with colB:
    st.info("Noah pulls **fresh** items from Google News, YouTube, and arXiv. "
            "Length grows with story volume; you set the minimum.")
with colA:
    generate = st.button("🚀 Generate today’s Noah", type="primary", use_container_width=True)

# ======================= Action ==========================
if generate:
    if not selected_topics:
        st.error("Type at least one topic/query."); st.stop()
    if not voice_id:
        st.error("No ElevenLabs voice ID selected/found."); st.stop()

    with st.spinner("Fetching sources across Google News, YouTube, and arXiv…"):
        topic_items = collect_items_for_queries(
            queries=selected_topics,
            language=language,
            per_feed=per_feed,
            recent_hours=recent_hours,
            cap_per_query=max_items_per_query,
        )
    st.success("Fetched fresh stories.")

    # Freeze EXACT items we will give to the model and display later
    used_items = {q: list(v) for q, v in topic_items.items()}

    # Auto-extend minutes based on story volume (never below requested)
    total_items = sum(len(v) for v in used_items.values())
    min_minutes_from_items = max(1, math.ceil((total_items * WORDS_PER_ITEM) / WPM_DEFAULT))
    effective_minutes = max(duration, min_minutes_from_items)

    with st.spinner("Synthesizing bullet points & breaking‑news script…"):
        result = llm_summarize_and_script(
            topics_map=used_items,
            language=language,
            total_minutes=effective_minutes,
            tone=tone,
        )
        bullets, script, target_words = result["bullets"], result["script"], result["target_words"]
        script = tighten_to_word_target(script, target_words, language)

    # Intro/Outro
    intro_text, outro_text = make_intro_outro(language)

    st.subheader("Bullets")
    st.markdown(bullets or "_(LLM returned no bullet section; showing full script below.)_")
    st.subheader("Narration Script")
    st.write(script)

    with st.spinner("Voicing with ElevenLabs…"):
        silence_short = AudioSegment.silent(duration=INTRO_MS)
        silence_long = AudioSegment.silent(duration=OUTRO_MS)

        # Intro
        intro_audio = elevenlabs_tts(intro_text, voice_id=voice_id)

        # Main narration
        main_parts = []
        for chunk in chunk_script_for_tts(script):
            main_parts.append(elevenlabs_tts(chunk, voice_id=voice_id))
            time.sleep(0.3)
        main_audio = sum(main_parts[1:], main_parts[0]) if main_parts else AudioSegment.silent(duration=500)

        # Outro
        outro_audio = elevenlabs_tts(outro_text, voice_id=voice_id)

        combined = intro_audio + silence_short + main_audio + silence_long + outro_audio

    st.success("Audio ready.")

    # --- Duration diagnostics
    actual_sec = len(combined) / 1000.0
    target_sec = effective_minutes * 60.0
    delta_sec = actual_sec - target_sec
    sign = "+" if delta_sec >= 0 else ""
    st.caption(
        f"Requested min {duration} min • auto‑target {effective_minutes} min for {total_items} fresh items "
        f"(~{WORDS_PER_ITEM} words/story @ ~{WPM_DEFAULT} wpm). "
        f"Actual MP3: {actual_sec/60:.1f} min ({sign}{delta_sec/60:.1f} min)."
    )

    st.subheader("🎧 Your Noah")
    title = f"Noah — {datetime.now().strftime('%Y-%m-%d')} — {', '.join(selected_topics)} — target {effective_minutes}min"
    render_audio_download(combined, title=title)

    with st.expander("Sources used (exact set passed to the model)"):
        for query, items in used_items.items():
            st.markdown(f"**{query}**")
            for it in items:
                st.markdown(f"- {it['title']} — {it['source']}  \n  {it['link']}  \n  _{it['published']}_")
else:
    st.markdown(
        """
        **How it works**
        1. Type any topics/queries (one per line).  
        2. Noah scans **fresh** sources (Google News, YouTube, arXiv) in the window you choose, merges duplicates, and drafts a *breaking‑news* narration with OpenAI.  
        3. Length scales automatically with story volume, book‑ended with a short intro/outro, and delivered as one MP3.  
        """
    )
    st.caption("Less doomscrolling. More signal. And yes, it’s all blue.")
