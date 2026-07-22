import uuid

from pydantic import BaseModel


class InternalAuditRequest(BaseModel):
    user_id: uuid.UUID | None = None
    action_type: str
    result: str
    resource_type: str | None = None
    resource_id: str | None = None
    ip_address: str | None = None
    detail: dict | None = None
