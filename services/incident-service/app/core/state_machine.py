import uuid

from app.schemas.contracts import IncidentStatus

# Otomatik (AI/scheduler tetikli) gecislerde gercek bir insan aktoru olmadigi icin sabit bir
# sentinel UUID kullanilir (audit/status_history alanlarinda "SYSTEM" rolunun kim'i olarak).
SYSTEM_ACTOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")

# Kaynak: ARCHITECTURE.md SS4.2.1 (case Bolum 4.2 durum makinesi tablosunun birebir uygulanmasi).
# "SYSTEM" gercek bir kullanici rolu degil; AI'in otomatik atamasi veya arka plan gorevlerinin
# (parca tedariki, 24 saat sonra otomatik kapanma) bu gecisleri tetiklemesi icin kullanilan
# ozel bir aktor degeridir.
ALLOWED_TRANSITIONS: dict[tuple[IncidentStatus, IncidentStatus], set[str]] = {
    (IncidentStatus.YENI, IncidentStatus.ATANDI): {"SYSTEM", "SUPERVIZOR"},
    (IncidentStatus.ATANDI, IncidentStatus.YOLDA): {"SAHA_TEKNISYENI"},
    (IncidentStatus.YOLDA, IncidentStatus.MUDAHALE_EDILIYOR): {"SAHA_TEKNISYENI"},
    (IncidentStatus.MUDAHALE_EDILIYOR, IncidentStatus.PARCA_BEKLENIYOR): {"SAHA_TEKNISYENI"},
    (IncidentStatus.PARCA_BEKLENIYOR, IncidentStatus.MUDAHALE_EDILIYOR): {"SYSTEM"},
    (IncidentStatus.MUDAHALE_EDILIYOR, IncidentStatus.COZULDU): {"SAHA_TEKNISYENI"},
    (IncidentStatus.COZULDU, IncidentStatus.KAPANDI): {"SYSTEM", "NOC_OPERATORU"},
}

# Bu gecisler icin rol dogru olsa bile sadece vakaya ATANAN teknisyen yetkilidir
# (baska bir Saha Teknisyeni'nin vakasini degistiremez).
ASSIGNED_TECHNICIAN_ONLY: set[tuple[IncidentStatus, IncidentStatus]] = {
    (IncidentStatus.ATANDI, IncidentStatus.YOLDA),
    (IncidentStatus.YOLDA, IncidentStatus.MUDAHALE_EDILIYOR),
    (IncidentStatus.MUDAHALE_EDILIYOR, IncidentStatus.PARCA_BEKLENIYOR),
    (IncidentStatus.MUDAHALE_EDILIYOR, IncidentStatus.COZULDU),
}


class TransitionError(Exception):
    pass


class InvalidTransition(TransitionError):
    """Grafta olmayan bir gecis denendi -> caller 422 donmeli."""


class UnauthorizedTransition(TransitionError):
    """Gecis grafta var ama bu rol/kisi yetkili degil -> caller 403 donmeli."""


def validate_transition(
    *,
    from_status: IncidentStatus,
    to_status: IncidentStatus,
    actor_role: str,
    actor_user_id: uuid.UUID,
    assigned_team_id: uuid.UUID | None,
) -> None:
    key = (from_status, to_status)

    if key not in ALLOWED_TRANSITIONS:
        raise InvalidTransition(f"{from_status.value} -> {to_status.value} gecerli bir durum gecisi degil")

    allowed_roles = ALLOWED_TRANSITIONS[key]
    if actor_role not in allowed_roles:
        raise UnauthorizedTransition(
            f"'{actor_role}' rolu {from_status.value} -> {to_status.value} gecisini yapamaz"
        )

    if key in ASSIGNED_TECHNICIAN_ONLY and actor_user_id != assigned_team_id:
        raise UnauthorizedTransition("Bu vakaya atanan teknisyen siz degilsiniz")
