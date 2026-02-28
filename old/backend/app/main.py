from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from app.utils.logger import setup_logger, initialize_run_logging, get_run_id, get_run_dir
from app.db.database import init_db, engine
from app.db import models
from datetime import datetime
import json

# Load environment variables from .env file
load_dotenv()

# Initialize run logging first
run_id, run_dir = initialize_run_logging()

# Set up logging
logger = setup_logger("main")

from app.routes import upload, analyze, generate, progress, questions, visualizations

app = FastAPI(title="AI Learning Platform API", version="1.0.0")

logger.info("=" * 80)
logger.info("AI Learning Platform API Starting")
logger.info("=" * 80)

# Initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Run directory: {run_dir}")
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Application shutting down...")
    # Update run metadata with end time
    if run_dir and (run_dir / "metadata.json").exists():
        try:
            with open(run_dir / "metadata.json", 'r') as f:
                metadata = json.load(f)
            metadata["end_time"] = datetime.now().isoformat()
            with open(run_dir / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Run {run_id} completed. Logs saved to: {run_dir}")
        except Exception as e:
            logger.warning(f"Failed to update run metadata: {e}")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS middleware configured for http://localhost:3000")

# Include routers
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(generate.router, prefix="/api", tags=["generate"])
app.include_router(progress.router, prefix="/api", tags=["progress"])
app.include_router(questions.router, prefix="/api", tags=["questions"])
app.include_router(visualizations.router, prefix="/api", tags=["visualizations"])

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "AI Learning Platform API"}

@app.get("/health")
async def health():
    logger.debug("Health check endpoint accessed")
    return {"status": "healthy"}

@app.get("/api/run-info")
async def get_run_info():
    """Get information about the current run"""
    metadata = None
    if run_dir and (run_dir / "metadata.json").exists():
        try:
            with open(run_dir / "metadata.json", 'r') as f:
                metadata = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read run metadata: {e}")
    
    return {
        "run_id": run_id,
        "run_directory": str(run_dir) if run_dir else None,
        "metadata": metadata
    }

