"""Manual entry script to run one monitor task once."""

from __future__ import annotations

import argparse
import os
from uuid import UUID

from app.agents.monitor_agent.handler.monitor_run_handler import MonitorRunHandler
from app.agents.monitor_agent.services.monitor_run_service import MonitorRunService
from app.integrations.feishu.client import FeishuClient, FeishuClientConfig
from app.integrations.llm.client import LlmClient, LlmClientConfig
from app.integrations.llm.service import LlmService
from app.integrations.pubmed.fetch_client import PubMedFetchClient
from app.integrations.pubmed.search_client import PubMedSearchClient
from app.integrations.pubmed.service import PubMedService
from app.repositories.db_adapter import SQLiteAdapter
from app.repositories.delivery_repository import DeliveryRepository
from app.repositories.llm_summary_repository import LlmSummaryRepository
from app.repositories.monitor_run_repository import MonitorRunRepository
from app.repositories.paper_repository import PaperQueryHitRepository, PaperRepository
from app.repositories.query_task_repository import QueryTaskRepository


def build_handler(db_path: str) -> MonitorRunHandler:
    adapter = SQLiteAdapter(db_path)

    query_repo = QueryTaskRepository(adapter)
    run_repo = MonitorRunRepository(adapter)
    paper_repo = PaperRepository(adapter)
    hit_repo = PaperQueryHitRepository(adapter)
    summary_repo = LlmSummaryRepository(adapter)
    delivery_repo = DeliveryRepository(adapter)

    pubmed_service = PubMedService(PubMedSearchClient(timeout=20), PubMedFetchClient(timeout=20))

    llm_url = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1/chat/completions")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm_provider = os.getenv("LLM_PROVIDER", "openai-compatible")
    llm_key = os.getenv("LLM_API_KEY")
    llm_client = LlmClient(
        LlmClientConfig(
            provider=llm_provider,
            model=llm_model,
            base_url=llm_url,
            api_key=llm_key,
            timeout=int(os.getenv("LLM_TIMEOUT", "30")),
        )
    )

    feishu_webhook = os.getenv("FEISHU_WEBHOOK_URL", "http://localhost:9999/mock_feishu")
    feishu_client = FeishuClient(
        FeishuClientConfig(
            webhook_url=feishu_webhook,
            timeout=int(os.getenv("FEISHU_TIMEOUT", "15")),
            max_retries=int(os.getenv("FEISHU_MAX_RETRIES", "2")),
        )
    )

    service = MonitorRunService(
        query_task_repo=query_repo,
        monitor_run_repo=run_repo,
        paper_repo=paper_repo,
        paper_hit_repo=hit_repo,
        summary_repo=summary_repo,
        delivery_repo=delivery_repo,
        pubmed_service=pubmed_service,
        llm_service=LlmService(llm_client),
        feishu_client=feishu_client,
    )
    return MonitorRunHandler(service)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run monitor task once by query_task_id")
    parser.add_argument("query_task_id", help="QueryTask UUID")
    parser.add_argument("--db-path", default=os.getenv("MONITOR_DB_PATH", "app.db"))
    args = parser.parse_args()

    handler = build_handler(args.db_path)
    result = handler.run_query_task(UUID(args.query_task_id))
    print(
        {
            "run_id": str(result.run_id),
            "query_task_id": str(result.query_task_id),
            "status": result.status.value,
            "raw_result_count": result.raw_result_count,
            "new_result_count": result.new_result_count,
            "paper_count": len(result.paper_results),
            "error_message": result.error_message,
        }
    )


if __name__ == "__main__":
    main()
