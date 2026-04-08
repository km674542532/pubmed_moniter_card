"""Runtime schemas for monitor run orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID


class RunOutcome(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


@dataclass(slots=True)
class PaperProcessResult:
    paper_id: UUID
    pmid: str | None
    llm_success: bool
    delivery_success: bool
    llm_error: str | None = None
    delivery_error: str | None = None


@dataclass(slots=True)
class MonitorRunResult:
    run_id: UUID
    query_task_id: UUID
    status: RunOutcome
    raw_result_count: int
    new_result_count: int
    paper_results: list[PaperProcessResult] = field(default_factory=list)
    error_message: str | None = None
