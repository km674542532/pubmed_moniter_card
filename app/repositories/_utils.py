"""Internal helpers for SQLite repository implementations."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any
from uuid import UUID


def to_db_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def from_db_json(value: str | None) -> Any:
    if value is None:
        return None
    return json.loads(value)
