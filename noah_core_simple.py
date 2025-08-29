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
    """Fetch recent, specific news updates from Tavily API"""
    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise Exception("TAVILY_API_KEY not found")
        
        all_articles = []
        
        for topic in topics:
            # Use more specific queries for recent updates
            specific_queries = [
                f"breaking news {topic} last 24 hours",
                f"latest developments {topic} today",
                f"recent updates {topic} this week",
                f"new developments {topic} recent",
                f"latest news {topic} updates"
            ]
            
            for query in specific_queries:
                response = requests.post(TAVILY_SEARCH_URL, json={
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "advanced",  # Use advanced search for better results
                    "max_results": min(cap_per_topic, 3),  # Limit per query
                    "include_answer": False,
                    "include_raw_content": True,  # Get full content for better analysis
                    "include_images": False,
                    "time_period": "1d"  # Focus on last 24 hours
                })
                
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("results", [])
                    
                    for article in articles:
                        # Add metadata for better filtering
                        article["topic"] = topic
                        article["query_used"] = query
                        article["relevance_score"] = calculate_relevance_score(article, topic)
                        all_articles.append(article)
                else:
                    print(f"Tavily API error for query '{query}': {response.status_code}")
        
        # Sort by relevance and recency, remove duplicates
        unique_articles = remove_duplicate_articles(all_articles)
        sorted_articles = sorted(unique_articles, key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        # Take top articles per topic
        final_articles = []
        topic_counts = {}
        
        for article in sorted_articles:
            topic = article["topic"]
            if topic_counts.get(topic, 0) < cap_per_topic:
                final_articles.append(article)
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        print(f"📰 Fetched {len(final_articles)} relevant articles from {len(all_articles)} total results")
        return final_articles
        
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

def calculate_relevance_score(article: Dict, topic: str) -> float:
    """Calculate relevance score based on recency, specificity, and topic match"""
    score = 0.0
    
    # Base score for topic relevance
    title = article.get("title", "").lower()
    content = article.get("content", "").lower()
    topic_lower = topic.lower()
    
    if topic_lower in title:
        score += 3.0
    elif topic_lower in content[:200]:  # First 200 chars
        score += 2.0
    
    # Bonus for recent content indicators
    if any(word in title.lower() for word in ["breaking", "latest", "new", "update", "developments", "announces", "reveals"]):
        score += 2.0
    
    if any(word in content.lower() for word in ["today", "yesterday", "this week", "recently", "announced", "released"]):
        score += 1.5
    
    # Bonus for specific companies/people mentioned
    if any(word in content.lower() for word in ["announced", "said", "revealed", "confirmed", "launched"]):
        score += 1.0
    
    # Penalty for generic content
    if any(word in title.lower() for word in ["overview", "guide", "explained", "what is", "introduction"]):
        score -= 1.0
    
    return score

def remove_duplicate_articles(articles: List[Dict]) -> List[Dict]:
    """Remove duplicate articles based on URL and title similarity"""
    seen_urls = set()
    seen_titles = set()
    unique_articles = []
    
    for article in articles:
        url = article.get("url", "")
        title = article.get("title", "").lower()
        
        # Check if we've seen this URL or very similar title
        if url not in seen_urls and not any(title_similarity(title, seen_title) > 0.8 for seen_title in seen_titles):
            unique_articles.append(article)
            seen_urls.add(url)
            seen_titles.add(title)
    
    return unique_articles

def title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity between two titles (simple implementation)"""
    words1 = set(title1.split())
    words2 = set(title2.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0

def generate_script(articles: List[Dict], topics: List[str], language: str, duration_minutes: int, tone: str = "professional"):
    """Generate news script focused on recent, specific updates"""
    try:
        # Prepare articles text with focus on recent developments
        articles_text = ""
        for article in articles:
            title = article.get("title", "")
            content = article.get("content", "")
            url = article.get("url", "")
            topic = article.get("topic", "")
            relevance_score = article.get("relevance_score", 0)
            
            articles_text += f"Topic: {topic}\nTitle: {title}\nContent: {content}\nURL: {url}\nRelevance Score: {relevance_score}\n\n"
        
        # Calculate target word count (roughly 150 words per minute)
        target_words = duration_minutes * 150
        
        prompt = f"""
You are Noah, a professional news anchor delivering a {duration_minutes}-minute briefing in {language} with a {tone} tone.

Your mission: Provide busy professionals with SPECIFIC, RECENT updates on their requested topics. Focus on what happened in the last 24 hours, not general overviews.

Topics requested: {', '.join(topics)}

Available news articles (ranked by relevance and recency):
{articles_text}

CRITICAL REQUIREMENTS:
1. Focus on SPECIFIC developments, announcements, and breaking news from the last 24 hours
2. Avoid generic overviews, explanations, or background information
3. Lead with the most recent and relevant updates first
4. Include specific details: company names, people, numbers, dates, locations
5. Structure as: "Company X announced Y today" or "Breaking: X happened in Y"
6. If no recent news exists, say so clearly and don't fill with generic content
7. Target approximately {target_words} words
8. Make it sound natural when spoken aloud
9. Each update should be actionable and informative

Format: Start with "Good [time], I'm Noah with your {duration_minutes}-minute briefing on [topics]." Then deliver specific updates, ending with "That concludes your briefing. Stay informed."

Focus on WHAT HAPPENED, not what things are.
"""

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7
        )
        
        script = response.choices[0].message.content.strip()
        return script
        
    except Exception as e:
        print(f"Error generating script: {e}")
        return f"Welcome to Noah. Here's your {duration_minutes}-minute briefing on {', '.join(topics)}. Unfortunately, there was an error generating the content. Please try again later."

def generate_script_with_precision(articles: List[Dict], topics: List[str], language: str, 
                                  target_duration_minutes: float, tone: str = "professional", 
                                  voice_id: str = "21m00Tcm4TlvDq8ikWAM", max_iterations: int = 2):
    """Generate news script with precision timing control (optimized for speed)"""
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
        
        # Prepare articles text (limit content for faster processing)
        articles_text = ""
        for article in articles[:3]:  # Limit to 3 articles for speed
            title = article.get("title", "")
            content = article.get("content", "")[:500]  # Limit content length
            url = article.get("url", "")
            topic = article.get("topic", "")
            
            articles_text += f"Topic: {topic}\nTitle: {title}\nContent: {content}\nURL: {url}\n\n"
        
        for iteration in range(max_iterations):
            print(f"🔄 Iteration {iteration + 1}: Targeting {target_words} words")
            
            # Adjust prompt based on iteration (more aggressive for speed)
            if iteration == 0:
                duration_instruction = f"Create a {target_duration_minutes}-minute news bulletin"
            else:
                duration_instruction = f"Create a MUCH SHORTER news bulletin - be very concise, target exactly {target_duration_minutes} minutes"
            
            prompt = f"""
You are Noah, a professional news anchor. {duration_instruction} in {language} with a {tone} tone.

Your mission: Provide busy professionals with SPECIFIC, RECENT updates on their requested topics. Focus on what happened in the last 24 hours, not general overviews.

Topics to cover: {', '.join(topics)}

Available news articles (ranked by relevance and recency):
{articles_text}

CRITICAL REQUIREMENTS:
1. Target EXACTLY {target_words} words (±15 words)
2. Focus on SPECIFIC developments, announcements, and breaking news from the last 24 hours
3. Avoid generic overviews, explanations, or background information
4. Lead with the most recent and relevant updates first
5. Include specific details: company names, people, numbers, dates, locations
6. Structure as: "Company X announced Y today" or "Breaking: X happened in Y"
7. If no recent news exists, say so clearly and don't fill with generic content
8. Make it sound natural when spoken aloud
9. Each update should be actionable and informative
10. Be precise with word count - this is for exact timing control

Current target: {target_words} words for {target_duration_minutes} minutes.

Format: Start with "Good [time], I'm Noah with your {target_duration_minutes}-minute briefing on [topics]." Then deliver specific updates, ending with "That concludes your briefing. Stay informed."

Focus on WHAT HAPPENED, not what things are.
"""

            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,  # Reduced for speed
                temperature=0.7
            )
            
            script = response.choices[0].message.content.strip()
            actual_words = len(script.split())
            
            print(f"📝 Generated: {actual_words} words (target: {target_words})")
            
            # Check if we're close enough (more lenient for speed)
            if abs(actual_words - target_words) <= 20:  # Allow 20 word tolerance
                print(f"✅ Word count within tolerance: {actual_words} vs {target_words}")
                return script, actual_words
            
            # Adjust target for next iteration (more aggressive)
            if actual_words > target_words:
                target_words = int(target_words * 0.80)  # Reduce by 20%
            else:
                target_words = int(target_words * 1.20)  # Increase by 20%
        
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
        
        # Step 1: Fetch news (limit for speed)
        print("📰 Fetching latest news...")
        articles = fetch_news(topics, lookback_hours, min(cap_per_topic, 3))  # Limit to 3 articles max
        
        # Validate news quality
        news_validation = validate_recent_news(articles, topics)
        print(f"📊 News quality: {news_validation['quality_score']:.1f}% ({news_validation['recent_articles']}/{news_validation['total_articles']} recent articles)")
        
        if not articles or not news_validation["has_recent_news"]:
            print("⚠️ No recent news found, creating no-news script")
            script = create_no_recent_news_script(topics, duration, language)
            word_count = len(script.split())
        else:
            print(f"📰 Found {len(articles)} relevant recent articles")
            
            # Step 2: Generate script with precision timing
            print("✍️ Generating news script with precision timing...")
            if strict_timing:
                try:
                    script, word_count = generate_script_with_precision(
                        articles, topics, language, duration, tone, voice
                    )
                except Exception as e:
                    print(f"⚠️ Precision timing failed, falling back to standard: {e}")
                    script = generate_script(articles, topics, language, duration, tone)
                    word_count = len(script.split())
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
                "timing_quality": "exact" if duration_accuracy < 0.5 else "close" if duration_accuracy < 1.0 else "approximate",
                "news_quality": {
                    "quality_score": news_validation["quality_score"],
                    "total_articles": news_validation["total_articles"],
                    "recent_articles": news_validation["recent_articles"],
                    "high_relevance_articles": news_validation["high_relevance_articles"],
                    "topics_with_news": list(news_validation["topics_with_news"]),
                    "topics_without_news": list(news_validation["topics_without_news"]),
                    "has_recent_news": news_validation["has_recent_news"]
                }
            }
        else:
            raise Exception(f"Audio generation failed: {audio_result['error']}")
            
    except Exception as e:
        print(f"❌ Error in make_noah_audio: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def validate_recent_news(articles: List[Dict], topics: List[str]) -> Dict:
    """Validate that we have recent, relevant news for the requested topics"""
    validation = {
        "has_recent_news": False,
        "total_articles": len(articles),
        "recent_articles": 0,
        "high_relevance_articles": 0,
        "topics_with_news": set(),
        "topics_without_news": set(topics),
        "quality_score": 0.0
    }
    
    if not articles:
        return validation
    
    for article in articles:
        topic = article.get("topic", "")
        relevance_score = article.get("relevance_score", 0)
        
        if topic in topics:
            validation["topics_with_news"].add(topic)
            validation["topics_without_news"].discard(topic)
            
            if relevance_score > 2.0:
                validation["high_relevance_articles"] += 1
            
            if relevance_score > 1.0:
                validation["recent_articles"] += 1
    
    # Calculate overall quality score
    if validation["total_articles"] > 0:
        validation["quality_score"] = (validation["recent_articles"] / validation["total_articles"]) * 100
        validation["has_recent_news"] = validation["quality_score"] > 50
    
    return validation

def create_no_recent_news_script(topics: List[str], duration_minutes: int, language: str) -> str:
    """Create a script when no recent news is available"""
    return f"""Good {get_time_greeting()}, I'm Noah with your {duration_minutes}-minute briefing on {', '.join(topics)}.

I've checked for the latest developments on your requested topics, but I don't have any breaking news or recent updates to report at this time. This could mean:

1. It's been a quiet period for these topics
2. The news cycle is currently focused elsewhere
3. Major developments may be brewing but haven't been announced yet

I recommend checking back in a few hours for fresh updates, or you can request different topics that may have more recent activity.

That concludes your briefing. Stay informed and have a great day."""

def get_time_greeting() -> str:
    """Get appropriate time-based greeting"""
    from datetime import datetime
    hour = datetime.now().hour
    
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "evening"
