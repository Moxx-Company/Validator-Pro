"""
Rate limiter for handling enterprise-level concurrent users
"""
import asyncio
import time
from collections import defaultdict
from typing import Dict, Optional

class RateLimiter:
    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests_per_minute = max_requests_per_minute
        self.user_requests: Dict[str, list] = defaultdict(list)
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    async def is_allowed(self, user_id: str) -> bool:
        """Check if user is allowed to make a request"""
        current_time = time.time()
        
        # Cleanup old requests periodically
        if current_time - self.last_cleanup > self.cleanup_interval:
            await self.cleanup_old_requests()
            self.last_cleanup = current_time
        
        # Get user's recent requests
        user_reqs = self.user_requests[user_id]
        
        # Remove requests older than 1 minute
        one_minute_ago = current_time - 60
        user_reqs[:] = [req_time for req_time in user_reqs if req_time > one_minute_ago]
        
        # Check if under limit
        if len(user_reqs) < self.max_requests_per_minute:
            user_reqs.append(current_time)
            return True
        
        return False
    
    async def cleanup_old_requests(self):
        """Clean up old request data"""
        current_time = time.time()
        one_hour_ago = current_time - 3600
        
        # Remove users with no recent activity
        users_to_remove = []
        for user_id, requests in self.user_requests.items():
            if not requests or max(requests) < one_hour_ago:
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del self.user_requests[user_id]

class ValidationQueue:
    def __init__(self, max_concurrent_validations: int = 100):
        self.max_concurrent = max_concurrent_validations
        self.active_validations = 0
        self.queue = asyncio.Queue()
        self.semaphore = asyncio.Semaphore(max_concurrent_validations)
    
    async def acquire(self):
        """Acquire a validation slot"""
        await self.semaphore.acquire()
        self.active_validations += 1
    
    def release(self):
        """Release a validation slot"""
        self.semaphore.release()
        self.active_validations = max(0, self.active_validations - 1)
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.max_concurrent - self.active_validations

# Global instances for enterprise-level rate limiting
rate_limiter = RateLimiter(max_requests_per_minute=120)  # 2 requests per second per user
validation_queue = ValidationQueue(max_concurrent_validations=200)  # 200 concurrent validations