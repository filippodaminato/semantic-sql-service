"""FastAPI application entry point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.database import engine, Base
from .core.config import settings
from .api import ontology, semantics, context, learning, retrieval, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup: Import all models to ensure they're registered
    # In production, use Alembic migrations: alembic upgrade head
    from src.db import models  # noqa: F401
    
    # Create tables with checkfirst to avoid errors if they exist
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as e:
        print(f"Warning during table creation: {e}")
        print("If using Alembic, run: alembic upgrade head")
    
    yield
    # Shutdown: cleanup if needed
    pass


app = FastAPI(
    title="Semantic SQL Engine - Management API",
    description="Enterprise API for managing semantic knowledge for SQL generation",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging Middleware
from fastapi import Request
import time
from .core.logging import get_logger

logger = get_logger("main")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    
    logger.info(
        f"Method={request.method} Path={request.url.path} "
        f"Status={response.status_code} Duration={process_time:.2f}ms"
    )
    return response

# Include routers
app.include_router(ontology.router)
app.include_router(semantics.router)
app.include_router(context.router)
app.include_router(learning.router)
app.include_router(retrieval.router)
app.include_router(admin.router)


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "semantic-sql-management-api",
        "version": "0.1.0"
    }


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Semantic SQL Engine - Management API",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
