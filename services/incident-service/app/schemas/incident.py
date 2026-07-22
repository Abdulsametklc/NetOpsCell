import uuid

from pydantic import BaseModel, Field

from app.schemas.contracts import FaultType, IncidentStatus


class StatusChangeRequest(BaseModel):
    to_status: IncidentStatus
    note: str | None = None


class FaultTypeChangeRequest(BaseModel):
    fault_type: FaultType


class ManualAssignRequest(BaseModel):
    team_id: uuid.UUID
    team_name: str = Field(min_length=1, max_length=128)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class ResolutionNoteCreate(BaseModel):
    note: str = Field(min_length=1, max_length=4000)


class EvaluationCreate(BaseModel):
    stars: int = Field(ge=1, le=5)
    is_permanent: bool
