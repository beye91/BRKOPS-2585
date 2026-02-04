# =============================================================================
# BRKOPS-2585 Common Pydantic Models
# =============================================================================

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: List[T]
    total: int
    page: int = 1
    per_page: int = 20
    pages: int = 1


class ErrorResponse(BaseModel):
    """Error response schema."""

    detail: str
    message: Optional[str] = None
    code: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    service: str
    version: str
    components: Optional[dict] = None


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = True
    message: str


class BaseTimestampModel(BaseModel):
    """Base model with timestamps."""

    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True
