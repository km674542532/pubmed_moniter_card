"""PubMed ESearch client for PMID retrieval in a fixed time window."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass


class PubMedSearchError(RuntimeError):
    """Raised when PubMed ESearch fails."""


@dataclass(slots=True)
class PubMedSearchResult:
    pmids: list[str]
    raw_response: dict


class PubMedSearchClient:
    """Thin ESearch wrapper with timeout/error handling."""

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def search_pmids(
        self,
        query_expression: str,
        start_date: str,
        end_date: str,
        retmax: int = 100,
    ) -> PubMedSearchResult:
        params = {
            "db": "pubmed",
            "term": query_expression,
            "retmode": "json",
            "retmax": str(retmax),
            "datetype": "pdat",
            "mindate": start_date,
            "maxdate": end_date,
        }
        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url=url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise PubMedSearchError(f"PubMed ESearch request failed: {exc}") from exc

        id_list = data.get("esearchresult", {}).get("idlist")
        if not isinstance(id_list, list):
            raise PubMedSearchError("PubMed ESearch returned invalid idlist")
        return PubMedSearchResult(pmids=[str(i) for i in id_list], raw_response=data)
