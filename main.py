# main.py - Main entry point for Daily Noah multi-page app
import streamlit as st
from homepage import show_homepage
from app import show_noah_interface

# Page configuration
st.set_page_config(
    page_title="Daily Noah - AI-Powered News Briefings",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def main():
    """Main routing function"""
    
    # Check if user is authenticated
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    # Route to appropriate page
    if st.session_state.authenticated:
        # User is logged in, show Noah interface
        show_noah_interface()
    else:
        # User is not logged in, show homepage
        show_homepage()

if __name__ == "__main__":
    main()
