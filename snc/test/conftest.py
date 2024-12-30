from sqlalchemy.orm import Session
import pytest
from snc.test.test_application.test_services import app_services_data
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from typing import Generator, Callable, Any
from os import getenv
from snc.env import getenv
from snc.database import _engine_str
from snc.infrastructure import entities


@pytest.fixture(scope="session", autouse=True)
def test_engine():
    """Create a test database engine that's used for the entire test session."""
    POSTGRES_DATABASE = f'{getenv("POSTGRES_DATABASE")}_test'
    engine = create_engine(_engine_str(POSTGRES_DATABASE))

    # Drop and recreate all tables
    entities.EntityBase.metadata.drop_all(engine)
    entities.EntityBase.metadata.create_all(engine)

    # Enable nested transactions for better isolation
    @event.listens_for(engine, "begin")
    def do_begin(conn):
        conn.execute("BEGIN")

    return engine


@pytest.fixture(scope="function")
def db_session(test_engine: Engine) -> Generator[Session, Any, Any]:
    """Create an isolated database session for each test.

    Uses nested transactions to ensure complete isolation between tests.
    All changes are rolled back after each test.
    """
    connection = test_engine.connect()

    # Begin an outer transaction that will never be committed
    transaction = connection.begin()

    # Begin a SAVEPOINT transaction
    connection.execute("SAVEPOINT test_start")

    # Create session bound to this connection
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Rollback to the SAVEPOINT
        connection.execute("ROLLBACK TO SAVEPOINT test_start")
        # Release the outer transaction
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="session")
def session_factory(test_engine: Engine) -> Callable[[], Session]:
    """Create a session factory for the test engine."""
    SessionLocal = sessionmaker(bind=test_engine)

    def factory():
        return SessionLocal()

    return factory


@pytest.fixture(autouse=True)
def setup_test_data(db_session: Session):
    """Insert test data before each test.

    This fixture runs automatically before each test, ensuring fresh test data.
    The data is automatically rolled back after each test due to the db_session fixture.
    """
    app_services_data.insert_fake_data(db_session)
    db_session.commit()
    yield
