# app.py — Noah UI (Streamlit) that calls the Render API
# High-contrast UI + consistent controls + exact-timing playback + ElevenLabs voice picker
# --------------------------------------------------------------------------------------
import os
import time
from typing import List, Dict, Any, Optional

import requests
import streamlit as st

# ---------- Config ----------
API_BASE = os.getenv("API_BASE", "").rstrip("/")   # Set in Render → Environment
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")  # Optional: for voice dropdown
APP_TITLE = "Noah — Daily Smart Bulletins"

# Brand colors (high contrast)
ACCENT = "#2563EB"      # blue
FG = "#E8EDF7"          # light text
FG_MUTED = "#C7D2FE"
BG = "#0B1220"          # deep navy
CARD = "#0F172A"        # slate
BORDER = "#1F2A44"

st.set_page_config(page_title="Noah • Zem Labs", page_icon="🎧", layout="wide")

# ---------- Styling (all inputs consistent + readable) ----------
st.markdown(
    f"""
    <style>
      .stApp {{ background:{BG}; color:{FG}; }}
      .block-container {{ padding-top: 1.2rem; }}
      h1, h2, h3, h4, h5, h6 {{ color:{FG}; letter-spacing:.2px; }}
      .zem-card {{ background:{CARD}; border:1px solid {BORDER}; border-radius:12px; padding:14px; }}
      .zem-label {{ font-weight:700; font-size:0.95rem; color:{FG}; margin:10px 0 6px; display:block; }}
      textarea, .stTextArea textarea, input, select {{ background:{CARD} !important; color:{FG} !important;
        border:1px solid {BORDER} !important; border-radius:10px !important; }}
      .stSelectbox [data-baseweb="select"] > div {{ background:{CARD} !important; color:{FG} !important;
        border:1px solid {BORDER} !important; border-radius:10px !important; }}
      .stSlider > div > div > div > div {{ background:{ACCENT}; }}
      .stButton>button {{ background:{ACCENT}; color:white; border:0; border-radius:10px; padding:10px 14px; font-weight:700; }}
      .smallcap {{ opacity:.9; font-size:12px; }}
      audio {{ width:100%; border-radius:10px; }}
      details {{ border:1px solid {BORDER}; border-radius:10px; overflow:hidden; }}
      details > summary {{ cursor:pointer; background:{CARD}; padding:8px 12px; }}
      details > div {{ padding:10px 12px; }}
      ::placeholder {{ color:{FG_MUTED}; opacity:0.95; }}
      /* ensure select chevrons visible */
      .css-1xc3v61-indicatorContainer, .css-15lsz6c-indicatorContainer {{ color:{FG_MUTED}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Helpers ----------
def _api_ok() -> bool:
    return API_BASE.startswith("http")

def parse_topics(raw: str) -> List[str]:
    items, seen = [], set()
    for chunk in raw.replace(",", "\n").split("\n"):
        s = chunk.strip()
        k = s.lower()
        if s and k not in seen:
            items.append(s); seen.add(k)
    return items

def call_noah_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not _api_ok():
        raise RuntimeError("API_BASE not set. In Render → Environment, add API_BASE=https://thenoah.onrender.com")
    r = requests.post(f"{API_BASE}/generate", json=payload, timeout=600)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(data["error"])
    return data

def get_eleven_voices() -> List[Dict[str,str]]:
    """
    Prefer fetching from ElevenLabs if ELEVENLABS_API_KEY exists on Streamlit.
    Falls back to trying API_BASE/voices (if you later add that), otherwise returns default option.
    """
    # 1) Direct ElevenLabs (server-side call; key never leaves server)
    if ELEVEN_API_KEY:
        try:
            res = requests.get(
                "https://api.elevenlabs.io/v1/voices",
                headers={"xi-api-key": ELEVEN_API_KEY},
                timeout=20,
            )
            if res.status_code == 200:
                j = res.json()
                voices = [{"name": v.get("name", "Unnamed"), "id": v.get("voice_id", "")} for v in j.get("voices", [])]
                voices.sort(key=lambda x: x["name"].lower())
                return [{"name": "Use API default", "id": ""}] + voices
        except Exception:
            pass
    # 2) Optional proxy via API (if you add later)
    if _api_ok():
        try:
            res = requests.get(f"{API_BASE}/voices", timeout=15)
            if res.status_code == 200:
                voices = res.json() or []
                if isinstance(voices, list):
                    return [{"name": "Use API default", "id": ""}] + voices
        except Exception:
            pass
    # 3) Fallback
    return [{"name": "Use API default", "id": ""}]

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def render_audio_exact(mp3_url: str, actual_seconds: float, target_minutes: int, strict: bool) -> None:
    """
    Render audio and, if strict, set playbackRate so the *heard* duration equals the exact target.
    We allow a wider but still natural range client-side: 0.60–1.35.
    """
    if not mp3_url:
        st.info("No audio returned."); return
    if not mp3_url.startswith("http"):
        mp3_url = f"{API_BASE}{mp3_url}"

    target_seconds = max(1, int(target_minutes * 60))
    rate = 1.0
    note = ""

    if strict and actual_seconds and actual_seconds > 0:
        desired_rate = actual_seconds / float(target_seconds)  # <1 slows down (longer), >1 speeds up
        rate = clamp(desired_rate, 0.60, 1.35)
        if abs(rate - desired_rate) > 0.02:
            note = " (adjusted to the limit; large mismatch from source)"
        else:
            note = " (matched requested length)"

    st.markdown(
        f"""
        <div class="zem-card">
          <audio id="noah-audio" controls src="{mp3_url}"></audio>
          <div class="smallcap">Target: {target_minutes} min • Actual audio: {actual_seconds/60:.1f} min • Playback rate: {rate:.2f}{note}</div>
        </div>
        <script>
          const a = document.getElementById('noah-audio');
          if (a) {{
            a.addEventListener('loadedmetadata', () => {{
              try {{ a.playbackRate = {rate:.4f}; }} catch (e) {{ }}
            }});
          }}
        </script>
        """,
        unsafe_allow_html=True,
    )

# ---------- Header ----------
c1, c2 = st.columns([0.72, 0.28])
with c1:
    st.markdown(f"<h1 style='margin-bottom:0.2rem'>{APP_TITLE}</h1>", unsafe_allow_html=True)
    st.caption("Generated news & insights in **your language**, **your voice**, **your time**.")
with c2:
    st.markdown(
        f"""
        <div class="zem-card" style="text-align:right">
          <div class="smallcap">API</div>
          <code style="font-size:12px">{API_BASE or "NOT SET"}</code>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------- Sidebar (uniform controls) ----------
with st.sidebar:
    st.markdown("<div class='zem-label'>Language</div>", unsafe_allow_html=True)
    language = st.selectbox(
        label="Language",
        options=[
            "English","Spanish","French","German","Italian","Portuguese",
            "Arabic","Hindi","Japanese","Korean","Chinese (Simplified)"
        ],
        index=0,
        key="lang_box",
    )

    st.markdown("<div class='zem-label'>Voice</div>", unsafe_allow_html=True)
    voices = get_eleven_voices()
    voice_names = [v["name"] for v in voices]
    voice_choice = st.selectbox("Voice", options=voice_names, index=0, key="voice_box")
    voice_id = next((v["id"] for v in voices if v["name"] == voice_choice), "")

    st.markdown("<div class='zem-label'>Topics / queries (one per line)</div>", unsafe_allow_html=True)
    topics_raw = st.text_area(
        label="Topics",
        height=140,
        value="world news\nAI research",
        key="topics_box",
        help="Type anything — one per line, e.g., 'semiconductor supply chain', 'Arsenal transfer rumors'.",
    )

    st.markdown("<div class='zem-label'>Exact length (minutes)</div>", unsafe_allow_html=True)
    target_minutes = st.slider("Exact minutes", min_value=2, max_value=30, value=8, key="minutes_box")

    st.markdown("<div class='zem-label'>Tone</div>", unsafe_allow_html=True)
    tone = st.selectbox(
        "Tone",
        ["neutral and calm","confident and crisp","warm and friendly","energetic and upbeat"],
        index=1,
        key="tone_box",
    )

    st.markdown("<div class='zem-label'>How far back to look (hours)</div>", unsafe_allow_html=True)
    lookback_hours = st.select_slider("Lookback (hours)", options=[6,12,24,36,48,72], value=24, key="lookback_box")

    st.markdown("<div class='zem-label'>Maximum stories per topic</div>", unsafe_allow_html=True)
    cap_per_query = st.slider("Cap per topic", min_value=2, max_value=8, value=6, key="cap_box")

    strict_timing = st.toggle("Strict timing (playback adjusted to hit the exact length)", value=True, key="strict_toggle")

    go = st.button("🚀 Generate Noah", use_container_width=True, key="go_button")

# ---------- Results ----------
left, right = st.columns([0.5, 0.5])

if go:
    queries = parse_topics(topics_raw)
    if not queries:
        st.error("Please add at least one topic.")
        st.stop()

    payload = {
        "queries": queries,
        "language": language,
        "tone": tone,
        "recent_hours": int(lookback_hours),
        "per_feed": 6,
        "cap_per_query": int(cap_per_query),
        # Tell the API to aim exactly here; your API already supports exact_minutes + minutes_target
        "min_minutes": int(target_minutes),
        "minutes_target": int(target_minutes),
        "exact_minutes": True
    }
    if voice_id:  # "" means "Use API default"
        payload["voice_id"] = voice_id

    with st.status("Generating your Noah… this can take 30–60 seconds", expanded=True) as s:
        try:
            s.write("Contacting Noah API…")
            t0 = time.time()
            data = call_noah_api(payload)
            s.write(f"Received response in {time.time()-t0:.1f}s.")
            s.update(label="Done ✓", state="complete")
        except requests.HTTPError as http_err:
            st.error(f"API HTTP error: {http_err.response.status_code} — {http_err.response.text}")
            st.stop()
        except Exception as e:
            st.error(f"API error: {e}")
            st.stop()

    # Render content
    with left:
        st.markdown("<h3>Bullet points</h3>", unsafe_allow_html=True)
        st.markdown(f"<div class='zem-card'>{(data.get('bullet_points') or '').replace(chr(10), '<br/>')}</div>", unsafe_allow_html=True)

        st.markdown("<h3 style='margin-top:16px'>Narration script</h3>", unsafe_allow_html=True)
        st.markdown(f"<div class='zem-card' style='white-space:pre-wrap'>{data.get('script') or ''}</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<h3>Your briefing</h3>", unsafe_allow_html=True)
        actual_seconds = float(data.get("duration_seconds") or 0)
        render_audio_exact(
            mp3_url=data.get("mp3_url", ""),
            actual_seconds=actual_seconds,
            target_minutes=target_minutes,
            strict=strict_timing,
        )

        # Sources
        st.markdown("<h4 style='margin-top:16px'>Sources used</h4>", unsafe_allow_html=True)
        src = data.get("sources") or {}
        if not src:
            st.caption("No sources returned.")
        else:
            html = ["<details><summary>Show sources</summary><div>"]
            for q, items in src.items():
                html.append(f"<div style='margin:6px 0'><b>{q}</b></div>")
                for it in items or []:
                    title = it.get("title", "(untitled)")
                    srcname = it.get("source", "")
                    link = it.get("link", "#")
                    html.append(f"<div style='margin-left:10px'>• {title} — {srcname} — <a href='{link}' target='_blank' rel='noopener'>link</a></div>")
            html.append("</div></details>")
            st.markdown("".join(html), unsafe_allow_html=True)

else:
    st.info("Enter topics on the left and click **Generate Noah** to try the beta.")
