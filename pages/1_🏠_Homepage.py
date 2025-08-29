# pages/1_🏠_Homepage.py - Daily Noah homepage with authentication
import streamlit as st
from auth_service import AuthService
import json

# Initialize auth service
@st.cache_resource
def get_auth_service():
    return AuthService()

def show_homepage():
    """Show the main homepage with authentication options"""
    
    # Page configuration
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
                    st.success("Login successful! Redirecting to your dashboard...")
                    # Redirect to main app
                    st.switch_page("app.py")
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

# Main execution
show_homepage()
