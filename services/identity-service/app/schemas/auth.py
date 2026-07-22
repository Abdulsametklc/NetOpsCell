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


class TokenResponse(BaseModel):
    access_token: str
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
