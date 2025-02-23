from typing import Dict, Any
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

class VisitCount(BaseModel):
    visits: int
    served_via: str

class VisitResponse(BaseModel):
    status: str
    message: str
    page_id: str
    timestamp: datetime

class ResetResponse(BaseModel):
    status: str
    message: str
    page_id: str

class ErrorResponse(BaseModel):
    status: str
    detail: str
    timestamp: datetime

class CounterStatus(BaseModel):
    status: str
    metrics: Dict[str, Any]
    redis_nodes: Dict[str, Any]
    last_batch_write: datetime | None

class CounterStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class CounterMetrics(BaseModel):
    visits: int = 0
    status: CounterStatusEnum = CounterStatusEnum.INACTIVE
    cache_size: int = 0
    last_update: datetime | None = None