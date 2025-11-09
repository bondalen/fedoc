"""Database session helpers built on psycopg2."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Iterator

import psycopg2
from psycopg2.extras import RealDictCursor


class SessionManager:
    """Lightweight session/connection factory for PostgreSQL."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    @contextmanager
    def connection(self) -> Iterator[psycopg2.extensions.connection]:
        """Yield a dedicated database connection."""

        conn = psycopg2.connect(self._dsn)
        try:
            self._initialize_connection(conn)
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def cursor(self) -> Generator[psycopg2.extensions.cursor, None, None]:
        """Yield a cursor with dict rows."""

        with self.connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                yield cursor

    @staticmethod
    def _initialize_connection(conn: psycopg2.extensions.connection) -> None:
        """Ensure AGE extension is loaded and search_path is configured."""

        with conn.cursor() as cursor:
            cursor.execute("LOAD 'age';")
            cursor.execute('SET search_path = ag_catalog, "$user", public;')

