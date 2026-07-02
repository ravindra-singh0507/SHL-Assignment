"""FastAPI application entry point."""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env before anything else
load_dotenv()

from .catalog import Catalog
from .retrieval import Retrieval
from .llm import LLM
from .agent import Agent
from .routes import router, set_agent
from .utils import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Startup
    try:
        logger.info("Initializing SHL AI Hiring Assistant...")

        catalog_path = os.getenv("CATALOG_PATH", "data/shl_product_catalog.json")
        logger.info(f"Loading catalog from {catalog_path}")
        catalog = Catalog(catalog_path)
        logger.info(f"Loaded {catalog.size()} assessments")

        retrieval = Retrieval(catalog)
        index_path = os.getenv("INDEX_PATH", "vector_store/tfidf_index.pkl")
        if Path(index_path).exists():
            logger.info(f"Loading vector index from {index_path}")
            retrieval.load_index()
        else:
            logger.info("Building vector index (first run)...")
            retrieval.build_index()
            retrieval.save_index()
            logger.info("Vector index built and saved")

        llm = LLM()
        logger.info("LLM initialized")

        agent = Agent(catalog, retrieval, llm)
        set_agent(agent)
        logger.info("Agent initialized and ready")

    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="SHL AI Hiring Assistant",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()
