# performance_monitor.py - Performance monitoring for ultra-fast Noah
import time
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
import os

class PerformanceMonitor:
    def __init__(self):
        self.metrics_file = "performance_metrics.json"
        self.metrics = {
            "generation_times": [],
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": [],
            "total_requests": 0,
            "successful_requests": 0,
            "average_generation_time": 0.0,
            "fastest_generation": float('inf'),
            "slowest_generation": 0.0,
            "performance_trends": []
        }
        self.load_metrics()
    
    def load_metrics(self):
        """Load performance metrics from file"""
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, 'r') as f:
                    self.metrics = json.load(f)
        except:
            pass
    
    def save_metrics(self):
        """Save performance metrics to file"""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
        except:
            pass
    
    def record_generation(self, start_time: float, end_time: float, 
                         cache_hit: bool, topics: List[str], duration: int,
                         success: bool, error: str = None):
        """Record generation performance metrics"""
        generation_time = end_time - start_time
        
        # Update basic metrics
        self.metrics["total_requests"] += 1
        if success:
            self.metrics["successful_requests"] += 1
        
        if cache_hit:
            self.metrics["cache_hits"] += 1
        else:
            self.metrics["cache_misses"] += 1
        
        # Record generation time
        generation_record = {
            "timestamp": datetime.now().isoformat(),
            "generation_time": generation_time,
            "topics": topics,
            "duration": duration,
            "cache_hit": cache_hit,
            "success": success
        }
        
        self.metrics["generation_times"].append(generation_record)
        
        # Keep only last 1000 records
        if len(self.metrics["generation_times"]) > 1000:
            self.metrics["generation_times"] = self.metrics["generation_times"][-1000:]
        
        # Update performance stats
        if success:
            self.metrics["fastest_generation"] = min(self.metrics["fastest_generation"], generation_time)
            self.metrics["slowest_generation"] = max(self.metrics["slowest_generation"], generation_time)
            
            # Calculate average
            recent_times = [r["generation_time"] for r in self.metrics["generation_times"][-100:] if r["success"]]
            if recent_times:
                self.metrics["average_generation_time"] = sum(recent_times) / len(recent_times)
        
        # Record errors
        if not success and error:
            error_record = {
                "timestamp": datetime.now().isoformat(),
                "error": error,
                "topics": topics,
                "duration": duration
            }
            self.metrics["errors"].append(error_record)
            
            # Keep only last 100 errors
            if len(self.metrics["errors"]) > 100:
                self.metrics["errors"] = self.metrics["errors"][-100:]
        
        # Update performance trends
        self.update_performance_trends()
        
        # Save metrics
        self.save_metrics()
    
    def update_performance_trends(self):
        """Update performance trends over time"""
        now = datetime.now()
        
        # Calculate hourly performance
        hour_ago = now - timedelta(hours=1)
        recent_generations = [
            g for g in self.metrics["generation_times"]
            if datetime.fromisoformat(g["timestamp"]) > hour_ago and g["success"]
        ]
        
        if recent_generations:
            avg_time = sum(g["generation_time"] for g in recent_generations) / len(recent_generations)
            cache_hit_rate = sum(1 for g in recent_generations if g["cache_hit"]) / len(recent_generations)
            
            trend = {
                "timestamp": now.isoformat(),
                "hourly_average_time": avg_time,
                "cache_hit_rate": cache_hit_rate,
                "request_count": len(recent_generations)
            }
            
            self.metrics["performance_trends"].append(trend)
            
            # Keep only last 168 trends (1 week of hourly data)
            if len(self.metrics["performance_trends"]) > 168:
                self.metrics["performance_trends"] = self.metrics["performance_trends"][-168:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary"""
        recent_generations = [g for g in self.metrics["generation_times"][-100:] if g["success"]]
        
        if not recent_generations:
            return {
                "status": "No data available",
                "total_requests": self.metrics["total_requests"],
                "cache_stats": {
                    "hits": self.metrics["cache_hits"],
                    "misses": self.metrics["cache_misses"],
                    "hit_rate": 0.0
                }
            }
        
        recent_times = [g["generation_time"] for g in recent_generations]
        
        summary = {
            "status": "operational",
            "total_requests": self.metrics["total_requests"],
            "successful_requests": self.metrics["successful_requests"],
            "success_rate": self.metrics["successful_requests"] / max(self.metrics["total_requests"], 1) * 100,
            "performance": {
                "average_generation_time": sum(recent_times) / len(recent_times),
                "fastest_generation": self.metrics["fastest_generation"],
                "slowest_generation": self.metrics["slowest_generation"],
                "recent_count": len(recent_generations)
            },
            "cache_stats": {
                "hits": self.metrics["cache_hits"],
                "misses": self.metrics["cache_misses"],
                "hit_rate": self.metrics["cache_hits"] / max(self.metrics["cache_hits"] + self.metrics["cache_misses"], 1) * 100
            },
            "recent_performance": {
                "last_10_avg": sum(recent_times[-10:]) / min(len(recent_times), 10),
                "last_50_avg": sum(recent_times[-50:]) / min(len(recent_times), 50),
                "trend": "improving" if len(recent_times) >= 2 and recent_times[-1] < recent_times[-2] else "stable"
            }
        }
        
        return summary
    
    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        return {
            "summary": self.get_performance_summary(),
            "recent_generations": self.metrics["generation_times"][-50:],
            "recent_errors": self.metrics["errors"][-20:],
            "performance_trends": self.metrics["performance_trends"][-24:],  # Last 24 hours
            "cache_performance": {
                "total_cache_operations": self.metrics["cache_hits"] + self.metrics["cache_misses"],
                "cache_efficiency": self.metrics["cache_hits"] / max(self.metrics["cache_hits"] + self.metrics["cache_misses"], 1) * 100
            }
        }
    
    def reset_metrics(self):
        """Reset all performance metrics"""
        self.metrics = {
            "generation_times": [],
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": [],
            "total_requests": 0,
            "successful_requests": 0,
            "average_generation_time": 0.0,
            "fastest_generation": float('inf'),
            "slowest_generation": 0.0,
            "performance_trends": []
        }
        self.save_metrics()
    
    def export_metrics(self, filename: str = None):
        """Export metrics to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_export_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.get_detailed_metrics(), f, indent=2)
            return filename
        except Exception as e:
            print(f"Error exporting metrics: {e}")
            return None

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Decorator for monitoring function performance
def monitor_performance(func):
    """Decorator to monitor function performance"""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        success = False
        error = None
        
        try:
            result = await func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            error = str(e)
            raise
        finally:
            end_time = time.time()
            
            # Extract topics and duration from args/kwargs if available
            topics = []
            duration = 5
            
            if args and hasattr(args[0], 'topics'):
                topics = args[0].topics
            elif 'topics' in kwargs:
                topics = kwargs['topics']
            
            if 'duration' in kwargs:
                duration = kwargs['duration']
            
            # Record metrics
            performance_monitor.record_generation(
                start_time, end_time, False, topics, duration, success, error
            )
    
    return wrapper
