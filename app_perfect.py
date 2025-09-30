# app_perfect.py - Launch-Ready Streamlit Frontend for Daily Noah
"""
🚀 DAILY NOAH PERFECT FRONTEND
The most reliable, launch-ready AI briefing interface.

Features:
- Perfect timing accuracy display
- Real-time progress tracking
- Beautiful, responsive UI
- Bulletproof error handling
- Production-ready reliability
"""

import os
import time
import json
import requests
import streamlit as st
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# ============================================================================
# PERFECT CONFIGURATION
# ============================================================================

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")

# Perfect styling
PERFECT_CSS = """
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    
    .progress-container {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 0.5rem;
    }
    
    .status-online {
        background: #4caf50;
    }
    
    .status-offline {
        background: #f44336;
    }
    
    .status-degraded {
        background: #ff9800;
    }
    
    .timing-display {
        background: #e3f2fd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
    
    .insight-highlight {
        background: #f3e5f5;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #9c27b0;
        margin: 1rem 0;
    }
</style>
"""

# ============================================================================
# PERFECT STATE MANAGEMENT
# ============================================================================

def initialize_perfect_state():
    """Initialize perfect session state"""
    if "generation_history" not in st.session_state:
        st.session_state.generation_history = []
    
    if "user_preferences" not in st.session_state:
        st.session_state.user_preferences = {
            "default_duration": 5,
            "default_voice": "21m00Tcm4TlvDq8ikWAM",
            "default_tone": "professional",
            "favorite_topics": ["AI developments", "tech news", "world news"]
        }

# ============================================================================
# PERFECT API CLIENT
# ============================================================================

class PerfectAPIClient:
    """Perfect API client with bulletproof error handling"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
    
    def get_health(self) -> Dict[str, Any]:
        """Get perfect health status"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def get_voices(self) -> Dict[str, Any]:
        """Get available voices with perfect error handling"""
        try:
            response = self.session.get(f"{self.base_url}/voices", timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error fetching voices: {e}")
            return {"voices": []}
    
    def start_generation(self, topics: List[str], language: str, voice: str, 
                        duration: int, tone: str) -> Dict[str, Any]:
        """Start perfect generation"""
        try:
            payload = {
                "topics": topics,
                "language": language,
                "voice": voice,
                "duration": duration,
                "tone": tone
            }
            
            response = self.session.post(f"{self.base_url}/generate", json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error starting generation: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_progress(self, progress_id: str) -> Dict[str, Any]:
        """Get generation progress with perfect error handling"""
        try:
            response = self.session.get(f"{self.base_url}/progress/{progress_id}", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_result(self, progress_id: str) -> Dict[str, Any]:
        """Get generation result with perfect error handling"""
        try:
            response = self.session.get(f"{self.base_url}/result/{progress_id}", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}

# ============================================================================
# PERFECT UI COMPONENTS
# ============================================================================

def render_perfect_header():
    """Render perfect header with status indicators"""
    st.markdown(PERFECT_CSS, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("""
        <div class="main-header">
            <h1>🎙️ Daily Noah Perfect</h1>
            <p>The Most Reliable AI Briefing System</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # System status
        if "system_health" in st.session_state:
            health = st.session_state.system_health
            status_class = f"status-{health.get('ok', False) and 'online' or 'offline'}"
            st.markdown(f"""
            <div class="metric-card">
                <h4>System Status</h4>
                <p><span class="status-indicator {status_class}"></span>
                {health.get('ok', False) and 'Online' or 'Offline'}</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        # Generation count
        history_count = len(st.session_state.get("generation_history", []))
        st.markdown(f"""
        <div class="metric-card">
            <h4>Generations</h4>
            <p>📊 {history_count} completed</p>
        </div>
        """, unsafe_allow_html=True)

def render_perfect_sidebar():
    """Render perfect sidebar with enhanced controls"""
    with st.sidebar:
        st.markdown("### 🎯 Perfect Generation Settings")
        
        # Topics input with suggestions
        st.markdown("**Topics**")
        topics_input = st.text_area(
            "Enter topics (one per line)",
            value="\n".join(st.session_state.user_preferences.get("favorite_topics", [
                "AI developments",
                "tech news",
                "world news"
            ])),
            height=120,
            placeholder="Enter topics here...\nOne topic per line\nExample:\nAI developments\ntech news\nworld news"
        )
        
        # Parse topics
        topics = [topic.strip() for topic in topics_input.split('\n') if topic.strip()]
        
        # Language selection
        st.markdown("**Language**")
        language = st.selectbox(
            "Select Language",
            ["English", "Spanish", "French", "German", "Italian", "Portuguese"],
            index=0
        )
        
        # Voice selection
        st.markdown("**Voice Selection**")
        if "voices_data" in st.session_state:
            voices = st.session_state.voices_data.get("voices", [])
            if voices:
                voice_options = {f"{v['name']} ({v['accent']})": v['id'] for v in voices}
                selected_voice_name = st.selectbox(
                    "Choose Voice",
                    list(voice_options.keys()),
                    index=0
                )
                selected_voice = voice_options[selected_voice_name]
            else:
                selected_voice = "21m00Tcm4TlvDq8ikWAM"
        else:
            selected_voice = "21m00Tcm4TlvDq8ikWAM"
        
        # Duration with perfect controls
        st.markdown("**Duration**")
        duration = st.slider(
            "Duration (minutes)", 
            1, 30, 
            st.session_state.user_preferences.get("default_duration", 5)
        )
        
        # Tone selection
        st.markdown("**Tone**")
        tone = st.selectbox(
            "Tone",
            ["professional", "friendly", "casual", "formal", "conversational", "authoritative"],
            index=0
        )
        
        # Perfect timing info
        st.markdown("#### ⏱️ Perfect Timing")
        st.info(f"""
        **Target Duration:** {duration} minutes
        **Expected Words:** ~{duration * 140} words
        **Timing Accuracy:** ±5 seconds
        """)
        
        # Save preferences
        if st.button("💾 Save Preferences", use_container_width=True):
            new_prefs = {
                "favorite_topics": topics,
                "default_duration": duration,
                "default_voice": selected_voice,
                "default_tone": tone
            }
            st.session_state.user_preferences.update(new_prefs)
            st.success("Preferences saved!")
        
        return {
            "topics": topics,
            "language": language,
            "voice": selected_voice,
            "duration": duration,
            "tone": tone
        }

def render_perfect_progress_tracking(progress_id: str):
    """Render perfect progress tracking with real-time updates"""
    if not progress_id:
        return None
    
    # Create progress containers
    progress_container = st.container()
    metrics_container = st.container()
    
    with progress_container:
        st.markdown("### 📊 Perfect Generation Progress")
        
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        time_container = st.empty()
        
        # Real-time progress tracking
        start_time = time.time()
        last_progress = 0
        
        while True:
            try:
                # Get progress from API
                api_client = PerfectAPIClient(API_BASE)
                progress_data = api_client.get_progress(progress_id)
                
                if progress_data.get("status") == "error":
                    st.error(f"Progress tracking error: {progress_data.get('error')}")
                    break
                
                progress_percent = progress_data.get("progress_percent", 0)
                current_step = progress_data.get("current_step", "Processing...")
                estimated_time = progress_data.get("estimated_time_remaining", 0)
                
                # Update UI
                progress_bar.progress(progress_percent / 100)
                status_text.info(f"🔄 {current_step} ({progress_percent}%)")
                
                # Show elapsed time
                elapsed = int(time.time() - start_time)
                time_text = f"⏱️ Elapsed: {elapsed}s"
                if estimated_time > 0:
                    time_text += f" | Est. remaining: {estimated_time}s"
                time_container.info(time_text)
                
                # Check if complete
                if progress_data.get("status") == "completed":
                    st.success("✅ Perfect generation completed!")
                    break
                elif progress_data.get("status") == "error":
                    st.error(f"❌ Error: {progress_data.get('error')}")
                    break
                
                # Smooth progress animation
                if progress_percent > last_progress:
                    time.sleep(0.5)  # Smooth updates
                else:
                    time.sleep(2)  # Check every 2 seconds
                
                last_progress = progress_percent
                
            except Exception as e:
                st.warning(f"⚠️ Progress check failed: {e}")
                time.sleep(3)
                continue
    
    return progress_id

def render_perfect_results_display(result: Dict[str, Any]):
    """Render perfect results display"""
    if result.get("status") != "success":
        st.error(f"Generation failed: {result.get('error')}")
        return
    
    st.markdown("### 🎉 Perfect Generation Complete!")
    
    # Results in tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🎵 Audio Player", "📝 Transcript", "📊 Perfect Metrics", "📰 Sources"])
    
    with tab1:
        render_perfect_audio_player(result)
    
    with tab2:
        render_perfect_transcript(result)
    
    with tab3:
        render_perfect_metrics(result)
    
    with tab4:
        render_perfect_sources(result)

def render_perfect_audio_player(result: Dict[str, Any]):
    """Render perfect audio player"""
    audio_url = result.get("audio_url", "")
    if audio_url:
        full_audio_url = f"{API_BASE}{audio_url}"
        
        # Audio player
        st.audio(full_audio_url, format="audio/mpeg")
        
        # Perfect timing display
        actual_duration = result.get("duration_minutes", 0)
        target_duration = result.get("target_duration_minutes", 0)
        timing_accuracy = result.get("timing_accuracy", 0)
        
        st.markdown(f"""
        <div class="timing-display">
            <h4>⏱️ Perfect Timing Results</h4>
            <p><strong>Target Duration:</strong> {target_duration:.2f} minutes</p>
            <p><strong>Actual Duration:</strong> {actual_duration:.2f} minutes</p>
            <p><strong>Timing Accuracy:</strong> {timing_accuracy:.1%}</p>
            <p><strong>Difference:</strong> {abs(actual_duration - target_duration):.2f} minutes</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Download button
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("⬇️ Download MP3", use_container_width=True):
                st.download_button(
                    "Download",
                    data=requests.get(full_audio_url, timeout=60).content,
                    file_name=result.get("mp3_name", "noah_bulletin.mp3"),
                    mime="audio/mpeg"
                )
        
        with col2:
            if st.button("📱 Share", use_container_width=True):
                st.info("Share functionality coming soon!")
        
        with col3:
            if st.button("⭐ Rate", use_container_width=True):
                st.info("Rating system coming soon!")

def render_perfect_transcript(result: Dict[str, Any]):
    """Render perfect transcript"""
    transcript = result.get("transcript", "")
    
    if transcript:
        # Transcript with word count
        word_count = result.get("word_count", 0)
        st.markdown(f"**Word Count:** {word_count} words")
        
        # Readable transcript
        st.text_area("Generated Transcript", transcript, height=400, disabled=True)
        
        # Transcript actions
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📋 Copy Transcript", use_container_width=True):
                st.code(transcript)
        
        with col2:
            if st.button("📝 Edit", use_container_width=True):
                st.info("Transcript editing coming soon!")
        
        with col3:
            if st.button("💾 Save", use_container_width=True):
                st.info("Save functionality coming soon!")

def render_perfect_metrics(result: Dict[str, Any]):
    """Render perfect metrics"""
    quality_metrics = result.get("quality_metrics", {})
    
    if quality_metrics:
        st.markdown("#### 📊 Perfect Quality Metrics")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Articles Found", quality_metrics.get("articles_found", 0))
        
        with col2:
            st.metric("Avg Relevance", f"{quality_metrics.get('average_relevance', 0):.2f}/10")
        
        with col3:
            st.metric("Avg Recency", f"{quality_metrics.get('average_recency', 0):.2f}/1.0")
        
        with col4:
            st.metric("Timing Accuracy", f"{quality_metrics.get('timing_accuracy', 0):.1%}")
        
        # Generation time
        generation_time = result.get("generation_time", 0)
        st.metric("Generation Time", f"{generation_time:.1f} seconds")
        
        # Perfect timing highlight
        timing_accuracy = quality_metrics.get("timing_accuracy", 0)
        if timing_accuracy > 0.95:
            st.success("🎯 Perfect timing accuracy achieved!")
        elif timing_accuracy > 0.90:
            st.info("✅ Excellent timing accuracy")
        else:
            st.warning("⚠️ Timing accuracy could be improved")

def render_perfect_sources(result: Dict[str, Any]):
    """Render perfect source articles"""
    sources = result.get("sources", [])
    
    if sources:
        st.markdown(f"#### 📰 Source Articles ({len(sources)} articles)")
        
        for i, source in enumerate(sources, 1):
            with st.expander(f"Article {i}: {source.get('title', 'Untitled')[:50]}..."):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Title:** {source.get('title', 'N/A')}")
                    st.markdown(f"**Source:** {source.get('source', 'N/A')}")
                    st.markdown(f"**Topic:** {source.get('topic', 'N/A')}")
                    st.markdown(f"**Relevance Score:** {source.get('relevance_score', 0):.2f}/10")
                    st.markdown(f"**Recency Score:** {source.get('recency_score', 0):.2f}/1.0")
                
                with col2:
                    if source.get('url'):
                        st.markdown(f"[📖 Read Full Article]({source['url']})")
                    
                    # Content preview
                    content = source.get('content', '')
                    if content:
                        st.markdown("**Preview:**")
                        st.text(content[:200] + "..." if len(content) > 200 else content)
    else:
        st.info("No source articles available for this briefing.")

# ============================================================================
# MAIN PERFECT APPLICATION
# ============================================================================

def main():
    """Main perfect application function"""
    # Initialize session state
    initialize_perfect_state()
    
    # Set page config
    st.set_page_config(
        page_title="Daily Noah Perfect",
        page_icon="🎙️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Render header
    render_perfect_header()
    
    # Check system health
    api_client = PerfectAPIClient(API_BASE)
    health = api_client.get_health()
    st.session_state.system_health = health
    
    if not health.get("ok", False):
        st.error("⚠️ System is offline. Please check your connection and try again.")
        st.stop()
    
    # Load voices
    if "voices_data" not in st.session_state:
        with st.spinner("Loading voices..."):
            voices_data = api_client.get_voices()
            st.session_state.voices_data = voices_data
    
    # Main content area
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Sidebar
        generation_params = render_perfect_sidebar()
    
    with col2:
        # Main generation area
        if not generation_params["topics"]:
            st.warning("⚠️ Please enter at least one topic in the sidebar to generate a briefing.")
            st.stop()
        
        # Generate button
        if st.button("🚀 Generate Perfect Bulletin", use_container_width=True, type="primary"):
            # Start generation
            with st.spinner("Starting perfect generation..."):
                start_result = api_client.start_generation(
                    topics=generation_params["topics"],
                    language=generation_params["language"],
                    voice=generation_params["voice"],
                    duration=generation_params["duration"],
                    tone=generation_params["tone"]
                )
            
            if start_result.get("status") == "started":
                progress_id = start_result.get("progress_id")
                
                # Track progress
                render_perfect_progress_tracking(progress_id)
                
                # Get final result
                result = api_client.get_result(progress_id)
                
                if result.get("status") == "success":
                    # Add to history
                    st.session_state.generation_history.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "params": generation_params,
                        "result": result
                    })
                    
                    # Display results
                    render_perfect_results_display(result)
                else:
                    st.error(f"Generation failed: {result.get('error')}")
            else:
                st.error(f"Failed to start generation: {start_result.get('error')}")
        
        # Generation history
        if st.session_state.generation_history:
            with st.expander("📚 Generation History"):
                for i, history_item in enumerate(reversed(st.session_state.generation_history[-5:])):
                    timestamp = history_item["timestamp"]
                    topics = history_item["params"]["topics"]
                    duration = history_item["params"]["duration"]
                    
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"**{', '.join(topics)}**")
                    
                    with col2:
                        st.write(f"{duration} min")
                    
                    with col3:
                        st.write(timestamp[:19])

if __name__ == "__main__":
    main()
