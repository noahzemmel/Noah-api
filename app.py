# app.py — Streamlit UI for Noah MVP with Authentication
import os, time, json, requests, streamlit as st
from auth_service import AuthService

# Configuration - Use the deployed backend URL
API_BASE = os.getenv("API_BASE", "https://noah-api-t6wj.onrender.com").rstrip("/")

# Initialize auth service
@st.cache_resource
def get_auth_service():
    return AuthService()

def check_authentication():
    """Check if user is authenticated"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    return st.session_state.authenticated

def show_homepage():
    """Show the homepage when user is not authenticated"""
    st.set_page_config(
        page_title="Daily Noah - AI-Powered News Briefings",
        page_icon="🎙️",
        layout="wide"
    )
    
    # Header
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 3.5rem; color: #1f77b4; margin-bottom: 1rem;">🎙️ Daily Noah</h1>
        <h2 style="font-size: 2rem; color: #666; margin-bottom: 2rem;">AI-Powered News Briefings, Perfectly Timed</h2>
        <p style="font-size: 1.2rem; color: #888; max-width: 600px; margin: 0 auto;">
            Get personalized news bulletins in your language, your voice, exactly when you want them. 
            Perfect for busy professionals who need to stay informed without the noise.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🚀 How It Works")
        st.markdown("""
        1. **Choose Your Topics** - Select what interests you most
        2. **Set Your Duration** - 1-15 minutes, perfectly timed
        3. **Pick Your Voice** - Choose from premium AI voices
        4. **Get Your Briefing** - AI-generated, human-quality news
        """)
        
        st.markdown("### ✨ Key Features")
        st.markdown("""
        - 🎯 **Perfect Timing** - Exactly the duration you request
        - 🌍 **Multi-Language** - English, Spanish, French, German, Italian
        - 🎙️ **Premium Voices** - Professional AI voices from ElevenLabs
        - 📰 **Recent News** - Latest updates from the last 24 hours
        - 📱 **Mobile Ready** - Works perfectly on all devices
        """)
    
    with col2:
        st.markdown("### 💎 Subscription Plans")
        
        # Free Plan
        with st.container():
            st.markdown("#### 🆓 Free Plan")
            st.markdown("**£0/month**")
            st.markdown("""
            - ✅ Generate news briefings
            - ✅ Basic voice options
            - ✅ Standard timing accuracy
            - ❌ Ad-supported experience
            - ❌ No downloads
            - ❌ Limited customization
            """)
        
        # Premium Plan
        with st.container():
            st.markdown("#### 💎 Premium Plan")
            st.markdown("**£7.99/month**")
            st.markdown("""
            - ✅ **Everything in Free**
            - ✅ **Ad-free experience**
            - ✅ **Fast downloads** (10x faster)
            - ✅ **All premium voices**
            - ✅ **Advanced customization**
            - ✅ **Priority processing**
            - ✅ **Export options**
            """)
            
            st.button("🚀 Upgrade to Premium", use_container_width=True, type="primary")
    
    # Authentication Section
    st.markdown("---")
    st.markdown("### 🔐 Get Started")
    
    # Tabs for login/signup
    tab1, tab2 = st.tabs(["📝 Sign Up", "🔑 Log In"])
    
    with tab1:
        st.markdown("#### Create Your Account")
        with st.form("signup_form"):
            email = st.text_input("Email Address", placeholder="your@email.com")
            password = st.text_input("Password", type="password", placeholder="Choose a strong password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                agree_terms = st.checkbox("I agree to the Terms of Service")
            with col2:
                agree_privacy = st.checkbox("I agree to the Privacy Policy")
            
            submitted = st.form_submit_button("Create Account", use_container_width=True)
            
            if submitted:
                if password != confirm_password:
                    st.error("Passwords don't match!")
                elif not agree_terms or not agree_privacy:
                    st.error("Please agree to the terms and privacy policy")
                elif len(password) < 8:
                    st.error("Password must be at least 8 characters long")
                else:
                    auth_service = get_auth_service()
                    result = auth_service.register_user(email, password)
                    if result["success"]:
                        st.success("Account created successfully! Please log in.")
                    else:
                        st.error(result["error"])
    
    with tab2:
        st.markdown("#### Welcome Back")
        with st.form("login_form"):
            login_email = st.text_input("Email Address", key="login_email", placeholder="your@email.com")
            login_password = st.text_input("Password", type="password", key="login_password", placeholder="Your password")
            
            submitted_login = st.form_submit_button("Log In", use_container_width=True)
            
            if submitted_login:
                auth_service = get_auth_service()
                result = auth_service.login_user(login_email, login_password)
                if result["success"]:
                    # Store session in session state
                    st.session_state.authenticated = True
                    st.session_state.user = result["user"]
                    st.session_state.session_token = result["session_token"]
                    st.session_state.subscription = result["subscription"]
                    st.success("Login successful! Welcome to Daily Noah!")
                    st.rerun()
                else:
                    st.error(result["error"])
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0; color: #666;">
        <p>© 2024 Daily Noah. All rights reserved.</p>
        <p>Built with ❤️ using AI, FastAPI, and Streamlit</p>
    </div>
    """, unsafe_allow_html=True)

def show_user_header():
    """Show user information and subscription status"""
    user = st.session_state.get("user", {})
    subscription = st.session_state.get("subscription", {})
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"### 👋 Welcome, {user.get('email', 'User')}")
    
    with col2:
        tier = subscription.get("tier", "free")
        if tier == "premium":
            st.success("💎 Premium User")
        else:
            st.info("🆓 Free User")
    
    with col3:
        if st.button("🚪 Logout"):
            # Logout user
            auth_service = get_auth_service()
            session_token = st.session_state.get("session_token")
            if session_token:
                auth_service.logout_user(session_token)
            
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            st.rerun()

def show_subscription_upgrade():
    """Show subscription upgrade prompt for free users"""
    subscription = st.session_state.get("subscription", {})
    
    if subscription.get("tier") == "free":
        with st.container():
            st.markdown("---")
            st.markdown("### 💎 Upgrade to Premium")
            st.markdown("""
            **Get the full Daily Noah experience:**
            - 🚫 **Ad-free** experience
            - ⬇ **Fast downloads** (10x faster)
            - 🎙️ **All premium voices**
            - ⚙️ **Advanced customization**
            - 🚀 **Priority processing**
            """)
            
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown("**Only £7.99/month**")
            with col2:
                if st.button("🚀 Upgrade Now", type="primary"):
                    st.info("Payment integration coming soon! For now, contact support to upgrade.")

def show_noah_interface():
    """Show the main Noah interface for authenticated users"""
    st.set_page_config(page_title="Noah — Daily Smart Bulletins", layout="wide")
    
    # Show user header
    show_user_header()
    
    # Show subscription upgrade prompt for free users
    show_subscription_upgrade()
    
    # Main Noah interface
    st.title("🎙️ Noah — Daily Smart Bulletins")
    st.caption(f"Generated news & insights in **your language**, **your voice**, **your time**.\n\nAPI: {API_BASE}")
    
    # Get user preferences
    auth_service = get_auth_service()
    user = st.session_state.get("user", {})
    user_prefs = auth_service.get_user_preferences(user.get("id", ""))
    
    with st.sidebar:
        st.subheader("🎯 Topics")
        topics_input = st.text_area(
            "Enter topics (one per line)", 
            value="\n".join(user_prefs.get("favorite_topics", ["tech news", "AI developments"])), 
            height=120, 
            placeholder="Enter topics here...\nOne topic per line\nExample:\ntech news\nAI developments\nworld news"
        )
        
        # Parse topics from text input
        topics = [topic.strip() for topic in topics_input.split('\n') if topic.strip()]
        
        st.subheader("🌍 Language")
        language = st.selectbox("Language", ["English", "Spanish", "French", "German", "Italian"], 
                               index=["English", "Spanish", "French", "German", "Italian"].index(user_prefs.get("default_language", "English")))
        
        st.subheader("🎙️ Voice")
        voices = fetch_voices()
        
        # Build options for selectbox
        def label(v: dict) -> str:
            name = v.get("name", "Unknown")
            accent = v.get("accent", "")
            return f"{name}" + (f" - {accent}" if accent else "")

        selected_voice = st.selectbox(
            "Voice", 
            options=voices, 
            index=0,
            format_func=label,
        )
        voice_id = selected_voice.get("id", user_prefs.get("default_voice", "21m00Tcm4TlvDq8ikWAM"))
        
        st.subheader("⏱️ Duration")
        duration = st.slider("Duration (minutes)", 1, 15, user_prefs.get("default_duration", 5))
        
        # Precision timing control
        strict_timing = st.checkbox("🎯 Enable Precision Timing", value=True, 
                                   help="When enabled, Noah will generate bulletins that are exactly the requested duration (±30 seconds)")
        
        # Quick test mode
        quick_test = st.checkbox("⚡ Quick Test Mode", value=False,
                                help="Enable for faster testing with reduced content (may affect timing precision)")

        st.subheader("🎨 Tone")
        tone = st.selectbox("Tone", ["professional", "friendly", "casual", "formal"], index=0)
        
        # Save preferences button
        if st.button("💾 Save Preferences"):
            new_prefs = {
                "default_language": language,
                "default_voice": voice_id,
                "default_duration": duration,
                "favorite_topics": topics
            }
            if auth_service.update_user_preferences(user.get("id", ""), new_prefs):
                st.success("Preferences saved!")
            else:
                st.error("Failed to save preferences")
    
    # Main content area
    status = st.empty()

    if not topics:
        st.warning("⚠️ Please enter at least one topic in the sidebar to generate a bulletin.")
        st.stop()

    run = st.button("🚀 Generate Bulletin", use_container_width=True, type="primary")

    if run:
        # Parse topics from the input (do this when button is clicked)
        topics_list = [topic.strip() for topic in topics_input.split('\n') if topic.strip()]
        
        if not topics_list:
            status.error("❌ Please enter at least one topic to generate a bulletin.")
            st.stop()
        
        try:
            # Create progress tracking UI
            progress_container = st.empty()
            progress_bar = st.progress(0)
            status_text = st.empty()
            time_container = st.empty()
            
            # Simulate progress steps
            progress_steps = [
                (10, "🔄 Initializing..."),
                (20, "📰 Fetching latest news..."),
                (40, "🤖 Generating script..."),
                (70, "🎙️ Creating audio..."),
                (90, "✨ Finalizing bulletin..."),
                (100, "✅ Complete!")
            ]
            
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
            
            # Start the API call in a thread (simplified approach)
            import threading
            import queue
            
            result_queue = queue.Queue()
            error_queue = queue.Queue()
            
            def make_api_call():
                try:
                    response = requests.post(f"{API_BASE}/generate", json=payload, timeout=300)
                    response.raise_for_status()
                    result_queue.put(response.json())
                except Exception as e:
                    error_queue.put(e)
            
            # Start API call
            api_thread = threading.Thread(target=make_api_call)
            api_thread.start()
            
            # Show progress while waiting
            start_time = time.time()
            step_index = 0
            
            while api_thread.is_alive():
                # Update progress
                if step_index < len(progress_steps):
                    progress_percent, step_text = progress_steps[step_index]
                    progress_bar.progress(progress_percent / 100)
                    status_text.info(step_text)
                    
                    # Show elapsed time
                    elapsed = int(time.time() - start_time)
                    time_container.info(f"⏱️ Elapsed time: {elapsed} seconds")
                    
                    # Move to next step every 10-15 seconds
                    if elapsed > (step_index + 1) * 12:
                        step_index += 1
                
                time.sleep(1)
            
            # Wait for result
            api_thread.join()
            
            # Get result or error
            if not result_queue.empty():
                result = result_queue.get()
            elif not error_queue.empty():
                raise error_queue.get()
            else:
                raise Exception("No result received from API")
            
            if result.get("status") == "success":
                status.success("✅ Bulletin generated successfully!")
                
                # Display results in a clean, focused layout
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.subheader("🎵 Audio Player")
                    audio_url = result.get("audio_url", "")
                    if audio_url:
                        # Construct full URL
                        full_audio_url = f"{API_BASE}{audio_url}"
                        st.audio(full_audio_url, format="audio/mpeg")
                        
                        # Download button (only for premium users)
                        subscription = st.session_state.get("subscription", {})
                        if subscription.get("tier") == "premium":
                            st.download_button(
                                "⬇ Download MP3",
                                data=requests.get(full_audio_url, timeout=60).content,
                                file_name=result.get("mp3_name", "noah_bulletin.mp3"),
                                mime="audio/mpeg",
                                use_container_width=True
                            )
                        else:
                            st.info("💎 **Premium Feature**: Download audio files by upgrading to Premium (£7.99/month)")
                    else:
                        st.warning("No audio generated.")
                
                with col2:
                    st.subheader("📝 Transcript")
                    transcript = result.get("transcript", "")
                    st.text_area("Generated Content", transcript, height=300, disabled=True)
                
                # Article sources below
                st.subheader("📰 Sources")
                srcs = result.get("sources", [])
                if not srcs:
                    st.info("No source articles available for this briefing.")
                else:
                    st.write(f"**{len(srcs)} source articles used in this briefing:**")
                    for i, s in enumerate(srcs, 1):
                        title = s.get("title", "")
                        url = s.get("url", "")
                        topic = s.get("topic", "")
                        
                        if title and url:
                            # Create a clean display with topic, title, and link
                            topic_display = f"**{topic}**" if topic else ""
                            st.markdown(f"{i}. {topic_display} **{title}**")
                            st.markdown(f"   [📖 Read Full Article]({url})")
                        elif url:
                            st.markdown(f"{i}. [📖 Read Article]({url})")
                        else:
                            st.write(f"{i}. Source information unavailable")
                
                # Show timing info in a subtle way
                with st.expander("⏱️ Timing Details"):
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
                    st.write(f"**Word Count:** {result.get('word_count', 0)} words")
                    
                    # Show news quality information
                    news_quality = result.get('news_quality', {})
                    if news_quality:
                        st.write("---")
                        st.write("**📰 News Quality Information**")
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
            
        except Exception as e:
            status.error(f"❌ Error: {str(e)}")
    else:
        # Show instructions when not generating
        st.info("🎯 Enter your topics in the sidebar and click 'Generate Bulletin' to get started!")
    
    # Footer
    st.markdown("---")
    st.caption("🎙️ Noah MVP - AI-powered news bulletins | Built with FastAPI, Streamlit, OpenAI, and ElevenLabs")

# Keep the existing fetch_voices function
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

# Main execution - check authentication and show appropriate interface
if __name__ == "__main__":
    if check_authentication():
        show_noah_interface()
    else:
        show_homepage()
