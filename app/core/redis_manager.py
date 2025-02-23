import redis
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from .consistent_hash import ConsistentHash
from .config import settings

logger = logging.getLogger(__name__)

class RedisManager:
    def __init__(self):
        """Initialize Redis connection pools and consistent hashing"""
        self.connection_pools: Dict[str, redis.ConnectionPool] = {}
        self.redis_clients: Dict[str, redis.Redis] = {}
        self.node_health: Dict[str, bool] = {}
        
        self.redis_nodes = settings.get_redis_nodes_list()
        self.consistent_hash = ConsistentHash(self.redis_nodes, settings.VIRTUAL_NODES)
        
        self._initialize_connections()
        
        asyncio.create_task(self._health_check_loop())

    def _initialize_connections(self) -> None:
        """Initialize Redis connections for all nodes"""
        for node in self.redis_nodes:
            try:
                self.connection_pools[node] = redis.ConnectionPool.from_url(
                    node,
                    password=settings.REDIS_PASSWORD,
                    db=settings.REDIS_DB,
                    socket_timeout=settings.REDIS_TIMEOUT,
                    retry_on_timeout=True,
                    max_connections=10
                )
                self.redis_clients[node] = redis.Redis(
                    connection_pool=self.connection_pools[node]
                )
                self.node_health[node] = True
                logger.info(f"Successfully connected to Redis node: {node}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis node {node}: {str(e)}")
                self.node_health[node] = False

    async def _health_check_loop(self) -> None:
        """Periodic health check for Redis nodes"""
        while True:
            await asyncio.sleep(30) 
            for node in self.redis_nodes:
                try:
                    redis_client = self.redis_clients[node]
                    redis_client.ping()
                    if not self.node_health[node]:
                        logger.info(f"Redis node {node} is back online")
                    self.node_health[node] = True
                except Exception:
                    if self.node_health[node]:
                        logger.error(f"Redis node {node} is down")
                    self.node_health[node] = False

    def get_connection(self, key: str) -> Tuple[redis.Redis, str]:
        """
        Get Redis connection for the given key using consistent hashing
        Returns tuple of (redis_client, node_url)
        """
        node = self.consistent_hash.get_node(key)
        if not self.node_health[node]:
            for _ in range(len(self.redis_nodes)):
                node = self.consistent_hash.get_node(f"fallback_{node}")
                if self.node_health[node]:
                    break
            else:
                raise Exception("No healthy Redis nodes available")
        
        return self.redis_clients[node], node

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment a counter in Redis with retry logic
        """
        for attempt in range(settings.REDIS_RETRY_ATTEMPTS):
            try:
                redis_client, _ = self.get_connection(key)
                return redis_client.incr(key, amount)
            except redis.RedisError as e:
                if attempt == settings.REDIS_RETRY_ATTEMPTS - 1:
                    logger.error(f"Failed to increment counter after {settings.REDIS_RETRY_ATTEMPTS} attempts: {str(e)}")
                    raise Exception(f"Failed to increment counter: {str(e)}")
                await asyncio.sleep(0.1 * (attempt + 1))  

    async def get(self, key: str) -> Tuple[Optional[int], str]:
        """
        Get value for a key from Redis
        Returns tuple of (value, node_url)
        """
        for attempt in range(settings.REDIS_RETRY_ATTEMPTS):
            try:
                redis_client, node = self.get_connection(key)
                value = redis_client.get(key)
                return (int(value) if value is not None else 0), node
            except redis.RedisError as e:
                if attempt == settings.REDIS_RETRY_ATTEMPTS - 1:
                    logger.error(f"Failed to get counter value after {settings.REDIS_RETRY_ATTEMPTS} attempts: {str(e)}")
                    raise Exception(f"Failed to get counter value: {str(e)}")
                await asyncio.sleep(0.1 * (attempt + 1))

    async def mget(self, keys: List[str]) -> Dict[str, Tuple[int, str]]:
        """
        Get multiple values from Redis
        Returns dict mapping keys to tuples of (value, node_url)
        """
        result: Dict[str, Tuple[int, str]] = {}
        
        node_keys: Dict[str, List[str]] = {}
        for key in keys:
            _, node = self.get_connection(key)
            if node not in node_keys:
                node_keys[node] = []
            node_keys[node].append(key)
        
        for node, node_key_list in node_keys.items():
            redis_client = self.redis_clients[node]
            try:
                values = redis_client.mget(node_key_list)
                for key, value in zip(node_key_list, values):
                    result[key] = (int(value) if value is not None else 0, node)
            except redis.RedisError as e:
                logger.error(f"Failed to get counter values from node {node}: {str(e)}")
                for key in node_key_list:
                    result[key] = (0, node)
        
        return result

    async def reset(self, key: str) -> bool:
        """Reset a counter to zero"""
        try:
            redis_client, _ = self.get_connection(key)
            return bool(redis_client.delete(key))
        except redis.RedisError as e:
            logger.error(f"Failed to reset counter: {str(e)}")
            raise Exception(f"Failed to reset counter: {str(e)}")

    def get_status(self) -> Dict[str, Any]:
        """Get Redis cluster status"""
        return {
            "nodes": len(self.redis_nodes),
            "healthy_nodes": sum(1 for health in self.node_health.values() if health),
            "node_status": self.node_health.copy(),
            "distribution": self.consistent_hash.get_node_distribution()
        }