"""
Reset the database with demo data.
This script resets the SQLAlchemy database to contain demo data for development.

Usage: python3 -m backend.script.reset_demo
"""

from sqlalchemy.orm import Session
from .reset_base import check_development_mode, reset_database
from ..test.test_application.test_services import app_services_data


def insert_demo_data(session: Session) -> None:
    """
    Insert demo data into the database.

    Args:
        session: SQLAlchemy session for database operations
    """
    # For now, we're using the same data as tests
    # In the future, we can add more specific demo data here
    app_services_data.insert_fake_data(session)


if __name__ == "__main__":
    check_development_mode()
    reset_database(insert_demo_data)
