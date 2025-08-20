# app.py — Streamlit UI (safe voice dropdown + polling)
import os, time, json, requests, streamlit as st

API_BASE = os.getenv("API_BASE", "https://thenoah.onrender.com").rstrip("/")

st.set_page_config(page_title="Noah — Daily Smart Bulletins", layout="wide")

st.title("Noah — Daily Smart Bulletins")
st.caption(f"Generated news & insights in **your language**, **your voice**, **your time**.\n\nAPI: {API_BASE}")

@st.cache_data(ttl=3600)
def fetch_voices():
    try:
        r = requests.get(f"{API_BASE}/voices", timeout=20)
        r.raise_for_status()
        data = r.json()
        voices = data.get("voices", [])
        if not voices:
            raise ValueError("empty voices")
        return voices
    except Exception:
        # Fallback; still works
        return [
            {"id": "", "name": "Use API default", "provider": "auto"},
            {"id": "alloy", "name": "Alloy", "provider": "openai"},
        ]

with st.sidebar:
    st.subheader("Language")
    language = st.selectbox("Language", ["English"], index=0)

    st.subheader("Voice")
    voices = fetch_voices()

    # Build options for selectbox and keep mapping to ids
    def label(v: dict) -> str:
        if not v.get("id"):
            return v.get("name", "Use API default")
        p = v.get("provider", "")
        return f"{v.get('name','Voice')}" + (f" ({p})" if p else "")

    selected_voice = st.selectbox(
        "Voice", options=voices, index=0,
        format_func=label,
    )
    voice_id = (selected_voice or {}).get("id", "")

    st.subheader("Topics / queries (one per line)")
    topics = st.text_area("Topics", value="world news\nAI research", height=140, label_visibility="collapsed")

    st.subheader("Exact length (minutes)")
    minutes = st.slider("Exact minutes", 2, 30, 8)

    st.subheader("Tone")
    tone = st.selectbox("Tone", ["confident and crisp", "warm and friendly", "neutral"], index=0)

    st.subheader("How far back to look (hours)")
    lookback = st.slider("Lookback", 6, 72, 24)

    st.subheader("Maximum stories per topic")
    cap = st.slider("Cap per topic", 2, 8, 6)

    strict = st.toggle("Strict timing (playback adjusted to exact length)", value=False)

    run = st.button("🚀 Generate Noah", use_container_width=True)

status = st.empty()
col1, col2, col3 = st.columns([1,1,1])

def call_api(payload: dict):
    r = requests.post(f"{API_BASE}/generate", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

def poll(job_id: str, max_wait=900, delay=2.5):
    t0 = time.time()
    while True:
        r = requests.get(f"{API_BASE}/result/{job_id}", timeout=30)
        if r.status_code == 404:
            return {"status": "error", "error": "job not found"}
        data = r.json()
        s = data.get("status")
        logs = "\n".join(data.get("logs", []))
        status.markdown(f"**Contacting Noah API…**\n\n**Started job:** `{job_id}`\n\n```\n{logs}\n```")
        if s in ("done", "error"):
            return data
        if time.time() - t0 > max_wait:
            return {"status": "error", "error": "Timeout waiting for API result.", "logs": data.get("logs", [])}
        time.sleep(delay)

if run:
    payload = {
        "queries": topics,
        "language": language,
        "tone": tone,
        "recent_hours": lookback,
        "cap_per_query": cap,
        "min_minutes": minutes,
        "exact_minutes": True,
        "voice_id": voice_id or None,
    }
    try:
        status.info("Submitting job…")
        start = call_api(payload)
        job_id = start.get("job_id")
        if not job_id:
            status.error(f"API error: {start}")
        else:
            data = poll(job_id)
            if data.get("status") == "done" and data.get("result"):
                res = data["result"]
                with col1:
                    st.subheader("Bullet points")
                    st.write("\n".join(f"- {b}" for b in res.get("bullets", [])) or "_none_")
                with col2:
                    st.subheader("Your briefing")
                    st.caption(f"Target: {res.get('target_minutes')} min • Actual: {res.get('actual_minutes')} min • Playback rate: {res.get('playback_rate')}")
                    mp3 = res.get("mp3_url")
                    if mp3:
                        st.audio(mp3, format="audio/mp3")
                        st.download_button("⬇ Download MP3", data=requests.get(mp3, timeout=60).content, file_name=res.get("mp3_name","noah.mp3"))
                    else:
                        st.warning("No audio returned.")
                with col3:
                    st.subheader("Sources used")
                    srcs = res.get("sources", [])
                    if not srcs:
                        st.write("_none_")
                    else:
                        for s in srcs:
                            title = s.get("title") or s.get("url","")
                            u = s.get("url","")
                            st.markdown(f"- **{title}**<br/>[{u}]({u})", unsafe_allow_html=True)
                status.success("Done ✓")
            else:
                status.error(f"API error: {data.get('error','Unknown error')}")
    except requests.HTTPError as e:
        status.error(f"API {e.response.status_code}: {e.response.text[:400]}")
    except Exception as e:
        status.error(f"Client error: {e}")
