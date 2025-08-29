# noah_core_simple.py - Python 3.13 compatible version
import os
import io
import re
import math
import json
import time
import base64
import random
import requests
from typing import List, Dict, Tuple
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from dateutil import parser as dateparse
from openai import OpenAI

# Constants
ELEVEN_VOICES_URL = "https://api.elevenlabs.io/v1/voices"
OPENAI_MODEL = "gpt-4"
TAVILY_SEARCH_URL = "https://api.tavily.com/search"

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_available_voices():
    """Get available voices from ElevenLabs"""
    try:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            return {"voices": []}
        
        response = requests.get(ELEVEN_VOICES_URL, headers={"xi-api-key": api_key})
        if response.status_code == 200:
            voices_data = response.json()
            formatted_voices = []
            
            for voice in voices_data.get("voices", []):
                formatted_voice = {
                    "id": voice.get("voice_id"),
                    "name": voice.get("name", "Unknown"),
                    "provider": "elevenlabs",
                    "language": voice.get("labels", {}).get("language", "en"),
                    "accent": voice.get("labels", {}).get("accent", "neutral"),
                    "description": voice.get("labels", {}).get("description", "")
                }
                formatted_voices.append(formatted_voice)
            
            return {"voices": formatted_voices}
        else:
            # Fallback voices if API fails
            return {
                "voices": [
                    {
                        "id": "21m00Tcm4TlvDq8ikWAM",
                        "name": "Rachel",
                        "provider": "elevenlabs",
                        "language": "en",
                        "accent": "us",
                        "description": "Clear and engaging female voice"
                    }
                ]
            }
    except Exception as e:
        print(f"Error fetching voices: {e}")
        return {"voices": []}

def health_check():
    """Check health of all APIs"""
    results = {
        "openai": False,
        "elevenlabs": False,
        "tavily": False,
        "ok": False
    }
    
    # Check OpenAI
    try:
        client.models.list()
        results["openai"] = True
    except Exception as e:
        print(f"OpenAI health check failed: {e}")
    
    # Check ElevenLabs
    try:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if api_key:
            response = requests.get(ELEVEN_VOICES_URL, headers={"xi-api-key": api_key})
            results["elevenlabs"] = response.status_code == 200
    except Exception as e:
        print(f"ElevenLabs health check failed: {e}")
    
    # Check Tavily
    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if api_key:
            response = requests.post(TAVILY_SEARCH_URL, json={
                "api_key": api_key,
                "query": "test",
                "search_depth": "basic",
                "max_results": 1
            })
            results["tavily"] = response.status_code == 200
    except Exception as e:
        print(f"Tavily health check failed: {e}")
    
    results["ok"] = all([results["openai"], results["elevenlabs"], results["tavily"]])
    return results

def fetch_news(topics: List[str], lookback_hours: int = 24, cap_per_topic: int = 5):
    """Fetch news from Tavily API"""
    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise Exception("TAVILY_API_KEY not found")
        
        all_articles = []
        
        for topic in topics:
            query = f"latest news about {topic}"
            
            response = requests.post(TAVILY_SEARCH_URL, json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": cap_per_topic,
                "include_answer": False,
                "include_raw_content": False,
                "include_images": False
            })
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get("results", [])
                
                for article in articles:
                    article["topic"] = topic
                    all_articles.append(article)
            else:
                print(f"Tavily API error for topic {topic}: {response.status_code}")
        
        return all_articles
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

def generate_script(articles: List[Dict], topics: List[str], language: str, duration_minutes: int, tone: str = "professional"):
    """Generate news script using GPT-4"""
    try:
        # Prepare articles text
        articles_text = ""
        for article in articles:
            title = article.get("title", "")
            content = article.get("content", "")
            url = article.get("url", "")
            topic = article.get("topic", "")
            
            articles_text += f"Topic: {topic}\nTitle: {title}\nContent: {content}\nURL: {url}\n\n"
        
        # Calculate target word count (roughly 150 words per minute)
        target_words = duration_minutes * 150
        
        prompt = f"""
You are Noah, a professional news anchor. Create a {duration_minutes}-minute news bulletin in {language} with a {tone} tone.

Topics to cover: {', '.join(topics)}

Available news articles:
{articles_text}

Requirements:
1. Create engaging, informative content
2. Target approximately {target_words} words
3. Structure as a professional news bulletin
4. Include introduction and conclusion
5. Make it sound natural when spoken aloud
6. Focus on the most important and recent news
7. If there's not enough news, add relevant background context

Format the response as a clean script ready for text-to-speech.
"""

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.7
        )
        
        script = response.choices[0].message.content.strip()
        return script
        
    except Exception as e:
        print(f"Error generating script: {e}")
        return f"Welcome to Noah. Here's your {duration_minutes}-minute briefing on {', '.join(topics)}. Unfortunately, there was an error generating the content. Please try again later."

def generate_audio(script: str, voice_id: str):
    """Generate audio using ElevenLabs TTS"""
    try:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise Exception("ELEVENLABS_API_KEY not found")
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
        
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "text": script,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.46,
                "similarity_boost": 0.7,
                "style": 0.25,
                "use_speaker_boost": True
            }
        }
        
        response = requests.post(url, headers=headers, json=data, stream=True)
        
        if response.status_code == 200:
            # Generate unique filename
            timestamp = int(time.time())
            filename = f"noah_{timestamp}.mp3"
            
            # Save audio to file
            audio_dir = os.getenv("AUDIO_DIR", "./audio")
            os.makedirs(audio_dir, exist_ok=True)
            filepath = os.path.join(audio_dir, filename)
            
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return {
                "success": True,
                "filename": filename,
                "filepath": filepath,
                "size_bytes": os.path.getsize(filepath)
            }
        else:
            raise Exception(f"ElevenLabs API error: {response.status_code}")
            
    except Exception as e:
        print(f"Error generating audio: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def make_noah_audio(topics: List[str], language: str = "English", voice: str = None, 
                    duration: int = 5, tone: str = "professional", 
                    lookback_hours: int = 24, cap_per_topic: int = 5, 
                    strict_timing: bool = False):
    """Main function to create Noah audio bulletin"""
    try:
        # Use default voice if none specified
        if not voice:
            voice = "21m00Tcm4TlvDq8ikWAM"
        
        print(f"🎙️ Creating {duration}-minute {language} bulletin on {', '.join(topics)}")
        
        # Step 1: Fetch news
        print("📰 Fetching latest news...")
        articles = fetch_news(topics, lookback_hours, cap_per_topic)
        
        if not articles:
            print("⚠️ No articles found, creating content with background context")
            # Create a basic script with background context
            script = f"Welcome to Noah. Here's your {duration}-minute briefing on {', '.join(topics)}. While we couldn't fetch the latest news at this time, here's some relevant background information. {', '.join(topics)} continue to be important topics in today's world. Stay tuned for more updates on these subjects. That concludes your Noah briefing. Stay informed and have a great day."
        else:
            print(f"📰 Found {len(articles)} articles")
            
            # Step 2: Generate script
            print("✍️ Generating news script...")
            script = generate_script(articles, topics, language, duration, tone)
        
        # Step 3: Generate audio
        print("🎵 Generating audio...")
        audio_result = generate_audio(script, voice)
        
        if audio_result["success"]:
            print(f"✅ Audio generated successfully: {audio_result['filename']}")
            
            # Calculate actual duration (rough estimate)
            word_count = len(script.split())
            estimated_duration = word_count / 150  # Rough words per minute
            
            return {
                "status": "success",
                "transcript": script,
                "audio_url": f"/download/{audio_result['filename']}",
                "duration_minutes": estimated_duration,
                "topics": topics,
                "language": language,
                "voice": voice,
                "mp3_name": audio_result['filename'],
                "word_count": word_count
            }
        else:
            raise Exception(f"Audio generation failed: {audio_result['error']}")
            
    except Exception as e:
        print(f"❌ Error in make_noah_audio: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
