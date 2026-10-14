"""Connection management and database initialization."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3

from spendwise.config import DB_PATH
from spendwise.db.schema import SCHEMA_SQL


def resolve_db_path(db_path: str | Path | None = None) -> Path:
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_connection(db_path: str | Path | None = None):
    """Yield a configured SQLite connection."""
    path = resolve_db_path(db_path)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    try:
        yield connection
    finally:
        connection.close()


def initialize_database(db_path: str | Path | None = None) -> None:
    """Create database tables and indexes if they do not exist."""
    with get_connection(db_path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.commit()
