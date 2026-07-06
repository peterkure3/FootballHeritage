"""Shared database engines and connection helpers for API routers."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine

from config import DATABASE_URI
from heritage_config import DATABASE_URI as HERITAGE_DATABASE_URI

engine = create_engine(DATABASE_URI)

heritage_engine = create_engine(HERITAGE_DATABASE_URI)


def get_db_connection():
    """Get database connection."""
    return engine


def get_heritage_db_connection():
    return heritage_engine

