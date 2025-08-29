# app.py — Streamlit UI for Noah MVP (Simplified API)
import os, time, json, requests, streamlit as st

# Configuration - Use the deployed backend URL
API_BASE = os.getenv("API_BASE", "https://noah-api-t6wj.onrender.com").rstrip("/")

st.set_page_config(page_title="Noah — Daily Smart Bulletins", layout="wide")

st.title("🎙️ Noah — Daily Smart Bulletins")
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
    except Exception as e:
        st.error(f"Error fetching voices: {e}")
        # Fallback voices
        return [
            {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel (Default)", "provider": "elevenlabs"},
        ]

with st.sidebar:
    st.subheader("🎯 Topics")
    topics_input = st.text_area(
        "Enter topics (one per line)", 
        value="tech news\nAI developments", 
        height=120, 
        placeholder="Enter topics here...\nOne topic per line\nExample:\ntech news\nAI developments\nworld news"
    )
    
    # Parse topics from text input
    topics = [topic.strip() for topic in topics_input.split('\n') if topic.strip()]
    
    st.subheader("🌍 Language")
    language = st.selectbox("Language", ["English", "Spanish", "French", "German", "Italian"], index=0)

    st.subheader("🎙️ Voice")
    voices = fetch_voices()
    
    # Build options for selectbox
    def label(v: dict) -> str:
        name = v.get("name", "Unknown")
        provider = v.get("provider", "")
        accent = v.get("accent", "")
        return f"{name} ({provider})" + (f" - {accent}" if accent else "")

    selected_voice = st.selectbox(
        "Voice", 
        options=voices, 
        index=0,
        format_func=label,
    )
    voice_id = selected_voice.get("id", "21m00Tcm4TlvDq8ikWAM")

    st.subheader("⏱️ Duration")
    duration = st.slider("Duration (minutes)", 1, 15, 5)
    
    # Precision timing control
    strict_timing = st.checkbox("🎯 Enable Precision Timing", value=True, 
                               help="When enabled, Noah will generate bulletins that are exactly the requested duration (±30 seconds)")
    
    # Quick test mode
    quick_test = st.checkbox("⚡ Quick Test Mode", value=False,
                            help="Enable for faster testing with reduced content (may affect timing precision)")

    st.subheader("🎨 Tone")
    tone = st.selectbox("Tone", ["professional", "friendly", "casual", "formal"], index=0)

    run = st.button("🚀 Generate Bulletin", use_container_width=True, type="primary")

# Main content area
status = st.empty()

if run:
    # Parse topics from the input (do this when button is clicked)
    topics_list = [topic.strip() for topic in topics_input.split('\n') if topic.strip()]
    
    if not topics_list:
        status.error("❌ Please enter at least one topic to generate a bulletin.")
        st.stop()
    
    try:
        status.info("🔄 Generating your news bulletin...")
        
        # Show progress steps
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Step 1: Preparing request
        status_text.info("📤 Preparing request...")
        progress_bar.progress(10)
        
        # Prepare payload for simplified API
        payload = {
            "topics": topics_list,
            "language": language,
            "voice": voice_id,
            "duration": duration,
            "tone": tone,
            "strict_timing": strict_timing,
            "quick_test": quick_test
        }
        
        # Debug: Show what we're sending
        st.json(payload)
        st.info(f"🌐 Sending request to: {API_BASE}/generate")
        st.info(f"📤 Payload: {payload}")
        
        # Step 2: Sending to API
        status_text.info("📡 Sending to Noah API...")
        progress_bar.progress(20)
        
        # Call the API
        response = requests.post(f"{API_BASE}/generate", json=payload, timeout=300)  # Increased to 5 minutes
        
        # Step 3: Processing response
        status_text.info("📥 Processing response...")
        progress_bar.progress(80)
        
        # Debug: Show response details
        st.info(f"📥 Response status: {response.status_code}")
        st.info(f"📥 Response headers: {dict(response.headers)}")
        
        response.raise_for_status()
        
        result = response.json()
        st.info(f"📥 Response body: {result}")
        
        # Step 4: Complete
        progress_bar.progress(100)
        status_text.success("✅ Processing complete!")
        
        if result.get("status") == "success":
            status.success("✅ Bulletin generated successfully!")
            
            # Display results in columns
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("📝 Transcript")
                transcript = result.get("transcript", "")
                st.text_area("Generated Content", transcript, height=300, disabled=True)
            
            with col2:
                st.subheader("🎵 Audio")
                audio_url = result.get("audio_url", "")
                if audio_url:
                    # Construct full URL
                    full_audio_url = f"{API_BASE}{audio_url}"
                    st.audio(full_audio_url, format="audio/mpeg")
                    
                    # Download button
                    st.download_button(
                        "⬇ Download MP3",
                        data=requests.get(full_audio_url, timeout=60).content,
                        file_name=result.get("mp3_name", "noah_bulletin.mp3"),
                        mime="audio/mpeg"
                    )
                else:
                    st.warning("No audio generated.")
                
                st.subheader("📊 Details")
                st.write(f"**Target Duration:** {result.get('target_duration_minutes', 0):.1f} minutes")
                st.write(f"**Actual Duration:** {result.get('duration_minutes', 0):.2f} minutes")
                
                # Show timing accuracy
                accuracy = result.get('duration_accuracy_minutes', 0)
                if accuracy < 0.5:
                    st.success(f"🎯 **Timing Accuracy:** EXACT (±{accuracy:.2f} minutes)")
                elif accuracy < 1.0:
                    st.info(f"🎯 **Timing Accuracy:** CLOSE (±{accuracy:.2f} minutes)")
                else:
                    st.warning(f"🎯 **Timing Accuracy:** APPROXIMATE (±{accuracy:.2f} minutes)")
                
                st.write(f"**Precision Timing:** {'✅ Enabled' if result.get('precision_timing', False) else '❌ Disabled'}")
                st.write(f"**Topics:** {', '.join(result.get('topics', []))}")
                st.write(f"**Language:** {result.get('language', 'Unknown')}")
                st.write(f"**Voice:** {result.get('voice', 'Unknown')}")
                st.write(f"**Word Count:** {result.get('word_count', 0)} words")
                
                # Show news quality information
                news_quality = result.get('news_quality', {})
                if news_quality:
                    st.subheader("📰 News Quality")
                    quality_score = news_quality.get('quality_score', 0)
                    
                    if quality_score > 80:
                        st.success(f"🟢 **News Quality:** EXCELLENT ({quality_score:.1f}%)")
                    elif quality_score > 60:
                        st.info(f"🔵 **News Quality:** GOOD ({quality_score:.1f}%)")
                    elif quality_score > 40:
                        st.warning(f"🟡 **News Quality:** FAIR ({quality_score:.1f}%)")
                    else:
                        st.error(f"🔴 **News Quality:** POOR ({quality_score:.1f}%)")
                    
                    st.write(f"**Recent Articles:** {news_quality.get('recent_articles', 0)}/{news_quality.get('total_articles', 0)}")
                    st.write(f"**High Relevance:** {news_quality.get('high_relevance_articles', 0)} articles")
                    
                    topics_with_news = news_quality.get('topics_with_news', [])
                    topics_without_news = news_quality.get('topics_without_news', [])
                    
                    if topics_with_news:
                        st.success(f"✅ **Topics with recent news:** {', '.join(topics_with_news)}")
                    
                    if topics_without_news:
                        st.warning(f"⚠️ **Topics without recent news:** {', '.join(topics_without_news)}")
                    
                    if not news_quality.get('has_recent_news', False):
                        st.info("💡 **Tip:** Try requesting different topics or check back later for fresh updates.")
        
        else:
            status.error(f"❌ Error: {result.get('error', 'Unknown error')}")
            
    except requests.exceptions.HTTPError as e:
        error_detail = e.response.text if e.response else "No details"
        status.error(f"❌ API Error {e.response.status_code}: {error_detail}")
        st.error(f"Full error: {error_detail}")
        
        # Debug: Show more error details
        st.error(f"Request URL: {API_BASE}/generate")
        st.error(f"Request payload: {payload}")
        st.error(f"Response status: {e.response.status_code}")
        st.error(f"Response text: {e.response.text}")
        
    except Exception as e:
        status.error(f"❌ Error: {str(e)}")
        st.error(f"Exception: {str(e)}")
        st.error(f"Exception type: {type(e)}")
else:
    # Show instructions when not generating
    st.info("🎯 Enter your topics in the sidebar and click 'Generate Bulletin' to get started!")

# Footer
st.markdown("---")
st.caption("🎙️ Noah MVP - AI-powered news bulletins | Built with FastAPI, Streamlit, OpenAI, and ElevenLabs")
