"""Thin database adapter abstractions for repository implementations."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Protocol


class DatabaseSession(Protocol):
    """Protocol for a minimal DB session used by repositories."""

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any: ...

    def executemany(self, sql: str, params: list[tuple[Any, ...]]) -> Any: ...


class DatabaseAdapter(Protocol):
    """Protocol for repository-friendly DB adapters."""

    @contextmanager
    def session(self) -> Iterator[DatabaseSession]: ...


@dataclass(slots=True)
class SQLiteAdapter:
    """SQLite-backed adapter; can be swapped with other adapters later."""

    db_path: str | Path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
