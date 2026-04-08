"""Repositories for paper and paper-query-hit persistence operations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.core.schemas.models import PaperDB, PaperQueryHitDB
from app.repositories._utils import from_db_json, to_db_value
from app.repositories.db_adapter import DatabaseAdapter
from app.repositories.exceptions import NotFoundError, RepositoryError


class PaperRepository:
    def __init__(self, adapter: DatabaseAdapter):
        self.adapter = adapter

    def upsert_paper(self, paper: PaperDB) -> PaperDB:
        if not paper.pmid:
            raise RepositoryError("paper upsert requires non-empty PMID as natural unique key")
        payload = paper.model_dump()
        with self.adapter.session() as conn:
            existing = conn.execute("SELECT id FROM paper WHERE pmid = ?", (paper.pmid,)).fetchone()
            if existing:
                payload["id"] = existing["id"]
                payload["updated_at"] = datetime.utcnow()
                conn.execute(
                    """
                    UPDATE paper SET doi=?, title=?, abstract=?, journal=?, publication_date=?, authors=?,
                    pubmed_url=?, raw_payload=?, updated_at=? WHERE pmid=?
                    """,
                    (
                        payload["doi"], payload["title"], payload["abstract"], payload["journal"],
                        to_db_value(payload["publication_date"]), to_db_value(payload["authors"]),
                        payload["pubmed_url"], to_db_value(payload["raw_payload"]),
                        to_db_value(payload["updated_at"]), payload["pmid"],
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO paper (
                        id, pmid, doi, title, abstract, journal, publication_date,
                        authors, pubmed_url, raw_payload, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    tuple(to_db_value(payload[k]) for k in (
                        "id", "pmid", "doi", "title", "abstract", "journal", "publication_date",
                        "authors", "pubmed_url", "raw_payload", "created_at", "updated_at"
                    )),
                )
        return self.get_by_pmid(paper.pmid)

    def get_by_pmid(self, pmid: str) -> PaperDB:
        with self.adapter.session() as conn:
            row = conn.execute("SELECT * FROM paper WHERE pmid = ?", (pmid,)).fetchone()
        if row is None:
            raise NotFoundError(f"paper not found by pmid: {pmid}")
        data = dict(row)
        data["authors"] = from_db_json(data.get("authors")) or []
        data["raw_payload"] = from_db_json(data.get("raw_payload"))
        return PaperDB.model_validate(data)

    def get_by_id(self, paper_id: UUID) -> PaperDB:
        with self.adapter.session() as conn:
            row = conn.execute("SELECT * FROM paper WHERE id = ?", (str(paper_id),)).fetchone()
        if row is None:
            raise NotFoundError(f"paper not found by id: {paper_id}")
        data = dict(row)
        data["authors"] = from_db_json(data.get("authors")) or []
        data["raw_payload"] = from_db_json(data.get("raw_payload"))
        return PaperDB.model_validate(data)

    def list_by_ids(self, paper_ids: list[UUID]) -> list[PaperDB]:
        if not paper_ids:
            return []
        placeholders = ",".join("?" for _ in paper_ids)
        with self.adapter.session() as conn:
            rows = conn.execute(f"SELECT * FROM paper WHERE id IN ({placeholders})", tuple(str(i) for i in paper_ids)).fetchall()
        papers: list[PaperDB] = []
        for row in rows:
            data = dict(row)
            data["authors"] = from_db_json(data.get("authors")) or []
            data["raw_payload"] = from_db_json(data.get("raw_payload"))
            papers.append(PaperDB.model_validate(data))
        return papers


class PaperQueryHitRepository:
    def __init__(self, adapter: DatabaseAdapter):
        self.adapter = adapter

    def create_hit(self, hit: PaperQueryHitDB) -> PaperQueryHitDB:
        payload = hit.model_dump()
        with self.adapter.session() as conn:
            conn.execute(
                """
                INSERT INTO paper_query_hit (id, paper_id, query_task_id, monitor_run_id, matched_at, rank_in_run)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                tuple(to_db_value(payload[k]) for k in (
                    "id", "paper_id", "query_task_id", "monitor_run_id", "matched_at", "rank_in_run"
                )),
            )
        return hit

    def list_hits_by_run(self, monitor_run_id: UUID) -> list[PaperQueryHitDB]:
        with self.adapter.session() as conn:
            rows = conn.execute(
                "SELECT * FROM paper_query_hit WHERE monitor_run_id = ? ORDER BY matched_at, rank_in_run",
                (str(monitor_run_id),),
            ).fetchall()
        return [PaperQueryHitDB.model_validate(dict(row)) for row in rows]

    def exists_hit(self, paper_id: UUID, query_task_id: UUID) -> bool:
        with self.adapter.session() as conn:
            row = conn.execute(
                "SELECT 1 FROM paper_query_hit WHERE paper_id = ? AND query_task_id = ? LIMIT 1",
                (str(paper_id), str(query_task_id)),
            ).fetchone()
        return row is not None
