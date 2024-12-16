import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from backend.env import getenv
from backend.database import _engine_str
from backend import entities

POSTGRES_DATABASE = f'{getenv("POSTGRES_DATABASE")}_test'

@pytest.fixture(scope="session", autouse=True)
def test_engine():
    engine = create_engine(_engine_str(POSTGRES_DATABASE))
    entities.EntityBase.metadata.drop_all(engine)
    entities.EntityBase.metadata.create_all(engine)
    return engine

@pytest.fixture(scope="function")
def db_session(test_engine: Engine):
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
def session_factory(test_engine: Engine):
    SessionLocal = sessionmaker(bind=test_engine)
    def factory():
        return SessionLocal()
    return factory