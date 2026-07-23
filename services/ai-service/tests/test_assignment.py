"""Unit tests for app.core.assignment (akilli saha ekibi atama skorlamasi) ve
app.core.geo.haversine_km.

ARCHITECTURE.md SS7: skor = (uzmanlik_eslesme x 0.4) + (mesafe_yakinlik x 0.3)
+ (bosluk_orani x 0.3). Bu formulun her bilesenini ayri ayri ve birlikte
dogrulariz. score_candidates() gercek bir AsyncSession bekler (Postgres'e ozgu
ARRAY sutunlari nedeniyle SQLite ile calismaz); bu yuzden DB yerine sahte
(fake) bir session/model kullanip GERCEK skorlama fonksiyonunu calistiririz -
boylece Postgres'e ihtiyac duymadan asil is mantigi test edilir.
"""

import uuid
from types import SimpleNamespace

import pytest

from app.core.assignment import CandidateScore, pick_best, score_candidates
from app.core.geo import haversine_km
from app.schemas.contracts import FaultType


class TestHaversine:
    def test_ayni_nokta_sifir_mesafe_verir(self):
        assert haversine_km(41.0082, 28.9784, 41.0082, 28.9784) == pytest.approx(0.0, abs=1e-9)

    def test_bilinen_iki_sehir_arasi_mesafe_dogru(self):
        # Istanbul (41.0082, 28.9784) - Ankara (39.9334, 32.8597) ~ 349 km (kus ucusu)
        km = haversine_km(41.0082, 28.9784, 39.9334, 32.8597)
        assert km == pytest.approx(349, abs=5)

    def test_simetrik(self):
        a = haversine_km(41.0082, 28.9784, 39.9334, 32.8597)
        b = haversine_km(39.9334, 32.8597, 41.0082, 28.9784)
        assert a == pytest.approx(b, abs=1e-9)


class TestPickBest:
    def _cand(self, score: float, has_capacity: bool, team_id: str = "t1") -> CandidateScore:
        return CandidateScore(
            team_id=team_id, team_name=team_id, score=score,
            expertise=0.0, proximity=0.0, capacity_ratio=0.0, has_capacity=has_capacity,
        )

    def test_bos_liste_none_doner(self):
        assert pick_best([]) is None

    def test_kapasitesi_dolu_tek_aday_none_doner(self):
        assert pick_best([self._cand(0.9, has_capacity=False)]) is None

    def test_en_yuksek_skorlu_musait_aday_secilir(self):
        low = self._cand(0.3, has_capacity=True, team_id="low")
        high = self._cand(0.9, has_capacity=True, team_id="high")
        chosen = pick_best([high, low])
        assert chosen is not None
        assert chosen.team_id == "high"

    def test_kapasitesi_dolu_daha_yuksek_skorlu_aday_atlanir(self):
        """Skoru yuksek ama kapasitesi dolu aday secilmemeli - musait olan
        (dusuk skorlu bile olsa) tercih edilmeli. score_candidates() zaten
        skora gore siraladigi icin ilk musait olan feasible[0] dogru secim."""
        full_but_high = self._cand(0.95, has_capacity=False, team_id="full")
        available_lower = self._cand(0.4, has_capacity=True, team_id="available")
        chosen = pick_best([full_but_high, available_lower])
        assert chosen is not None
        assert chosen.team_id == "available"


class _FakeScalars:
    def __init__(self, items: list) -> None:
        self._items = items

    def all(self):
        return self._items


class _FakeResult:
    def __init__(self, items: list) -> None:
        self._items = items

    def scalars(self):
        return _FakeScalars(self._items)


class _FakeSession:
    """score_candidates()'in bekledigi AsyncSession arayuzunun (execute + get)
    gercek bir Postgres olmadan calisan minimal sahte implementasyonu."""

    def __init__(self, teams: list, workloads: dict) -> None:
        self._teams = teams
        self._workloads = workloads

    async def execute(self, _stmt):
        return _FakeResult(self._teams)

    async def get(self, _model, team_id):
        return self._workloads.get(team_id)


def make_team(*, team_id=None, specializations, base_lat, base_lon, capacity=5):
    return SimpleNamespace(
        id=team_id or uuid.uuid4(),
        name=f"team-{specializations}",
        specializations=specializations,
        base_lat=base_lat,
        base_lon=base_lon,
        capacity=capacity,
        is_active=True,
    )


def make_workload(active_incident_count: int):
    return SimpleNamespace(active_incident_count=active_incident_count)


class TestScoreCandidatesFormula:
    @pytest.mark.asyncio
    async def test_uzmanlik_eslesen_ve_yakin_ekip_daha_yuksek_skor_alir(self):
        istanbul = (41.0082, 28.9784)
        near = make_team(specializations=[FaultType.ISINMA], base_lat=istanbul[0], base_lon=istanbul[1])
        far = make_team(specializations=[FaultType.ISINMA], base_lat=39.9334, base_lon=32.8597)  # Ankara
        session = _FakeSession(teams=[near, far], workloads={near.id: make_workload(0), far.id: make_workload(0)})

        results = await score_candidates(session, fault_type=FaultType.ISINMA, lat=istanbul[0], lng=istanbul[1])

        assert results[0].team_id == str(near.id)  # daha yakin olan ekip once gelmeli
        assert results[0].score > results[1].score

    @pytest.mark.asyncio
    async def test_uzmanligi_olmayan_ekip_dusuk_skor_alir(self):
        istanbul = (41.0082, 28.9784)
        matches = make_team(specializations=[FaultType.ISINMA], base_lat=istanbul[0], base_lon=istanbul[1])
        no_match = make_team(specializations=[FaultType.YAZILIM], base_lat=istanbul[0], base_lon=istanbul[1])
        session = _FakeSession(
            teams=[matches, no_match],
            workloads={matches.id: make_workload(0), no_match.id: make_workload(0)},
        )

        results = await score_candidates(session, fault_type=FaultType.ISINMA, lat=istanbul[0], lng=istanbul[1])
        by_id = {r.team_id: r for r in results}

        assert by_id[str(matches.id)].components["uzmanlik_eslesme"] == 1.0
        assert by_id[str(no_match.id)].components["uzmanlik_eslesme"] == 0.0
        assert by_id[str(matches.id)].score > by_id[str(no_match.id)].score

    @pytest.mark.asyncio
    async def test_dolu_kapasiteli_ekip_bosluk_orani_sifira_yaklasir(self):
        istanbul = (41.0082, 28.9784)
        team = make_team(specializations=[FaultType.ISINMA], base_lat=istanbul[0], base_lon=istanbul[1], capacity=5)
        session = _FakeSession(teams=[team], workloads={team.id: make_workload(5)})  # tam kapasitede

        results = await score_candidates(session, fault_type=FaultType.ISINMA, lat=istanbul[0], lng=istanbul[1])

        assert results[0].components["bosluk_orani"] == pytest.approx(0.0)
        assert results[0].has_capacity is False

    @pytest.mark.asyncio
    async def test_workload_kaydi_yoksa_bos_kabul_edilir(self):
        istanbul = (41.0082, 28.9784)
        team = make_team(specializations=[FaultType.ISINMA], base_lat=istanbul[0], base_lon=istanbul[1])
        session = _FakeSession(teams=[team], workloads={})  # hic workload kaydi yok

        results = await score_candidates(session, fault_type=FaultType.ISINMA, lat=istanbul[0], lng=istanbul[1])

        assert results[0].components["bosluk_orani"] == pytest.approx(1.0)
        assert results[0].has_capacity is True

    @pytest.mark.asyncio
    async def test_formul_agirliklari_dogru_uygulaniyor(self):
        """skor = uzmanlik*0.4 + yakinlik*0.3 + bosluk*0.3 - ayni noktada (yakinlik=1.0),
        tam uzmanlik eslesmesi (1.0) ve bos kapasite (1.0) ile skor tam 1.0 olmali."""
        lat, lng = 41.0082, 28.9784
        team = make_team(specializations=[FaultType.ISINMA], base_lat=lat, base_lon=lng, capacity=5)
        session = _FakeSession(teams=[team], workloads={team.id: make_workload(0)})

        results = await score_candidates(session, fault_type=FaultType.ISINMA, lat=lat, lng=lng)

        assert results[0].score == pytest.approx(1.0, abs=1e-6)
