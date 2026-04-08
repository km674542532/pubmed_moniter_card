"""Structured event logger for monitor run lifecycle."""

from __future__ import annotations

import json
import logging
from uuid import UUID


class MonitorEventLogger:
    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger("monitor_run")

    def emit(
        self,
        *,
        run_id: UUID | None,
        query_task_id: UUID,
        step: str,
        status: str,
        payload_ref: str | None = None,
        error: str | None = None,
        **extra: object,
    ) -> None:
        payload = {
            "run_id": str(run_id) if run_id else None,
            "query_task_id": str(query_task_id),
            "step": step,
            "status": status,
            "payload_ref": payload_ref,
            "error": error,
            **extra,
        }
        level = logging.ERROR if error else logging.INFO
        self.logger.log(level, json.dumps(payload, ensure_ascii=False))
