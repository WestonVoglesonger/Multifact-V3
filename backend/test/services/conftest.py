import pytest
import random
import string
from sqlalchemy.orm import Session
from unittest.mock import MagicMock
from backend.env import getenv
from backend.database import _engine_str
from backend import entities
from backend.entities.ni_token import NIToken
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, select
from typing import Callable, Generator, Any
from sqlalchemy.engine import Engine
from unittest.mock import patch
"""Shared pytest fixtures for database dependent tests."""

import pytest

from sqlalchemy import create_engine, text, Engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, ProgrammingError

from ...database import _engine_str
from ...env import getenv
from ... import entities

POSTGRES_DATABASE = f'{getenv("POSTGRES_DATABASE")}_test'
POSTGRES_USER = getenv("POSTGRES_USER")

__authors__ = ["Kris Jordan"]
__copyright__ = "Copyright 2023"
__license__ = "MIT"


def reset_database():
    engine = create_engine(_engine_str(""))
    with engine.connect() as connection:
        try:
            conn = connection.execution_options(autocommit=False)
            conn.execute(text("ROLLBACK"))  # Get out of transactional mode...
            conn.execute(text(f"DROP DATABASE {POSTGRES_DATABASE}"))
        except ProgrammingError:
            ...
        except OperationalError:
            print(
                "Could not drop database because it's being accessed by others (psql open?)"
            )
            exit(1)

        conn.execute(text(f"CREATE DATABASE {POSTGRES_DATABASE}"))
        conn.execute(
            text(
                f"GRANT ALL PRIVILEGES ON DATABASE {POSTGRES_DATABASE} TO {POSTGRES_USER}"
            )
        )


@pytest.fixture(scope="session", autouse=True)
def test_engine():
    POSTGRES_DATABASE = f'{getenv("POSTGRES_DATABASE")}_test'
    engine = create_engine(_engine_str(POSTGRES_DATABASE))
    entities.EntityBase.metadata.drop_all(engine)
    entities.EntityBase.metadata.create_all(engine)
    return engine

@pytest.fixture(scope="function")
def db_session(test_engine: Engine) -> Generator[Session, Any, Any]:
    connection = test_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture(scope="session")
def session_factory(test_engine: Engine) -> Callable[[], Session]:
    SessionLocal = sessionmaker(bind=test_engine)

    def factory():
        return SessionLocal()

    return factory
