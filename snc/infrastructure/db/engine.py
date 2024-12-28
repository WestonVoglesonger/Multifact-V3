from sqlalchemy import create_engine
from snc.env import getenv


def _engine_str(database: str = getenv("POSTGRES_DATABASE")) -> str:
    """Helper function for reading settings from environment variables to produce connection string."""
    dialect = "postgresql+psycopg2"
    user = getenv("POSTGRES_USER")
    password = getenv("POSTGRES_PASSWORD")
    host = getenv("POSTGRES_HOST")
    port = getenv("POSTGRES_PORT")
    return f"{dialect}://{user}:{password}@{host}:{port}/{database}"


engine = create_engine(_engine_str(), echo=False)

# Import all models to ensure they are registered with the metadata
from snc.infrastructure.entities.ni_document import NIDocument
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.db.models import EntityBase

# Create all tables if they don't exist
EntityBase.metadata.create_all(engine)
