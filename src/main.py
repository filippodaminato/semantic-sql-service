"""
FastAPI application entry point for Semantic SQL Engine Management API.

This module initializes the FastAPI application, configures middleware,
registers API routers, and handles application lifecycle events.

The application provides a RESTful API for managing semantic knowledge
used in SQL generation, including:
- Physical ontology (datasources, tables, columns, relationships)
- Business semantics (metrics, synonyms)
- Context & values (nominal values, context rules)
- Learning (golden SQL examples)
- Retrieval (semantic search for AI agents)
- Admin (management operations)
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time

from .core.database import engine, Base
from .core.config import settings
from .core.logging import get_logger
from .api import ontology, semantics, context, learning, retrieval, admin

# Initialize logger for this module
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    
    This context manager handles:
    - Startup: Database table creation (development only)
    - Shutdown: Cleanup operations (if needed)
    
    Note:
        In production, database schema should be managed via Alembic migrations.
        The table creation here is a convenience for development environments.
        Run `alembic upgrade head` in production instead.
    
    Yields:
        None: Control is yielded to the application runtime
    
    Example:
        The lifespan is automatically used by FastAPI when creating the app:
        ```python
        app = FastAPI(lifespan=lifespan)
        ```
    """
    # Startup: Import all models to ensure SQLAlchemy registers them
    # This is necessary for Base.metadata.create_all() to work correctly
    from src.db import models  # noqa: F401
    
    # Create database tables if they don't exist (development convenience)
    # In production, use Alembic migrations: `alembic upgrade head`
    # FAILSAFE: Commented out to prevent conflict with Alembic migrations
    # try:
    #     Base.metadata.create_all(bind=engine, checkfirst=True)
    #     logger.info("Database tables verified/created successfully")
    # except Exception as e:
    #     # Log warning but don't fail startup - migrations may handle this
    #     logger.warning(f"Warning during table creation: {e}")
    #     logger.warning("If using Alembic, run: alembic upgrade head")
    
    # Yield control to the application
    yield
    
    # Shutdown: Perform cleanup if needed
    # Currently no cleanup required, but this is where you would:
    # - Close database connections
    # - Stop background tasks
    # - Flush caches
    # - Close external service connections
    logger.info("Application shutting down")


# Initialize FastAPI application
app = FastAPI(
    title="Semantic SQL Engine - Management API",
    description="Enterprise API for managing semantic knowledge for SQL generation",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS middleware
# WARNING: allow_origins=["*"] is permissive and should be restricted in production
# For production, specify exact origins:
# allow_origins=["https://yourdomain.com", "https://app.yourdomain.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    HTTP middleware for request/response logging.
    
    Logs all HTTP requests with:
    - HTTP method (GET, POST, etc.)
    - Request path
    - Response status code
    - Request processing duration in milliseconds
    
    Args:
        request: The incoming HTTP request
        call_next: The next middleware/handler in the chain
    
    Returns:
        Response: The HTTP response from the handler
    
    Example log output:
        Method=POST Path=/api/v1/ontology/tables Status=201 Duration=45.23ms
    """
    # Record start time for duration calculation
    start_time = time.time()
    
    # Process the request through the handler chain
    response = await call_next(request)
    
    # Calculate processing time in milliseconds
    process_time = (time.time() - start_time) * 1000
    
    # Log request details
    logger.info(
        f"Method={request.method} Path={request.url.path} "
        f"Status={response.status_code} Duration={process_time:.2f}ms"
    )
    
    return response


# Register API routers
# Each router handles a specific domain of the API
app.include_router(ontology.router)      # Physical ontology management
app.include_router(semantics.router)      # Business semantics (metrics, synonyms)
app.include_router(context.router)       # Context & values (nominal values, rules)
app.include_router(learning.router)      # Learning (golden SQL examples)
app.include_router(retrieval.router)     # Retrieval API for AI agents
app.include_router(admin.router)        # Admin operations


@app.get("/health")
def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns a simple health status indicating the service is running.
    This endpoint is typically used by:
    - Kubernetes liveness/readiness probes
    - Load balancers for health checks
    - Monitoring systems (Prometheus, Datadog, etc.)
    
    Returns:
        dict: Health status information containing:
            - status: Always "healthy" if endpoint is reachable
            - service: Service identifier
            - version: Application version
    
    Example:
        >>> GET /health
        {
            "status": "healthy",
            "service": "semantic-sql-management-api",
            "version": "0.1.0"
        }
    """
    return {
        "status": "healthy",
        "service": "semantic-sql-management-api",
        "version": "0.1.0"
    }


@app.get("/")
def root():
    """
    Root endpoint providing API information and navigation.
    
    Returns basic information about the API and links to documentation.
    This is the entry point for users discovering the API.
    
    Returns:
        dict: API information containing:
            - message: Welcome message
            - docs: Link to Swagger UI documentation
            - health: Link to health check endpoint
    
    Example:
        >>> GET /
        {
            "message": "Semantic SQL Engine - Management API",
            "docs": "/docs",
            "health": "/health"
        }
    """
    return {
        "message": "Semantic SQL Engine - Management API",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    """
    Direct execution entry point for development.
    
    This allows running the application directly with:
        python -m src.main
    
    Note:
        In production, use a proper ASGI server like:
        - uvicorn: uvicorn src.main:app --host 0.0.0.0 --port 8000
        - gunicorn with uvicorn workers
        - Docker container with proper process management
    """
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
