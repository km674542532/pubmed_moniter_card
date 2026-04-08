"""Repository for LLM summary persistence with multi-version support."""

from __future__ import annotations

from uuid import UUID

from app.core.schemas.models import LlmSummaryDB
from app.repositories._utils import from_db_json, to_db_value
from app.repositories.db_adapter import DatabaseAdapter


class LlmSummaryRepository:
    def __init__(self, adapter: DatabaseAdapter):
        self.adapter = adapter

    def create(self, summary: LlmSummaryDB) -> LlmSummaryDB:
        payload = summary.model_dump()
        with self.adapter.session() as conn:
            conn.execute(
                """
                INSERT INTO llm_summary (
                    id, paper_id, model_name, prompt_version, summary_version,
                    one_line_takeaway, plain_chinese_summary, study_type,
                    core_methods, main_findings, why_it_matters,
                    relevance_level, relevance_score, novelty_score, actionability_score,
                    reason_for_relevance, tags, recommended_action, structured_output, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(to_db_value(payload[k]) for k in (
                    "id", "paper_id", "model_name", "prompt_version", "summary_version",
                    "one_line_takeaway", "plain_chinese_summary", "study_type", "core_methods", "main_findings",
                    "why_it_matters", "relevance_level", "relevance_score", "novelty_score", "actionability_score",
                    "reason_for_relevance", "tags", "recommended_action", "structured_output", "generated_at"
                )),
            )
        return summary

    def get_latest_by_paper_id(self, paper_id: UUID) -> LlmSummaryDB | None:
        with self.adapter.session() as conn:
            row = conn.execute(
                "SELECT * FROM llm_summary WHERE paper_id = ? ORDER BY summary_version DESC, generated_at DESC LIMIT 1",
                (str(paper_id),),
            ).fetchone()
        if row is None:
            return None
        return self._parse_row(dict(row))

    def list_by_paper_ids(self, paper_ids: list[UUID]) -> list[LlmSummaryDB]:
        if not paper_ids:
            return []
        placeholders = ",".join("?" for _ in paper_ids)
        with self.adapter.session() as conn:
            rows = conn.execute(
                f"SELECT * FROM llm_summary WHERE paper_id IN ({placeholders}) ORDER BY paper_id, summary_version DESC",
                tuple(str(i) for i in paper_ids),
            ).fetchall()
        return [self._parse_row(dict(row)) for row in rows]

    @staticmethod
    def _parse_row(data: dict) -> LlmSummaryDB:
        data["core_methods"] = from_db_json(data.get("core_methods")) or []
        data["main_findings"] = from_db_json(data.get("main_findings")) or []
        data["tags"] = from_db_json(data.get("tags")) or []
        data["structured_output"] = from_db_json(data.get("structured_output"))
        return LlmSummaryDB.model_validate(data)
