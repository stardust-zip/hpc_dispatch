# hpc_dispatch/main.py
import sys
import os
import logging
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- FIX: Add parent directory to Python's path ---
# This allows running 'uvicorn main:app' from within the hpc_dispatch directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


from hpc_dispatch.config import settings
from hpc_dispatch.database import create_db_and_tables, http_client_store
from hpc_dispatch.routers import dispatches, shelves, system
from hpc_dispatch import schemas  # Import schemas to call rebuild

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown events.
    Handles DB creation and shared HTTP client.
    """
    # Startup
    logger.info("Application starting up...")
    if settings.MOCK_AUTH_ENABLED:
        logger.warning("!!! MOCK AUTHENTICATION IS ENABLED !!!")
    else:
        logger.info(f"Connecting to User Service at: {settings.HPC_USER_SERVICE_URL}")

    create_db_and_tables()
    http_client_store["client"] = httpx.AsyncClient()
    logger.info("Startup complete.")
    yield
    # Shutdown
    logger.info("Application shutting down...")
    await http_client_store["client"].close()
    logger.info("Shutdown complete.")


# Initialize FastAPI app
app = FastAPI(
    title="HPC Dispatch Microservice",
    description="Service to manage dispatches and nested shelves.",
    version="1.2.0",
    lifespan=lifespan,
)

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # <-- FIX: Corrected typo from CORS_origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the routers from the routers package
app.include_router(system.router)
app.include_router(dispatches.router)
app.include_router(shelves.router)

# --- FIX: Rebuild schemas to resolve forward references ---
# This is called here after all models and schemas are defined and imported.
schemas.ShelfReadWithChildren.model_rebuild()
schemas.ShelfReadWithDispatches.model_rebuild()
schemas.DispatchReadWithDetails.model_rebuild()
