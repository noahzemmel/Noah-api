# server.py - Render Deployment Server (Lightning Fast)
"""
⚡ DAILY NOAH LIGHTNING SERVER FOR RENDER
The fastest, most reliable AI briefing generation system.

This is the main server file that Render will use for deployment.
It imports and uses the lightning-fast core system.
"""

# Import the lightning-fast server
from server_lightning import app

# This makes the app available for Render deployment
__all__ = ["app"]