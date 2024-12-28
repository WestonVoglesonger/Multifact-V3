from sqlalchemy.orm import Session
import pytest
from snc.test.test_application.test_services import app_services_data
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from typing import Generator, Callable, Any
from os import getenv
from snc.env import getenv
from snc.database import _engine_str
from snc.infrastructure import entities


@pytest.fixture(autouse=True)
def setup_insert_data_fixture(db_session: Session):
    """
    Automatically inserts demo data before each test and commits the session.
    """
    # Insert demo data (assumed to include multiple documents and tokens)
    app_services_data.insert_fake_data(db_session)
    db_session.commit()
    yield
    # Teardown can be handled here if necessary


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
