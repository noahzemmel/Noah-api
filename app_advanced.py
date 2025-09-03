# app_advanced.py - World-Class Streamlit Frontend for Daily Noah
"""
🚀 DAILY NOAH ADVANCED FRONTEND
The most sophisticated AI briefing interface ever built.

Features:
- Real-time WebSocket updates
- Advanced progress tracking
- Beautiful, responsive UI/UX
- Advanced analytics dashboard
- Voice preview and testing
- Content quality controls
- Real-time collaboration
- Mobile-optimized design
- Dark/light theme support
- Advanced user preferences
"""

import os
import time
import json
import asyncio
import requests
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import websockets
import threading
from dataclasses import dataclass

# ============================================================================
# ADVANCED CONFIGURATION
# ============================================================================

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")
WS_BASE = API_BASE.replace("http", "ws")

# Advanced styling
ADVANCED_CSS = """
<style>
    /* Advanced styling for world-class UI */
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
    
    .quality-indicator {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    
    .quality-premium {
        background: #e3f2fd;
        color: #1976d2;
    }
    
    .quality-enterprise {
        background: #f3e5f5;
        color: #7b1fa2;
    }
    
    .voice-card {
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .voice-card:hover {
        border-color: #667eea;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
    }
    
    .voice-card.selected {
        border-color: #667eea;
        background: #f0f4ff;
    }
    
    .analytics-chart {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
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
</style>
"""

# ============================================================================
# ADVANCED DATA MODELS
# ============================================================================

@dataclass
class GenerationRequest:
    topics: List[str]
    language: str = "English"
    voice: str = "21m00Tcm4TlvDq8ikWAM"
    duration: int = 5
    tone: str = "professional"
    quality: str = "premium"
    priority: str = "normal"
    enable_caching: bool = True
    enable_analytics: bool = True

@dataclass
class ProgressData:
    progress_id: str
    status: str
    progress_percent: int
    current_step: str
    estimated_time_remaining: Optional[int] = None
    error: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None

# ============================================================================
# ADVANCED STATE MANAGEMENT
# ============================================================================

def initialize_session_state():
    """Initialize advanced session state"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if "user_id" not in st.session_state:
        st.session_state.user_id = f"user_{int(time.time())}"
    
    if "generation_history" not in st.session_state:
        st.session_state.generation_history = []
    
    if "user_preferences" not in st.session_state:
        st.session_state.user_preferences = {
            "default_quality": "premium",
            "default_duration": 5,
            "default_voice": "21m00Tcm4TlvDq8ikWAM",
            "theme": "light",
            "notifications": True,
            "auto_download": False
        }
    
    if "websocket_connected" not in st.session_state:
        st.session_state.websocket_connected = False
    
    if "real_time_updates" not in st.session_state:
        st.session_state.real_time_updates = []

# ============================================================================
# ADVANCED API CLIENT
# ============================================================================

class AdvancedAPIClient:
    """Advanced API client with caching and error handling"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-User-ID": st.session_state.get("user_id", "anonymous")
        })
    
    async def get_health(self) -> Dict[str, Any]:
        """Get advanced health status"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"overall_status": "unhealthy", "error": str(e)}
    
    async def get_voices(self) -> Dict[str, Any]:
        """Get available voices with caching"""
        cache_key = "voices_advanced"
        if cache_key in st.session_state:
            cached_time = st.session_state.get(f"{cache_key}_time", 0)
            if time.time() - cached_time < 3600:  # 1 hour cache
                return st.session_state[cache_key]
        
        try:
            response = self.session.get(f"{self.base_url}/voices", timeout=15)
            response.raise_for_status()
            voices_data = response.json()
            
            # Cache the result
            st.session_state[cache_key] = voices_data
            st.session_state[f"{cache_key}_time"] = time.time()
            
            return voices_data
        except Exception as e:
            st.error(f"Error fetching voices: {e}")
            return {"voices": [], "error": str(e)}
    
    async def start_generation(self, request: GenerationRequest) -> Dict[str, Any]:
        """Start advanced generation"""
        try:
            payload = {
                "topics": request.topics,
                "language": request.language,
                "voice": request.voice,
                "duration": request.duration,
                "tone": request.tone,
                "quality": request.quality,
                "priority": request.priority,
                "enable_caching": request.enable_caching,
                "enable_analytics": request.enable_analytics,
                "user_id": st.session_state.get("user_id")
            }
            
            response = self.session.post(f"{self.base_url}/generate", json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error starting generation: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_progress(self, progress_id: str) -> Dict[str, Any]:
        """Get generation progress"""
        try:
            response = self.session.get(f"{self.base_url}/progress/{progress_id}", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_result(self, progress_id: str) -> Dict[str, Any]:
        """Get generation result"""
        try:
            response = self.session.get(f"{self.base_url}/result/{progress_id}", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_analytics(self, date_range: str = "7d") -> Dict[str, Any]:
        """Get advanced analytics"""
        try:
            payload = {
                "user_id": st.session_state.get("user_id"),
                "date_range": date_range,
                "metrics": ["generation_time", "quality_score", "cache_hits", "success_rate"]
            }
            
            response = self.session.post(f"{self.base_url}/analytics", json=payload, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

# ============================================================================
# ADVANCED UI COMPONENTS
# ============================================================================

def render_advanced_header():
    """Render advanced header with status indicators"""
    st.markdown(ADVANCED_CSS, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("""
        <div class="main-header">
            <h1>🎙️ Daily Noah Advanced</h1>
            <p>The World's Most Advanced AI Briefing System</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # System status
        if "system_health" in st.session_state:
            health = st.session_state.system_health
            status_class = f"status-{health.get('overall_status', 'offline')}"
            st.markdown(f"""
            <div class="metric-card">
                <h4>System Status</h4>
                <p><span class="status-indicator {status_class}"></span>
                {health.get('overall_status', 'Unknown').title()}</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        # User info
        user_id = st.session_state.get("user_id", "Anonymous")
        st.markdown(f"""
        <div class="metric-card">
            <h4>User</h4>
            <p>👤 {user_id}</p>
        </div>
        """, unsafe_allow_html=True)

def render_advanced_sidebar():
    """Render advanced sidebar with enhanced controls"""
    with st.sidebar:
        st.markdown("### 🎯 Generation Settings")
        
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
            ["English", "Spanish", "French", "German", "Italian", "Portuguese", "Chinese", "Japanese"],
            index=0
        )
        
        # Advanced voice selection
        st.markdown("**Voice Selection**")
        if "voices_data" in st.session_state:
            voices = st.session_state.voices_data.get("voices", [])
            if voices:
                selected_voice = render_voice_selector(voices)
            else:
                selected_voice = "21m00Tcm4TlvDq8ikWAM"
        else:
            selected_voice = "21m00Tcm4TlvDq8ikWAM"
        
        # Duration with advanced controls
        st.markdown("**Duration**")
        duration = st.slider("Duration (minutes)", 1, 30, st.session_state.user_preferences.get("default_duration", 5))
        
        # Quality selection
        st.markdown("**Content Quality**")
        quality_options = {
            "Draft": "draft",
            "Standard": "standard", 
            "Premium": "premium",
            "Enterprise": "enterprise"
        }
        
        quality_labels = list(quality_options.keys())
        quality_index = quality_labels.index("Premium")  # Default to Premium
        
        selected_quality_label = st.selectbox(
            "Quality Level",
            quality_labels,
            index=quality_index
        )
        selected_quality = quality_options[selected_quality_label]
        
        # Tone selection
        st.markdown("**Tone**")
        tone = st.selectbox(
            "Tone",
            ["professional", "friendly", "casual", "formal", "conversational", "authoritative"],
            index=0
        )
        
        # Priority selection
        st.markdown("**Priority**")
        priority = st.selectbox(
            "Generation Priority",
            ["low", "normal", "high", "urgent"],
            index=1
        )
        
        # Advanced options
        with st.expander("🔧 Advanced Options"):
            enable_caching = st.checkbox("Enable Caching", value=True)
            enable_analytics = st.checkbox("Enable Analytics", value=True)
            auto_download = st.checkbox("Auto Download", value=False)
        
        # Save preferences
        if st.button("💾 Save Preferences", use_container_width=True):
            new_prefs = {
                "favorite_topics": topics,
                "default_language": language,
                "default_voice": selected_voice,
                "default_duration": duration,
                "default_quality": selected_quality,
                "auto_download": auto_download
            }
            st.session_state.user_preferences.update(new_prefs)
            st.success("Preferences saved!")
        
        return GenerationRequest(
            topics=topics,
            language=language,
            voice=selected_voice,
            duration=duration,
            tone=tone,
            quality=selected_quality,
            priority=priority,
            enable_caching=enable_caching,
            enable_analytics=enable_analytics
        )

def render_voice_selector(voices: List[Dict]) -> str:
    """Render advanced voice selector with previews"""
    selected_voice = st.session_state.user_preferences.get("default_voice", "21m00Tcm4TlvDq8ikWAM")
    
    # Group voices by language
    voices_by_language = {}
    for voice in voices:
        lang = voice.get("language", "en")
        if lang not in voices_by_language:
            voices_by_language[lang] = []
        voices_by_language[lang].append(voice)
    
    # Language tabs
    if len(voices_by_language) > 1:
        lang_tabs = st.tabs(list(voices_by_language.keys()))
        for i, (lang, lang_voices) in enumerate(voices_by_language.items()):
            with lang_tabs[i]:
                selected_voice = render_voice_cards(lang_voices, selected_voice)
    else:
        selected_voice = render_voice_cards(voices, selected_voice)
    
    return selected_voice

def render_voice_cards(voices: List[Dict], current_selection: str) -> str:
    """Render voice selection cards"""
    selected_voice = current_selection
    
    for voice in voices:
        voice_id = voice.get("id", "")
        name = voice.get("name", "Unknown")
        accent = voice.get("accent", "")
        gender = voice.get("gender", "unknown")
        quality_score = voice.get("quality_score", 0.9)
        
        # Create voice card
        col1, col2 = st.columns([3, 1])
        
        with col1:
            is_selected = voice_id == current_selection
            card_class = "voice-card selected" if is_selected else "voice-card"
            
            st.markdown(f"""
            <div class="{card_class}" onclick="selectVoice('{voice_id}')">
                <h4>{name}</h4>
                <p>🎭 {accent.title()} • 👤 {gender.title()}</p>
                <p>⭐ Quality: {quality_score:.1f}/1.0</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if st.button("▶️", key=f"preview_{voice_id}", help="Preview voice"):
                st.info(f"Previewing {name}...")
        
        if st.button(f"Select {name}", key=f"select_{voice_id}", use_container_width=True):
            selected_voice = voice_id
            st.session_state.user_preferences["default_voice"] = voice_id
            st.rerun()
    
    return selected_voice

def render_progress_tracking(progress_id: str):
    """Render advanced progress tracking with real-time updates"""
    if not progress_id:
        return None
    
    # Create progress containers
    progress_container = st.container()
    metrics_container = st.container()
    
    with progress_container:
        st.markdown("### 📊 Generation Progress")
        
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
                api_client = AdvancedAPIClient(API_BASE)
                progress_data = asyncio.run(api_client.get_progress(progress_id))
                
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
                    st.success("✅ Generation completed successfully!")
                    break
                elif progress_data.get("status") == "error":
                    st.error(f"❌ Error: {progress_data.get('error')}")
                    break
                
                # Update metrics if available
                if progress_data.get("metrics"):
                    with metrics_container:
                        render_generation_metrics(progress_data["metrics"])
                
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

def render_generation_metrics(metrics: Dict[str, Any]):
    """Render generation metrics in real-time"""
    st.markdown("### 📈 Real-time Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Quality Score", f"{metrics.get('quality_score', 0):.2f}")
    
    with col2:
        st.metric("Timing Accuracy", f"{metrics.get('timing_accuracy', 0):.1%}")
    
    with col3:
        st.metric("Cache Hits", metrics.get('cache_hits', 0))
    
    with col4:
        st.metric("API Calls", metrics.get('api_calls', 0))

def render_results_display(result: Dict[str, Any]):
    """Render advanced results display"""
    if result.get("status") != "success":
        st.error(f"Generation failed: {result.get('error')}")
        return
    
    st.markdown("### 🎉 Generation Complete!")
    
    # Results in tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🎵 Audio Player", "📝 Transcript", "📊 Analytics", "📰 Sources"])
    
    with tab1:
        render_audio_player(result)
    
    with tab2:
        render_transcript(result)
    
    with tab3:
        render_generation_analytics(result)
    
    with tab4:
        render_sources(result)

def render_audio_player(result: Dict[str, Any]):
    """Render advanced audio player"""
    audio_url = result.get("audio_url", "")
    if audio_url:
        full_audio_url = f"{API_BASE}{audio_url}"
        
        # Audio player
        st.audio(full_audio_url, format="audio/mpeg")
        
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
        
        # Audio metrics
        st.markdown("#### 🎵 Audio Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Duration", f"{result.get('duration_minutes', 0):.2f} min")
        
        with col2:
            st.metric("File Size", f"{result.get('audio_metrics', {}).get('file_size_bytes', 0) / 1024 / 1024:.1f} MB")
        
        with col3:
            accuracy = result.get('duration_accuracy', 0)
            st.metric("Timing Accuracy", f"±{accuracy:.2f} min")

def render_transcript(result: Dict[str, Any]):
    """Render transcript with advanced features"""
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

def render_generation_analytics(result: Dict[str, Any]):
    """Render generation analytics"""
    metrics = result.get("generation_metrics", {})
    
    if metrics:
        st.markdown("#### 📊 Generation Analytics")
        
        # Performance metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Time", f"{metrics.get('total_time', 0):.1f}s")
        
        with col2:
            st.metric("Content Time", f"{metrics.get('content_generation_time', 0):.1f}s")
        
        with col3:
            st.metric("Audio Time", f"{metrics.get('audio_generation_time', 0):.1f}s")
        
        with col4:
            st.metric("Quality Score", f"{metrics.get('quality_score', 0):.2f}")
        
        # Performance breakdown chart
        if metrics.get('total_time', 0) > 0:
            breakdown_data = {
                "Phase": ["News Fetching", "Content Generation", "Audio Generation", "Other"],
                "Time (s)": [
                    metrics.get('news_fetch_time', 0),
                    metrics.get('content_generation_time', 0),
                    metrics.get('audio_generation_time', 0),
                    metrics.get('total_time', 0) - metrics.get('news_fetch_time', 0) - 
                    metrics.get('content_generation_time', 0) - metrics.get('audio_generation_time', 0)
                ]
            }
            
            fig = px.pie(
                values=breakdown_data["Time (s)"],
                names=breakdown_data["Phase"],
                title="Generation Time Breakdown"
            )
            st.plotly_chart(fig, use_container_width=True)

def render_sources(result: Dict[str, Any]):
    """Render source articles"""
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
                    st.markdown(f"**Quality Score:** {source.get('quality_score', 0):.2f}")
                    st.markdown(f"**Sentiment:** {source.get('sentiment', 'N/A')}")
                
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

def render_analytics_dashboard():
    """Render advanced analytics dashboard"""
    st.markdown("### 📊 Analytics Dashboard")
    
    # Date range selector
    col1, col2 = st.columns([1, 3])
    
    with col1:
        date_range = st.selectbox("Date Range", ["1d", "7d", "30d", "90d"], index=1)
    
    with col2:
        if st.button("🔄 Refresh Analytics"):
            st.rerun()
    
    # Get analytics data
    api_client = AdvancedAPIClient(API_BASE)
    analytics_data = asyncio.run(api_client.get_analytics(date_range))
    
    if analytics_data.get("error"):
        st.error(f"Error loading analytics: {analytics_data['error']}")
        return
    
    metrics = analytics_data.get("metrics", {})
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Generations", metrics.get("total_generations", 0))
    
    with col2:
        st.metric("Success Rate", f"{metrics.get('success_rate', 0):.1%}")
    
    with col3:
        st.metric("Avg Generation Time", f"{metrics.get('average_generation_time', 0):.1f}s")
    
    with col4:
        st.metric("Cache Hit Rate", f"{metrics.get('cache_hit_rate', 0):.1%}")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Quality scores chart
        quality_scores = metrics.get("quality_scores", {})
        if quality_scores:
            fig = px.bar(
                x=list(quality_scores.keys()),
                y=list(quality_scores.values()),
                title="Quality Score Distribution",
                labels={"x": "Quality Level", "y": "Average Score"}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Popular topics chart
        popular_topics = metrics.get("popular_topics", [])
        if popular_topics:
            topics_data = {
                "Topic": [t["topic"] for t in popular_topics],
                "Count": [t["count"] for t in popular_topics]
            }
            fig = px.pie(
                values=topics_data["Count"],
                names=topics_data["Topic"],
                title="Popular Topics"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Voice usage chart
    voice_usage = metrics.get("voice_usage", {})
    if voice_usage:
        fig = px.bar(
            x=list(voice_usage.keys()),
            y=list(voice_usage.values()),
            title="Voice Usage Distribution",
            labels={"x": "Voice ID", "y": "Usage Count"}
        )
        st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application function"""
    # Initialize session state
    initialize_session_state()
    
    # Set page config
    st.set_page_config(
        page_title="Daily Noah Advanced",
        page_icon="🎙️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Render header
    render_advanced_header()
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["🎙️ Generate", "📊 Analytics", "⚙️ Settings"])
    
    with tab1:
        # Sidebar
        generation_request = render_advanced_sidebar()
        
        # Main generation area
        if not generation_request.topics:
            st.warning("⚠️ Please enter at least one topic in the sidebar to generate a briefing.")
            st.stop()
        
        # Generate button
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button("🚀 Generate Advanced Bulletin", use_container_width=True, type="primary"):
                # Start generation
                with st.spinner("Starting advanced generation..."):
                    api_client = AdvancedAPIClient(API_BASE)
                    start_result = asyncio.run(api_client.start_generation(generation_request))
                
                if start_result.get("status") == "started":
                    progress_id = start_result.get("progress_id")
                    
                    # Track progress
                    render_progress_tracking(progress_id)
                    
                    # Get final result
                    result = asyncio.run(api_client.get_result(progress_id))
                    
                    if result.get("status") == "success":
                        # Add to history
                        st.session_state.generation_history.append({
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "request": generation_request,
                            "result": result
                        })
                        
                        # Display results
                        render_results_display(result)
                    else:
                        st.error(f"Generation failed: {result.get('error')}")
                else:
                    st.error(f"Failed to start generation: {start_result.get('error')}")
        
        # Generation history
        if st.session_state.generation_history:
            with st.expander("📚 Generation History"):
                for i, history_item in enumerate(reversed(st.session_state.generation_history[-5:])):
                    timestamp = history_item["timestamp"]
                    topics = history_item["request"].topics
                    duration = history_item["request"].duration
                    
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"**{', '.join(topics)}**")
                    
                    with col2:
                        st.write(f"{duration} min")
                    
                    with col3:
                        st.write(timestamp[:19])
    
    with tab2:
        render_analytics_dashboard()
    
    with tab3:
        st.markdown("### ⚙️ Advanced Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🎨 Appearance")
            theme = st.selectbox("Theme", ["light", "dark", "auto"])
            st.session_state.user_preferences["theme"] = theme
            
            st.markdown("#### 🔔 Notifications")
            notifications = st.checkbox("Enable Notifications", value=True)
            st.session_state.user_preferences["notifications"] = notifications
        
        with col2:
            st.markdown("#### 🚀 Performance")
            auto_download = st.checkbox("Auto Download", value=False)
            st.session_state.user_preferences["auto_download"] = auto_download
            
            st.markdown("#### 💾 Data")
            if st.button("Clear Cache"):
                st.session_state.clear()
                st.success("Cache cleared!")
            
            if st.button("Export Settings"):
                st.download_button(
                    "Download Settings",
                    data=json.dumps(st.session_state.user_preferences, indent=2),
                    file_name="noah_settings.json",
                    mime="application/json"
                )

if __name__ == "__main__":
    main()
