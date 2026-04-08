"""Repository for delivery record persistence operations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.core.schemas.enums import DeliveryStatus
from app.core.schemas.models import DeliveryRecordDB
from app.repositories.db_adapter import DatabaseAdapter
from app.repositories.exceptions import NotFoundError


class DeliveryRepository:
    def __init__(self, adapter: DatabaseAdapter):
        self.adapter = adapter

    def create(self, record: DeliveryRecordDB) -> DeliveryRecordDB:
        payload = record.model_dump()
        with self.adapter.session() as conn:
            conn.execute(
                """
                INSERT INTO delivery_record (
                    id, paper_id, target_type, target_ref, card_id,
                    delivery_status, delivered_at, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(payload["id"]),
                    str(payload["paper_id"]),
                    payload["target_type"],
                    payload["target_ref"],
                    payload["card_id"],
                    payload["delivery_status"].value,
                    payload["delivered_at"].isoformat() if payload["delivered_at"] else None,
                    payload["error_message"],
                ),
            )
        return record

    def update_status(
        self,
        delivery_id: UUID,
        status: DeliveryStatus,
        card_id: str | None = None,
        error_message: str | None = None,
    ) -> DeliveryRecordDB:
        delivered_at = datetime.utcnow().isoformat() if status == DeliveryStatus.SENT else None
        with self.adapter.session() as conn:
            cursor = conn.execute(
                """
                UPDATE delivery_record
                SET delivery_status = ?, card_id = COALESCE(?, card_id), delivered_at = ?, error_message = ?
                WHERE id = ?
                """,
                (status.value, card_id, delivered_at, error_message, str(delivery_id)),
            )
            if cursor.rowcount == 0:
                raise NotFoundError(f"delivery record not found: {delivery_id}")
        return self._get_by_id(delivery_id)

    def list_failed(self) -> list[DeliveryRecordDB]:
        with self.adapter.session() as conn:
            rows = conn.execute(
                "SELECT * FROM delivery_record WHERE delivery_status = ? ORDER BY id DESC",
                (DeliveryStatus.FAILED.value,),
            ).fetchall()
        return [DeliveryRecordDB.model_validate(dict(row)) for row in rows]

    def _get_by_id(self, delivery_id: UUID) -> DeliveryRecordDB:
        with self.adapter.session() as conn:
            row = conn.execute("SELECT * FROM delivery_record WHERE id = ?", (str(delivery_id),)).fetchone()
        if row is None:
            raise NotFoundError(f"delivery record not found: {delivery_id}")
        return DeliveryRecordDB.model_validate(dict(row))
