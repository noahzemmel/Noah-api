# app.py — Streamlit UI (polling + live progress + show TTS provider)
import os, time, requests, streamlit as st

API_BASE = os.getenv("API_BASE", "https://thenoah.onrender.com")
MAX_WAIT_SECONDS = int(os.getenv("NOAH_MAX_CLIENT_WAIT", "900"))  # 15 minutes

st.set_page_config(page_title="Noah — Daily Smart Bulletins", page_icon="🗞️", layout="wide")

st.markdown("""
<style>
:root { --ink:#E8EDF7; --muted:#9AA6B2; --panel:#0F172A; --border:#1F2A44; }
.small-muted {color:var(--muted);font-size:0.85rem;}
.card {background:var(--panel);border-radius:14px;padding:18px;border:1px solid var(--border);}
h1,h2,h3 {color:var(--ink)}
.stAudio { margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Language")
    lang = st.selectbox("Language", ["English"], index=0)

    st.header("Voice")
    voice_opts = ["Use API default"]
    try:
        r = requests.get(f"{API_BASE}/voices", timeout=10)
        if r.ok:
            for v in r.json():
                voice_opts.append(f"{v['name']} — {v['id']}")
    except Exception:
        pass
    sel_voice = st.selectbox("Voice", voice_opts, index=0)
    voice_id = sel_voice.split("—")[-1].strip() if "—" in sel_voice else ""

    st.header("Topics / queries (one per line)")
    topics = st.text_area("Topics", height=140, label_visibility="collapsed", placeholder="world news\nAI research")

    st.header("Exact length (minutes)")
    minutes = st.slider("Exact minutes", 2, 30, 8, 1)

    st.header("Tone")
    tone = st.selectbox("Tone", ["confident and crisp","calm and neutral","warm and friendly","fast and energetic"], index=0)

    st.header("How far back to look (hours)")
    lookback = st.slider("Lookback", 6, 72, 24, 1)

    st.header("Maximum stories per topic")
    cap = st.slider("Cap per topic", 2, 8, 6, 1)

    strict = st.toggle("Strict timing (playback adjusted to exact length)", value=True)

    go = st.button("🚀 Generate Noah", use_container_width=True)

st.title("Noah — Daily Smart Bulletins")
st.caption("Generated news & insights in your language, your voice, your time.")

if "last" not in st.session_state: st.session_state.last = None

def call_with_retry(method, url, **kw):
    for i in range(5):
        try:
            r = requests.request(method, url, timeout=30, **kw)
            if r.status_code in (502,503,504):
                time.sleep(1.5*(i+1)); continue
            return r
        except requests.exceptions.RequestException:
            time.sleep(1.5*(i+1))
    raise RuntimeError(f"Failed to reach {url}")

if go:
    queries = [q.strip() for q in topics.splitlines() if q.strip()]
    payload = {
        "queries": queries,
        "language": lang,
        "tone": tone,
        "recent_hours": lookback,
        "per_feed": 4,
        "cap_per_query": cap,
        "min_minutes": minutes,
        "exact_minutes": bool(strict),
        "voice_id": voice_id or None,
    }
    with st.status("Contacting Noah API…", state="running", expanded=True) as stat:
        try:
            r = call_with_retry("POST", f"{API_BASE}/generate", json=payload)
            if not r.ok:
                st.error(f"API {r.status_code}: {r.text[:400]}")
            else:
                job_id = r.json().get("job_id")
                st.write(f"Started job: `{job_id}`")

                start = time.time(); res = None; last_stage = ""
                while True:
                    time.sleep(2.0)
                    rr = call_with_retry("GET", f"{API_BASE}/result/{job_id}")
                    js = rr.json()
                    if js.get("status") == "done":
                        res = js.get("result"); break
                    if js.get("status") == "error":
                        st.error(f"API job failed: {js.get('error','unknown error')[:400]}"); break
                    stage = js.get("progress","")
                    if stage and stage != last_stage:
                        st.write(f"• {stage.replace('_',' ').title()}"); last_stage = stage
                    if time.time() - start > MAX_WAIT_SECONDS:
                        st.error("Timeout waiting for API result."); break
                if res:
                    st.success(f"Received in {time.time()-start:.1f}s")
                    st.session_state.last = res
        except Exception as e:
            st.error(f"Client error: {e}")

res = st.session_state.last
if res:
    col1, col2 = st.columns([1,1])
    with col1:
        st.subheader("Bullet points")
        st.markdown(res.get("bullet_points") or "-")
    with col2:
        st.subheader("Your briefing")
        provider = res.get("tts_provider","")
        note = f" • Voice: {provider}" if provider else ""
        target_m = res.get("minutes_target", 0)
        actual_s = float(res.get("duration_seconds", 0))
        st.caption(f"Target: {target_m} min • Actual: {actual_s/60:.1f} min • Playback: {res.get('playback_rate_applied',1.0):.2f}x{note}")
        st.audio(f"{API_BASE}{res['mp3_url']}")
        audio = call_with_retry("GET", f"{API_BASE}{res['mp3_url']}").content
        st.download_button("⬇️ Download MP3", data=audio, file_name="noah.mp3", mime="audio/mpeg", use_container_width=True)

    with st.expander("Sources used"):
        for topic, items in (res.get("sources") or {}).items():
            st.markdown(f"**{topic}**")
            for it in items:
                st.markdown(f"- {it.get('title','')} — *{it.get('source','')}* — [link]({it.get('link','#')})")
