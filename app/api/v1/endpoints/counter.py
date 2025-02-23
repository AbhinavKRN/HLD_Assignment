from fastapi import APIRouter, HTTPException, Depends, Path
from typing import Dict, Any
from ....services.visit_counter import VisitCounterService
from ....schemas.counter import VisitCount

router = APIRouter()

_counter_service = None

def get_visit_counter_service():
    """
    Dependency that returns a singleton instance of VisitCounterService
    """
    global _counter_service
    if _counter_service is None:
        _counter_service = VisitCounterService()
    return _counter_service

@router.post("/visit/{page_id}")
async def record_visit(
    page_id: str = Path(..., description="Unique identifier for the page"),
    counter_service: VisitCounterService = Depends(get_visit_counter_service)
):
    """
    Record a visit for a website page
    
    - Increments the visit counter for the specified page
    - Uses write batching for better performance
    - Updates Redis through sharding
    """
    try:
        await counter_service.increment_visit(page_id)
        return {
            "status": "success",
            "message": f"Visit recorded for page {page_id}",
            "page_id": page_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record visit: {str(e)}"
        )

@router.get("/visits/{page_id}", response_model=VisitCount)
async def get_visits(
    page_id: str = Path(..., description="Unique identifier for the page"),
    counter_service: VisitCounterService = Depends(get_visit_counter_service)
):
    """
    Get visit count for a website page
    
    - Returns the total visit count for the specified page
    - Serves from in-memory cache if available
    - Falls back to Redis if cache miss
    - Indicates the source of the count (in_memory/redis)
    """
    try:
        count, source = await counter_service.get_visit_count(page_id)
        
        if source == "cache":
            served_via = "in_memory"
        elif isinstance(source, str) and source.startswith("redis"):
            served_via = source  
        else:
            served_via = "redis"
            
        return VisitCount(visits=count, served_via=served_via)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get visit count: {str(e)}"
        )

@router.get("/status")
async def get_counter_status(
    counter_service: VisitCounterService = Depends(get_visit_counter_service)
):
    """
    Get the current status of the visit counter service
    """
    try:
        cache_stats = await counter_service.get_cache_stats()
        return {
            "status": "healthy",
            "cache_size": len(counter_service.cache),
            "write_buffer_size": len(counter_service.write_buffer),
            "cache_hits": cache_stats["hits"],
            "cache_misses": cache_stats["misses"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get counter status: {str(e)}"
        )

@router.delete("/visits/{page_id}")
async def reset_counter(
    page_id: str = Path(..., description="Unique identifier for the page"),
    counter_service: VisitCounterService = Depends(get_visit_counter_service)
):
    """
    Reset the visit counter for a specific page
    """
    try:
        await counter_service.reset_counter(page_id)
        return {
            "status": "success",
            "message": f"Counter reset for page {page_id}"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset counter: {str(e)}"
        )