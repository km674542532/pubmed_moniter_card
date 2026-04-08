"""Repository for query task persistence operations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from app.core.schemas.models import QueryTaskDB
from app.repositories._utils import to_db_value
from app.repositories.db_adapter import DatabaseAdapter
from app.repositories.exceptions import NotFoundError


class QueryTaskRepository:
    def __init__(self, adapter: DatabaseAdapter):
        self.adapter = adapter

    def create(self, data: QueryTaskDB) -> QueryTaskDB:
        payload = data.model_dump()
        with self.adapter.session() as conn:
            conn.execute(
                """
                INSERT INTO query_task (
                    id, name, query_expression, schedule, timezone, lookback_hours,
                    is_enabled, created_at, updated_at, created_by, updated_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(to_db_value(payload[k]) for k in (
                    "id", "name", "query_expression", "schedule", "timezone", "lookback_hours",
                    "is_enabled", "created_at", "updated_at", "created_by", "updated_by"
                )),
            )
        return data

    def update(self, task_id: UUID, **updates: object) -> QueryTaskDB:
        if not updates:
            return self.get_by_id(task_id)
        updates["updated_at"] = datetime.utcnow()
        columns = ", ".join(f"{k} = ?" for k in updates)
        params = tuple(to_db_value(v) for v in updates.values()) + (str(task_id),)
        with self.adapter.session() as conn:
            cursor = conn.execute(f"UPDATE query_task SET {columns} WHERE id = ?", params)
            if cursor.rowcount == 0:
                raise NotFoundError(f"query_task not found: {task_id}")
        return self.get_by_id(task_id)

    def get_by_id(self, task_id: UUID) -> QueryTaskDB:
        with self.adapter.session() as conn:
            row = conn.execute("SELECT * FROM query_task WHERE id = ?", (str(task_id),)).fetchone()
        if row is None:
            raise NotFoundError(f"query_task not found: {task_id}")
        return QueryTaskDB.model_validate(dict(row))

    def list_active(self) -> list[QueryTaskDB]:
        with self.adapter.session() as conn:
            rows = conn.execute("SELECT * FROM query_task WHERE is_enabled = 1 ORDER BY created_at DESC").fetchall()
        return [QueryTaskDB.model_validate(dict(row)) for row in rows]

    def disable(self, task_id: UUID) -> QueryTaskDB:
        return self.update(task_id, is_enabled=False)

    @staticmethod
    def new(**kwargs: object) -> QueryTaskDB:
        now = datetime.utcnow()
        return QueryTaskDB(id=uuid4(), created_at=now, updated_at=now, **kwargs)
