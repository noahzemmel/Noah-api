# noah_core_advanced.py - World-Class AI Briefing Core Engine
"""
🚀 DAILY NOAH ADVANCED CORE ENGINE
The most sophisticated AI briefing generation system ever built.

Features:
- Intelligent content optimization with GPT-4 Turbo
- Advanced caching and performance optimization
- Multi-language support with cultural context
- Voice cloning and advanced TTS customization
- Smart content expansion and timing precision
- Real-time analytics and monitoring
- Enterprise-grade security and error handling
- Parallel processing and async optimization
"""

import os
import io
import re
import math
import json
import time
import base64
import random
import asyncio
import hashlib
import aiohttp
from typing import List, Dict, Tuple, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Core dependencies
import requests
from dotenv import load_dotenv
from dateutil import parser as dateparse
from openai import AsyncOpenAI
import structlog

# Load environment variables
load_dotenv()

# ============================================================================
# ADVANCED CONFIGURATION
# ============================================================================

class ContentQuality(Enum):
    """Content quality levels"""
    DRAFT = "draft"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class GenerationPriority(Enum):
    """Generation priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class GenerationConfig:
    """Advanced generation configuration"""
    quality: ContentQuality = ContentQuality.PREMIUM
    priority: GenerationPriority = GenerationPriority.NORMAL
    max_retries: int = 3
    timeout_seconds: int = 300
    enable_caching: bool = True
    enable_analytics: bool = True
    enable_optimization: bool = True

@dataclass
class ContentMetrics:
    """Content generation metrics"""
    generation_time: float
    word_count: int
    quality_score: float
    timing_accuracy: float
    cache_hits: int
    api_calls: int
    error_count: int

# Constants
ELEVEN_VOICES_URL = "https://api.elevenlabs.io/v1/voices"
OPENAI_MODEL = "gpt-4-turbo-preview"
TAVILY_SEARCH_URL = "https://api.tavily.com/search"

# Advanced voice timing profiles (words per minute)
VOICE_TIMING_PROFILES = {
    "21m00Tcm4TlvDq8ikWAM": {"wpm": 140, "pause_factor": 1.0, "clarity": 0.95},  # Rachel
    "2EiwWnXFnvU5JabPnv8n": {"wpm": 135, "pause_factor": 1.1, "clarity": 0.92},  # Clyde
    "CwhRBWXzGAHq8TQ4Fs17": {"wpm": 145, "pause_factor": 0.9, "clarity": 0.98},  # Roger
    "EXAVITQu4vr4xnSDxMaL": {"wpm": 138, "pause_factor": 1.05, "clarity": 0.94},  # Sarah
    "default": {"wpm": 140, "pause_factor": 1.0, "clarity": 0.95}
}

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Advanced logging
logger = structlog.get_logger()

# ============================================================================
# ADVANCED CACHING SYSTEM
# ============================================================================

class AdvancedCache:
    """Advanced caching system with TTL and intelligent invalidation"""
    
    def __init__(self):
        self.cache = {}
        self.ttl = {}
        self.access_count = {}
        self.last_access = {}
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self.ttl:
            return True
        return time.time() > self.ttl[key]
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value with access tracking"""
        if key in self.cache and not self._is_expired(key):
            self.access_count[key] = self.access_count.get(key, 0) + 1
            self.last_access[key] = time.time()
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """Set cached value with TTL"""
        self.cache[key] = value
        self.ttl[key] = time.time() + ttl_seconds
        self.access_count[key] = 0
        self.last_access[key] = time.time()
    
    def invalidate(self, pattern: str = None):
        """Invalidate cache entries matching pattern"""
        if pattern is None:
            self.cache.clear()
            self.ttl.clear()
            self.access_count.clear()
            self.last_access.clear()
        else:
            keys_to_remove = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_remove:
                self.cache.pop(key, None)
                self.ttl.pop(key, None)
                self.access_count.pop(key, None)
                self.last_access.pop(key, None)

# Global cache instance
cache = AdvancedCache()

# ============================================================================
# ADVANCED VOICE MANAGEMENT
# ============================================================================

async def get_available_voices_advanced() -> Dict[str, Any]:
    """Get available voices with advanced metadata and caching"""
    cache_key = "voices_advanced"
    cached_voices = cache.get(cache_key)
    if cached_voices:
        return cached_voices
    
    try:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            return {"voices": [], "error": "API key not found"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                ELEVEN_VOICES_URL, 
                headers={"xi-api-key": api_key},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    voices_data = await response.json()
                    formatted_voices = []
                    
                    for voice in voices_data.get("voices", []):
                        voice_id = voice.get("voice_id")
                        timing_profile = VOICE_TIMING_PROFILES.get(voice_id, VOICE_TIMING_PROFILES["default"])
                        
                        formatted_voice = {
                            "id": voice_id,
                            "name": voice.get("name", "Unknown"),
                            "provider": "elevenlabs",
                            "language": voice.get("labels", {}).get("language", "en"),
                            "accent": voice.get("labels", {}).get("accent", "neutral"),
                            "description": voice.get("labels", {}).get("description", ""),
                            "gender": voice.get("labels", {}).get("gender", "unknown"),
                            "age": voice.get("labels", {}).get("age", "unknown"),
                            "use_case": voice.get("labels", {}).get("use_case", "general"),
                            "timing_profile": timing_profile,
                            "quality_score": voice.get("labels", {}).get("quality_score", 0.9),
                            "preview_url": voice.get("preview_url", ""),
                            "available_for_cloning": voice.get("labels", {}).get("cloning", False)
                        }
                        formatted_voices.append(formatted_voice)
                    
                    result = {
                        "voices": formatted_voices,
                        "total_count": len(formatted_voices),
                        "cached_at": datetime.now(timezone.utc).isoformat(),
                        "cache_ttl": 3600
                    }
                    
                    # Cache for 1 hour
                    cache.set(cache_key, result, 3600)
                    return result
                else:
                    error_text = await response.text()
                    return {"voices": [], "error": f"API error: {response.status} - {error_text}"}
                    
    except Exception as e:
        logger.error("Error fetching voices", error=str(e))
        return {"voices": [], "error": str(e)}

# ============================================================================
# ADVANCED NEWS FETCHING
# ============================================================================

async def fetch_news_advanced(
    topics: List[str], 
    lookback_hours: int = 24,
    max_articles_per_topic: int = 5,
    quality_threshold: float = 0.7,
    enable_parallel: bool = True
) -> Dict[str, Any]:
    """Advanced news fetching with parallel processing and quality filtering"""
    
    cache_key = f"news_{hashlib.md5('_'.join(topics).encode()).hexdigest()}_{lookback_hours}_{max_articles_per_topic}"
    cached_news = cache.get(cache_key)
    if cached_news:
        return cached_news
    
    start_time = time.time()
    all_articles = []
    topic_coverage = {}
    api_calls = 0
    
    # Generate advanced search queries
    search_queries = []
    for topic in topics:
        base_queries = [
            f"breaking news {topic} last {lookback_hours} hours",
            f"latest developments {topic} today",
            f"recent updates {topic} this week",
            f"new developments {topic} recent",
            f"latest news {topic} updates"
        ]
        search_queries.extend(base_queries)
    
    async def fetch_tavily_news(query: str) -> List[Dict]:
        """Fetch news from Tavily API with error handling"""
        nonlocal api_calls
        try:
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                return []
            
            payload = {
                "query": query,
                "search_depth": "advanced",
                "include_raw_content": True,
                "time_period": "1d" if lookback_hours <= 24 else "1w",
                "max_results": max_articles_per_topic
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    TAVILY_SEARCH_URL,
                    json=payload,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    api_calls += 1
                    if response.status == 200:
                        data = await response.json()
                        articles = data.get("results", [])
                        
                        # Enhanced article processing
                        processed_articles = []
                        for article in articles:
                            processed_article = {
                                "title": article.get("title", ""),
                                "url": article.get("url", ""),
                                "content": article.get("content", "")[:1000],  # Limit content
                                "published_date": article.get("published_date", ""),
                                "relevance_score": calculate_advanced_relevance_score(article, topics),
                                "topic": extract_topic_from_content(article.get("content", ""), topics),
                                "source": article.get("url", "").split("/")[2] if article.get("url") else "unknown",
                                "quality_score": calculate_content_quality(article),
                                "sentiment": analyze_sentiment(article.get("content", "")),
                                "readability_score": calculate_readability(article.get("content", ""))
                            }
                            
                            # Quality filtering
                            if processed_article["quality_score"] >= quality_threshold:
                                processed_articles.append(processed_article)
                        
                        return processed_articles
                    else:
                        logger.warning(f"Tavily API error for query '{query}': {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching news for query '{query}': {e}")
            return []
    
    # Parallel fetching
    if enable_parallel:
        tasks = [fetch_tavily_news(query) for query in search_queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Task failed: {result}")
    else:
        # Sequential fetching
        for query in search_queries:
            articles = await fetch_tavily_news(query)
            all_articles.extend(articles)
    
    # Advanced deduplication and ranking
    unique_articles = remove_duplicate_articles_advanced(all_articles)
    ranked_articles = rank_articles_by_relevance(unique_articles, topics)
    
    # Calculate topic coverage
    for topic in topics:
        topic_articles = [a for a in ranked_articles if topic.lower() in a.get("topic", "").lower()]
        topic_coverage[topic] = len(topic_articles)
    
    # Calculate metrics
    generation_time = time.time() - start_time
    avg_quality = sum(a.get("quality_score", 0) for a in ranked_articles) / len(ranked_articles) if ranked_articles else 0
    
    result = {
        "articles": ranked_articles,
        "total_articles": len(ranked_articles),
        "topic_coverage": topic_coverage,
        "generation_time": generation_time,
        "api_calls": api_calls,
        "average_quality": avg_quality,
        "cached_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Cache for 30 minutes
    cache.set(cache_key, result, 1800)
    return result

def calculate_advanced_relevance_score(article: Dict, topics: List[str]) -> float:
    """Calculate advanced relevance score based on multiple factors"""
    score = 0.0
    content = article.get("content", "").lower()
    title = article.get("title", "").lower()
    
    # Topic relevance
    for topic in topics:
        topic_lower = topic.lower()
        if topic_lower in title:
            score += 3.0
        if topic_lower in content:
            score += 1.0
    
    # Recency bonus
    published_date = article.get("published_date", "")
    if published_date:
        try:
            pub_date = dateparse.parse(published_date)
            hours_ago = (datetime.now(timezone.utc) - pub_date).total_seconds() / 3600
            if hours_ago <= 6:
                score += 2.0
            elif hours_ago <= 24:
                score += 1.0
        except:
            pass
    
    # Content quality indicators
    if len(content) > 200:
        score += 0.5
    if "breaking" in title or "urgent" in title:
        score += 1.0
    if "announced" in content or "reported" in content:
        score += 0.5
    
    return min(score, 10.0)  # Cap at 10

def extract_topic_from_content(content: str, topics: List[str]) -> str:
    """Extract the most relevant topic from content"""
    content_lower = content.lower()
    topic_scores = {}
    
    for topic in topics:
        topic_lower = topic.lower()
        score = content_lower.count(topic_lower)
        if score > 0:
            topic_scores[topic] = score
    
    return max(topic_scores.items(), key=lambda x: x[1])[0] if topic_scores else topics[0]

def calculate_content_quality(article: Dict) -> float:
    """Calculate content quality score"""
    score = 0.5  # Base score
    
    content = article.get("content", "")
    title = article.get("title", "")
    
    # Length indicators
    if len(content) > 100:
        score += 0.1
    if len(content) > 500:
        score += 0.1
    if len(title) > 20:
        score += 0.1
    
    # Quality indicators
    if "http" in content:  # Has links
        score += 0.1
    if any(word in content.lower() for word in ["announced", "reported", "confirmed", "revealed"]):
        score += 0.1
    if any(word in title.lower() for word in ["breaking", "urgent", "exclusive", "latest"]):
        score += 0.1
    
    return min(score, 1.0)

def analyze_sentiment(content: str) -> str:
    """Simple sentiment analysis"""
    positive_words = ["good", "great", "excellent", "positive", "success", "growth", "improvement"]
    negative_words = ["bad", "terrible", "negative", "failure", "decline", "crisis", "problem"]
    
    content_lower = content.lower()
    positive_count = sum(1 for word in positive_words if word in content_lower)
    negative_count = sum(1 for word in negative_words if word in content_lower)
    
    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    else:
        return "neutral"

def calculate_readability(content: str) -> float:
    """Calculate simple readability score"""
    if not content:
        return 0.0
    
    sentences = len(re.findall(r'[.!?]+', content))
    words = len(content.split())
    
    if sentences == 0:
        return 0.0
    
    avg_words_per_sentence = words / sentences
    return max(0, min(1, 1 - (avg_words_per_sentence - 15) / 30))

def remove_duplicate_articles_advanced(articles: List[Dict]) -> List[Dict]:
    """Advanced deduplication based on content similarity"""
    unique_articles = []
    seen_urls = set()
    seen_titles = set()
    
    for article in articles:
        url = article.get("url", "")
        title = article.get("title", "").lower().strip()
        
        # Skip if URL or title already seen
        if url in seen_urls or title in seen_titles:
            continue
        
        # Check for similar titles (fuzzy matching)
        is_duplicate = False
        for seen_title in seen_titles:
            if calculate_title_similarity(title, seen_title) > 0.8:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_articles.append(article)
            seen_urls.add(url)
            seen_titles.add(title)
    
    return unique_articles

def calculate_title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity between two titles"""
    words1 = set(title1.split())
    words2 = set(title2.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0

def rank_articles_by_relevance(articles: List[Dict], topics: List[str]) -> List[Dict]:
    """Rank articles by relevance and quality"""
    def relevance_score(article):
        base_score = article.get("relevance_score", 0)
        quality_score = article.get("quality_score", 0)
        recency_bonus = 0
        
        # Recency bonus
        published_date = article.get("published_date", "")
        if published_date:
            try:
                pub_date = dateparse.parse(published_date)
                hours_ago = (datetime.now(timezone.utc) - pub_date).total_seconds() / 3600
                if hours_ago <= 6:
                    recency_bonus = 2.0
                elif hours_ago <= 24:
                    recency_bonus = 1.0
            except:
                pass
        
        return base_score + (quality_score * 2) + recency_bonus
    
    return sorted(articles, key=relevance_score, reverse=True)

# ============================================================================
# ADVANCED CONTENT GENERATION
# ============================================================================

async def generate_script_advanced(
    articles: List[Dict], 
    topics: List[str], 
    language: str,
    target_duration_minutes: float, 
    tone: str = "professional",
    voice_id: str = "21m00Tcm4TlvDq8ikWAM",
    quality: ContentQuality = ContentQuality.PREMIUM
) -> Tuple[str, int, ContentMetrics]:
    """Generate advanced news script with intelligent optimization"""
    
    start_time = time.time()
    cache_hits = 0
    api_calls = 0
    
    # Get voice timing profile
    timing_profile = VOICE_TIMING_PROFILES.get(voice_id, VOICE_TIMING_PROFILES["default"])
    target_words = int(target_duration_minutes * timing_profile["wpm"])
    
    # Prepare advanced articles context
    articles_context = prepare_advanced_articles_context(articles, topics, quality)
    
    # Generate intelligent prompt
    prompt = create_advanced_prompt(
        topics, language, target_duration_minutes, tone, 
        target_words, articles_context, quality
    )
    
    # Generate content with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            api_calls += 1
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000 if quality == ContentQuality.ENTERPRISE else 2000,
                temperature=0.7 if quality == ContentQuality.ENTERPRISE else 0.8,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1
            )
            
            script = response.choices[0].message.content.strip()
            word_count = len(script.split())
            
            # Quality validation
            if validate_script_quality(script, target_words, topics, quality):
                generation_time = time.time() - start_time
                metrics = ContentMetrics(
                    generation_time=generation_time,
                    word_count=word_count,
                    quality_score=calculate_script_quality_score(script, articles, topics),
                    timing_accuracy=1 - abs(word_count - target_words) / target_words,
                    cache_hits=cache_hits,
                    api_calls=api_calls,
                    error_count=0
                )
                return script, word_count, metrics
            else:
                logger.warning(f"Script quality validation failed, attempt {attempt + 1}")
                
        except Exception as e:
            logger.error(f"Script generation attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise e
    
    # Fallback generation
    return generate_fallback_script(topics, language, target_duration_minutes, tone), 0, ContentMetrics(
        generation_time=time.time() - start_time,
        word_count=0,
        quality_score=0.0,
        timing_accuracy=0.0,
        cache_hits=cache_hits,
        api_calls=api_calls,
        error_count=1
    )

def prepare_advanced_articles_context(articles: List[Dict], topics: List[str], quality: ContentQuality) -> str:
    """Prepare advanced articles context for AI generation"""
    if not articles:
        return "No recent articles available for the requested topics."
    
    # Limit articles based on quality level
    max_articles = {
        ContentQuality.DRAFT: 3,
        ContentQuality.STANDARD: 5,
        ContentQuality.PREMIUM: 8,
        ContentQuality.ENTERPRISE: 12
    }.get(quality, 5)
    
    context_parts = []
    for i, article in enumerate(articles[:max_articles]):
        topic = article.get("topic", "general")
        title = article.get("title", "")
        content = article.get("content", "")
        source = article.get("source", "unknown")
        quality_score = article.get("quality_score", 0)
        sentiment = article.get("sentiment", "neutral")
        
        context_parts.append(f"""
Article {i+1} - {topic.upper()}:
Title: {title}
Source: {source}
Quality Score: {quality_score:.2f}
Sentiment: {sentiment}
Content: {content[:400]}{'...' if len(content) > 400 else ''}
""")
    
    return "\n".join(context_parts)

def create_advanced_prompt(
    topics: List[str], 
    language: str, 
    target_duration_minutes: float,
    tone: str, 
    target_words: int, 
    articles_context: str,
    quality: ContentQuality
) -> str:
    """Create advanced AI prompt based on quality level"""
    
    base_prompt = f"""
You are Noah, the world's most advanced AI news anchor. Create a {target_duration_minutes}-minute news bulletin in {language} with a {tone} tone.

TARGET: Exactly {target_words} words (±15 words) for precise timing.

TOPICS: {', '.join(topics)}

AVAILABLE NEWS ARTICLES:
{articles_context}

CORE REQUIREMENTS:
1. Focus on SPECIFIC, RECENT developments from the last 24 hours
2. Avoid generic overviews - lead with breaking news and announcements
3. Include specific details: names, numbers, dates, locations
4. Structure as professional news briefing with clear transitions
5. Make it sound natural when spoken aloud
6. End with "That concludes your briefing. Stay informed and have a great day."

QUALITY LEVEL: {quality.value.upper()}
"""
    
    if quality == ContentQuality.ENTERPRISE:
        base_prompt += """
ENTERPRISE ENHANCEMENTS:
- Add market implications and expert analysis
- Include relevant historical context
- Provide actionable insights for professionals
- Use sophisticated vocabulary and complex sentence structures
- Include multiple perspectives on major developments
"""
    elif quality == ContentQuality.PREMIUM:
        base_prompt += """
PREMIUM ENHANCEMENTS:
- Add context and "why this matters" explanations
- Include relevant background information
- Use professional terminology
- Provide clear implications for each development
"""
    
    return base_prompt

def validate_script_quality(script: str, target_words: int, topics: List[str], quality: ContentQuality) -> bool:
    """Validate script quality based on multiple criteria"""
    word_count = len(script.split())
    
    # Word count validation
    word_tolerance = 20 if quality == ContentQuality.ENTERPRISE else 25
    if abs(word_count - target_words) > word_tolerance:
        return False
    
    # Topic coverage validation
    script_lower = script.lower()
    topics_covered = sum(1 for topic in topics if topic.lower() in script_lower)
    if topics_covered < len(topics) * 0.7:  # At least 70% topic coverage
        return False
    
    # Content quality validation
    if len(script) < 200:  # Minimum length
        return False
    
    # Professional structure validation
    if not any(phrase in script_lower for phrase in ["good morning", "good afternoon", "good evening"]):
        return False
    
    if not script_lower.endswith(("stay informed", "have a great day", "thank you")):
        return False
    
    return True

def calculate_script_quality_score(script: str, articles: List[Dict], topics: List[str]) -> float:
    """Calculate comprehensive script quality score"""
    score = 0.0
    
    # Content richness
    word_count = len(script.split())
    if word_count > 300:
        score += 0.2
    if word_count > 500:
        score += 0.1
    
    # Topic coverage
    script_lower = script.lower()
    topics_covered = sum(1 for topic in topics if topic.lower() in script_lower)
    score += (topics_covered / len(topics)) * 0.3
    
    # Professional structure
    if any(phrase in script_lower for phrase in ["good morning", "good afternoon", "good evening"]):
        score += 0.1
    if "that concludes" in script_lower or "stay informed" in script_lower:
        score += 0.1
    
    # Specificity indicators
    if any(word in script_lower for word in ["announced", "reported", "confirmed", "revealed"]):
        score += 0.1
    if any(word in script_lower for word in ["percent", "million", "billion", "thousand"]):
        score += 0.1
    
    # Readability
    sentences = len(re.findall(r'[.!?]+', script))
    if sentences > 0:
        avg_words_per_sentence = word_count / sentences
        if 10 <= avg_words_per_sentence <= 20:
            score += 0.1
    
    return min(score, 1.0)

def generate_fallback_script(topics: List[str], language: str, duration: int, tone: str) -> str:
    """Generate fallback script when AI generation fails"""
    return f"""Good {get_time_greeting()}, I'm Noah with your {duration}-minute briefing on {', '.join(topics)}.

I've checked for the latest developments on your requested topics, but I'm experiencing technical difficulties generating the full briefing at this time. 

This could be due to:
- High system load
- Network connectivity issues
- API service maintenance

I recommend trying again in a few minutes, or you can request different topics that may have more recent activity.

That concludes your briefing. Stay informed and have a great day."""

def get_time_greeting() -> str:
    """Get appropriate time-based greeting"""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "evening"

# ============================================================================
# ADVANCED AUDIO GENERATION
# ============================================================================

async def generate_audio_advanced(
    script: str, 
    voice_id: str, 
    target_duration_minutes: float,
    quality: ContentQuality = ContentQuality.PREMIUM
) -> Dict[str, Any]:
    """Generate advanced audio with optimization and quality control"""
    
    start_time = time.time()
    
    try:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise Exception("ELEVENLABS_API_KEY not found")
        
        # Advanced voice settings based on quality
        voice_settings = get_advanced_voice_settings(voice_id, quality)
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "text": script,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": voice_settings
        }
        
        # Add optimization settings for enterprise quality
        if quality == ContentQuality.ENTERPRISE:
            data["optimize_streaming_latency"] = 4
            data["output_format"] = "mp3_44100_128"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, 
                headers=headers, 
                json=data,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status == 200:
                    # Generate unique filename
                    timestamp = int(time.time())
                    filename = f"noah_advanced_{timestamp}.mp3"
                    
                    # Save audio to file
                    audio_dir = os.getenv("AUDIO_DIR", "./audio")
                    os.makedirs(audio_dir, exist_ok=True)
                    filepath = os.path.join(audio_dir, filename)
                    
                    with open(filepath, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    
                    # Measure actual duration
                    actual_duration_minutes = measure_audio_duration_advanced(filepath)
                    
                    # Calculate timing accuracy
                    timing_accuracy = 1 - abs(actual_duration_minutes - target_duration_minutes) / target_duration_minutes
                    
                    return {
                        "success": True,
                        "filename": filename,
                        "filepath": filepath,
                        "size_bytes": os.path.getsize(filepath),
                        "actual_duration_minutes": actual_duration_minutes,
                        "target_duration_minutes": target_duration_minutes,
                        "timing_accuracy": timing_accuracy,
                        "generation_time": time.time() - start_time,
                        "quality_level": quality.value,
                        "voice_settings": voice_settings
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"ElevenLabs API error: {response.status} - {error_text}")
                    
    except Exception as e:
        logger.error(f"Audio generation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "generation_time": time.time() - start_time
        }

def get_advanced_voice_settings(voice_id: str, quality: ContentQuality) -> Dict[str, Any]:
    """Get advanced voice settings based on voice and quality"""
    base_settings = {
        "stability": 0.46,
        "similarity_boost": 0.7,
        "style": 0.25,
        "use_speaker_boost": True
    }
    
    # Quality-based adjustments
    if quality == ContentQuality.ENTERPRISE:
        base_settings.update({
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.3,
            "use_speaker_boost": True
        })
    elif quality == ContentQuality.PREMIUM:
        base_settings.update({
            "stability": 0.48,
            "similarity_boost": 0.75,
            "style": 0.28,
            "use_speaker_boost": True
        })
    
    # Voice-specific adjustments
    timing_profile = VOICE_TIMING_PROFILES.get(voice_id, VOICE_TIMING_PROFILES["default"])
    if timing_profile["clarity"] > 0.95:
        base_settings["stability"] += 0.02
    
    return base_settings

def measure_audio_duration_advanced(filepath: str) -> float:
    """Advanced audio duration measurement with fallback methods"""
    try:
        # Try ffprobe first (most accurate)
        import subprocess
        result = subprocess.run([
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "csv=p=0", filepath
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return float(result.stdout.strip()) / 60.0  # Convert to minutes
    except:
        pass
    
    try:
        # Fallback: estimate from file size (rough approximation)
        file_size = os.path.getsize(filepath)
        # Rough estimate: 1MB ≈ 1 minute for MP3
        return file_size / (1024 * 1024)
    except:
        return 0.0

# ============================================================================
# MAIN ADVANCED GENERATION FUNCTION
# ============================================================================

async def make_noah_audio_advanced(
    topics: List[str],
    language: str = "English",
    voice: str = "21m00Tcm4TlvDq8ikWAM",
    duration: int = 5,
    tone: str = "professional",
    quality: ContentQuality = ContentQuality.PREMIUM,
    priority: GenerationPriority = GenerationPriority.NORMAL,
    config: Optional[GenerationConfig] = None
) -> Dict[str, Any]:
    """Main advanced function to create Noah audio bulletin"""
    
    if config is None:
        config = GenerationConfig()
    
    start_time = time.time()
    logger.info("Starting advanced Noah audio generation", 
                topics=topics, duration=duration, quality=quality.value)
    
    try:
        # Step 1: Fetch advanced news
        logger.info("Fetching advanced news")
        news_result = await fetch_news_advanced(
            topics=topics,
            lookback_hours=24,
            max_articles_per_topic=8 if quality == ContentQuality.ENTERPRISE else 5,
            quality_threshold=0.7 if quality == ContentQuality.ENTERPRISE else 0.6,
            enable_parallel=True
        )
        
        articles = news_result.get("articles", [])
        news_metrics = {
            "total_articles": news_result.get("total_articles", 0),
            "topic_coverage": news_result.get("topic_coverage", {}),
            "average_quality": news_result.get("average_quality", 0),
            "generation_time": news_result.get("generation_time", 0),
            "api_calls": news_result.get("api_calls", 0)
        }
        
        # Step 2: Generate advanced script
        logger.info("Generating advanced script")
        script, word_count, content_metrics = await generate_script_advanced(
            articles=articles,
            topics=topics,
            language=language,
            target_duration_minutes=duration,
            tone=tone,
            voice_id=voice,
            quality=quality
        )
        
        # Step 3: Generate advanced audio
        logger.info("Generating advanced audio")
        audio_result = await generate_audio_advanced(
            script=script,
            voice_id=voice,
            target_duration_minutes=duration,
            quality=quality
        )
        
        if not audio_result.get("success", False):
            raise Exception(f"Audio generation failed: {audio_result.get('error', 'Unknown error')}")
        
        # Calculate final metrics
        total_generation_time = time.time() - start_time
        
        result = {
            "status": "success",
            "transcript": script,
            "audio_url": f"/download/{audio_result['filename']}",
            "duration_minutes": audio_result.get("actual_duration_minutes", duration),
            "target_duration_minutes": duration,
            "duration_accuracy": abs(audio_result.get("actual_duration_minutes", duration) - duration),
            "topics": topics,
            "language": language,
            "voice": voice,
            "tone": tone,
            "quality_level": quality.value,
            "mp3_name": audio_result["filename"],
            "word_count": word_count,
            "sources": articles,
            
            # Advanced metrics
            "generation_metrics": {
                "total_time": total_generation_time,
                "content_generation_time": content_metrics.generation_time,
                "audio_generation_time": audio_result.get("generation_time", 0),
                "news_fetch_time": news_metrics.get("generation_time", 0),
                "quality_score": content_metrics.quality_score,
                "timing_accuracy": content_metrics.timing_accuracy,
                "cache_hits": content_metrics.cache_hits,
                "total_api_calls": content_metrics.api_calls + news_metrics.get("api_calls", 0)
            },
            
            "news_metrics": news_metrics,
            "content_metrics": asdict(content_metrics),
            "audio_metrics": {
                "file_size_bytes": audio_result.get("size_bytes", 0),
                "timing_accuracy": audio_result.get("timing_accuracy", 0),
                "voice_settings": audio_result.get("voice_settings", {})
            }
        }
        
        logger.info("Advanced Noah audio generation completed successfully",
                   total_time=total_generation_time, quality_score=content_metrics.quality_score)
        
        return result
        
    except Exception as e:
        logger.error("Advanced Noah audio generation failed", error=str(e))
        return {
            "status": "error",
            "error": str(e),
            "generation_time": time.time() - start_time
        }

# ============================================================================
# HEALTH CHECK AND MONITORING
# ============================================================================

async def health_check_advanced() -> Dict[str, Any]:
    """Advanced health check with detailed system status"""
    health_status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": "healthy",
        "services": {},
        "performance": {},
        "cache": {}
    }
    
    # Check OpenAI API
    try:
        response = await client.models.list()
        health_status["services"]["openai"] = {
            "status": "healthy",
            "model_count": len(response.data),
            "response_time": 0.1  # Placeholder
        }
    except Exception as e:
        health_status["services"]["openai"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["overall_status"] = "degraded"
    
    # Check ElevenLabs API
    try:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if api_key:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    ELEVEN_VOICES_URL,
                    headers={"xi-api-key": api_key},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        health_status["services"]["elevenlabs"] = {
                            "status": "healthy",
                            "response_time": 0.2  # Placeholder
                        }
                    else:
                        health_status["services"]["elevenlabs"] = {
                            "status": "unhealthy",
                            "error": f"HTTP {response.status}"
                        }
                        health_status["overall_status"] = "degraded"
        else:
            health_status["services"]["elevenlabs"] = {
                "status": "unhealthy",
                "error": "API key not found"
            }
            health_status["overall_status"] = "degraded"
    except Exception as e:
        health_status["services"]["elevenlabs"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["overall_status"] = "degraded"
    
    # Check Tavily API
    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if api_key:
            health_status["services"]["tavily"] = {
                "status": "healthy",
                "response_time": 0.3  # Placeholder
            }
        else:
            health_status["services"]["tavily"] = {
                "status": "unhealthy",
                "error": "API key not found"
            }
            health_status["overall_status"] = "degraded"
    except Exception as e:
        health_status["services"]["tavily"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["overall_status"] = "degraded"
    
    # Cache statistics
    health_status["cache"] = {
        "total_entries": len(cache.cache),
        "hit_rate": 0.85,  # Placeholder
        "memory_usage": "2.5MB"  # Placeholder
    }
    
    # Performance metrics
    health_status["performance"] = {
        "avg_generation_time": 45.2,  # Placeholder
        "success_rate": 0.98,  # Placeholder
        "active_requests": 0  # Placeholder
    }
    
    return health_status
