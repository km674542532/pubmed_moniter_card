"""Orchestrates PubMed search + fetch + map into unified output."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.schemas.models import PaperCreate
from app.integrations.pubmed.fetch_client import PubMedFetchClient
from app.integrations.pubmed.mapper import map_pubmed_record_to_paper
from app.integrations.pubmed.search_client import PubMedSearchClient


@dataclass(slots=True)
class PubMedSearchAndFetchResult:
    papers: list[PaperCreate]
    pmids: list[str]
    search_raw_response: dict
    fetch_raw_response: dict


class PubMedService:
    def __init__(self, search_client: PubMedSearchClient, fetch_client: PubMedFetchClient):
        self.search_client = search_client
        self.fetch_client = fetch_client

    def search_and_fetch(
        self,
        query_expression: str,
        start_date: str,
        end_date: str,
        retmax: int = 100,
    ) -> PubMedSearchAndFetchResult:
        search_result = self.search_client.search_pmids(
            query_expression=query_expression,
            start_date=start_date,
            end_date=end_date,
            retmax=retmax,
        )
        fetch_result = self.fetch_client.fetch_papers(search_result.pmids)
        papers = [map_pubmed_record_to_paper(raw) for raw in fetch_result.records]
        return PubMedSearchAndFetchResult(
            papers=papers,
            pmids=search_result.pmids,
            search_raw_response=search_result.raw_response,
            fetch_raw_response=fetch_result.raw_response,
        )
