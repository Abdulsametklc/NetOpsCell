"""Unit tests for app.core.state_machine.validate_transition().

Pure logic, no DB/network involved - covers:
  * every edge in ALLOWED_TRANSITIONS with a happy-path test
  * InvalidTransition for edges not present in the graph
  * UnauthorizedTransition for a role not permitted on an existing edge
  * UnauthorizedTransition for ASSIGNED_TECHNICIAN_ONLY edges when the actor
    is not the technician assigned to the incident
"""

import uuid

import pytest

from app.core.state_machine import (
    ALLOWED_TRANSITIONS,
    ASSIGNED_TECHNICIAN_ONLY,
    InvalidTransition,
    SYSTEM_ACTOR_ID,
    UnauthorizedTransition,
    validate_transition,
)
from app.schemas.contracts import IncidentStatus

SOME_USER_ID = uuid.uuid4()
SOME_OTHER_USER_ID = uuid.uuid4()


def _first_role(from_status: IncidentStatus, to_status: IncidentStatus) -> str:
    return sorted(ALLOWED_TRANSITIONS[(from_status, to_status)])[0]


class TestHappyPathAllTransitions:
    """Every single edge in ALLOWED_TRANSITIONS must succeed with the right actor."""

    @pytest.mark.parametrize("from_status, to_status", list(ALLOWED_TRANSITIONS.keys()))
    def test_gecis_grafindaki_her_kenar_dogru_aktorle_basarili(self, from_status, to_status):
        key = (from_status, to_status)
        role = _first_role(from_status, to_status)

        if key in ASSIGNED_TECHNICIAN_ONLY:
            actor_user_id = SOME_USER_ID
            assigned_team_id = SOME_USER_ID
        else:
            actor_user_id = SOME_USER_ID
            assigned_team_id = SOME_OTHER_USER_ID  # should not matter outside the ONLY-set

        # Should not raise.
        validate_transition(
            from_status=from_status,
            to_status=to_status,
            actor_role=role,
            actor_user_id=actor_user_id,
            assigned_team_id=assigned_team_id,
        )

    def test_yeni_to_atandi_ile_supervizor_basarili(self):
        validate_transition(
            from_status=IncidentStatus.YENI,
            to_status=IncidentStatus.ATANDI,
            actor_role="SUPERVIZOR",
            actor_user_id=SOME_USER_ID,
            assigned_team_id=None,
        )

    def test_yeni_to_atandi_ile_admin_basarili(self):
        validate_transition(
            from_status=IncidentStatus.YENI,
            to_status=IncidentStatus.ATANDI,
            actor_role="ADMIN",
            actor_user_id=SOME_USER_ID,
            assigned_team_id=None,
        )

    def test_yeni_to_atandi_ile_system_basarili(self):
        validate_transition(
            from_status=IncidentStatus.YENI,
            to_status=IncidentStatus.ATANDI,
            actor_role="SYSTEM",
            actor_user_id=SYSTEM_ACTOR_ID,
            assigned_team_id=None,
        )

    def test_atandi_to_yolda_atanan_teknisyen_ile_basarili(self):
        validate_transition(
            from_status=IncidentStatus.ATANDI,
            to_status=IncidentStatus.YOLDA,
            actor_role="SAHA_TEKNISYENI",
            actor_user_id=SOME_USER_ID,
            assigned_team_id=SOME_USER_ID,
        )

    def test_cozuldu_to_kapandi_noc_operatoru_ile_basarili(self):
        validate_transition(
            from_status=IncidentStatus.COZULDU,
            to_status=IncidentStatus.KAPANDI,
            actor_role="NOC_OPERATORU",
            actor_user_id=SOME_USER_ID,
            assigned_team_id=None,
        )

    def test_cozuldu_to_kapandi_system_ile_basarili(self):
        validate_transition(
            from_status=IncidentStatus.COZULDU,
            to_status=IncidentStatus.KAPANDI,
            actor_role="SYSTEM",
            actor_user_id=SYSTEM_ACTOR_ID,
            assigned_team_id=None,
        )

    def test_parca_bekleniyor_to_mudahale_ediliyor_system_ile_basarili(self):
        validate_transition(
            from_status=IncidentStatus.PARCA_BEKLENIYOR,
            to_status=IncidentStatus.MUDAHALE_EDILIYOR,
            actor_role="SYSTEM",
            actor_user_id=SYSTEM_ACTOR_ID,
            assigned_team_id=None,
        )


class TestInvalidTransition:
    """Edges that simply do not exist in ALLOWED_TRANSITIONS."""

    def test_yeni_to_cozuldu_gecersiz_gecis(self):
        with pytest.raises(InvalidTransition):
            validate_transition(
                from_status=IncidentStatus.YENI,
                to_status=IncidentStatus.COZULDU,
                actor_role="ADMIN",
                actor_user_id=SOME_USER_ID,
                assigned_team_id=None,
            )

    def test_yeni_to_kapandi_gecersiz_gecis(self):
        with pytest.raises(InvalidTransition):
            validate_transition(
                from_status=IncidentStatus.YENI,
                to_status=IncidentStatus.KAPANDI,
                actor_role="ADMIN",
                actor_user_id=SOME_USER_ID,
                assigned_team_id=None,
            )

    def test_kapandi_to_yeni_geri_gecis_gecersiz(self):
        with pytest.raises(InvalidTransition):
            validate_transition(
                from_status=IncidentStatus.KAPANDI,
                to_status=IncidentStatus.YENI,
                actor_role="ADMIN",
                actor_user_id=SOME_USER_ID,
                assigned_team_id=None,
            )

    def test_ayni_duruma_gecis_gecersiz(self):
        with pytest.raises(InvalidTransition):
            validate_transition(
                from_status=IncidentStatus.ATANDI,
                to_status=IncidentStatus.ATANDI,
                actor_role="SAHA_TEKNISYENI",
                actor_user_id=SOME_USER_ID,
                assigned_team_id=SOME_USER_ID,
            )


class TestUnauthorizedTransitionWrongRole:
    """Edge exists in the graph but the given role is not among the allowed roles."""

    def test_yeni_to_atandi_saha_teknisyeni_yetkisiz(self):
        with pytest.raises(UnauthorizedTransition):
            validate_transition(
                from_status=IncidentStatus.YENI,
                to_status=IncidentStatus.ATANDI,
                actor_role="SAHA_TEKNISYENI",
                actor_user_id=SOME_USER_ID,
                assigned_team_id=None,
            )

    def test_atandi_to_yolda_supervizor_yetkisiz(self):
        with pytest.raises(UnauthorizedTransition):
            validate_transition(
                from_status=IncidentStatus.ATANDI,
                to_status=IncidentStatus.YOLDA,
                actor_role="SUPERVIZOR",
                actor_user_id=SOME_USER_ID,
                assigned_team_id=SOME_USER_ID,
            )

    def test_cozuldu_to_kapandi_saha_teknisyeni_yetkisiz(self):
        with pytest.raises(UnauthorizedTransition):
            validate_transition(
                from_status=IncidentStatus.COZULDU,
                to_status=IncidentStatus.KAPANDI,
                actor_role="SAHA_TEKNISYENI",
                actor_user_id=SOME_USER_ID,
                assigned_team_id=SOME_USER_ID,
            )

    def test_parca_bekleniyor_to_mudahale_ediliyor_saha_teknisyeni_yetkisiz(self):
        """Bu gecis sadece SYSTEM aktorune acik; saha teknisyeni manuel tetikleyemez."""
        with pytest.raises(UnauthorizedTransition):
            validate_transition(
                from_status=IncidentStatus.PARCA_BEKLENIYOR,
                to_status=IncidentStatus.MUDAHALE_EDILIYOR,
                actor_role="SAHA_TEKNISYENI",
                actor_user_id=SOME_USER_ID,
                assigned_team_id=SOME_USER_ID,
            )


class TestUnauthorizedTransitionWrongAssignee:
    """Role is correct, edge is in ASSIGNED_TECHNICIAN_ONLY, but actor != assigned technician."""

    def test_atandi_to_yolda_baska_teknisyen_yetkisiz(self):
        with pytest.raises(UnauthorizedTransition):
            validate_transition(
                from_status=IncidentStatus.ATANDI,
                to_status=IncidentStatus.YOLDA,
                actor_role="SAHA_TEKNISYENI",
                actor_user_id=SOME_USER_ID,
                assigned_team_id=SOME_OTHER_USER_ID,
            )

    def test_yolda_to_mudahale_ediliyor_baska_teknisyen_yetkisiz(self):
        with pytest.raises(UnauthorizedTransition):
            validate_transition(
                from_status=IncidentStatus.YOLDA,
                to_status=IncidentStatus.MUDAHALE_EDILIYOR,
                actor_role="SAHA_TEKNISYENI",
                actor_user_id=SOME_USER_ID,
                assigned_team_id=SOME_OTHER_USER_ID,
            )

    def test_mudahale_ediliyor_to_parca_bekleniyor_baska_teknisyen_yetkisiz(self):
        with pytest.raises(UnauthorizedTransition):
            validate_transition(
                from_status=IncidentStatus.MUDAHALE_EDILIYOR,
                to_status=IncidentStatus.PARCA_BEKLENIYOR,
                actor_role="SAHA_TEKNISYENI",
                actor_user_id=SOME_USER_ID,
                assigned_team_id=SOME_OTHER_USER_ID,
            )

    def test_mudahale_ediliyor_to_cozuldu_baska_teknisyen_yetkisiz(self):
        with pytest.raises(UnauthorizedTransition):
            validate_transition(
                from_status=IncidentStatus.MUDAHALE_EDILIYOR,
                to_status=IncidentStatus.COZULDU,
                actor_role="SAHA_TEKNISYENI",
                actor_user_id=SOME_USER_ID,
                assigned_team_id=SOME_OTHER_USER_ID,
            )

    def test_atanmamis_vaka_assigned_team_id_none_iken_teknisyen_yetkisiz(self):
        """assigned_team_id None ise hicbir actor_user_id ona esit olamaz -> yetkisiz."""
        with pytest.raises(UnauthorizedTransition):
            validate_transition(
                from_status=IncidentStatus.ATANDI,
                to_status=IncidentStatus.YOLDA,
                actor_role="SAHA_TEKNISYENI",
                actor_user_id=SOME_USER_ID,
                assigned_team_id=None,
            )


class TestAllowedTransitionsGraphCoverage:
    def test_grafta_tam_yedi_gecis_tanimli(self):
        assert len(ALLOWED_TRANSITIONS) == 7

    def test_her_assigned_technician_only_kenari_graftadir(self):
        assert ASSIGNED_TECHNICIAN_ONLY.issubset(set(ALLOWED_TRANSITIONS.keys()))
