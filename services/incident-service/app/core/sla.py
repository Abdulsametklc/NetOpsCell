from datetime import timedelta

from app.schemas.contracts import Priority

# Case Bolum 4.4 SLA tablosu. Gamification Service de ayni sureleri (bagimsiz statik sabit
# olarak) puan hesaplarken kullanir - bkz. gamification-service/app/consumers/handlers.py.
SLA_DURATIONS: dict[Priority, timedelta] = {
    Priority.KRITIK: timedelta(hours=1),
    Priority.YUKSEK: timedelta(hours=4),
    Priority.ORTA: timedelta(hours=12),
    Priority.DUSUK: timedelta(hours=48),
}
