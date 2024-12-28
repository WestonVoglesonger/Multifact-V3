"""
Base module for database reset functionality.
This module provides common functionality used by both reset_testing.py and reset_demo.py.
"""

import sys
import subprocess
from typing import Optional, Callable
from sqlalchemy.orm import Session
from ..database import engine
from ..env import getenv
from ..infrastructure import entities


def check_development_mode() -> None:
    """
    Ensure the script can only be run in development mode.

    Raises:
        SystemExit: If not in development mode
    """
    if getenv("MODE") != "development":
        print("This script can only be run in development mode.", file=sys.stderr)
        print(
            "Add MODE=development to your .env file in workspace's `backend/` directory"
        )
        sys.exit(1)


def reset_database(
    insert_data_func: Optional[Callable[[Session], None]] = None
) -> None:
    """
    Reset the database to a clean state and optionally insert data.

    Args:
        insert_data_func: Optional function that takes a Session and inserts data
    """
    # Run Delete and Create Database Scripts
    subprocess.run(["python3", "-m", "backend.script.delete_database"])
    subprocess.run(["python3", "-m", "backend.script.create_database"])

    # Reset Tables
    entities.EntityBase.metadata.drop_all(engine)
    entities.EntityBase.metadata.create_all(engine)

    # Initialize the SQLAlchemy session
    with Session(engine) as session:
        if insert_data_func:
            insert_data_func(session)
        session.commit()
