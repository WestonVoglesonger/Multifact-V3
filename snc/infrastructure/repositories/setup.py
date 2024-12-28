"""
Helper module for setting up repositories with minimal configuration.
"""

from dataclasses import dataclass
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from snc.infrastructure.entities.entity_base import EntityBase
from snc.infrastructure.repositories.document_repository import DocumentRepository
from snc.infrastructure.repositories.token_repository import TokenRepository
from snc.infrastructure.repositories.artifact_repository import ArtifactRepository


@dataclass
class Repositories:
    document_repo: DocumentRepository
    token_repo: TokenRepository
    artifact_repo: ArtifactRepository


def setup_repositories(
    db_url: str = "sqlite:///:memory:",
) -> tuple[Session, Repositories]:
    """
    Set up repositories with a default in-memory SQLite database.

    Args:
        db_url: Database URL. Defaults to in-memory SQLite.

    Returns:
        Tuple of (Session, Repositories)
    """
    engine = create_engine(db_url)
    EntityBase.metadata.create_all(engine)

    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()

    repositories = Repositories(
        document_repo=DocumentRepository(session),
        token_repo=TokenRepository(session),
        artifact_repo=ArtifactRepository(session),
    )

    return session, repositories
