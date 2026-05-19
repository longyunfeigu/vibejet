# Caching Patterns - Redis Best Practices

Production-ready caching patterns for FastAPI microservices using Redis.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Configuration Patterns](#configuration-patterns)
- [Basic Operations](#basic-operations)
- [Data Structure Patterns](#data-structure-patterns)
- [Caching Strategies](#caching-strategies)
- [TTL & Invalidation](#ttl--invalidation)
- [Distributed Locking](#distributed-locking)
- [Pub/Sub Patterns](#pubsub-patterns)
- [Performance Optimization](#performance-optimization)
- [Monitoring & Metrics](#monitoring--metrics)
- [Testing Patterns](#testing-patterns)
- [Anti-Patterns](#anti-patterns)

---

## Architecture Overview

### Redis Client Architecture

```
Application Layer (Services)
         ↓
    CacheInterface (Protocol)
         ↓
    RedisClient (Implementation)
         ↓
    aioredis (Driver)
         ↓
    Redis Server
```

### Directory Structure

```
infrastructure/external/cache/
├── __init__.py              # Public exports
├── redis_client.py          # Main Redis client implementation
│   ├── CacheInterface       # Abstract protocol
│   ├── RedisClient          # Full implementation
│   ├── CachePatterns        # High-level caching patterns
│   └── CacheMetrics         # Performance tracking
└── exceptions.py            # Cache-specific exceptions
```

### Core Abstractions

```python
from typing import Protocol, Any, Optional, List
from abc import abstractmethod

class CacheInterface(Protocol):
    """Abstract cache interface for dependency injection."""

    @abstractmethod
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value by key."""
        ...

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value with optional TTL."""
        ...

    @abstractmethod
    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        ...

    @abstractmethod
    async def exists(self, *keys: str) -> int:
        """Check key existence."""
        ...
```

---

## Configuration Patterns

### pydantic-settings Integration

```python
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class RedisSettings(BaseSettings):
    """Redis configuration with sensible defaults."""

    # Connection
    url: Optional[str] = Field(
        default=None,
        description="Redis connection URL (redis://host:port/db)",
    )
    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)
    password: Optional[str] = Field(default=None)

    # Connection pool
    max_connections: int = Field(
        default=10,
        description="Maximum connections in pool",
    )
    socket_timeout: float = Field(
        default=5.0,
        description="Socket timeout in seconds",
    )
    socket_connect_timeout: float = Field(
        default=5.0,
        description="Connection timeout in seconds",
    )

    # Cache behavior
    default_ttl: int = Field(
        default=300,
        description="Default TTL in seconds (5 minutes)",
    )
    namespace: str = Field(
        default="app",
        description="Key prefix for namespace isolation",
    )

    # Lock settings
    lock_auto_renew: bool = Field(default=False)
    lock_renew_interval_ratio: float = Field(default=0.6)
    lock_jitter_ratio: float = Field(default=0.1)

    @property
    def connection_url(self) -> str:
        """Build connection URL."""
        if self.url:
            return self.url
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"

    class Config:
        env_prefix = "REDIS_"

class Settings(BaseSettings):
    redis: RedisSettings = Field(default_factory=RedisSettings)
```

### Environment Variables

```bash
# .env
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=20
REDIS_DEFAULT_TTL=600
REDIS_NAMESPACE=knowledge-hub
REDIS_LOCK_AUTO_RENEW=true
```

### Client Initialization

```python
from infrastructure.external.cache import RedisClient, get_redis_client

# Global client instance
_redis_client: Optional[RedisClient] = None

async def init_redis_client() -> RedisClient:
    """Initialize Redis client on application startup."""
    global _redis_client
    _redis_client = RedisClient(
        url=settings.redis.connection_url,
        namespace=settings.redis.namespace,
        default_ttl=settings.redis.default_ttl,
        max_connections=settings.redis.max_connections,
    )
    await _redis_client.connect()
    return _redis_client

async def shutdown_redis_client() -> None:
    """Close Redis client on application shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None

def get_redis_client() -> RedisClient:
    """Get the global Redis client instance."""
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized")
    return _redis_client
```

### FastAPI Lifespan Integration

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    if settings.redis.url:
        await init_redis_client()
        logger.info("redis_client_initialized")

    yield

    # Shutdown
    if settings.redis.url:
        await shutdown_redis_client()
        logger.info("redis_client_closed")

app = FastAPI(lifespan=lifespan)
```

---

## Basic Operations

### String Operations

```python
# Simple get/set
value = await cache.get("user:123")
await cache.set("user:123", {"name": "John", "email": "john@example.com"})

# With TTL
await cache.set("session:abc", session_data, ttl=3600)  # 1 hour

# Conditional set
await cache.set("lock:resource", "1", nx=True)   # Only if not exists
await cache.set("counter", 100, xx=True)         # Only if exists
await cache.set("temp", "data", keepttl=True)    # Preserve existing TTL

# Get and set atomically
old_value = await cache.getset("counter", new_value)

# Batch operations
values = await cache.mget(["user:1", "user:2", "user:3"])
await cache.mset({"user:1": data1, "user:2": data2})

# Counters
count = await cache.incr("page_views")
count = await cache.decr("available_slots")
count = await cache.incrby("score", 10)
```

### Hash Operations

```python
# Single field
await cache.hset("user:123", "name", "John")
name = await cache.hget("user:123", "name")

# Multiple fields
await cache.hset("user:123", mapping={
    "name": "John",
    "email": "john@example.com",
    "role": "admin",
})

# Get all fields
user_data = await cache.hgetall("user:123")
# Returns: {"name": "John", "email": "john@example.com", "role": "admin"}

# Field operations
exists = await cache.hexists("user:123", "email")
await cache.hdel("user:123", "temp_field")
await cache.hincrby("user:123", "login_count", 1)
```

### List Operations

```python
# Push/pop
await cache.lpush("queue:tasks", task1, task2)  # Push to left
await cache.rpush("queue:tasks", task3)          # Push to right
task = await cache.lpop("queue:tasks")           # Pop from left
task = await cache.rpop("queue:tasks")           # Pop from right

# Blocking pop (for queues)
task = await cache.blpop("queue:tasks", timeout=30)

# Range operations
items = await cache.lrange("recent:items", 0, 9)  # First 10 items
length = await cache.llen("queue:tasks")
await cache.ltrim("recent:items", 0, 99)  # Keep only first 100
```

### Set Operations

```python
# Add/remove members
await cache.sadd("tags:article:123", "python", "fastapi", "redis")
await cache.srem("tags:article:123", "deprecated")

# Query operations
members = await cache.smembers("tags:article:123")
is_member = await cache.sismember("tags:article:123", "python")
count = await cache.scard("tags:article:123")

# Set operations
common = await cache.sinter("tags:article:123", "tags:article:456")
all_tags = await cache.sunion("tags:article:123", "tags:article:456")
unique = await cache.sdiff("tags:article:123", "tags:article:456")
```

### Sorted Set Operations

```python
# Add with scores
await cache.zadd("leaderboard", {
    "player1": 1000,
    "player2": 850,
    "player3": 920,
})

# Options: nx (only add new), xx (only update), ch (return changed count)
changed = await cache.zadd("leaderboard", {"player1": 1050}, xx=True, ch=True)

# Range queries
top_10 = await cache.zrange("leaderboard", 0, 9, desc=True, withscores=True)
# Returns: [("player1", 1050), ("player3", 920), ("player2", 850)]

# Ranking and scoring
rank = await cache.zrank("leaderboard", "player2")  # 0-based rank
score = await cache.zscore("leaderboard", "player1")
await cache.zincrby("leaderboard", 50, "player2")  # Increment score
```

---

## Data Structure Patterns

### 1. Session Storage

```python
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import json

@dataclass
class UserSession:
    user_id: str
    email: str
    roles: List[str]
    created_at: datetime
    last_activity: datetime

class SessionStore:
    """Redis-backed session storage."""

    def __init__(self, cache: RedisClient, ttl: int = 3600):
        self._cache = cache
        self._ttl = ttl

    async def create(self, session_id: str, session: UserSession) -> None:
        """Create new session."""
        key = f"session:{session_id}"
        data = {
            **asdict(session),
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
        }
        await self._cache.set(key, data, ttl=self._ttl)

    async def get(self, session_id: str) -> Optional[UserSession]:
        """Get session and refresh TTL."""
        key = f"session:{session_id}"
        data = await self._cache.get(key)
        if data is None:
            return None

        # Refresh TTL on access
        await self._cache.expire(key, self._ttl)

        return UserSession(
            user_id=data["user_id"],
            email=data["email"],
            roles=data["roles"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
        )

    async def update_activity(self, session_id: str) -> bool:
        """Update last activity timestamp."""
        key = f"session:{session_id}"
        if not await self._cache.exists(key):
            return False

        await self._cache.hset(
            key,
            "last_activity",
            datetime.utcnow().isoformat(),
        )
        await self._cache.expire(key, self._ttl)
        return True

    async def destroy(self, session_id: str) -> None:
        """Destroy session."""
        await self._cache.delete(f"session:{session_id}")
```

### 2. Rate Limiter

```python
from dataclasses import dataclass
from typing import Tuple

@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_at: int  # Unix timestamp

class RateLimiter:
    """Sliding window rate limiter using sorted sets."""

    def __init__(
        self,
        cache: RedisClient,
        limit: int = 100,
        window_seconds: int = 60,
    ):
        self._cache = cache
        self._limit = limit
        self._window = window_seconds

    async def check(self, identifier: str) -> RateLimitResult:
        """Check rate limit for identifier."""
        key = f"ratelimit:{identifier}"
        now = time.time()
        window_start = now - self._window

        async with self._cache.pipeline(transaction=True) as pipe:
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            # Add current request
            pipe.zadd(key, {str(now): now})
            # Count requests in window
            pipe.zcard(key)
            # Set expiry
            pipe.expire(key, self._window)

            results = await pipe.execute()

        current_count = results[2]
        allowed = current_count <= self._limit

        return RateLimitResult(
            allowed=allowed,
            remaining=max(0, self._limit - current_count),
            reset_at=int(now + self._window),
        )
```

### 3. Leaderboard

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class LeaderboardEntry:
    user_id: str
    score: float
    rank: int

class Leaderboard:
    """Real-time leaderboard using sorted sets."""

    def __init__(self, cache: RedisClient, name: str):
        self._cache = cache
        self._key = f"leaderboard:{name}"

    async def add_score(self, user_id: str, score: float) -> float:
        """Add or update user score."""
        await self._cache.zadd(self._key, {user_id: score})
        return await self._cache.zscore(self._key, user_id)

    async def increment_score(self, user_id: str, delta: float) -> float:
        """Increment user score."""
        return await self._cache.zincrby(self._key, delta, user_id)

    async def get_rank(self, user_id: str) -> Optional[int]:
        """Get user rank (1-based)."""
        rank = await self._cache.zrevrank(self._key, user_id)
        return rank + 1 if rank is not None else None

    async def get_top(self, count: int = 10) -> List[LeaderboardEntry]:
        """Get top N users."""
        results = await self._cache.zrange(
            self._key,
            0,
            count - 1,
            desc=True,
            withscores=True,
        )
        return [
            LeaderboardEntry(user_id=user_id, score=score, rank=i + 1)
            for i, (user_id, score) in enumerate(results)
        ]

    async def get_around(
        self,
        user_id: str,
        count: int = 5,
    ) -> List[LeaderboardEntry]:
        """Get users around a specific user."""
        rank = await self._cache.zrevrank(self._key, user_id)
        if rank is None:
            return []

        start = max(0, rank - count // 2)
        end = start + count - 1

        results = await self._cache.zrange(
            self._key,
            start,
            end,
            desc=True,
            withscores=True,
        )
        return [
            LeaderboardEntry(user_id=uid, score=score, rank=start + i + 1)
            for i, (uid, score) in enumerate(results)
        ]
```

### 4. Counter with Time Buckets

```python
class TimeSeriesCounter:
    """Counter with time-based buckets for analytics."""

    def __init__(
        self,
        cache: RedisClient,
        name: str,
        bucket_seconds: int = 60,
        retention_buckets: int = 1440,  # 24 hours at 1-minute buckets
    ):
        self._cache = cache
        self._name = name
        self._bucket_seconds = bucket_seconds
        self._retention = retention_buckets

    def _bucket_key(self, timestamp: float) -> str:
        bucket = int(timestamp // self._bucket_seconds)
        return f"counter:{self._name}:{bucket}"

    async def increment(self, value: int = 1) -> int:
        """Increment current bucket."""
        now = time.time()
        key = self._bucket_key(now)
        ttl = self._bucket_seconds * self._retention

        count = await self._cache.incrby(key, value)
        await self._cache.expire(key, ttl)
        return count

    async def get_range(
        self,
        start_time: float,
        end_time: float,
    ) -> List[Tuple[int, int]]:
        """Get counts for time range."""
        results = []
        current = start_time

        while current < end_time:
            key = self._bucket_key(current)
            count = await self._cache.get(key) or 0
            bucket_time = int(current // self._bucket_seconds) * self._bucket_seconds
            results.append((bucket_time, int(count)))
            current += self._bucket_seconds

        return results

    async def get_total(
        self,
        start_time: float,
        end_time: float,
    ) -> int:
        """Get total count for time range."""
        buckets = await self.get_range(start_time, end_time)
        return sum(count for _, count in buckets)
```

---

## Caching Strategies

### 1. Cache-Aside (Lazy Loading)

Most common pattern - application manages cache.

```python
class CacheAsideRepository:
    """Repository with cache-aside pattern."""

    def __init__(
        self,
        cache: RedisClient,
        db: AsyncSession,
        ttl: int = 300,
    ):
        self._cache = cache
        self._db = db
        self._ttl = ttl

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user with cache-aside pattern."""
        cache_key = f"user:{user_id}"

        # 1. Try cache first
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return User(**cached)

        # 2. Cache miss - fetch from database
        user = await self._db.get(User, user_id)
        if user is None:
            return None

        # 3. Populate cache
        await self._cache.set(
            cache_key,
            user.to_dict(),
            ttl=self._ttl,
        )

        return user

    async def update_user(self, user_id: str, data: dict) -> User:
        """Update user and invalidate cache."""
        # 1. Update database
        user = await self._db.get(User, user_id)
        for key, value in data.items():
            setattr(user, key, value)
        await self._db.commit()

        # 2. Invalidate cache
        await self._cache.delete(f"user:{user_id}")

        return user
```

### 2. Write-Through

Writes go through cache to database.

```python
class WriteThroughRepository:
    """Repository with write-through pattern."""

    async def create_user(self, data: CreateUserDTO) -> User:
        """Create user with write-through."""
        # 1. Write to database first
        user = User(**data.dict())
        self._db.add(user)
        await self._db.commit()

        # 2. Write to cache (only if DB succeeded)
        cache_key = f"user:{user.id}"
        await self._cache.set(
            cache_key,
            user.to_dict(),
            ttl=self._ttl,
        )

        return user

    async def update_user(self, user_id: str, data: dict) -> User:
        """Update user with write-through."""
        # 1. Update database
        user = await self._db.get(User, user_id)
        for key, value in data.items():
            setattr(user, key, value)
        await self._db.commit()

        # 2. Update cache (not delete - write-through)
        cache_key = f"user:{user_id}"
        await self._cache.set(
            cache_key,
            user.to_dict(),
            ttl=self._ttl,
        )

        return user
```

### 3. Write-Behind (Write-Back)

Writes to cache immediately, database updated asynchronously.

```python
class WriteBehindRepository:
    """Repository with write-behind pattern."""

    WRITE_QUEUE = "write_queue"

    async def update_user_fast(self, user_id: str, data: dict) -> dict:
        """Fast update via cache, async database write."""
        cache_key = f"user:{user_id}"

        # 1. Update cache immediately
        current = await self._cache.get(cache_key) or {}
        updated = {**current, **data, "updated_at": datetime.utcnow().isoformat()}
        await self._cache.set(cache_key, updated, ttl=self._ttl)

        # 2. Queue for async database write
        await self._cache.rpush(self.WRITE_QUEUE, {
            "operation": "update_user",
            "user_id": user_id,
            "data": data,
            "timestamp": time.time(),
        })

        return updated

    async def process_write_queue(self) -> int:
        """Background worker to process write queue."""
        processed = 0

        while True:
            item = await self._cache.lpop(self.WRITE_QUEUE)
            if item is None:
                break

            if item["operation"] == "update_user":
                user = await self._db.get(User, item["user_id"])
                if user:
                    for key, value in item["data"].items():
                        setattr(user, key, value)
                    await self._db.commit()

            processed += 1

        return processed
```

### 4. Refresh-Ahead (Proactive Refresh)

Proactively refresh cache before expiration.

```python
class RefreshAheadCache:
    """Proactive cache refresh pattern."""

    def __init__(
        self,
        cache: RedisClient,
        ttl: int = 300,
        refresh_threshold: float = 0.8,  # Refresh when 80% TTL elapsed
    ):
        self._cache = cache
        self._ttl = ttl
        self._threshold = refresh_threshold

    async def get_with_refresh(
        self,
        key: str,
        fetch_func: Callable[[], Awaitable[Any]],
    ) -> Any:
        """Get value with proactive refresh."""
        value = await self._cache.get(key)
        remaining_ttl = await self._cache.ttl(key)

        # Calculate if refresh needed
        should_refresh = (
            remaining_ttl > 0 and
            remaining_ttl < self._ttl * (1 - self._threshold)
        )

        if should_refresh:
            # Refresh in background (don't block)
            asyncio.create_task(self._refresh(key, fetch_func))

        if value is None:
            # Full cache miss - fetch synchronously
            value = await fetch_func()
            await self._cache.set(key, value, ttl=self._ttl)

        return value

    async def _refresh(
        self,
        key: str,
        fetch_func: Callable[[], Awaitable[Any]],
    ) -> None:
        """Background refresh task."""
        try:
            value = await fetch_func()
            await self._cache.set(key, value, ttl=self._ttl)
        except Exception as e:
            logger.warning(f"Refresh failed for {key}: {e}")
```

### 5. CachePatterns Utility Class

```python
class CachePatterns:
    """High-level caching patterns for common use cases."""

    def __init__(self, cache: RedisClient):
        self._cache = cache

    async def cache_aside(
        self,
        key: str,
        fetch_func: Callable[[], Awaitable[Any]],
        ttl: Optional[int] = None,
    ) -> Any:
        """Standard cache-aside pattern."""
        value = await self._cache.get(key)
        if value is not None:
            return value

        value = await fetch_func()
        if value is not None:
            await self._cache.set(key, value, ttl=ttl)

        return value

    async def write_through(
        self,
        key: str,
        value: Any,
        write_func: Callable[[Any], Awaitable[bool]],
        ttl: Optional[int] = None,
    ) -> bool:
        """Write-through pattern."""
        success = await write_func(value)
        if success:
            await self._cache.set(key, value, ttl=ttl)
        return success

    async def write_behind(
        self,
        key: str,
        value: Any,
        queue_key: str = "write_queue",
        ttl: Optional[int] = None,
    ) -> bool:
        """Write-behind pattern with queue."""
        success = await self._cache.set(key, value, ttl=ttl)
        if success:
            await self._cache.rpush(queue_key, {
                "key": key,
                "value": value,
                "timestamp": time.time(),
            })
        return success

    async def refresh_ahead(
        self,
        key: str,
        fetch_func: Callable[[], Awaitable[Any]],
        ttl: int,
        refresh_ratio: float = 0.8,
    ) -> Any:
        """Refresh-ahead pattern."""
        value = await self._cache.get(key)
        remaining = await self._cache.ttl(key)

        if remaining > 0 and remaining < ttl * (1 - refresh_ratio):
            new_value = await fetch_func()
            await self._cache.set(key, new_value, ttl=ttl)
            return new_value

        if value is None:
            value = await fetch_func()
            await self._cache.set(key, value, ttl=ttl)

        return value
```

---

## TTL & Invalidation

### TTL Management

```python
# Set TTL on creation
await cache.set("key", value, ttl=3600)  # 1 hour

# Update TTL on existing key
await cache.expire("key", 1800)  # Reset to 30 minutes

# Check remaining TTL
remaining = await cache.ttl("key")
# Returns: positive int (seconds), -1 (no expiry), -2 (not exists)

# Preserve TTL on update
await cache.set("key", new_value, keepttl=True)

# Expiry at specific time
expire_at = datetime.utcnow() + timedelta(hours=24)
await cache.expireat("key", int(expire_at.timestamp()))
```

### Invalidation Patterns

#### 1. Direct Invalidation

```python
async def invalidate_user(user_id: str) -> None:
    """Invalidate specific user cache."""
    await cache.delete(f"user:{user_id}")

async def invalidate_users(user_ids: List[str]) -> int:
    """Batch invalidate multiple users."""
    keys = [f"user:{uid}" for uid in user_ids]
    return await cache.delete(*keys)
```

#### 2. Pattern-Based Invalidation

```python
async def invalidate_by_pattern(pattern: str) -> int:
    """Invalidate keys matching pattern using SCAN."""
    deleted = 0
    async for key in cache.scan_iter(match=pattern):
        await cache.delete(key)
        deleted += 1
    return deleted

# Usage
await invalidate_by_pattern("user:*:profile")  # All user profiles
await invalidate_by_pattern("session:abc*")     # Sessions starting with abc
```

#### 3. Namespace Invalidation

```python
class NamespacedCache:
    """Cache with namespace versioning for mass invalidation."""

    def __init__(self, cache: RedisClient, namespace: str):
        self._cache = cache
        self._namespace = namespace

    async def _get_version(self) -> int:
        """Get current namespace version."""
        version = await self._cache.get(f"{self._namespace}:version")
        return int(version) if version else 1

    async def _key(self, key: str) -> str:
        """Build versioned key."""
        version = await self._get_version()
        return f"{self._namespace}:v{version}:{key}"

    async def get(self, key: str) -> Any:
        return await self._cache.get(await self._key(key))

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        return await self._cache.set(await self._key(key), value, ttl=ttl)

    async def invalidate_all(self) -> None:
        """Invalidate entire namespace by incrementing version."""
        await self._cache.incr(f"{self._namespace}:version")
        # Old keys will naturally expire
```

#### 4. Tag-Based Invalidation

```python
class TaggedCache:
    """Cache with tag-based invalidation."""

    async def set_with_tags(
        self,
        key: str,
        value: Any,
        tags: List[str],
        ttl: int = None,
    ) -> None:
        """Set value with associated tags."""
        # Store value
        await self._cache.set(key, value, ttl=ttl)

        # Associate key with tags
        for tag in tags:
            await self._cache.sadd(f"tag:{tag}", key)

    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all keys with given tag."""
        tag_key = f"tag:{tag}"
        keys = await self._cache.smembers(tag_key)

        if keys:
            deleted = await self._cache.delete(*keys)
            await self._cache.delete(tag_key)
            return deleted
        return 0

# Usage
await cache.set_with_tags(
    "article:123",
    article_data,
    tags=["user:456", "category:tech"],
)

# Invalidate all articles by user
await cache.invalidate_by_tag("user:456")
```

---

## Distributed Locking

### Basic Lock Usage

```python
# Context manager pattern
async with cache.lock("resource:123", timeout=30) as lock:
    # Critical section
    data = await fetch_resource()
    await process_resource(data)
    # Lock automatically released on exit

# Manual lock management
lock = await cache.acquire_lock("resource:123", timeout=30)
try:
    # Critical section
    pass
finally:
    await cache.release_lock(lock)
```

### Lock with Auto-Renewal

```python
class DistributedLock:
    """Distributed lock with automatic renewal."""

    def __init__(
        self,
        cache: RedisClient,
        name: str,
        timeout: int = 30,
        auto_renew: bool = True,
        renew_interval: float = 0.6,  # Renew at 60% of timeout
    ):
        self._cache = cache
        self._name = name
        self._timeout = timeout
        self._auto_renew = auto_renew
        self._renew_interval = renew_interval
        self._token = str(uuid.uuid4())
        self._renewal_task: Optional[asyncio.Task] = None

    async def acquire(self, blocking_timeout: float = None) -> bool:
        """Acquire lock with optional blocking."""
        key = f"lock:{self._name}"
        deadline = time.time() + (blocking_timeout or 0)

        while True:
            # Try to acquire
            acquired = await self._cache.set(
                key,
                self._token,
                ttl=self._timeout,
                nx=True,
            )

            if acquired:
                if self._auto_renew:
                    self._start_renewal()
                return True

            if blocking_timeout is None or time.time() >= deadline:
                return False

            await asyncio.sleep(0.1)

    async def release(self) -> bool:
        """Release lock if we own it."""
        if self._renewal_task:
            self._renewal_task.cancel()

        key = f"lock:{self._name}"
        # Use Lua script for atomic check-and-delete
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        return await self._cache.eval(script, [key], [self._token]) == 1

    def _start_renewal(self) -> None:
        """Start background renewal task."""
        async def renew():
            interval = self._timeout * self._renew_interval
            while True:
                await asyncio.sleep(interval)
                await self._cache.expire(f"lock:{self._name}", self._timeout)

        self._renewal_task = asyncio.create_task(renew())

    async def __aenter__(self):
        if not await self.acquire(blocking_timeout=10):
            raise LockError(f"Could not acquire lock: {self._name}")
        return self

    async def __aexit__(self, *args):
        await self.release()
```

### Lock Patterns

```python
# Prevent duplicate processing
async def process_order(order_id: str) -> None:
    async with cache.lock(f"order:{order_id}", timeout=60):
        order = await get_order(order_id)
        if order.status == "pending":
            await process_payment(order)
            order.status = "processed"
            await save_order(order)

# Rate-limited resource access
async def access_external_api(user_id: str) -> dict:
    lock_key = f"api:ratelimit:{user_id}"
    if not await cache.lock(lock_key, timeout=1, blocking_timeout=0):
        raise RateLimitError("Too many requests")

    try:
        return await external_api.call()
    finally:
        await cache.release_lock(lock_key)
```

---

## Pub/Sub Patterns

### Basic Pub/Sub

```python
# Publisher
await cache.publish("notifications", {
    "type": "new_message",
    "user_id": "123",
    "message_id": "456",
})

# Subscriber
async def message_handler():
    async for message in cache.subscribe("notifications"):
        print(f"Received: {message}")

# Pattern subscription
async for message in cache.psubscribe("user:*:events"):
    user_id = message.channel.split(":")[1]
    print(f"Event for user {user_id}: {message.data}")
```

### Event-Driven Cache Invalidation

```python
class CacheInvalidator:
    """Distributed cache invalidation via Pub/Sub."""

    CHANNEL = "cache:invalidate"

    def __init__(self, cache: RedisClient):
        self._cache = cache
        self._local_cache: Dict[str, Any] = {}

    async def start_listener(self) -> None:
        """Start listening for invalidation messages."""
        async for message in self._cache.subscribe(self.CHANNEL):
            key = message["key"]
            if key in self._local_cache:
                del self._local_cache[key]
                logger.debug(f"Local cache invalidated: {key}")

    async def invalidate(self, key: str) -> None:
        """Invalidate key across all instances."""
        # Invalidate local
        if key in self._local_cache:
            del self._local_cache[key]

        # Invalidate Redis
        await self._cache.delete(key)

        # Notify other instances
        await self._cache.publish(self.CHANNEL, {"key": key})
```

---

## Performance Optimization

### Pipeline for Batch Operations

```python
# Without pipeline: N round trips
for key in keys:
    await cache.get(key)  # Network round trip each time

# With pipeline: 1 round trip
async with cache.pipeline() as pipe:
    for key in keys:
        pipe.get(key)
    results = await pipe.execute()  # Single round trip
```

### Transaction for Atomicity

```python
async with cache.pipeline(transaction=True) as pipe:
    # All commands execute atomically
    pipe.set("balance:123", 1000)
    pipe.hset("user:123", "balance", 1000)
    pipe.zadd("balances", {"user:123": 1000})
    results = await pipe.execute()
```

### Connection Pooling

```python
# Configure in settings
redis_settings = RedisSettings(
    max_connections=20,  # Adjust based on concurrency
    socket_timeout=5.0,
    socket_connect_timeout=5.0,
)

# Connection pool is managed automatically by aioredis
```

### Efficient Key Design

```python
# ✅ Good: Short, descriptive, hierarchical
"u:123"              # User 123
"u:123:sess:abc"     # User 123, session abc
"art:456:views"      # Article 456 views

# ❌ Bad: Long, redundant, non-hierarchical
"user_data_for_user_id_123"
"article_456_page_view_counter"
```

### Compression for Large Values

```python
import zlib
import json

class CompressedCache:
    """Cache with automatic compression for large values."""

    COMPRESSION_THRESHOLD = 1024  # Compress values > 1KB

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        serialized = json.dumps(value).encode()

        if len(serialized) > self.COMPRESSION_THRESHOLD:
            compressed = zlib.compress(serialized)
            await self._cache.set(
                key,
                {"compressed": True, "data": compressed.hex()},
                ttl=ttl,
            )
        else:
            await self._cache.set(key, value, ttl=ttl)

        return True

    async def get(self, key: str) -> Any:
        value = await self._cache.get(key)

        if isinstance(value, dict) and value.get("compressed"):
            compressed = bytes.fromhex(value["data"])
            serialized = zlib.decompress(compressed)
            return json.loads(serialized)

        return value
```

---

## Monitoring & Metrics

### Built-in Metrics

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import List

class CacheStatus(Enum):
    HIT = "hit"
    MISS = "miss"
    ERROR = "error"

@dataclass
class CacheMetrics:
    """Track cache performance metrics."""

    hits: int = 0
    misses: int = 0
    errors: int = 0
    operation_times: List[float] = field(default_factory=list)
    max_samples: int = 1000

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def avg_operation_time(self) -> float:
        if not self.operation_times:
            return 0.0
        return sum(self.operation_times) / len(self.operation_times)

    def record_get(self, status: CacheStatus) -> None:
        if status == CacheStatus.HIT:
            self.hits += 1
        elif status == CacheStatus.MISS:
            self.misses += 1
        else:
            self.errors += 1

    def record_operation_time(self, duration: float) -> None:
        self.operation_times.append(duration)
        if len(self.operation_times) > self.max_samples:
            self.operation_times.pop(0)
```

### Prometheus Integration

```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics
cache_operations = Counter(
    "cache_operations_total",
    "Total cache operations",
    ["operation", "status"],
)
cache_latency = Histogram(
    "cache_latency_seconds",
    "Cache operation latency",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
)
cache_hit_rate = Gauge(
    "cache_hit_rate",
    "Cache hit rate",
)

class MonitoredCache:
    """Redis cache with Prometheus metrics."""

    async def get(self, key: str) -> Any:
        start = time.perf_counter()
        try:
            value = await self._cache.get(key)
            status = "hit" if value is not None else "miss"
            cache_operations.labels(operation="get", status=status).inc()
            return value
        except Exception:
            cache_operations.labels(operation="get", status="error").inc()
            raise
        finally:
            cache_latency.labels(operation="get").observe(
                time.perf_counter() - start
            )

    async def update_hit_rate(self) -> None:
        """Periodically update hit rate gauge."""
        info = await self._cache.info("stats")
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        cache_hit_rate.set(hits / total if total > 0 else 0)
```

### Health Check

```python
async def redis_health_check() -> dict:
    """Health check for Redis connection."""
    try:
        start = time.perf_counter()
        await cache.ping()
        latency = time.perf_counter() - start

        info = await cache.info("memory")

        return {
            "status": "healthy",
            "latency_ms": latency * 1000,
            "memory_used": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
```

---

## Testing Patterns

### Unit Testing with Mock

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_cache():
    """Create mock cache for unit tests."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=1)
    return cache

async def test_cache_aside_miss(mock_cache):
    """Test cache miss triggers fetch."""
    mock_cache.get.return_value = None

    service = UserService(cache=mock_cache)
    user = await service.get_user("123")

    mock_cache.get.assert_called_once_with("user:123")
    mock_cache.set.assert_called_once()

async def test_cache_aside_hit(mock_cache):
    """Test cache hit returns cached value."""
    mock_cache.get.return_value = {"id": "123", "name": "John"}

    service = UserService(cache=mock_cache)
    user = await service.get_user("123")

    mock_cache.get.assert_called_once()
    mock_cache.set.assert_not_called()
    assert user.name == "John"
```

### Integration Testing with Test Containers

```python
import pytest
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer() as redis:
        yield redis

@pytest.fixture
async def redis_client(redis_container):
    client = RedisClient(
        url=f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}",
        namespace="test",
    )
    await client.connect()
    yield client
    await client.flushdb()  # Clean up
    await client.close()

@pytest.mark.integration
async def test_set_and_get(redis_client):
    """Test basic set and get operations."""
    await redis_client.set("test:key", {"value": 123})
    result = await redis_client.get("test:key")

    assert result == {"value": 123}

@pytest.mark.integration
async def test_ttl_expiration(redis_client):
    """Test TTL expiration."""
    await redis_client.set("test:ttl", "value", ttl=1)

    # Should exist immediately
    assert await redis_client.exists("test:ttl") == 1

    # Should expire after 1 second
    await asyncio.sleep(1.5)
    assert await redis_client.exists("test:ttl") == 0
```

### Fake Cache for Tests

```python
class FakeCache:
    """In-memory fake cache for testing."""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._ttls: Dict[str, float] = {}

    async def get(self, key: str, default: Any = None) -> Any:
        if key in self._ttls and time.time() > self._ttls[key]:
            del self._data[key]
            del self._ttls[key]
        return self._data.get(key, default)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        **kwargs,
    ) -> bool:
        self._data[key] = value
        if ttl:
            self._ttls[key] = time.time() + ttl
        return True

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                self._ttls.pop(key, None)
                deleted += 1
        return deleted

    async def exists(self, *keys: str) -> int:
        return sum(1 for key in keys if key in self._data)

    async def clear(self) -> None:
        self._data.clear()
        self._ttls.clear()
```

---

## Anti-Patterns

### ❌ Cache Stampede

```python
# ❌ BAD: Multiple concurrent requests all miss and hit DB
async def get_user(user_id: str) -> User:
    value = await cache.get(f"user:{user_id}")
    if value is None:
        # 100 requests all miss and hit DB simultaneously!
        value = await db.get(user_id)
        await cache.set(f"user:{user_id}", value)
    return value

# ✅ GOOD: Use distributed lock to prevent stampede
async def get_user(user_id: str) -> User:
    key = f"user:{user_id}"
    value = await cache.get(key)
    if value is None:
        lock_key = f"lock:{key}"
        async with cache.lock(lock_key, timeout=5):
            # Double-check after acquiring lock
            value = await cache.get(key)
            if value is None:
                value = await db.get(user_id)
                await cache.set(key, value)
    return value
```

### ❌ Caching Null Values

```python
# ❌ BAD: Don't cache null, causes repeated DB hits
async def get_user(user_id: str) -> Optional[User]:
    value = await cache.get(f"user:{user_id}")
    if value is None:
        value = await db.get(user_id)  # Returns None for non-existent
        if value:  # Don't cache if null
            await cache.set(f"user:{user_id}", value)
    return value

# ✅ GOOD: Cache null with short TTL
NULL_MARKER = "__NULL__"

async def get_user(user_id: str) -> Optional[User]:
    value = await cache.get(f"user:{user_id}")
    if value == NULL_MARKER:
        return None
    if value is None:
        value = await db.get(user_id)
        if value:
            await cache.set(f"user:{user_id}", value, ttl=3600)
        else:
            await cache.set(f"user:{user_id}", NULL_MARKER, ttl=60)  # Short TTL
    return value
```

### ❌ Large Keys/Values

```python
# ❌ BAD: Storing large objects directly
await cache.set("all_users", list_of_10000_users)

# ✅ GOOD: Store references, paginate, or use separate keys
for user in users:
    await cache.set(f"user:{user.id}", user)
await cache.sadd("user_ids", *[u.id for u in users])
```

### ❌ No TTL on Caches

```python
# ❌ BAD: No TTL means stale data forever
await cache.set("user:123", user_data)

# ✅ GOOD: Always set TTL
await cache.set("user:123", user_data, ttl=3600)
```

### ❌ Cache as Primary Storage

```python
# ❌ BAD: Using cache as primary storage
await cache.set("order:123", order)  # No database write!

# ✅ GOOD: Cache is secondary to database
await db.save(order)
await cache.set("order:123", order, ttl=3600)
```

---

## Quick Reference

### Common TTL Values

| Use Case | TTL | Notes |
|----------|-----|-------|
| Session | 24h | Refresh on activity |
| User profile | 1h | Invalidate on update |
| API response | 5m | Balance freshness/load |
| Rate limit | 1m | Sliding window |
| Feature flags | 30s | Quick propagation |
| Static config | 24h | Invalidate on deploy |

### Key Naming Conventions

```
{entity}:{id}                    # user:123
{entity}:{id}:{attribute}        # user:123:profile
{namespace}:{entity}:{id}        # app:user:123
{entity}:{id}:{relation}:{id}    # user:123:orders:456
```

### Troubleshooting

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| High miss rate | Short TTL, poor key design | Increase TTL, review key patterns |
| Memory growth | No TTL, large values | Add TTL, compress values |
| Connection errors | Pool exhausted | Increase pool size |
| Slow operations | Large values, network | Compress, use pipeline |
| Stale data | Missing invalidation | Implement invalidation strategy |

---

## Related Documentation

- [Architecture Overview](architecture-overview.md)
- [Async & Errors](async-and-errors.md)
- [Testing Guide](testing-guide.md)
- [Messaging Patterns](messaging-patterns.md)
