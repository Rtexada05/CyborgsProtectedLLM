"""
Main FastAPI application for the Protected Chat System
"""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .core.logging_config import setup_logging, get_logger
from .api.routes import chat, admin, health
from .services.conversation_memory import shared_conversation_memory
from .services.evaluation_store import shared_evaluation_store
from .services.metrics_logger import shared_metrics_logger
from .services.rag_manager import shared_rag_manager

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Cyborgs Protected Chat System")
    logger.info(f"Log level: {settings.LOG_LEVEL}")
    logger.info(f"Default security mode: {settings.DEFAULT_SECURITY_MODE}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    await shared_conversation_memory.initialize()
    await shared_evaluation_store.initialize()
    await shared_rag_manager.bootstrap()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Cyborgs Protected Chat System")


# Create FastAPI application
app = FastAPI(
    title="Cyborgs Protected Chat System",
    description="A FastAPI-based protected chat system that defends against prompt injection, RAG injection, steganographic content, and tool abuse",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    redirect_slashes=False,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def chat_trace_middleware(request: Request, call_next):
    """Assign a trace ID and count every inbound chat attempt before auth/validation."""

    if request.url.path not in {"/chat", "/chat/"}:
        return await call_next(request)

    # Ignore browser CORS preflights and other non-chat verbs so one logical
    # chat submission does not inflate total-request metrics.
    if request.method.upper() != "POST":
        return await call_next(request)

    trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    request.state.trace_id = trace_id

    response = await call_next(request)
    if response.status_code != 307:
        await shared_metrics_logger.log_chat_attempt(trace_id)
    response.headers["X-Trace-Id"] = trace_id
    return response

# Include routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Cyborgs Protected Chat System",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred"},
    )
    trace_id = getattr(getattr(request, "state", None), "trace_id", None)
    if trace_id:
        response.headers["X-Trace-Id"] = trace_id
    return response


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
