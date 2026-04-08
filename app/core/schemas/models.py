"""Unified core schemas for persistence, service I/O, and external payloads."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas.base import AuditFieldsModel, IdentifiedModel, SchemaModel, TimestampedModel
from app.core.schemas.enums import (
    DeliveryStatus,
    FeedbackLabel,
    MonitorRunStatus,
    RecommendedAction,
    RelevanceLevel,
)


class QueryTaskDB(IdentifiedModel, AuditFieldsModel):
    """Persistent monitor query definition."""

    name: str = Field(description="Human-readable task name")
    query_expression: str = Field(description="Raw query expression used by data source")
    schedule: str = Field(description="Cron or schedule expression")
    timezone: str = Field(default="UTC", description="IANA timezone for schedule")
    lookback_hours: int = Field(default=24, ge=1, description="Window overlap for late arrivals")
    is_enabled: bool = Field(default=True, description="Task enabled flag")


class QueryTaskUpsert(SchemaModel):
    """Service input model for creating/updating query tasks."""

    name: str
    query_expression: str
    schedule: str
    timezone: str = "UTC"
    lookback_hours: int = Field(default=24, ge=1)
    is_enabled: bool = True


class QueryTaskView(SchemaModel):
    """Service output model used by internal callers."""

    id: UUID
    name: str
    query_expression: str
    schedule: str
    timezone: str
    lookback_hours: int
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class MonitorRunDB(IdentifiedModel):
    """Persistent execution record for one monitor run."""

    query_task_id: UUID = Field(description="Owning query task ID")
    triggered_at: datetime = Field(description="When scheduler triggered the run")
    window_start: datetime = Field(description="Monitor window start in UTC")
    window_end: datetime = Field(description="Monitor window end in UTC")
    status: MonitorRunStatus = Field(description="Current run state")
    raw_result_count: int = Field(default=0, ge=0, description="Total fetched result count")
    new_result_count: int = Field(default=0, ge=0, description="Count of deduplicated new papers")
    error_message: str | None = Field(default=None, description="Error details for failed runs")


class MonitorRunCreate(SchemaModel):
    """Service input model when starting a monitor run."""

    query_task_id: UUID
    triggered_at: datetime
    window_start: datetime
    window_end: datetime
    status: MonitorRunStatus = MonitorRunStatus.PENDING


class MonitorRunView(SchemaModel):
    """Service output model for monitor run inspection."""

    id: UUID
    query_task_id: UUID
    triggered_at: datetime
    window_start: datetime
    window_end: datetime
    status: MonitorRunStatus
    raw_result_count: int
    new_result_count: int
    error_message: str | None


class PaperDB(IdentifiedModel, TimestampedModel):
    """Canonical paper record persisted by the system."""

    pmid: str | None = Field(default=None, description="PubMed identifier")
    doi: str | None = Field(default=None, description="DOI identifier")
    title: str = Field(description="Paper title")
    abstract: str | None = Field(default=None, description="Paper abstract text")
    journal: str | None = Field(default=None, description="Journal name")
    publication_date: date | None = Field(default=None, description="Publication date")
    authors: list[str] = Field(default_factory=list, description="Ordered author names")
    pubmed_url: str | None = Field(default=None, description="PubMed URL")
    raw_payload: dict[str, Any] | None = Field(
        default=None,
        description="Original provider payload for traceability",
    )


class PaperCreate(SchemaModel):
    """Service input model for creating canonical paper records."""

    pmid: str | None = None
    doi: str | None = None
    title: str
    abstract: str | None = None
    journal: str | None = None
    publication_date: date | None = None
    authors: list[str] = Field(default_factory=list)
    pubmed_url: str | None = None
    raw_payload: dict[str, Any] | None = None


class ExternalPaperPayload(SchemaModel):
    """External integration payload before canonical normalization."""

    source: str = Field(description="Provider/source name")
    external_id: str | None = Field(default=None, description="Provider native identifier")
    fetched_at: datetime = Field(description="Payload fetch time")
    payload: dict[str, Any] = Field(description="Raw integration payload")


class PaperView(SchemaModel):
    """Service output model for paper detail queries."""

    id: UUID
    pmid: str | None
    doi: str | None
    title: str
    abstract: str | None
    journal: str | None
    publication_date: date | None
    authors: list[str]
    pubmed_url: str | None
    created_at: datetime
    updated_at: datetime


class PaperQueryHitDB(IdentifiedModel):
    """Mapping record linking paper hits to query/run."""

    paper_id: UUID
    query_task_id: UUID
    monitor_run_id: UUID
    matched_at: datetime
    rank_in_run: int | None = Field(default=None, ge=1)


class PaperQueryHitCreate(SchemaModel):
    """Service input model for persisting query hits."""

    paper_id: UUID
    query_task_id: UUID
    monitor_run_id: UUID
    matched_at: datetime
    rank_in_run: int | None = Field(default=None, ge=1)


class LlmSummaryDB(IdentifiedModel):
    """Persistent structured summary generated by LLM."""

    paper_id: UUID
    model_name: str
    prompt_version: str
    summary_version: int = Field(default=1, ge=1)
    one_line_takeaway: str | None = None
    plain_chinese_summary: str | None = None
    study_type: str | None = None
    core_methods: list[str] = Field(default_factory=list)
    main_findings: list[str] = Field(default_factory=list)
    why_it_matters: str | None = None
    relevance_level: RelevanceLevel = RelevanceLevel.MEDIUM
    relevance_score: float = Field(default=0.0, ge=0, le=1)
    novelty_score: float = Field(default=0.0, ge=0, le=1)
    actionability_score: float = Field(default=0.0, ge=0, le=1)
    reason_for_relevance: str | None = None
    tags: list[str] = Field(default_factory=list)
    recommended_action: RecommendedAction = RecommendedAction.SAVE_FOR_LATER
    structured_output: dict[str, Any] | None = None
    generated_at: datetime


class LlmSummaryCreate(SchemaModel):
    """Service input model for storing LLM summary output."""

    paper_id: UUID
    model_name: str
    prompt_version: str
    one_line_takeaway: str | None = None
    plain_chinese_summary: str | None = None
    study_type: str | None = None
    core_methods: list[str] = Field(default_factory=list)
    main_findings: list[str] = Field(default_factory=list)
    why_it_matters: str | None = None
    relevance_level: RelevanceLevel = RelevanceLevel.MEDIUM
    relevance_score: float = Field(default=0.0, ge=0, le=1)
    novelty_score: float = Field(default=0.0, ge=0, le=1)
    actionability_score: float = Field(default=0.0, ge=0, le=1)
    reason_for_relevance: str | None = None
    tags: list[str] = Field(default_factory=list)
    recommended_action: RecommendedAction = RecommendedAction.SAVE_FOR_LATER
    structured_output: dict[str, Any] | None = None
    generated_at: datetime


class ExternalSummaryPayload(SchemaModel):
    """External payload contract returned to client applications."""

    paper_id: UUID
    summary: str
    relevance_level: RelevanceLevel
    recommended_action: RecommendedAction
    tags: list[str] = Field(default_factory=list)


class DeliveryRecordDB(IdentifiedModel):
    """Persistent delivery execution record for each target."""

    paper_id: UUID
    target_type: str = Field(description="Delivery channel type, e.g. feishu/email")
    target_ref: str = Field(description="Channel reference such as chat_id")
    card_id: str | None = Field(default=None, description="Remote card/message ID")
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING
    delivered_at: datetime | None = None
    error_message: str | None = None


class DeliveryRequest(SchemaModel):
    """Service input model for creating delivery jobs."""

    paper_id: UUID
    target_type: str
    target_ref: str


class DeliveryRecordView(SchemaModel):
    """Service output model for delivery status queries."""

    id: UUID
    paper_id: UUID
    target_type: str
    target_ref: str
    card_id: str | None
    delivery_status: DeliveryStatus
    delivered_at: datetime | None
    error_message: str | None


class UserFeedbackDB(IdentifiedModel):
    """Persistent normalized feedback record."""

    paper_id: UUID
    source: str = Field(description="Feedback source/channel")
    label: FeedbackLabel
    note: str | None = Field(default=None, description="Optional free-text note")
    actor: str | None = Field(default=None, description="User/service that created the feedback")
    created_at: datetime


class UserFeedbackCreate(SchemaModel):
    """Service input model for collecting feedback."""

    paper_id: UUID
    source: str
    label: FeedbackLabel
    note: str | None = None
    actor: str | None = None


class PreferenceProfileDB(IdentifiedModel):
    """Preference profile used for filtering and ranking behavior."""

    profile_name: str
    hard_rules: list[str] = Field(default_factory=list)
    soft_preferences: list[str] = Field(default_factory=list)
    excluded_patterns: list[str] = Field(default_factory=list)
    preferred_journals: list[str] = Field(default_factory=list)
    updated_at: datetime


class PreferenceProfileUpsert(SchemaModel):
    """Service input model for profile update operations."""

    profile_name: str
    hard_rules: list[str] = Field(default_factory=list)
    soft_preferences: list[str] = Field(default_factory=list)
    excluded_patterns: list[str] = Field(default_factory=list)
    preferred_journals: list[str] = Field(default_factory=list)


class PreferenceProfileView(SchemaModel):
    """Service output model for preference profile retrieval."""

    id: UUID
    profile_name: str
    hard_rules: list[str]
    soft_preferences: list[str]
    excluded_patterns: list[str]
    preferred_journals: list[str]
    updated_at: datetime
