"""Repository for monitor run persistence operations."""

from __future__ import annotations

from uuid import UUID

from app.core.schemas.enums import MonitorRunStatus
from app.core.schemas.models import MonitorRunDB
from app.repositories._utils import to_db_value
from app.repositories.db_adapter import DatabaseAdapter
from app.repositories.exceptions import NotFoundError


class MonitorRunRepository:
    def __init__(self, adapter: DatabaseAdapter):
        self.adapter = adapter

    def create(self, data: MonitorRunDB) -> MonitorRunDB:
        payload = data.model_dump()
        with self.adapter.session() as conn:
            conn.execute(
                """
                INSERT INTO monitor_run (
                    id, query_task_id, triggered_at, window_start, window_end, status,
                    raw_result_count, new_result_count, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(
                    to_db_value(payload[k])
                    for k in (
                        "id",
                        "query_task_id",
                        "triggered_at",
                        "window_start",
                        "window_end",
                        "status",
                        "raw_result_count",
                        "new_result_count",
                        "error_message",
                    )
                ),
            )
        return data

    def update_status(
        self,
        run_id: UUID,
        status: MonitorRunStatus,
        error_message: str | None = None,
        raw_result_count: int | None = None,
        new_result_count: int | None = None,
    ) -> MonitorRunDB:
        updates: dict[str, object] = {"status": status.value, "error_message": error_message}
        if raw_result_count is not None:
            updates["raw_result_count"] = raw_result_count
        if new_result_count is not None:
            updates["new_result_count"] = new_result_count

        set_clause = ", ".join(f"{key} = ?" for key in updates)
        params = tuple(updates.values()) + (str(run_id),)
        with self.adapter.session() as conn:
            cursor = conn.execute(f"UPDATE monitor_run SET {set_clause} WHERE id = ?", params)
            if cursor.rowcount == 0:
                raise NotFoundError(f"monitor_run not found: {run_id}")
        return self.get_by_id(run_id)

    def get_by_id(self, run_id: UUID) -> MonitorRunDB:
        with self.adapter.session() as conn:
            row = conn.execute("SELECT * FROM monitor_run WHERE id = ?", (str(run_id),)).fetchone()
        if row is None:
            raise NotFoundError(f"monitor_run not found: {run_id}")
        return MonitorRunDB.model_validate(dict(row))

    def list_by_query_task(self, query_task_id: UUID) -> list[MonitorRunDB]:
        with self.adapter.session() as conn:
            rows = conn.execute(
                "SELECT * FROM monitor_run WHERE query_task_id = ? ORDER BY triggered_at DESC",
                (str(query_task_id),),
            ).fetchall()
        return [MonitorRunDB.model_validate(dict(row)) for row in rows]
