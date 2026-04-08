"""Controlled vocabularies used across schema layers."""

from enum import Enum


class MonitorRunStatus(str, Enum):
    """Execution status of a monitor run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"


class DeliveryStatus(str, Enum):
    """Delivery lifecycle status."""

    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    SKIPPED = "skipped"


class FeedbackLabel(str, Enum):
    """Normalized user feedback labels."""

    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    NOT_RELEVANT = "not_relevant"
    NEEDS_MORE_DETAIL = "needs_more_detail"
    FOLLOW_UP = "follow_up"


class RelevanceLevel(str, Enum):
    """Human-readable relevance tier for ranking papers."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendedAction(str, Enum):
    """Suggested downstream action generated from summary analysis."""

    READ_FULL_TEXT = "read_full_text"
    SHARE_WITH_TEAM = "share_with_team"
    TRACK_FOLLOW_UP = "track_follow_up"
    SAVE_FOR_LATER = "save_for_later"
    IGNORE = "ignore"
