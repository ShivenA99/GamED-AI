"""GamED.AI v2 - FastAPI Application Entry Point"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
import os

# Load environment variables (override=True ensures .env takes precedence over inherited env vars)
load_dotenv(override=True)

# Configure centralized logging
from app.utils.logging_config import setup_logging, get_logger

# Set up logging based on environment
log_level = os.getenv("LOG_LEVEL", "INFO")
log_to_file = os.getenv("LOG_TO_FILE", "true").lower() == "true"
setup_logging(
    level=log_level,
    log_to_file=log_to_file,
    structured=os.getenv("STRUCTURED_LOGGING", "false").lower() == "true"
)

logger = get_logger("gamed_ai.main")

# Suppress Pydantic V1 deprecation warnings for Python 3.14+
import warnings
warnings.filterwarnings("ignore", message=".*Pydantic V1.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*pydantic.v1.*", category=UserWarning)

# Import routes after logging setup
from app.routes import generate, questions, review, sessions, pipeline, observability, poc_game, pipeline_graph
from app.db.database import init_db

# Create FastAPI app
app = FastAPI(
    title="GamED.AI v2 API",
    description="Agentic Game Generation Platform for Educational Content",
    version="2.0.0"
)

# Add rate limiter state and exception handler
from app.routes.generate import limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

logger.info("=" * 80)
logger.info("GamED.AI v2 API Starting", metadata={"version": "2.0.0"})
logger.info("=" * 80)


@app.on_event("startup")
async def startup_event():
    """Initialize database, tool registry, and seed agent registry on startup"""
    logger.info("Initializing database...")
    try:
        with logger.time_operation("database_init"):
            init_db()
        logger.info("Database initialized successfully")

        # Initialize tool registry ONCE at startup (not in graph creation)
        # This prevents redundant registration and log spam
        from app.tools.registry import initialize_tools
        try:
            initialize_tools()
            logger.info("Tool registry initialized successfully")
        except Exception as e:
            logger.warning(f"Tool registry initialization failed (non-fatal): {e}")

        # Seed agent registry for dashboard
        from app.db.seed_agent_registry import seed_agent_registry
        try:
            seed_agent_registry()
            logger.info("Agent registry seeded successfully")
        except Exception as e:
            logger.warning(f"Agent registry seeding failed (non-fatal): {e}")
    except Exception as e:
        logger.error("Database initialization failed", exc_info=True, metadata={"error": str(e)})


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Application shutting down...")


# CORS middleware - secure configuration
# Allow origins from environment variable or default to localhost
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Specific methods only
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Request-ID",
        "Accept",
        "Accept-Language",
        "Origin",
    ],  # Specific headers only
    max_age=3600,  # Cache preflight for 1 hour
)
logger.info("CORS middleware configured", metadata={"origins": CORS_ORIGINS})

# Include routers
app.include_router(generate.router, prefix="/api", tags=["generate"])
app.include_router(questions.router, prefix="/api", tags=["questions"])
app.include_router(review.router, prefix="/api", tags=["review"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(pipeline.router, prefix="/api", tags=["pipeline"])
app.include_router(observability.router, prefix="/api", tags=["observability"])
app.include_router(poc_game.router, prefix="/api", tags=["poc-game"])
app.include_router(pipeline_graph.router, prefix="/api/pipeline", tags=["pipeline-graph"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "GamED.AI v2",
        "version": "2.0.0",
        "description": "Agentic Game Generation Platform"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/health/sam3")
async def health_sam3():
    """SAM3 Metal GPU status — shows queue depth, busy state, timing."""
    try:
        from app.services.asset_gen.segmentation import get_sam3_status
        return get_sam3_status()
    except ImportError:
        return {"state": "unavailable", "error": "segmentation module not importable"}
