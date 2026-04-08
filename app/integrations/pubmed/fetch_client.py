"""PubMed ESummary client that fetches raw paper payloads by PMID."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass


class PubMedFetchError(RuntimeError):
    """Raised when PubMed ESummary fetch fails."""


@dataclass(slots=True)
class PubMedFetchResult:
    records: list[dict]
    raw_response: dict


class PubMedFetchClient:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def fetch_papers(self, pmids: list[str]) -> PubMedFetchResult:
        if not pmids:
            return PubMedFetchResult(records=[], raw_response={"result": {}})

        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
            "version": "2.0",
        }
        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url=url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise PubMedFetchError(f"PubMed ESummary request failed: {exc}") from exc

        result = data.get("result", {})
        uids = result.get("uids", [])
        if not isinstance(uids, list):
            raise PubMedFetchError("PubMed ESummary returned invalid uids")

        records: list[dict] = []
        for uid in uids:
            rec = result.get(str(uid), {})
            if isinstance(rec, dict):
                records.append(rec)
        return PubMedFetchResult(records=records, raw_response=data)
