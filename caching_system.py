"""
Advanced Caching System for Phone & Email Validation
Reduces database load and improves response times for large user base
"""
import hashlib
import json
import time
from typing import Optional, Dict, Any
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class ValidationCache:
    """
    In-memory LRU cache for validation results
    Reduces repeated validation calls for common numbers/emails
    """
    
    def __init__(self, max_size: int = 100000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
        self.logger = logging.getLogger(__name__)
        
    def _generate_key(self, validation_type: str, input_data: str) -> str:
        """Generate consistent cache key"""
        # Normalize input for consistent caching
        normalized = input_data.strip().lower()
        key_data = f"{validation_type}:{normalized}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self.access_times:
            return True
        return time.time() - self.access_times[key] > self.ttl_seconds
    
    def _evict_oldest(self):
        """Remove oldest cache entries when at capacity"""
        if len(self.cache) >= self.max_size:
            # Remove 10% of oldest entries
            sorted_keys = sorted(self.access_times.items(), key=lambda x: x[1])
            keys_to_remove = [k for k, _ in sorted_keys[:self.max_size // 10]]
            
            for key in keys_to_remove:
                self.cache.pop(key, None)
                self.access_times.pop(key, None)
    
    def get(self, validation_type: str, input_data: str) -> Optional[Dict[str, Any]]:
        """Get cached validation result"""
        key = self._generate_key(validation_type, input_data)
        
        if key in self.cache and not self._is_expired(key):
            # Update access time for LRU
            self.access_times[key] = time.time()
            self.logger.debug(f"Cache hit for {validation_type}: {input_data[:10]}...")
            return self.cache[key]
        
        # Remove expired entry
        if key in self.cache:
            del self.cache[key]
            del self.access_times[key]
            
        return None
    
    def set(self, validation_type: str, input_data: str, result: Dict[str, Any]):
        """Cache validation result"""
        key = self._generate_key(validation_type, input_data)
        
        # Evict old entries if needed
        self._evict_oldest()
        
        # Store result
        self.cache[key] = result
        self.access_times[key] = time.time()
        
        self.logger.debug(f"Cached result for {validation_type}: {input_data[:10]}...")
    
    def clear(self):
        """Clear all cached entries"""
        self.cache.clear()
        self.access_times.clear()
        self.logger.info("Validation cache cleared")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'entries': len(self.cache),
            'max_size': self.max_size,
            'ttl_seconds': self.ttl_seconds,
            'memory_usage_mb': sum(len(str(v)) for v in self.cache.values()) / 1024 / 1024
        }

# Global cache instance
_validation_cache = None

def get_cache() -> ValidationCache:
    """Get global cache instance"""
    global _validation_cache
    if _validation_cache is None:
        from performance_config import CACHE_MAX_ENTRIES, CACHE_TTL_SECONDS
        _validation_cache = ValidationCache(
            max_size=CACHE_MAX_ENTRIES,
            ttl_seconds=CACHE_TTL_SECONDS
        )
    return _validation_cache

def cached_validation(validation_type: str):
    """
    Decorator for caching validation results
    Usage: @cached_validation('email') or @cached_validation('phone')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, input_data: str, *args, **kwargs):
            from performance_config import CACHE_VALIDATION_RESULTS
            
            if not CACHE_VALIDATION_RESULTS:
                return func(self, input_data, *args, **kwargs)
            
            cache = get_cache()
            
            # Try to get from cache
            cached_result = cache.get(validation_type, input_data)
            if cached_result is not None:
                return cached_result
            
            # Not in cache, perform validation
            result = func(self, input_data, *args, **kwargs)
            
            # Cache the result (convert to dict if needed)
            if hasattr(result, '__dict__'):
                cache_data = result.__dict__.copy()
            else:
                cache_data = result
                
            cache.set(validation_type, input_data, cache_data)
            
            return result
        return wrapper
    return decorator

class DatabaseQueryCache:
    """
    Cache for frequent database queries
    Reduces database load for user lookups, subscription checks, etc.
    """
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
        
    def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user subscription data"""
        key = f"user_sub:{user_id}"
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.ttl_seconds:
                return entry['data']
            else:
                del self.cache[key]
        return None
    
    def set_user_subscription(self, user_id: str, data: Dict[str, Any]):
        """Cache user subscription data"""
        key = f"user_sub:{user_id}"
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }

# Global instances
validation_cache = get_cache()
db_cache = DatabaseQueryCache()

def clear_all_caches():
    """Clear all caches - useful for maintenance"""
    validation_cache.clear()
    db_cache.cache.clear()
    logger.info("All caches cleared")