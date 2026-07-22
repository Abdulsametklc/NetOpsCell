from pydantic import BaseModel

from app.schemas.contracts import IncidentStatus


class StatusChangeRequest(BaseModel):
    to_status: IncidentStatus
    note: str | None = None
