from pydantic_settings import BaseSettings
from pydantic import model_validator, Field
from typing import List
import os

class Settings(BaseSettings):
    REDIS_NODES: str = Field(
        default="redis://redis1:6379,redis://redis2:6379,redis://redis3:6379",
        description="Comma-separated string of Redis nodes"
    )
    REDIS_PASSWORD: str = Field(default="", description="Redis password")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_TIMEOUT: int = Field(default=5, description="Redis connection timeout in seconds")
    REDIS_RETRY_ATTEMPTS: int = Field(default=3, description="Number of Redis retry attempts")
    
    VIRTUAL_NODES: int = Field(
        default=100,
        description="Number of virtual nodes per physical node in consistent hashing"
    )
    
    CACHE_TTL_SECONDS: int = Field(
        default=5,
        description="Time-to-live for cached items in seconds"
    )
    CACHE_CAPACITY: int = Field(
        default=1000,
        description="Maximum number of items in the cache"
    )
    
    BATCH_INTERVAL_SECONDS: float = Field(
        default=5.0,
        description="Interval between batch writes to Redis"
    )
    BATCH_SIZE_LIMIT: int = Field(
        default=1000,
        description="Maximum number of items in a batch"
    )
    
    DEBUG: bool = Field(default=True, description="Debug mode flag")
    API_PREFIX: str = Field(default="/api/v1", description="API route prefix")
    PROJECT_NAME: str = Field(default="Visit Counter Service", description="Project name")
    
    ENABLE_METRICS: bool = Field(default=True, description="Enable metrics collection")
    METRICS_INTERVAL_SECONDS: int = Field(
        default=60,
        description="Interval for metrics collection in seconds"
    )

    @model_validator(mode='after')
    def validate_redis_nodes(self):
        """Validate Redis nodes configuration"""
        if not self.REDIS_NODES:
            raise ValueError("REDIS_NODES configuration is required")
        
        nodes = [node.strip() for node in self.REDIS_NODES.split(",")]
        if not nodes:
            raise ValueError("At least one Redis node must be configured")
        
        for node in nodes:
            if not node.startswith("redis://"):
                raise ValueError(f"Invalid Redis URL format: {node}")
        
        return self

    def get_redis_nodes_list(self) -> List[str]:
        """Get Redis nodes as a list"""
        return [node.strip() for node in self.REDIS_NODES.split(",") if node.strip()]

    def get_redis_connection_params(self) -> dict:
        """Get Redis connection parameters"""
        return {
            "password": self.REDIS_PASSWORD,
            "db": self.REDIS_DB,
            "socket_timeout": self.REDIS_TIMEOUT,
            "retry_on_timeout": True,
            "max_connections": 10
        }

    class Config:
        env_file = ".env"
        case_sensitive = True
        validate_assignment = True

settings = Settings()