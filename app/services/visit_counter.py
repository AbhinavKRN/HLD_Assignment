from typing import Dict, List, Any, Tuple, Optional
import asyncio
import logging
from datetime import datetime
from ..core.redis_manager import RedisManager
from ..core.config import settings
from ..schemas.counter import CounterMetrics, CounterStatus, CounterStatusEnum

logger = logging.getLogger(__name__)

class VisitCounterService:
    def __init__(self):
        """Initialize the visit counter service with Redis manager and in-memory cache"""
        self.redis_manager = RedisManager()
        self.cache: Dict[str, Dict[str, Any]] = {}  # In-memory cache
        self.write_buffer: Dict[str, int] = {}  # Write buffer for batching
        self.last_write_time = datetime.now()
        self.metrics = CounterMetrics(
            visits=0,
            status=CounterStatusEnum.ACTIVE,
            cache_size=0,
            last_update=None
        )
        
        # Start background tasks
        self._start_background_tasks()
        
    def _start_background_tasks(self):
        """Start all background tasks"""
        asyncio.create_task(self._batch_write_loop())
        asyncio.create_task(self._cache_cleanup_loop())
        asyncio.create_task(self._metrics_update_loop())
        
    async def _batch_write_loop(self):
        """Background task to periodically flush write buffer to Redis"""
        while True:
            try:
                await asyncio.sleep(settings.BATCH_INTERVAL_SECONDS)
                await self._flush_write_buffer()
            except Exception as e:
                logger.error(f"Error in batch write loop: {str(e)}")
            
    async def _cache_cleanup_loop(self):
        """Background task to clean up expired cache entries"""
        while True:
            try:
                await asyncio.sleep(settings.CACHE_TTL_SECONDS)
                self._cleanup_cache()
            except Exception as e:
                logger.error(f"Error in cache cleanup loop: {str(e)}")

    async def _metrics_update_loop(self):
        """Background task to update metrics"""
        while True:
            try:
                await asyncio.sleep(settings.METRICS_INTERVAL_SECONDS)
                await self.update_metrics()
            except Exception as e:
                logger.error(f"Error in metrics update loop: {str(e)}")

    def _cleanup_cache(self):
        """Remove expired entries from cache"""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self.cache.items()
            if (now - entry['timestamp']).total_seconds() >= settings.CACHE_TTL_SECONDS
        ]
        for key in expired_keys:
            del self.cache[key]

    async def update_metrics(self):
        try:
            # Update metrics properly using the defined fields
            self.metrics = CounterMetrics(
                visits=self.metrics.visits,
                status=CounterStatusEnum.ACTIVE,
                cache_size=len(self.cache),
                last_update=datetime.now()
            )
        except Exception as e:
            logging.error(f"Error in metrics update loop: {str(e)}")

    async def _flush_write_buffer(self):
        """Flush write buffer to Redis"""
        if not self.write_buffer:
            return
            
        buffer_to_write = self.write_buffer.copy()
        self.write_buffer.clear()
        
        for page_id, count in buffer_to_write.items():
            if count > 0:
                try:
                    await self.redis_manager.increment(f"visits:{page_id}", count)
                except Exception as e:
                    logger.error(f"Failed to flush counter for {page_id}: {str(e)}")
                    # Restore count to buffer
                    if page_id not in self.write_buffer:
                        self.write_buffer[page_id] = 0
                    self.write_buffer[page_id] += count

        self.last_write_time = datetime.now()

    async def increment_visit(self, page_id: str) -> None:
        """
        Increment visit count for a page
        
        Args:
            page_id: Unique identifier for the page
        """
        try:
            if page_id not in self.write_buffer:
                self.write_buffer[page_id] = 0
            self.write_buffer[page_id] += 1
            
            cache_key = f"visits:{page_id}"
            if cache_key in self.cache:
                del self.cache[cache_key]
                
        except Exception as e:
            logger.error(f"Failed to increment visit for {page_id}: {str(e)}")
            raise
            
    async def get_visit_count(self, page_id: str) -> Tuple[int, str]:
        """
        Get current visit count for a page
        
        Args:
            page_id: Unique identifier for the page
            
        Returns:
            Tuple of (visit_count, source)
        """
        cache_key = f"visits:{page_id}"
        
        try:
            if cache_key in self.cache:
                cache_entry = self.cache[cache_key]
                if (datetime.now() - cache_entry['timestamp']).total_seconds() < settings.CACHE_TTL_SECONDS:
                    self.metrics.cache_hits += 1
                    return cache_entry['value'], "in_memory"
                
            self.metrics.cache_misses += 1
            
            await self._flush_write_buffer()
            
            count, node = await self.redis_manager.get(cache_key)
            
            if page_id in self.write_buffer:
                count += self.write_buffer[page_id]
            
            self.cache[cache_key] = {
                'value': count,
                'timestamp': datetime.now()
            }
            
            return count, f"redis_{node}"
            
        except Exception as e:
            logger.error(f"Failed to get visit count for {page_id}: {str(e)}")
            return self.write_buffer.get(page_id, 0), "write_buffer"

    async def reset_counter(self, page_id: str) -> bool:
        """
        Reset visit counter for a page
        
        Args:
            page_id: Unique identifier for the page
            
        Returns:
            True if reset successful
        """
        cache_key = f"visits:{page_id}"
        try:
            self.cache.pop(cache_key, None)
            self.write_buffer.pop(page_id, None)
            
            return await self.redis_manager.reset(cache_key)
        except Exception as e:
            logger.error(f"Failed to reset counter for {page_id}: {str(e)}")
            raise

    async def get_status(self) -> CounterStatus:
        """Get current service status"""
        try:
            redis_status = self.redis_manager.get_status()
            return CounterStatus(
                status="healthy" if redis_status["healthy_nodes"] > 0 else "error",
                metrics=self.metrics,
                redis_nodes=redis_status["node_status"],
                last_batch_write=self.last_write_time
            )
        except Exception as e:
            logger.error(f"Failed to get service status: {str(e)}")
            raise