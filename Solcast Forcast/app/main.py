"""
Main FastAPI application.
ThingsBoard Power Forecast API - Production-ready backend service.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import health_router, forecast_router
from app.utils.config import settings
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("="*60)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("="*60)
    
    # Validate configuration
    try:
        settings.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
    
    logger.info(f"ThingsBoard Host: {settings.TB_HOST}")
    logger.info(f"Default Target Level: {settings.DEFAULT_TARGET_LEVEL}")
    logger.info(f"Timezone: {settings.TZ_LOCAL}")
    logger.info("API is ready to accept requests")
    logger.info("="*60)
    
    yield
    
    # Shutdown
    logger.info("="*60)
    logger.info("Shutting down API service")
    logger.info("="*60)


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    **ThingsBoard Power Forecast API**
    
    A production-ready backend service for running power forecasting models on ThingsBoard assets.
    
    ## Features
    
    - **Health Check**: Monitor service status
    - **Long-Running Forecasts**: Process multiple assets asynchronously
    - **Job Tracking**: Monitor forecast job progress
    - **New Asset Processing**: Quick processing for individual new assets
    
    ## Workflow
    
    1. Start a forecast job with `/forecast/start`
    2. Receive a job ID immediately
    3. Check job status with `/forecast/status/{job_id}`
    4. Job runs in background: retrieves assets → runs predictions → writes telemetry
    
    ## Authentication
    
    This is an internal service. ThingsBoard authentication is handled automatically using credentials from environment variables.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )


# Include routers
app.include_router(health_router, tags=["Health"])
app.include_router(forecast_router, tags=["Forecast"])


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
