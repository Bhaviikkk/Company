"""
Production-grade rate limiting using Redis
"""
from typing import Optional, Dict
from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis.asyncio as redis
import time
import logging

logger = logging.getLogger(__name__)

# Redis connection for rate limiting
try:
    redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
except Exception as e:
    logger.warning(f"Redis not available for rate limiting: {e}")
    redis_client = None

class ProductionRateLimiter:
    """Advanced rate limiter with multiple tiers"""
    
    def __init__(self):
        self.limits = {
            "public": "100/hour",
            "authenticated": "1000/hour", 
            "admin": "5000/hour",
            "premium": "10000/hour"
        }
        
        # In-memory fallback if Redis unavailable
        self.memory_store = {}
    
    def get_identifier(self, request: Request) -> str:
        """Get rate limit identifier from request"""
        
        # Check for API key in headers
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"
        
        # Check for JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            return f"token:{token[:10]}"  # Use first 10 chars of token
        
        # Fallback to IP address
        return f"ip:{get_remote_address(request)}"
    
    def get_user_tier(self, request: Request) -> str:
        """Determine user tier for rate limiting"""
        
        # Check authentication
        auth_header = request.headers.get("Authorization")
        api_key = request.headers.get("X-API-Key")
        
        if auth_header or api_key:
            # TODO: Verify token/API key and determine tier
            # For now, assume authenticated users
            return "authenticated"
        
        return "public"
    
    async def check_rate_limit(self, request: Request) -> bool:
        """Check if request is within rate limits"""
        
        identifier = self.get_identifier(request)
        tier = self.get_user_tier(request)
        limit = self.limits.get(tier, self.limits["public"])
        
        # Parse limit (e.g., "100/hour")
        count, period = limit.split("/")
        count = int(count)
        
        period_seconds = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }.get(period, 3600)
        
        current_time = int(time.time())
        window_start = current_time - period_seconds
        
        if redis_client:
            try:
                # Use Redis sliding window
                pipe = redis_client.pipeline()
                pipe.zremrangebyscore(identifier, 0, window_start)
                pipe.zcard(identifier)
                pipe.zadd(identifier, {str(current_time): current_time})
                pipe.expire(identifier, period_seconds)
                
                results = await pipe.execute()
                current_requests = results[1]
                
                if current_requests >= count:
                    raise RateLimitExceeded(detail=f"Rate limit exceeded: {limit}")
                
                return True
                
            except Exception as e:
                logger.error(f"Redis rate limiting error: {e}")
                # Fallback to memory store
                return self._memory_rate_limit(identifier, count, period_seconds)
        
        else:
            return self._memory_rate_limit(identifier, count, period_seconds)
    
    def _memory_rate_limit(self, identifier: str, count: int, period_seconds: int) -> bool:
        """Fallback in-memory rate limiting"""
        
        current_time = time.time()
        
        if identifier not in self.memory_store:
            self.memory_store[identifier] = []
        
        # Clean old entries
        self.memory_store[identifier] = [
            timestamp for timestamp in self.memory_store[identifier]
            if current_time - timestamp < period_seconds
        ]
        
        # Check limit
        if len(self.memory_store[identifier]) >= count:
            raise RateLimitExceeded(detail=f"Rate limit exceeded")
        
        # Add current request
        self.memory_store[identifier].append(current_time)
        return True

# Global rate limiter
production_limiter = ProductionRateLimiter()

# Limiter instance for FastAPI
limiter = Limiter(key_func=get_remote_address)

# Rate limiting decorator
def rate_limit(limit: str):
    """Decorator for rate limiting endpoints"""
    def decorator(func):
        return limiter.limit(limit)(func)
    return decorator