import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict

PersonnelRole = Literal["SAHA_TEKNISYENI", "NOC_OPERATORU", "SUPERVIZOR", "ADMIN"]


class RegisterCustomerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str
    last_name: str
    gsm: str
    email: str | None = None


class RegisterCustomerResponse(BaseModel):
    gsm: str
    otp_sent: bool = True


class OtpVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gsm: str
    code: str


class UserPublic(BaseModel):
    id: uuid.UUID
    role: str
    first_name: str
    last_name: str
    gsm: str | None = None
    email: str | None = None
    specializations: list[str] = []
    regions: list[str] = []


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic


class PersonnelCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str
    last_name: str
    email: str
    password: str
    role: PersonnelRole
    specializations: list[str] = []
    regions: list[str] = []
    base_lat: float | None = None
    base_lon: float | None = None


class LoginRequest(BaseModel):
    """Personel: {email, password}. Müşteri: {gsm, otp}. Tek uçtan iki akış da
    kabul edilir (TASK_SPLIT.md §0 - "login (kayıt/giriş)")."""

    model_config = ConfigDict(extra="forbid")

    email: str | None = None
    password: str | None = None
    gsm: str | None = None
    otp: str | None = None


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class LogoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: PersonnelRole | None = None
    specializations: list[str] | None = None
    regions: list[str] | None = None
    is_active: bool | None = None
    base_lat: float | None = None
    base_lon: float | None = None


class AuditLogEntry(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    action_type: str
    resource_type: str | None
    resource_id: str | None
    ip_address: str | None
    result: str
    detail: dict | None
    created_at: str
