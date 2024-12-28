from sqlalchemy.orm import Session as SQLAlchemySession, sessionmaker
from .engine import engine

Session = sessionmaker(bind=engine)


def get_session() -> SQLAlchemySession:
    """Get a new database session."""
    return Session()
