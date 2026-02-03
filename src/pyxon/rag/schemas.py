from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ReflectionDecision(BaseModel):
    """
    Structured output for reflection node.
    Filter must be {"document_id": "uuid-string"} or null.
    """
    critique: str = Field(
        description="Single concise critique message explaining document sufficiency and lessons from previous failures"
    )
    should_continue: bool = Field(
        description="TRUE if documents insufficient/irrelevant and we need another retrieval attempt, FALSE if sufficient"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of documents to retrieve next (1-20). Increase if coverage insufficient, decrease if noise too high"
    )
    filter: Optional[Dict[str, str]] = Field(
        default=None,
        description='Metadata filter as dict with string keys/values, e.g. {"document_id": "some-uuid"}, or null'
    )

