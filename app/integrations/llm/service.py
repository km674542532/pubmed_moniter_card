"""LLM integration service for structured paper summarization."""

from __future__ import annotations

from app.core.schemas.models import PaperDB, PaperView
from app.integrations.llm.client import LlmClient, LlmClientError
from app.integrations.llm.prompt_builder import (
    build_general_literature_prompt,
    build_preference_mapping_prompt,
)
from app.integrations.llm.schemas import LlmSummaryOutput


class LlmIntegrationError(RuntimeError):
    """Raised when summarize flow cannot produce structured output."""


class LlmService:
    def __init__(self, client: LlmClient, prompt_version: str = "v1"):
        self.client = client
        self.prompt_version = prompt_version

    def summarize_paper(
        self,
        paper: PaperDB | PaperView,
        preference_context: dict | None = None,
    ) -> LlmSummaryOutput:
        stage_a_prompt = build_general_literature_prompt(paper)
        stage_a = self.client.chat_json(stage_a_prompt)
        if not stage_a.success or stage_a.content is None:
            raise LlmIntegrationError(f"LLM stage A summarize failed: {stage_a.error_message}")

        summary_payload = dict(stage_a.content)

        # Stage B 预留：仅在有偏好上下文时做附加映射，输出合并到结构化结果。
        if preference_context:
            stage_b_prompt = build_preference_mapping_prompt(summary_payload, preference_context)
            stage_b = self.client.chat_json(stage_b_prompt)
            if not stage_b.success or stage_b.content is None:
                raise LlmIntegrationError(f"LLM stage B preference mapping failed: {stage_b.error_message}")
            summary_payload["structured_output"] = {
                "stage_a": stage_a.content,
                "stage_b": stage_b.content,
            }

        try:
            return LlmSummaryOutput(
                model_name=self.client.config.model,
                prompt_version=self.prompt_version,
                summary_version=int(summary_payload.get("summary_version", 1)),
                one_line_takeaway=summary_payload.get("one_line_takeaway"),
                plain_chinese_summary=summary_payload.get("plain_chinese_summary"),
                study_type=summary_payload.get("study_type"),
                core_methods=summary_payload.get("core_methods", []),
                main_findings=summary_payload.get("main_findings", []),
                why_it_matters=summary_payload.get("why_it_matters"),
                relevance_level=summary_payload.get("relevance_level", "medium"),
                relevance_score=float(summary_payload.get("relevance_score", 0.0)),
                novelty_score=float(summary_payload.get("novelty_score", 0.0)),
                actionability_score=float(summary_payload.get("actionability_score", 0.0)),
                reason_for_relevance=summary_payload.get("reason_for_relevance"),
                tags=summary_payload.get("tags", []),
                recommended_action=summary_payload.get("recommended_action", "save_for_later"),
                structured_output=summary_payload.get("structured_output"),
            )
        except Exception as exc:
            raise LlmIntegrationError(f"LLM output mapping failed: {exc}") from exc
