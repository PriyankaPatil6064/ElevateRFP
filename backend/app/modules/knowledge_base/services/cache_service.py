# app/modules/knowledge_base/services/cache_service.py
from typing import Any, Optional, List, Dict, Union
import json
import pickle
import hashlib
from datetime import datetime, timedelta
import asyncio
import structlog
from dataclasses import dataclass, asdict

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from app.config import settings

logger = structlog.get_logger()

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    tags: List[str] = None

class CacheService:
    """Enterprise caching service with multi-level caching"""
    
    def __init__(self):
        self.redis_client = None
        self.memory_cache = {}  # L1 cache
        self.max_memory_size = 1000  # Maximum items in memory cache
        self.default_ttl = 3600  # 1 hour default TTL
        
        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "memory_hits": 0,
            "redis_hits": 0,
            "evictions": 0
        }
        
        # Initialize Redis connection if available
        if REDIS_AVAILABLE:
            self._init_redis()
        
        logger.info("Cache Service initialized", 
                   redis_available=REDIS_AVAILABLE,
                   memory_cache_size=self.max_memory_size)
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False  # We'll handle encoding ourselves
            )
            logger.info("Redis cache initialized", url=settings.REDIS_URL)
        except Exception as e:
            logger.warning("Redis initialization failed", error=str(e))
            self.redis_client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (checks memory first, then Redis)"""
        try:
            # Check memory cache first (L1)
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                
                # Check if expired
                if entry.expires_at and datetime.now() > entry.expires_at:
                    del self.memory_cache[key]
                else:
                    # Update access statistics
                    entry.access_count += 1
                    entry.last_accessed = datetime.now()
                    
                    self.stats["hits"] += 1
                    self.stats["memory_hits"] += 1
                    
                    logger.debug("Memory cache hit", key=key)
                    return entry.value
            
            # Check Redis cache (L2)
            if self.redis_client:
                try:
                    cached_data = await self.redis_client.get(key)
                    if cached_data:
                        # Deserialize data
                        value = pickle.loads(cached_data)
                        
                        # Store in memory cache for faster future access
                        await self._set_memory_cache(key, value, self.default_ttl)
                        
                        self.stats["hits"] += 1
                        self.stats["redis_hits"] += 1
                        
                        logger.debug("Redis cache hit", key=key)
                        return value
                        
                except Exception as e:
                    logger.warning("Redis get failed", key=key, error=str(e))
            
            # Cache miss
            self.stats["misses"] += 1
            logger.debug("Cache miss", key=key)
            return None
            
        except Exception as e:
            logger.error("Cache get failed", key=key, error=str(e))
            return None
    
    async def set(self, 
                 key: str, 
                 value: Any, 
                 ttl: Optional[int] = None,
                 tags: List[str] = None) -> bool:
        """Set value in cache"""
        try:
            ttl = ttl or self.default_ttl
            
            # Set in memory cache (L1)
            await self._set_memory_cache(key, value, ttl, tags)
            
            # Set in Redis cache (L2)
            if self.redis_client:
                try:
                    serialized_value = pickle.dumps(value)
                    await self.redis_client.setex(key, ttl, serialized_value)
                    
                    # Store tags for cache invalidation
                    if tags:
                        for tag in tags:
                            tag_key = f"tag:{tag}"
                            await self.redis_client.sadd(tag_key, key)
                            await self.redis_client.expire(tag_key, ttl)
                    
                except Exception as e:
                    logger.warning("Redis set failed", key=key, error=str(e))
            
            self.stats["sets"] += 1
            logger.debug("Cache set", key=key, ttl=ttl)
            return True
            
        except Exception as e:
            logger.error("Cache set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            deleted = False
            
            # Delete from memory cache
            if key in self.memory_cache:
                del self.memory_cache[key]
                deleted = True
            
            # Delete from Redis cache
            if self.redis_client:
                try:
                    redis_deleted = await self.redis_client.delete(key)
                    deleted = deleted or redis_deleted > 0
                except Exception as e:
                    logger.warning("Redis delete failed", key=key, error=str(e))
            
            if deleted:
                self.stats["deletes"] += 1
                logger.debug("Cache delete", key=key)
            
            return deleted
            
        except Exception as e:
            logger.error("Cache delete failed", key=key, error=str(e))
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear cache entries matching pattern"""
        try:
            cleared_count = 0
            
            # Clear from memory cache
            keys_to_delete = []
            for key in self.memory_cache.keys():
                if self._matches_pattern(key, pattern):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self.memory_cache[key]
                cleared_count += 1
            
            # Clear from Redis cache
            if self.redis_client:
                try:
                    # Get keys matching pattern
                    redis_keys = await self.redis_client.keys(pattern)
                    if redis_keys:
                        redis_cleared = await self.redis_client.delete(*redis_keys)
                        cleared_count += redis_cleared
                except Exception as e:
                    logger.warning("Redis pattern clear failed", pattern=pattern, error=str(e))
            
            logger.info("Cache pattern cleared", pattern=pattern, count=cleared_count)
            return cleared_count
            
        except Exception as e:
            logger.error("Cache pattern clear failed", pattern=pattern, error=str(e))
            return 0
    
    async def clear_by_tags(self, tags: List[str]) -> int:
        """Clear cache entries by tags"""
        try:
            cleared_count = 0
            
            if self.redis_client:
                for tag in tags:
                    try:
                        tag_key = f"tag:{tag}"
                        # Get all keys with this tag
                        keys = await self.redis_client.smembers(tag_key)
                        
                        if keys:
                            # Delete the keys
                            deleted = await self.redis_client.delete(*keys)
                            cleared_count += deleted
                            
                            # Delete the tag set
                            await self.redis_client.delete(tag_key)
                            
                            # Also clear from memory cache
                            for key in keys:
                                if isinstance(key, bytes):
                                    key = key.decode('utf-8')
                                if key in self.memory_cache:
                                    del self.memory_cache[key]
                        
                    except Exception as e:
                        logger.warning("Tag clear failed", tag=tag, error=str(e))
            
            logger.info("Cache cleared by tags", tags=tags, count=cleared_count)
            return cleared_count
            
        except Exception as e:
            logger.error("Cache tag clear failed", tags=tags, error=str(e))
            return 0
    
    async def _set_memory_cache(self, 
                              key: str, 
                              value: Any, 
                              ttl: int,
                              tags: List[str] = None) -> bool:
        """Set value in memory cache with LRU eviction"""
        try:
            # Check if we need to evict items
            if len(self.memory_cache) >= self.max_memory_size:
                await self._evict_lru_items()
            
            # Calculate expiration time
            expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None
            
            # Calculate approximate size
            size_bytes = len(pickle.dumps(value))
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                expires_at=expires_at,
                size_bytes=size_bytes,
                tags=tags or []
            )
            
            self.memory_cache[key] = entry
            return True
            
        except Exception as e:
            logger.error("Memory cache set failed", key=key, error=str(e))
            return False
    
    async def _evict_lru_items(self, count: int = None):
        """Evict least recently used items from memory cache"""
        try:
            count = count or max(1, len(self.memory_cache) // 10)  # Evict 10% by default
            
            # Sort by last accessed time (oldest first)
            sorted_items = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1].last_accessed or x[1].created_at
            )
            
            # Evict oldest items
            for i in range(min(count, len(sorted_items))):
                key = sorted_items[i][0]
                del self.memory_cache[key]
                self.stats["evictions"] += 1
            
            logger.debug("LRU eviction completed", evicted_count=count)
            
        except Exception as e:
            logger.error("LRU eviction failed", error=str(e))
    
    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern (simple wildcard support)"""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)
    
    async def get_multi(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache"""
        results = {}
        
        # Try to get all from memory cache first
        memory_hits = {}
        redis_keys = []
        
        for key in keys:
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                if not entry.expires_at or datetime.now() <= entry.expires_at:
                    memory_hits[key] = entry.value
                    entry.access_count += 1
                    entry.last_accessed = datetime.now()
                else:
                    del self.memory_cache[key]
                    redis_keys.append(key)
            else:
                redis_keys.append(key)
        
        results.update(memory_hits)
        self.stats["memory_hits"] += len(memory_hits)
        
        # Get remaining keys from Redis
        if redis_keys and self.redis_client:
            try:
                redis_values = await self.redis_client.mget(redis_keys)
                
                for key, value in zip(redis_keys, redis_values):
                    if value:
                        deserialized = pickle.loads(value)
                        results[key] = deserialized
                        
                        # Cache in memory for future access
                        await self._set_memory_cache(key, deserialized, self.default_ttl)
                
                self.stats["redis_hits"] += len([v for v in redis_values if v])
                
            except Exception as e:
                logger.warning("Redis mget failed", error=str(e))
        
        # Update statistics
        self.stats["hits"] += len(results)
        self.stats["misses"] += len(keys) - len(results)
        
        return results
    
    async def set_multi(self, items: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values in cache"""
        try:
            ttl = ttl or self.default_ttl
            success = True
            
            # Set in memory cache
            for key, value in items.items():
                mem_success = await self._set_memory_cache(key, value, ttl)
                success = success and mem_success
            
            # Set in Redis cache
            if self.redis_client and items:
                try:
                    # Prepare Redis pipeline
                    pipe = self.redis_client.pipeline()
                    
                    for key, value in items.items():
                        serialized = pickle.dumps(value)
                        pipe.setex(key, ttl, serialized)
                    
                    await pipe.execute()
                    
                except Exception as e:
                    logger.warning("Redis mset failed", error=str(e))
                    success = False
            
            self.stats["sets"] += len(items)
            return success
            
        except Exception as e:
            logger.error("Multi set failed", error=str(e))
            return False
    
    async def health_check(self) -> bool:
        """Check cache service health"""
        try:
            # Test memory cache
            test_key = "health_check_test"
            test_value = {"timestamp": datetime.now().isoformat()}
            
            await self.set(test_key, test_value, ttl=60)
            retrieved = await self.get(test_key)
            await self.delete(test_key)
            
            memory_healthy = retrieved is not None
            
            # Test Redis cache
            redis_healthy = True
            if self.redis_client:
                try:
                    await self.redis_client.ping()
                except Exception as e:
                    logger.warning("Redis health check failed", error=str(e))
                    redis_healthy = False
            
            return memory_healthy and redis_healthy
            
        except Exception as e:
            logger.error("Cache health check failed", error=str(e))
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / max(total_requests, 1)
        
        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "memory_cache_size": len(self.memory_cache),
            "memory_cache_max_size": self.max_memory_size,
            "redis_available": self.redis_client is not None,
            "default_ttl": self.default_ttl
        }
    
    async def clear_all(self) -> bool:
        """Clear all cache entries"""
        try:
            # Clear memory cache
            self.memory_cache.clear()
            
            # Clear Redis cache
            if self.redis_client:
                try:
                    await self.redis_client.flushdb()
                except Exception as e:
                    logger.warning("Redis flush failed", error=str(e))
                    return False
            
            logger.info("All cache cleared")
            return True
            
        except Exception as e:
            logger.error("Clear all cache failed", error=str(e))
            return False
    
    async def get_cache_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cache entry information"""
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            return {
                "key": entry.key,
                "created_at": entry.created_at.isoformat(),
                "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
                "access_count": entry.access_count,
                "last_accessed": entry.last_accessed.isoformat() if entry.last_accessed else None,
                "size_bytes": entry.size_bytes,
                "tags": entry.tags,
                "location": "memory"
            }
        
        # Check Redis for TTL info
        if self.redis_client:
            try:
                ttl = await self.redis_client.ttl(key)
                if ttl > 0:
                    return {
                        "key": key,
                        "ttl_seconds": ttl,
                        "location": "redis"
                    }
            except Exception as e:
                logger.warning("Redis TTL check failed", key=key, error=str(e))
        
        return None
    
    def __del__(self):
        """Cleanup on destruction"""
        if self.redis_client:
            try:
                # Close Redis connection
                asyncio.create_task(self.redis_client.close())
            except Exception:
                pass