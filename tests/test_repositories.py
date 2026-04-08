from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.core.schemas.enums import DeliveryStatus, MonitorRunStatus
from app.core.schemas.models import (
    DeliveryRecordDB,
    LlmSummaryDB,
    MonitorRunDB,
    PaperDB,
    PaperQueryHitDB,
    QueryTaskDB,
)
from app.repositories.db_adapter import SQLiteAdapter
from app.repositories.delivery_repository import DeliveryRepository
from app.repositories.llm_summary_repository import LlmSummaryRepository
from app.repositories.monitor_run_repository import MonitorRunRepository
from app.repositories.paper_repository import PaperQueryHitRepository, PaperRepository
from app.repositories.query_task_repository import QueryTaskRepository
from db.init_db import init_db


class RepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test.db"
        init_db(self.db_path)
        self.adapter = SQLiteAdapter(self.db_path)

        self.query_repo = QueryTaskRepository(self.adapter)
        self.run_repo = MonitorRunRepository(self.adapter)
        self.paper_repo = PaperRepository(self.adapter)
        self.hit_repo = PaperQueryHitRepository(self.adapter)
        self.summary_repo = LlmSummaryRepository(self.adapter)
        self.delivery_repo = DeliveryRepository(self.adapter)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def _seed_query_and_run(self) -> tuple[QueryTaskDB, MonitorRunDB]:
        now = datetime.utcnow()
        task = QueryTaskDB(
            id=uuid4(),
            name="oncology",
            query_expression="cancer[Title]",
            schedule="0 8 * * *",
            timezone="UTC",
            lookback_hours=24,
            is_enabled=True,
            created_at=now,
            updated_at=now,
            created_by="test",
            updated_by="test",
        )
        self.query_repo.create(task)

        run = MonitorRunDB(
            id=uuid4(),
            query_task_id=task.id,
            triggered_at=now,
            window_start=now,
            window_end=now,
            status=MonitorRunStatus.PENDING,
            raw_result_count=0,
            new_result_count=0,
            error_message=None,
        )
        self.run_repo.create(run)
        return task, run

    def test_paper_upsert_should_not_duplicate(self) -> None:
        now = datetime.utcnow()
        p1 = PaperDB(
            id=uuid4(),
            pmid="12345",
            doi="10.1000/abc",
            title="First",
            abstract="A",
            journal="J",
            publication_date=None,
            authors=["A1"],
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/12345/",
            raw_payload={"x": 1},
            created_at=now,
            updated_at=now,
        )
        saved1 = self.paper_repo.upsert_paper(p1)

        p2 = p1.model_copy(update={"id": uuid4(), "title": "Updated"})
        saved2 = self.paper_repo.upsert_paper(p2)

        self.assertEqual(saved1.id, saved2.id)
        self.assertEqual(saved2.title, "Updated")

    def test_one_paper_can_have_multiple_query_hits(self) -> None:
        task, run = self._seed_query_and_run()
        now = datetime.utcnow()
        paper = self.paper_repo.upsert_paper(
            PaperDB(
                id=uuid4(),
                pmid="99999",
                doi=None,
                title="Hit Paper",
                abstract=None,
                journal=None,
                publication_date=None,
                authors=[],
                pubmed_url=None,
                raw_payload=None,
                created_at=now,
                updated_at=now,
            )
        )
        hit1 = PaperQueryHitDB(
            id=uuid4(),
            paper_id=paper.id,
            query_task_id=task.id,
            monitor_run_id=run.id,
            matched_at=now,
            rank_in_run=1,
        )
        hit2 = hit1.model_copy(update={"id": uuid4(), "rank_in_run": 2})
        self.hit_repo.create_hit(hit1)
        self.hit_repo.create_hit(hit2)

        hits = self.hit_repo.list_hits_by_run(run.id)
        self.assertEqual(len(hits), 2)

    def test_summary_supports_multiple_versions(self) -> None:
        now = datetime.utcnow()
        paper = self.paper_repo.upsert_paper(
            PaperDB(
                id=uuid4(),
                pmid="22222",
                doi=None,
                title="Summary Paper",
                abstract=None,
                journal=None,
                publication_date=None,
                authors=[],
                pubmed_url=None,
                raw_payload=None,
                created_at=now,
                updated_at=now,
            )
        )

        s1 = LlmSummaryDB(
            id=uuid4(),
            paper_id=paper.id,
            model_name="gpt",
            prompt_version="v1",
            summary_version=1,
            generated_at=now,
        )
        s2 = s1.model_copy(update={"id": uuid4(), "summary_version": 2})
        self.summary_repo.create(s1)
        self.summary_repo.create(s2)

        latest = self.summary_repo.get_latest_by_paper_id(paper.id)
        self.assertIsNotNone(latest)
        self.assertEqual(latest.summary_version, 2)

    def test_failed_delivery_can_be_queried(self) -> None:
        now = datetime.utcnow()
        paper = self.paper_repo.upsert_paper(
            PaperDB(
                id=uuid4(),
                pmid="33333",
                doi=None,
                title="Delivery Paper",
                abstract=None,
                journal=None,
                publication_date=None,
                authors=[],
                pubmed_url=None,
                raw_payload=None,
                created_at=now,
                updated_at=now,
            )
        )
        record = DeliveryRecordDB(
            id=uuid4(),
            paper_id=paper.id,
            target_type="feishu",
            target_ref="chat_1",
            card_id=None,
            delivery_status=DeliveryStatus.PENDING,
            delivered_at=None,
            error_message=None,
        )
        self.delivery_repo.create(record)
        self.delivery_repo.update_status(record.id, DeliveryStatus.FAILED, error_message="network error")

        failed = self.delivery_repo.list_failed()
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0].error_message, "network error")


if __name__ == "__main__":
    unittest.main()
