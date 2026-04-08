"""Handler entry for monitor run execution."""

from __future__ import annotations

from uuid import UUID

from app.agents.monitor_agent.schemas.monitor_run_runtime import MonitorRunResult
from app.agents.monitor_agent.services.monitor_run_service import MonitorRunService


class MonitorRunHandler:
    def __init__(self, service: MonitorRunService):
        self.service = service

    def run_query_task(self, query_task_id: UUID) -> MonitorRunResult:
        return self.service.run_query_task(query_task_id)
