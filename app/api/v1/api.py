from fastapi import APIRouter
from .endpoints import counter

api_router = APIRouter()

api_router.include_router(
    counter.router,
    prefix="/counter",
    tags=["counter"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"},
    }
)

@api_router.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy", "service": "visit_counter"}

@api_router.get("/metrics", tags=["metrics"])
async def get_metrics():
    return {
        "status": "available",
        "redis_shards": ["redis1:6379", "redis2:6379", "redis3:6379"],
        "cache_enabled": True,
        "batch_processing_enabled": True
    }