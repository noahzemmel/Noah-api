# server.py - Render Deployment Server (Perfect Timing)
"""
🎯 DAILY NOAH PERFECT TIMING SERVER FOR RENDER

GUARANTEED SOLUTIONS:
1. 🎯 EXACT TIMING - Iterative verification until duration matches EXACTLY
   - Generates audio, measures actual duration, adjusts if needed
   - Repeats up to 3 times until within ±5 seconds
   
2. 📰 COMPREHENSIVE DEPTH - 15-20 articles for in-depth coverage
   - Multiple queries per topic for breadth
   - Full article content (no truncation)
   
3. ⚡ FAST GENERATION - Optimized to complete in <60 seconds
   - Parallel news fetching
   - Fast timeouts
   - Efficient processing

This is the main server file that Render will use for deployment.
"""

# Import the perfect timing server
from server_perfect_timing import app

# This makes the app available for Render deployment
__all__ = ["app"]