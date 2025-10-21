from sqlmodel import create_engine, SQLModel, Session
import httpx
from .config import settings

# Database setup
engine = create_engine(settings.DATABASE_URL, echo=False)

# Shared httpx client store
# This will be populated during the application's lifespan
http_client_store: dict = {}


def create_db_and_tables():
    """Creates all database tables based on SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency to get a database session."""
    with Session(engine) as session:
        yield session


async def get_http_client() -> httpx.AsyncClient:
    """Dependency to get the shared httpx.AsyncClient instance."""
    return http_client_store["client"]
