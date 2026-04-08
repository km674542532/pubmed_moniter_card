"""Builds Feishu interactive-card payloads for paper delivery."""

from __future__ import annotations

from app.core.schemas.models import PaperDB, PaperView
from app.integrations.llm.schemas import LlmSummaryOutput


def build_paper_card(paper: PaperDB | PaperView, llm_summary: LlmSummaryOutput, metadata: dict | None = None) -> dict:
    meta = metadata or {}
    return {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": paper.title}},
            "elements": [
                {"tag": "markdown", "content": f"**期刊**: {paper.journal or '-'}"},
                {"tag": "markdown", "content": f"**PMID**: {paper.pmid or '-'}"},
                {"tag": "markdown", "content": f"**一句话**: {llm_summary.one_line_takeaway or '-'}"},
                {"tag": "markdown", "content": f"**中文总结**: {llm_summary.plain_chinese_summary or '-'}"},
                {
                    "tag": "markdown",
                    "content": (
                        f"**相关性**: {llm_summary.relevance_level} ({llm_summary.relevance_score:.2f})\\n"
                        f"**建议动作**: {llm_summary.recommended_action}"
                    ),
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "查看 PubMed"},
                            "type": "primary",
                            "url": paper.pubmed_url or "https://pubmed.ncbi.nlm.nih.gov/",
                        }
                    ],
                },
            ],
        },
        "metadata": meta,
    }
