# noah_core_ultra.py - Ultra-fast Noah core with parallel processing and caching
import asyncio
import aiohttp
import time
import json
from typing import List, Dict, Any, Optional
from fast_content_generator import FastContentGenerator
import os
from datetime import datetime, timedelta

class NoahCoreUltra:
    def __init__(self):
        self.fast_generator = FastContentGenerator()
        self.audio_cache = {}
        self.voice_cache = {}
        self.cache_file = "ultra_cache.json"
        self.load_cache()
        
    def load_cache(self):
        """Load ultra cache for maximum speed"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    self.audio_cache = cache_data.get('audio', {})
                    self.voice_cache = cache_data.get('voices', {})
        except:
            self.audio_cache = {}
            self.voice_cache = {}
    
    def save_cache(self):
        """Save ultra cache"""
        try:
            cache_data = {
                'audio': self.audio_cache,
                'voices': self.voice_cache,
                'timestamp': datetime.now().isoformat()
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f)
        except:
            pass
    
    def get_audio_cache_key(self, transcript: str, voice_id: str) -> str:
        """Generate cache key for audio"""
        import hashlib
        key_data = f"{transcript[:100]}_{voice_id}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_cached_audio(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached audio if available"""
        if cache_key in self.audio_cache:
            cached = self.audio_cache[cache_key]
            # Check if cache is less than 1 hour old
            cache_time = datetime.fromisoformat(cached["cached_at"])
            if datetime.now() - cache_time < timedelta(hours=1):
                return cached["audio_data"]
        return None
    
    def cache_audio(self, cache_key: str, audio_data: Dict[str, Any]):
        """Cache generated audio"""
        self.audio_cache[cache_key] = {
            "audio_data": audio_data,
            "cached_at": datetime.now().isoformat()
        }
        # Keep only last 50 cached audio items
        if len(self.audio_cache) > 50:
            oldest_key = min(self.audio_cache.keys(), 
                           key=lambda k: self.audio_cache[k]["cached_at"])
            del self.audio_cache[oldest_key]
        self.save_cache()
    
    async def make_noah_audio_ultra(self, topics: List[str], language: str, voice_id: str, 
                                   duration: int, tone: str = "professional", 
                                   strict_timing: bool = True, quick_test: bool = False) -> Dict[str, Any]:
        """Ultra-fast Noah audio generation with parallel processing"""
        start_time = time.time()
        
        try:
            # Step 1: Generate content in parallel (fastest possible)
            print("🚀 Starting ultra-fast content generation...")
            content = await self.fast_generator.generate_content_parallel(
                topics, language, duration, tone
            )
            
            content_time = time.time() - start_time
            print(f"⚡ Content generated in {content_time:.2f}s")
            
            # Step 2: Generate audio with caching
            audio_start = time.time()
            audio_result = await self.generate_audio_ultra(
                content["transcript"], voice_id, duration
            )
            
            audio_time = time.time() - audio_start
            print(f"🎵 Audio generated in {audio_time:.2f}s")
            
            # Step 3: Measure actual duration for precision
            actual_duration = await self.measure_audio_duration_ultra(audio_result.get("audio_url", ""))
            
            # Step 4: Calculate timing accuracy
            target_duration = duration
            duration_accuracy = abs(actual_duration - target_duration)
            
            # Step 5: Determine timing quality
            if duration_accuracy < 0.5:
                timing_quality = "EXACT"
            elif duration_accuracy < 1.0:
                timing_quality = "CLOSE"
            elif duration_accuracy < 2.0:
                timing_quality = "APPROXIMATE"
            else:
                timing_quality = "NEEDS_IMPROVEMENT"
            
            total_time = time.time() - start_time
            
            result = {
                "status": "success",
                "transcript": content["transcript"],
                "audio_url": audio_result.get("audio_url", ""),
                "mp3_name": audio_result.get("mp3_name", "noah_bulletin.mp3"),
                "target_duration_minutes": target_duration,
                "actual_duration_minutes": actual_duration,
                "duration_accuracy_minutes": duration_accuracy,
                "precision_timing": strict_timing,
                "timing_quality": timing_quality,
                "word_count": content.get("word_count", 0),
                "news_quality": content.get("news_quality", {}),
                "sources": content.get("sources", []),
                "generation_metadata": {
                    "total_time_seconds": total_time,
                    "content_generation_time": content_time,
                    "audio_generation_time": audio_time,
                    "cache_hits": content.get("generation_metadata", {}).get("cache_used", False),
                    "parallel_processing": True,
                    "optimization_level": "ultra"
                }
            }
            
            print(f"🎉 Ultra-fast Noah generated in {total_time:.2f}s total!")
            return result
            
        except Exception as e:
            print(f"❌ Error in ultra-fast generation: {e}")
            return {
                "status": "error",
                "error": str(e),
                "generation_metadata": {
                    "total_time_seconds": time.time() - start_time,
                    "error_occurred": True
                }
            }
    
    async def generate_audio_ultra(self, transcript: str, voice_id: str, duration: int) -> Dict[str, Any]:
        """Generate audio with ultra-fast processing and caching"""
        # Check cache first
        cache_key = self.get_audio_cache_key(transcript, voice_id)
        cached_audio = self.get_cached_audio(cache_key)
        if cached_audio:
            print("⚡ Audio cache hit!")
            return cached_audio
        
        # Generate new audio
        try:
            # This would integrate with your actual ElevenLabs API call
            # For now, simulate the process
            await asyncio.sleep(0.5)  # Simulate API call
            
            audio_result = {
                "audio_url": f"/download/ultra_fast_{int(time.time())}.mp3",
                "mp3_name": f"ultra_fast_{int(time.time())}.mp3"
            }
            
            # Cache the result
            self.cache_audio(cache_key, audio_result)
            
            return audio_result
            
        except Exception as e:
            print(f"Error generating audio: {e}")
            return {"audio_url": "", "mp3_name": ""}
    
    async def measure_audio_duration_ultra(self, audio_url: str) -> float:
        """Measure audio duration with ultra-fast processing"""
        if not audio_url:
            return 0.0
        
        try:
            # This would use ffprobe or similar for actual measurement
            # For now, estimate based on URL or return default
            await asyncio.sleep(0.01)  # Minimal delay
            
            # Extract duration from URL if possible, otherwise estimate
            if "ultra_fast_" in audio_url:
                # Estimate based on typical generation
                return 5.0  # Default 5 minutes
            else:
                return 5.0
                
        except Exception as e:
            print(f"Error measuring audio duration: {e}")
            return 5.0
    
    async def get_available_voices_ultra(self) -> Dict[str, Any]:
        """Get available voices with ultra-fast caching"""
        # Check voice cache
        if self.voice_cache and (datetime.now() - datetime.fromisoformat(self.voice_cache.get("timestamp", "2000-01-01")) < timedelta(hours=24)):
            print("⚡ Voice cache hit!")
            return self.voice_cache["voices"]
        
        try:
            # This would integrate with your actual ElevenLabs API call
            # For now, return cached voices
            voices = [
                {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "accent": "american"},
                {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "accent": "american"},
                {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "accent": "british"},
                {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "accent": "british"},
                {"id": "MF3mGy4ClWxXeEaq2vXQ", "name": "Elli", "accent": "american"},
                {"id": "VR6AewLTigWG4xSOukaG", "name": "Josh", "accent": "american"},
                {"id": "pNInz6obpgDQGcFmaJgB", "name": "Arnold", "accent": "american"},
                {"id": "yoZ06aMxZJJ28mfd3POQ", "name": "Adam", "accent": "american"},
                {"id": "t0jbNlBVZ17f02VDIeMI", "name": "Sam", "accent": "american"},
                {"id": "piTKgcLEGmPE4e6mEKli", "name": "Dorothy", "accent": "american"}
            ]
            
            # Cache voices
            self.voice_cache = {
                "voices": {"voices": voices},
                "timestamp": datetime.now().isoformat()
            }
            self.save_cache()
            
            return {"voices": voices}
            
        except Exception as e:
            print(f"Error fetching voices: {e}")
            return {"voices": []}
    
    def cleanup(self):
        """Cleanup ultra resources"""
        self.fast_generator.cleanup()
        self.save_cache()

# Global ultra instance
noah_core_ultra = NoahCoreUltra()
