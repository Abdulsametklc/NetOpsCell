from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def generate_incident_number(db: AsyncSession) -> str:
    """INC-{yil}-{6 haneli sequence} uretir. Postgres native SEQUENCE kullanir, cakismasizdir."""
    result = await db.execute(text("SELECT nextval('incident_number_seq')"))
    seq_val = result.scalar_one()
    year = datetime.now(timezone.utc).year
    return f"INC-{year}-{seq_val:06d}"
