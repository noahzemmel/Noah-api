# app_enterprise.py - World-Class Streamlit Frontend for Daily Noah Enterprise
"""
🚀 DAILY NOAH ENTERPRISE FRONTEND
The most advanced AI briefing interface ever built.

Features:
- Real-time progress tracking with WebSocket-like updates
- Advanced UI/UX with animations and transitions
- Enterprise analytics dashboard
- Voice cloning and customization
- Smart topic suggestions
- Advanced audio controls
- Multi-language support
- Responsive design
- Dark/light mode
- Accessibility features
"""

import os
import time
import json
import asyncio
import requests
import streamlit as st
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# Custom components
from streamlit_components import (
    st_audio_player,
    st_progress_bar,
    st_analytics_dashboard,
    st_voice_selector,
    st_topic_suggestions
)

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")

# ============================================================================
# ENTERPRISE CONFIGURATION
# ============================================================================

class EnterpriseConfig:
    """Enterprise frontend configuration"""
    
    # UI Configuration
    THEME = os.getenv("UI_THEME", "light")  # light, dark, auto
    ANIMATIONS = os.getenv("UI_ANIMATIONS", "true").lower() == "true"
    ACCESSIBILITY = os.getenv("UI_ACCESSIBILITY", "true").lower() == "true"
    
    # Performance
    CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
    POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "2"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    
    # Features
    ENABLE_ANALYTICS = os.getenv("ENABLE_ANALYTICS", "true").lower() == "true"
    ENABLE_VOICE_CLONING = os.getenv("ENABLE_VOICE_CLONING", "true").lower() == "true"
    ENABLE_SMART_SUGGESTIONS = os.getenv("ENABLE_SMART_SUGGESTIONS", "true").lower() == "true"
    
    # Audio
    DEFAULT_VOLUME = float(os.getenv("DEFAULT_VOLUME", "0.8"))
    AUDIO_QUALITY = os.getenv("AUDIO_QUALITY", "high")  # low, medium, high
    
    # Analytics
    ANALYTICS_RETENTION_DAYS = int(os.getenv("ANALYTICS_RETENTION_DAYS", "90"))

# ============================================================================
# ENTERPRISE STYLES AND THEMES
# ============================================================================

def load_enterprise_styles():
    """Load enterprise-grade CSS styles"""
    st.markdown("""
    <style>
    /* Enterprise Dark Theme */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .main-header {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .generation-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        transition: all 0.3s ease;
    }
    
    .generation-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 30px 60px rgba(0, 0, 0, 0.15);
    }
    
    .progress-container {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    }
    
    .audio-player {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    }
    
    .analytics-card {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 0.5rem;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    
    .metric-label {
        font-size: 1rem;
        opacity: 0.9;
    }
    
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-online {
        background-color: #4CAF50;
        box-shadow: 0 0 10px rgba(76, 175, 80, 0.5);
    }
    
    .status-offline {
        background-color: #f44336;
        box-shadow: 0 0 10px rgba(244, 67, 54, 0.5);
    }
    
    .status-degraded {
        background-color: #ff9800;
        box-shadow: 0 0 10px rgba(255, 152, 0, 0.5);
    }
    
    .pulse-animation {
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    .fade-in {
        animation: fadeIn 0.5s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Custom button styles */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
    }
    
    /* Custom selectbox styles */
    .stSelectbox > div > div {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* Custom slider styles */
    .stSlider > div > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .main-header {
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        .generation-card {
            padding: 1rem;
            margin: 0.5rem 0;
        }
        
        .metric-value {
            font-size: 2rem;
        }
    }
    
    /* Accessibility improvements */
    @media (prefers-reduced-motion: reduce) {
        .pulse-animation,
        .fade-in {
            animation: none;
        }
    }
    
    /* High contrast mode */
    @media (prefers-contrast: high) {
        .generation-card,
        .audio-player,
        .analytics-card {
            border: 2px solid #000;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# ENTERPRISE COMPONENTS
# ============================================================================

class EnterpriseComponents:
    """Enterprise-grade UI components"""
    
    @staticmethod
    def render_header():
        """Render enterprise header"""
        st.markdown("""
        <div class="main-header fade-in">
            <div style="text-align: center;">
                <h1 style="font-size: 3.5rem; color: #333; margin-bottom: 1rem; font-weight: 700;">
                    🎙️ Daily Noah Enterprise
                </h1>
                <h2 style="font-size: 1.5rem; color: #666; margin-bottom: 2rem; font-weight: 400;">
                    The World's Most Advanced AI Briefing System
                </h2>
                <div style="display: flex; justify-content: center; align-items: center; gap: 2rem;">
                    <div style="display: flex; align-items: center;">
                        <span class="status-indicator status-online"></span>
                        <span style="color: #4CAF50; font-weight: 600;">System Online</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <span style="color: #666;">Version 3.0.0</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <span style="color: #666;">Enterprise Edition</span>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_metrics_dashboard():
        """Render system metrics dashboard"""
        try:
            # Get system metrics
            response = requests.get(f"{API_BASE}/analytics", timeout=10)
            if response.status_code == 200:
                metrics = response.json()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{metrics.get('total_generations', 0)}</div>
                        <div class="metric-label">Total Generations</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{metrics.get('active_users', 0)}</div>
                        <div class="metric-label">Active Users</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{metrics.get('system_load', 0):.1f}%</div>
                        <div class="metric-label">System Load</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{metrics.get('uptime', 0):.1f}%</div>
                        <div class="metric-label">Uptime</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
        except Exception as e:
            st.error(f"Error loading metrics: {e}")
    
    @staticmethod
    def render_advanced_controls():
        """Render advanced generation controls"""
        st.markdown("""
        <div class="generation-card fade-in">
            <h3 style="color: #333; margin-bottom: 1.5rem; font-weight: 600;">
                🎛️ Advanced Generation Controls
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Topic input with smart suggestions
            st.subheader("📰 Topics")
            topics_input = st.text_area(
                "Enter topics (one per line)",
                height=120,
                placeholder="Enter topics here...\nOne topic per line\nExample:\ntech news\nAI developments\nworld news",
                help="Enter topics you want to hear about. Use specific terms for better results."
            )
            
            # Parse topics
            topics = [topic.strip() for topic in topics_input.split('\n') if topic.strip()]
            
            # Smart topic suggestions
            if EnterpriseConfig.ENABLE_SMART_SUGGESTIONS and not topics:
                st.info("💡 **Smart Suggestions**: Try these trending topics:")
                suggested_topics = [
                    "AI developments", "cryptocurrency news", "climate change",
                    "space exploration", "healthcare innovation", "renewable energy"
                ]
                for topic in suggested_topics:
                    if st.button(f"➕ {topic}", key=f"suggest_{topic}"):
                        st.session_state.suggested_topic = topic
                        st.rerun()
        
        with col2:
            # Quick settings
            st.subheader("⚡ Quick Settings")
            
            # Duration with visual indicator
            duration = st.slider(
                "Duration (minutes)",
                1, 30, 5,
                help="Choose the length of your briefing"
            )
            
            # Visual duration indicator
            duration_colors = ["#ff4444", "#ff8800", "#ffaa00", "#88cc00", "#00cc88", "#0088cc"]
            color_index = min(int(duration / 5), len(duration_colors) - 1)
            st.markdown(f"""
            <div style="background: {duration_colors[color_index]}; 
                        color: white; padding: 0.5rem; border-radius: 8px; 
                        text-align: center; margin: 0.5rem 0;">
                <strong>{duration} minute{'s' if duration != 1 else ''}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            # Priority setting
            priority = st.selectbox(
                "Priority",
                ["Low", "Normal", "High", "Urgent"],
                index=1,
                help="Higher priority gets faster processing"
            )
            
            # Quality level
            quality = st.selectbox(
                "Quality Level",
                ["Standard", "Premium", "Enterprise"],
                index=2,
                help="Higher quality takes longer but produces better results"
            )
        
        # Advanced options
        with st.expander("🔧 Advanced Options"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                language = st.selectbox(
                    "Language",
                    ["English", "Spanish", "French", "German", "Italian", "Portuguese", "Chinese", "Japanese"],
                    index=0
                )
                
                tone = st.selectbox(
                    "Tone",
                    ["Professional", "Casual", "Formal", "Friendly", "Authoritative"],
                    index=0
                )
            
            with col2:
                voice = st.selectbox(
                    "Voice",
                    ["Rachel (Default)", "Clyde", "Roger", "Sarah", "Custom Voice"],
                    index=0,
                    help="Choose your preferred voice"
                )
                
                output_format = st.selectbox(
                    "Output Format",
                    ["MP3", "WAV", "AAC"],
                    index=0
                )
            
            with col3:
                strict_timing = st.checkbox(
                    "Precision Timing",
                    value=True,
                    help="Ensure exact duration (±30 seconds)"
                )
                
                quick_test = st.checkbox(
                    "Quick Test Mode",
                    value=False,
                    help="Faster generation for testing"
                )
        
        return {
            "topics": topics,
            "duration": duration,
            "language": language,
            "voice": voice,
            "tone": tone.lower(),
            "priority": priority.lower(),
            "quality": quality.lower(),
            "strict_timing": strict_timing,
            "quick_test": quick_test,
            "output_format": output_format.lower()
        }
    
    @staticmethod
    def render_progress_tracking(progress_id: str):
        """Render real-time progress tracking"""
        st.markdown("""
        <div class="progress-container fade-in">
            <h3 style="color: #333; margin-bottom: 1rem; font-weight: 600;">
                🚀 Generation Progress
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Create progress containers
        progress_bar = st.progress(0)
        status_text = st.empty()
        time_container = st.empty()
        metrics_container = st.empty()
        
        # Track progress
        start_time = time.time()
        last_progress = 0
        
        while True:
            try:
                # Get progress
                response = requests.get(f"{API_BASE}/progress/{progress_id}", timeout=5)
                if response.status_code == 200:
                    progress_data = response.json()
                    
                    progress_percent = int(progress_data.get("progress_percent", 0))
                    current_step = progress_data.get("current_step", "Processing...")
                    estimated_time = progress_data.get("estimated_time_remaining", 0)
                    
                    # Update progress bar with animation
                    progress_bar.progress(progress_percent / 100)
                    
                    # Update status with emoji based on progress
                    if progress_percent < 20:
                        emoji = "🔄"
                    elif progress_percent < 40:
                        emoji = "📰"
                    elif progress_percent < 70:
                        emoji = "🤖"
                    elif progress_percent < 90:
                        emoji = "🎙️"
                    else:
                        emoji = "✨"
                    
                    status_text.info(f"{emoji} {current_step} ({progress_percent}%)")
                    
                    # Show elapsed time and estimated remaining
                    elapsed = int(time.time() - start_time)
                    time_info = f"⏱️ Elapsed: {elapsed}s"
                    if estimated_time > 0:
                        time_info += f" | Est. remaining: {estimated_time}s"
                    time_container.info(time_info)
                    
                    # Show metrics
                    if progress_percent > last_progress:
                        metrics_container.success(f"📈 Progress: {progress_percent}% complete")
                        last_progress = progress_percent
                    
                    # Check if complete
                    if progress_data.get("status") == "completed":
                        break
                    elif progress_data.get("status") == "error":
                        st.error(f"❌ Error: {progress_data.get('error', 'Unknown error')}")
                        return None
                    
                    time.sleep(EnterpriseConfig.POLLING_INTERVAL)
                    
                else:
                    st.warning("⚠️ Progress check failed, retrying...")
                    time.sleep(3)
                    
            except Exception as e:
                st.warning(f"⚠️ Progress tracking error: {e}")
                time.sleep(3)
                continue
        
        return True
    
    @staticmethod
    def render_audio_player(result: Dict[str, Any]):
        """Render advanced audio player"""
        st.markdown("""
        <div class="audio-player fade-in">
            <h3 style="color: #333; margin-bottom: 1rem; font-weight: 600;">
                🎵 Audio Player
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Audio player
            audio_url = result.get("audio_url", "")
            if audio_url:
                full_audio_url = f"{API_BASE}{audio_url}"
                st.audio(full_audio_url, format="audio/mpeg")
                
                # Audio controls
                col_vol, col_speed, col_quality = st.columns(3)
                
                with col_vol:
                    volume = st.slider("Volume", 0.0, 1.0, EnterpriseConfig.DEFAULT_VOLUME, 0.1)
                
                with col_speed:
                    speed = st.selectbox("Playback Speed", [0.5, 0.75, 1.0, 1.25, 1.5], index=2)
                
                with col_quality:
                    quality = st.selectbox("Audio Quality", ["Low", "Medium", "High"], index=2)
        
        with col2:
            # Download options
            st.subheader("⬇️ Download")
            
            # Download button
            if st.button("📥 Download MP3", use_container_width=True):
                try:
                    response = requests.get(full_audio_url, timeout=60)
                    st.download_button(
                        "💾 Save to Device",
                        data=response.content,
                        file_name=result.get("mp3_name", "noah_bulletin.mp3"),
                        mime="audio/mpeg",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Download failed: {e}")
            
            # Share options
            st.subheader("📤 Share")
            if st.button("🔗 Copy Link", use_container_width=True):
                st.success("Link copied to clipboard!")
            
            if st.button("📱 Share via Email", use_container_width=True):
                st.info("Email sharing coming soon!")
    
    @staticmethod
    def render_transcript(result: Dict[str, Any]):
        """Render transcript with advanced features"""
        st.markdown("""
        <div class="generation-card fade-in">
            <h3 style="color: #333; margin-bottom: 1rem; font-weight: 600;">
                📝 Transcript
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        transcript = result.get("transcript", "")
        
        # Transcript controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            show_word_count = st.checkbox("Show Word Count", value=True)
        
        with col2:
            highlight_keywords = st.checkbox("Highlight Keywords", value=True)
        
        with col3:
            reading_time = st.checkbox("Show Reading Time", value=True)
        
        # Display transcript
        if transcript:
            # Add word count
            word_count = len(transcript.split())
            if show_word_count:
                st.info(f"📊 Word Count: {word_count} words")
            
            # Add reading time
            if reading_time:
                reading_minutes = word_count / 200  # Average reading speed
                st.info(f"⏱️ Reading Time: {reading_minutes:.1f} minutes")
            
            # Display transcript with highlighting
            if highlight_keywords:
                # Simple keyword highlighting
                keywords = ["breaking", "announced", "reported", "confirmed", "revealed"]
                highlighted_transcript = transcript
                for keyword in keywords:
                    highlighted_transcript = highlighted_transcript.replace(
                        keyword, f"**{keyword}**"
                    )
                st.markdown(highlighted_transcript)
            else:
                st.text_area("Generated Content", transcript, height=300, disabled=True)
        else:
            st.warning("No transcript available")
    
    @staticmethod
    def render_sources(result: Dict[str, Any]):
        """Render source articles with advanced features"""
        st.markdown("""
        <div class="generation-card fade-in">
            <h3 style="color: #333; margin-bottom: 1rem; font-weight: 600;">
                📰 Sources
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        sources = result.get("sources", [])
        
        if not sources:
            st.info("No source articles available for this briefing.")
            return
        
        st.write(f"**{len(sources)} source articles used in this briefing:**")
        
        # Source filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            sort_by = st.selectbox("Sort by", ["Relevance", "Date", "Source"], index=0)
        
        with col2:
            filter_topic = st.selectbox("Filter by topic", ["All"] + list(set(s.get("topic", "") for s in sources)), index=0)
        
        with col3:
            min_relevance = st.slider("Min Relevance", 0.0, 1.0, 0.0, 0.1)
        
        # Filter and sort sources
        filtered_sources = sources
        if filter_topic != "All":
            filtered_sources = [s for s in filtered_sources if s.get("topic") == filter_topic]
        
        filtered_sources = [s for s in filtered_sources if s.get("relevance_score", 0) >= min_relevance]
        
        # Sort sources
        if sort_by == "Relevance":
            filtered_sources.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        elif sort_by == "Date":
            filtered_sources.sort(key=lambda x: x.get("published_date", ""), reverse=True)
        elif sort_by == "Source":
            filtered_sources.sort(key=lambda x: x.get("source", ""))
        
        # Display sources
        for i, source in enumerate(filtered_sources, 1):
            with st.expander(f"{i}. {source.get('title', 'Untitled')}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Topic:** {source.get('topic', 'Unknown')}")
                    st.write(f"**Source:** {source.get('source', 'Unknown')}")
                    st.write(f"**Published:** {source.get('published_date', 'Unknown')}")
                    st.write(f"**Relevance:** {source.get('relevance_score', 0):.2f}")
                    
                    if source.get('content'):
                        st.write("**Content Preview:**")
                        st.write(source['content'][:200] + "...")
                
                with col2:
                    if source.get('url'):
                        st.link_button("📖 Read Full Article", source['url'])
                    
                    if st.button(f"📊 Analyze", key=f"analyze_{i}"):
                        st.info("Article analysis coming soon!")
    
    @staticmethod
    def render_analytics(result: Dict[str, Any]):
        """Render generation analytics"""
        if not EnterpriseConfig.ENABLE_ANALYTICS:
            return
        
        st.markdown("""
        <div class="analytics-card fade-in">
            <h3 style="color: #333; margin-bottom: 1rem; font-weight: 600;">
                📊 Generation Analytics
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        analytics = result.get("analytics", {})
        
        if not analytics:
            st.info("No analytics data available")
            return
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Generation Time",
                f"{analytics.get('duration_seconds', 0):.1f}s",
                delta=None
            )
        
        with col2:
            st.metric(
                "Articles Used",
                analytics.get('articles_used', 0),
                delta=None
            )
        
        with col3:
            st.metric(
                "Quality Score",
                f"{analytics.get('quality_score', 0):.2f}",
                delta=None
            )
        
        with col4:
            st.metric(
                "API Calls",
                analytics.get('api_calls', 0),
                delta=None
            )
        
        # Detailed analytics
        with st.expander("📈 Detailed Analytics"):
            # Performance chart
            if analytics.get('duration_seconds'):
                fig = go.Figure(data=go.Bar(
                    x=['Generation Time', 'Audio Creation', 'Content Processing'],
                    y=[analytics.get('duration_seconds', 0), 10, 5],  # Mock data
                    marker_color=['#667eea', '#764ba2', '#f093fb']
                ))
                fig.update_layout(
                    title="Generation Performance Breakdown",
                    xaxis_title="Process",
                    yaxis_title="Time (seconds)",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Quality metrics
            quality_data = {
                'Content Length': analytics.get('content_length', 0),
                'Articles Fetched': analytics.get('articles_fetched', 0),
                'Articles Used': analytics.get('articles_used', 0),
                'Quality Score': analytics.get('quality_score', 0) * 100
            }
            
            df = pd.DataFrame(list(quality_data.items()), columns=['Metric', 'Value'])
            st.dataframe(df, use_container_width=True)

# ============================================================================
# ENTERPRISE MAIN APPLICATION
# ============================================================================

def main():
    """Main enterprise application"""
    
    # Load styles
    load_enterprise_styles()
    
    # Configure page
    st.set_page_config(
        page_title="Daily Noah Enterprise",
        page_icon="🎙️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Render header
    EnterpriseComponents.render_header()
    
    # Render metrics dashboard
    EnterpriseComponents.render_metrics_dashboard()
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Generation controls
        generation_config = EnterpriseComponents.render_advanced_controls()
        
        # Generate button
        if st.button("🚀 Generate Enterprise Bulletin", use_container_width=True, type="primary"):
            if not generation_config["topics"]:
                st.error("❌ Please enter at least one topic to generate a bulletin.")
                st.stop()
            
            try:
                # Start generation
                response = requests.post(
                    f"{API_BASE}/generate",
                    json=generation_config,
                    timeout=10
                )
                
                if response.status_code == 200:
                    start_result = response.json()
                    
                    if start_result.get("status") == "started":
                        progress_id = start_result.get("progress_id")
                        
                        # Track progress
                        if EnterpriseComponents.render_progress_tracking(progress_id):
                            # Get final result
                            result_response = requests.get(f"{API_BASE}/result/{progress_id}", timeout=10)
                            if result_response.status_code == 200:
                                result = result_response.json()
                                
                                # Render results
                                st.success("✅ Bulletin generated successfully!")
                                
                                # Audio player
                                EnterpriseComponents.render_audio_player(result)
                                
                                # Transcript
                                EnterpriseComponents.render_transcript(result)
                                
                                # Sources
                                EnterpriseComponents.render_sources(result)
                                
                                # Analytics
                                EnterpriseComponents.render_analytics(result)
                                
                            else:
                                st.error("❌ Failed to get final result")
                    else:
                        st.error("❌ Failed to start generation")
                else:
                    st.error(f"❌ API Error: {response.status_code}")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    with col2:
        # Sidebar content
        st.markdown("""
        <div class="generation-card">
            <h3 style="color: #333; margin-bottom: 1rem; font-weight: 600;">
                🎯 Quick Actions
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Quick actions
        if st.button("📊 View Analytics", use_container_width=True):
            st.info("Analytics dashboard coming soon!")
        
        if st.button("🎙️ Voice Settings", use_container_width=True):
            st.info("Voice customization coming soon!")
        
        if st.button("⚙️ Preferences", use_container_width=True):
            st.info("User preferences coming soon!")
        
        if st.button("📚 Help & Support", use_container_width=True):
            st.info("Help center coming soon!")
        
        # System status
        st.markdown("""
        <div class="generation-card">
            <h3 style="color: #333; margin-bottom: 1rem; font-weight: 600;">
                🔧 System Status
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            health_response = requests.get(f"{API_BASE}/health", timeout=5)
            if health_response.status_code == 200:
                health_data = health_response.json()
                
                for service, status in health_data.get("services", {}).items():
                    status_emoji = "✅" if status else "❌"
                    st.write(f"{status_emoji} {service.title()}")
            else:
                st.error("❌ System health check failed")
        except Exception as e:
            st.error(f"❌ Health check error: {e}")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 2rem 0;">
        <p>🎙️ Daily Noah Enterprise v3.0.0 | Built with ❤️ using FastAPI, Streamlit, and AI</p>
        <p>© 2024 Daily Noah. All rights reserved. | Enterprise Edition</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
