"""Repository for preference profile persistence operations."""

from __future__ import annotations

from datetime import datetime

from app.core.schemas.models import PreferenceProfileDB
from app.repositories._utils import from_db_json, to_db_value
from app.repositories.db_adapter import DatabaseAdapter


class PreferenceRepository:
    def __init__(self, adapter: DatabaseAdapter):
        self.adapter = adapter

    def get_active_profile(self) -> PreferenceProfileDB | None:
        with self.adapter.session() as conn:
            row = conn.execute("SELECT * FROM preference_profile ORDER BY updated_at DESC LIMIT 1").fetchone()
        if row is None:
            return None
        return self._parse_row(dict(row))

    def upsert_profile(self, profile: PreferenceProfileDB) -> PreferenceProfileDB:
        payload = profile.model_dump()
        payload["updated_at"] = datetime.utcnow()
        with self.adapter.session() as conn:
            existing = conn.execute(
                "SELECT id FROM preference_profile WHERE profile_name = ?",
                (profile.profile_name,),
            ).fetchone()
            if existing:
                payload["id"] = existing["id"]
                conn.execute(
                    """
                    UPDATE preference_profile
                    SET hard_rules=?, soft_preferences=?, excluded_patterns=?, preferred_journals=?, updated_at=?
                    WHERE profile_name=?
                    """,
                    (
                        to_db_value(payload["hard_rules"]),
                        to_db_value(payload["soft_preferences"]),
                        to_db_value(payload["excluded_patterns"]),
                        to_db_value(payload["preferred_journals"]),
                        to_db_value(payload["updated_at"]),
                        payload["profile_name"],
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO preference_profile (
                        id, profile_name, hard_rules, soft_preferences,
                        excluded_patterns, preferred_journals, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(payload["id"]),
                        payload["profile_name"],
                        to_db_value(payload["hard_rules"]),
                        to_db_value(payload["soft_preferences"]),
                        to_db_value(payload["excluded_patterns"]),
                        to_db_value(payload["preferred_journals"]),
                        to_db_value(payload["updated_at"]),
                    ),
                )
        return self.get_active_profile()

    @staticmethod
    def _parse_row(data: dict) -> PreferenceProfileDB:
        data["hard_rules"] = from_db_json(data.get("hard_rules")) or []
        data["soft_preferences"] = from_db_json(data.get("soft_preferences")) or []
        data["excluded_patterns"] = from_db_json(data.get("excluded_patterns")) or []
        data["preferred_journals"] = from_db_json(data.get("preferred_journals")) or []
        return PreferenceProfileDB.model_validate(data)
