# app.py — Noah UI (Streamlit) that calls the Render API
# Polished contrast + exact-timing playback
# --------------------------------------------------------------------------------------
import os
import time
from typing import List, Dict, Any

import requests
import streamlit as st

# ---------- Config ----------
API_BASE = os.getenv("API_BASE", "").rstrip("/")   # Set in Render → Environment
APP_TITLE = "Noah — Daily Smart Bulletins"

# Brand colors (high contrast)
ACCENT = "#2563EB"      # blue
FG = "#E8EDF7"          # light text
FG_MUTED = "#C7D2FE"
BG = "#0B1220"          # deep navy
CARD = "#0F172A"        # slate
BORDER = "#1F2A44"

st.set_page_config(page_title="Noah • Zem Labs", page_icon="🎧", layout="wide")

# ---------- Styling (high contrast, clear labels) ----------
st.markdown(
    f"""
    <style>
      .stApp {{
        background:{BG};
        color:{FG};
      }}
      .block-container {{
        padding-top: 1.2rem;
      }}
      h1, h2, h3, h4, h5, h6 {{
        color:{FG};
        letter-spacing:.2px;
      }}
      .zem-card {{
        background:{CARD};
        border:1px solid {BORDER};
        border-radius:12px;
        padding:14px;
      }}
      .zem-label {{
        font-weight:700;
        font-size:0.95rem;
        color:{FG};
        margin-bottom:6px;
        display:block;
      }}
      textarea, .stTextArea textarea, input, select, .stSelectbox [data-baseweb="select"] > div {{
        background:{CARD} !important;
        color:{FG} !important;
        border:1px solid {BORDER} !important;
        border-radius:10px !important;
      }}
      .stSlider > div > div > div > div {{ background:{ACCENT}; }}
      .stButton>button {{
        background:{ACCENT};
        color:white;
        border:0;
        border-radius:10px;
        padding:10px 14px;
        font-weight:700;
      }}
      .smallcap {{ opacity:.85; font-size:12px; }}
      audio {{ width:100%; border-radius:10px; }}
      details {{ border:1px solid {BORDER}; border-radius:10px; overflow:hidden; }}
      details > summary {{ cursor:pointer; background:{CARD}; padding:8px 12px; }}
      details > div {{ padding:10px 12px; }}
      /* make select chevrons visible on dark */
      .css-1xc3v61-indicatorContainer, .css-15lsz6c-indicatorContainer {{ color:{FG_MUTED}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Helpers ----------
def parse_topics(raw: str) -> List[str]:
    items, seen = [], set()
    for chunk in raw.replace(",", "\n").split("\n"):
        s = chunk.strip()
        key = s.lower()
        if s and key not in seen:
            items.append(s); seen.add(key)
    return items

def call_noah_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not (API_BASE.startswith("https://") or API_BASE.startswith("http://")):
        raise RuntimeError("API_BASE not set. In Render → Environment, add API_BASE=https://thenoah.onrender.com")
    r = requests.post(f"{API_BASE}/generate", json=payload, timeout=600)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(data["error"])
    return data

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def render_audio_with_target(mp3_url: str, actual_seconds: float, target_minutes: int, strict: bool) -> None:
    """
    Render an <audio> element and, if strict mode is on, apply a subtle playbackRate
    to hit the requested duration exactly. We clamp between 0.85–1.25 so it still sounds natural.
    """
    if not mp3_url:
        st.info("No audio returned.")
        return

    if not mp3_url.startswith("http"):
        mp3_url = f"{API_BASE}{mp3_url}"

    target_seconds = max(1, int(target_minutes * 60))
    rate = 1.0
    note = ""

    if strict and actual_seconds and actual_seconds > 0:
        # rate > 1.0 = a bit faster; < 1.0 = a bit slower
        desired_rate = actual_seconds / target_seconds
        rate = clamp(desired_rate, 0.85, 1.25)

        # If we had to clamp, mention we couldn't match perfectly
        if abs(rate - desired_rate) > 0.02:
            note = " (adjusted to the limit; could not match perfectly)"
        else:
            note = " (adjusted to match exactly)"

    # Custom audio with JS to set playbackRate (Streamlit's st.audio has no speed control)
    st.markdown(
        f"""
        <div class="zem-card">
          <audio id="noah-audio" controls src="{mp3_url}"></audio>
          <div class="smallcap">Target: {target_minutes} min • Actual: {actual_seconds/60:.1f} min • Playback rate: {rate:.2f}{note}</div>
        </div>
        <script>
          const a = document.getElementById('noah-audio');
          if (a) {{
            // Wait until metadata loads to ensure duration is known, then set rate
            a.addEventListener('loadedmetadata', () => {{
              try {{ a.playbackRate = {rate:.4f}; }} catch (e) {{}}
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
          <div class="smallcap">API base</div>
          <code style="font-size:12px">{API_BASE or "NOT SET"}</code>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------- Sidebar (clear language & voice first) ----------
with st.sidebar:
    st.markdown("<div class='zem-label'>Language</div>", unsafe_allow_html=True)
    language = st.selectbox(
        label=" ",
        label_visibility="collapsed",
        options=[
            "English","Spanish","French","German","Italian","Portuguese",
            "Arabic","Hindi","Japanese","Korean","Chinese (Simplified)"
        ],
        index=0,
        help="Choose the narration language."
    )

    st.markdown("<div class='zem-label' style='margin-top:8px'>Voice (optional)</div>", unsafe_allow_html=True)
    voice_id = st.text_input(
        label=" ",
        label_visibility="collapsed",
        placeholder="ElevenLabs voice_id (leave blank to use the API default)",
        help="Paste an ElevenLabs voice_id to override the API's default voice. Leave blank to use the default."
    )

    st.markdown("<div class='zem-label' style='margin-top:12px'>Topics / queries (one per line)</div>", unsafe_allow_html=True)
    topics_raw = st.text_area(
        label=" ",
        label_visibility="collapsed",
        height=140,
        value="world news\nAI research",
        help="Type anything — one per line, e.g., 'semiconductor supply chain', 'Arsenal transfer rumors'.",
    )

    st.markdown("<div class='zem-label' style='margin-top:10px'>Exact length (minutes)</div>", unsafe_allow_html=True)
    target_minutes = st.slider(label=" ", label_visibility="collapsed", min_value=2, max_value=30, value=8)

    st.markdown("<div class='zem-label' style='margin-top:10px'>Tone</div>", unsafe_allow_html=True)
    tone = st.selectbox(
        label="  ",
        label_visibility="collapsed",
        options=["neutral and calm","confident and crisp","warm and friendly","energetic and upbeat"],
        index=1,
    )

    st.markdown("<div class='zem-label' style='margin-top:10px'>How far back to look (hours)</div>", unsafe_allow_html=True)
    lookback_hours = st.select_slider(label="   ", label_visibility="collapsed", options=[6,12,24,36,48,72], value=24)

    st.markdown("<div class='zem-label' style='margin-top:10px'>Maximum stories per topic</div>", unsafe_allow_html=True)
    cap_per_query = st.slider(label="    ", label_visibility="collapsed", min_value=2, max_value=8, value=6, help="Controls density & runtime.")

    strict_timing = st.toggle("Strict timing (adjust playback speed slightly to hit the exact length)", value=True)

    go = st.button("🚀 Generate Noah", use_container_width=True)

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
        # New hints for the API:
        "min_minutes": int(target_minutes),      # backward compatible
        "minutes_target": int(target_minutes),   # explicit target
        "exact_minutes": True                    # ask API to aim precisely if you add support
    }
    if voice_id.strip():
        payload["voice_id"] = voice_id.strip()

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
        render_audio_with_target(
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
            expander_html = ["<details><summary>Show sources</summary><div>"]
            for q, items in src.items():
                expander_html.append(f"<div style='margin:6px 0'><b>{q}</b></div>")
                for it in items or []:
                    title = it.get("title", "(untitled)")
                    srcname = it.get("source", "")
                    link = it.get("link", "#")
                    expander_html.append(f"<div style='margin-left:10px'>• {title} — {srcname} — <a href='{link}' target='_blank' rel='noopener'>link</a></div>")
            expander_html.append("</div></details>")
            st.markdown("".join(expander_html), unsafe_allow_html=True)

else:
    st.info("Enter topics on the left and click **Generate Noah** to try the beta.")
