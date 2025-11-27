"""Pydantic models for API requests."""
from pydantic import BaseModel


class RequestModel(BaseModel):
    """Model for basic request."""
    query: str


class TermRequestModel(BaseModel):
    """Model for term definition request."""
    term: str


class ProcessRequestModel(BaseModel):
    """Model for processing user request."""
    query: str
    request_type: str  # "document" или "term"
    template_name: str | None = None  # Имя файла шаблона


class FeedbackRequestModel(BaseModel):
    """Model for feedback submission."""
    author: str | None = None
    doc_type: str | None = None
    doc_ref: str | None = None
    operation: str | None = None  # "delete", "replace", "add", "comment"
    old_text: str | None = None
    new_text: str | None = None
    comment: str | None = None


