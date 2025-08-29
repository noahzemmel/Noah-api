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

def generate_script_with_precision(articles: List[Dict], topics: List[str], language: str, 
                                  target_duration_minutes: float, tone: str = "professional", 
                                  voice_id: str = "21m00Tcm4TlvDq8ikWAM", max_iterations: int = 3):
    """Generate news script with precision timing control"""
    try:
        # Voice-specific timing adjustments (words per minute)
        voice_timing = {
            "21m00Tcm4TlvDq8ikWAM": 140,  # Rachel - measured
            "2EiwWnXFnvU5JabPnv8n": 135,  # Clyde - measured
            "CwhRBWXzGAHq8TQ4Fs17": 145,  # Roger - measured
            "EXAVITQu4vr4xnSDxMaL": 138,  # Sarah - measured
            "default": 140
        }
        
        words_per_minute = voice_timing.get(voice_id, voice_timing["default"])
        target_words = int(target_duration_minutes * words_per_minute)
        
        print(f"🎯 Target: {target_duration_minutes} minutes = {target_words} words (using {words_per_minute} wpm)")
        
        # Prepare articles text
        articles_text = ""
        for article in articles:
            title = article.get("title", "")
            content = article.get("content", "")
            url = article.get("url", "")
            topic = article.get("topic", "")
            
            articles_text += f"Topic: {topic}\nTitle: {title}\nContent: {content}\nURL: {url}\n\n"
        
        for iteration in range(max_iterations):
            print(f"🔄 Iteration {iteration + 1}: Targeting {target_words} words")
            
            # Adjust prompt based on iteration
            if iteration == 0:
                duration_instruction = f"Create a {target_duration_minutes}-minute news bulletin"
            elif iteration == 1:
                duration_instruction = f"Create a SHORTER news bulletin targeting exactly {target_duration_minutes} minutes"
            else:
                duration_instruction = f"Create a MUCH SHORTER news bulletin - be very concise, target exactly {target_duration_minutes} minutes"
            
            prompt = f"""
You are Noah, a professional news anchor. {duration_instruction} in {language} with a {tone} tone.

Topics to cover: {', '.join(topics)}

Available news articles:
{articles_text}

CRITICAL REQUIREMENTS:
1. Target EXACTLY {target_words} words (±10 words)
2. Create engaging, informative content
3. Structure as a professional news bulletin
4. Include brief introduction and conclusion
5. Make it sound natural when spoken aloud
6. Focus on the most important and recent news
7. If there's not enough news, add relevant background context
8. Be precise with word count - this is for exact timing control

Current target: {target_words} words for {target_duration_minutes} minutes.

Format the response as a clean script ready for text-to-speech.
"""

            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.7
            )
            
            script = response.choices[0].message.content.strip()
            actual_words = len(script.split())
            
            print(f"📝 Generated: {actual_words} words (target: {target_words})")
            
            # Check if we're close enough
            if abs(actual_words - target_words) <= 15:  # Allow 15 word tolerance
                print(f"✅ Word count within tolerance: {actual_words} vs {target_words}")
                return script, actual_words
            
            # Adjust target for next iteration
            if actual_words > target_words:
                target_words = int(target_words * 0.85)  # Reduce by 15%
            else:
                target_words = int(target_words * 1.15)  # Increase by 15%
        
        print(f"⚠️ Max iterations reached, using final script with {len(script.split())} words")
        return script, len(script.split())
        
    except Exception as e:
        print(f"Error generating script with precision: {e}")
        return f"Welcome to Noah. Here's your {target_duration_minutes}-minute briefing on {', '.join(topics)}. Unfortunately, there was an error generating the content. Please try again later.", 0

def measure_audio_duration(audio_filepath: str) -> float:
    """Measure actual audio duration using ffprobe or file size estimation"""
    try:
        # Try using ffprobe for exact duration
        import subprocess
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
            '-of', 'csv=p=0', audio_filepath
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            duration = float(result.stdout.strip())
            return duration / 60.0  # Convert to minutes
    except:
        pass
    
    try:
        # Fallback: estimate from file size (rough but works)
        file_size = os.path.getsize(audio_filepath)
        # Rough estimation: 1MB ≈ 1 minute for MP3
        estimated_minutes = file_size / (1024 * 1024)
        return estimated_minutes
    except:
        return 0.0

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

def generate_audio_with_timing(script: str, voice_id: str, target_duration_minutes: float):
    """Generate audio and measure actual duration"""
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
            
            # Measure actual duration
            actual_duration_minutes = measure_audio_duration(filepath)
            
            return {
                "success": True,
                "filename": filename,
                "filepath": filepath,
                "size_bytes": os.path.getsize(filepath),
                "actual_duration_minutes": actual_duration_minutes,
                "target_duration_minutes": target_duration_minutes,
                "duration_accuracy": abs(actual_duration_minutes - target_duration_minutes)
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
    """Main function to create Noah audio bulletin with precision timing"""
    try:
        # Use default voice if none specified
        if not voice:
            voice = "21m00Tcm4TlvDq8ikWAM"
        
        print(f"🎙️ Creating {duration}-minute {language} bulletin on {', '.join(topics)}")
        print(f"🎯 Precision timing: {'ENABLED' if strict_timing else 'Standard'}")
        
        # Step 1: Fetch news
        print("📰 Fetching latest news...")
        articles = fetch_news(topics, lookback_hours, cap_per_topic)
        
        if not articles:
            print("⚠️ No articles found, creating content with background context")
            # Create a basic script with background context
            script = f"Welcome to Noah. Here's your {duration}-minute briefing on {', '.join(topics)}. While we couldn't fetch the latest news at this time, here's some relevant background information. {', '.join(topics)} continue to be important topics in today's world. Stay tuned for more updates on these subjects. That concludes your Noah briefing. Stay informed and have a great day."
            word_count = len(script.split())
        else:
            print(f"📰 Found {len(articles)} articles")
            
            # Step 2: Generate script with precision timing
            print("✍️ Generating news script with precision timing...")
            if strict_timing:
                script, word_count = generate_script_with_precision(
                    articles, topics, language, duration, tone, voice
                )
            else:
                script = generate_script(articles, topics, language, duration, tone)
                word_count = len(script.split())
        
        # Step 3: Generate audio with timing measurement
        print("🎵 Generating audio with duration measurement...")
        if strict_timing:
            audio_result = generate_audio_with_timing(script, voice, duration)
        else:
            audio_result = generate_audio(script, voice)
        
        if audio_result["success"]:
            print(f"✅ Audio generated successfully: {audio_result['filename']}")
            
            # Get actual duration
            if strict_timing and "actual_duration_minutes" in audio_result:
                actual_duration = audio_result["actual_duration_minutes"]
                duration_accuracy = audio_result.get("duration_accuracy", 0)
                print(f"🎯 Duration: {actual_duration:.2f} minutes (target: {duration}, accuracy: ±{duration_accuracy:.2f} min)")
            else:
                # Fallback estimation
                actual_duration = word_count / 140  # Rough estimate
                duration_accuracy = abs(actual_duration - duration)
                print(f"📊 Estimated duration: {actual_duration:.2f} minutes (target: {duration})")
            
            return {
                "status": "success",
                "transcript": script,
                "audio_url": f"/download/{audio_result['filename']}",
                "duration_minutes": actual_duration,
                "target_duration_minutes": duration,
                "duration_accuracy_minutes": duration_accuracy,
                "topics": topics,
                "language": language,
                "voice": voice,
                "mp3_name": audio_result['filename'],
                "word_count": word_count,
                "precision_timing": strict_timing,
                "timing_quality": "exact" if duration_accuracy < 0.5 else "close" if duration_accuracy < 1.0 else "approximate"
            }
        else:
            raise Exception(f"Audio generation failed: {audio_result['error']}")
            
    except Exception as e:
        print(f"❌ Error in make_noah_audio: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
