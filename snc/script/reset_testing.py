"""
Reset the database with testing data.
This script resets the SQLAlchemy database to contain the same data that
is used when running the pytests.

Usage: python3 -m backend.script.reset_testing
"""

from .reset_base import check_development_mode, reset_database
from ..test.test_application.test_services import app_services_data

if __name__ == "__main__":
    check_development_mode()
    reset_database(app_services_data.insert_fake_data)
