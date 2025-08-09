# app.py — Noah UI (Streamlit) that calls the Render API
# --------------------------------------------------------------------------------------
# This page collects the user's preferences, calls your FastAPI service (/generate),
# and displays bullet points, the narration script, sources, and a playable MP3.
# It requires ONE env var in this Streamlit service:
#   API_BASE = https://thenoah.onrender.com            # <-- set this on Render (Environment tab)
#
# Keep your OpenAI/ElevenLabs keys ONLY on the API service. Do NOT store keys here.
# --------------------------------------------------------------------------------------

import os
import json
import time
from typing import List, Dict, Any

import requests
import streamlit as st

# --------------------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------------------
API_BASE = os.getenv("API_BASE", "").rstrip("/")  # set on Render → Environment
APP_TITLE = "Noah — Daily Smart Bulletins"
ACCENT = "#2563EB"  # blue
BG_DARK = "#0b1220"
CARD_DARK = "#0f172a"
BORDER = "#1f2a44"

st.set_page_config(page_title="Noah • Zem Labs", page_icon="🎧", layout="wide")

# Minimal dark theme via inline CSS (keeps Carrd/brand feel)
st.markdown(
    f"""
    <style>
      .stApp {{ background:{BG_DARK}; color:#e5e7eb; }}
      .stButton>button {{ background:{ACCENT}; color:white; border:0; border-radius:10px; padding:8px 14px; font-weight:600; }}
      .block-container {{ padding-top: 1.5rem; }}
      div[data-baseweb="select"] > div {{ background:{CARD_DARK}; }}
      textarea, .stTextArea textarea {{ background:{CARD_DARK}; color:#e5e7eb; border:1px solid {BORDER}; border-radius:10px; }}
      .stSlider > div > div > div > div {{ background:{ACCENT}; }}
      .stNotification-content, .stAlert {{ background:{CARD_DARK}; border:1px solid {BORDER}; }}
      .stExpander {{ border:1px solid {BORDER}; border-radius:10px; overflow:hidden; }}
      .stExpander summary {{ background:{CARD_DARK}; }}
      audio {{ width:100%; border-radius:10px; }}
      .smallcap {{ opacity:.75; font-size:12px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def _api_base_ok() -> bool:
    return API_BASE.startswith("https://") or API_BASE.startswith("http://")

def parse_topics(raw: str) -> List[str]:
    # split by line and commas; strip empties; dedupe preserving order
    items = []
    for chunk in raw.replace(",", "\n").split("\n"):
        s = chunk.strip()
        if s and s.lower() not in [x.lower() for x in items]:
            items.append(s)
    return items

def call_noah_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    POSTs to {API_BASE}/generate and returns JSON.
    Raises a clear error if the API returns an error.
    """
    if not _api_base_ok():
        raise RuntimeError("API_BASE is not set. In Render → Environment, add API_BASE=https://thenoah.onrender.com")

    url = f"{API_BASE}/generate"
    r = requests.post(url, json=payload, timeout=600)
    # This raises for non-2xx (e.g., 500)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(data["error"])
    return data

def fmt_minutes(seconds: float) -> str:
    m = max(0.0, float(seconds) / 60.0)
    return f"{m:.1f} min"

# --------------------------------------------------------------------------------------
# UI — Header
# --------------------------------------------------------------------------------------
left_head, right_head = st.columns([0.7, 0.3])
with left_head:
    st.title(APP_TITLE)
    st.caption("Generated news & insights in your language, your voice, your time.")

with right_head:
    st.markdown(
        f"""
        <div style="text-align:right">
          <span class="smallcap">Built by <b>Zem Labs</b></span><br/>
          <span class="smallcap">API: <code>{API_BASE or "NOT SET"}</code></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------------------
# UI — Sidebar controls
# --------------------------------------------------------------------------------------
with st.sidebar:
    st.header("Customize your briefing")
    topics_raw = st.text_area(
        "Topics / queries (one per line)",
        height=140,
        value="world news\nAI research",
        help="Type anything — one per line (e.g., 'semiconductor supply chain', 'Arsenal transfer rumors').",
    )

    min_minutes = st.slider("Requested minimum length (minutes)", 2, 30, 8)
    language = st.selectbox(
        "Language",
        [
            "English","Spanish","French","German","Italian","Portuguese",
            "Arabic","Hindi","Japanese","Korean","Chinese (Simplified)"
        ],
        index=0,
    )
    tone = st.selectbox(
        "Tone",
        ["neutral and calm","confident and crisp","warm and friendly","energetic and upbeat"],
        index=1,
    )
    lookback_hours = st.select_slider(
        "How far back to look (hours)",
        options=[6,12,24,36,48,72],
        value=24,
    )
    cap_per_query = st.slider("Maximum stories per topic", 2, 8, 6, help="Controls density & runtime.")
    per_feed = 6  # keep aligned with the API’s recommendation

    go = st.button("🚀 Generate Noah", use_container_width=True)

# --------------------------------------------------------------------------------------
# Main — results area
# --------------------------------------------------------------------------------------
left, right = st.columns([0.5, 0.5])

if go:
    queries = parse_topics(topics_raw)
    if not queries:
        st.error("Please add at least one topic.")
        st.stop()

    # Build request to API
    payload = {
        "queries": queries,
        "language": language,
        "tone": tone,
        "recent_hours": int(lookback_hours),
        "per_feed": int(per_feed),
        "cap_per_query": int(cap_per_query),
        "min_minutes": int(min_minutes),
        # NOTE: omit voice_id here if your API service has ELEVENLABS_VOICE_ID set.
        # "voice_id": "YOUR_OPTIONAL_SPECIFIC_VOICE_ID",
    }

    with st.status("Generating your Noah… this can take 30–60 seconds", expanded=True) as s:
        try:
            s.write("Contacting Noah API…")
            t0 = time.time()
            data = call_noah_api(payload)
            dt = time.time() - t0
            s.write(f"Received response in {dt:.1f}s.")
            s.update(label="Done ✓", state="complete")
        except requests.HTTPError as http_err:
            st.error(f"API HTTP error: {http_err.response.status_code} — {http_err.response.text}")
            st.stop()
        except Exception as e:
            st.error(f"API error: {e}")
            st.stop()

    # Render results
    with left:
        st.subheader("Bullet points")
        st.write(data.get("bullet_points") or "_(none)_")

        st.subheader("Narration script")
        st.write(data.get("script") or "_(none)_")

    with right:
        st.subheader("Your briefing")
        mp3_url = data.get("mp3_url")
        if mp3_url:
            # If API returned a relative path, prepend the base
            if not mp3_url.startswith("http"):
                mp3_url = f"{API_BASE}{mp3_url}"
            st.audio(mp3_url)
            st.caption(
                f"Target: {data.get('minutes_target','?')} min • "
                f"Actual: {fmt_minutes(data.get('duration_seconds', 0))}"
            )
        else:
            st.info("No audio returned.")

        with st.expander("Sources used", expanded=False):
            sources = data.get("sources") or {}
            if not sources:
                st.caption("No sources returned.")
            else:
                for q, items in sources.items():
                    st.markdown(f"**{q}**")
                    for it in items or []:
                        title = it.get("title", "(untitled)")
                        src = it.get("source", "")
                        link = it.get("link", "")
                        st.markdown(f"- {title} — {src} — [link]({link})")

else:
    st.info("Enter topics on the left and click **Generate Noah** to try the beta.")
