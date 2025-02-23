from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging
import time
from datetime import datetime
from typing import Dict, Any

from .core.config import settings
from .api.v1.api import api_router
from .core.redis_manager import RedisManager
from .services.visit_counter import VisitCounterService

logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app with metadata
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A scalable visit counter service with Redis sharding and caching",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Application state
app.state.start_time = datetime.now()
app.state.request_count = 0
app.state.redis_manager = RedisManager()
app.state.visit_counter = VisitCounterService()

# Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]  # Configure as needed for production
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.middleware("http")
async def count_requests(request: Request, call_next):
    app.state.request_count += 1
    return await call_next(request)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error handler caught: {str(exc)}", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )

@app.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": str(datetime.now() - app.state.start_time)
    }

@app.get("/status")
async def service_status():
    """Detailed service status endpoint"""
    redis_status = await app.state.redis_manager.get_status()
    counter_status = await app.state.visit_counter.get_status()
    
    return {
        "status": "healthy",
        "uptime": str(datetime.now() - app.state.start_time),
        "total_requests": app.state.request_count,
        "redis_status": redis_status,
        "counter_status": counter_status,
        "version": "1.0.0",
        "debug_mode": settings.DEBUG
    }

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting visit counter service...")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down visit counter service...")

app.include_router(
    api_router,
    prefix=settings.API_PREFIX,
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

if settings.DEBUG:
    from fastapi.openapi.docs import get_swagger_ui_html
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=app.title + " - API Docs",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="/static/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui.css",
        )