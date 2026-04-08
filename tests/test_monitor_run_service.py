from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.agents.monitor_agent.services.monitor_run_service import MonitorRunService
from app.core.schemas.models import QueryTaskDB, PaperCreate
from app.integrations.feishu.schemas import FeishuDeliveryResult
from app.integrations.llm.schemas import LlmSummaryOutput
from app.repositories.db_adapter import SQLiteAdapter
from app.repositories.delivery_repository import DeliveryRepository
from app.repositories.llm_summary_repository import LlmSummaryRepository
from app.repositories.monitor_run_repository import MonitorRunRepository
from app.repositories.paper_repository import PaperQueryHitRepository, PaperRepository
from app.repositories.query_task_repository import QueryTaskRepository
from db.init_db import init_db


class _FakePubMedService:
    def search_and_fetch(self, query_expression: str, start_date: str, end_date: str, retmax: int = 100):
        _ = (query_expression, start_date, end_date, retmax)

        class _R:
            pmids = ["1", "2"]
            papers = [
                PaperCreate(pmid="1", title="p1", authors=[], raw_payload={"uid": "1"}),
                PaperCreate(pmid="2", title="p2", authors=[], raw_payload={"uid": "2"}),
            ]
            search_raw_response = {}
            fetch_raw_response = {}

        return _R()


class _FakeLlmService:
    def __init__(self):
        self.calls = 0

    def summarize_paper(self, paper):
        self.calls += 1
        if paper.pmid == "2":
            raise RuntimeError("llm boom")
        return LlmSummaryOutput(model_name="m", prompt_version="v1", summary_version=1, one_line_takeaway="ok")


class _FakeFeishuClient:
    def send_card(self, payload: dict) -> FeishuDeliveryResult:
        _ = payload
        return FeishuDeliveryResult(success=True, card_id="msg_1", raw_response={"code": 0})


class MonitorRunServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        init_db(self.db_path)
        adapter = SQLiteAdapter(self.db_path)
        self.query_repo = QueryTaskRepository(adapter)
        self.run_repo = MonitorRunRepository(adapter)
        self.paper_repo = PaperRepository(adapter)
        self.hit_repo = PaperQueryHitRepository(adapter)
        self.summary_repo = LlmSummaryRepository(adapter)
        self.delivery_repo = DeliveryRepository(adapter)

        now = datetime.utcnow()
        self.task = QueryTaskDB(
            id=uuid4(),
            name="t",
            query_expression="covid",
            schedule="0 0 * * *",
            timezone="UTC",
            lookback_hours=24,
            is_enabled=True,
            created_at=now,
            updated_at=now,
            created_by=None,
            updated_by=None,
        )
        self.query_repo.create(self.task)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_run_should_be_partial_when_one_paper_llm_fails(self) -> None:
        service = MonitorRunService(
            query_task_repo=self.query_repo,
            monitor_run_repo=self.run_repo,
            paper_repo=self.paper_repo,
            paper_hit_repo=self.hit_repo,
            summary_repo=self.summary_repo,
            delivery_repo=self.delivery_repo,
            pubmed_service=_FakePubMedService(),
            llm_service=_FakeLlmService(),
            feishu_client=_FakeFeishuClient(),
        )
        result = service.run_query_task(self.task.id)
        self.assertEqual(result.status.value, "partial_success")
        self.assertEqual(result.raw_result_count, 2)
        self.assertEqual(len(result.paper_results), 2)


if __name__ == "__main__":
    unittest.main()
