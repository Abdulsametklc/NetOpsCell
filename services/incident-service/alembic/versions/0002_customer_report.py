"""musteri arizasi bildirimi icin alanlar

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-23

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("incidents", sa.Column("customer_description", sa.Text(), nullable=True))
    op.alter_column("incidents", "lat", existing_type=sa.Float(), nullable=True)
    op.alter_column("incidents", "lng", existing_type=sa.Float(), nullable=True)


def downgrade() -> None:
    op.alter_column("incidents", "lat", existing_type=sa.Float(), nullable=False)
    op.alter_column("incidents", "lng", existing_type=sa.Float(), nullable=False)
    op.drop_column("incidents", "customer_description")
