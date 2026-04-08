"""Schemas for Feishu integration responses."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class FeishuDeliveryResult:
    success: bool
    card_id: str | None
    raw_response: dict | None
    error_message: str | None = None
