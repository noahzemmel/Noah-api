# app.py (Streamlit UI)
import os, time, requests, json, math
from typing import List, Dict
from pathlib import Path
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8080")
MAX_WAIT = int(os.getenv("NOAH_MAX_CLIENT_WAIT", "900"))  # seconds

st.set_page_config(
    page_title="Zem Labs • Noah",
    page_icon="🎧",
    layout="wide",
)

# ---------------- UI theming tweaks ----------------
st.markdown("""
<style>
/* Make labels visible/high-contrast */
.stSelectbox label, .stTextArea label, .stSlider label, .stCheckbox label {
  font-weight: 600 !important; color: #e9eef7 !important;
}
.block-container { padding-top: 1.2rem; }
</style>
""", unsafe_allow_html=True)

# ---------------- Helper calls ----------------
def api_get_voices() -> List[Dict]:
    try:
        r = requests.get(f"{API_BASE}/voices", timeout=30)
        r.raise_for_status()
        return r.json().get("voices", [])
    except Exception:
        return [{"provider":"openai","id":"alloy","name":"alloy"}]

def call_api_generate(payload: Dict) -> str:
    r = requests.post(f"{API_BASE}/generate", json=payload, timeout=600)
    r.raise_for_status()
    return r.json()["job_id"]

def poll_result(job_id: str, wait_s: int = MAX_WAIT) -> Dict:
    t0 = time.time()
    while True:
        r = requests.get(f"{API_BASE}/result/{job_id}", timeout=60)
        r.raise_for_status()
        data = r.json()
        if data.get("status") in ("done","error"):
            return data
        if time.time() - t0 > wait_s:
            return {"status":"timeout","job_id":job_id}
        time.sleep(2)

# Keep state so results don't disappear on rerun
if "last" not in st.session_state:
    st.session_state.last = None

# ---------------- Sidebar controls ----------------
with st.sidebar:
    st.header("Language")
    language = st.selectbox("Language", ["English","French","German","Spanish","Arabic"], index=0)

    st.header("Voice")
    voices = api_get_voices()
    voice_options = ["Use API default"] + [f"{v['name']} ({v['provider']})" for v in voices]
    voice_pick = st.selectbox("Voice", voice_options, index=0)
    chosen_voice_id = ""
    chosen_voice_provider = ""
    if voice_pick != "Use API default":
        vi = voices[voice_options.index(voice_pick)-1]
        # Only pass ElevenLabs voice_id to API; OpenAI voices selected via env on API
        if vi["provider"] == "elevenlabs":
            chosen_voice_id = vi["id"]
            chosen_voice_provider = "elevenlabs"

    st.header("Topics / queries (one per line)")
    topics = st.text_area("Topics", value="world news\nAI research", height=140)

    st.header("Exact length (minutes)")
    exact_minutes = st.slider("Exact minutes", min_value=2, max_value=30, value=8, step=1)

    st.header("Tone")
    tone = st.selectbox("Tone", ["confident and crisp", "warm and friendly", "neutral", "urgent"])

    st.header("How far back to look (hours)")
    lookback = st.slider("Lookback", min_value=6, max_value=72, value=24, step=6)

    st.header("Maximum stories per topic")
    cap_per = st.slider("Cap per topic", min_value=2, max_value=8, value=6, step=1)

    strict = st.checkbox("Strict timing (playback adjusted to exact length)", value=True)

    run = st.button("🚀 Generate Noah", use_container_width=True)

# ---------------- Main column ----------------
st.title("Noah — Daily Smart Bulletins")
st.caption("Generated news & insights in your language, your voice, your time.")
st.markdown(f"""
<span style="float:right; font-size: 12px; opacity:0.65;">API: <code>{API_BASE}</code></span>
""", unsafe_allow_html=True)
st.divider()

status = st.empty()
colL, colR = st.columns([1,1.2], gap="large")

def render_result(res: Dict):
    with colL:
        st.subheader("Bullet points")
        b = res["result"].get("bullets", [])
        if b:
            st.markdown("\n".join([f"- {x}" for x in b]))
        else:
            st.info("No bullets returned.")

        with st.expander("Sources used", expanded=True):
            srcs = res["result"].get("sources", [])
            if not srcs:
                st.write("No sources available.")
            else:
                by_topic: Dict[str, List[Dict]] = {}
                for s in srcs:
                    by_topic.setdefault(s.get("query","(topic)"), []).append(s)
                for t, arr in by_topic.items():
                    st.write(f"**{t}**")
                    for s in arr[:10]:
                        title = s.get("title","(title)")
                        link = s.get("link","#")
                        st.markdown(f"- {title} — [link]({link})")

    with colR:
        st.subheader("Your briefing")
        mp3_url = res["result"].get("mp3_url")
        if mp3_url:
            st.audio(f"{API_BASE}{mp3_url}", format="audio/mp3")
            meta = res["result"]
            st.caption(
                f"Target: {meta.get('target_minutes')} min • "
                f"Actual: {meta.get('actual_minutes')} min • "
                f"Playback: {meta.get('playback_rate')}x • "
                f"Voice: {meta.get('tts_provider')}"
            )
            st.download_button("Download MP3", data=requests.get(f"{API_BASE}{mp3_url}", timeout=60).content,
                               file_name="noah.mp3", mime="audio/mpeg")
        else:
            st.error("No audio produced.")

# ---------------- Action ----------------
if run:
    st.session_state.last = None
    payload = {
        "queries": topics,
        "language": language,
        "tone": tone,
        "recent_hours": int(lookback),
        "cap_per_query": int(cap_per),
        "min_minutes": float(exact_minutes),
        "exact_minutes": bool(strict),
    }
    if chosen_voice_id and chosen_voice_provider == "elevenlabs":
        payload["voice_id"] = chosen_voice_id

    with status.container():
        with st.status("Contacting Noah API…", expanded=True) as s:
            try:
                job_id = call_api_generate(payload)
                st.write(f"Started job: `{job_id}`")
                # poll
                res = poll_result(job_id)
                if res.get("status") == "done":
                    s.update(label="Done ✓", state="complete")
                    st.session_state.last = res
                elif res.get("status") == "timeout":
                    s.update(label="Timeout waiting for API result.", state="error")
                else:
                    s.update(label=f"Failed ✗\n\n{res.get('error','(no details)')}", state="error")
            except requests.HTTPError as e:
                s.update(label=f"API {e.response.status_code}: {e.response.text[:500]}", state="error")
            except Exception as e:
                s.update(label=f"Error: {e}", state="error")

# Persist last result on screen
if st.session_state.last:
    render_result(st.session_state.last)
else:
    with st.container():
        st.info("Enter topics on the left and click **Generate Noah** to try the beta.")
