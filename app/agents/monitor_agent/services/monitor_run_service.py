"""Main orchestration service for a single monitor run execution."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.agents.monitor_agent.schemas.monitor_run_runtime import MonitorRunResult, PaperProcessResult, RunOutcome
from app.agents.monitor_agent.services.event_logger import MonitorEventLogger
from app.core.schemas.enums import DeliveryStatus, MonitorRunStatus, RecommendedAction, RelevanceLevel
from app.core.schemas.models import DeliveryRecordDB, LlmSummaryDB, MonitorRunDB, PaperCreate, PaperDB, PaperQueryHitDB
from app.integrations.feishu.card_builder import build_paper_card
from app.integrations.feishu.client import FeishuClient
from app.integrations.llm.schemas import LlmSummaryOutput
from app.integrations.llm.service import LlmService
from app.integrations.pubmed.search_client import PubMedSearchError
from app.integrations.pubmed.service import PubMedService
from app.repositories.delivery_repository import DeliveryRepository
from app.repositories.exceptions import NotFoundError
from app.repositories.llm_summary_repository import LlmSummaryRepository
from app.repositories.monitor_run_repository import MonitorRunRepository
from app.repositories.paper_repository import PaperQueryHitRepository, PaperRepository
from app.repositories.query_task_repository import QueryTaskRepository


class MonitorRunService:
    """Coordinates query task execution from PubMed to Feishu delivery."""

    def __init__(
        self,
        query_task_repo: QueryTaskRepository,
        monitor_run_repo: MonitorRunRepository,
        paper_repo: PaperRepository,
        paper_hit_repo: PaperQueryHitRepository,
        summary_repo: LlmSummaryRepository,
        delivery_repo: DeliveryRepository,
        pubmed_service: PubMedService,
        llm_service: LlmService,
        feishu_client: FeishuClient,
        event_logger: MonitorEventLogger | None = None,
    ):
        self.query_task_repo = query_task_repo
        self.monitor_run_repo = monitor_run_repo
        self.paper_repo = paper_repo
        self.paper_hit_repo = paper_hit_repo
        self.summary_repo = summary_repo
        self.delivery_repo = delivery_repo
        self.pubmed_service = pubmed_service
        self.llm_service = llm_service
        self.feishu_client = feishu_client
        self.event_logger = event_logger or MonitorEventLogger()

    def run_query_task(self, query_task_id: UUID) -> MonitorRunResult:
        task = self.query_task_repo.get_by_id(query_task_id)
        if not task.is_enabled:
            raise RuntimeError(f"query_task is disabled: {query_task_id}")

        now = datetime.utcnow()
        window_end = now
        window_start = now - timedelta(hours=task.lookback_hours)
        run = MonitorRunDB(
            id=uuid4(),
            query_task_id=task.id,
            triggered_at=now,
            window_start=window_start,
            window_end=window_end,
            status=MonitorRunStatus.RUNNING,
            raw_result_count=0,
            new_result_count=0,
            error_message=None,
        )
        self.monitor_run_repo.create(run)
        self.event_logger.emit(
            run_id=run.id,
            query_task_id=query_task_id,
            step="monitor_run_started",
            status=RunOutcome.RUNNING.value,
            payload_ref=f"monitor_run:{run.id}",
        )

        try:
            self.event_logger.emit(
                run_id=run.id,
                query_task_id=query_task_id,
                step="pubmed_search_started",
                status="running",
            )
            pubmed_result = self.pubmed_service.search_and_fetch(
                query_expression=task.query_expression,
                start_date=window_start.date().isoformat(),
                end_date=window_end.date().isoformat(),
                retmax=200,
            )
            self.event_logger.emit(
                run_id=run.id,
                query_task_id=query_task_id,
                step="pubmed_search_completed",
                status="success",
                payload_ref="pubmed_search_response",
                raw_count=len(pubmed_result.pmids),
            )
        except PubMedSearchError as exc:
            self.monitor_run_repo.update_status(run.id, MonitorRunStatus.FAILED, str(exc), 0, 0)
            self.event_logger.emit(
                run_id=run.id,
                query_task_id=query_task_id,
                step="monitor_run_failed",
                status=RunOutcome.FAILED.value,
                error=str(exc),
            )
            return MonitorRunResult(
                run_id=run.id,
                query_task_id=query_task_id,
                status=RunOutcome.FAILED,
                raw_result_count=0,
                new_result_count=0,
                paper_results=[],
                error_message=str(exc),
            )

        normalized = [self._paper_create_to_db(p) for p in pubmed_result.papers if p.pmid]
        self.event_logger.emit(
            run_id=run.id,
            query_task_id=query_task_id,
            step="papers_normalized",
            status="success",
            payload_ref="normalized_papers",
            normalized_count=len(normalized),
        )

        deduped = self._dedupe_by_pmid(normalized)
        self.event_logger.emit(
            run_id=run.id,
            query_task_id=query_task_id,
            step="papers_deduplicated",
            status="success",
            deduplicated_count=len(deduped),
        )

        paper_results: list[PaperProcessResult] = []
        partial_error = False

        for index, paper_db in enumerate(deduped, start=1):
            existed = self._paper_exists(paper_db.pmid)
            stored_paper = self.paper_repo.upsert_paper(paper_db)
            if not existed:
                self.paper_hit_repo.create_hit(
                    PaperQueryHitDB(
                        id=uuid4(),
                        paper_id=stored_paper.id,
                        query_task_id=query_task_id,
                        monitor_run_id=run.id,
                        matched_at=now,
                        rank_in_run=index,
                    )
                )

            paper_result = PaperProcessResult(
                paper_id=stored_paper.id,
                pmid=stored_paper.pmid,
                llm_success=False,
                delivery_success=False,
            )

            self.event_logger.emit(
                run_id=run.id,
                query_task_id=query_task_id,
                step="llm_summary_started",
                status="running",
                payload_ref=f"paper:{stored_paper.id}",
            )
            try:
                summary = self.llm_service.summarize_paper(stored_paper)
                self.summary_repo.create(self._to_summary_db(stored_paper.id, summary))
                paper_result.llm_success = True
                self.event_logger.emit(
                    run_id=run.id,
                    query_task_id=query_task_id,
                    step="llm_summary_completed",
                    status="success",
                    payload_ref=f"paper:{stored_paper.id}",
                )
            except Exception as exc:  # noqa: BLE001 - runtime boundary catch
                partial_error = True
                paper_result.llm_error = str(exc)
                self.event_logger.emit(
                    run_id=run.id,
                    query_task_id=query_task_id,
                    step="llm_summary_completed",
                    status="failed",
                    payload_ref=f"paper:{stored_paper.id}",
                    error=str(exc),
                )
                paper_results.append(paper_result)
                continue

            self.event_logger.emit(
                run_id=run.id,
                query_task_id=query_task_id,
                step="delivery_started",
                status="running",
                payload_ref=f"paper:{stored_paper.id}",
            )
            delivery = self._deliver(stored_paper, summary)
            paper_result.delivery_success = delivery.delivery_status == DeliveryStatus.SENT
            if not paper_result.delivery_success:
                partial_error = True
                paper_result.delivery_error = delivery.error_message
            self.event_logger.emit(
                run_id=run.id,
                query_task_id=query_task_id,
                step="delivery_completed",
                status="success" if paper_result.delivery_success else "failed",
                payload_ref=f"delivery:{delivery.id}",
                error=delivery.error_message,
            )
            paper_results.append(paper_result)

        if partial_error:
            final = RunOutcome.PARTIAL_SUCCESS
        else:
            final = RunOutcome.SUCCESS

        self.monitor_run_repo.update_status(
            run.id,
            self._to_monitor_run_status(final),
            None if final != RunOutcome.PARTIAL_SUCCESS else "Some papers failed in llm/delivery",
            raw_result_count=len(pubmed_result.pmids),
            new_result_count=len(deduped),
        )

        self.event_logger.emit(
            run_id=run.id,
            query_task_id=query_task_id,
            step="monitor_run_completed",
            status=final.value,
            payload_ref=f"monitor_run:{run.id}",
            raw_result_count=len(pubmed_result.pmids),
            new_result_count=len(deduped),
        )
        return MonitorRunResult(
            run_id=run.id,
            query_task_id=query_task_id,
            status=final,
            raw_result_count=len(pubmed_result.pmids),
            new_result_count=len(deduped),
            paper_results=paper_results,
            error_message=None if final != RunOutcome.PARTIAL_SUCCESS else "Some papers failed in llm/delivery",
        )

    def _paper_exists(self, pmid: str | None) -> bool:
        if not pmid:
            return False
        try:
            self.paper_repo.get_by_pmid(pmid)
            return True
        except NotFoundError:
            return False

    @staticmethod
    def _paper_create_to_db(paper: PaperCreate) -> PaperDB:
        now = datetime.utcnow()
        return PaperDB(
            id=uuid4(),
            pmid=paper.pmid,
            doi=paper.doi,
            title=paper.title,
            abstract=paper.abstract,
            journal=paper.journal,
            publication_date=paper.publication_date,
            authors=paper.authors,
            pubmed_url=paper.pubmed_url,
            raw_payload=paper.raw_payload,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _dedupe_by_pmid(papers: list[PaperDB]) -> list[PaperDB]:
        uniq: dict[str, PaperDB] = {}
        for paper in papers:
            if paper.pmid and paper.pmid not in uniq:
                uniq[paper.pmid] = paper
        return list(uniq.values())

    @staticmethod
    def _to_monitor_run_status(outcome: RunOutcome) -> MonitorRunStatus:
        if outcome == RunOutcome.SUCCESS:
            return MonitorRunStatus.SUCCEEDED
        if outcome == RunOutcome.PARTIAL_SUCCESS:
            return MonitorRunStatus.PARTIAL
        if outcome == RunOutcome.FAILED:
            return MonitorRunStatus.FAILED
        return MonitorRunStatus.RUNNING

    @staticmethod
    def _safe_relevance(value: str) -> RelevanceLevel:
        try:
            return RelevanceLevel(value)
        except Exception:
            return RelevanceLevel.MEDIUM

    @staticmethod
    def _safe_action(value: str) -> RecommendedAction:
        try:
            return RecommendedAction(value)
        except Exception:
            return RecommendedAction.SAVE_FOR_LATER

    def _to_summary_db(self, paper_id: UUID, summary: LlmSummaryOutput) -> LlmSummaryDB:
        return LlmSummaryDB(
            id=uuid4(),
            paper_id=paper_id,
            model_name=summary.model_name,
            prompt_version=summary.prompt_version,
            summary_version=summary.summary_version,
            one_line_takeaway=summary.one_line_takeaway,
            plain_chinese_summary=summary.plain_chinese_summary,
            study_type=summary.study_type,
            core_methods=summary.core_methods,
            main_findings=summary.main_findings,
            why_it_matters=summary.why_it_matters,
            relevance_level=self._safe_relevance(summary.relevance_level),
            relevance_score=summary.relevance_score,
            novelty_score=summary.novelty_score,
            actionability_score=summary.actionability_score,
            reason_for_relevance=summary.reason_for_relevance,
            tags=summary.tags,
            recommended_action=self._safe_action(summary.recommended_action),
            structured_output=summary.structured_output,
            generated_at=datetime.utcnow(),
        )

    def _deliver(self, paper: PaperDB, summary: LlmSummaryOutput) -> DeliveryRecordDB:
        delivery = DeliveryRecordDB(
            id=uuid4(),
            paper_id=paper.id,
            target_type="feishu",
            target_ref="default_webhook",
            card_id=None,
            delivery_status=DeliveryStatus.PENDING,
            delivered_at=None,
            error_message=None,
        )
        self.delivery_repo.create(delivery)

        payload = build_paper_card(paper, summary, metadata={"paper_id": str(paper.id)})
        resp = self.feishu_client.send_card(payload)
        if resp.success:
            return self.delivery_repo.update_status(
                delivery.id,
                DeliveryStatus.SENT,
                card_id=resp.card_id,
                error_message=None,
            )
        return self.delivery_repo.update_status(
            delivery.id,
            DeliveryStatus.FAILED,
            error_message=resp.error_message,
        )
