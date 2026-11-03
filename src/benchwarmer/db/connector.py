"""SQLite connection manager and zipapp asset extractor stub."""

from typing import Optional
import sqlite3


class SQLiteConnector:
    """Read-only SQLite connection manager."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        raise NotImplementedError("SQLiteConnector.__init__ not implemented in Phase 0")

    def get_connection(self) -> sqlite3.Connection:
        raise NotImplementedError("SQLiteConnector.get_connection not implemented in Phase 0")

    def close(self) -> None:
        raise NotImplementedError("SQLiteConnector.close not implemented in Phase 0")

    def __enter__(self) -> "SQLiteConnector":
        raise NotImplementedError("SQLiteConnector.__enter__ not implemented in Phase 0")

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        raise NotImplementedError("SQLiteConnector.__exit__ not implemented in Phase 0")
