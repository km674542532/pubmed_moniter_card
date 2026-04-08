"""Mapper from PubMed external payload to internal PaperCreate schema."""

from __future__ import annotations

import re
from datetime import date

from app.core.schemas.models import PaperCreate


def _extract_publication_date(raw: dict) -> date | None:
    text = raw.get("sortpubdate") or raw.get("pubdate")
    if not isinstance(text, str) or not text.strip():
        return None

    value = text.strip()
    m = re.match(r"^(\d{4})[-/](\d{2})[-/](\d{2})", value)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"^(\d{4})[-/](\d{2})", value)
    if m:
        return date(int(m.group(1)), int(m.group(2)), 1)
    m = re.match(r"^(\d{4})", value)
    if m:
        return date(int(m.group(1)), 1, 1)
    return None


def map_pubmed_record_to_paper(raw_record: dict) -> PaperCreate:
    authors = [a.get("name") for a in raw_record.get("authors", []) if isinstance(a, dict) and a.get("name")]
    pmid = str(raw_record.get("uid")) if raw_record.get("uid") else None
    pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None

    return PaperCreate(
        pmid=pmid,
        doi=raw_record.get("elocationid"),
        title=raw_record.get("title") or "",
        abstract=raw_record.get("abstract"),
        journal=raw_record.get("fulljournalname") or raw_record.get("source"),
        publication_date=_extract_publication_date(raw_record),
        authors=authors,
        pubmed_url=pubmed_url,
        raw_payload=raw_record,
    )
