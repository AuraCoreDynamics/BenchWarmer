"""SQLite connection manager and zipapp asset extractor for BenchWarmer."""

import hashlib
import importlib.resources
import os
import sqlite3
import tempfile
import threading
from pathlib import Path
from typing import Optional


def compute_canonical_checksum(conn: sqlite3.Connection) -> str:
    """Compute the deterministic SHA-256 checksum over benchmark_scores."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT model_id, suite, benchmark, metric, printf('%.6f', score), printf('%.6f', raw_score) "
        "FROM benchmark_scores ORDER BY model_id, suite, benchmark, metric"
    )
    hasher = hashlib.sha256()
    for row in cursor.fetchall():
        line = f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]}\n"
        hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()


class SQLiteConnector:
    """Thread-safe, read-only SQLite connection manager."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._custom_path = db_path
        self._local = threading.local()
        self._resolved_path = self._resolve_db_path()

    def _resolve_db_path(self) -> Path:
        if self._custom_path is not None:
            p = Path(self._custom_path).resolve()
            if not p.exists():
                raise FileNotFoundError(f"Database file not found: {p}")
            return p

        # Check if running as packaged or filesystem resource
        try:
            package_data = importlib.resources.files("benchwarmer").joinpath("data")
            db_resource = package_data.joinpath("benchmarks.db")
            checksum_resource = package_data.joinpath("checksum.sha256")

            # Try to get OS path directly if on filesystem
            try:
                candidate_path = Path(str(db_resource)).resolve()
                if candidate_path.exists() and candidate_path.is_file():
                    return candidate_path
            except Exception:
                pass

            # Extract from zipapp / archive
            checksum_text = checksum_resource.read_text(encoding="utf-8").strip()
            expected_hash = checksum_text.split()[0] if checksum_text else "default"
            temp_db_path = Path(tempfile.gettempdir()) / f"benchwarmer_{expected_hash[:16]}.db"

            if not temp_db_path.exists():
                db_bytes = db_resource.read_bytes()
                # Verify extracted data
                temp_db_path.write_bytes(db_bytes)
                test_conn = sqlite3.connect(temp_db_path)
                try:
                    computed_hash = compute_canonical_checksum(test_conn)
                    if computed_hash != expected_hash:
                        temp_db_path.unlink(missing_ok=True)
                        raise ValueError(
                            f"Checksum mismatch for extracted benchmarks.db: {computed_hash} != {expected_hash}"
                        )
                finally:
                    test_conn.close()

            return temp_db_path
        except Exception:
            # Fallback to local source directory relative path if available
            local_fallback = Path(__file__).resolve().parent.parent / "data" / "benchmarks.db"
            if local_fallback.exists():
                return local_fallback
            raise FileNotFoundError("Could not resolve benchmarks.db from package resources or filesystem.")

    def get_connection(self) -> sqlite3.Connection:
        """Return a thread-local read-only SQLite connection."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            posix_path = self._resolved_path.as_posix()
            uri = f"file:///{posix_path}?mode=ro" if not posix_path.startswith("/") else f"file:{posix_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            # Enable query optimization pragmas
            conn.execute("PRAGMA query_only = ON;")
            self._local.conn = conn
        return conn

    def close(self) -> None:
        """Close current thread connection."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None

    def __enter__(self) -> "SQLiteConnector":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
