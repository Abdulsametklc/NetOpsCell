"""Unit tests for app.consumers.handlers._compute_level (saf fonksiyon, DB gerektirmez).

ARCHITECTURE.md seviye esikleri: BRONZ (<500) -> GUMUS (500-1499) -> ALTIN
(1500-2999) -> PLATIN (3000+).
"""

import pytest

from app.consumers.handlers import _compute_level
from app.schemas.contracts import Level


@pytest.mark.parametrize(
    "points, expected",
    [
        (0, Level.BRONZ),
        (499, Level.BRONZ),
        (500, Level.GUMUS),
        (1499, Level.GUMUS),
        (1500, Level.ALTIN),
        (2999, Level.ALTIN),
        (3000, Level.PLATIN),
        (10_000, Level.PLATIN),
    ],
)
def test_seviye_esikleri_dogru(points: int, expected: Level):
    assert _compute_level(points) == expected
