from __future__ import annotations

import unittest
from datetime import datetime
from uuid import uuid4

from app.core.schemas.models import PaperDB
from app.integrations.feishu.card_builder import build_paper_card
from app.integrations.llm.schemas import LlmClientResponse
from app.integrations.llm.service import LlmIntegrationError, LlmService
from app.integrations.pubmed.mapper import map_pubmed_record_to_paper


class _FakeLlmClient:
    class _Config:
        model = "fake-model"

    def __init__(self, responses: list[LlmClientResponse]):
        self.responses = responses
        self.config = self._Config()

    def chat_json(self, prompt: str, temperature: float = 0.2) -> LlmClientResponse:
        _ = (prompt, temperature)
        return self.responses.pop(0)


class IntegrationTests(unittest.TestCase):
    def _paper(self) -> PaperDB:
        now = datetime.utcnow()
        return PaperDB(
            id=uuid4(),
            pmid="123456",
            doi="10.1/2",
            title="A paper",
            abstract="abstract",
            journal="journal",
            publication_date=None,
            authors=["Alice", "Bob"],
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/123456/",
            raw_payload={"source": "x"},
            created_at=now,
            updated_at=now,
        )

    def test_pubmed_mapper_maps_to_paper_schema(self) -> None:
        raw = {
            "uid": "314159",
            "title": "Mapped title",
            "abstract": "Mapped abstract",
            "fulljournalname": "Nature",
            "sortpubdate": "2024-03-15",
            "authors": [{"name": "A"}, {"name": "B"}],
            "elocationid": "10.1000/test",
        }
        paper = map_pubmed_record_to_paper(raw)
        self.assertEqual(paper.pmid, "314159")
        self.assertEqual(paper.title, "Mapped title")
        self.assertEqual(paper.authors, ["A", "B"])
        self.assertEqual(paper.raw_payload, raw)

    def test_llm_service_outputs_structured_object(self) -> None:
        fake_client = _FakeLlmClient(
            responses=[
                LlmClientResponse(
                    success=True,
                    content={
                        "summary_version": 1,
                        "one_line_takeaway": "takeaway",
                        "plain_chinese_summary": "总结",
                        "core_methods": ["m1"],
                        "main_findings": ["f1"],
                        "relevance_level": "high",
                        "relevance_score": 0.9,
                        "novelty_score": 0.8,
                        "actionability_score": 0.7,
                        "recommended_action": "read_full_text",
                        "tags": ["oncology"],
                    },
                    raw_response={"ok": True},
                )
            ]
        )
        service = LlmService(client=fake_client)
        output = service.summarize_paper(self._paper())
        self.assertEqual(output.one_line_takeaway, "takeaway")
        self.assertEqual(output.relevance_level, "high")
        self.assertEqual(output.tags, ["oncology"])

    def test_feishu_card_builder_generates_stable_payload(self) -> None:
        fake_client = _FakeLlmClient(
            responses=[LlmClientResponse(success=True, content={"one_line_takeaway": "x"}, raw_response={})]
        )
        summary = LlmService(fake_client).summarize_paper(self._paper())
        card = build_paper_card(self._paper(), summary, metadata={"run_id": "r1"})
        self.assertEqual(card["msg_type"], "interactive")
        self.assertIn("card", card)
        self.assertEqual(card["metadata"]["run_id"], "r1")

    def test_integration_failure_is_visible_to_caller(self) -> None:
        fake_client = _FakeLlmClient(
            responses=[LlmClientResponse(success=False, content=None, raw_response=None, error_message="timeout")]
        )
        service = LlmService(client=fake_client)
        with self.assertRaises(LlmIntegrationError) as ctx:
            service.summarize_paper(self._paper())
        self.assertIn("stage A", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
