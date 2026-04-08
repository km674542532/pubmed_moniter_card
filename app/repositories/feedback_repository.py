"""Repository for user feedback persistence operations."""

from __future__ import annotations

from uuid import UUID

from app.core.schemas.models import UserFeedbackDB
from app.repositories.db_adapter import DatabaseAdapter


class FeedbackRepository:
    def __init__(self, adapter: DatabaseAdapter):
        self.adapter = adapter

    def create(self, feedback: UserFeedbackDB) -> UserFeedbackDB:
        payload = feedback.model_dump()
        with self.adapter.session() as conn:
            conn.execute(
                """
                INSERT INTO user_feedback (id, paper_id, source, label, note, actor, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(payload["id"]),
                    str(payload["paper_id"]),
                    payload["source"],
                    payload["label"].value,
                    payload["note"],
                    payload["actor"],
                    payload["created_at"].isoformat(),
                ),
            )
        return feedback

    def list_by_paper_id(self, paper_id: UUID) -> list[UserFeedbackDB]:
        with self.adapter.session() as conn:
            rows = conn.execute(
                "SELECT * FROM user_feedback WHERE paper_id = ? ORDER BY created_at DESC",
                (str(paper_id),),
            ).fetchall()
        return [UserFeedbackDB.model_validate(dict(row)) for row in rows]

    def list_recent(self, limit: int = 50) -> list[UserFeedbackDB]:
        with self.adapter.session() as conn:
            rows = conn.execute(
                "SELECT * FROM user_feedback ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [UserFeedbackDB.model_validate(dict(row)) for row in rows]
