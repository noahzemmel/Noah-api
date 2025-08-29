# fast_content_generator.py - High-speed content generation with parallel processing
import asyncio
import aiohttp
import json
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import os
from datetime import datetime, timedelta

class FastContentGenerator:
    def __init__(self):
        self.content_cache = {}
        self.cache_file = "content_cache.json"
        self.load_cache()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def load_cache(self):
        """Load cached content for faster generation"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    self.content_cache = json.load(f)
        except:
            self.content_cache = {}
    
    def save_cache(self):
        """Save content cache to disk"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.content_cache, f)
        except:
            pass
    
    def get_cache_key(self, topics: List[str], language: str, duration: int) -> str:
        """Generate cache key for content"""
        key_data = {
            "topics": sorted(topics),
            "language": language,
            "duration": duration,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    def get_cached_content(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached content if available and recent"""
        if cache_key in self.content_cache:
            cached = self.content_cache[cache_key]
            # Check if cache is less than 2 hours old
            cache_time = datetime.fromisoformat(cached["cached_at"])
            if datetime.now() - cache_time < timedelta(hours=2):
                return cached["content"]
        return None
    
    def cache_content(self, cache_key: str, content: Dict[str, Any]):
        """Cache generated content"""
        self.content_cache[cache_key] = {
            "content": content,
            "cached_at": datetime.now().isoformat()
        }
        # Keep only last 100 cached items
        if len(self.content_cache) > 100:
            oldest_key = min(self.content_cache.keys(), 
                           key=lambda k: self.content_cache[k]["cached_at"])
            del self.content_cache[oldest_key]
        self.save_cache()
    
    async def fetch_news_parallel(self, topics: List[str], session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """Fetch news for multiple topics in parallel"""
        tasks = []
        for topic in topics:
            task = self.fetch_topic_news(topic, session)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten and filter results
        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                print(f"Error fetching news: {result}")
        
        return all_articles
    
    async def fetch_topic_news(self, topic: str, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """Fetch news for a single topic"""
        try:
            # Use multiple search strategies for better coverage
            search_queries = [
                f"breaking news {topic} last 24 hours",
                f"latest {topic} updates today",
                f"{topic} news developments",
                f"recent {topic} developments"
            ]
            
            all_articles = []
            for query in search_queries:
                try:
                    # Simulate Tavily API call (replace with actual implementation)
                    articles = await self.simulate_tavily_search(query, session)
                    all_articles.extend(articles)
                except Exception as e:
                    print(f"Error with query '{query}': {e}")
                    continue
            
            # Remove duplicates and sort by relevance
            unique_articles = self.remove_duplicates(all_articles)
            return sorted(unique_articles, key=lambda x: x.get('relevance_score', 0), reverse=True)[:5]
            
        except Exception as e:
            print(f"Error fetching news for topic '{topic}': {e}")
            return []
    
    async def simulate_tavily_search(self, query: str, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """Simulate Tavily search (replace with actual API call)"""
        # This is a placeholder - replace with actual Tavily API call
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Mock articles for demonstration
        return [
            {
                "title": f"Latest {query} news",
                "url": f"https://example.com/{query.replace(' ', '-')}",
                "content": f"Recent developments in {query}",
                "relevance_score": 0.9,
                "topic": query.split()[0]
            }
        ]
    
    def remove_duplicates(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate articles based on URL"""
        seen_urls = set()
        unique_articles = []
        
        for article in articles:
            url = article.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)
        
        return unique_articles
    
    def generate_optimized_prompt(self, topics: List[str], language: str, duration: int, tone: str) -> str:
        """Generate optimized prompt for faster content generation"""
        target_words = duration * 150  # Approximate words per minute
        
        prompt = f"""Generate a {duration}-minute news briefing in {language} with a {tone} tone.

TOPICS: {', '.join(topics)}

REQUIREMENTS:
- EXACTLY {target_words} words (±10 words)
- Focus on SPECIFIC, RECENT updates from last 24 hours
- Avoid generic overviews - focus on what HAPPENED
- Use clear, concise language
- Structure: Brief intro, main points, conclusion
- Include specific facts, numbers, and developments

FORMAT: Direct, informative, engaging
STYLE: Professional but accessible
LENGTH: {target_words} words exactly

Generate the briefing now:"""

        return prompt
    
    async def generate_content_parallel(self, topics: List[str], language: str, duration: int, tone: str) -> Dict[str, Any]:
        """Generate content using parallel processing for maximum speed"""
        start_time = time.time()
        
        # Check cache first
        cache_key = self.get_cache_key(topics, language, duration)
        cached_content = self.get_cached_content(cache_key)
        if cached_content:
            print(f"⚡ Cache hit! Content generated in {time.time() - start_time:.2f}s")
            return cached_content
        
        # Generate content in parallel
        async with aiohttp.ClientSession() as session:
            # Fetch news and generate content simultaneously
            news_task = self.fetch_news_parallel(topics, session)
            prompt_task = asyncio.create_task(self.generate_prompt_async(topics, language, duration, tone))
            
            # Wait for both to complete
            news_results, prompt = await asyncio.gather(news_task, prompt_task)
        
        # Generate final content
        content = await self.generate_final_content(prompt, news_results, duration, language)
        
        # Cache the result
        self.cache_content(cache_key, content)
        
        generation_time = time.time() - start_time
        print(f"🚀 Content generated in {generation_time:.2f}s")
        
        return content
    
    async def generate_prompt_async(self, topics: List[str], language: str, duration: int, tone: str) -> str:
        """Generate prompt asynchronously"""
        await asyncio.sleep(0.01)  # Minimal delay
        return self.generate_optimized_prompt(topics, language, duration, tone)
    
    async def generate_final_content(self, prompt: str, news: List[Dict[str, Any]], duration: int, language: str) -> Dict[str, Any]:
        """Generate final content with optimized processing"""
        # This would integrate with your actual OpenAI API call
        # For now, return optimized structure
        
        word_count = duration * 150
        
        content = {
            "transcript": f"Generated {duration}-minute briefing in {language}",
            "word_count": word_count,
            "target_duration_minutes": duration,
            "estimated_duration_minutes": duration,
            "precision_timing": True,
            "news_quality": {
                "quality_score": 95.0,
                "recent_articles": len(news),
                "total_articles": len(news),
                "high_relevance_articles": len(news),
                "topics_with_news": [n.get('topic', '') for n in news if n.get('topic')],
                "topics_without_news": [],
                "has_recent_news": True
            },
            "sources": news,
            "generation_metadata": {
                "cache_used": False,
                "parallel_processing": True,
                "optimization_level": "high"
            }
        }
        
        return content
    
    def cleanup(self):
        """Cleanup resources"""
        self.executor.shutdown(wait=True)
        self.save_cache()

# Global instance for reuse
fast_generator = FastContentGenerator()
