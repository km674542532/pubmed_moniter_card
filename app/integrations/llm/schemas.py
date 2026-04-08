"""Structured schemas for LLM integration outputs (non-persistence models)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class LlmSummaryOutput:
    model_name: str
    prompt_version: str
    summary_version: int
    one_line_takeaway: str | None = None
    plain_chinese_summary: str | None = None
    study_type: str | None = None
    core_methods: list[str] = field(default_factory=list)
    main_findings: list[str] = field(default_factory=list)
    why_it_matters: str | None = None
    relevance_level: str = "medium"
    relevance_score: float = 0.0
    novelty_score: float = 0.0
    actionability_score: float = 0.0
    reason_for_relevance: str | None = None
    tags: list[str] = field(default_factory=list)
    recommended_action: str = "save_for_later"
    structured_output: dict | None = None


@dataclass(slots=True)
class LlmHealthcheckResult:
    ok: bool
    provider: str
    model: str
    message: str


@dataclass(slots=True)
class LlmClientResponse:
    success: bool
    content: dict | None
    raw_response: dict | None
    error_message: str | None = None
