"""Prompt builders for paper summarization and preference mapping."""

from __future__ import annotations

from app.core.schemas.models import PaperDB, PaperView


def build_general_literature_prompt(paper: PaperDB | PaperView) -> str:
    return (
        "你是医学文献分析助手。请基于以下论文信息输出结构化 JSON，总结研究类型、方法、核心发现、"
        "临床/科研意义，并给出相关性与可执行性评分。\n"
        f"标题: {paper.title}\n"
        f"摘要: {paper.abstract or ''}\n"
        f"期刊: {paper.journal or ''}\n"
        f"作者: {', '.join(paper.authors)}\n"
        "请确保输出可被 JSON 解析，且不要输出额外解释文本。"
    )


def build_preference_mapping_prompt(summary_json: dict, preference_context: dict) -> str:
    return (
        "你是偏好映射助手。请根据用户偏好对已有论文总结进行二次映射，"
        "输出 JSON，包含偏好匹配理由、推荐动作与标签调整建议。\n"
        f"现有总结: {summary_json}\n"
        f"偏好上下文: {preference_context}\n"
        "只输出 JSON。"
    )
