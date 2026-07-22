"""add ML_MODEL value to prediction_method enum

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-23

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ML fallback (app/core/ml_fallback.py) devreye girince PredictionMethod.ML_MODEL
    # kullaniliyor (bkz. app/schemas/contracts.py, docs/ai-approach.md SS7.1) - Postgres
    # tarafindaki enum tipi de guncellenmeli, yoksa INSERT
    # "invalid input value for enum prediction_method: ML_MODEL" ile patlar.
    # PG 12+: IF NOT EXISTS ile idempotent.
    op.execute("ALTER TYPE prediction_method ADD VALUE IF NOT EXISTS 'ML_MODEL'")


def downgrade() -> None:
    # PostgreSQL enum tiplerinden deger cikarmayi desteklemiyor (DROP VALUE yok).
    # Geri almak icin tum tipi yeniden olusturup bagli kolonlari donusturmek gerekir -
    # bu riskli/karmasik oldugu icin bilincli olarak no-op birakildi.
    pass
