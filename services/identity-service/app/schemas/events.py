from typing import Literal

from pydantic import BaseModel

# docs/CONTRACTS.md §3 - IdentityPersonnelUpserted ile birebir aynı (her serviste kopya tutulur).


class IdentityPersonnelUpserted(BaseModel):
    event_type: Literal["identity.personnel.upserted"] = "identity.personnel.upserted"
    user_id: str
    name: str
    specializations: list[str]
    regions: list[str]
    base_lat: float
    base_lon: float
    is_active: bool
