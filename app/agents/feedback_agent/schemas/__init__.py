"""Feedback agent schema bindings to the unified core contracts."""

from app.core.schemas import PreferenceProfileDB, PreferenceProfileUpsert, PreferenceProfileView, UserFeedbackCreate, UserFeedbackDB

__all__ = [
    "PreferenceProfileDB",
    "PreferenceProfileUpsert",
    "PreferenceProfileView",
    "UserFeedbackCreate",
    "UserFeedbackDB",
]
