"""Database initialization script for repository layer core tables."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS query_task (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    query_expression TEXT NOT NULL,
    schedule TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    lookback_hours INTEGER NOT NULL DEFAULT 24,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT,
    updated_by TEXT
);

CREATE TABLE IF NOT EXISTS monitor_run (
    id TEXT PRIMARY KEY,
    query_task_id TEXT NOT NULL,
    triggered_at TEXT NOT NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    status TEXT NOT NULL,
    raw_result_count INTEGER NOT NULL DEFAULT 0,
    new_result_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    FOREIGN KEY (query_task_id) REFERENCES query_task(id)
);

CREATE TABLE IF NOT EXISTS paper (
    id TEXT PRIMARY KEY,
    pmid TEXT NOT NULL UNIQUE,
    doi TEXT,
    title TEXT NOT NULL,
    abstract TEXT,
    journal TEXT,
    publication_date TEXT,
    authors TEXT NOT NULL DEFAULT '[]',
    pubmed_url TEXT,
    raw_payload TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paper_query_hit (
    id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    query_task_id TEXT NOT NULL,
    monitor_run_id TEXT NOT NULL,
    matched_at TEXT NOT NULL,
    rank_in_run INTEGER,
    FOREIGN KEY (paper_id) REFERENCES paper(id),
    FOREIGN KEY (query_task_id) REFERENCES query_task(id),
    FOREIGN KEY (monitor_run_id) REFERENCES monitor_run(id)
);

CREATE TABLE IF NOT EXISTS llm_summary (
    id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    summary_version INTEGER NOT NULL,
    one_line_takeaway TEXT,
    plain_chinese_summary TEXT,
    study_type TEXT,
    core_methods TEXT NOT NULL DEFAULT '[]',
    main_findings TEXT NOT NULL DEFAULT '[]',
    why_it_matters TEXT,
    relevance_level TEXT NOT NULL,
    relevance_score REAL NOT NULL,
    novelty_score REAL NOT NULL,
    actionability_score REAL NOT NULL,
    reason_for_relevance TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    recommended_action TEXT NOT NULL,
    structured_output TEXT,
    generated_at TEXT NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES paper(id)
);

CREATE TABLE IF NOT EXISTS delivery_record (
    id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_ref TEXT NOT NULL,
    card_id TEXT,
    delivery_status TEXT NOT NULL,
    delivered_at TEXT,
    error_message TEXT,
    FOREIGN KEY (paper_id) REFERENCES paper(id)
);

CREATE TABLE IF NOT EXISTS user_feedback (
    id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    source TEXT NOT NULL,
    label TEXT NOT NULL,
    note TEXT,
    actor TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES paper(id)
);

CREATE TABLE IF NOT EXISTS preference_profile (
    id TEXT PRIMARY KEY,
    profile_name TEXT NOT NULL UNIQUE,
    hard_rules TEXT NOT NULL DEFAULT '[]',
    soft_preferences TEXT NOT NULL DEFAULT '[]',
    excluded_patterns TEXT NOT NULL DEFAULT '[]',
    preferred_journals TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_paper_pmid ON paper(pmid);
CREATE INDEX IF NOT EXISTS idx_monitor_run_query_task_id ON monitor_run(query_task_id);
CREATE INDEX IF NOT EXISTS idx_paper_query_hit_run ON paper_query_hit(monitor_run_id);
CREATE INDEX IF NOT EXISTS idx_paper_query_hit_paper ON paper_query_hit(paper_id);
CREATE INDEX IF NOT EXISTS idx_llm_summary_paper_id ON llm_summary(paper_id);
CREATE INDEX IF NOT EXISTS idx_llm_summary_version ON llm_summary(paper_id, summary_version DESC);
CREATE INDEX IF NOT EXISTS idx_delivery_status ON delivery_record(delivery_status);
CREATE INDEX IF NOT EXISTS idx_delivery_paper_id ON delivery_record(paper_id);
CREATE INDEX IF NOT EXISTS idx_feedback_paper_id ON user_feedback(paper_id);
"""


def init_db(db_path: str | Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db(Path("app.db"))
