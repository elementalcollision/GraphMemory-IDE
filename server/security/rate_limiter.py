"""
Advanced Rate Limiting System for GraphMemory-IDE

This module implements a production-ready rate limiting system using:
- Token bucket algorithm for smooth rate limiting
- Redis backend for distributed rate limiting
- Multiple rate tiers (per-second, per-minute, per-hour)
- FastAPI middleware integration
- Configurable limits per endpoint
- Rate limit headers in responses

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

import asyncio
import time
import json
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict

import aioredis
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..core.config import settings
from ..core.logger import logger


class RateLimitType(Enum):
    """Rate limit types with their time windows in seconds."""
    PER_SECOND = 1
    PER_MINUTE = 60
    PER_HOUR = 3600
    PER_DAY = 86400


@dataclass
class RateLimitRule:
    """Configuration for a rate limit rule."""
    endpoint: str
    rate_type: RateLimitType
    max_requests: int
    burst_allowance: int = 0  # Extra requests allowed in burst
    description: str = ""


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None


class TokenBucket:
    """
    Token bucket implementation for rate limiting.
    
    The token bucket algorithm allows for burst traffic while maintaining
    an average rate limit over time.
    """
    
    def __init__(self, capacity: int, refill_rate: float, burst_allowance: int = 0) -> None:
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
            burst_allowance: Additional tokens for burst traffic
        """
        self.capacity = capacity + burst_allowance
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False otherwise
        """
        now = time.time()
        
        # Add tokens based on elapsed time
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        
        # Check if we have enough tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False
    
    def get_available_tokens(self) -> int:
        """Get current number of available tokens."""
        now = time.time()
        elapsed = now - self.last_refill
        current_tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        return int(current_tokens)


class AdvancedRateLimiter:
    """
    Advanced rate limiter with Redis backend and multiple algorithms.
    
    Features:
    - Distributed rate limiting across multiple servers
    - Multiple rate limit tiers
    - Token bucket algorithm for smooth limiting
    - Sliding window counters for accuracy
    - Per-user and global rate limiting
    """
    
    def __init__(self, redis_url: str) -> None:
        """Initialize rate limiter with Redis connection."""
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.local_buckets: Dict[str, TokenBucket] = {}
        
        # Default rate limit rules
        self.rules: List[RateLimitRule] = [
            RateLimitRule("/api/chat", RateLimitType.PER_MINUTE, 30, 5, "Chat API rate limit"),
            RateLimitRule("/api/memory", RateLimitType.PER_MINUTE, 60, 10, "Memory API rate limit"),
            RateLimitRule("/api/upload", RateLimitType.PER_HOUR, 100, 20, "File upload rate limit"),
            RateLimitRule("/api/auth", RateLimitType.PER_MINUTE, 10, 2, "Authentication rate limit"),
            RateLimitRule("*", RateLimitType.PER_MINUTE, 120, 20, "Global rate limit"),
        ]
    
    async def initialize(self) -> None:
        """Initialize rate limiter with Redis connection"""
        try:
            if self.redis_url:
                self.redis_client = await aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_timeout=5.0,
                    socket_connect_timeout=5.0
                )
                # Test connection
                await self.redis_client.ping()
                self.storage_type = "redis"
                logger.info("Rate limiter initialized with Redis storage")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory storage.")
            self.storage_type = "memory"
            self.rate_limits = {}
            self.request_counts = defaultdict(list)
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.aclose()
    
    def get_rate_limit_key(self, identifier: str, rule: RateLimitRule) -> str:
        """Generate Redis key for rate limit tracking."""
        window = int(time.time()) // rule.rate_type.value
        return f"rate_limit:{rule.endpoint}:{identifier}:{rule.rate_type.name}:{window}"
    
    def get_user_identifier(self, request: Request) -> str:
        """
        Extract user identifier for rate limiting.
        
        Priority:
        1. Authenticated user ID
        2. API key
        3. IP address
        """
        # Try to get user ID from authentication
        if hasattr(request.state, 'user') and request.state.user:
            return f"user:{request.state.user.id}"
        
        # Try to get API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key[:10]}"  # Use first 10 chars for privacy
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def find_matching_rule(self, endpoint: str) -> Optional[RateLimitRule]:
        """Find the most specific rate limit rule for an endpoint."""
        # Look for exact match first
        for rule in self.rules:
            if rule.endpoint == endpoint:
                return rule
        
        # Look for wildcard matches
        for rule in self.rules:
            if rule.endpoint == "*":
                return rule
        
        return None
    
    async def check_rate_limit_redis(self, key: str, rule: RateLimitRule) -> RateLimitResult:
        """Check rate limit using Redis sliding window."""
        try:
            pipe = self.redis_client.pipeline()
            
            # Current time window
            now = time.time()
            window_start = int(now) - rule.rate_type.value
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiration
            pipe.expire(key, rule.rate_type.value + 10)
            
            results = await pipe.execute()
            current_count = results[1]
            
            # Check if limit exceeded
            allowed = current_count < rule.max_requests
            remaining = max(0, rule.max_requests - current_count - 1)
            
            # Calculate reset time
            reset_time = int(now) + rule.rate_type.value
            
            # Calculate retry after if limit exceeded
            retry_after = None
            if not allowed:
                retry_after = rule.rate_type.value
            
            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_time=reset_time,
                retry_after=retry_after
            )
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fall back to local check
            return await self.check_rate_limit_local(key, rule)
    
    async def check_rate_limit_local(self, key: str, rule: RateLimitRule) -> RateLimitResult:
        """Check rate limit using local token bucket."""
        # Get or create token bucket
        if key not in self.local_buckets:
            self.local_buckets[key] = TokenBucket(
                capacity=rule.max_requests,
                refill_rate=rule.max_requests / rule.rate_type.value,
                burst_allowance=rule.burst_allowance
            )
        
        bucket = self.local_buckets[key]
        allowed = bucket.consume(1)
        remaining = bucket.get_available_tokens()
        
        # Calculate reset time
        reset_time = int(time.time()) + rule.rate_type.value
        
        # Calculate retry after if limit exceeded
        retry_after = None
        if not allowed:
            retry_after = int(rule.rate_type.value / rule.max_requests)
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=reset_time,
            retry_after=retry_after
        )
    
    async def check_rate_limit(self, request: Request) -> Tuple[bool, Dict[str, str]]:
        """
        Check if request should be rate limited.
        
        Returns:
            Tuple of (allowed, headers) where headers contain rate limit info
        """
        try:
            # Get user identifier
            identifier = self.get_user_identifier(request)
            
            # Find matching rule
            endpoint = str(request.url.path)
            rule = self.find_matching_rule(endpoint)
            
            if not rule:
                # No rate limit rule found, allow request
                return True, {}
            
            # Generate rate limit key
            key = self.get_rate_limit_key(identifier, rule)
            
            # Check rate limit
            if self.redis_client:
                result = await self.check_rate_limit_redis(key, rule)
            else:
                result = await self.check_rate_limit_local(key, rule)
            
            # Prepare response headers
            headers = {
                "X-RateLimit-Limit": str(rule.max_requests),
                "X-RateLimit-Remaining": str(result.remaining),
                "X-RateLimit-Reset": str(result.reset_time),
                "X-RateLimit-Type": rule.rate_type.name,
            }
            
            if result.retry_after:
                headers["Retry-After"] = str(result.retry_after)
            
            return result.allowed, headers
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # On error, allow request but log the issue
            return True, {}
    
    def add_rule(self, rule: RateLimitRule) -> None:
        """Add a new rate limit rule."""
        self.rules.append(rule)
        logger.info(f"Added rate limit rule: {rule.endpoint} - {rule.max_requests}/{rule.rate_type.name}")
    
    def remove_rule(self, endpoint: str, rate_type: RateLimitType) -> None:
        """Remove a rate limit rule."""
        self.rules = [
            rule for rule in self.rules 
            if not (rule.endpoint == endpoint and rule.rate_type == rate_type)
        ]
        logger.info(f"Removed rate limit rule: {endpoint} - {rate_type.name}")
    
    async def get_rate_limit_status(self, request: Request) -> Dict:
        """Get current rate limit status for debugging."""
        identifier = self.get_user_identifier(request)
        endpoint = str(request.url.path)
        rule = self.find_matching_rule(endpoint)
        
        if not rule:
            return {"status": "no_rule", "endpoint": endpoint}
        
        key = self.get_rate_limit_key(identifier, rule)
        
        if self.redis_client:
            try:
                count = await self.redis_client.zcard(key)
                return {
                    "status": "active",
                    "endpoint": endpoint,
                    "identifier": identifier,
                    "current_count": count,
                    "limit": rule.max_requests,
                    "window": rule.rate_type.name,
                    "remaining": max(0, rule.max_requests - count)
                }
            except Exception as e:
                logger.error(f"Failed to get rate limit status: {e}")
        
        return {"status": "local_mode", "endpoint": endpoint}

    def normalize_timeframe(self, timeframe: str) -> float:
        """Convert timeframe string to seconds"""
        if timeframe.endswith('s'):
            return float(timeframe[:-1])
        elif timeframe.endswith('m'):
            return float(timeframe[:-1]) * 60
        elif timeframe.endswith('h'):
            return float(timeframe[:-1]) * 3600
        elif timeframe.endswith('d'):
            return float(timeframe[:-1]) * 86400
        else:
            return float(timeframe)  # assume seconds

    def calculate_reset_time(self, timeframe_seconds: float) -> float:
        """Calculate time until rate limit resets"""
        now = time.time()
        window_start = now - timeframe_seconds
        return min(timeframe_seconds, max(1.0, timeframe_seconds - (now - window_start)))

    def calculate_retry_after(self, rule: RateLimitRule) -> float:
        """Calculate retry-after time for rate limited requests"""
        timeframe_seconds = self.normalize_timeframe(rule.timeframe)
        return min(timeframe_seconds, max(1.0, timeframe_seconds * 0.1))  # 10% of timeframe or 1 second minimum


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""
    
    def __init__(self, app: ASGIApp, rate_limiter: AdvancedRateLimiter) -> None:
        super().__init__(app)
        self.rate_limiter = rate_limiter
    
    async def dispatch(self, request: Request, call_next) -> None:
        """Process request through rate limiter."""
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/metrics"] or request.url.path.startswith("/static"):
            return await call_next(request)
        
        # Check rate limit
        allowed, headers = await self.rate_limiter.check_rate_limit(request)
        
        if not allowed:
            # Rate limit exceeded
            logger.warning(
                f"Rate limit exceeded for {self.rate_limiter.get_user_identifier(request)} "
                f"on {request.url.path}"
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": headers.get("Retry-After", "60")
                },
                headers=headers
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


# Global rate limiter instance
rate_limiter = AdvancedRateLimiter(settings.RATE_LIMIT_REDIS_URL)


async def initialize_rate_limiter() -> None:
    """Initialize the global rate limiter."""
    await rate_limiter.initialize()


async def close_rate_limiter() -> None:
    """Close the global rate limiter."""
    await rate_limiter.close()


def get_rate_limiter() -> AdvancedRateLimiter:
    """Get the global rate limiter instance."""
    return rate_limiter 