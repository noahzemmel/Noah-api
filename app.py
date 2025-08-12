# app.py — Streamlit UI for Noah that PERSISTS results in session_state
import os, time, requests, streamlit as st
from typing import List, Dict, Any

# ---- Config
API_BASE = os.getenv("API_BASE", "").rstrip("/")
APP_TITLE = "Noah — Daily Smart Bulletins"

ACCENT="#2563EB"; FG="#E8EDF7"; FG_MUTED="#C7D2FE"; BG="#0B1220"; CARD="#0F172A"; BORDER="#1F2A44"
st.set_page_config(page_title="Noah • Zem Labs", page_icon="🎧", layout="wide")

st.markdown(f"""
<style>
  .stApp{{background:{BG};color:{FG};}}
  .block-container{{padding-top:1.2rem;}}
  h1,h2,h3,h4{{color:{FG};}}
  .zem-card{{background:{CARD};border:1px solid {BORDER};border-radius:12px;padding:14px;}}
  .zem-label{{font-weight:700;font-size:.95rem;color:{FG};margin:10px 0 6px;display:block;}}
  textarea,.stTextArea textarea,input,select{{background:{CARD}!important;color:{FG}!important;
    border:1px solid {BORDER}!important;border-radius:10px!important;}}
  .stSelectbox [data-baseweb="select"]>div{{background:{CARD}!important;color:{FG}!important;
    border:1px solid {BORDER}!important;border-radius:10px!important;}}
  .stSlider>div>div>div>div{{background:{ACCENT};}}
  .stButton>button{{background:{ACCENT};color:white;border:0;border-radius:10px;padding:10px 14px;font-weight:700;}}
  ::placeholder{{color:{FG_MUTED};opacity:.95;}}
  audio{{width:100%;border-radius:10px;height:40px;}}
  details{{border:1px solid {BORDER};border-radius:10px;overflow:hidden;}}
  details>summary{{cursor:pointer;background:{CARD};padding:8px 12px;}}
  details>div{{padding:10px 12px;}}
</style>
""", unsafe_allow_html=True)

# ---- Helpers
def parse_topics(s:str)->List[str]:
    out, seen=[],set()
    for c in s.replace(",","\n").split("\n"):
        c=c.strip(); k=c.lower()
        if c and k not in seen: out.append(c); seen.add(k)
    return out

def call_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not API_BASE.startswith("http"):
        raise RuntimeError("API_BASE not set. In Render → Environment, add API_BASE=https://thenoah.onrender.com")
    r = requests.post(f"{API_BASE}/generate", json=payload, timeout=600)
    text = r.text
    try:
        data = r.json()
    except Exception:
        data = {"error": text}
    if r.status_code >= 400:
        raise RuntimeError(f"API {r.status_code}: {data.get('error', text)[:600]}")
    return data

def fetch_voices()->List[Dict[str,str]]:
    try:
        r=requests.get(f"{API_BASE}/voices",timeout=20)
        if r.status_code==200:
            lst=r.json() or []
            lst=[{"name":"Use API default","id":""}] + lst + [{"name":"Custom voice id…","id":"__custom__"}]
            return lst
    except Exception:
        pass
    return [{"name":"Use API default","id":""},{"name":"Custom voice id…","id":"__custom__"}]

def render_audio(mp3_url:str, actual_sec:float, target_min:int, rate_hint:float|None):
    """Scrubbable, persistent audio player."""
    if not mp3_url:
        st.info("No audio returned.")
        return
    if not mp3_url.startswith("http"):
        mp3_url=f"{API_BASE}{mp3_url}"
    rate = rate_hint or 1.0
    st.markdown(f"""
      <div class="zem-card">
        <audio id="noah-audio" controls preload="metadata" playsinline src="{mp3_url}"></audio>
        <div class="smallcap">Target: {target_min} min • Actual audio: {actual_sec/60:.1f} min • Playback rate: {rate:.2f}</div>
      </div>
      <script>
        const a=document.getElementById('noah-audio');
        if(a){{ a.addEventListener('loadedmetadata', ()=>{{ try{{ a.playbackRate={rate:.4f}; }}catch(e){{}} }}); }}
      </script>
    """, unsafe_allow_html=True)

# ---- Session state
if "noah_result" not in st.session_state:
    st.session_state.noah_result = None
if "last_payload" not in st.session_state:
    st.session_state.last_payload = None

# ---- Header
c1,c2=st.columns([0.72,0.28])
with c1:
    st.markdown(f"<h1 style='margin-bottom:.2rem'>{APP_TITLE}</h1>", unsafe_allow_html=True)
    st.caption("Generated news & insights in **your language**, **your voice**, **your time**.")
with c2:
    st.markdown(f"<div class='zem-card' style='text-align:right'><div class='smallcap'>API</div>"
                f"<code style='font-size:12px'>{API_BASE or 'NOT SET'}</code></div>", unsafe_allow_html=True)

# ---- Sidebar form (prevents reruns while typing)
with st.sidebar:
    with st.form("controls", clear_on_submit=False):
        st.markdown("<div class='zem-label'>Language</div>", unsafe_allow_html=True)
        language=st.selectbox("Language",["English","Spanish","French","German","Italian","Portuguese",
                            "Arabic","Hindi","Japanese","Korean","Chinese (Simplified)"],index=0,key="lang")

        st.markdown("<div class='zem-label'>Voice</div>", unsafe_allow_html=True)
        voice_options=fetch_voices(); voice_names=[v["name"] for v in voice_options]
        voice_choice=st.selectbox("Voice", voice_names, index=0, key="voice")
        voice_id=next((v["id"] for v in voice_options if v["name"]==voice_choice), "")
        if voice_id=="__custom__":
            voice_id=st.text_input("Paste custom ElevenLabs voice_id", key="custom_id")

        st.markdown("<div class='zem-label'>Topics / queries (one per line)</div>", unsafe_allow_html=True)
        topics_raw=st.text_area("Topics", height=140, value="world news\nAI research", key="topics")

        st.markdown("<div class='zem-label'>Exact length (minutes)</div>", unsafe_allow_html=True)
        minutes=st.slider("Exact minutes",2,30,8,key="min")

        st.markdown("<div class='zem-label'>Tone</div>", unsafe_allow_html=True)
        tone=st.selectbox("Tone",["neutral and calm","confident and crisp","warm and friendly","energetic and upbeat"],index=1,key="tone")

        st.markdown("<div class='zem-label'>How far back to look (hours)</div>", unsafe_allow_html=True)
        lookback=st.select_slider("Lookback", options=[6,12,24,36,48,72], value=24, key="lb")

        st.markdown("<div class='zem-label'>Maximum stories per topic</div>", unsafe_allow_html=True)
        cap=st.slider("Cap per topic",2,8,6,key="cap")

        strict = st.toggle("Strict timing (playback adjusted to exact length)", value=True, key="strict")

        submitted = st.form_submit_button("🚀 Generate Noah", use_container_width=True)

# ---- If submitted, call the API and SAVE the result in session_state
if submitted:
    queries = parse_topics(topics_raw)
    if not queries:
        st.sidebar.error("Please add at least one topic.")
    else:
        payload={"queries":queries,"language":language,"tone":tone,"recent_hours":int(lookback),
                 "per_feed":6,"cap_per_query":int(cap),
                 "min_minutes":int(minutes),"minutes_target":int(minutes),
                 "exact_minutes":True}
        if voice_id and voice_id!="__custom__":
            payload["voice_id"]=voice_id

        with st.status("Generating your Noah… this can take 30–60 seconds", expanded=True) as s:
            try:
                s.write("Contacting Noah API…")
                t0=time.time()
                data=call_api(payload)
                s.write(f"Received in {time.time()-t0:.1f}s")
                s.update(label="Done ✓", state="complete")
                # PERSIST the result and payload
                st.session_state.noah_result = {
                    "data": data,
                    "minutes": int(minutes),
                    "strict": bool(strict),
                }
                st.session_state.last_payload = payload
            except Exception as e:
                s.update(label="Failed ✗", state="error")
                st.error(str(e))

# ---- Always render the last result from session_state (so it survives reruns)
res = st.session_state.noah_result
L,R = st.columns([0.5,0.5])
if res and isinstance(res, dict):
    data = res.get("data") or {}
    minutes = res.get("minutes") or 0
    strict = res.get("strict") or False

    with L:
        st.markdown("<h3>Bullet points</h3>", unsafe_allow_html=True)
        st.markdown(f"<div class='zem-card'>{(data.get('bullet_points') or '').replace(chr(10),'<br/>')}</div>", unsafe_allow_html=True)
        st.markdown("<h3 style='margin-top:16px'>Narration script</h3>", unsafe_allow_html=True)
        st.markdown(f"<div class='zem-card' style='white-space:pre-wrap'>{data.get('script') or ''}</div>", unsafe_allow_html=True)

    with R:
        st.markdown("<h3>Your briefing</h3>", unsafe_allow_html=True)
        render_audio(
            mp3_url=data.get("mp3_url",""),
            actual_sec=float(data.get("duration_seconds") or 0),
            target_min=int(minutes),
            rate_hint=float(data.get("playback_rate_applied") or 1.0) if strict else 1.0,
        )
        st.markdown("<h4 style='margin-top:16px'>Sources used</h4>", unsafe_allow_html=True)
        src=data.get("sources") or {}
        if not src:
            st.caption("No sources returned.")
        else:
            html=["<details open><summary>Show sources</summary><div>"]
            for q, items in src.items():
                html.append(f"<div style='margin:6px 0'><b>{q}</b></div>")
                for it in items or []:
                    html.append(f"<div style='margin-left:10px'>• {it.get('title','(untitled)')} — {it.get('source','')} — <a href='{it.get('link','#')}' target='_blank' rel='noopener'>link</a></div>")
            html.append("</div></details>")
            st.markdown("".join(html), unsafe_allow_html=True)
else:
    st.info("Enter topics on the left and click **Generate Noah** to try the beta.")
