"""docs/CONTRACTS.md'den kopyalanan ortak sözleşme tipleri (database-per-service
kuralı gereği pip paketi yerine her serviste kopya tutulur)."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    violations: list[str] | None = None
    retry_after_seconds: int | None = None


class ResponseEnvelope(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: ErrorDetail | None = None
