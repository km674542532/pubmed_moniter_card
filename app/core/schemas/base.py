"""Shared base schemas for the literature monitoring system."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class SchemaModel(BaseModel):
    """Common config for all schema models."""

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=False,
        extra="forbid",
        str_strip_whitespace=True,
    )


class IdentifiedModel(SchemaModel):
    """Mixin that provides a globally unique identifier."""

    id: UUID = Field(default_factory=uuid4, description="Unique object identifier")


class TimestampedModel(SchemaModel):
    """Mixin for create/update timestamps maintained by the system."""

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp in UTC",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp in UTC",
    )


class AuditFieldsModel(TimestampedModel):
    """Common audit fields mixin."""

    created_by: str | None = Field(default=None, description="Actor that created this record")
    updated_by: str | None = Field(default=None, description="Actor that last updated this record")
